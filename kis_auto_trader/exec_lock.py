"""
실행(run_once) 구간 자체를 감싸는 잠금장치 (2026-08-11 추가).

(2026-09-04) 실전투자를 접은 뒤로는 이 구간이 실제 매매가 아니라 순수 관찰/
기록이지만, 아래 설명된 중복 실행 문제(같은 프로세스가 겹쳐 도는 것) 자체는
매매 여부와 무관하게 여전히 막아야 해서 잠금장치는 그대로 둔다.

daemon.py 의 daemon.lock 은 daemon 프로세스끼리 중복 실행되는 것만 막았다.
그런데 오늘 daemon 이 main.py 를 서브프로세스로 돌리는 도중에, 사람이 터미널에서
직접 `python main.py` 를 같이 실행해서 두 실행이 겹친 사고가 있었다 (솔트룩스가
0 -> 13 -> 21 -> 30주로 짧은 시간에 3번 중복 매수됐다). 두 프로세스가 각자
holdings 스냅샷을 따로 들고 있다 보니, 서로의 매수를 모른 채 똑같은 "아직 안
샀다"는 판단을 반복했기 때문이다.

daemon.lock 과 별도로 이 잠금은 "실행 경로가 daemon 서브프로세스든 사람이 직접
실행한 것이든 상관없이" 실제 매매 로직(run_once, liquidate_all_positions) 실행
구간 자체를 막는다. 이미 누가 실행 중이면 기다리지 않고 즉시 건너뛴다 - 몇 분
기다렸다가 실행하면 그 사이 시세가 바뀌어 오히려 더 혼란스럽다.

(2026-09-03) 처음 버전은 "락 파일 존재 확인 후 PID 써넣기"를 직접 구현했는데,
그 방식이 원자적이지 않아서(check-then-write) 정확히 막으려던 것과 같은 종류의
중복 실행 사고(써니전자/소마젠 2배 매수)가 다시 터졌고, 강제종료 시 락이 안
풀려 손절 판단이 4시간 멈추는 사고까지 이어졌다. proc_lock.ProcLock (OS 파일
잠금 기반)으로 교체해서 두 문제를 근본적으로 없앴다 - 자세한 이유는
proc_lock.py 참고.
"""
from contextlib import contextmanager

from common import BASE_DIR
import proc_lock

LOCK_PATH = BASE_DIR / "trading.lock"

AlreadyRunning = proc_lock.AlreadyRunning

_lock = proc_lock.ProcLock(LOCK_PATH)

_GUARD_MESSAGE = (
    "이미 다른 매매 실행(자동/수동)이 진행 중이라 겹치지 않도록 이번 실행은 건너뜁니다. "
    "daemon 이 돌고 있는 동안에는 python main.py 를 직접 실행하지 마세요."
)


def try_acquire() -> bool:
    return _lock.try_acquire()


def release():
    _lock.release()


@contextmanager
def guard():
    """with exec_lock.guard(): ... 이미 다른 매매 실행이 진행 중이면 AlreadyRunning."""
    with _lock.guard(_GUARD_MESSAGE):
        yield
