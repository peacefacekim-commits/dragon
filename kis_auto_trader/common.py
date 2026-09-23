import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
TOKEN_CACHE_PATH = BASE_DIR / "token_cache.json"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
TRADE_LOG_PATH = LOG_DIR / "trades.csv"
DECISION_LOG_PATH = LOG_DIR / "decisions.csv"
# (2026-08-27 추가) 코스피-전략 상관관계 분석용, 하루 1회 코스피 지수 기록.
MARKET_LOG_PATH = LOG_DIR / "market_history.csv"
# (2026-08-31 추가) 코스닥 등락 외에 추가로 검증해볼 지표 2개 - 아직 슬롯 결정에는
# 안 쓰고 로그만 쌓는다 (며칠 데이터 모아서 코스닥 지표처럼 실제 승률 상관관계부터
# 확인한 뒤에 쓸지 결정하기로 함). market.py의 log_investor_snapshot/log_uplow_snapshot 참고.
INVESTOR_LOG_PATH = LOG_DIR / "investor_history.csv"
UPLOW_LOG_PATH = LOG_DIR / "uplow_history.csv"
# (2026-09-01 추가, 사토시룰) 후보 종목별 최근 변동성 기록 - 위와 같은 이유로
# backup.py 대상에 포함. volatility.py 참고.
CANDIDATE_VOLATILITY_LOG_PATH = LOG_DIR / "candidate_volatility.csv"
# (2026-09-03 추가) 코스닥 마이너스로 줄어든 슬롯 대신 가상매수한 기록 -
# virtual_positions.py 참고. 이것도 backup.py 대상에 포함.
VIRTUAL_TRADE_LOG_PATH = LOG_DIR / "virtual_trades.csv"
# (2026-09-03 추가) 감시종목별 회차마다 외국인순매수/프로그램매매/거래량회전율 등
# 이미 조회 중인데 안 쓰고 버리던 필드를 전부 기록 - candidate_snapshot.py 참고.
CANDIDATE_SNAPSHOT_LOG_PATH = LOG_DIR / "candidate_snapshot.csv"
BLOCKLIST_PATH = BASE_DIR / "blocked_stocks.json"

load_dotenv(BASE_DIR / ".env")


@dataclass
class WatchItem:
    code: str
    name: str
    invest_ratio: float
    fixed_qty: int | None = None  # 있으면 비율 계산 무시하고 항상 이 수량만 매수


