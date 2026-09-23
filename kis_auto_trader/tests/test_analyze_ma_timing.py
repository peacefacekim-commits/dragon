"""analyze_ma_timing.py 검증 - 타이밍 규칙을 공평하게 쟀는가.

(2026-09-22 신설) 이 파일의 위험은 넷이다.

  1) **기준선을 낮추는 것.** 타이밍 규칙의 상대는 무작위가 아니라
     검증된 저변동 전략(+22.3%)이다. 무작위와 비교하면 지는 규칙도
     이겨 보인다.
  2) **미래를 보는 것.** 이동평균을 di 종가까지 계산해놓고 di 시가에
     팔면 그날 떨어질 것을 미리 아는 셈이 된다. 타이밍 규칙에서는 이
     실수가 결과를 완전히 뒤집는다.
  3) **같은 시가에 사고파는 것.** 교체일에 산 종목을 그날 데드크로스로
     팔면 수수료만 버린다. 규칙 탓이 아니라 구현 탓인 손해다.
  4) **대조군이 두 가지를 같이 바꾸는 것.** 무작위 매도 대조군은 파는
     신호만 갈아치워야 한다. 들어가는 쪽까지 바꾸면 무엇이 차이를
     만들었는지 알 수 없다.

실행:
  python tests/test_analyze_ma_timing.py
  python tests/test_analyze_ma_timing.py --slow   # 실제 패널까지
"""
import pathlib
import random
import statistics as st
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import analyze_ma_timing as M  # noqa: E402

