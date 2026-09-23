"""
관찰(데이터 수집) 실행 진입점.

  python main.py

하루 여러 번 실행하는 걸 전제로 만들었습니다 (보통 daemon.py가 반복 실행).

(2026-09-04 대개편) 실전투자를 완전히 접으면서, 예전에 여기 있던 "REAL을
입력해야 실행되는" 확인 절차를 없앴다 - api_client.py에 실제 주문을 낼 수
있는 함수 자체가 더 이상 없어서, 그 확인이 막아주던 위험(실수로 실전투자가
시작되는 것) 자체가 사라졌다. 이제 이 스크립트는 trader.run_once()(순수
관찰/기록)를 실행하는 것뿐이다.
"""
import sys
from datetime import datetime

import exec_lock
from common import LOG_DIR, load_config
from trader import run_once

RUN_LOG_PATH = LOG_DIR / "run_history.log"

# 2026-07-30 11시경, 원인 불명(추정: 네트워크/DNS 단계에서 requests 의 timeout=10 이
# 안 먹히는 상황)으로 프로세스가 몇 시간째 멈춰서 그 뒤로 10분 간격 예약 실행이 전부
# 막혔던 사고가 있었다. 어떤 이유로든 다시는 오래 멈추지 않도록, 워치독은 그대로
# 유지한다 (평소 실행은 몇십 초면 끝남).
import os
import threading

WATCHDOG_TIMEOUT_SEC = 120
_watchdog: threading.Timer | None = None


def _start_watchdog():
    global _watchdog
    _watchdog = threading.Timer(WATCHDOG_TIMEOUT_SEC, _watchdog_kill)
    _watchdog.daemon = True
    _watchdog.start()


def _cancel_watchdog():
    if _watchdog is not None:
        _watchdog.cancel()


def _watchdog_kill():
    try:
        with open(RUN_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.now().isoformat(timespec='seconds')}] "
                f"실패 - 워치독 강제종료 ({WATCHDOG_TIMEOUT_SEC}초 초과, 원인 불명 행 추정)\n"
            )
    except Exception:
        pass
    os._exit(1)


def _log_run(message: str):
    """예약 실행처럼 화면을 볼 수 없는 상황에서도 흔적이 남도록 파일에 직접 기록한다."""
    try:
        with open(RUN_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass


def main():
    _log_run("main.py 시작")

    try:
        cfg = load_config()
    except Exception as e:
        msg = f"설정을 불러오지 못했습니다: {e}"
        print(f"[!] {msg}")
        _log_run(f"실패 - {msg}")
        sys.exit(1)

    try:
        with exec_lock.guard():
            run_once(cfg)
    except exec_lock.AlreadyRunning as e:
        msg = str(e)
        print(f"[!] {msg}")
        _log_run(f"건너뜀 - {msg}")
        sys.exit(0)
    except Exception as e:
        msg = f"실행 중 오류: {type(e).__name__}: {e}"
        print(f"[!] {msg}")
        _log_run(f"실패 - {msg}")
        sys.exit(1)

    _log_run("정상 종료")


if __name__ == "__main__":
    _start_watchdog()
    try:
        main()
    finally:
        _cancel_watchdog()
