"""
코스닥 마이너스로 줄어든 슬롯 대신, 그 자리를 "가상 매수"로 기록해서 실제
돈 없이 데이터만 쌓는다. (2026-09-03 추가, 사용자 요청: "코스닥 지수가
마이너스인 날은 슬롯 하나만 열고 나머지 4개의 슬롯은 가상으로 투자를
했으면 하는데" - 실제 슬롯은 risk.KOSDAQ_NEGATIVE_SLOT_CAP(=1)로 줄이되,
그래서 못 연 나머지 슬롯도 그냥 버리지 말고 "실제로 열었으면 어땠을까"
데이터를 계속 쌓기 위함.)

실제 잔고/주문 함수는 이 모듈에서 절대 부르지 않는다 - 순수하게 로컬 JSON
상태 + 로그 CSV로만 동작한다. 손절/익절 판단은 risk.py의 실제 매매와 완전히
같은 함수(check_stop_loss/check_take_profit/net_realized_pnl)를 그대로
재사용해서, "가상으로 투자했으면 어떻게 됐을까"가 실제 규칙과 어긋나지
않게 한다.

(2026-09-04) 실전투자를 완전히 접으면서 api_client.py의 실제 주문 함수
자체가 삭제됐고, dip_buy 신호(strategy.py)도 삭제됐다.

(2026-09-05 확장) "여러 투자 방식을 실제로 했다면 어떤 데이터가 나올지
보고 싶다"는 요청으로, 이제 하나의 가상매매 장부가 아니라 전략(factors.py의
모멘텀/추세추종/저변동성 등)별로 독립된 장부를 동시에 관리한다. 포지션
키를 "전략이름:종목코드"로 만들어서 같은 종목을 여러 전략이 동시에(서로
모른 채) 각자 가상매수할 수 있게 한다 - 실제로는 한 JSON 파일 안에 전략별
서브키가 있는 게 아니라, 최상위 키 자체가 복합키다(구현이 단순해서).

(2026-09-05 도입 당시 버그, 2026-09-12 발견/수정) 처음엔 FIELDNAMES에
"strategy"를 opened_at/closed_at 바로 뒤(중간)에 넣었는데, virtual_trades.csv가
이미 9/4에 만들어진 옛날(전략 구분 이전, 9컬럼) 파일이라 _log_close()가
"파일이 이미 있으니 헤더는 새로 안 씀"으로 판단해서 헤더 줄은 9컬럼 그대로
남고 실제 값만 10컬럼으로 쌓였다 - 그 결과 strategy 값이 code로,
code가 name으로 밀려 읽히는 식으로 실제 저장된 데이터가 며칠치 다 잘못
정렬됐었다(9/7~9/9). 로그 파일에 새 컬럼을 추가할 땐 반드시 맨 끝에
붙여야 한다는 걸(기존 INVESTOR_LOG_FIELDS 확장 때도 그렇게 했던 것과
같은 이유) 다시 배워서, FIELDNAMES 순서를 맨 끝으로 옮기고 기존 파일도
직접 다시 정렬해 복구했다.
"""
import csv
import json
from datetime import datetime

from common import BASE_DIR, VIRTUAL_TRADE_LOG_PATH, Config

import risk

STATE_PATH = BASE_DIR / "virtual_positions.json"

FIELDNAMES = [
    "opened_at", "closed_at", "code", "name", "qty",
    "avg_price", "close_price", "note", "realized_pnl", "strategy",
]


def _key(strategy: str, code: str) -> str:
    return f"{strategy}:{code}"


def has_position(state: dict, strategy: str, code: str) -> bool:
    return _key(strategy, code) in state


def count_open(state: dict, strategy: str) -> int:
    prefix = f"{strategy}:"
    return sum(1 for k in state if k.startswith(prefix))


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def open_virtual(
    state: dict, code: str, name: str, price: float, qty: int,
    strategy: str = "default", index_at_buy: float | None = None,
) -> None:
    """state 를 직접 수정한다 (호출하는 쪽이 이후 save_state 로 저장).
    (2026-09-05) strategy 별로 독립된 포지션을 가지므로, 같은 code 라도
    strategy 가 다르면 서로 다른 포지션으로 취급한다."""
    state[_key(strategy, code)] = {
        "strategy": strategy,
        "code": code,
        "name": name,
        "qty": qty,
        "avg_price": price,
        "index_at_buy": index_at_buy,
        "opened_at": datetime.now().isoformat(timespec="seconds"),
    }


