"""trader.py의 다중 팩터 가상매매(모멘텀/추세추종/저변동성/밸류)와 감시종목
확장(screener 순위 API 병합)을 검증하는 회귀 테스트.

(2026-09-05 추가) "감시종목 수를 늘리고, 여러 투자 방식을 실제로 했다면
어떤 데이터가 나올지 보고 싶다"는 요청으로 trader.py에 추가된 로직 전용
테스트 - tests/test_observation.py(순수 관찰 골격)와는 별도로 둔다.

실행:
  python tests/test_factor_strategies.py

네트워크 호출은 전부 스텁 처리하고, 모든 상태 파일은 임시 디렉터리에
격리해서 실제 계좌/저장소에 영향이 전혀 없다."""
import sys, types, tempfile, pathlib, os, csv

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

auth_stub = types.ModuleType('auth')
auth_stub.get_access_token = lambda cfg: 't'
auth_stub.get_hashkey = lambda cfg, b: 'h'
sys.modules['auth'] = auth_stub
news_stub = types.ModuleType('news')
news_stub.fetch_recent_news = lambda c: []
news_stub.judge_sentiment = lambda n, i: 'neutral'
sys.modules['news'] = news_stub
requests_stub = types.ModuleType('requests')
requests_stub.get = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('네트워크 호출 금지'))
requests_stub.exceptions = types.SimpleNamespace(RequestException=Exception, ConnectionError=Exception, Timeout=Exception)
sys.modules['requests'] = requests_stub

os.environ['KIS_REAL_APP_KEY'] = 'k'
os.environ['KIS_REAL_APP_SECRET'] = 's'
os.environ['KIS_REAL_ACCOUNT_NO'] = '123-01'

tmp = pathlib.Path(tempfile.mkdtemp())
(tmp / 'logs').mkdir()

import common
common.BASE_DIR = tmp
common.LOG_DIR = tmp / 'logs'
common.TRADE_LOG_PATH = tmp / 'logs' / 'trades.csv'
common.DECISION_LOG_PATH = tmp / 'logs' / 'decisions.csv'
common.MARKET_LOG_PATH = tmp / 'logs' / 'market_history.csv'
common.INVESTOR_LOG_PATH = tmp / 'logs' / 'investor_history.csv'
common.UPLOW_LOG_PATH = tmp / 'logs' / 'uplow_history.csv'
common.VIRTUAL_TRADE_LOG_PATH = tmp / 'logs' / 'virtual_trades.csv'
common.CANDIDATE_SNAPSHOT_LOG_PATH = tmp / 'logs' / 'candidate_snapshot.csv'

import risk
risk.TRADE_LOG_PATH = common.TRADE_LOG_PATH

import api_client
import backup
import candidate_snapshot
import market
import screener
import trader
import virtual_positions as vp
from common import Config, WatchItem

vp.STATE_PATH = tmp / 'virtual_positions.json'
vp.VIRTUAL_TRADE_LOG_PATH = common.VIRTUAL_TRADE_LOG_PATH
candidate_snapshot.CANDIDATE_SNAPSHOT_LOG_PATH = common.CANDIDATE_SNAPSHOT_LOG_PATH
backup.backup_trade_data = lambda: True

results = []
def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


WATCHLIST_CODES = [("100001", "감시A")]

