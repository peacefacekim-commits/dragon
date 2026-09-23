"""
공용 프로세스 잠금 (2026-09-03 추가, exec_lock/daemon.py/watch_positions.py 통합).

세 곳(exec_lock.py의 trading.lock, daemon.py의 daemon.lock, watch_positions.py의
watch_positions.lock)에 "락 파일이 있으면 안에 적힌 PID를 읽어서 tasklist로
살아있는지 확인하고, 죽었으면 덮어쓴다"는 패턴이 각자 복사돼 있었다. 이 방식은
결함이 두 가지였다 (2026-09-03, 써니전자/소마젠 중복매수 + 아이큐어 손절 미실행
사고로 실제로 터짐):

1. 원자적이지 않다 (check-then-write). "파일 존재 확인"과 "파일 쓰기"가 별도
   연산이라, 두 프로세스가 파일이 아직 없는 순간에 거의 동시에 확인하면 둘 다
   "없음"으로 보고 둘 다 통과해버린다.
2. 락 해제가 프로세스의 정상 종료(finally 블록)에 의존한다. daemon.py는 멈춘
   자식 프로세스를 타임아웃으로 강제종료하는데, 강제종료되면 finally가 안 돌아서
   락 파일이 죽은 PID를 문 채로 영원히 남는다. 그 PID가 나중에 다른 프로세스에
   재사용되면(윈도우는 PID를 금방 재사용함) tasklist 확인이 "살아있음"으로
   오판해서 락이 영구적으로 눌러붙는다 - 이후 모든 실행이 조용히 스킵된다.

OS 파일 잠금(Windows: msvcrt.locking, POSIX: fcntl.flock - 개발/테스트 환경이
리눅스라 둘 다 지원)으로 바꿔서 두 문제를 한 번에 없앤다:
- 잠금 획득이 OS 시스템콜 레벨에서 원자적이라 레이스 자체가 없다.
- 잠금은 "열려 있는 파일 핸들"에 걸리는 것이라, 프로세스가 정상 종료든 강제
  종료든 크래시든 상관없이 OS가 프로세스 종료 시 핸들을 자동으로 닫으면서 잠금도
  같이 풀어준다. release() 코드가 실행됐는지와 무관하게 항상 풀린다.
"""
import os
from contextlib import contextmanager

try:
    import msvcrt
    _PLATFORM = "windows"
except ImportError:
    import fcntl
    _PLATFORM = "posix"


class AlreadyRunning(Exception):
    """이미 다른 프로세스가 이 잠금을 잡고 있어서 이번 실행은 건너뛴다."""


class ProcLock:
    """파일 하나를 OS 레벨 잠금으로 관리한다.

        lock = ProcLock(path)
        if not lock.try_acquire():
            ...  # 이미 다른 프로세스가 잡고 있음
        try:
            ...
        finally:
            lock.release()

    또는 with lock.guard(): ... 로 AlreadyRunning 예외를 바로 쓸 수도 있다.
    """

    def __init__(self, path):
        self.path = path
        self._fh = None

    def try_acquire(self) -> bool:
        if self._fh is not None:
            # 이미 이 인스턴스가 잡고 있는 상태에서 또 acquire 하는 건 호출부 버그.
            raise RuntimeError(f"ProcLock({self.path})을 이미 잡은 상태에서 다시 acquire 호출됨")

        fh = open(self.path, "a+b")
        try:
            if _PLATFORM == "windows":
                if os.fstat(fh.fileno()).st_size == 0:
                    fh.write(b"\0")
                    fh.flush()
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            return False

        # 잠금은 이미 잡았으니, 디버깅용으로 현재 PID를 내용으로 남긴다
        # (락 자체의 안전성은 이 내용과 무관 - 순전히 사람이 들여다볼 때 참고용).
        fh.seek(0)
        fh.write(str(os.getpid()).encode())
        fh.truncate()
        fh.flush()
        self._fh = fh
        return True

    def release(self):
        fh = self._fh
        if fh is None:
            return
        self._fh = None
        try:
            fh.seek(0)
            if _PLATFORM == "windows":
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        finally:
            fh.close()

    @contextmanager
    def guard(self, message="이미 다른 실행이 진행 중이라 이번 실행은 건너뜁니다."):
        if not self.try_acquire():
            raise AlreadyRunning(message)
        try:
            yield
        finally:
            self.release()
