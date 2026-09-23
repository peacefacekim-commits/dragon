"""trader.py의 새 순수 관찰(데이터 수집) 흐름을 검증하는 회귀 테스트.

(2026-09-04 대개편) 실전투자를 완전히 접으면서 예전 tests/sim20.py(매수/매도/
손절/익절/교체 20개 시나리오)는 더 이상 의미가 없어져서 이 파일로 교체했다.
이제 확인할 건 "코드가 죽지 않고, 회차마다 예정된 것들이 전부 기록되는가"뿐이다.

또한 구조적으로 실제 주문을 낼 방법이 없어졌다는 것도 여기서 직접 확인한다 -
api_client.py에 주문 관련 함수가 하나도 안 남아있는지 체크한다 (설정으로 끈
게 아니라 코드 자체에 없다는 걸 회귀적으로 보장).

실행:
  python tests/test_observation.py
(저장소 루트 어디서 실행해도 되도록 아래에서 repo 루트를 sys.path에 직접 추가한다)

네트워크 호출은 전부 스텁 처리하고, 모든 상태 파일은 임시 디렉터리에 격리해서
실제 계좌/저장소에 영향이 전혀 없다."""
import sys, types, tempfile, pathlib, os, csv, re

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
requests_stub.post = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('네트워크 호출 금지 - 애초에 주문 함수가 없어야 함'))
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
common.CANDIDATE_VOLATILITY_LOG_PATH = tmp / 'logs' / 'candidate_volatility.csv'
common.VIRTUAL_TRADE_LOG_PATH = tmp / 'logs' / 'virtual_trades.csv'
common.CANDIDATE_SNAPSHOT_LOG_PATH = tmp / 'logs' / 'candidate_snapshot.csv'

import api_client
import backup
import market
import trader
from common import Config, WatchItem

backup.backup_trade_data = lambda: True

results = []
def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


WATCHLIST_CODES = [("100001", "종목A"), ("100002", "종목B"), ("100003", "종목C")]

cfg = Config(
    mode="real", total_capital=1_800_000, cash_buffer_ratio=0.0,
    entry_mode="dip_buy", short_ma=5, long_ma=20,
    dip_buy_pct=-10.0, dip_lookback_days=20, rebound_confirm_pct=3.0,
    reversal_window_days=3, volume_multiplier=0.0, volume_avg_days=5,
    candidate_selection="dip", stop_loss_pct=-4.0, stop_loss_amount=16000.0,
    take_profit_pct=3.5, take_profit_amount=16000.0,
    buy_fee_pct=0.015, sell_fee_pct=0.015, sell_tax_pct=0.18,
    max_positions=5, daily_loss_limit_pct=5.0,
    market_adaptive_enabled=False, index_code="0001", trend_ma_days=20,
    max_adjust_days=5, bull_tp_per_day=0.0, bull_sl_per_day=0.0,
    bear_tp_per_day=0.0, bear_sl_per_day=0.0, use_relative_stop_loss=False,
    watchlist=[WatchItem(code=c, name=n, invest_ratio=0.2) for c, n in WATCHLIST_CODES],
    app_key="k", app_secret="s", account_no="1-01", base_url="https://x",
    daily_loss_limit_amount=100000.0, daily_loss_limit_amount_kosdaq_negative=10000.0,
    real_trading_enabled=False,
)

# =====================================================================
# 0) 구조적 확인: api_client.py에 주문 관련 함수가 하나도 없어야 한다
# =====================================================================
for fn in ["place_order", "place_order_and_verify", "_submit_order", "_try_on_exchange",
           "get_order_fill_price", "api_get_holding_qty"]:
    check(f"0) api_client에 {fn} 함수가 없음 (구조적으로 실제 주문 불가)", not hasattr(api_client, fn))