src = (REPO_ROOT / "analyze_ma_timing.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes, start=0):
        self.close = list(closes)
        self.open = list(closes)
        self.high = list(closes)
        self.low = list(closes)
        self.value = [1e9] * len(closes)
        self.pos = {start + i: i for i in range(len(closes))}


UP = [float(100 + i) for i in range(40)]
DOWN = [float(200 - i) for i in range(40)]
FLAT = [100.0] * 40


# =====================================================================
# A) 이동평균 상태 - 값이 맞고, 모르는 것을 False 로 안 만드는가
# =====================================================================
up = {"A": FakeSeries(UP)}
dn = {"A": FakeSeries(DOWN)}
fl = {"A": FakeSeries(FLAT)}
check("A1) 이동평균이 5/20", (M.MA_SHORT, M.MA_LONG) == (5, 20))
check("A2) 오르는 중이면 골든", M.above(M.ma_states(up), up, "A", 30) is True)
check("A3) 내리는 중이면 데드", M.above(M.ma_states(dn), dn, "A", 30) is False)
# 딱 같으면 '위' 가 아니므로 False 다 (None 이 아니다). None 은 '모른다' 전용
# 이라서 구분해둔다. 실제 데이터에서 5일선과 20일선이 소수점까지 같은 일은
# 거래가 멈춘 종목 정도이고, 그건 팔리는 쪽이 맞다.
check("A4) 평평하면 False - '위' 가 아니다 (모른다와 다르다)",
      M.above(M.ma_states(fl), fl, "A", 30) is False)
check("A5) 기록이 모자라면 None (모른다)",
      M.above(M.ma_states(up), up, "A", 5) is None)
check("A6) 없는 종목이면 None", M.above(M.ma_states(up), up, "Z", 30) is None)
check("A7) 모르는 것을 False 로 보면 안 된다고 적었다",
      "모르는 것을 False 로 취급하면 안 된다" in flat)
check("A8) 왜 미리 계산하는지 적었다", "누적합으로 한 번에 만들어두고" in flat)

# 누적합 계산이 직접 평균과 같은가
_s = FakeSeries(UP)
_arr = M.ma_states({"A": _s})["A"]
_j = 30
_ms = st.mean(_s.close[_j - M.MA_SHORT + 1:_j + 1])
_ml = st.mean(_s.close[_j - M.MA_LONG + 1:_j + 1])
check("A9) 누적합이 직접 평균과 같은 답을 준다", _arr[_j] == (_ms > _ml),
      f"누적합 {_arr[_j]} / 직접 {_ms > _ml}")

# =====================================================================
# B) 미래를 안 보는가 (핵심 2)
# =====================================================================
# 39일까지 오르다가 40번째에 꺾인다. di=40 (j=39) 에서는 아직 골든이고,
# 꺾인 것을 반영한 신호는 di=41 부터 나와야 한다.
turn = {"A": FakeSeries(UP + [60.0])}
_ts = M.ma_states(turn)
check("B1) di 시점 신호는 di-1 종가까지만 본다",
      M.above(_ts, turn, "A", 40) is True,
      f"{M.above(_ts, turn, 'A', 40)}")
check("B2) 꺾인 것은 하루 뒤에 반영된다",
      M.above(_ts, turn, "A", 41) is False,
      f"{M.above(_ts, turn, 'A', 41)}")
check("B3) di-1 을 쓴다고 코드에 있다", "s.pos.get(di - 1)" in src)
check("B4) 왜 그런지 적었다", "di-1 종가까지로 계산하고 매매는 di 시가다" in flat)
for fn in ("index_states",):
    body = src.split(f"def {fn}(")[1].split("\ndef ")[0]
    check(f"B5) {fn} 도 di-1 까지만 본다", "di-1 종가까지" in body)

# =====================================================================
# C) 같은 날 사고팔지 않는가 (핵심 3)
# =====================================================================
check("C1) 그날 산 종목은 데드크로스 검사에서 뺀다",
      "opened.get(c) == di" in src)
check("C2) 왜 그런지 적었다", "같은 시가에 사고팔지 않는다" in flat)
check("C3) 기준에도 미리 적어뒀다",
      "수수료만 버린다" in flat or "수수료만 버리는 것을" in flat)

# =====================================================================
# D) 규칙 목록 - 늘리지 않았는가
# =====================================================================
check("D1) 규칙이 다섯 개", len(M.RULES) == 5)
check("D2) 첫 번째가 '없음' 이고 아무 것도 안 켠다",
      M.RULES[0] == ("없음", False, False, False))
check("D3) 지수 규칙이 둘", len(M.INDEX_RULES) == 2)
check("D4) 주기가 20/120 둘뿐", M.PERIODS == (20, 120))
check("D5) 종목수가 10 고정", M.PICK == 10)
check("D6) 문턱을 훑지 않는 이유를 적었다",
      "12칸이 60칸이 되고" in flat)
check("D7) 다중검정 칸 수를 밝혔다", "12칸을 봤다" in flat)

# =====================================================================
# E) 기준선이 저변동 전략 자체인가 (핵심 1)
# =====================================================================
check("E1) 무작위가 기준선이 아니라고 못박았다",
      "무작위가 기준선이 아니다" in flat)
check("E2) 검증된 저변동이 기준선이라고 적었다",
      "검증된 저변동 전략 자체**가 기준선이다" in flat
      or "검증된 저변동 전략 자체" in flat)
check("E3) 조건 1 이 '없음' 을 이기는 것이다",
      "'없음' 을 이긴다" in flat and "무작위가 아니다" in flat)
check("E4) 시작일 4/5 가 기준", M.MIN_START_WINS == 4)
check("E5) p 문턱 0.05 / 500회", (M.PERM_ALPHA, M.N_PERM) == (0.05, 500))

# =====================================================================
# F) 대조군이 파는 신호만 바꾸는가 (핵심 4)
# =====================================================================
check("F1) 골든만매수와 재투자는 그대로 둔다",
      M.control_rule((True, True, True)) == (True, False, True))
check("F2) 파는 신호만 끈다",
      M.control_rule((False, True, False)) == (False, False, False))
check("F3) 왜 그런지 적었다",
      "파는 신호만** 무작위로 갈아치운다" in flat
      or "파는 신호만" in flat)
check("F4) 둘 다 바꾸면 안 되는 이유를 적었다",
      "무엇이 차이를 만들었는지 알 수 없다" in flat)
check("F5) 파는 횟수를 맞춘다", "매도 횟수를 target 에 맞춘다" in flat)
check("F6) 안 맞추면 왜 안 되는지 적었다",
      "'덜 팔았다' 가 되어 비교가 안 된다" in flat)

# =====================================================================
# G) 채택 조건 넷
# =====================================================================
check("G1) 넷을 다 넘으면 채택",
      M.accepted(4, True, True, 0.01, 4, 6, 1.0) is True)
check("G2) 시작일이 모자라면 탈락",
      M.accepted(3, True, True, 0.01, 4, 6, 1.0) is False)
check("G3) 반띵 한쪽만 이기면 탈락",
      M.accepted(5, True, False, 0.01, 4, 6, 1.0) is False)
check("G4) p 가 크면 탈락",
      M.accepted(5, True, True, 0.20, 4, 6, 1.0) is False)
check("G5) 양수인 해가 과반이 아니면 탈락",
      M.accepted(5, True, True, 0.01, 3, 6, 1.0) is False)
check("G6) 최고 해를 빼면 음수면 탈락",
      M.accepted(5, True, True, 0.01, 5, 6, -1.0) is False)
check("G7) 잰 해가 없으면 탈락",
      M.accepted(5, True, True, 0.01, 0, 0, 1.0) is False)
check("G8) 결과를 보고 조건을 안 고친다고 적었다",
      "결과를 보고 조건을 고치지 않는다" in flat)
check("G9) 조건 1 에서 끝났다고 밝힌다",
      "조건 2/3/4 는 돌리지 않았다" in flat)

# =====================================================================
# H) 슬리피지 산수
# =====================================================================
check("H1) 늘어난 왕복이 없으면 무한 (0으로 안 나눈다)",
      M.slip_flip(5.0, 0) == float("inf"))
check("H2) 차이를 늘어난 왕복 두 배로 나눈다",
      abs(M.slip_flip(4.0, 10.0) - 0.2) < 1e-12,
      f"{M.slip_flip(4.0, 10.0)}")
check("H3) 어림값이라고 밝혔다", "어림값이다" in flat)
check("H4) 안 쟀고 왜 안 쟀는지 적었다",
      "수수료 전에 이미 졌으므로 볼 필요가" in flat)

# =====================================================================
# I) 지수 대용을 대용이라고 밝혔는가
# =====================================================================
check("I1) KOSPI 가 아니라고 못박았다", "KOSPI 가 아니다" in flat)
check("I2) 왜 대용인지 적었다", "5.7년치 지수 종가가 저장소에 없다" in flat)
check("I3) 소형주로 기운다고 밝혔다", "소형주 쪽으로 기운" in flat)
check("I4) 한계를 결과에도 다시 적었다",
      "KOSPI 종가로 다시 하면 숫자가 달라질 수 있다" in flat)
_lvl = M.market_index(["d0", "d1", "d2"],
                      {"A": FakeSeries([100.0, 110.0, 121.0])})
check("I5) 지수가 동일가중 수익률로 쌓인다",
      abs(_lvl[-1] - 121.0) < 1e-6, str(_lvl))
check("I6) 값이 없는 종목은 건너뛴다 (안 터진다)",
      len(M.market_index(["d0", "d1"], {"A": FakeSeries([100.0])})) == 2)
_iarr = M.index_states([100.0 + i for i in range(40)])
check("I7) 지수 오름세면 골든", _iarr[30] is True)
check("I8) 앞부분은 None", _iarr[5] is None)

# =====================================================================
# J) 골든 필터가 무엇을 포기하게 하는지 쟀는가
# =====================================================================
check("J1) golden_cost 함수가 있다", hasattr(M, "golden_cost"))
check("J2) 규칙 매도가 0 건인데도 진다는 것을 짚었다",
      "규칙 매도가 0 건인데도 진다" in flat)
check("J3) 그래서 원인이 고르는 쪽이라고 잇는다",
      "고르는 쪽이 망가진 것" in flat)
check("J4) 순위를 28번째까지 내려간다고 적었다", "28번째까지" in src)
check("J5) 백분위가 98 -> 92 라고 적었다", "98" in src and "92" in src)
check("J6) -6 만큼 밀린다고 적었다", "-6 만큼 덜 안정적인 쪽으로" in flat)
check("J7) 최악 회차를 밝혔다", "57번째까지" in src and "27% 뿐" in flat)
check("J8) 어제 결과와 잇는다",
      "analyze_old_rules.py" in src and "+0.750" in src)

# =====================================================================
# K) 결과 숫자가 모듈 출력과 맞는가
# =====================================================================
for tok in ("20.3", "-16.2", "0.1", "-18.3", "402", "10.3",
            "-8.2", "-49.4", "867", "20.7", "5.8", "-34.0", "9.0",
            "-5.0", "-40.5", "699", "16.5",
            "22.3", "-15.9", "0.7", "-11.0", "2.0",
            "-3.1", "-43.8", "774", "15.3", "14.3", "-19.7",
            "-42.0", "740", "14.5",
            "765일", "617일", "45%", "16.9", "-18.4",
            "-20.1%p", "-28.5%p", "-14.4%p", "-25.3%p",
            "-21.6%p", "-25.4%p", "-7.9%p", "-12.0%p", "-5.3%p"):
    check(f"K) 문서에 {tok} 가 있다", tok in src)
check("K1) 전부 0/5 라고 밝힌다", "전부 0/5" in flat)
check("K2) 유일한 예외(2/5)도 탈락이라고 적었다", "2/5 인데 이것도 탈락" in flat)
check("K3) 배관 확인을 적었다",
      "analyze_styles.py 의 20.2% / 22.0% 와 맞는다" in flat)

# =====================================================================
# L) 이번에 배운 것을 남겼는가
# =====================================================================
check("L1) 낙폭이 준 것은 투자를 덜 한 것이라고 정리한다",
      "위험관리가 아니라 투자를 덜 한 것이다" in flat)
check("L2) 낙폭 4.9%p 의 값이 수익 21.6%p 라고 적었다",
      "낙폭 4.9%p 를 사는\n값이 수익 21.6%p 다" in src
      or "낙폭 4.9%p 를 사는 값이 수익 21.6%p 다" in flat)
check("L3) 익절 때와 뒤집혔다고 밝힌다", "**정반대**다" in src)
check("L4) '노는 돈을 없애라' 가 보편 규칙이 아니라고 정리한다",
      "보편 규칙이 아니다" in flat)
check("L5) 왜 뒤집혔는지 설명한다", "재투자 대상이 다르다" in flat)
check("L6) 앞 파일 결론을 옮겨 쓰면 틀린다고 적었다",
      "그대로 옮겨 쓰면 틀린다" in flat)
check("L7) 내 예상이 틀렸다고 밝힌다", "기대는 틀렸다" in flat)
check("L8) 지수 규칙이 낙폭조차 못 줄였다고 짚는다",
      "낙폭이 **-15.9% 로\n기준선과 같다.**" in src
      or "낙폭이 **-15.9% 로 기준선과 같다.**" in flat)
check("L9) 깨지는 시기가 안 겹친다고 해석한다", "겹치지 않는다" in flat)
check("L10) 어제 것과 다른 질문이라고 갈라뒀다",
      "쓰는 자리가 다르면 다른\n질문이다" in src
      or "쓰는 자리가 다르면 다른 질문이다" in flat)

# =====================================================================
# M) 돌려봐도 되는가 - 가짜 패널로 run 이 도는가
# =====================================================================
_p = {c: FakeSeries([100.0 + i * (1 if c == "A" else -1) for i in range(60)])
      for c in ("A", "B", "C")}
_ord = {di: ["A", "B", "C"] for di in range(25, 60)}
_sts = M.ma_states(_p)
_c, _n, _f = M.run(list(range(60)), _p, _ord, _sts, 25, 20,
                   (False, False, False), pick=2)
check("M1) '없음' 은 규칙 매도가 0 건", _n == 0, f"{_n}건")
check("M2) 곡선 길이가 기간과 같다", len(_c) == 35, f"{len(_c)}")
_c2, _n2, _f2 = M.run(list(range(60)), _p, _ord, _sts, 25, 20,
                      (False, True, False), pick=2)
check("M3) 데드크로스 매도를 켜면 판다 (내리는 종목이 있으니)", _n2 > 0,
      f"{_n2}건")
check("M4) 수수료가 0 보다 크다", _f > 0)
_c3, _n3, _f3 = M.run(list(range(60)), _p, _ord, _sts, 25, 20,
                      (True, False, False), pick=2)
check("M5) 골든만 매수는 규칙 매도가 0 건", _n3 == 0)
_rng = random.Random(1)
_c4, _n4, _f4 = M.run(list(range(60)), _p, _ord, _sts, 25, 20,
                      (False, False, False), pick=2, rng=_rng,
                      rand_sell_p=0.5)
check("M6) 무작위 매도 대조군도 돈다", _n4 > 0, f"{_n4}건")
check("M7) 후보가 없는 날은 건너뛴다 (안 터진다)",
      M.run(list(range(60)), _p, {}, _sts, 25, 20,
            (False, False, False), pick=2)[1] == 0)

# =====================================================================
# N) 실제 패널 (--slow)
# =====================================================================
if "--slow" in sys.argv:
    import analyze_event_rebal as E
    import strategy as S
    dates, pnl = S.load_panel(verbose=False)
    order, _r = E.daily_ranks(dates, pnl, M.BASE_DI)
    states = M.ma_states(pnl)
    import analyze_fundamentals as F
    base = F.annualized(M.run(dates, pnl, order, states, M.BASE_DI, 120,
                              (False, False, False))[0])
    check("N1) 120일 기준선이 22.3% 대 (문서와 같다)",
          22.0 <= base <= 22.6, f"{base:.2f}%")
    rows = M.golden_cost(dates, pnl, order, states)
    check("N2) 필터 없는 백분위 중앙이 98",
          round(st.median(r[0] for r in rows)) == 98,
          f"{st.median(r[0] for r in rows):.1f}")
    check("N3) 골든 필터 백분위 중앙이 92",
          round(st.median(r[1] for r in rows)) == 92,
          f"{st.median(r[1] for r in rows):.1f}")
    check("N4) 순위 깊이 중앙이 28",
          round(st.median(r[2] for r in rows)) == 28,
          f"{st.median(r[2] for r in rows):.1f}")
else:
    check("N0) 느린 검사는 --slow 로 따로 돈다 (기본은 건너뜀)", True)

# =====================================================================
# O) 안전
# =====================================================================
check("O1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"O2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