def _check_header_matches() -> None:
    """(2026-09-12 추가) 파일이 이미 있는데 그 헤더가 지금 코드의 FIELDNAMES와
    다르면, 예전에 실제로 겪은 사고(헤더는 옛날 9컬럼인데 실제 값은 새
    10컬럼으로 며칠치 밀려 쌓인 것)가 조용히 반복될 수 있다. 매번 파일을
    통째로 다시 읽는 비용을 감수하더라도(가상매매 청산 빈도가 낮아 부담
    적음), 헤더가 어긋난 그 순간 바로 눈에 띄게 경고한다 - 며칠 뒤에야
    데이터를 들여다보다 발견하는 것보다 훨씬 낫다."""
    if not VIRTUAL_TRADE_LOG_PATH.exists():
        return
    try:
        with open(VIRTUAL_TRADE_LOG_PATH, encoding="utf-8-sig") as f:
            header = next(csv.reader(f), None)
    except Exception:
        return
    if header is not None and header != FIELDNAMES:
        print(
            f"[!!!] virtual_trades.csv 헤더({header})가 지금 코드의 컬럼 순서"
            f"({FIELDNAMES})와 다릅니다 - 값이 밀려 잘못 기록될 수 있으니 "
            f"바로 확인/마이그레이션이 필요합니다."
        )


def _log_close(
    opened_at: str, strategy: str, code: str, name: str, qty: int, avg_price: float,
    close_price: float, note: str, realized_pnl: float,
) -> None:
    _check_header_matches()
    is_new = not VIRTUAL_TRADE_LOG_PATH.exists()
    with open(VIRTUAL_TRADE_LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if is_new:
            w.writeheader()
        w.writerow({
            "opened_at": opened_at,
            "closed_at": datetime.now().isoformat(timespec="seconds"),
            "strategy": strategy,
            "code": code,
            "name": name,
            "qty": qty,
            "avg_price": f"{avg_price:.0f}",
            "close_price": f"{close_price:.0f}",
            "note": note,
            "realized_pnl": f"{realized_pnl:.0f}",
        })


def check_and_close(
    cfg: Config, state: dict, code: str, current_price: float,
    stop_loss_pct: float, take_profit_pct: float,
    strategy: str = "default", index_change_pct: float | None = None,
) -> bool:
    """가상 포지션의 손절/익절 조건을 실제 매매와 같은 기준(risk.check_stop_loss /
    risk.check_take_profit)으로 확인한다. 걸렸으면 state 에서 지우고
    virtual_trades.csv 에 기록한 뒤 True 를 돌려준다 (state 저장은 호출하는
    쪽 책임). 해당 (strategy, code) 조합이 가상 포지션이 아니면 False.

    (2026-09-05) market_state(시장국면별 조정 기준) 의존을 없앴다 - 여러
    전략을 동시에 공정하게 비교하려면 전략마다 같은 손절/익절 기준을 써야
    하므로, cfg.stop_loss_pct/take_profit_pct 를 호출하는 쪽이 그대로 넘긴다."""
    key = _key(strategy, code)
    pos = state.get(key)
    if not pos:
        return False

    hit, detail = risk.check_stop_loss(
        cfg, pos["avg_price"], current_price, qty=pos["qty"],
        threshold_pct=stop_loss_pct, index_change_pct=index_change_pct,
    )
    note = None
    if hit:
        note = f"가상 손절: {detail}"
    elif risk.check_take_profit(
        cfg, pos["avg_price"], current_price, qty=pos["qty"],
        threshold_pct=take_profit_pct,
    ):
        note = "가상 익절"

    if note is None:
        return False

    realized_pnl = risk.net_realized_pnl(cfg, pos["avg_price"], current_price, pos["qty"])
    _log_close(
        pos["opened_at"], strategy, code, pos["name"], pos["qty"], pos["avg_price"],
        current_price, note, realized_pnl,
    )
    print(f"  -> [가상:{strategy}] {note} (가상손익 {realized_pnl:+,.0f}원, 실제 돈 아님)")
    del state[key]
    return True