# 실제 주문을 내던 모듈들 자체가 없어야 한다.
# (2026-09-13) 이 목록에 backtest 가 있었는데 뺐다. 그때 지운 backtest.py 는
# 실거래 전략을 돌리던 파일이었고, 지금 같은 이름으로 새로 만든 backtest.py 는
# 쌓아둔 일봉 패널을 읽어 계산만 하는 파일이라 성격이 다르다. 대신 바로 아래에서
# "주문도 API 호출도 하지 않는다"를 확인한다 - 목록에서 빼기만 하면 검사에
# 구멍이 생기므로.
#
# (2026-09-16) 같은 이유로 strategy 도 뺐다. 그때 지운 strategy.py 는 실제로
# 주문을 내던 파일이고, 지금 같은 이름으로 새로 만든 strategy.py 는 krx_panel
# 을 읽어 백테스트만 하는 파일이다. 역시 아래에서 주문/API 를 안 쓰는지 본다.
import importlib
for mod_name in ["compare_strategies", "manual_trade", "liquidate",
                  "evening_screen", "watch_positions"]:
    try:
        importlib.import_module(mod_name)
        check(f"0) {mod_name} 모듈이 삭제되어 import 실패해야 함", False, "import 성공함 (삭제 안 됨)")
    except ModuleNotFoundError:
        check(f"0) {mod_name} 모듈이 삭제됨 (import 실패 확인)", True)

# 새 backtest.py / strategy.py / paper_trade.py 는 패널 파일만 읽는다 - 주문은
# 물론 API/인증조차 건드리면 안 된다. (2026-09-17) paper_trade.py 는 이름이
# 'trade' 라서 특히 헷갈리기 쉽다. CSV 만 읽고 CSV 만 쓴다.
import backtest as _bt        # noqa: F401
import strategy as _st        # noqa: F401
import paper_trade as _pt     # noqa: F401
import analyze_losers as _al  # noqa: F401
import analyze_skip_rules as _asr  # noqa: F401
import analyze_timing as _at  # noqa: F401
import analyze_flow as _af  # noqa: F401
import analyze_extremes as _ax  # noqa: F401
for _name in ("backtest.py", "strategy.py", "paper_trade.py",
              "analyze_losers.py", "analyze_skip_rules.py",
              "analyze_timing.py", "analyze_flow.py",
              "analyze_extremes.py", "analyze_self_signal.py",
              "analyze_pools.py", "analyze_lowvol.py",
              "analyze_windows.py", "analyze_best_rounds.py",
              "analyze_bottoms.py", "analyze_decay.py",
              "analyze_news_ceiling.py", "analyze_consensus.py",
              "analyze_rare_trading.py", "analyze_cascade.py",
              "plan_2m.py", "analyze_short_term.py",
              "analyze_turnover.py", "analyze_stops.py",
              "analyze_event_rebal.py", "analyze_recycle.py",
              "analyze_knobs.py", "analyze_fundamentals.py",
              "analyze_why.py", "analyze_intraday.py",
              "analyze_styles.py"):
    _src = (REPO_ROOT / _name).read_text(encoding="utf-8")
    for banned in ["place_order", "api_client", "auth", "requests"]:
        check(f"0) {_name} 가 {banned} 를 쓰지 않음 (계산 전용, 실행 경로 아님)",
              banned not in _src)
    # 사용자 PC 는 윈도우다. 리눅스 절대경로가 박혀 있으면 그쪽에서 안 돈다.
    check(f"0b) {_name} 에 리눅스 절대경로가 박혀 있지 않음",
          '"/home/user/' not in _src)

# --- .bat 안의 한글은 콘솔 코드페이지에 따라 깨진다 (실제로 겪었다).
#     파일 이름은 한글이어도 되지만 **내용**은 ASCII 만 쓴다.
#     (2026-09-19 추가) 새 .bat 를 만들 때마다 같은 실수를 반복하지 않도록
#     검사로 박아둔다.
#
#     아래 둘은 이 규칙이 생기기 전에 만든 실계좌 매매용 실행 파일이다.
#     지금은 주문 함수 자체가 없어서 쓰이지 않으므로, 내용을 건드려서
#     새 문제를 만들기보다 알려진 예외로 적어둔다.
_BAT_LEGACY = {"run_daemon_scheduled.bat", "run_trader.bat"}
for _bat in sorted(REPO_ROOT.glob("*.bat")):
    if _bat.name in _BAT_LEGACY:
        continue
    _bad = [c for c in _bat.read_bytes() if c > 127]
    check(f"0c) {_bat.name} 내용이 ASCII 다 (한글은 CP949 에서 깨진다)",
          not _bad, f"ASCII 아닌 바이트 {len(_bad)}개")