@dataclass
class Config:
    mode: str  # "mock" | "real"
    total_capital: float
    cash_buffer_ratio: float
    entry_mode: str  # "ma_cross" | "dip_buy"
    short_ma: int
    long_ma: int
    dip_buy_pct: float
    dip_lookback_days: int
    rebound_confirm_pct: float
    reversal_window_days: int
    volume_multiplier: float
    volume_avg_days: int
    candidate_selection: str  # "dip" (기본, 고점대비 하락폭 큰 순) | "volatility" (일중 변동폭 큰 순)
    stop_loss_pct: float
    stop_loss_amount: float
    take_profit_pct: float
    take_profit_amount: float
    buy_fee_pct: float
    sell_fee_pct: float
    sell_tax_pct: float
    max_positions: int
    # (2026-08-26 추가) 오늘 실현손실이 total_capital 의 이 비율(%)을 넘으면
    # 신규 매수를 오늘 안에는 더 이상 하지 않는다 (보유 종목 손절/익절은 계속함).
    # 0이면 이 안전장치 자체가 꺼진 것. risk.daily_loss_limit_breached() 참고.
    daily_loss_limit_pct: float

    # 시장(코스피) 상황 반영 설정
    market_adaptive_enabled: bool
    index_code: str
    trend_ma_days: int
    max_adjust_days: int
    bull_tp_per_day: float
    bull_sl_per_day: float
    bear_tp_per_day: float
    bear_sl_per_day: float
    use_relative_stop_loss: bool

    watchlist: list[WatchItem]

    app_key: str
    app_secret: str
    account_no: str
    base_url: str

    # (2026-09-03 추가) 0보다 크면 rebound_confirm_pct(저점 대비 고정%) 대신
    # "고점->저점 하락폭 중 몇 %를 되돌렸는가"로 반등을 판단한다.
    # strategy.compute_dip_signal 문서 참고. 0이면 꺼짐(기존 동작 그대로).
    retracement_ratio: float = 0.0

    # (2026-09-03 추가) 오늘 실현손실이 이 금액(원)을 넘으면 신규 매수를 중단한다.
    # daily_loss_limit_pct(계좌 총액 비율)와 별개의 절대 금액 기준 -
    # risk.daily_loss_limit_breached() 문서 참고. 0이면 꺼짐.
    # (평소/코스닥 플러스인 날 기준값 - 코스닥 마이너스인 날은 아래
    # daily_loss_limit_amount_kosdaq_negative 가 대신 적용된다.)
    daily_loss_limit_amount: float = 0.0

    # (2026-09-03 추가) 전날 코스닥이 마이너스인 날(슬롯도 KOSDAQ_NEGATIVE_SLOT_CAP로
    # 줄어드는 그 조건)엔, 위 daily_loss_limit_amount 대신 이 값을 손실 한도로 쓴다.
    # risk.effective_daily_loss_limit_amount() 참고. 0이면 꺼짐(코스닥 상태와 무관하게
    # 항상 daily_loss_limit_amount 하나만 적용 - 하위 호환).
    daily_loss_limit_amount_kosdaq_negative: float = 0.0

    # (2026-09-04 추가) False면 신규 실제 매수를 완전히 중단하고, 그 신호를 전부
    # 가상매수로 돌린다 - 사용자 요청: "오늘 거래를 끝으로 실제 투자는 멈추고,
    # 가상투자로 자료를 모은 다음에 투자를 계획하겠다." 이미 보유 중인 종목이
    # 있다면 손절/익절 감시는 그대로 계속된다(신규 매수만 막음). trader.py의
    # run_once()가 이 값이 False면 effective_cap을 강제로 0으로 만들어서, 원래도
    # 있던 "실제 슬롯 한도 도달 시 가상매수로 대체" 로직(virtual_positions.py)을
    # 그대로 재사용한다 - 별도 경로를 새로 안 만들고 이미 검증된 경로를 씀.
    # 기본값 True(기존 동작 그대로) - 하위 호환.
    real_trading_enabled: bool = True

    # (2026-09-03 추가) 주가가 이 금액(원) 미만인 종목은 아예 후보에서 제외한다.
    # 실거래 78건을 분석해보니 매수단가 1만원을 경계로 성적이 확연히 갈렸다
    # (1만원 미만 38건 -198,901원/승률 31.6% vs 1만원 이상 40건 +81,450원/승률 67.5%).
    # 9월 폭락 구간을 빼고 8월만 봐도 같은 방향이었고(68.4% vs 37.9%, 우연일 확률 1.7%),
    # 경계선을 5천/7천/1만/1.5만/2만원으로 바꿔가며 봐도 방향이 일정해서 특정 임계값
    # 하나에 끼워맞춘 결과는 아니라고 판단했다. screener._filter_affordable() 참고
    # (이미 있던 "예산보다 비싼 종목 제외"(상한선)와 짝이 되는 하한선).
    # 0이면 꺼짐 - 하위 호환.
    min_stock_price: float = 0.0

    # (2026-09-13 추가) 고정 유니버스 목표 종목 수 - universe.py 참고.
    # 매일 같은 종목을 관찰해야 패널 데이터가 쌓이므로, 이 개수만큼 한 번
    # 정해두고 그 뒤로는 바꾸지 않는다.
    universe_size: int = 200

    # (2026-09-13 추가) 일봉 패널을 언제부터 받아올지 ("YYYYMMDD") - panel.py 참고.
    # 한 달 보유 전략을 검증할 때 실질 표본은 종목 수가 아니라 개월 수에 가깝기
    # 때문에, 기간이 길수록 좋다. 대신 첫 수집 시간이 길어진다
    # (종목 200개 x 5년이면 대략 12,000번 호출 = 25분 안팎).
    panel_start_date: str = "20210101"


MOCK_BASE_URL = "https://openapivts.koreainvestment.com:29443"
REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"


