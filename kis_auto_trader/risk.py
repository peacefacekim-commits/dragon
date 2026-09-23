"""
자금 배분과 손절/익절 판단. 전략 신호보다 이 모듈의 판단이 우선한다.
"""
import csv
import math
from datetime import datetime

from common import Config, TRADE_LOG_PATH, WatchItem


def total_realized_pnl() -> float:
    """지금까지 실현손익 합계 (매도 기록의 realized_pnl 합). 기록 없으면 0."""
    if not TRADE_LOG_PATH.exists():
        return 0.0
    total = 0.0
    with open(TRADE_LOG_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            pnl = row.get("realized_pnl")
            if pnl:
                try:
                    total += float(pnl)
                except ValueError:
                    pass
    return total


def daily_realized_pnl(today: datetime | None = None) -> float:
    """오늘(today 안 주면 실제 오늘) 실현손익 합계. 기록 없으면 0.
    (2026-08-26 추가, 계좌 전체 손실 한도용)"""
    if not TRADE_LOG_PATH.exists():
        return 0.0
    date_str = (today or datetime.now()).strftime("%Y-%m-%d")
    total = 0.0
    with open(TRADE_LOG_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("timestamp", "")[:10] != date_str:
                continue
            pnl = row.get("realized_pnl")
            if pnl:
                try:
                    total += float(pnl)
                except ValueError:
                    pass
    return total


def account_total_value(available_cash: float, holdings: dict) -> float:
    """실제 계좌 총액(현금+보유종목 매입원가) 근사치. (2026-08-26 추가)
    calc_buy_quantity() 의 포지션 크기 계산과 daily_loss_limit_breached() 의
    손실 한도 계산이 "계좌 총액"이라는 같은 개념을 서로 다르게 계산하면
    또 어긋날 수 있어서(오늘 이미 realized_pnl 계산식이 두 곳에서 따로
    놀아서 문제가 됐었다), 하나로 합쳤다. 보유종목 가치는 현재 시세 대신
    매입원가(avg_price)로 근사한다 - 종목마다 현재가를 추가 조회할 필요
    없이 이미 갖고 있는 holdings 정보만으로 계산 가능하다."""
    held_value = sum(h["qty"] * h["avg_price"] for h in holdings.values())
    return max(available_cash, 0.0) + held_value


def daily_loss_limit_breached(
    cfg: Config, total_account_value: float, today: datetime | None = None,
    amount_override: float | None = None,
) -> tuple[bool, float]:
    """오늘 실현손실이 (실제 계좌 총액) 의 daily_loss_limit_pct(%) 를 넘었으면
    (True, 오늘 실현손익) 을 반환한다. 신규 매수만 막고, 보유 종목의 손절/익절
    감시는 계속되게 하는 용도로 쓴다 (2026-08-26 추가).

    2026-08-26에 "얼마나 더 잃어야 전략이 잘못됐다고 판단하냐"는 지적을 받고
    만듦 - 그동안 종목별 손절만 있고, 계좌 전체 차원의 손실 한도가 없어서
    "데이터를 더 모으자"는 명분으로 손실 한도 없이 계속 진행하는 문제가 있었다.

    (2026-08-26, 처음엔 cfg.total_capital(config.yaml 에 적힌 고정 숫자) 기준으로
    짰는데, 계좌 총액이 그 숫자와 계속 달라지니(이미 손실이 나서 실제로는
    total_capital 보다 적음) 그 기준 자체가 부정확했다. 이제 호출하는 쪽
    (trader.py) 이 조회한 실제 계좌 총액(현금+보유종목 매입원가)을 인자로
    받아서, 그때그때 진짜 계좌 크기 기준으로 판단한다 - calc_buy_quantity() 가
    포지션 크기를 계산하는 방식과 동일한 기준.

    daily_loss_limit_pct 가 0 이하면 이 안전장치 자체가 꺼진 것으로 보고
    %기준은 항상 통과시킨다 (하위 호환 - 기존 config.yaml 에는 이 값이 없음).

    (2026-09-03 추가) daily_loss_limit_amount(원) - %기준과 별개로, 오늘
    실현손실이 이 금액을 넘으면도 막는다. 계좌 총액에 비례하는 %기준과 달리
    "오늘은 딱 여기까지만 잃으면 그만 보자"는 절대 금액 기준을 원하는 요청으로
    추가 - stop_loss_pct/stop_loss_amount 가 손절 하나를 %와 금액 두 기준으로
    같이 보는 것과 같은 패턴(둘 중 먼저 걸리는 쪽에서 멈춤). 0 이하면 이쪽도
    꺼진 것으로 본다.

    amount_override 를 주면 cfg.daily_loss_limit_amount 대신 그 값을 금액기준으로
    쓴다 (2026-09-03 추가, "코스닥 마이너스인 날은 만원, 아닌 날은 10만원"처럼
    날마다 다른 금액 한도를 쓰고 싶다는 요청 - 호출하는 쪽(trader.py)이
    effective_daily_loss_limit_amount() 로 오늘 적용할 금액을 미리 정해서 넘긴다.
    None 이면(안 주면) 기존처럼 cfg.daily_loss_limit_amount 를 그대로 쓴다 - 하위 호환."""
    today_pnl = daily_realized_pnl(today)
    hit = False
    if cfg.daily_loss_limit_pct > 0:
        limit = -abs(total_account_value * cfg.daily_loss_limit_pct / 100)
        if today_pnl <= limit:
            hit = True
    amount_limit = cfg.daily_loss_limit_amount if amount_override is None else amount_override
    if not hit and amount_limit > 0:
        if today_pnl <= -abs(amount_limit):
            hit = True
    return hit, today_pnl


def effective_daily_loss_limit_amount(cfg: Config, kosdaq_change_pct: float | None) -> float:
    """오늘 적용할 일일 손실한도 금액(원)을 정한다. (2026-09-03 추가)

    전날 코스닥이 마이너스면(risk.effective_max_positions 와 동일한 판단 기준)
    cfg.daily_loss_limit_amount_kosdaq_negative 를, 아니면 cfg.daily_loss_limit_amount
    를 쓴다. daily_loss_limit_amount_kosdaq_negative 가 0(꺼짐)이면 코스닥 상태와
    무관하게 항상 cfg.daily_loss_limit_amount 하나만 쓴다 - 하위 호환.

    kosdaq_change_pct 를 못 구했으면(None) effective_max_positions 와 동일하게
    fail-open - 평소(cfg.daily_loss_limit_amount) 기준으로 돌려준다."""
    if (
        kosdaq_change_pct is not None
        and kosdaq_change_pct < 0
        and cfg.daily_loss_limit_amount_kosdaq_negative > 0
    ):
        return cfg.daily_loss_limit_amount_kosdaq_negative
    return cfg.daily_loss_limit_amount


def calc_buy_quantity(
    cfg: Config, item: WatchItem, current_price: float,
    available_cash: float | None = None, open_slots: int | None = None,
    holdings: dict | None = None,
) -> int:
    """이 종목에 배정된 예산으로 살 수 있는 주식 수 (내림).

    item.fixed_qty 가 있으면 비율 계산을 아예 무시하고 그 수량 그대로 사려고 한다
    (예: "삼성전자는 항상 딱 1주"). 그래도 실제로 그만큼 살 돈이 없으면 못 사므로
    available_cash 캡은 그대로 적용한다.

    (2026-08-26 변경) holdings 를 주면, "현재 계좌 총액(현금+보유종목 매입원가)을
    max_positions 로 고정 등분"하는 방식을 쓴다. 8/19~8/26 사이에는 available_cash를
    "지금 빈 슬롯 수"로 나눴는데(실현손익 전액 재투자), 슬롯이 채워질수록 남은 빈
    슬롯 하나에 배정되는 돈이 계속 커지는 구조라 포지션이 과도하게 커지고, 그만큼
    한 번 잘못된 판단의 손실 금액도 커졌다(예: 08-20 바이오니아 -42,780원). 실제
    데이터로 확인해보니 이 변경 이후 건당 평균 수익률 자체도 나빠졌다(+0.13%->
    -0.81%). 사용자 요청으로, 슬롯이 몇 개 찼든 상관없이 "계좌 총액 / max_positions"
    로 매번 고정된 예산을 쓰도록 되돌린다 - 포지션 크기가 계좌 상황에 안 흔들리고
    항상 일정하게 유지된다. 보유종목 가치는 현재 시세 대신 매입원가(avg_price)로
    근사한다 - 종목마다 현재가를 추가 조회할 필요 없이 이미 갖고 있는 holdings
    정보만으로 계산 가능하고, 예산 산정 목적으로는 충분한 근사치.

    holdings 가 없으면(예: 잔고 조회 없이 이 함수만 단독 호출하는 경우), 이전
    방식(open_slots 기준, 그마저 없으면 total_capital/invest_ratio 정적 방식)으로
    대체 계산한다."""
    if current_price <= 0:
        return 0

    if item.fixed_qty is not None:
        qty = item.fixed_qty
        if available_cash is not None:
            qty = min(qty, math.floor(available_cash / current_price))
        return qty

    if available_cash is not None and holdings is not None:
        budget = account_total_value(available_cash, holdings) / max(cfg.max_positions, 1)
        budget = min(budget, available_cash)
    elif available_cash is not None and open_slots is not None:
        budget = max(available_cash, 0.0) / max(open_slots, 1)
    else:
        budget = cfg.total_capital * item.invest_ratio
        if available_cash is not None:
            budget = min(budget, available_cash)
    return math.floor(budget / current_price)


def check_stop_loss(
    cfg: Config, avg_price: float, current_price: float, qty: int = 0,
    threshold_pct: float | None = None, index_change_pct: float | None = None,
) -> tuple[bool, str]:
    """손절 판단. (손절할지, 사유) 를 돌려준다.

    threshold_pct 를 주면 그 값을 손절 기준으로 쓴다 (시장 상황에 따라 조정된 값).
    index_change_pct 를 주면 상대평가로 판단한다 - 내 종목 수익률에서 같은 기간
    코스피 수익률을 뺀 값이 기준 이하일 때만 손절. 시장이 통째로 빠지는 날
    혼자만 손절당하는 걸 막기 위함.

    (2026-08-20) %기준 OR 금액기준 - 둘 중 먼저 도달하는 쪽에서 손절한다. 익절과
    마찬가지로 슬롯이 커지면 %기준만으론 손실 확정까지 너무 오래 걸릴 수 있어서
    추가함. 손절은 수수료를 감안하지 않는다는 기존 방침(net_change_pct 를 안 씀)을
    그대로 따라, 금액기준도 수수료 차감 없이 원화 손실액만 본다. 상대평가(코스피
    대비) 모드여도 금액기준은 그대로 적용된다 - 절대 손실액 안전장치라서.
    cfg.stop_loss_amount 가 0이면 금액 기준은 꺼진 것으로 본다."""
    if avg_price <= 0:
        return False, ""

    threshold = cfg.stop_loss_pct if threshold_pct is None else threshold_pct
    change_pct = (current_price - avg_price) / avg_price * 100

    if cfg.use_relative_stop_loss and index_change_pct is not None:
        relative = change_pct - index_change_pct
        hit = relative <= threshold
        reason = (
            f"종목 {change_pct:+.1f}% - 코스피 {index_change_pct:+.1f}% "
            f"= 상대 {relative:+.1f}% (기준 {threshold:+.1f}%)"
        )
    else:
        hit = change_pct <= threshold
        reason = f"종목 {change_pct:+.1f}% (기준 {threshold:+.1f}%)"

    if not hit and cfg.stop_loss_amount > 0 and qty > 0:
        loss_amount = (current_price - avg_price) * qty
        if loss_amount <= -cfg.stop_loss_amount:
            hit = True
            reason = f"종목당 손실액 {loss_amount:,.0f}원 (기준 -{cfg.stop_loss_amount:,.0f}원)"

    return hit, reason


def net_change_pct(cfg: Config, avg_price: float, current_price: float) -> float:
    """매수 수수료, 매도 수수료, 매도 시 증권거래세를 다 뺀 뒤의 순손익률(%).
    손절 판단에는 안 쓰고(손실을 막는 목적이라 수수료 때문에 매도를 늦추면 안 됨),
    익절 판단에만 쓴다."""
    buy_cost = avg_price * (1 + cfg.buy_fee_pct / 100)
    sell_proceeds = current_price * (1 - cfg.sell_fee_pct / 100 - cfg.sell_tax_pct / 100)
    return (sell_proceeds - buy_cost) / buy_cost * 100


def net_realized_pnl(cfg: Config, avg_price: float, sell_price: float, qty: int) -> float:
    """실제 거래 기록에 남길 순손익(원) - 매수 수수료, 매도 수수료, 매도 시 증권거래세를
    전부 뺀 값. (2026-08-26 추가) 익절 판단(check_take_profit)은 처음부터
    net_change_pct()로 수수료를 반영해서 정확했는데, 정작 trader.py가 거래 기록에
    남기는 realized_pnl 은 (매도가-매수가)*수량 만 계산한 세전 근사치였다. 판단은
    맞게 하고 기록은 다르게 남긴 불일치 - 실제 계좌 손익과 로그가 계속 어긋나서
    (예: 08-20 로그상 +4,380원이었지만 수수료 반영하면 실제로는 +1,750원 수준)
    발견됨. 이제 판단과 기록이 같은 계산식을 쓴다."""
    buy_cost = avg_price * (1 + cfg.buy_fee_pct / 100)
    sell_proceeds = sell_price * (1 - cfg.sell_fee_pct / 100 - cfg.sell_tax_pct / 100)
    return (sell_proceeds - buy_cost) * qty


def check_take_profit(
    cfg: Config, avg_price: float, current_price: float, qty: int = 0,
    threshold_pct: float | None = None,
) -> bool:
    """익절 라인에 닿았으면 True. avg_price 는 평균 매수 단가.
    수수료·세금을 뺀 순손익률 기준이라, 겉보기 상승률이 기준을 넘어도
    수수료를 빼고 나면 미달일 경우 아직 팔지 않는다.
    threshold_pct 를 주면 그 값을 익절 기준으로 쓴다 (시장 상황에 따라 조정된 값).

    (2026-08-11) %기준 OR 금액기준 - 둘 중 먼저 도달하는 쪽에서 익절한다.
    슬롯마다 실제 매수 금액이 달라서, %만 쓰면 큰 슬롯은 매수 후 오래 걸려야
    도달하는 이익 금액이 작은 슬롯의 %기준 이익 금액보다 커지는 불균형이 생긴다.
    cfg.take_profit_amount(원, 종목당 순이익)로 그 하한을 잡아준다 - 0이면
    (기본값) 금액 기준은 꺼진 것으로 보고 %기준만 그대로 적용한다."""
    threshold = cfg.take_profit_pct if threshold_pct is None else threshold_pct
    if avg_price <= 0:
        return False

    if threshold > 0 and net_change_pct(cfg, avg_price, current_price) >= threshold:
        return True

    if cfg.take_profit_amount > 0 and qty > 0:
        buy_cost = avg_price * (1 + cfg.buy_fee_pct / 100)
        sell_proceeds = current_price * (1 - cfg.sell_fee_pct / 100 - cfg.sell_tax_pct / 100)
        net_profit_amount = (sell_proceeds - buy_cost) * qty
        if net_profit_amount >= cfg.take_profit_amount:
            return True

    return False


def can_open_new_position(cfg: Config, current_holding_count: int, max_positions: int | None = None) -> bool:
    """max_positions 를 안 주면 cfg.max_positions 그대로 쓴다 (기존 동작 그대로).
    (2026-08-28) 코스피-코스닥 격차에 따른 슬롯 수 실험(effective_max_positions)을
    호출하는 쪽에서 넘길 수 있도록 인자를 추가했다."""
    limit = max_positions if max_positions is not None else cfg.max_positions
    return current_holding_count < limit


# (2026-08-28 추가, 실험 단계) 코스닥이 마이너스인 날엔 슬롯을 이 개수로
# 제한한다. 처음엔 코스피-코스닥 격차(양수/음수) 기준이었다가, 2x2(코스피×코스닥
# 부호) 4분면으로 나눠보니 승률 상위 2개(코스피-/코스닥+ 70.0%, 코스피+/코스닥+
# 57.9%)가 전부 "코스닥+", 하위 2개(코스피-/코스닥- 33.3%, 코스피+/코스닥- 0%)가
# 전부 "코스닥-"였다 - 즉 코스피 부호는 승패에 큰 영향이 없고 코스닥 부호가
# 핵심이라는 뜻이라, 코스닥 부호 단독 기준으로 단순화했다("코스피·코스닥 둘 다
# 좋은 날도 투자해보고 싶다"는 요청 반영 - 격차 기준이었으면 코스피가 코스닥을
# 크게 앞지르는 날(예: 8/20, 격차 +3.9%p)엔 둘 다 플러스여도 슬롯이 제한됐음).
#
# (2026-09-03) 2에서 1로 낮춤. analyze_daily_conditions.py로 7/29~9/3 실제
# 거래일 24일을 다시 확인해보니(이상치 하루 제거, 중앙값 기준) 전날 코스닥
# 마이너스인 날의 성적이 여전히 나빴다(중앙값 기준으로도 방향 유지) - 근거가
# 이전보다 탄탄해졌다고 판단해 더 보수적으로 조정. 완전히 0으로(아예 매수 안
# 함) 하지 않고 1로 둔 건, 실전 데이터를 계속 쌓아서 이 판단 자체를 검증하고
# 싶다는 요청 때문 - 0으로 막으면 그 조건에서의 데이터가 더는 안 쌓인다.
KOSDAQ_NEGATIVE_SLOT_CAP = 1


def effective_max_positions(cfg: Config, kosdaq_change_pct: float | None) -> int:
    """전날 코스닥 등락률(market.kosdaq_change_pct)로 열 수 있는 최대 슬롯 수를
    정한다. (2026-08-28 추가, 2026-08-31 기준을 "오늘 값"에서 "전날 마감
    확정값"으로 변경 - market.kosdaq_change_pct 문서 참고. 전날 값은 하루 종일
    안 바뀌므로, 예전에 있던 "장 시작 시점에 한 번만 고정"하는 캐시 장치는
    더 이상 필요 없어져서 없앴다 - 매 회차 이 함수를 다시 불러도 항상 같은
    값이 나온다.)

    코스닥이 마이너스면 슬롯을 KOSDAQ_NEGATIVE_SLOT_CAP개로 제한한다. 0 이상이면
    평소(cfg.max_positions) 그대로 - 8/4~8/28 데이터에서 코스닥 플러스인 날의
    승률이 뚜렷이 좋았다(2x2 분석 참고).

    kosdaq_change_pct 를 못 구했으면(None, 지수 조회 실패 등) 안전하게 평소 그대로
    돌려준다 - 판단 불가 상황에서 임의로 제한하면 안 되므로 fail-open."""
    if kosdaq_change_pct is None:
        return cfg.max_positions
    if kosdaq_change_pct < 0:
        return min(KOSDAQ_NEGATIVE_SLOT_CAP, cfg.max_positions)
    return cfg.max_positions