# --- (2026-09-20 추가) 데이터를 푸시하는 .bat 는 푸시 전에 pull 해야 한다.
#     실제로 겪은 문제: KRX 수집은 1단계에서 pull 하고 10시간 뒤에 5단계에서
#     push 한다. 그 사이에 내가 커밋을 올려놔서 push 가 거부됐다. 수집은
#     멀쩡히 끝나고 커밋까지 됐는데 사용자 화면에는 에러만 남았다.
for _bat in sorted(REPO_ROOT.glob("*.bat")):
    if _bat.name in _BAT_LEGACY:
        continue
    _t = _bat.read_text(encoding="utf-8")
    if "git push" not in _t:
        continue
    _before = _t.split("git push")[0]
    # "git pull" 을 그대로 찾으면 안 된다. 에디터를 막으려고 중간에 옵션이
    # 붙는다 (git -c core.editor=true pull). 하는 일로 찾는다.
    _PULL = re.compile(r"git(?:\s+-c\s+\S+)*\s+pull\b")
    check(f"0c2) {_bat.name} 은 push 전에 pull 한다 (10시간 뒤 거부 방지)",
          _PULL.search(_before.rsplit("git commit", 1)[-1]),
          "commit 과 push 사이에 pull 이 있어야 한다")

# --- (2026-09-21 추가) pull 이 에디터를 열면 안 된다.
#     실제로 겪은 문제: 맨 앞의 "git pull" 이 머지 메시지 편집기(vim)를
#     띄웠고, 저장 없이 빠져나오면서 .git/MERGE_HEAD 가 남았다. 그 뒤로는
#     모든 pull 이 "You have not concluded your merge" 로 실패했고, 밤새
#     모은 KRX 재무 데이터가 며칠 동안 GitHub 에 못 올라갔다.
#     화면에는 에러만 보이고 원인은 안 보였다.
#     설명문(rem)과 화면에 찍는 글(echo)에도 "git pull" 이 나오므로
#     실제로 실행되는 줄만 본다.
_PULL_CMD = re.compile(r"^git(?:\s+-c\s+\S+)*\s+pull\b")


def _bat_commands(text):
    for raw in text.splitlines():
        ln = raw.strip()
        low = ln.lower()
        if not ln or low.startswith(("rem ", "rem\t", "::", "echo")) or low == "rem":
            continue
        yield ln


for _bat in sorted(REPO_ROOT.glob("*.bat")):
    if _bat.name in _BAT_LEGACY:
        continue
    for _cmd in _bat_commands(_bat.read_text(encoding="utf-8")):
        if not _PULL_CMD.match(_cmd):
            continue
        check(f"0c3) {_bat.name} 의 pull 이 에디터를 안 연다",
              "--no-edit" in _cmd or "core.editor" in _cmd,
              f"vim 에 갇히면 머지가 남는다: {_cmd}")

# --- 머지가 남아 있으면 그 뒤 git 명령이 전부 막힌다. 데이터를 푸시하는
#     .bat 는 그 상태를 스스로 알아채고 풀어야 한다.
for _bat in sorted(REPO_ROOT.glob("*.bat")):
    if _bat.name in _BAT_LEGACY:
        continue
    _t = _bat.read_text(encoding="utf-8")
    if "git push" not in _t:
        continue
    check(f"0c4) {_bat.name} 은 끝나지 않은 머지를 먼저 확인한다",
          "MERGE_HEAD" in _t,
          "남은 머지를 못 풀면 수집 결과가 계속 못 올라간다")
    check(f"0c5) {_bat.name} 은 충돌이 있으면 멈춘다 (멋대로 커밋 금지)",
          "diff-filter=U" in _t and "exit /b 1" in _t)

# --- (2026-09-19 추가) 마감 뒤 수집이 한 덩어리로 돌아가는지.
#
#     여기서 확인하려는 것은 순서와 고장 격리 둘이다.
#     순서: market_indicators 가 미국 데이터와 krx_panel 을 읽어서 그날
#           지표 행을 만든다. 그러니 그 둘을 collect_daily 보다 먼저
#           받아야 한다. 거꾸로면 어제 값으로 계산된 행이 남는다.
#     격리: 한 단계가 죽어도 나머지는 돌아야 한다. 미국 데이터를 못 받은
#           것 때문에 한국 일봉까지 못 받으면 그날 기록이 통째로 빈다.
import daemon as _dm  # noqa: E402