cfg = Config(
    mode="real", total_capital=1_800_000, cash_buffer_ratio=0.0,
    entry_mode="dip_buy", short_ma=5, long_ma=20,
    dip_buy_pct=-10.0, dip_lookback_days=20, rebound_confirm_pct=3.0,
    reversal_window_days=3, volume_multiplier=0.0, volume_avg_days=5,
    candidate_selection="dip", stop_loss_pct=-4.0, stop_loss_amount=0.0,
    take_profit_pct=3.5, take_profit_amount=0.0,
    buy_fee_pct=0.015, sell_fee_pct=0.015, sell_tax_pct=0.18,
    max_positions=2, daily_loss_limit_pct=0.0,
    market_adaptive_enabled=False, index_code="0001", trend_ma_days=20,
    max_adjust_days=5, bull_tp_per_day=0.0, bull_sl_per_day=0.0,
    bear_tp_per_day=0.0, bear_sl_per_day=0.0, use_relative_stop_loss=False,
    watchlist=[WatchItem(code=c, name=n, invest_ratio=0.2) for c, n in WATCHLIST_CODES],
    app_key="k", app_secret="s", account_no="1-01", base_url="https://x",
    daily_loss_limit_amount=0.0, daily_loss_limit_amount_kosdaq_negative=0.0,
    real_trading_enabled=False,
)

api_client.get_holdings = lambda c: {}
market.fetch_kospi_kosdaq_closes = lambda c: None
market.log_index_snapshot = lambda *a, **k: None
market.fetch_investor_flows = lambda c: None
market.log_investor_snapshot = lambda *a, **k: None
market.fetch_uplow_counts = lambda c: None
market.log_uplow_snapshot = lambda *a, **k: None

# =====================================================================
# 1) 감시종목 확장: screener._base_candidates가 추가 종목을 주면 합쳐지는지
# =====================================================================
EXTRA_CODES = [("200001", "확장B"), ("200002", "확장C")]
screener._base_candidates = lambda c: [{"code": code, "name": name} for code, name in EXTRA_CODES]

universe = trader._build_universe(cfg)
universe_codes = {u["code"] for u in universe}
check("1) 감시종목 + 확장후보가 합쳐져 3종목", universe_codes == {"100001", "200001", "200002"}, str(universe_codes))

# 확장 조회 자체가 실패해도 감시종목만으로는 계속 (fail-open) - 이미 test_observation에서
# 유사 확인했지만 여기선 _build_universe 단위로 한 번 더 직접 확인
screener._base_candidates = lambda c: (_ for _ in ()).throw(RuntimeError("순위 조회 실패"))
universe2 = trader._build_universe(cfg)
check("2) 확장 조회 실패해도 감시종목은 그대로 남음", {u["code"] for u in universe2} == {"100001"})

screener._base_candidates = lambda c: [{"code": code, "name": name} for code, name in EXTRA_CODES]

# =====================================================================
# 2) 팩터별 가상 진입 확인 - 종목마다 특성을 뚜렷하게 다르게 설계
# =====================================================================
# 100001(감시A): 모멘텀 뚜렷 (60일전 100 -> 오늘 150, +50%), 변동 큼, 추세도 위
# 200001(확장B): 60일선 위, 모멘텀은 약함(+1%), 변동성 아주 낮음(거의 고정), PBR 낮음(0.5)
# 200002(확장C): 60일선 아래, 모멘텀 마이너스, 변동성 큼, PBR 높음(5.0)


def make_daily_rows(pattern):
    return [{"date": f"d{i}", "close": c, "high": c, "low": c, "volume": 100} for i, c in enumerate(pattern)]


rows_A = make_daily_rows([100.0] * 60 + [150.0])          # 모멘텀 +50%, 60일선도 확실히 위
rows_B = make_daily_rows([100.0] * 60 + [101.0])           # 거의 안 움직임 -> 변동성 낮음, 60일선 근소 위
rows_C = make_daily_rows([200.0] * 60 + [100.0])           # 급락 -> 60일선 아래, 모멘텀 -50%

daily_rows_map = {"100001": rows_A, "200001": rows_B, "200002": rows_C}
price_map = {"100001": 150.0, "200001": 101.0, "200002": 100.0}
raw_map = {
    "100001": {"pbr": "3.0", "per": "20.0"},
    "200001": {"pbr": "0.5", "per": "5.0"},   # 저PBR -> 밸류 후보
    "200002": {"pbr": "8.0", "per": "50.0"},
}

