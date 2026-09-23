"""새 구조(일봉 페이징 + 고정 유니버스 + 패널 + 백테스트) 검증.

(2026-09-13 신설) 여기서 제일 중요한 건 백테스트가 미래 정보를 쓰지 않는지다.
그게 틀리면 나머지 숫자는 전부 의미가 없다. 그래서 "나중 데이터를 잘라내도
같은 날의 팩터 점수가 똑같이 나오는가"를 직접 비교한다 - 코드를 읽고 판단하는
대신 실제로 값이 같은지 확인하는 방식.

실제 API는 부르지 않는다. 대신 KIS 일봉 API의 "한 번에 100건" 상한을 흉내낸
가짜 응답을 만들어서, 페이징이 정말 그 상한을 넘어 이어붙이는지 확인한다.

실행:
  python tests/test_panel_backtest.py
"""
import pathlib
import shutil
import sys
import tempfile
from datetime import datetime, timedelta

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


def approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


# ---------------------------------------------------------------- 가짜 일봉 시장
#
# 실제 KIS 응답을 흉내낸다: 영업일(월~금)만 존재하고, 한 번 호출에 최대 100건.

def business_days(start: str, end: str) -> list[str]:
    d = datetime.strptime(start, "%Y%m%d")
    e = datetime.strptime(end, "%Y%m%d")
    out = []
    while d <= e:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


class FakeMarket:
    """종목별 일봉을 미리 만들어두고, KIS API처럼 100건 상한을 걸어 돌려준다."""

    MAX_ROWS = 100

    def __init__(self, listed_from: dict, price_fn):
        # listed_from: {code: "YYYYMMDD"} - 이 날짜 전에는 데이터가 없다(상장 전)
        self.listed_from = listed_from
        self.price_fn = price_fn
        self.calls = []

    def bars_for(self, code, start, end):
        out = []
        for i, d in enumerate(business_days("20200101", "20261231")):
            if d < self.listed_from[code] or d < start or d > end:
                continue
            close = self.price_fn(code, i)
            out.append({
                "date": d, "close": close, "high": close * 1.02,
                "low": close * 0.98, "open": close * 0.995, "volume": 1000 + i,
            })
        return out

    def get_daily_prices(self, cfg, code, lookback_days=90, start_date=None, end_date=None):
        self.calls.append((code, start_date, end_date))
        rows = self.bars_for(code, start_date, end_date)
        # KIS 처럼 최신 것부터 100건까지만 준다
        return sorted(rows, key=lambda r: r["date"])[-self.MAX_ROWS:]


def steady(code, i):
    base = {"AAA": 1000.0, "BBB": 5000.0, "CCC": 20000.0}[code]
    slope = {"AAA": 1.0, "BBB": 0.0, "CCC": -1.0}[code]
    return base + slope * i


# ---------------------------------------------------------------- 1) 일봉 페이징

import api_client  # noqa: E402

market = FakeMarket({"AAA": "20200101", "BBB": "20200101", "CCC": "20240701"}, steady)
api_client.get_daily_prices = market.get_daily_prices
api_client._throttle = lambda: None  # 테스트에서 초당 8건 제한은 시간 낭비

truncs = []
bars = api_client.get_daily_prices_range(
    None, "AAA", "20240101", "20241231",
    on_truncated=lambda *a: truncs.append(a))

expected = business_days("20240101", "20241231")
check("1) 페이징으로 1년치를 다 받아온다 (100건 상한을 넘김)",
      len(bars) == len(expected), f"{len(bars)}건 (기대 {len(expected)}건)")
check("1b) 날짜 중복 없음", len({b['date'] for b in bars}) == len(bars))
check("1c) 오래된 순으로 정렬됨", [b["date"] for b in bars] == sorted(b["date"] for b in bars))
check("1d) 조각 길이가 100건 상한 아래라 잘림 경고가 없음", truncs == [], str(truncs[:1]))

# 상장 전 구간을 요청하면 일찍 멈춘다 (빈 호출을 끝까지 반복하지 않음)
market.calls.clear()
bars_c = api_client.get_daily_prices_range(None, "CCC", "20200101", "20241231")
check("1e) 상장(2024-07-01) 이후 데이터만 돌아옴",
      bars_c and bars_c[0]["date"] >= "20240701", bars_c[0]["date"] if bars_c else "없음")
# 2020~2024 전체를 조각내면 15번 넘게 불러야 하는데, 조기 종료로 훨씬 적어야 한다
check("1f) 상장 전 구간에서 조기 종료해 호출을 낭비하지 않음",
      len(market.calls) <= 8, f"{len(market.calls)}번 호출")