_names = [n for (_l, n, _a, _t) in _dm.DAILY_STEPS]
# (2026-09-21) 개수를 박아두면 단계를 늘릴 때마다 뜻 없이 깨진다.
# 있어야 할 단계가 다 있는지로 바꿨다.
for _need in ("fetch_intraday.py", "fetch_us_market.py", "fetch_us_futures.py",
              "fetch_krx_history.py", "collect_daily.py"):
    check(f"0d) 마감 뒤 수집에 {_need} 가 있다", _need in _names, str(_names))
# 10분봉은 KIS 당일분봉 API 가 오늘 것만 주므로 소급이 안 된다. 뒤 단계가
# 오래 걸리거나 터져도 이건 먼저 끝나 있어야 한다. 나머지는 나중에 채울 수 있다.
check("0d1b) 10분봉을 제일 먼저 받는다 (소급이 안 되므로)",
      _names[0] == "fetch_intraday.py", str(_names))
check("0d2) 전략이 읽는 krx_panel 을 갱신하는 단계가 있다",
      "fetch_krx_history.py" in _names, str(_names))
check("0d3) 그 단계에 --update 가 붙어 있다 (없으면 받은 종목을 전부 건너뛴다)",
      any(n == "fetch_krx_history.py" and "--update" in a
          for (_l, n, a, _t) in _dm.DAILY_STEPS), str(_dm.DAILY_STEPS))
check("0d4) 미국 데이터를 collect_daily 보다 먼저 받는다 (지표가 그걸 읽는다)",
      _names.index("fetch_us_market.py") < _names.index("collect_daily.py"),
      str(_names))
check("0d5) 한국 일봉도 collect_daily 보다 먼저 받는다",
      _names.index("fetch_krx_history.py") < _names.index("collect_daily.py"),
      str(_names))
check("0d6) KRX 갱신 시간제한이 넉넉하다 (1,744종목 x 0.4초 = 12분 이상)",
      all(t >= 3600 for (_l, n, _a, t) in _dm.DAILY_STEPS
          if n == "fetch_krx_history.py"), str(_dm.DAILY_STEPS))

# 한 단계가 실패해도 나머지가 돌아야 한다 - 가짜로 확인한다.
_ran, _saved = [], _dm._run_script
_dm._run_script = lambda p, t, label, args=None: (
    _ran.append(label), (_ for _ in ()).throw(RuntimeError("죽음"))
    if label == "미국 지수 수집" else None)[1]
try:
    _dm.run_daily_collection()
except Exception as _e:
    _ran.append(f"터짐:{type(_e).__name__}")
_dm._run_script = _saved
check("0d7) 한 단계가 죽어도 나머지 단계가 돈다 (고장 격리)",
      "일일 패널 수집" in _ran and not any(s.startswith("터짐") for s in _ran),
      str(_ran))

# KRX 계정이 없으면 매일 실패 알림을 보내지 말고 조용히 건너뛴다.
import os as _os  # noqa: E402
_keep = (_os.environ.pop("KRX_ID", None), _os.environ.pop("KRX_PW", None))
check("0e) 계정이 없으면 KRX 단계를 건너뛴다고 판단한다",
      _dm.krx_credentials_missing() is True)
_ran2, _saved2 = [], _dm._run_script
_dm._run_script = lambda p, t, label, args=None: _ran2.append(label)
_dm.run_daily_collection()
_dm._run_script = _saved2
check("0e2) 그래서 KRX 단계를 아예 실행하지 않는다 (실패 알림이 매일 가지 않게)",
      "KRX 일봉 갱신" not in _ran2, str(_ran2))
check("0e3) 계정이 없어도 나머지 단계는 그대로 돈다",
      "일일 패널 수집" in _ran2 and "미국 지수 수집" in _ran2, str(_ran2))
_os.environ["KRX_ID"], _os.environ["KRX_PW"] = "id", "pw"
check("0e4) 계정이 있으면 건너뛰지 않는다",
      _dm.krx_credentials_missing() is False)
