"""
코스피 지수를 보고 시장 국면을 판단해서, 익절/손절 기준을 유동적으로 조정한다.

두 가지를 한다.
  1) 추세 지속일수 반영
     - 코스피 종가가 20일 이동평균 위에 있으면 상승장, 아래면 하락장으로 본다.
     - 그 상태가 며칠째 이어지고 있는지 세서, 지속일수만큼 기준을 조금씩 옮긴다.
       상승장이 길어지면: 익절선을 높여 더 오래 들고 가고, 손절선도 여유 있게.
       하락장이 길어지면: 익절선을 낮춰 빨리 확정하고, 손절선은 빡빡하게.
  2) 상대평가 (risk.py 에서 사용)
     - 손절을 "내 종목이 몇 % 빠졌나"가 아니라 "코스피보다 몇 %p 더 나쁜가"로 판단한다.
       시장이 통째로 무너지는 날 혼자만 손절당하는 걸 막기 위함.

조정폭은 config.yaml 의 market_adaptive 항목에서 조절한다.
"""
import csv
from dataclasses import dataclass
from datetime import datetime

import api_client
from common import Config, INVESTOR_LOG_PATH, MARKET_LOG_PATH, UPLOW_LOG_PATH


@dataclass
class MarketState:
    index_value: float
    ma_value: float
    trend: str  # "bull" | "bear"
    trend_days: int  # 그 추세가 이어진 연속 거래일 수
    take_profit_pct: float  # 조정 후 익절 기준
    stop_loss_pct: float  # 조정 후 손절 기준
    note: str


def _moving_average(values: list[float], period: int) -> float:
    return sum(values[-period:]) / period


def _count_trend_days(closes: list[float], ma_days: int) -> tuple[str, int]:
    """오늘부터 거슬러 올라가며, 같은 국면(20일선 위/아래)이 며칠 이어졌는지 센다."""
    if len(closes) < ma_days + 1:
        return "bull", 0

    def state_at(i: int) -> str:
        window = closes[: i + 1]
        return "bull" if window[-1] > _moving_average(window, ma_days) else "bear"

    today_state = state_at(len(closes) - 1)
    days = 0
    for i in range(len(closes) - 1, ma_days - 1, -1):
        if state_at(i) == today_state:
            days += 1
        else:
            break
    return today_state, days


def analyze(cfg: Config) -> MarketState:
    """시장 국면을 분석해서 조정된 익절/손절 기준을 돌려준다.
    지수 조회에 실패하면 조정 없이 config 원래 값을 그대로 쓴다 (안전한 기본 동작)."""
    base_tp = cfg.take_profit_pct
    base_sl = cfg.stop_loss_pct

    if not cfg.market_adaptive_enabled:
        return MarketState(0, 0, "bull", 0, base_tp, base_sl, "시장 반영 기능 꺼짐 (기본 기준 사용)")

    try:
        rows = api_client.get_index_daily_prices(cfg, cfg.index_code, lookback_days=90)
        closes = [r["close"] for r in rows]
        if len(closes) < cfg.trend_ma_days + 1:
            return MarketState(0, 0, "bull", 0, base_tp, base_sl, "지수 데이터 부족 (기본 기준 사용)")

        trend, days = _count_trend_days(closes, cfg.trend_ma_days)
        ma_value = _moving_average(closes, cfg.trend_ma_days)
        index_value = closes[-1]
    except Exception as e:
        return MarketState(0, 0, "bull", 0, base_tp, base_sl, f"지수 조회 실패, 기본 기준 사용 ({e})")

    # 지속일수는 상한을 둔다. (하락장 50일째라고 손절선이 무한정 조여지면 안 되므로)
    effective_days = min(days, cfg.max_adjust_days)

    if trend == "bull":
        tp = base_tp + cfg.bull_tp_per_day * effective_days
        sl = base_sl + cfg.bull_sl_per_day * effective_days
    else:
        tp = base_tp + cfg.bear_tp_per_day * effective_days
        sl = base_sl + cfg.bear_sl_per_day * effective_days

    # 안전장치: 익절이 0 이하로 내려가거나 손절이 0 이상으로 올라가면 말이 안 되므로 막는다.
    tp = max(tp, 0.5)
    sl = min(sl, -1.0)

    label = "상승장" if trend == "bull" else "하락장"
    note = (
        f"{label} {days}일째 (지수 {index_value:,.0f} / {cfg.trend_ma_days}일선 {ma_value:,.0f}) "
        f"-> 익절 {base_tp:+.1f}%→{tp:+.1f}%, 손절 {base_sl:+.1f}%→{sl:+.1f}%"
    )
    return MarketState(index_value, ma_value, trend, days, tp, sl, note)