# 조각을 일부러 너무 길게 잡으면 잘림 경고가 뜨는지 (경고가 실제로 작동하는지)
truncs.clear()
api_client.get_daily_prices_range(None, "AAA", "20240101", "20241231",
                                  chunk_days=400, on_truncated=lambda *a: truncs.append(a))
check("1g) 조각이 너무 길면 잘림 경고가 뜬다", len(truncs) > 0, f"{len(truncs)}건")


# ---------------------------------------------------------------- 2) 패널 저장소

import panel  # noqa: E402

tmpdir = pathlib.Path(tempfile.mkdtemp())
panel.DATA_DIR = tmpdir / "data"

rows_2025 = [{"date": "20250102", "code": "AAA", "name": "에이", "open": 100, "high": 110,
              "low": 90, "close": 105, "volume": 10}]
rows_2026 = [{"date": "20260102", "code": "AAA", "name": "에이", "open": 200, "high": 210,
              "low": 190, "close": 205, "volume": 20}]
panel.append(rows_2025 + rows_2026)
check("2) 연도별로 파일이 나뉜다",
      (panel.DATA_DIR / "panel_2025.csv").exists() and (panel.DATA_DIR / "panel_2026.csv").exists())

added_again = panel.append(rows_2025)
check("2b) 같은 (날짜,종목)을 다시 넣어도 행이 안 늘어난다", added_again == 0, f"{added_again}행 추가됨")

panel.append([{**rows_2025[0], "close": 999}])
check("2c) 같은 (날짜,종목)은 새 값으로 덮어쓴다 (장중 미완성 행 보정)",
      float(panel.load_by_code(["AAA"])["AAA"][0]["close"]) == 999)

cov = panel.coverage()
check("2d) coverage 가 첫날/마지막날/행수를 맞게 센다",
      cov["AAA"] == ("20250102", "20260102", 2), str(cov))

# 빠진 구간 계산
check("2e) 가진 게 없으면 전체 구간을 받는다",
      panel._missing_ranges(None, "20250101", "20251231") == [("20250101", "20251231")])
mr = panel._missing_ranges(("20250301", "20250630", 80), "20250101", "20251231")
check("2f) 앞쪽 구멍과 뒤쪽 구멍을 둘 다 찾는다",
      mr == [("20250101", "20250228"), ("20250630", "20251231")], str(mr))
check("2g) 마지막 보유일을 다시 받는다 (장중 미완성 행을 덮어쓰려고)",
      mr[-1][0] == "20250630", str(mr))


# 실제 backfill: 두 번 돌려도 두 번째는 새 데이터가 없어야 한다 (멱등성)
class FakeCfg:
    panel_start_date = "20240101"


shutil.rmtree(panel.DATA_DIR, ignore_errors=True)
stocks = [{"code": "AAA", "name": "에이"}, {"code": "BBB", "name": "비"}]
r1 = panel.backfill(FakeCfg(), stocks, start_date="20240101", end_date="20241231", verbose=False)
r2 = panel.backfill(FakeCfg(), stocks, start_date="20240101", end_date="20241231", verbose=False)
check("2h) 첫 수집에서 2종목 1년치가 들어온다",
      r1["added"] == len(expected) * 2, f"{r1['added']}행")
check("2i) 같은 기간을 다시 돌려도 새 행이 0개다 (매일 돌려도 안전)",
      r2["added"] == 0, f"{r2['added']}행 추가됨")


# ---------------------------------------------------------------- 3) 백테스트

import backtest  # noqa: E402

p = backtest.Panel.load()
check("3) 패널을 백테스트용으로 읽는다", len(p.bars) == 2 and len(p.dates) == len(expected),
      f"{len(p.bars)}종목 {len(p.dates)}일")

# --- 미래 정보를 안 쓰는지: 뒤쪽 데이터를 잘라내도 같은 날 점수가 같아야 한다
cut_date = p.dates[150]
truncated = backtest.Panel({
    c: [{"date": b.date, "code": c, "name": "", "open": b.open, "high": b.high,
         "low": b.low, "close": b.close, "volume": b.volume}
        for b in bs if b.date <= cut_date]
    for c, bs in p.bars.items()})

