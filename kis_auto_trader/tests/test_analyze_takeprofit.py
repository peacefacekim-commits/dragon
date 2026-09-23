"""analyze_takeprofit.py 검증 - 문턱을 진짜로 끝까지 올렸는가.

(2026-09-21 신설) 이 파일이 생긴 계기는 내가 **좁은 범위만 재고 계열
전체를 부정한 것** 이다. k=1~3 만 재놓고 "익절은 안 된다" 고 했는데,
사용자가 "900% 올랐으면 파는 게 이득 아니냐" 고 반박했고 그 지적이
맞았다. 그래서 여기서 제일 중요한 검사는:

  - 훑은 범위가 정말로 세 자릿수까지 가는가 (B 절)
  - '발동 안 함' 과 '해롭지 않음' 을 구분해서 적었는가 (E 절)

두 번째가 핵심이다. +1000% 익절이 22.0% 로 기준과 같은 이유는 규칙이
좋아서가 아니라 한 번도 안 켜져서다. 이걸 '중립적이다' 라고 적으면
읽는 사람이 속는다.

실행:
  python tests/test_analyze_takeprofit.py
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import analyze_takeprofit as M  # noqa: E402

src = (REPO_ROOT / "analyze_takeprofit.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes, opens=None):
        self.close = list(closes)
        self.open = list(opens if opens is not None else closes)
        self.pos = {i: i for i in range(len(closes))}


# =====================================================================
# A) 시간비례 문턱 계산
# =====================================================================
check("A1) 보유일이 0이면 문턱도 0", M.threshold_at(0, 1.0) == 0.0)
check("A2) 보유일에 비례한다",
      abs(M.threshold_at(10, 1.0) - 10 * M.EDGE_PER_DAY) < 1e-12)
check("A3) k 배수가 곱해진다",
      abs(M.threshold_at(10, 3.0) - 3 * M.threshold_at(10, 1.0)) < 1e-12)
check("A4) 5일 보유면 문턱이 1% 도 안 된다 (이게 지는 이유)",
      M.threshold_at(5, 1.0) < 1.0, f"{M.threshold_at(5, 1.0):.2f}%")
check("A5) 하루 엣지는 analyze_why 값을 쓴다", M.EDGE_PER_DAY == 0.0896)
check("A6) 그 출처를 적어뒀다", "analyze_why.py 에서 잰 하루 평균" in flat)

# =====================================================================
# B) 훑은 범위 - 이 파일이 생긴 이유
# =====================================================================
check("B1) 문턱이 세 자릿수까지 간다", max(M.THRESHOLDS) >= 1000,
      str(M.THRESHOLDS))
check("B2) 사용자가 물은 900% 가 범위 안이다",
      min(M.THRESHOLDS) < 900 < max(M.THRESHOLDS))
check("B3) 낮은 문턱도 같이 재서 비교가 된다", min(M.THRESHOLDS) <= 20)
check("B4) 도달 분포에 900 칸이 있다",
      900 in [t for t, _n in M.reach_counts([0.0])])
check("B5) 왜 범위를 넓혔는지 밝힌다",
      "큰 이익 구간을 한 번도 건드리지 않았다" in flat)
check("B6) 앞선 말이 과했다고 적었다", "과한 말이었다" in flat)
check("B7) 시간비례도 같이 남겼다", tuple(M.KS) == (1.0, 1.5, 2.0, 3.0))

# =====================================================================
# C) 도달 분포 계산
# =====================================================================
cnt = dict(M.reach_counts([5.0, 15.0, 25.0, 250.0]))
check("C1) 도달 건수가 누적이다 (10 이상 3건)", cnt[10] == 3, str(cnt))
check("C2) 250 짜리 하나가 200 칸에 잡힌다", cnt[200] == 1)
check("C3) 300 칸은 0건", cnt[300] == 0)
check("C4) 빈 입력이어도 안 터진다", M.reach_counts([])[0][1] == 0)
check("C5) 분위수 - 중앙", M.quantile([1.0, 2.0, 3.0], 0.5) == 2.0)
check("C6) 분위수 - 최고가 범위를 안 넘는다",
      M.quantile([1.0, 2.0, 3.0], 1.0) == 3.0)
check("C7) 빈 분위수는 0", M.quantile([], 0.5) == 0.0)

# =====================================================================
# D) run() - 문턱이 실제로 매도를 일으키는가
# =====================================================================
N = 400
# 계속 오르는 종목 하나. 문턱이 낮으면 팔리고 높으면 안 팔려야 한다.
rising = {c: FakeSeries([100.0 * (1.01 ** i) for i in range(N)])
          for c in ("a",)}
order = {di: ["a"] for di in range(N)}
dates = list(range(N))

_c, n_low = M.run(dates, rising, order, 0, tp=20)
_c, n_high = M.run(dates, rising, order, 0, tp=100000)
check("D1) 낮은 문턱은 매도를 일으킨다", n_low > 0, f"{n_low}건")
check("D2) 닿을 수 없는 문턱은 매도 0건", n_high == 0, f"{n_high}건")

flat_panel = {c: FakeSeries([1000.0] * N) for c in ("a",)}
_c, n_flat = M.run(dates, flat_panel, order, 0, tp=20)
check("D3) 안 오르면 익절이 안 걸린다", n_flat == 0, f"{n_flat}건")

# 매도 수수료를 떼는가 - 값이 안 변하는 시장에서 자본이 줄어야 한다
curve_flat, _n = M.run(dates, flat_panel, order, 0)
check("D4) 수수료가 붙는다 (매수 쪽)", curve_flat[-1] < M.CAPITAL,
      f"{curve_flat[-1]:,.0f}원")
check("D5) 매도 수수료를 판다는 쪽에서 뗀다",
      "(1 - FEE_ONE_WAY)" in src)

rec = []
M.run(dates, rising, order, 0, tp=20, collect=rec)
check("D6) 보유 구간을 기록한다 (최고%, 나갈때%, 보유일)",
      rec and len(rec[0]) == 3, str(rec[:1]))
check("D7) 기록된 최고가 나갈 때보다 작지 않다",
      all(r[0] >= r[1] - 1e-9 for r in rec))

c1, s1 = M.run(dates, rising, order, 0, tp=50)
c2, s2 = M.run(dates, rising, order, 0, tp=50)
check("D8) 같은 입력이면 같은 결과 (무작위성 없음)", c1 == c2 and s1 == s2)
check("D9) 익절을 안 쓰면 규칙 없는 기준선이 된다",
      M.run(dates, rising, order, 0)[1] == 0)

check("E0) 연환산/낙폭이 평소 정의와 같다",
      abs(M.mdd([100, 120, 60]) - (-50.0)) < 1e-9
      and abs(M.annualized([100.0] * 246, capital=100.0)) < 1e-6)

# =====================================================================
# E) 문서 - 결론을 정확하게 적었는가 (이 파일의 핵심)
# =====================================================================
for tok in ("22.0", "17.6", "18.4", "18.2", "20.5", "22.4", "203.0",
            "46.5", "61.4", "0/5", "3/5"):
    check(f"E) 결과표에 {tok} 가 있다", tok in src)
check("E1) 900% 도달이 0건이라고 밝힌다",
      "+900% 이상    0건" in src and "( 0.00%)" in src)
check("E2) 300% 도 0건이라고 밝힌다", "+300% 이상    0건" in src)
check("E3) 사용자 말이 맞는 방향이라고 인정한다",
      "방향은 사용자가 맞다" in flat)
check("E4) 그런데 +200% 가 거래 1건이라고 못박는다",
      "거래 1건" in flat and "표본 1개로 결론" in flat)
check("E5) 높은 문턱은 '발동 안 함' 이라고 구분해서 적는다",
      "한 번도 발동하지 않는" in flat and "매도 0건" in flat)
check("E6) '규칙이 나쁜 게 아니라' 라고 구분한다",
      "규칙이 나쁘다는 뜻이 아니라" in flat)
check("E7) 앞선 부정이 잰 범위 안에서만 맞았다고 밝힌다",
      "잰 범위 안에서만" in flat)
check("E8) 왜 900% 가 안 나오는지 구조로 설명한다",
      "애초에 후보에서 빠진다" in flat)
check("E9) 폭등하면 다음 교체에 밀린다는 것도 적었다",
      "다음 교체일에 순위 밖으로 밀려" in flat)
check("E10) 낮은 문턱이 해로운 이유를 짚는다",
      "오를 여지가 남은 종목을 곧바로 내보내기" in flat)
check("E11) 시간비례 문턱 결과를 표로 남겼다",
      "기대의 1.0배     3.8" in src and "기대의 3.0배     6.0" in src)
check("E12) 시간비례의 낙폭 감소가 개선이 아니라고 짚는다",
      "개선이 아니라" in flat and "현금으로 도망가 있는 시간" in flat)
check("E13) 43건이 적다는 한계를 밝힌다",
      "43건은 적다" in flat)
check("E14) 꼬리는 확률 추정이 아니라고 밝힌다",
      "확률 추정이 아니다" in flat)
check("E15) 2021~2026 한계를 밝힌다", "2021~2026 한국 시장이다" in flat)
check("E16) 다중검정 칸수를 적었다",
      "고정 문턱 7개 + k 4개 + 재투자 문턱 5개 = 16개" in flat)
check("E17) 채택한 게 없다고 밝힌다", "규칙을 추가하지 않는다" in flat)
check("E18) 실행법이 두 가지 다 적혀 있다",
      "python analyze_takeprofit.py" in src and "--slope" in src)

# =====================================================================
# H) 앞으로 더 오르나 (--forward) - 사용자 질문에 직접 답하는 부분
# =====================================================================
check("H1) 보유 구간을 뽑는 함수가 있다", hasattr(M, "segments"))
segs = M.segments(dates, rising, order, 0)
check("H2) 구간이 (종목, 진입, 청산, 기준가) 4칸",
      segs and len(segs[0]) == 4, str(segs[:1]))
check("H3) 청산이 진입보다 뒤다", all(s[2] > s[1] for s in segs))
check("H4) 기준가가 0이 아니다", all(s[3] for s in segs))

# 계속 오르는 종목: 문턱을 넘은 뒤로도 계속 오르므로 전부 양수여야 한다
fw = M.forward_after(rising, segs, 10)
check("H5) 계속 오르면 문턱 후 수익도 양수", fw and all(v > 0 for v in fw),
      f"{len(fw)}건")
# 안 오르는 종목은 문턱을 못 넘으므로 표본이 없다
check("H6) 문턱을 못 넘으면 표본에 안 들어간다",
      M.forward_after(flat_panel, M.segments(dates, flat_panel, order, 0),
                      10) == [])
check("H7) 문턱이 높을수록 표본이 준다",
      len(M.forward_after(rising, segs, 10)) >=
      len(M.forward_after(rising, segs, 100)))
check("H8) 잴 문턱이 100%까지 간다", max(M.FWD_LEVELS) >= 100,
      str(M.FWD_LEVELS))
check("H9) 100% 확신할 수 없다고 못박는다",
      "확신할 수 없다. 100% 가 아니다" in flat)
check("H10) 교체일이 특별한 날이 아니라고 밝힌다",
      "교체일은 특별한 날이 아니다" in flat and "미리 정해둔 날" in flat)
check("H11) +50% 뒤로는 떨어지는 쪽이 더 많다고 적었다",
      "56.9%" in src and "-1.62" in src)
check("H12) 평균과 중앙값이 갈라진다고 설명한다",
      "평균과 중앙값이 갈라지기" in flat and "8.65" in src)
check("H13) 10종목이면 평균을 받는다고 짚는다",
      "받는 것은 중앙값이 아니라" in flat)
check("H14) 둘 다 참일 수 있다고 정리한다", "동시에 참일 수 있다" in flat)

# =====================================================================
# I) 재투자 판 (--swap) - 앞 표의 군더더기를 걷은 것
# =====================================================================
check("I1) 재투자 함수가 있다", hasattr(M, "run_swap"))
check("I2) 앞 표가 현금으로 두는 판이었다고 밝힌다",
      "다음 교체일까지 현금으로" in flat and "군더더기" in flat)
_c, ns_win = M.run_swap(dates, rising, order, 0, tp=20, mode="win")
check("I3) 이익 규칙이 매도를 일으킨다", ns_win > 0, f"{ns_win}건")
_c, ns_lose = M.run_swap(dates, rising, order, 0, tp=20, mode="lose")
check("I4) 계속 오르면 거울 규칙은 발동 안 한다", ns_lose == 0)
_c, ns_r0 = M.run_swap(dates, rising, order, 0, tp=20, mode="rand", prob=0.0)
check("I5) 확률 0이면 무작위 매도도 0", ns_r0 == 0)
# 종목이 하나뿐이면 팔 것도 하나라 비교가 안 된다. 한 종목만 오르고
# 나머지는 제자리인 판을 만든다: 이익 규칙은 한 종목에서만 발동하고
# 무작위는 다섯 종목 전부에서 발동해야 한다.
mixed = {"a": FakeSeries([100.0 * (1.01 ** i) for i in range(N)])}
mixed.update({c: FakeSeries([100.0] * N) for c in ("b", "c", "d", "e")})
morder = {di: ["a", "b", "c", "d", "e"] for di in range(N)}
_c, mw = M.run_swap(dates, mixed, morder, 0, tp=20, mode="win")
_c, mr = M.run_swap(dates, mixed, morder, 0, tp=20, mode="rand",
                    prob=1.0, seed=3)
check("I6) 무작위는 안 오른 종목도 판다 (이익 규칙보다 많이)",
      mr > mw > 0, f"무작위 {mr}건 vs 이익 {mw}건")
a1, _ = M.run_swap(dates, rising, order, 0, tp=20, mode="rand", prob=0.3, seed=5)
a2, _ = M.run_swap(dates, rising, order, 0, tp=20, mode="rand", prob=0.3, seed=5)
b1, _ = M.run_swap(dates, rising, order, 0, tp=20, mode="rand", prob=0.3, seed=6)
check("I7) 같은 씨앗이면 같은 결과", a1 == a2)
check("I8) 다른 씨앗이면 다른 결과 (대조군이 진짜 무작위)", a1 != b1)
check("I9) 대조군 씨앗이 20개다", M.N_CONTROL_SEEDS == 20)
check("I10) 대조군 매도 횟수를 맞춘다 (수수료/회전량을 같게)",
      hasattr(M, "match_prob") and "같은 횟수" in flat)
check("I11) 왜 무작위 대조군이 핵심인지 적었다",
      "회전이 버는 건지 갈라야" in flat)
check("I12) 이웃 문턱을 같이 잰다", tuple(M.NEIGHBORS) == (20, 25, 30, 35, 40))

check("I13) 재투자 +30%가 기준을 넘는다고 적었다",
      "+30%      22.8" in src and "22.8%, 4/5" in src)
check("I14) 회전 대조군 20개를 전부 넘었다고 적었다",
      "20개 전부보다 위다" in flat and "17.5 ~ 22.0" in flat)
check("I15) 익절이 대조군을 넘은 건 처음이라고 밝힌다",
      "이번이 처음이다" in flat)
check("I16) 그래도 채택 안 한다고 밝힌다", "그래도 채택하지 않는다" in flat)
check("I17) 이유1 - 이웃이 안 따라온다", "봉우리 하나다" in flat
      and "+25% 는 20.6%" in flat)
check("I18) 이유2 - 낙폭이 나빠진다",
      "-15.9% -> -17.6%" in flat and "방향이 반대다" in flat)
check("I19) 이유3 - 후반부에 몰렸다", "후반부에 몰려" in flat
      and "8.9 vs 8.5" in flat)
check("I20) 해로운 진짜 원인이 '판 돈이 논다' 였다고 정리한다",
      "판 돈이 놀기" in flat)
check("I21) 미해결로 남긴다고 밝힌다", "미해결로 남긴다" in flat)
check("I22) 다시 잴 조건을 미리 적어뒀다",
      "셋 다" in flat and "나빠지지 않을 것" in flat)
check("I23) 거울 규칙 결과도 적었다", "거울 규칙(-30% 손실이면" in flat
      and "21.6%" in src)
check("I24) 다중검정 칸수를 갱신했다", "= 16개" in flat)
check("I25) 실행법 네 가지가 다 있다",
      all(t in src for t in ("--slope", "--forward", "--swap")))

# =====================================================================
# F) 조건이 다른 곳과 같은가
# =====================================================================
check("F1) 자본이 공용 상수", M.CAPITAL == 2_000_000)
check("F2) 수수료가 공용 상수", M.FEE_ONE_WAY == M.E.FEE_ONE_WAY)
check("F3) 주기/종목수가 채택안과 같다", M.PERIOD == 120 and M.PICK == 10)
check("F4) 시작일 5개", M.N_STARTS == 5)
check("F5) 종목 선정이 그 시점 정보로만 한다", "K.ranks(dates, panel" in src)

# =====================================================================
# G) 안전
# =====================================================================
check("G1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"G2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
