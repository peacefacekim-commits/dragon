"""
매수 시점의 코스피 지수를 종목별로 기록해둔다.

상대평가 손절("코스피보다 몇 %p 더 나쁜가")을 계산하려면, 그 종목을 살 때
코스피가 몇이었는지 알아야 한다. 증권사 잔고 조회는 평균단가만 주고 그때의
지수는 알려주지 않으므로 여기서 따로 관리한다.

이 프로그램 밖에서 산 종목(앱에서 직접 매수 등)은 기록이 없는데, 그 경우엔
상대평가를 못 하니 일반(절대) 손절 기준으로 넘어간다.
"""
import json

from common import BASE_DIR

STATE_PATH = BASE_DIR / "position_state.json"


def _load() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_buy(code: str, index_value: float) -> None:
    data = _load()
    data[code] = {"index_at_buy": index_value}
    _save(data)


def clear(code: str) -> None:
    data = _load()
    if code in data:
        del data[code]
        _save(data)


def get_index_at_buy(code: str) -> float | None:
    entry = _load().get(code)
    return entry.get("index_at_buy") if entry else None