for _k, _v in zip(("KRX_ID", "KRX_PW"), _keep):
    _os.environ.pop(_k, None)
    if _v is not None:
        _os.environ[_k] = _v

# =====================================================================
# 1) 정상 케이스: 3종목 전부 조회 성공 -> candidate_snapshot.csv에 3줄 기록
# =====================================================================
api_client.get_holdings = lambda c: {}
market.fetch_kospi_kosdaq_closes = lambda c: None
market.log_index_snapshot = lambda *a, **k: None
market.fetch_investor_flows = lambda c: None
market.log_investor_snapshot = lambda *a, **k: None
market.fetch_uplow_counts = lambda c: None
market.log_uplow_snapshot = lambda *a, **k: None

quotes = {"100001": 10000.0, "100002": 20000.0, "100003": 999.0}
api_client.get_quote = lambda c, code: {
    "price": quotes[code], "high": quotes[code], "low": quotes[code],
    "change_pct": 1.0, "volume": 12345, "raw": {"frgn_ntby_qty": "100"},
}

trader.run_once(cfg)

with open(common.CANDIDATE_SNAPSHOT_LOG_PATH, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
check("1) candidate_snapshot.csv에 감시종목 3개 전부 기록됨", len(rows) == 3, str(len(rows)))
check("1b) 기록된 가격이 정확함", {r["code"]: float(r["price"]) for r in rows} == quotes)

# =====================================================================
# 2) 종목 하나 조회 실패해도 나머지는 계속 기록됨 (예외 전파 안 됨)
# =====================================================================
common.CANDIDATE_SNAPSHOT_LOG_PATH.unlink()


def flaky_quote(c, code):
    if code == "100002":
        raise RuntimeError("일시적 조회 실패")
    return {"price": quotes[code], "high": quotes[code], "low": quotes[code],
            "change_pct": 0.0, "volume": 1, "raw": {}}


api_client.get_quote = flaky_quote
try:
    trader.run_once(cfg)
    ok2 = True
except Exception as e:
    ok2 = False
    print(f"   예외: {e}")
check("2) 한 종목 조회 실패해도 run_once 자체는 예외 없이 끝남", ok2)

with open(common.CANDIDATE_SNAPSHOT_LOG_PATH, encoding="utf-8-sig") as f:
    rows2 = list(csv.DictReader(f))
check("2b) 실패한 종목 빼고 나머지 2개는 기록됨", len(rows2) == 2, str(len(rows2)))

# =====================================================================
# 3) 실제 보유 종목이 있으면(과거 잔량 등) 경고만 하고 절대 매도를 시도하지 않음
#    (매도할 방법 자체가 코드에 없으니, 여기서는 "예외 없이 끝나는지"만 확인)
# =====================================================================
api_client.get_quote = lambda c, code: {
    "price": quotes[code], "high": quotes[code], "low": quotes[code],
    "change_pct": 0.0, "volume": 1, "raw": {},
}
api_client.get_holdings = lambda c: {"100001": {"qty": 10, "avg_price": 9000.0, "name": "종목A"}}
try:
    trader.run_once(cfg)
    ok3 = True
except Exception as e:
    ok3 = False
    print(f"   예외: {e}")
check("3) 실제 보유 종목이 있어도(과거 잔량) 예외 없이 끝남 (매도 시도 안 함)", ok3)

# =====================================================================
# 4) get_holdings 조회 자체가 실패해도(예: 네트워크 오류) 관찰은 계속 진행됨
# =====================================================================
api_client.get_holdings = lambda c: (_ for _ in ()).throw(RuntimeError("계좌 조회 실패"))
common.CANDIDATE_SNAPSHOT_LOG_PATH.unlink()
try:
    trader.run_once(cfg)
    ok4 = True
except Exception as e:
    ok4 = False
    print(f"   예외: {e}")
check("4) 잔고 조회 실패해도 관찰은 계속 진행됨 (fail-open)", ok4)
with open(common.CANDIDATE_SNAPSHOT_LOG_PATH, encoding="utf-8-sig") as f:
    rows4 = list(csv.DictReader(f))
check("4b) 잔고 조회 실패와 무관하게 3종목 다 기록됨", len(rows4) == 3, str(len(rows4)))

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
