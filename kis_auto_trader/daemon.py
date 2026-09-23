"""
장 시작부터 마감까지 계속 살아있으면서, 스스로 일정 간격마다 관찰 회차를 실행한다.

(2026-09-04 대개편) 실전투자를 완전히 접고 순수 데이터 수집 전용으로 바뀌면서,
전량 정리(liquidate.py)·저녁 자동 종목 선정(evening_screen.py)·사토시룰 빠른
매도감시(watch_positions.py)를 전부 없앴다 - 셋 다 "실제/가상 포지션을 들고
있다가 정리한다"는 전제였는데, 이제 포지션 자체가 없다(매수/매도 판단이 없는
순수 관찰이므로). 감시목록은 config.yaml에 적힌 대로 하루 종일 고정이다.

기존에는 Windows 작업 스케줄러가 하루 여러 번 파이썬을 새로 띄우는 구조였는데,
그 방식으로 실행이 통째로 누락되는 일이 있었다. 원인을 특정하지 못해서, 실패
지점을 줄이는 쪽으로 구조를 바꿨다. 스케줄러는 아침에 이 파일을 한 번만
띄우고, 이후 반복은 이 프로그램이 직접 관리한다.

각 회차는 별도 프로세스(main.py)로 실행한다. 그래야 하나가 멈추거나 죽어도
이 프로그램 자체는 멀쩡히 살아남아 다음 회차를 이어갈 수 있다.

  python daemon.py            # 기본 설정(10분 간격)으로 실행
  python daemon.py --interval 5   # 5분 간격으로 실행
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

import proc_lock
from common import BASE_DIR, LOG_DIR

RUN_LOG_PATH = LOG_DIR / "run_history.log"
RUN_CONSOLE_LOG_PATH = LOG_DIR / "run_console.log"
MAIN_SCRIPT = BASE_DIR / "main.py"
# (2026-09-13 추가) 하루 1회, 장 마감 뒤에 도는 일봉 패널 수집 - collect_daily.py 참고.
COLLECT_SCRIPT = BASE_DIR / "collect_daily.py"
UNIVERSE_SCRIPT = BASE_DIR / "universe.py"
LOCK_PATH = BASE_DIR / "daemon.lock"
_lock = proc_lock.ProcLock(LOCK_PATH)

MARKET_OPEN = (9, 5)          # 09:05 부터 관찰 회차 시작
MARKET_CLOSE = (15, 30)       # 15:30 장마감, 관찰 종료

CYCLE_TIMEOUT_SEC = 180        # 회차 타임아웃
# 패널 수집은 처음 한 번이 오래 걸린다 (종목 200개 x 몇 년치를 통째로 받으므로
# 20~30분). 관찰 회차와 같은 3분을 주면 첫날 수집이 매번 중간에 잘린다.
COLLECT_TIMEOUT_SEC = 3600


def log(message: str):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {message}"
    print(line, flush=True)
    try:
        with open(RUN_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _append_console_log(label: str, stdout: str, stderr: str, returncode) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    lines = [f"[{ts}] === {label} (종료코드 {returncode}) ==="]
    if stdout:
        lines.append(stdout.rstrip())
    if stderr:
        lines.append("--- stderr ---")
        lines.append(stderr.rstrip())
    lines.append("")
    try:
        with open(RUN_CONSOLE_LOG_PATH, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass


def _at(now: datetime, hm: tuple[int, int]) -> datetime:
    return now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)


def _run_script(script_path, timeout_sec: int, label: str, args: list[str] | None = None):
    """스크립트를 별도 프로세스로 돌린다. 멈추거나 죽어도 이 프로세스(daemon)는 안 죽는다."""
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), *(args or [])],
            cwd=str(BASE_DIR),
            timeout=timeout_sec,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
        )
        _append_console_log(label, proc.stdout, proc.stderr, proc.returncode)
        if proc.returncode != 0:
            log(f"{label} 실패 (종료코드 {proc.returncode}) - {(proc.stderr or '').strip()[:200]}")
    except subprocess.TimeoutExpired as e:
        _append_console_log(label, e.stdout or "", e.stderr or "", f"TIMEOUT>{timeout_sec}s")
        log(f"{label} 강제종료 ({timeout_sec}초 초과)")
    except Exception as e:
        log(f"{label} 실행 중 예외: {type(e).__name__}: {e}")


def run_one_cycle():
    _run_script(MAIN_SCRIPT, CYCLE_TIMEOUT_SEC, "관찰 회차")


def krx_credentials_missing() -> bool:
    """KRX 계정이 설정돼 있지 않으면 True.

    설정이 없으면 fetch_krx_history.py 는 안내문만 찍고 실패로 끝난다.
    그걸 매일 돌리면 실패 알림이 매일 한 통씩 간다. 알림을 보내야 할
    진짜 고장과 "아직 계정을 안 넣었다"는 구별해야 하므로 미리 걸러서
    조용히 건너뛴다.
    """
    return not (os.getenv("KRX_ID") and os.getenv("KRX_PW"))


# (2026-09-19 추가) 마감 뒤 수집 순서. 순서가 중요하다.
#
# market_indicators.compute_all() 이 us_align 으로 미국 데이터를 읽고
# krx_panel 을 읽어서 그날 지표 행을 만든다. 그래서 미국/한국 데이터를
# 먼저 받아야 그날 행이 최신 값으로 계산된다. 거꾸로 돌리면 어제 미국
# 값으로 계산된 행이 남는다 (다음날 다시 돌 때 덮어쓰이긴 하지만 그날
# 하루는 틀린 값이다).
#
# KRX 갱신을 여기 넣는 이유: 전략과 모든 분석이 읽는 건 krx_panel 인데
# 그걸 전진시키는 단계가 어디에도 없어서 20260915 에서 멈춰 있었다.
# collect_daily.py 가 채우는 panel_* 은 API 유니버스(136종목)로 만든
# 다른 파일이다. 둘을 헷갈리면 "매일 수집하는데 왜 안 늘지" 가 된다.
#
# 한 단계가 실패해도 _run_script 가 잡아서 다음 단계로 넘어간다.
# 미국 데이터를 못 받았다고 한국 일봉까지 못 받으면 안 되기 때문이다.
DAILY_STEPS = (
    # (2026-09-21) 10분봉을 맨 앞에 둔다. KIS 당일분봉 API 는 **오늘 것만**
    # 주므로 소급이 안 된다. 하루 빠뜨리면 그날은 영구히 없다. 뒤 단계가
    # 오래 걸리거나 터져도 이건 먼저 끝나 있어야 한다.
    # (나머지 단계의 데이터는 나중에 소급해서 채울 수 있다.)
    ("10분봉 수집", "fetch_intraday.py", (), 1800),
    ("미국 지수 수집", "fetch_us_market.py", (), 1800),
    ("미국 선물 수집", "fetch_us_futures.py", (), 1800),
    ("KRX 일봉 갱신", "fetch_krx_history.py", ("--update",), 10800),
    ("일일 패널 수집", "collect_daily.py", (), COLLECT_TIMEOUT_SEC),
)


def run_daily_collection():
    """장 마감 뒤 하루 1회 데이터 수집 (2026-09-13 추가, 2026-09-19 확장).

    장중 관찰 회차와 달리 하루에 딱 한 번만 돌면 되는 일이라, 관찰 루프가
    끝난 뒤에 이어서 실행한다. 별도 예약 작업을 하나 더 만들지 않아도 되고,
    관찰 루프가 어떻게 끝났든(정상 종료/늦게 시작) 항상 이 단계는 지나간다.
    """
    for label, name, args, timeout in DAILY_STEPS:
        if name == "fetch_krx_history.py" and krx_credentials_missing():
            log(f"{label} 건너뜀 - KRX_ID/KRX_PW 가 설정돼 있지 않습니다 "
                f"(설정하면 krx_panel 이 매일 자동으로 갱신됩니다)")
            continue
        # _run_script 안에도 예외 처리가 있지만 여기서 한 번 더 감싼다.
        # 한 단계가 어떤 이유로든 예외를 던지면 그 뒤 단계가 통째로
        # 안 돌아서 그날 기록이 빈다. 수집이 이 함수의 목적이므로
        # 격리를 남의 구현에 맡기지 않고 여기서 보장한다.
        try:
            _run_script(BASE_DIR / name, timeout, label, args=list(args))
        except Exception as e:
            log(f"{label} 에서 예외 - 다음 단계로 넘어갑니다: {type(e).__name__}: {e}")


def run_universe_topup():
    """고정 유니버스가 목표 종목 수에 못 미치면 채운다 (2026-09-13 추가).

    장중에 한다. 유니버스는 KIS 순위 API로 채우는데 그건 장이 열려 있을 때
    값을 주므로, 마감 뒤에 도는 collect_daily.py 에만 맡기면 유니버스가 영영
    안 채워질 수 있다. 목표 개수를 다 채운 뒤에는 아무 일도 하지 않는다.
    """
    _run_script(UNIVERSE_SCRIPT, CYCLE_TIMEOUT_SEC, "유니버스 채우기", args=["--build"])


def main():
    parser = argparse.ArgumentParser(description="장중 상주하며 주기적으로 관찰 회차 실행")
    parser.add_argument("--interval", type=int, default=10, help="실행 간격(분), 기본 %(default)s분")
    args = parser.parse_args()
    interval = timedelta(minutes=args.interval)

    if not _lock.try_acquire():
        log("이미 다른 daemon이 실행 중이라 중복 실행하지 않고 종료합니다.")
        return

    try:
        now = datetime.now()
        if now.weekday() >= 5:
            log("주말이라 실행하지 않습니다.")
            return

        open_at = _at(now, MARKET_OPEN)
        close_at = _at(now, MARKET_CLOSE)

        # (2026-09-13) 장마감 뒤에 시작됐어도 그냥 끝내지 않는다. 장중 관찰은
        # 못 하지만 일봉 패널 수집은 오히려 마감 뒤가 제 시간이라, 그것만
        # 하고 끝낸다 - 예전에는 이 경우 그날 데이터가 통째로 비었다.
        if now >= close_at:
            log("이미 장마감 시각이 지나, 장중 관찰은 건너뛰고 일봉 패널 수집만 실행합니다.")
            run_daily_collection()
            return

        log(f"daemon 시작 (간격 {args.interval}분, {open_at:%H:%M} 관찰 시작 -> {close_at:%H:%M} 장마감)")

        if now < open_at:
            wait = (open_at - now).total_seconds()
            log(f"장 시작까지 {wait / 60:.0f}분 대기")
            time.sleep(wait)

        # 유니버스 채우기는 장중에 딱 한 번. 순위 API가 장중에 값을 주기 때문이다.
        run_universe_topup()

        next_run = datetime.now()
        while datetime.now() < close_at:
            log("회차 시작 시도")
            run_one_cycle()

            # 다음 실행 시각을 계산한다. 노트북이 잠들었다 깨어나서 여러 회차를
            # 놓쳤더라도, 지난 회차를 몰아서 실행하지 않고 다음 정시로 맞춘다.
            next_run += interval
            now = datetime.now()
            while next_run <= now:
                next_run += interval

            if next_run >= close_at:
                break

            sleep_sec = (next_run - now).total_seconds()
            time.sleep(max(sleep_sec, 1))

        log("당일 관찰 종료 - 일봉 패널 수집을 시작합니다.")
        run_daily_collection()
        log("daemon 종료")
    finally:
        _lock.release()


if __name__ == "__main__":
    main()