same = True
for code in p.bars:
    for factor in backtest.FACTORS:
        a = backtest.factor_score(p, code, cut_date, factor, 120, 5, 60)
        b = backtest.factor_score(truncated, code, cut_date, factor, 120, 5, 60)
        if (a is None) != (b is None) or (a is not None and not approx(a, b)):
            same = False
            print(f"      {code}/{factor}: 전체={a} 잘라낸뒤={b}")
check("3b) 미래 데이터를 잘라내도 같은 날 팩터 점수가 동일하다 (미래 정보 미사용)", same)

# --- 매수는 '다음 거래일 시가'에 이뤄지는가
code = "AAA"
si = 100
signal_date = p.dates_of[code][si]
bars_a = p.bars[code]
buy_expected = bars_a[si + 1].open
sell_expected = bars_a[si + 1 + 20].open
got = backtest.hold_return(p, code, signal_date, hold_days=20, stop_loss_pct=None)
check("3c) 신호일 종가가 아니라 다음 거래일 시가에 사고, 보유기간 뒤 시가에 판다",
      approx(got, sell_expected / buy_expected - 1.0),
      f"계산값 {got:.6f} / 기대 {sell_expected / buy_expected - 1.0:.6f}")

# --- 손절이 실제로 잘리는가 (저가가 손절선 밑으로 내려간 날)
crash = backtest.Panel({"XXX": [
    {"date": d, "code": "XXX", "name": "", "open": 1000, "high": 1010,
     "low": 1000 if i < 3 else 800, "close": 1000, "volume": 1}
    for i, d in enumerate(["20250102", "20250103", "20250106", "20250107", "20250108"])]})
r = backtest.hold_return(crash, "XXX", "20250102", hold_days=4, stop_loss_pct=-10.0)
check("3d) 저가가 손절선을 뚫으면 손절가로 잘린다", approx(r, -0.10), f"{r}")

# --- 갭하락이면 손절선이 아니라 그날 시가(더 불리한 쪽)로 체결
gap = backtest.Panel({"YYY": [
    {"date": d, "code": "YYY", "name": "", "open": 1000 if i < 2 else 700,
     "high": 1010, "low": 1000 if i < 2 else 690, "close": 1000, "volume": 1}
    for i, d in enumerate(["20250102", "20250103", "20250106", "20250107"])]})
r = backtest.hold_return(gap, "YYY", "20250102", hold_days=3, stop_loss_pct=-10.0)
check("3e) 갭하락이면 손절선(-10%)이 아니라 시가(-30%)로 체결된다 - 실제보다 좋게 안 나오게",
      approx(r, -0.30), f"{r}")

# --- 모멘텀이 실제로 오르는 종목을 고르는가 (동작 확인용 최소 검증)
res = backtest.run(p, factor="momentum", rebalance_days=20, hold_days=20, top_n=1,
                   lookback=60, skip=5, min_candidates=2)
check("3f) 백테스트가 끝까지 돌고 결과를 낸다", res is not None and res.periods > 0,
      res.line() if res else "None")

# AAA 는 계속 오르고 BBB 는 평평하므로 모멘텀 1등은 항상 AAA 여야 한다
picked_aaa = backtest.factor_score(p, "AAA", p.dates[150], "momentum", 60, 5, 60)
picked_bbb = backtest.factor_score(p, "BBB", p.dates[150], "momentum", 60, 5, 60)
check("3g) 오르는 종목의 모멘텀 점수가 평평한 종목보다 높다",
      picked_aaa > picked_bbb, f"AAA={picked_aaa:.4f} BBB={picked_bbb:.4f}")
# 저변동성 팩터: 조용한 종목과 출렁이는 종목을 직접 만들어서 부호 방향을 확인한다
# (패널에 있는 AAA/BBB 는 둘 다 직선이라 이 비교에 못 쓴다)
vol_dates = business_days("20250102", "20250630")
quiet = [{"date": d, "code": "QUIET", "name": "", "open": 1000, "high": 1001,
          "low": 999, "close": 1000 + (i % 2), "volume": 1} for i, d in enumerate(vol_dates)]
wild = [{"date": d, "code": "WILD", "name": "", "open": 1000, "high": 1300,
         "low": 700, "close": 1000 + 200 * (i % 2), "volume": 1} for i, d in enumerate(vol_dates)]
volp = backtest.Panel({"QUIET": quiet, "WILD": wild})
q = backtest.factor_score(volp, "QUIET", vol_dates[-1], "low_vol", 60, 5, 60)
w = backtest.factor_score(volp, "WILD", vol_dates[-1], "low_vol", 60, 5, 60)
check("3h) 저변동성 팩터는 조용한 종목에 더 높은 점수를 준다 (부호 방향)",
      q > w, f"조용={q:.5f} 출렁={w:.5f}")

