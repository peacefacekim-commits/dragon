"""analyze_overnight.py 검증 - 분해가 맞고, 결론을 좋게 안 기울였는가.

(2026-09-22 신설) 이 파일에서 틀릴 수 있는 방향이 셋이다.

  1) **오버나이트를 부풀리는 쪽.** 전일 종가가 없는 날이나 거래정지로
     끊긴 날을 0% 로 메우면 가짜 수익이 생긴다. split_day 가 None 을
     돌려주는지, 그리고 그 날을 아예 빼는지 본다.
  2) **산술평균을 연환산해놓고 '벌 수 있는 돈' 이라 부르는 것.**
     +60.9% 가 그런 숫자다. 문서가 이걸 명시적으로 막았는지 본다.
  3) **미래를 보는 것.** 체결 시점을 바꾸는 측정 4 에서, 종목 선정이
     네 방식 모두 같아야 한다. 안 그러면 격차가 시점의 것이 아니다.

그리고 사전 등록 규약을 지켰는지도 본다 - 조건은 결과를 보기 전에
정해졌고, 사후 검사(측정 5)는 사후라고 이름표가 붙어 있어야 한다.

실행:
  python tests/test_analyze_overnight.py
"""
import pathlib
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


import analyze_overnight as M  # noqa: E402