api_client.get_quote = lambda c, code: {
    "price": price_map[code], "high": price_map[code], "low": price_map[code],
    "change_pct": 0.0, "volume": 1000, "raw": raw_map[code],
}
api_client.get_daily_prices = lambda c, code, lookback_days=90: daily_rows_map[code]

trader.run_once(cfg)

vstate = vp.load_state()
check("3) 모멘텀 전략: 100001(가장 수익률 높음)이 진입됨", vp.has_position(vstate, "momentum", "100001"), str(list(vstate)))
check("4) 추세추종 전략: 200002(60일선 아래)는 진입 안 됨", not vp.has_position(vstate, "trend", "200002"))
check("5) 추세추종 전략: 100001(60일선 위)은 진입됨", vp.has_position(vstate, "trend", "100001"))
check("6) 저변동성 전략: 200001(거의 안 움직임)이 진입됨", vp.has_position(vstate, "low_vol", "200001"), str(list(vstate)))
check("7) 밸류 전략: 200001(PBR 0.5, 가장 저평가)이 진입됨", vp.has_position(vstate, "value", "200001"), str(list(vstate)))
check("8) 밸류 전략: 200002(PBR 8.0, 고평가)는 진입 안 됨", not vp.has_position(vstate, "value", "200002"))

with open(common.VIRTUAL_TRADE_LOG_PATH, encoding="utf-8-sig") if common.VIRTUAL_TRADE_LOG_PATH.exists() else open(os.devnull) as f:
    pass  # 이번 회차엔 진입만 있고 청산은 없어서 아직 파일 없을 수 있음 - 정상

# =====================================================================
# 3) 같은 종목을 여러 전략이 동시에 보유할 수 있는지 (전략별 독립 장부)
# =====================================================================
check("9) 100001은 momentum과 trend 두 전략에 동시에 진입됨 (전략별 독립 장부)",
      vp.has_position(vstate, "momentum", "100001") and vp.has_position(vstate, "trend", "100001"))

# =====================================================================
# 4) 다음 회차: 100001 가격 폭락 -> momentum/trend 전략 둘 다 손절되는지
#    (같은 손절 기준을 공유하므로 둘 다 걸려야 함)
# =====================================================================
price_map["100001"] = 140.0  # 150 -> 140 = -6.7%, 기준 -4% 손절 발동
api_client.get_quote = lambda c, code: {
    "price": price_map[code], "high": price_map[code], "low": price_map[code],
    "change_pct": 0.0, "volume": 1000, "raw": raw_map[code],
}

trader.run_once(cfg)
vstate2 = vp.load_state()
# (100001은 폭락 후에도 여전히 모멘텀 1위/60일선 위라 손절 -> 같은 회차 안에서 곧바로
# 재진입한다 - 이게 버그가 아니라 의도된 동작인지, 새 평단(140원)으로 다시 열렸는지로
# 확인한다. "청산 자체가 됐는지"는 virtual_trades.csv 기록(아래 12번)으로 따로 검증.)
check("10) 폭락 후 momentum 포지션이 새 평단(140원)으로 재진입됨 (기존 150원 포지션은 청산됨)",
      vp.has_position(vstate2, "momentum", "100001") and vstate2["momentum:100001"]["avg_price"] == 140.0,
      str(vstate2.get("momentum:100001")))
check("11) 폭락 후 trend 포지션도 새 평단(140원)으로 재진입됨 (같은 손절기준 공유)",
      vp.has_position(vstate2, "trend", "100001") and vstate2["trend:100001"]["avg_price"] == 140.0,
      str(vstate2.get("trend:100001")))

with open(common.VIRTUAL_TRADE_LOG_PATH, encoding="utf-8-sig") as f:
    closed_rows = list(csv.DictReader(f))
strategies_closed = {r["strategy"] for r in closed_rows if r["code"] == "100001"}
check("12) virtual_trades.csv에 momentum/trend 둘 다 손절 기록 남음",
      strategies_closed == {"momentum", "trend"}, str(strategies_closed))

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
