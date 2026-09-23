"""strategy.py 검증 - 특히 미래 정보를 안 보는지.

(2026-09-16 신설) 이 파일에서 틀리면 결과가 전부 거짓이 되는 곳은 셋이다.

  1) 유니버스와 팩터 점수가 '진입일 전날 종가까지' 만 봐야 한다.
     진입일 당일 값을 쓰면 시가에 살 수 없는 정보로 고른 셈이 된다.
  2) 보유 중 데이터가 끊긴 종목(상장폐지/거래정지)을 조용히 빼면
     생존편향이 되살아난다. 반드시 세고 보고해야 한다.
  3) 나쁜날 게이트의 부호는 전반부에서만 정해야 한다. 후반부를 보고
     정하면 채점이 무의미해진다.

합성 데이터로 검증한다 - 정답을 손으로 계산할 수 있어야 하기 때문이다.

실행:
  python tests/test_strategy.py
"""
import csv
import pathlib
import shutil
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import strategy as S  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# ---------------------------------------------------------------- 합성 패널
# 200거래일, 종목 5개.
#   QUIET  : 매일 정확히 +0.1% (변동성 0) -> low_vol 이 반드시 1등
#   NOISY  : +3%/-3% 교대 (변동성 큼)
#   CHEAP  : 종가 1,000원 (가격 하한에 걸려 빠져야 함)
#   THIN   : 거래량 1 (거래대금 하위). 변동성은 QUIET 보다 크게 둔다 -
#            안 그러면 low_vol 1등이 QUIET 과 갈려서 테스트가 흔들린다.
#   GONE   : 100일째에 데이터가 끊긴다 (상장폐지 모사)
tmp = pathlib.Path(tempfile.mkdtemp()) / "data"
tmp.mkdir(parents=True)
S.DATA_DIR = tmp

DAYS = [f"2026{m:02d}{d:02d}" for m in range(1, 11) for d in range(1, 21)]
rows = []


def add(code, i, o, c, vol):
    rows.append({"date": DAYS[i], "code": code, "name": code,
                 "open": o, "high": max(o, c), "low": min(o, c),
                 "close": c, "volume": vol})


for i in range(len(DAYS)):
    q = 10000 * (1.001 ** i)
    add("QUIET", i, q, q * 1.001, 100000)
    n = 10000 * (1.03 if i % 2 else 0.97) ** 1
    add("NOISY", i, 10000, n, 100000)
    add("CHEAP", i, 1000, 1001, 100000)
    add("THIN", i, 10000, 10000 * (1.005 if i % 3 else 0.995), 1)
    if i < 100:
        add("GONE", i, 10000, 10000 - i * 50, 100000)

with open(tmp / "krx_panel_2026.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, ["date", "code", "name", "open", "high", "low",
                            "close", "volume"])
    w.writeheader()
    w.writerows(rows)

dates, panel = S.load_panel(verbose=False)
check("0) 패널이 읽힌다", len(panel) == 5 and len(dates) == 200,
      f"{len(panel)}종목 {len(dates)}일")

# ---------------------------------------------------------------- 1) 미래 차단
# 진입일 di 의 값을 바꿔도 점수가 안 바뀌어야 한다 (전날까지만 보므로).
DI = 150
before_u = S.universe_at(panel, DI, size=5, min_price=0)
before_f = S.factor_score(panel, "QUIET", DI, "low_vol")

s = panel["QUIET"]
j = s.pos[DI]
orig_c, orig_v = s.close[j], s.value[j]
s.close[j] = 1.0           # 진입일 종가를 말도 안 되는 값으로
s.value[j] = 0.0           # 진입일 거래대금도 0 으로
after_u = S.universe_at(panel, DI, size=5, min_price=0)
after_f = S.factor_score(panel, "QUIET", DI, "low_vol")
s.close[j], s.value[j] = orig_c, orig_v

check("1) 진입일 종가를 바꿔도 팩터 점수가 안 바뀐다 (전날까지만 봄)",
      before_f == after_f, f"{before_f} vs {after_f}")
check("1b) 진입일 거래대금을 바꿔도 유니버스가 안 바뀐다",
      before_u == after_u, f"{before_u} vs {after_u}")

# 전날 값을 바꾸면 반드시 바뀌어야 한다 (테스트가 헛돌지 않게 하는 확인)
jp = s.pos[DI - 1]
orig = s.close[jp]
s.close[jp] = orig * 1.5
changed = S.factor_score(panel, "QUIET", DI, "low_vol")
s.close[jp] = orig
check("1c) 전날 종가를 바꾸면 점수가 바뀐다 (1번이 헛돌지 않음을 확인)",
      changed != before_f, f"{before_f} vs {changed}")

# ---------------------------------------------------------------- 2) 필터
check("2) 가격 하한이 5,000원 미만을 뺀다 (규칙 3)",
      "CHEAP" not in S.universe_at(panel, DI, size=5, min_price=5000),
      str(S.universe_at(panel, DI, size=5, min_price=5000)))
check("2b) 하한을 0 으로 내리면 다시 들어온다",
      "CHEAP" in S.universe_at(panel, DI, size=5, min_price=0))
check("2c) 거래대금 하위는 유니버스를 좁히면 빠진다",
      "THIN" not in S.universe_at(panel, DI, size=3, min_price=0),
      str(S.universe_at(panel, DI, size=3, min_price=0)))