# 반전(reversal) 팩터는 모멘텀의 정확한 반대여야 한다
m = backtest.factor_score(p, "AAA", p.dates[150], "momentum", 60, 5, 60)
rv = backtest.factor_score(p, "AAA", p.dates[150], "reversal", 60, 5, 60)
check("3h2) 반전 팩터는 모멘텀의 부호만 뒤집은 값이다", approx(rv, -m), f"{rv} vs {-m}")

# --- 보유기간이 패널 끝을 넘어가면 집계에서 빠져야 한다 (마지막 구간 낙관 방지)
last_date = p.dates[-1]
check("3i) 팔 날이 없는 마지막 구간은 집계에서 빠진다",
      backtest.hold_return(p, "AAA", last_date, hold_days=20, stop_loss_pct=None) is None)


# ---------------------------------------------------------------- 4) 고정 유니버스

import universe  # noqa: E402

universe.UNIVERSE_PATH = tmpdir / "universe.json"


class UCfg:
    universe_size = 3
    min_stock_price = 5000.0


# 거래량순위 API 응답을 흉내낸다 (거래대금 = stck_prpr x acml_vol 가 30억 이상이어야 통과)
def vol_row(code, name, price, vol):
    return {"mksc_shrn_iscd": code, "hts_kor_isnm": name,
            "stck_prpr": str(price), "acml_vol": str(vol)}


fake_vol_rows = [
    vol_row("111111", "가나", 10000, 900_000),            # 90억
    vol_row("222222", "다라", 8000, 800_000),             # 64억
    vol_row("333333", "싼주식", 1000, 9_000_000),          # 가격 하한에 걸려 제외
    vol_row("444444", "KODEX 레버리지", 20000, 1_000_000),  # 키워드로 제외
    vol_row("555555", "마바", 30000, 500_000),
    vol_row("666666", "사아", 30000, 400_000),
    vol_row("777777", "거래없음", 30000, 10),              # 거래대금 하한에 걸려 제외
]

universe._volume_rank = lambda cfg, market, blng: fake_vol_rows

universe.top_up(UCfg(), verbose=False)
got_codes = universe.codes()
check("4) 목표 개수(3)만큼만 채운다", len(got_codes) == 3, str(got_codes))
check("4b) 가격 하한 미만 종목은 안 들어간다", "333333" not in got_codes)
check("4c) 레버리지/인버스류는 안 들어간다", "444444" not in got_codes)
check("4c2) 거래대금 30억 미만 종목은 안 들어간다", "777777" not in got_codes)
# 거래대금: 마바 150억 > 사아 120억 > 가나 90억 > 다라 64억 순이므로 위 3개가 들어가야 한다
check("4c3) 거래대금 큰 순으로 먼저 들어간다",
      got_codes == ["555555", "666666", "111111"], str(got_codes))
check("4c4) 출처가 '거래대금상위'로 기록된다",
      universe.source_counts() == {"거래대금상위": 3}, str(universe.source_counts()))

before = list(got_codes)
universe._volume_rank = lambda cfg, market, blng: [vol_row("999999", "새종목", 9000, 500_000)]
universe.top_up(UCfg(), verbose=False)
check("4d) 목표를 채운 뒤에는 유니버스가 바뀌지 않는다 (패널이 흔들리면 안 되므로)",
      universe.codes() == before, str(universe.codes()))

# 목표를 늘리면 그때는 더 채운다. 기존 종목은 그대로 남아야 한다.
class UCfg5(UCfg):
    universe_size = 5


universe._volume_rank = lambda cfg, market, blng: fake_vol_rows + [
    vol_row("999999", "새종목", 9000, 500_000)]
universe.top_up(UCfg5(), verbose=False)
after = universe.codes()
check("4e) 목표를 늘리면 더 채우되, 기존 종목은 하나도 안 빠진다",
      all(c in after for c in before) and len(after) == 5, str(after))

# --- (2026-09-19 추가) 더 이상 안 채워질 때 그렇다고 말해야 한다.
#     실제 실행에서 "0종목 추가 -> 136종목 (목표 200)" 인데도 "며칠에 걸쳐
#     채워집니다" 라고 안내했다. 순위 API 는 매일 거의 같은 이름을 주므로
#     후보를 받았는데 0종목이 추가됐다면 기다려도 안 채워진다. 안내가 틀리면
#     사용자가 며칠을 헛되게 기다린다.
import contextlib  # noqa: E402
import io  # noqa: E402


