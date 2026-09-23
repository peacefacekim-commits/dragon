"""paper_trade.py 검증 - 앞검증이 앞검증으로 남는지.

(2026-09-17 신설) 이 파일에서 틀리면 앞검증이 조용히 백테스트로 바뀐다.
그게 가장 위험한 실패 방식이다 - 결과가 나오는데 그 결과가 거짓이 된다.

지켜야 하는 것 다섯 개.

  1) 얼린 게이트를 실수로 덮어쓰지 않는다. 덮어쓰면 '기준을 먼저 정했다'
     는 전제가 무너진다.
  2) 게이트 점수는 얼린 계수만 쓴다. 새 데이터로 계수가 다시 계산되면
     안 된다.
  3) 게이트가 '쉼' 이라 한 회차도 수익률을 채운다. 안 채우면 "쉰 게
     맞았나" 를 영영 확인할 수 없다.
  4) 채점은 얼린 날 이후에 기록된 것만 센다. 학습에 쓴 구간이 채점에
     섞이면 상관이 부풀려진다.
  5) 보유기간이 안 지난 회차는 청산하지 않는다 (미래 정보 금지).

합성 데이터로 검증한다 - 정답을 손으로 계산할 수 있어야 하기 때문이다.

실행:
  python tests/test_paper_trade.py
"""
import csv
import json
import pathlib
import shutil
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import market_indicators as mi  # noqa: E402
import paper_trade as P  # noqa: E402
import strategy as S  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# ---------------------------------------------------------------- 합성 데이터
# 300거래일, 종목 12개. 전부 매일 +0.1% 로 올라가되 변동성만 다르게 둔다.
# 정답을 손으로 계산할 수 있어야 하므로 시가는 종가와 같게 둔다.
tmp = pathlib.Path(tempfile.mkdtemp()) / "data"
tmp.mkdir(parents=True)
S.DATA_DIR = tmp
P.DATA_DIR = tmp
P.GATE_PATH = tmp / "gate_frozen.json"

DAYS = [f"2026{m:02d}{d:02d}" for m in range(1, 13) for d in range(1, 26)][:300]
prows = []
for i, d in enumerate(DAYS):
    for s in range(12):
        # s 번째 종목의 변동성을 s 에 비례하게 (0번이 가장 저변동)
        wig = (1 + s * 0.002) if i % 2 else (1 - s * 0.002)
        px = 10000 * (1.001 ** i) * wig
        prows.append({"date": d, "code": f"S{s:03d}", "name": f"S{s:03d}",
                      "open": px, "high": px, "low": px, "close": px,
                      "volume": 100000 + s})

with open(tmp / "krx_panel_2026.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, ["date", "code", "name", "open", "high", "low",
                            "close", "volume"])
    w.writeheader()
    w.writerows(prows)

# 지표: 하나만 결과와 상관이 있게 두고 나머지는 상수에 가깝게 둔다.
irows = []
for i, d in enumerate(DAYS):
    row = {"date": d}
    for k in mi.PREDICTOR_FIELDS:
        row[k] = 1.0 if i % 2 else -1.0
    # result_c2c 는 '그날' 결과다. 전날 것을 끌어와야 오늘 쓸 수 있는 값이
    # 되므로, 날짜마다 다른 값을 넣어 어느 날 것을 가져오는지 확인한다.
    row["result_c2c"] = float(i)
    for k in ("result_o2c", "result_breadth"):
        row[k] = 0.0
    irows.append(row)
with open(tmp / "market_indicators_2026.csv", "w", encoding="utf-8",
          newline="") as fh:
    w = csv.DictWriter(fh, mi.FIELDS)
    w.writeheader()
    w.writerows(irows)

P.HOLDS = (5,)
P.TOP_N = 3
S.UNIVERSE_SIZE = 12
S.MIN_PRICE = 0
P.FIELDS = [f for f in P.FIELDS]   # 원본을 건드리지 않게 복사

dates, panel = S.load_panel(verbose=False)
check("0) 합성 패널이 읽힌다", len(panel) == 12 and len(dates) == 300,
      f"{len(panel)}종목 {len(dates)}일")

# ------------------------------------------------------- 1) 얼리기와 덮어쓰기
g = P.freeze()
check("1) 게이트가 얼려진다", g is not None and P.GATE_PATH.exists())
before = P.GATE_PATH.read_text(encoding="utf-8")
g2 = P.freeze()
check("1b) 두 번째 --freeze 는 거부된다 (앞검증 전제 보호)", g2 is None)
check("1c) 거부됐을 때 파일이 그대로다",
      P.GATE_PATH.read_text(encoding="utf-8") == before)