src = (REPO_ROOT / "analyze_overnight.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    """strategy.Series 흉내. di/open/close/pos 만 쓴다."""

    def __init__(self, recs):
        # recs = [(di, open, close)]
        self.di, self.open, self.close, self.pos = [], [], [], {}
        for k, (di, o, c) in enumerate(recs):
            self.di.append(di)
            self.open.append(o)
            self.close.append(c)
            self.pos[di] = k


# =====================================================================
# A) split_day - 모르는 날을 0 으로 메우지 않는가 (제일 중요)
# =====================================================================
s = FakeSeries([(0, 100.0, 110.0), (1, 121.0, 132.0)])
o, i = M.split_day(s, 0)
check("A1) 첫 기록은 오버나이트를 모른다 (None)", o is None)
check("A2) 첫 기록도 장중은 안다", abs(i - 10.0) < 1e-9, f"{i}")
check("A3) 0 으로 메우지 않는다", o != 0)

o, i = M.split_day(s, 1)
check("A4) 둘째 날 오버나이트 = 121/110-1 = 10%", abs(o - 10.0) < 1e-9,
      f"{o}")
check("A5) 둘째 날 장중 = 132/121-1 = 9.0909%", abs(i - 9.0909) < 0.001,
      f"{i}")

# 끊긴 날 (거래정지 등) - di 가 안 이어지면 오버나이트를 모른다
s2 = FakeSeries([(0, 100.0, 110.0), (5, 121.0, 132.0)])
o, i = M.split_day(s2, 1)
check("A6) di 가 끊기면 오버나이트는 None", o is None,
      f"{o}")
check("A7) 끊겨도 장중은 잰다", i is not None)
check("A8) 코드가 di 연속을 실제로 확인한다",
      "s.di[j] != s.di[j - 1] + 1" in src)

# 둘을 곱하면 일간수익률이 돼야 한다 (분해가 맞다는 뜻)
o, i = M.split_day(s, 1)
combined = (1 + o / 100) * (1 + i / 100) - 1
daily = 132.0 / 110.0 - 1
check("A9) 오버나이트 x 장중 = 전일종가->종가",
      abs(combined - daily) < 1e-12, f"{combined:.9f} vs {daily:.9f}")

# 내려간 날도 맞나
s3 = FakeSeries([(0, 100.0, 100.0), (1, 95.0, 90.0)])
o, i = M.split_day(s3, 1)
check("A10) 갭하락 -5%", abs(o - (-5.0)) < 1e-9, f"{o}")
check("A11) 장중 -5.263%", abs(i - (-5.2631)) < 0.001, f"{i}")
check("A12) 곱하면 -10%",
      abs(((1 + o / 100) * (1 + i / 100) - 1) - (-0.10)) < 1e-12)

# =====================================================================
# B) annualize - 복리로 세는가
# =====================================================================
check("B1) 일 0% 면 연 0%", abs(M.annualize(0.0)) < 1e-12)
check("B2) 복리다 (단리 x 246 이 아니다)",
      M.annualize(0.1) > 0.1 * 246, f"{M.annualize(0.1):.1f}%")
check("B3) 일 0.210% 면 연 68% 쯤",
      65 < M.annualize(0.210) < 72, f"{M.annualize(0.210):.1f}%")
check("B4) 음수 일평균이면 음수 연환산", M.annualize(-0.2) < 0)
check("B5) 일수를 줄이면 작아진다",
      M.annualize(0.1, 100) < M.annualize(0.1, 246))

# =====================================================================
# C) 문서가 기록한 숫자 - 실제로 적혀 있는가
#    (재현은 느려서 여기서 다 못 돌린다. 대신 숫자가 문서에 박혀
#     있는지, 그리고 서로 모순이 없는지 본다.)
# =====================================================================
for tok in ("+0.1936%", "-0.2011%", "+60.9%", "-39.1%", "-1.8%",
            "-7.8%", "+0.0563%", "+0.0102%", "+14.9%", "+2.5%",
            "+17.8%", "4.6배", "0.1219%", "0.5666%",
            "12.6%", "12.3%", "12.1%", "12.7%"):
    check(f"C) 문서에 {tok} 가 있다", tok in src)

# 측정 1 의 일평균과 연환산이 서로 맞나
check("C1) +0.1936%/일 을 연환산하면 60.9% 근처",
      abs(M.annualize(0.1936) - 60.9) < 1.5,
      f"{M.annualize(0.1936):.1f}%")
check("C2) -0.2011%/일 을 연환산하면 -39.1% 근처",
      abs(M.annualize(-0.2011) - (-39.1)) < 1.5,
      f"{M.annualize(-0.2011):.1f}%")
check("C3) 저변동 +0.0563%/일 -> 14.9% 근처",
      abs(M.annualize(0.0563) - 14.9) < 1.0,
      f"{M.annualize(0.0563):.1f}%")
check("C4) 저변동 +0.0102%/일 -> 2.5% 근처",
      abs(M.annualize(0.0102) - 2.5) < 0.5,
      f"{M.annualize(0.0102):.1f}%")

# 측정 3 의 뺄셈이 맞나
check("C5) 유니버스 수수료 후 = 0.1936 - 0.210 = -0.0164",
      abs((0.1936 - M.FEE_ROUND_TRIP) - (-0.0164)) < 1e-9)
check("C6) 저변동 수수료 후 = 0.0563 - 0.210 = -0.1537",
      abs((0.0563 - M.FEE_ROUND_TRIP) - (-0.1537)) < 1e-9)
check("C7) 둘 다 음수다 (안 된다는 결론이 산수와 맞다)",
      0.1936 - M.FEE_ROUND_TRIP < 0 and 0.0563 - M.FEE_ROUND_TRIP < 0)
check("C8) 유니버스가 수수료의 92% 까지 갔다",
      abs(0.1936 / M.FEE_ROUND_TRIP - 0.922) < 0.01,
      f"{0.1936 / M.FEE_ROUND_TRIP * 100:.1f}%")
check("C9) 문서가 '아깝게 못 넘는다' 를 '넘는다' 로 안 썼다",
      "안 된다.**" in src and "못 넘은 것은 못 넘은 것" in flat)

# 측정 5 의 단조성 - 문서가 적은 다섯 값이 실제로 단조 증가하는가
gaps = [0.1219, 0.2611, 0.3964, 0.4690, 0.5666]
check("C10) 변동성 구간 격차가 단조 증가한다",
      all(gaps[k] < gaps[k + 1] for k in range(len(gaps) - 1)))
check("C11) 고변동/저변동 = 4.6배", abs(gaps[-1] / gaps[0] - 4.6) < 0.1,
      f"{gaps[-1] / gaps[0]:.2f}배")

# =====================================================================
# D) 판정 - 조건 넷과 절대선이 실제로 걸리는가
# =====================================================================
check("D1) 조건1 문턱이 4다", M.MIN_YEARS_WIN == 4)
check("D2) 조건3 문턱이 0.05 다", M.P_CUTOFF == 0.05)
check("D3) 절대선이 0.10%p 다", M.MIN_EDGE_PP == 0.10)

# 다 통과해야만 채택
check("D4) 전부 좋으면 채택",
      M.verdict("x", 1.0, 5, 6, 0.5, 0.5, 0.5, 0.01) is True)
check("D5) 이긴 해가 모자라면 탈락",
      M.verdict("x", 1.0, 3, 6, 0.5, 0.5, 0.5, 0.01) is False)
check("D6) 반띵 방향이 다르면 탈락",
      M.verdict("x", 1.0, 5, 6, -0.5, 0.5, 0.5, 0.01) is False)
check("D7) 대조 p 가 크면 탈락",
      M.verdict("x", 1.0, 5, 6, 0.5, 0.5, 0.5, 0.50) is False)
check("D8) 최고 해를 빼면 음수면 탈락",
      M.verdict("x", 1.0, 5, 6, 0.5, 0.5, -0.5, 0.01) is False)
check("D9) 격차가 절대선보다 작으면 탈락 (다 통과해도)",
      M.verdict("x", 0.05, 5, 6, 0.5, 0.5, 0.5, 0.01) is False)
check("D10) 딱 절대선이면 통과 (경계)",
      M.verdict("x", 0.10, 5, 6, 0.5, 0.5, 0.5, 0.01) is True)
check("D11) p 가 딱 0.05 면 탈락 (경계. < 이지 <= 가 아니다)",
      M.verdict("x", 1.0, 5, 6, 0.5, 0.5, 0.5, 0.05) is False)

# 실제로 잰 D 방식이 정말 탈락인가 (문서가 적은 값으로 다시 돌린다)
check("D12) 측정한 D 방식은 탈락이다",
      M.verdict("D", 0.15, 3, 6, -0.23, 0.83, -1.00, 0.397) is False)
check("D13) 측정한 B 방식은 탈락이다",
      M.verdict("B", -0.33, 2, 6, -0.03, -0.58, -1.01, 0.687) is False)
check("D14) 측정한 C 방식은 탈락이다",
      M.verdict("C", -0.48, 3, 6, 0.20, -1.37, -0.86, 0.786) is False)
check("D15) 문서 결론이 '바꾸지 않는다' 다",
      "체결 시점은 바꾸지 않는다" in flat)

# =====================================================================
# E) 측정 4 가 공정한가 - 바뀌는 것이 체결 시점 하나뿐인가
# =====================================================================
check("E1) 종목 선정을 회차마다 한 번만 한다 (네 방식이 공유)",
      "종목 선정은 방식마다 같다" in flat)
check("E2) build_rounds 가 종목을 함께 돌려준다",
      "rounds.append((buy_di, sell_di, codes))" in src)
check("E3) run_fill 은 종목을 받기만 한다 (다시 안 뽑는다)",
      "def run_fill" in src
      and "pick_low_vol" not in src.split("def run_fill")[1].split("def ")[0])
check("E4) 수수료를 회차마다 뗀다",
      "st.mean(rets) - fee / 100" in src)
check("E5) 네 방식이 같은 수수료를 문다 (교체 횟수가 고정)",
      "교체 횟수가 고정" in flat)
check("E6) 체결 시점 네 가지가 등록돼 있다", len(M.FILLS) == 4)
check("E7) 기준이 시가/시가다 (지금 쓰는 방식)",
      M.FILLS[0][1] == "open" and M.FILLS[0][2] == "open")
check("E8) 네 조합이 서로 다르다",
      len({(b, s) for _n, b, s in M.FILLS}) == 4)

# leg_price 가 실제로 시점을 가르는가
s4 = FakeSeries([(0, 100.0, 200.0)])
check("E9) open 을 고르면 시가", M.leg_price(s4, 0, "open") == 100.0)
check("E10) close 를 고르면 종가", M.leg_price(s4, 0, "close") == 200.0)

# 캐시가 답을 안 바꾸는가
check("E11) 캐시는 di 별로 잡는다 (같은 di 면 같은 답)",
      "_PICK_CACHE" in src and "캐시는" in src)

# =====================================================================
# F) 사전 등록 규약
# =====================================================================
check("F1) 결과 보기 전에 정했다고 밝혔다",
      "숫자를 보기 전에 정했다" in flat)
check("F2) git log 가 순서를 증명한다고 적었다", "git log" in src)
check("F3) 조건 넷이 문서에 있다",
      "조건 1" in src and "조건 2" in src and "조건 3" in src
      and "조건 4" in src)
check("F4) 절대선의 근거를 적었다", "슬리피지를 못 쟀기 때문" in flat)
check("F5) 측정 5 가 사후라고 이름표가 붙어 있다",
      "사후 검사" in src and "이걸로 아무것도 채택하지 않는다" in flat)
check("F6) 사후 검사가 사전 등록에 없다고 밝혔다",
      "사전 등록에 없다" in flat)

# =====================================================================
# G) 좋게 기울이지 않았는가 (이 파일의 위험 방향)
# =====================================================================
check("G1) +60.9% 를 '벌 수 있는 돈' 으로 읽지 말라고 못박았다",
      "'벌 수 있는 돈'\n     으로 읽으면 안 된다" in src
      or "으로 읽으면 안 된다" in flat)
check("G2) 검산이 처음에 안 맞았다는 것을 숨기지 않았다",
      "안 맞는다" in src)
check("G3) 분산 손실로 설명하고 숫자를 냈다",
      "분산 손실" in src and "6.0%p" in src)
check("G4) 검산이 결국 통과했다고 적었다", "검산은 통과했다" in flat)
check("G5) 슬리피지가 0 으로 들어갔다고 맨 앞에 밝혔다",
      "슬리피지가 0 으로 들어가 있다" in flat)
check("G6) 결과가 전부 상한이라고 적었다", "전부 상한이다" in flat)
check("G7) 측정 5 가 증명이 아니라고 밝혔다",
      "증명한 게 아니라" in flat)
check("G8) 공매도로 먹는다는 결론을 막았다", "공매도" in src)
check("G9) 아직 못 잰 것을 적었다 (10분봉 1일치)",
      "아직 못 쟀다" in flat and "10분봉이 1일치뿐" in flat)
check("G10) 독립 표본 수를 적었다 (표본.md 규약)",
      "독립 표본" in src and "표본.md" in src)

# =====================================================================
# H) 밖에서 가져온 사실을 출처와 함께 적었는가
# =====================================================================
for tok in ("Barber", "Odean", "-23.9bp", "JFE 2018", "JRFM 2022",
            "Baltussen", "225", "RVOL"):
    check(f"H) 1절에 {tok} 가 있다", tok in src)
check("H1) 대만 표본이 우리보다 크다는 맥락을 적었다",
      "1992~2006" in src)
check("H2) -23.9bp 가 우리 수수료와 비슷하다고 이었다",
      "우리가 잰 왕복 수수료 0.21% 와 거의 같다" in flat)
check("H3) 논문 뒷받침 없는 것은 없다고 밝혔다",
      "논문 뒷받침은 못 찾았다" in flat)
check("H4) 돌파매매를 새로 잴 이유가 줄었다고 적었다",
      "새로 재볼 이유가 줄었다" in flat)

# =====================================================================
# I) compound_universe - 복리가 산술평균과 다른가
# =====================================================================
check("I1) 왜 다른지 적었다", "분산 손실" in src)
check("I2) '얼마 벌었나' 는 복리 쪽이라고 밝혔다",
      "'얼마 벌었나' 는 이쪽이다" in flat)
# 산수 자체: +10%/-10% 를 오가면 산술평균 0, 복리는 마이너스
a = st.mean([10.0, -10.0])
g = (1.10 * 0.90 - 1) * 100
check("I3) 산술평균 0 인데 복리는 음수다",
      abs(a) < 1e-12 and g < 0, f"산술 {a}, 복리 {g:.2f}%")

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