# ---------------------------------------------------------------- 3) 팩터 방향
sc_q = S.factor_score(panel, "QUIET", DI, "low_vol")
sc_n = S.factor_score(panel, "NOISY", DI, "low_vol")
check("3) low_vol 은 변동성이 낮은 쪽에 높은 점수", sc_q > sc_n,
      f"QUIET {sc_q:.6f} > NOISY {sc_n:.6f}")
check("3b) low_vol 점수는 음수 (표준편차에 마이너스)", sc_q <= 0, f"{sc_q}")
try:
    S.factor_score(panel, "QUIET", DI, "없는팩터")
    raised = False
except ValueError:
    raised = True
check("3c) 모르는 팩터 이름은 조용히 넘어가지 않고 예외", raised)

# ---------------------------------------------------------------- 4) 수수료
r, cut = S.trade_return(panel, "QUIET", 100, 120)
expect = (panel["QUIET"].open[panel["QUIET"].pos[120]]
          / panel["QUIET"].open[panel["QUIET"].pos[100]] - 1) * 100
check("4) 수익률은 시가->시가 (갭을 안 먹는 보수적 가정)",
      abs(r - expect) < 1e-9 and not cut, f"{r} vs {expect}")

res = S.run(dates, panel, factor="low_vol", hold_days=20, top_n=1,
            universe_size=5, min_price=5000, start_di=70,
            min_stocks=1, verbose=False)
res0 = S.run(dates, panel, factor="low_vol", hold_days=20, top_n=1,
             universe_size=5, min_price=5000, start_di=70, fee_pct=0.0,
             min_stocks=1, verbose=False)
check("4b) 회차 수익에서 수수료가 정확히 빠진다",
      abs((res0["mean"] - res["mean"]) - S.FEE_ROUND_TRIP_PCT) < 1e-9,
      f"{res0['mean']} - {res['mean']}")
check("4c) 변동성 0 인 종목만 고르면 회차가 다 양수여야 한다",
      res["win"] == 1.0, f"승률 {res['win']}")

# ---------------------------------------------------------------- 5) 끊김
# GONE 은 100일째에 끊긴다. 90일 진입 -> 110일 청산이면 끊김 처리.
r, cut = S.trade_return(panel, "GONE", 90, 110)
check("5) 보유 중 끊긴 종목은 마지막 종가로 청산하고 끊김으로 표시", cut,
      f"ret={r} cut={cut}")
r50, cut50 = S.trade_return(panel, "GONE", 90, 110, delisting_loss=50)
check("5b) --delisting-loss 를 주면 그 손실률로 처리",
      cut50 and abs(r50 + 50) < 1e-9, f"{r50}")
check("5c) 끊김은 조용히 빠지지 않고 세어진다 (생존편향 방지)",
      S.run(dates, panel, factor="low_vol", hold_days=20, top_n=5,
            universe_size=5, min_price=0, start_di=85, end_di=110,
            min_stocks=1, verbose=False)["delisted"] > 0)

# ---------------------------------------------------------------- 6) 기준선
# 'all' 은 유니버스 전체를 동일가중으로 사야 한다. 상위 N 을 자르면 점수가
# 전부 같아서 종목코드 순으로 잘리고, 기준선이 되지 못한다 (실제로 있던 버그).
r_all = S.run(dates, panel, factor="all", hold_days=20, top_n=1,
              universe_size=5, min_price=0, start_di=70, min_stocks=1,
              verbose=False)
r_one = S.run(dates, panel, factor="low_vol", hold_days=20, top_n=1,
              universe_size=5, min_price=0, start_di=70, min_stocks=1,
              verbose=False)
check("6) 'all' 은 top_n 을 무시하고 유니버스 전체를 산다",
      r_all["rounds"][0]["n"] > r_one["rounds"][0]["n"],
      f"all {r_all['rounds'][0]['n']}종목 vs low_vol {r_one['rounds'][0]['n']}종목")

# ---------------------------------------------------------------- 7) 게이트
# 전반부만 보고 부호를 정하는지. 후반부에서만 상관이 있는 가짜 지표를 넣고,
# 게이트가 그걸 학습하지 못해야 정상이다.
day_vals = {}
outcome = {}
for i, d in enumerate(DAYS):
    # 전반부(0~99)는 지표와 결과가 반대, 후반부(100~)는 같은 방향
    x = 1.0 if i % 2 else -1.0
    day_vals[d] = {"fake": x}
    outcome[d] = (-x if i < 100 else x)
train = DAYS[:100]
g = S.build_day_gate(day_vals, DAYS, {d: outcome[d] for d in train})
check("7) 전반부 표본이 50개 이상이면 게이트가 만들어진다", g is not None)
if g:
    check("7b) 부호를 전반부에서만 정한다 (전반부 상관이 음수이므로 -)",
          g["signs"]["fake"] == -1.0, str(g["signs"]))
g_small = S.build_day_gate(day_vals, DAYS, {d: outcome[d] for d in DAYS[:30]})
check("7c) 전반부 표본이 모자라면 게이트를 안 만든다 (None)",
      g_small is None)

# ---------------------------------------------------------------- 8) 관찰 전용
src = (REPO_ROOT / "strategy.py").read_text(encoding="utf-8")
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"8) 주문/통신 코드가 없다 ({banned})", banned not in src)
check("8b) 살아남은 규칙 여섯 개가 문서에 적혀 있다",
      all(k in src for k in ("5,000원", "고정 비중", "개입")))
check("8c) 주의문에 표본 한계가 적혀 있다", "60" in S.CAUTION)

shutil.rmtree(tmp.parent, ignore_errors=True)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
