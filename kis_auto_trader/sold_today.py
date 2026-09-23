"""
오늘 이미 매도한 종목 코드를 기록한다 (2026-08-20, "당일 재진입 금지").

replace_blocked_stock() 이 슬롯을 교체할 때, 방금 판 종목이 하락+반등 조건을
다시 만족해서 그대로 재후보로 뽑히는 구멍이 있었다 - 슬롯은 다른 종목으로
넘어갔다고 표시해놓고, 실제로는 그 다음 검색에서 방금 판 종목이 여전히 후보
제외 목록에 없어서 도로 뽑힐 수 있었다. 매도 시점에 여기 기록해두고,
replace_blocked_stock() 이 후보를 고를 때 이 목록도 제외 대상에 넣는다.

main.py 가 매 회차 새 프로세스로 실행되므로 파일에 저장해야 회차 사이에
남는다. watch_state.json 과 마찬가지로 저녁스크리닝이 감시목록을 통째로
새로 짤 때 전부 초기화한다 - 오늘 판 기록이 내일까지 남으면 안 되므로.
"""
import json

from common import BASE_DIR

SOLD_TODAY_PATH = BASE_DIR / "sold_today.json"


def _load() -> list:
    if SOLD_TODAY_PATH.exists():
        try:
            return json.loads(SOLD_TODAY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(data: list) -> None:
    SOLD_TODAY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def mark_sold(code: str) -> None:
    """이 종목을 오늘 판 것으로 기록한다 (이미 있으면 중복 추가 안 함)."""
    data = _load()
    if code not in data:
        data.append(code)
        _save(data)


def all_sold_today() -> set:
    return set(_load())


def clear_all() -> None:
    """저녁스크리닝으로 감시목록을 통째로 새로 짤 때 오늘 판 기록을 전부 지운다."""
    _save([])