g3 = P.freeze(force=True)
check("1d) --force 를 주면 덮어쓴다", g3 is not None)
saved = json.loads(P.GATE_PATH.read_text(encoding="utf-8"))
check("1e) 얼린 파일에 학습 구간과 표본 수가 남는다",
      saved.get("train_from") and saved.get("train_n") and
      saved.get("train_n_independent") is not None,
      f"{saved.get('train_from')} ~ {saved.get('train_to')} n={saved.get('train_n')}")
check("1f) 얼린 파일에 쉼 기준값이 남는다 (나중에 바뀌면 안 되므로)",
      "skip_below" in saved and "skip_pct" in saved)

# --------------------------------------------- 2) 점수는 얼린 계수만 쓴다
gate = P.load_gate()
vals = {k: 1.0 for k in gate["keys"]}
sc_a = P.gate_score(gate, vals)
# 패널을 크게 흔들어도 점수는 그대로여야 한다 (계수가 파일에 얼려 있으므로)
s0 = panel["S000"]
s0.close[-1] = 1.0
sc_b = P.gate_score(P.load_gate(), vals)
check("2) 새 데이터가 들어와도 게이트 점수가 안 바뀐다 (계수가 얼려 있음)",
      sc_a == sc_b, f"{sc_a} vs {sc_b}")
check("2b) 지표 값이 다르면 점수는 달라진다 (2번이 헛돌지 않음)",
      P.gate_score(gate, {k: -1.0 for k in gate["keys"]}) != sc_a)
check("2c) 지표가 하나라도 비면 점수는 None",
      P.gate_score(gate, {**vals, gate["keys"][0]: None}) is None)

# ------------------------------------------------------------------ 3) 기록
added = P.record(verbose=False)
check("3) 마지막 거래일 회차가 기록된다", added == 1, f"{added}개")
again = P.record(verbose=False)
check("3b) 같은 날을 두 번 기록하지 않는다", again == 0, f"{again}개")

rows = list(csv.DictReader(open(tmp / "paper_trades_2026.csv",
                                encoding="utf-8-sig")))
check("3c) 기록된 행이 1개", len(rows) == 1, str(len(rows)))
r0 = rows[0]
check("3d) 진입일이 패널 마지막 날", r0["date"] == dates[-1], r0["date"])
check("3e) 종목 3개가 기록된다", len(r0["picks"].split(";")) == 3, r0["picks"])
check("3f) 저변동 종목이 뽑힌다 (S000 이 가장 저변동)",
      "S000" in r0["picks"], r0["picks"])
check("3g) 판정이 투자/쉼 중 하나로 남는다",
      r0["gate_verdict"] in ("투자", "쉼"), r0["gate_verdict"])
check("3h) 그날 지표가 같이 남는다 (나중에 재분석용)",
      all(r0[k] != "" for k in mi.PREDICTOR_FIELDS))
check("3i) 아직 청산 전이라 수익률이 비어 있다", r0["realized_pct"] == "")

# ----------------------------------- 3k) 전날 등락과 '전날 하락이면 쉼' 규칙
# result_c2c 에 날짜 순번(i)을 넣었으므로, 마지막 날(i=299)의 prev_c2c 는
# 그 전날 값인 298 이어야 한다. 오늘 값(299)을 쓰면 미래 정보다.
pc = P.load_prev_c2c()
check("3k) 전날 등락은 '전날' 값을 가져온다 (오늘 값이 아니다)",
      pc[DAYS[299]] == 298.0, f"{pc.get(DAYS[299])}")
check("3l) 첫날은 전날이 없으므로 값이 없다", DAYS[0] not in pc)
check("3m) 기록된 prev_c2c 가 전날 값과 같다",
      float(r0["prev_c2c"]) == 298.0, r0["prev_c2c"])
check("3n) 전날이 상승(+298)이면 규칙 판정은 '투자'",
      r0["rule_prevdown"] == "투자", r0["rule_prevdown"])
# 부호를 뒤집으면 판정도 뒤집혀야 한다 (위 검사가 헛돌지 않게)
_saved = P.load_prev_c2c
P.load_prev_c2c = lambda: {DAYS[299]: -1.0}
(tmp / "paper_trades_2026.csv").unlink()
P.record(verbose=False)
r_neg = list(csv.DictReader(open(tmp / "paper_trades_2026.csv",
                                 encoding="utf-8-sig")))[0]
P.load_prev_c2c = _saved
check("3o) 전날이 하락이면 규칙 판정이 '쉼' 으로 바뀐다",
      r_neg["rule_prevdown"] == "쉼", r_neg["rule_prevdown"])