def load_config() -> Config:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    mode = raw["account"]["mode"].strip().lower()
    if mode not in ("mock", "real"):
        raise ValueError(f"config.yaml 의 account.mode 는 mock 또는 real 이어야 합니다 (현재: {mode})")

    if mode == "mock":
        app_key = os.environ.get("KIS_MOCK_APP_KEY", "")
        app_secret = os.environ.get("KIS_MOCK_APP_SECRET", "")
        account_no = os.environ.get("KIS_MOCK_ACCOUNT_NO", "")
        base_url = MOCK_BASE_URL
    else:
        app_key = os.environ.get("KIS_REAL_APP_KEY", "")
        app_secret = os.environ.get("KIS_REAL_APP_SECRET", "")
        account_no = os.environ.get("KIS_REAL_ACCOUNT_NO", "")
        base_url = REAL_BASE_URL

    if not app_key or not app_secret or not account_no:
        raise RuntimeError(
            f"{mode} 모드에 필요한 API 키/계좌번호가 .env 에 없습니다. "
            f".env.example 을 참고해 .env 파일을 채워주세요."
        )

    watchlist = [
        WatchItem(
            code=str(w["code"]),
            name=w["name"],
            invest_ratio=float(w["invest_ratio"]),
            fixed_qty=int(w["fixed_qty"]) if w.get("fixed_qty") is not None else None,
        )
        for w in raw["watchlist"]
    ]

    ma_raw = raw.get("market_adaptive", {}) or {}

    entry_mode = raw["strategy"].get("entry_mode", "ma_cross").strip().lower()
    if entry_mode not in ("ma_cross", "dip_buy", "news_buy"):
        raise ValueError(
            f"config.yaml 의 strategy.entry_mode 는 ma_cross, dip_buy, news_buy 중 하나여야 합니다 "
            f"(현재: {entry_mode})"
        )

    candidate_selection = str(raw["strategy"].get("candidate_selection", "dip")).strip().lower()
    if candidate_selection not in ("dip", "volatility"):
        raise ValueError(
            f"config.yaml 의 strategy.candidate_selection 은 dip, volatility 중 하나여야 합니다 "
            f"(현재: {candidate_selection})"
        )

    return Config(
        mode=mode,
        total_capital=float(raw["account"]["total_capital"]),
        cash_buffer_ratio=float(raw["account"]["cash_buffer_ratio"]),
        entry_mode=entry_mode,
        short_ma=int(raw["strategy"]["short_ma"]),
        long_ma=int(raw["strategy"]["long_ma"]),
        dip_buy_pct=float(raw["strategy"].get("dip_buy_pct", -5.0)),
        dip_lookback_days=int(raw["strategy"].get("dip_lookback_days", 5)),
        rebound_confirm_pct=float(raw["strategy"].get("rebound_confirm_pct", 0.0)),
        reversal_window_days=int(raw["strategy"].get("reversal_window_days", 3)),
        # 0이면 거래량 확인 기능 꺼짐 (2026-08-20, 하위 호환)
        volume_multiplier=float(raw["strategy"].get("volume_multiplier", 0)),
        volume_avg_days=int(raw["strategy"].get("volume_avg_days", 5)),
        candidate_selection=candidate_selection,
        stop_loss_pct=float(raw["risk"]["stop_loss_pct"]),
        # 종목당 손실 금액(원)이 이 값 이상이면 %기준과 무관하게 손절 (2026-08-20).
        # 없으면 0 (금액 기준 꺼짐 -> % 기준만 적용, 하위 호환)
        stop_loss_amount=float(raw["risk"].get("stop_loss_amount", 0)),
        # 없으면 0 (익절 기능 끔) 으로 취급 -> 하위 호환
        take_profit_pct=float(raw["risk"].get("take_profit_pct", 0)),
        # 종목당 순이익 금액(원)이 이 값 이상이면 %기준과 무관하게 익절 (2026-08-11).
        # 없으면 0 (금액 기준 꺼짐 -> % 기준만 적용, 하위 호환)
        take_profit_amount=float(raw["risk"].get("take_profit_amount", 0)),
        # 매수 수수료, 매도 수수료, 매도 시 증권거래세 (전부 %, 없으면 아래 기본값)
        buy_fee_pct=float(raw.get("fees", {}).get("buy_fee_pct", 0.015)),
        sell_fee_pct=float(raw.get("fees", {}).get("sell_fee_pct", 0.015)),
        sell_tax_pct=float(raw.get("fees", {}).get("sell_tax_pct", 0.18)),
        max_positions=int(raw["risk"]["max_positions"]),
        # 없으면 0 (계좌 전체 손실 한도 꺼짐 -> 하위 호환, 2026-08-26 추가)
        daily_loss_limit_pct=float(raw["risk"].get("daily_loss_limit_pct", 0)),
        market_adaptive_enabled=bool(ma_raw.get("enabled", False)),
        index_code=str(ma_raw.get("index_code", "0001")),
        trend_ma_days=int(ma_raw.get("trend_ma_days", 20)),
        max_adjust_days=int(ma_raw.get("max_adjust_days", 5)),
        bull_tp_per_day=float(ma_raw.get("bull_tp_per_day", 0.3)),
        bull_sl_per_day=float(ma_raw.get("bull_sl_per_day", -0.3)),
        bear_tp_per_day=float(ma_raw.get("bear_tp_per_day", -0.2)),
        bear_sl_per_day=float(ma_raw.get("bear_sl_per_day", 0.3)),
        use_relative_stop_loss=bool(ma_raw.get("use_relative_stop_loss", False)),
        watchlist=watchlist,
        app_key=app_key,
        app_secret=app_secret,
        account_no=account_no,
        base_url=base_url,
        retracement_ratio=float(raw["strategy"].get("retracement_ratio", 0.0)),
        daily_loss_limit_amount=float(raw["risk"].get("daily_loss_limit_amount", 0)),
        daily_loss_limit_amount_kosdaq_negative=float(
            raw["risk"].get("daily_loss_limit_amount_kosdaq_negative", 0)
        ),
        min_stock_price=float(raw["strategy"].get("min_stock_price", 0)),
        real_trading_enabled=bool(raw["account"].get("real_trading_enabled", True)),
        universe_size=int((raw.get("universe") or {}).get("size", 200)),
        panel_start_date=str((raw.get("universe") or {}).get("panel_start_date", "20210101")),
    )
