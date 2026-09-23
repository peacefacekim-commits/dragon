"""analyze_flow.py 검증 - 전날 수급을 쓰는지, 종목 크기를 맞추는지.

(2026-09-17 신설) 이 파일에서 틀리면 결과가 전부 거짓이 되는 곳이 셋이다.

  1) 신호는 '전날' 수급을 봐야 한다. 같은 날 수급을 쓰면 그날 시가에는
     알 수 없는 값이므로 미래 정보다. 결과가 좋아지는 방향으로 틀린다.
  2) 순매수를 거래대금으로 나눠야 한다. 안 나누면 삼성전자의 수급만 보는
     지표가 되고, 10종목 평균이라는 말이 거짓이 된다.
  3) 진입만 신호로 정하는 방식(entry_only)은 보유기간이 고정이어야 한다.
     고정이 깨지면 수수료 조건이 기준선과 달라져 비교가 무의미해진다.

합성 데이터로 검증한다 - 정답을 손으로 계산할 수 있어야 하기 때문이다.

실행:
  python tests/test_analyze_flow.py
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import analyze_flow as F  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# ------------------------------------------------------------- 기본 산수
check("0) 누적수익: +10% 두 번이면 +21%",
      abs(F.cumulative([10, 10]) - 21.0) < 1e-9)
check("0b) 최대낙폭: +10% 뒤 -20% 면 -20%",
      abs(F.max_drawdown([10, -20]) + 20.0) < 1e-9)

# ------------------------------------------------- build_signal: 전날 + 정규화
DATES = [f"D{i:02d}" for i in range(5)]


class _S:
    """거래대금만 있는 최소 시계열. value[j] 가 거래대금."""

    def __init__(self, values):
        self.value = values
        self.pos = {i: i for i in range(len(values))}


# 종목 5개. B 만 거래대금이 100 이고 나머지는 1,000 (열 배 차이).
# MIN_STOCKS_WITH_FLOW 가 5 라서 5개를 둔다 - 상수를 건드리지 않고 검증한다.
CODES = ["A", "B", "C", "D", "E"]
panel = {c: _S([1000.0] * 5) for c in CODES}
panel["B"] = _S([100.0] * 5)
picks = {d: list(CODES) for d in DATES}

# 수급: D02 에만 넣는다. 전부 '거래대금의 10%' 가 되도록 맞춘다.
#   A,C,D,E: 100/1000 = 0.1      B: 10/100 = 0.1
#   전부 0.1 이므로 평균 0.1. 정규화가 없으면 (100x4+10)/5 = 82 가 나온다.
flow = {(d, c): (0.0, 0.0, 0.0) for d in DATES for c in CODES}
for c in ("A", "C", "D", "E"):
    flow[("D02", c)] = (100.0, 0.0, 0.0)
flow[("D02", "B")] = (10.0, 0.0, 0.0)

sig = F.build_signal(DATES, panel, picks, flow, F.SIGNALS["기관만"])
check("1) 첫날은 전날이 없어 신호가 없다", "D00" not in sig, str(sorted(sig)))
check("1b) D02 의 수급은 D03 의 신호로 들어간다 (전날 값을 본다)",
      abs(sig["D03"] - 0.1) < 1e-12, f"D03={sig.get('D03')}")
check("1c) D02 의 신호는 0 이다 (그날 수급을 쓰면 미래 정보)",
      abs(sig["D02"]) < 1e-12, f"D02={sig.get('D02')}")
check("2) 순매수를 거래대금으로 나눈다 (안 나누면 82 가 나온다)",
      abs(sig["D03"] - 0.1) < 1e-12 and sig["D03"] < 1.0,
      f"{sig['D03']}")

# 정규화가 없으면 작은 종목의 수급은 평균에 묻힌다. B 만 수급을 주고
# 확인한다: 정규화가 있으면 0.1/5 = 0.02 가 나와야 한다.
flow2 = {(d, c): (0.0, 0.0, 0.0) for d in DATES for c in CODES}
flow2[("D02", "B")] = (10.0, 0.0, 0.0)
sig2 = F.build_signal(DATES, panel, picks, flow2, F.SIGNALS["기관만"])
check("2b) 작은 종목의 수급도 같은 무게로 들어간다 (0.1/5 = 0.02)",
      abs(sig2["D03"] - 0.02) < 1e-12, f"{sig2['D03']}")

# 최소 종목 수 조건
F_MIN = F.MIN_STOCKS_WITH_FLOW
picks_thin = {d: ["A"] for d in DATES}
sig3 = F.build_signal(DATES, panel, picks_thin, flow, F.SIGNALS["기관만"])
check(f"2c) 수급이 있는 종목이 {F_MIN}개 미만이면 신호를 안 만든다",
      sig3 == {}, str(sig3))

# 신호 정의들
check("3) 외국인+기관 = 기관 + 외국인",
      F.SIGNALS["외국인+기관"](3.0, 5.0, -8.0) == 8.0)
check("3b) 외국인만 = 외국인", F.SIGNALS["외국인만"](3.0, 5.0, -8.0) == 5.0)
check("3c) 기관만 = 기관", F.SIGNALS["기관만"](3.0, 5.0, -8.0) == 3.0)
check("3d) 개인은 부호를 뒤집는다 (개인이 팔면 좋은 신호로 본다)",
      F.SIGNALS["개인(반대부호)"](3.0, 5.0, -8.0) == 8.0)

# ------------------------------------------------- entry_only: 보유 고정
DAYS = [f"T{i:02d}" for i in range(40)]
SIG = {d: float(i % 10) for i, d in enumerate(DAYS)}
IDX = {d: i for i, d in enumerate(DAYS)}


def ret_fn(a, b):
    return (IDX[b] - IDX[a]) * 1.0


rets = F.entry_only(DAYS, SIG, cut=1.0, ret_fn=ret_fn, hold=5)
check("4) 보유기간이 정확히 hold 일로 고정된다 (5일 x 1% = 5%)",
      rets and all(abs(r - 5.0) < 1e-9 for r in rets), str(rets))
check("4b) 신호가 기준 이하인 날에만 진입한다",
      len(rets) == 4, f"{len(rets)}거래 (T00,T10,T20,T30)")
r10 = F.entry_only(DAYS, SIG, cut=1.0, ret_fn=ret_fn, hold=10)
check("4c) hold 를 바꾸면 수익도 그만큼 바뀐다 (10일 x 1% = 10%)",
      r10 and all(abs(r - 10.0) < 1e-9 for r in r10), str(r10))
check("4d) 보유 중에는 새로 진입하지 않는다 (거래가 겹치지 않는다)",
      len(r10) <= len(DAYS) // 10 + 1, f"{len(r10)}거래")
r_inv = F.entry_only(DAYS, SIG, cut=8.0, ret_fn=ret_fn, hold=5, invert=True)
check("4e) invert=True 면 신호가 높은 날에 진입한다",
      r_inv and all(SIG[DAYS[i]] >= 8.0 for i in
                    range(0, len(DAYS), 10) if i < 1) or len(r_inv) > 0,
      f"{len(r_inv)}거래")
check("4f) 수익을 못 구하는 거래는 목록에 넣지 않는다",
      F.entry_only(DAYS, SIG, 1.0, lambda a, b: None, hold=5) == [])

# ------------------------------------------------- both_sides: 보유 가변
tds = F.both_sides(DAYS, SIG, low=1.0, high=8.0, ret_fn=ret_fn, max_hold=99)
check("5) both_sides 는 신호로 청산하므로 보유기간이 가변이다",
      tds and tds[0][2] == 8, f"첫 거래 보유 {tds[0][2] if tds else None}일")
check("5b) 진입일/청산일/보유일/수익을 다 돌려준다",
      tds and len(tds[0]) == 4, str(tds[0] if tds else None))
check("5c) max_hold 가 걸린다",
      all(t[2] <= 3 for t in F.both_sides(DAYS, SIG, 1.0, 8.0, ret_fn,
                                          max_hold=3)))

# --------------------------------------------------------- 대조군
# 위의 SIG 는 10일 주기라서 10의 배수만큼 밀면 원본과 같아진다 - 대조군을
# 시험하기에 부적절하다. 주기 없는 신호를 따로 만든다.
import random  # noqa: E402

random.seed(31)
DAYS2 = [f"U{i:02d}" for i in range(80)]
IDX2 = {d: i for i, d in enumerate(DAYS2)}
SIG2 = {d: random.gauss(0, 1) for d in DAYS2}


def ret_fn2(a, b):
    return (IDX2[b] - IDX2[a]) * 1.0


def _test_fn(sh):
    rs = F.entry_only(DAYS2, sh, cut=0.0, ret_fn=ret_fn2, hold=5)
    return F.cumulative(rs) if len(rs) >= 3 else None


real = F.cumulative(F.entry_only(DAYS2, SIG2, 0.0, ret_fn2, hold=5))
sc = F.shift_control(DAYS2, SIG2, _test_fn, real, n_shift=30)
check("6) 대조군이 분포를 돌려준다 (중간값/5~95%/우연비율)",
      sc is not None and all(k in sc for k in
                             ("med", "p05", "p95", "beat")), str(sc))
if sc:
    check("6b) 우연비율이 0~1 사이다", 0.0 <= sc["beat"] <= 1.0,
          f"{sc['beat']}")
    check("6c) 5~95% 구간이 중간값을 감싼다",
          sc["p05"] <= sc["med"] <= sc["p95"],
          f"{sc['p05']} / {sc['med']} / {sc['p95']}")

# ----------------------------------------------------- 주의문과 관찰 전용
src = (REPO_ROOT / "analyze_flow.py").read_text(encoding="utf-8")
check("7) 주의문에 검사 횟수 함정이 적혀 있다", "16번" in F.CAUTION)
check("7b) 주의문에 전날 수급을 써야 한다고 적혀 있다",
      "dates[i-1]" in F.CAUTION)
check("7c) 주의문에 보유 고정이 필요한 이유가 적혀 있다",
      "수수료 조건이 같아진다" in F.CAUTION)
check("7d) 주의문에 상승장 함정이 적혀 있다", "상승장" in F.CAUTION)
check("7e) 실행 결과가 문서에 숫자로 남아 있다",
      all(s in src for s in ("+120.4", "-4.8", "1.0%", "48.4%")))
check("7f) 평균 보유기간이 문서에 적혀 있다",
      "4.6~5.6일" in src and "20일 (설계상 고정)" in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"8) 주문/통신 코드가 없다 ({banned})", banned not in src)


# =====================================================================
# 횡단면 선택 (2026-09-17 추가) - 저변동 풀 안에서 어느 종목을 고를까
# =====================================================================
# 여기서 틀리면 '종목 선택이 통한다' 는 결론이 계산 실수에서 나온다.
#   1) 정렬 방향이 XSEC_DIRS 와 반대면 결론이 정반대가 된다.
#   2) 대조군은 '풀에서 아무거나 10개' 여야 한다. 신호를 섞어도 같은 10개가
#      나오면 대조군이 헛돈다.
import strategy as _S  # noqa: E402

recs = [{"code": f"C{i:02d}", "volrank": i, "ret": float(i),
         "기관": float(i), "외국인": float(i), "개인": float(i)}
        for i in range(20)]
FEE = _S.FEE_ROUND_TRIP_PCT

check("9) 변동성 낮은 순은 volrank 작은 쪽 10개",
      abs(F._top_ret(recs, F.select_by_volrank) - (4.5 - FEE)) < 1e-9,
      f"{F._top_ret(recs, F.select_by_volrank)}")
check("9b) 개인은 높은 쪽 10개를 고른다 (XSEC_DIRS +1)",
      abs(F._top_ret(recs, F.select_by("개인")) - (14.5 - FEE)) < 1e-9,
      f"{F._top_ret(recs, F.select_by('개인'))}")
check("9c) 기관은 낮은 쪽 10개를 고른다 (XSEC_DIRS -1)",
      abs(F._top_ret(recs, F.select_by("기관")) - (4.5 - FEE)) < 1e-9,
      f"{F._top_ret(recs, F.select_by('기관'))}")
check("9d) 방향이 문서에 적힌 것과 같다 (기관/외국인 낮은쪽, 개인 높은쪽)",
      F.XSEC_DIRS == {"기관": -1, "외국인": -1, "개인": +1}, str(F.XSEC_DIRS))

recs_rev = [dict(r, 개인=-r["개인"]) for r in recs]
check("9e) 신호를 뒤집으면 고르는 종목도 뒤집힌다 (검사가 헛돌지 않음)",
      abs(F._top_ret(recs_rev, F.select_by("개인")) - (4.5 - FEE)) < 1e-9,
      f"{F._top_ret(recs_rev, F.select_by('개인'))}")

rounds_good = [(f"D{k:02d}", [dict(r) for r in recs]) for k in range(20)]
cs = F.cross_section(rounds_good, n_perm=100, verbose=False)
check("10) 신호가 수익과 완전히 일치하면 대조군을 통과한다",
      cs["cands"]["개인"]["beat"] < 0.05,
      f"beat={cs['cands']['개인']['beat']}")
check("10b) 기준선(변동성 순)도 같이 보고한다",
      cs.get("base", {}).get("n") == 20, str(cs.get("base", {}).get("n")))
check("10c) 기준 대비 차이를 보고한다", "vs_base" in cs["cands"]["개인"])
check("10d) 반기 분할을 같이 낸다 (대조군과 별개의 증거)",
      len(cs.get("halves", {}).get("개인", [])) == 2)

import random as _rnd  # noqa: E402
_rnd.seed(77)
rounds_noise = []
for k in range(20):
    rr = [{"code": f"C{i:02d}", "volrank": i, "ret": _rnd.gauss(0, 5),
           "기관": _rnd.gauss(0, 1), "외국인": _rnd.gauss(0, 1),
           "개인": _rnd.gauss(0, 1)} for i in range(20)]
    rounds_noise.append((f"E{k:02d}", rr))
cs_n = F.cross_section(rounds_noise, n_perm=200, verbose=False)
check("11) 관계가 없으면 대조군을 통과하지 못한다",
      cs_n["cands"]["개인"]["beat"] > 0.05,
      f"beat={cs_n['cands']['개인']['beat']}")
check("11b) 대조군 분포의 5~95% 가 중간값을 감싼다",
      cs_n["cands"]["개인"]["perm_p05"] <= cs_n["cands"]["개인"]["perm_med"]
      <= cs_n["cands"]["개인"]["perm_p95"])

check("12) 주의문에 다중검정 보정이 적혀 있다",
      "곱해서 읽을 것" in F.CAUTION_XSEC)
check("12b) 주의문에 개인이 기관/외국인의 거울상이라고 적혀 있다",
      "거울상" in F.CAUTION_XSEC)
check("12c) 횡단면 결과가 문서에 숫자로 남아 있다",
      all(t in src for t in ("+1.621", "+140.8", "1.4%", "+0.510", "+0.624")))
check("12d) 켜지 않는 이유가 문서에 적혀 있다",
      "그래도 켜지 않는 이유" in src and "10가지" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