check("3p) 두 규칙의 판정이 서로 독립적으로 기록된다",
      r_neg["gate_verdict"] in ("투자", "쉼")
      and r_neg["rule_prevdown"] == "쉼",
      f"게이트 {r_neg['gate_verdict']} / 전날규칙 {r_neg['rule_prevdown']}")
check("3q) 새 컬럼이 맨 끝에 붙어 있다 (기존 행이 밀리지 않게)",
      P.FIELDS[-2:] == ["prev_c2c", "rule_prevdown"], str(P.FIELDS[-2:]))

# 컬럼 순서 규칙: 새 컬럼은 맨 끝에 붙여야 한다
import yearly_csv  # noqa: E402
check("3j) 저장된 헤더가 코드의 컬럼 순서와 같다 (가운데 끼워넣기 사고 방지)",
      yearly_csv.check_header(tmp, P.PREFIX, P.FIELDS) == [],
      str(yearly_csv.check_header(tmp, P.PREFIX, P.FIELDS)))

# ------------------------------------------------------------------ 4) 청산
n = P.settle(verbose=False)
check("4) 보유기간이 안 지난 회차는 청산하지 않는다", n == 0, f"{n}개")

# 보유기간이 지난 회차를 손으로 넣고 청산시킨다.
ENTRY_I = 200
entry, picks = dates[ENTRY_I], ["S000", "S001", "S002"]
allrows = yearly_csv.load_rows(tmp, P.PREFIX, P.KEY_FIELDS)
row = {f: "" for f in P.FIELDS}
row.update({"date": entry, "hold_days": "5", "picks": ";".join(picks),
            "gate_score": "-9.0000", "gate_verdict": "쉼"})
for k in mi.PREDICTOR_FIELDS:
    row[k] = "1"
allrows[(entry, "5")] = row
yearly_csv.write_years(tmp, P.PREFIX, P.FIELDS, allrows, {entry[:4]})

n = P.settle(verbose=False)
check("4b) 보유기간이 지난 회차는 청산된다", n == 1, f"{n}개")

done = {(r["date"], r["hold_days"]): r for r in csv.DictReader(
    open(tmp / "paper_trades_2026.csv", encoding="utf-8-sig"))}
got = done[(entry, "5")]
check("4c) 청산일이 진입일 + 보유일 로 채워진다",
      got["exit_date"] == dates[ENTRY_I + 5],
      f"{got['exit_date']} vs {dates[ENTRY_I + 5]}")

expect = []
for c in picks:
    s = panel[c]
    expect.append((s.open[s.pos[ENTRY_I + 5]] / s.open[s.pos[ENTRY_I]] - 1) * 100)
expect = sum(expect) / len(expect) - S.FEE_ROUND_TRIP_PCT
# CSV 에는 소수 넷째 자리까지 저장하므로 그 자리 이내로만 비교한다.
check("4d) 수익률이 시가->시가 평균 - 수수료 와 같다 (저장 자릿수 이내)",
      abs(float(got["realized_pct"]) - expect) < 1e-4,
      f"{got['realized_pct']} vs {expect:.6f}")
check("4e) 게이트가 '쉼' 이라 한 회차도 수익률이 채워진다 (쉰 판단을 채점하려면 필수)",
      got["gate_verdict"] == "쉼" and got["realized_pct"] != "",
      f"{got['gate_verdict']} / {got['realized_pct']}")
check("4f) 청산 시각이 기록된다", got["settled_at"] != "")

n2 = P.settle(verbose=False)
check("4g) 이미 청산된 회차를 다시 건드리지 않는다", n2 == 0, f"{n2}개")

# ------------------------------------------------------------------ 5) 채점
# 위에서 넣은 회차는 진입일이 얼린 날보다 과거다 -> 채점에서 빠져야 한다.
out = P.score(verbose=False)
check("5) 얼린 날 이전에 기록된 회차는 채점에 안 들어간다 (앞검증 유지)",
      out.get(5) is None or out[5]["n"] == 0,
      str(out.get(5)))

src = (REPO_ROOT / "paper_trade.py").read_text(encoding="utf-8")
check("5b) 채점은 얼린 날 이후만 센다는 것이 코드에 있다", "frozen_day" in src)
check("5c) 주의문에 표본이 얼마나 필요한지 적혀 있다",
      "13년" in P.CAUTION or "167" in P.CAUTION)
check("5d) 겹치는 회차라는 한계가 주의문에 적혀 있다", "독립 표본" in P.CAUTION)

# ------------------------------------------------------------- 6) 관찰 전용
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"6) 주문/통신 코드가 없다 ({banned})", banned not in src)

shutil.rmtree(tmp.parent, ignore_errors=True)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