def fetch_kospi_kosdaq_closes(cfg: Config) -> tuple[list[dict], list[dict]] | None:
    """코스피/코스닥 일봉을 한 번에 가져온다. (2026-08-28 추가)

    원래 log_index_snapshot()과 index_divergence_pct()가 각자 따로 코스피/코스닥을
    조회하고 있어서, market.analyze()의 조회(1번)까지 합쳐 회차마다 지수 API
    호출이 5번(analyze 1 + 스냅샷용 2 + 격차계산용 2)이나 나갔다 - "회차마다
    이렇게 많이 조회해도 매매 속도에 지장 없냐"는 질문을 받고서야 이 중복을
    알아챘다. 이 함수 하나로 합쳐서, 두 용도(스냅샷 기록/격차 계산) 다 같은
    조회 결과를 나눠 쓴다 - 회차당 지수 조회가 5번에서 3번(analyze 1 + 이거 2)
    으로 줄어든다.

    조회 실패하거나 데이터가 비어있으면 None (호출하는 쪽이 각자 안전하게 처리)."""
    try:
        kospi_rows = api_client.get_index_daily_prices(cfg, "0001", lookback_days=10)
        kosdaq_rows = api_client.get_index_daily_prices(cfg, "1001", lookback_days=10)
        if not kospi_rows or not kosdaq_rows:
            return None
        return kospi_rows, kosdaq_rows
    except Exception:
        return None


def log_index_snapshot(index_closes: tuple[list[dict], list[dict]] | None) -> None:
    """코스피/코스닥 최신 종가를 회차마다(하루에도 여러 번) 기록한다.
    (2026-08-27 추가, 08-28 리팩터링: 직접 조회하지 않고 fetch_kospi_kosdaq_closes()의
    결과를 받아 쓰도록 바꿈 - 회차당 지수 조회 중복 제거)

    코스피와 코스닥을 같이 남기는 이유: "코스피는 오르는데 코스닥(소형주 비중
    높은 지수)은 안 오르거나 빠지는 날 = 대형주로 쏠리는 날"이라는 가설을
    검증하려는 목적.

    index_closes가 None이거나(조회 실패), 파일 기록 자체가 실패하면(디스크 문제,
    OneDrive 동기화로 인한 파일 잠금 등 - 이 저장소가 OneDrive 폴더 안에 있음)
    그 회차는 그냥 기록을 건너뛴다 - 이 로그는 나중에 분석용일 뿐이라, 여기서
    난 문제로 정작 매매(특히 보유종목 손절/익절 감시)가 통째로 막히면 안 되므로
    예외를 밖으로 절대 던지지 않는다."""
    if not index_closes:
        return
    kospi_rows, kosdaq_rows = index_closes
    try:
        write_header = not MARKET_LOG_PATH.exists()
        with open(MARKET_LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "kospi", "kosdaq"])
            if write_header:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "kospi": f"{kospi_rows[-1]['close']:.2f}",
                "kosdaq": f"{kosdaq_rows[-1]['close']:.2f}",
            })
    except Exception:
        return


def index_divergence_pct(index_closes: tuple[list[dict], list[dict]] | None) -> float | None:
    """오늘 코스피 등락률 - 코스닥 등락률. (2026-08-28 추가, 실험 단계, 같은 날
    리팩터링: fetch_kospi_kosdaq_closes()의 결과를 받아 쓰도록 바꿈)

    (2026-08-28 보강) 슬롯 수 조절은 이제 이 값 대신 kosdaq_change_pct() 단독
    기준으로 바뀌었다 (2x2 분석 결과 코스피 부호는 승패에 큰 영향이 없었음 -
    risk.effective_max_positions 참고). 이 함수는 분석/기록용으로 남겨둔다 -
    market_history.csv에 코스피/코스닥 원값이 그대로 쌓이니 이 값은 언제든
    나중에 다시 계산해볼 수 있다.

    index_closes가 None이거나 데이터가 2일치 미만이면 None을 돌려준다."""
    if not index_closes:
        return None
    kospi_rows, kosdaq_rows = index_closes
    if len(kospi_rows) < 2 or len(kosdaq_rows) < 2:
        return None
    try:
        kospi_change = (kospi_rows[-1]["close"] - kospi_rows[-2]["close"]) / kospi_rows[-2]["close"] * 100
        kosdaq_change = (kosdaq_rows[-1]["close"] - kosdaq_rows[-2]["close"]) / kosdaq_rows[-2]["close"] * 100
        return kospi_change - kosdaq_change
    except Exception:
        return None


