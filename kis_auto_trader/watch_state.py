"""
장중 "지켜보는 중"인 슬롯이 몇 회차째 매수 조건을 못 채웠는지 기록한다 (2026-08-19,
프로젝트A). 6회차(10분 간격이면 약 1시간) 동안 계속 hold면 그 종목을 포기하고
다른 후보로 교체한다 - 슬롯이 한 종목에 하루 종일 묶여있는 걸 막기 위함.

main.py 가 매 회차 새 프로세스로 실행되므로, 회차 사이에 값을 유지하려면 파일에
저장해야 한다. 저녁스크리닝(evening_screen.py)이 감시목록을 통째로 새로 짤 때마다
전부 초기화한다 - 어제 카운트가 오늘 남아있는 종목에 잘못 이어지면 안 되므로.
"""
import json

from common import BASE_DIR

WATCH_STATE_PATH = BASE_DIR / "watch_state.json"


def _load() -> dict:
    if WATCH_STATE_PATH.exists():
        try:
            return json.loads(WATCH_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    WATCH_STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def increment(code: str) -> int:
    """이 종목을 관망(hold)한 채로 확인한 회차 수를 1 늘리고, 늘어난 값을 돌려준다."""
    data = _load()
    data[code] = data.get(code, 0) + 1
    _save(data)
    return data[code]


def reset(code: str) -> None:
    """이 종목의 관망 카운터를 지운다 (매수됐거나, 다른 종목으로 교체돼 카운트를
    새로 시작해야 할 때)."""
    data = _load()
    if code in data:
        del data[code]
        _save(data)


def clear_all() -> None:
    """저녁스크리닝으로 감시목록을 통째로 새로 짤 때 이전 카운터를 전부 지운다."""
    _save({})