class UCfg9(UCfg):
    universe_size = 9  # 후보로 절대 못 채우는 목표


universe.UNIVERSE_PATH = tmpdir / "universe_saturated.json"
universe.save(universe._empty())
universe._volume_rank = lambda cfg, market, blng: fake_vol_rows

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    universe.top_up(UCfg9(), verbose=True)
first = buf.getvalue()
n_first = len(universe.codes())
check("4j) 후보가 남아 있는 동안은 채운다 (포화 판정이 성급하지 않다)",
      n_first == 4 and "4종목 추가" in first, f"{n_first}종목 / {first!r}")
check("4j2) 덜 찼고 방금 채웠으면 '며칠에 걸쳐' 안내가 맞다",
      "며칠에 걸쳐" in first)

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    universe.top_up(UCfg9(), verbose=True)
second = buf.getvalue()
check("4k) 같은 후보로 다시 돌리면 0종목 추가다 (실제로 본 상황)",
      "0종목 추가" in second and len(universe.codes()) == n_first, second)
check("4k2) 0종목이면 '더 안 늘어난다'고 말한다",
      "더 안 늘어납니다" in second, second)
check("4k3) 0종목이면 '며칠에 걸쳐 채워진다'고 말하지 않는다 (틀린 안내)",
      "며칠에 걸쳐" not in second, second)
check("4k4) 해결 방법을 알려준다 (목표 낮추기 / 직접 추가)",
      "목표를 낮추" in second and "universe.json" in second, second)
check("4k5) 전략은 krx_panel 에서 뽑으므로 영향 없다고 밝힌다",
      "krx_panel" in second and "영향을 주지는 않습니다" in second, second)

# 후보 조회 자체가 실패했을 때는 포화라고 단정하면 안 된다 (원인이 다르다).
universe._volume_rank = lambda cfg, market, blng: []
import screener as _scr  # noqa: E402
_scr._base_candidates = lambda cfg: []
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    universe.top_up(UCfg9(), verbose=True)
third = buf.getvalue()
check("4k6) 후보가 아예 없으면 포화라고 단정하지 않는다",
      "더 안 늘어납니다" not in third, third)

# --- 대체 출처(fallback): 거래량순위 TR 은 이 저장소에서 실계좌로 확인된 적이
#     없으므로, 실패했을 때 등락률 순위로 넘어가는 경로가 꼭 동작해야 한다.
universe.UNIVERSE_PATH = tmpdir / "universe_fallback.json"


def boom(cfg, market, blng):
    raise RuntimeError("거래량순위 조회 실패: 없는 TR")


universe._volume_rank = boom
import screener  # noqa: E402
screener._base_candidates = lambda cfg: [
    {"code": "aaaaaa", "name": "등락률종목", "price": 12000}]
universe.top_up(UCfg(), verbose=False)
check("4f) 거래량순위가 실패하면 등락률 순위로 되돌아가 채운다",
      universe.codes() == ["aaaaaa"], str(universe.codes()))
check("4g) 대체 출처로 들어온 종목은 그렇게 표시된다 (나중에 편향 확인용)",
      universe.source_counts() == {"등락률상위(대체)": 1}, str(universe.source_counts()))

# 출처 기록이 없던 옛 종목은 '모름'이 아니라 등락률 출처로 이름 붙어야 한다.
# (출처를 적기 시작한 건 9/14 부터이고, 그 전 코드는 등락률 순위만 썼다)
universe.save({"built_at": None, "note": "", "stocks": [{"code": "bbbbbb", "name": "옛종목"}]})
check("4g2) 출처 기록이 없는 옛 종목은 등락률 출처로 표시된다",
      universe.source_counts() == {universe.LEGACY_SOURCE: 1}, str(universe.source_counts()))
check("4g3) 출처로 종목을 걸러낼 수 있다 (출처별 비교용)",
      universe.codes(source=universe.LEGACY_SOURCE) == ["bbbbbb"]
      and universe.codes(source="거래대금상위") == [],
      str(universe.codes(source="거래대금상위")))
universe.save(universe._empty())

# --- --reset 은 목록을 비우고, 다시 채울 수 있어야 한다
universe.save(universe._empty())
check("4h) reset 하면 유니버스가 빈다", universe.codes() == [])
universe.top_up(UCfg(), verbose=False)
check("4i) reset 뒤 다시 채워진다", universe.codes() == ["aaaaaa"])


# ---------------------------------------------------------------- 5) 일별 재무지표