def kosdaq_change_pct(index_closes: tuple[list[dict], list[dict]] | None) -> float | None:
    """전날(직전 거래일) 코스닥 등락률. (2026-08-28 추가, 2026-08-31 기준 변경)

    8/4~8/28 데이터를 코스피×코스닥 부호 2x2로 나눠보니, 승률 상위 2분면(70.0%,
    57.9%)이 전부 "코스닥+"였고 하위 2분면(33.3%, 0%)이 전부 "코스닥-"였다 -
    코스피 부호는 승패에 큰 영향이 없었다는 뜻이라, 슬롯 수 조절 기준을 이걸로
    단순화했다 (risk.effective_max_positions 참고).

    (2026-08-31 변경) 처음엔 "오늘 장 시작 시점까지의" 코스닥 등락률(오늘 값 vs
    어제 종가)을 썼는데, 오늘 값은 장중 실시간으로 계속 바뀌는 값이라 장 시작
    직후 몇 분만의 수치로 하루 전체를 판단하는 셈이었다 - 노이즈가 낄 수 있다는
    지적을 받았다. 대신 "전날 마감 기준"(어제 종가 vs 그제 종가)으로 바꿨다 -
    이미 확정된 값이라 노이즈가 없고, 실제로 확인해보니 예측력도 밀리지 않았다
    (전날 코스닥 마이너스 → 다음날 평균 승률 81.3%, 플러스 → 37.7%, 8/4~8/28
    기준). 부수 효과로 이 값은 하루 종일 절대 안 바뀌므로, 예전에 "장 시작
    시점에 한 번만 고정"하던 캐시 장치(risk.daily_effective_max_positions)도
    더 이상 필요 없어져서 없앴다.

    index_closes가 None이거나 데이터가 3일치 미만(전날/그제 종가를 모두 봐야
    하므로)이면 None."""
    if not index_closes:
        return None
    _, kosdaq_rows = index_closes
    if len(kosdaq_rows) < 3:
        return None
    try:
        return (kosdaq_rows[-2]["close"] - kosdaq_rows[-3]["close"]) / kosdaq_rows[-3]["close"] * 100
    except Exception:
        return None


def fetch_investor_flows(cfg: Config) -> dict | None:
    """코스닥 시장 개인/외국인/기관계 순매수(오늘, 최신값). 조회 실패 시 None (fail-open, 로그 전용).
    (2026-08-31 개인만으로 추가, 2026-09-02 외국인/기관계까지 확장 - "장 초반엔 개인이,
    나중엔 기관/외국인이 주로 움직이는 거 아니냐"는 가설을 나중에 검증해보기 위함)
    슬롯 결정에는 아직 안 쓰고 logs/investor_history.csv 에 쌓기만 한다."""
    try:
        return api_client.get_investor_flows(cfg, market_code="1001", market_iscd="KSQ")
    except Exception:
        return None


def fetch_uplow_counts(cfg: Config) -> dict | None:
    """코스닥 시장 상한가/하한가 종목수(지금 이 순간). 조회 실패 시 None (fail-open, 로그 전용).
    (2026-08-31 추가) 슬롯 결정에는 아직 안 쓰고 logs/uplow_history.csv 에 쌓기만 한다."""
    try:
        return api_client.get_uplow_price_count(cfg, market_code="1001")
    except Exception:
        return None


INVESTOR_LOG_FIELDS = [
    "timestamp", "kosdaq_prsn_ntby_qty", "kosdaq_frgn_ntby_qty", "kosdaq_orgn_ntby_qty",
]


def log_investor_snapshot(flows: dict | None) -> None:
    """코스닥 개인/외국인/기관계 순매수를 회차마다 기록한다 (분석용, 2026-08-31 개인만
    으로 추가, 2026-09-02 외국인/기관계까지 확장 - 컬럼이 2개에서 4개로 늘어서, 그 전에
    개인만 쌓인 옛날 행은 새 컬럼이 빈 칸으로 남는다. 새 컬럼 확장 시점은 RULES.md 참고).
    log_index_snapshot 과 동일하게, 조회/기록 실패는 그 회차만 건너뛰고 절대
    예외를 던지지 않는다 (매매 감시를 막으면 안 되므로)."""
    if flows is None:
        return
    try:
        write_header = not INVESTOR_LOG_PATH.exists()
        with open(INVESTOR_LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=INVESTOR_LOG_FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "kosdaq_prsn_ntby_qty": f"{flows['prsn']:.0f}",
                "kosdaq_frgn_ntby_qty": f"{flows['frgn']:.0f}",
                "kosdaq_orgn_ntby_qty": f"{flows['orgn']:.0f}",
            })
    except Exception:
        return


def log_uplow_snapshot(counts: dict | None) -> None:
    """코스닥 상한가/하한가 종목수를 회차마다 기록한다 (분석용, 2026-08-31 추가).
    log_index_snapshot 과 동일하게, 조회/기록 실패는 그 회차만 건너뛰고 절대
    예외를 던지지 않는다 (매매 감시를 막으면 안 되므로)."""
    if not counts:
        return
    try:
        write_header = not UPLOW_LOG_PATH.exists()
        with open(UPLOW_LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "kosdaq_up_count", "kosdaq_down_count"])
            if write_header:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "kosdaq_up_count": counts["up"],
                "kosdaq_down_count": counts["down"],
            })
    except Exception:
        return


def index_change_pct_since(cfg: Config, index_at_buy: float) -> float | None:
    """매수 시점 지수 대비 지금 지수가 몇 % 변했는지. 상대평가 손절에 쓴다."""
    if not index_at_buy:
        return None
    try:
        now = api_client.get_index_price(cfg, cfg.index_code)
    except Exception:
        return None
    return (now - index_at_buy) / index_at_buy * 100