import fundamentals  # noqa: E402

fundamentals.DATA_DIR = tmpdir / "fund"

quote_calls = []


def fake_quote(cfg, code):
    quote_calls.append(code)
    if code == "BAD":
        raise RuntimeError("조회 실패")
    return {"price": 12345.0, "raw": {
        "per": "11.2", "pbr": "0.9", "eps": "1100", "bps": "13700",
        "hts_frgn_ehrt": "4.31", "vol_tnrt": "1.22",
        "whol_loan_rmnd_rate": "0.55", "hts_avls": "35000",
        "lstn_stcn": "20000000", "w52_hgpr_vrss_prpr_ctrt": "-12.3",
        "pgtr_ntby_qty": "-2139", "frgn_ntby_qty": "0",
        # 여기 없는 필드(예: 시가총액을 안 주는 종목)는 빈칸으로 남아야 한다
    }}


api_client.get_quote = fake_quote
fund_stocks = [{"code": "111111", "name": "가나"}, {"code": "222222", "name": "다라"},
               {"code": "BAD", "name": "실패종목"}]
r = fundamentals.collect(None, fund_stocks, verbose=False)
check("5) 조회 성공한 종목만 기록되고 실패는 건너뛴다",
      r["fetched"] == 2 and r["failed"] == 1 and r["added"] == 2, str(r))

rows = fundamentals.load_rows()
one = next(v for k, v in rows.items() if k[1] == "111111")
check("5b) PER/PBR/외국인지분율이 값으로 들어간다",
      one["per"] == "11.2" and one["pbr"] == "0.9" and one["hts_frgn_ehrt"] == "4.31",
      f"per={one['per']} pbr={one['pbr']} frgn={one['hts_frgn_ehrt']}")
# 종목별 수급 - 프로그램매매는 실제로 들어오는 유일한 흐름 지표라 꼭 기록돼야 한다
check("5b2) 프로그램매매 순매수가 기록된다 (음수 부호 유지)",
      one["pgtr_ntby_qty"] == "-2139", f"pgtr={one['pgtr_ntby_qty']!r}")
check("5b3) 외국인 순매수도 기록된다 (거의 0이지만, 계속 0인지 확인할 수 있게)",
      one["frgn_ntby_qty"] == "0", f"frgn={one['frgn_ntby_qty']!r}")

# 같은 날 다시 돌리면 API를 다시 부르지 않아야 한다 (하루 여러 번 실행돼도 호출 안 늘게)
quote_calls.clear()
r2 = fundamentals.collect(None, fund_stocks, verbose=False)
check("5c) 오늘 이미 기록된 종목은 다시 조회하지 않는다",
      "111111" not in quote_calls and r2["skipped"] == 2, f"호출={quote_calls} {r2}")
check("5d) 같은 날 다시 돌려도 행이 안 늘어난다", r2["added"] == 0, str(r2))

# 응답에 없는 필드는 빈칸으로 남아야 한다 (없는 값을 추정해 채우면 안 됨)
api_client.get_quote = lambda cfg, code: {"price": 1000.0, "raw": {"per": "5.0"}}
fundamentals.collect(None, [{"code": "333333", "name": "필드없음"}], verbose=False)
three = next(v for k, v in fundamentals.load_rows().items() if k[1] == "333333")
check("5e) 응답에 없는 필드는 빈칸으로 남는다 (임의로 채우지 않음)",
      three["pbr"] == "" and three["hts_avls"] == "" and three["per"] == "5.0",
      f"pbr={three['pbr']!r} hts_avls={three['hts_avls']!r}")

# 연도별 파일로 나뉘는지 + 컬럼 순서가 어긋나면 알리는지
check("5f) 연도별 파일로 저장된다",
      len(list(fundamentals.DATA_DIR.glob("fundamentals_*.csv"))) == 1,
      str(list(fundamentals.DATA_DIR.glob("fundamentals_*.csv"))))

import yearly_csv  # noqa: E402
check("5g) 지금 컬럼 순서와 파일 헤더가 일치한다",
      yearly_csv.check_header(fundamentals.DATA_DIR, "fundamentals",
                              fundamentals.FIELDNAMES) == [])
check("5h) 컬럼 순서가 다르면 어긋난 파일을 찾아낸다 (밀려 읽히는 사고 방지)",
      yearly_csv.check_header(fundamentals.DATA_DIR, "fundamentals",
                              ["date", "code", "엉뚱한컬럼"]) != [])

shutil.rmtree(tmpdir, ignore_errors=True)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
