"""analyze_follow_up.py 검증 - 목표가 바뀐 만큼 조건도 제대로 바꿨는가.

(2026-09-22 신설) 목표가 "저변동을 이겨라" 에서 "시장이 오를 때
따라가라" 로 바뀌었다. 목표가 바뀌면 느슨해지기 쉽다. 이 파일의 위험은
다섯이다.

  1) **허용치를 결과 보고 늘리는 것.** 연수익 -3.0%p / 낙폭 -5.0%p 를
     결과 보기 전에 박았다. 50종목이 낙폭 -7.6%p 로 아깝게 걸렸는데,
     이걸 8%p 로 늘리면 채택이 된다. 그래서 상수로 박고 검사한다.
  2) **상승 포착률만 보고 좋아하는 것.** 하락 포착률이 같이 오른다.
     둘을 나눈 비대칭 비율을 같이 봐야 한다.
  3) **50종목의 +4.6%p 를 실력으로 읽는 것.** 자기 흩어짐이 21.1%p 다.
  4) **'유니버스 200종목' 을 시장이라고 부르는 것.** 78종목만 채워졌고
     싼 종목 쪽으로 기울어 있다.
  5) **포착률 기준을 전략 쪽 사정에 물들이는 것.** 기준은 수수료도 1주
     제약도 없는 맨 지수여야 한다.

실행:
  python tests/test_analyze_follow_up.py
  python tests/test_analyze_follow_up.py --slow   # 실제 패널까지
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


import analyze_follow_up as M  # noqa: E402

src = (REPO_ROOT / "analyze_follow_up.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes, start=0):
        self.close = list(closes)
        self.open = list(closes)
        self.high = list(closes)
        self.low = list(closes)
        self.value = [1e9] * len(closes)
        self.pos = {start + i: i for i in range(len(closes))}


# =====================================================================
# A) 허용치를 상수로 박았는가 (핵심 1)
# =====================================================================
check("A1) 연수익 허용치가 3.0%p", M.MAX_RETURN_GIVEUP == 3.0)
check("A2) 낙폭 허용치가 5.0%p", M.MAX_MDD_GIVEUP == 5.0)
check("A3) 3.0%p 의 근거를 적었다",
      "주기 20일->120일\n         의 1.8%p" in src
      or "주기 20일->120일 의 1.8%p" in flat
      or "1.8%p" in src)
check("A4) 5.0%p 의 근거를 적었다",
      "저변동의 최대낙폭이 -15.9% 다" in flat)
check("A5) 결과 보기 전에 박았다고 밝혔다",
      "결과를 보기 전에" in flat)
check("A6) 늘리지 않는다고 못박았다",
      "결과를 보고 허용치를 늘리지 않는다" in flat)
check("A7) 화면 출력에도 허용치를 적는다",
      "결과 보기 전에 박은 값" in src)
check("A8) 50종목이 아깝게 걸린 것을 숨기지 않았다",
      "-7.6%p" in src and "조건 3(낙폭)에서 -7.6%p 로 걸렸고" in flat)

# 허용치 경계
_a = dict(up_cap=0.5, base_up_cap=0.4, ret=20.0, base_ret=22.0,
          mdd=-19.0, base_mdd=-16.0, years_pos=4, years_total=6,
          rest_mean=1.0)
check("A9) 허용치 안이면 통과", M.accepted(**_a) is True)
check("A10) 연수익이 3.0%p 넘게 깎이면 탈락",
      M.accepted(**{**_a, "ret": 18.9}) is False)
check("A11) 딱 3.0%p 는 통과 (경계)",
      M.accepted(**{**_a, "ret": 19.0}) is True)
check("A12) 낙폭이 5.0%p 넘게 나빠지면 탈락",
      M.accepted(**{**_a, "mdd": -21.1}) is False)
check("A13) 딱 5.0%p 는 통과 (경계)",
      M.accepted(**{**_a, "mdd": -21.0}) is True)
check("A14) 상승 포착이 안 오르면 탈락 (목표를 못 이룸)",
      M.accepted(**{**_a, "up_cap": 0.4}) is False)
check("A15) 양수 해가 과반이 아니면 탈락",
      M.accepted(**{**_a, "years_pos": 3}) is False)
check("A16) 최고 해 빼면 음수면 탈락",
      M.accepted(**{**_a, "rest_mean": -1.0}) is False)
check("A17) 포착률이 None 이면 탈락 (안 터진다)",
      M.accepted(**{**_a, "up_cap": None}) is False)

# =====================================================================
# B) 포착률 계산 (핵심 2, 5)
# =====================================================================
# 시장이 하루 +10%, 다음날 -10%. 전략이 그 절반씩만 움직인다.
mkt = {0: 100.0, 1: 110.0, 2: 99.0}
strat = [100.0, 105.0, 99.75]        # +5%, -5%
uc, dc, nu, nd = M.capture(strat, mkt, 0)
check("B1) 오른날/내린날을 나눈다", (nu, nd) == (1, 1), f"{nu}/{nd}")
check("B2) 상승 포착률이 0.5", abs(uc - 0.5) < 1e-9, f"{uc}")
check("B3) 하락 포착률이 0.5", abs(dc - 0.5) < 1e-9, f"{dc}")
check("B4) 시장과 똑같이 움직이면 1.0",
      abs(M.capture([100.0, 110.0, 99.0], mkt, 0)[0] - 1.0) < 1e-9)
check("B5) 시장 값이 없으면 건너뛴다 (안 터진다)",
      M.capture([100.0, 110.0], {}, 0) == (None, None, 0, 0))
check("B6) 오른날이 없으면 상승 포착률 None",
      M.capture([100.0, 99.0], {0: 100.0, 1: 99.0}, 0)[0] is None)

check("B7) 비대칭 비율이 상승/하락", abs(M.asymmetry(0.6, 0.3) - 2.0) < 1e-9)
check("B8) 하락이 0 이면 None (0 으로 안 나눈다)",
      M.asymmetry(0.6, 0.0) is None)
check("B9) 하나라도 None 이면 None", M.asymmetry(None, 0.3) is None)
check("B10) 1.0 이 '시장을 그냥 산 것' 이라고 적었다",
      "1.0 은 시장을 그냥 산 것과 같고" in flat)
check("B11) 포착률만 보면 대가가 안 보인다고 적었다",
      "'상승이 올랐다' 만 보이고 대가가 안 보인다" in flat)
check("B12) 좋은 모양을 정의했다",
      "상승은 1 에\n가깝고 하락은 0 에 가까운 것" in src
      or "상승은 1 에 가깝고 하락은 0 에 가까운 것" in flat)

# =====================================================================
# C) 기준이 맨 지수인가 (핵심 5)
# =====================================================================
check("C1) 수수료도 1주 제약도 없는 지수라고 적었다",
      "수수료도 1주 제약도 없는" in flat)
check("C2) 왜 포트폴리오로 안 만드는지 적었다",
      "기준이 전략 쪽 사정" in flat
      and "그 사정을 재는 숫자가 되어버린다" in flat)
_p = {"A": FakeSeries([100.0, 110.0]), "B": FakeSeries([100.0, 90.0])}
_ord = {0: ["A", "B"], 1: ["A", "B"]}
_lvl = M.market_index(["d0", "d1"], _p, _ord, base=0)
check("C3) 동일가중 지수가 맞다 (+10%, -10% -> 0%)",
      abs(_lvl[1] - 100.0) < 1e-9, f"{_lvl}")
check("C4) 값이 없는 종목은 건너뛴다",
      len(M.market_index(["d0", "d1"], {"A": FakeSeries([100.0])},
                         _ord, base=0)) == 2)
check("C5) 수수료를 안 뺀다 (지수다)",
      "FEE_ONE_WAY" not in src.split("def market_index(")[1]
      .split("\ndef ")[0])

# =====================================================================
# D) 잡음을 잡음이라고 했는가 (핵심 3)
# =====================================================================
check("D1) 시작일 흩어짐을 출력한다", "시작일 5개가 얼마나 흩어지나" in src)
check("D2) 중앙값만 보면 안 된다고 적었다", "중앙값만 보면 안 된다" in flat)
check("D3) 50종목 흩어짐 21.1%p 를 적었다", "21.1" in src)
check("D4) 우위보다 흩어짐이 네 배 크다고 짚었다",
      "자기 흩어짐 21.1%p 가 네 배 넘게 크다" in flat)
check("D5) 구간이 완전히 겹친다고 적었다",
      "완전히\n덮는다" in src or "완전히 덮는다" in flat)
check("D6) 지그재그라서 단조롭지 않다고 짚었다",
      "지그재그다" in flat and "단조로울 텐데 아니다" in flat)
check("D7) 무엇을 믿을지 갈라놨다",
      "믿을 것은 낙폭/포착률이고, 연수익 차이는\n아니다" in src
      or "믿을 것은 낙폭/포착률이고, 연수익 차이는 아니다" in flat)
check("D8) 50종목의 +4.6%p 를 잡음으로 본다고 명시했다",
      "+4.6%p 는 잡음으로 본다" in flat)
check("D9) 조건 2 통과도 실력이 아니었다고 적었다",
      "조건 2 를 통과한\n것도 실력이 아니었다" in src
      or "조건 2 를 통과한 것도 실력이 아니었다" in flat)

# =====================================================================
# E) 200종목을 시장이라고 부르지 않는가 (핵심 4)
# =====================================================================
check("E1) 시장이 아니라고 제목에 박았다",
      "'유니버스 200종목' 칸은 시장이 아니다" in flat)
check("E2) 78종목만 채워졌다고 밝혔다", "채운 종목이 **78개**다" in src)
check("E3) 왜 못 채우는지 산수로 보였다",
      "1종목당 1만원이고" in flat and "5,000원 제약" in flat)
check("E4) 싼 종목으로 기운다고 밝혔다",
      "싼 종목부터** 채우므로" in src or "싼 종목 쪽으로 기운다" in flat)
check("E5) 그래서 포착률이 1 을 넘는다고 설명했다",
      "1.14 가 1 을 넘고" in flat)
check("E6) 깨끗한 시장 숫자가 맨 지수라고 못박았다",
      "깨끗한 시장 숫자는 맨 지수\n쪽(-7.0%)" in src
      or "깨끗한 시장 숫자는 맨 지수 쪽(-7.0%)" in flat)
check("E7) 다른 칸도 못 채운다고 밝혔다", "30->22, 50->32, 100->51" in src)
check("E8) 종목수가 아니라 분산의 정도로 읽으라고 적었다",
      "'분산의 정도' 로 읽어야 한다" in flat)
check("E9) 채운 종목수를 표에 넣는다", "채운종목" in src)
check("E10) 절반도 못 차면 경고한다",
      "목표의 절반도 안 찬다" in src)

# =====================================================================
# F) 안 되는 길을 먼저 지웠는가
# =====================================================================
check("F1) 대형주가 저변동과 같다고 짚었다",
      "대형주는 저변동과 +0.722" in flat)
check("F2) 근거를 analyze_selectors 로 댔다",
      "analyze_selectors.py" in src and "-0.722" in src)
check("F3) 오르는 것을 사는 길도 지웠다",
      "추세 -30.9%" in src and "골든크로스 필터 -7.9%p" in src
      and "dip -29.6%" in src)
check("F4) 시총가중을 왜 안 넣었는지 적었다",
      "buy_greedy 가 동일가중 배분기" in flat)
check("F5) 그건 추정이고 잰 게 아니라고 밝혔다",
      "추정이고 잰 것이 아니다" in flat)

# =====================================================================
# G) 목표가 바뀐 것을 분명히 했는가
# =====================================================================
check("G1) 이기려는 게 아니라고 밝혔다", "이기려는 게\n아니다" in src
      or "이기려는 게 아니다" in flat)
check("G2) 저변동이 설계상 상승을 포기한다고 적었다",
      "설계상 상승을 포기하는 전략" in flat)
check("G3) monitor 의 0.37/0.50 을 근거로 들었다",
      "0.37" in src and "0.50" in src)
check("G4) monitor 와 뜻이 반대라고 밝혔다",
      "monitor.py 와 뜻이 반대다" in flat)
check("G5) monitor 문턱을 안 쓴다고 못박았다",
      "monitor.py 의 문턱을 가져다 쓰지 않는다" in flat)
check("G6) monitor 를 import 하지 않는다", "import monitor" not in src)
check("G7) analyze_winning_period 의 0.29 를 출발점으로 들었다",
      "0.29" in src and "analyze_winning_period.py" in src)

# =====================================================================
# H) 결과 숫자가 모듈 출력과 맞는가
# =====================================================================
for tok in ("-7.0%", "22.3", "-15.9", "-12.7", "0.39", "0.25", "1.55",
            "16.5", "-21.6", "-14.5", "0.51", "0.40", "1.27",
            "26.9", "-23.6", "-12.9", "0.62", "0.47", "1.32",
            "18.2", "-31.8", "0.82", "0.68", "1.21",
            "2.1", "-53.5", "-28.6", "1.14", "1.09", "1.05",
            "29.3%p", "+4.6%p", "-5.8", "-15.8", "-20.2", "-37.6",
            "16.9", "26.7", "9.8", "12.5", "33.6", "21.1", "8.1", "15.8"):
    check(f"H) 문서에 {tok} 가 있다", tok in src)
check("H1) 시장이 손실이었다는 것을 제일 앞에 뒀다",
      "어느 숫자보다 중요한 것" in flat)
check("H2) 저변동 우위가 착각이 아니라고 결론냈다",
      "저변동 우위는 착각이 아니었다" in flat)
check("H3) 따라갈 시장이 내려가는 시장이었다고 짚었다",
      "따라갈 시장이 내려가는 시장이었다" in flat)
check("H4) 채택 0개라고 밝혔다", "채택 0개" in src)
check("H5) 전부 조건 3 에서 걸렸다고 적었다",
      "전부 조건 3(낙폭 -5.0%p)에서\n걸렸다" in src
      or "전부 조건 3(낙폭 -5.0%p)에서 걸렸다" in flat)

# =====================================================================
# I) 결론이 목표를 어떻게 고치라고 하는가
# =====================================================================
check("I1) 종목 수로 이루려면 값이 하락이라고 정리했다",
      "**종목 수로** 이루려 하면 값이 하락이다" in src
      or "종목 수로 이루려 하면 값이 하락이다" in flat)
check("I2) 원하는 것이 비대칭 비율이라고 짚었다",
      "'상승 포착률' 이 아니라 **비대칭 비율**로\n보인다" in src
      or "비대칭 비율" in flat)
check("I3) 사용자의 전제와 같은 말이라고 잇는다",
      "큰 이득을 포기하더라도 큰 손해를 피하고 작은 이득을 쌓는다" in flat)
check("I4) 그 지표에서 지금 것이 제일 좋다고 밝힌다",
      "저변동 10종목이 이미\n다섯 칸 중 제일 좋다 (1.55)" in src
      or "저변동 10종목이 이미 다섯 칸 중 제일 좋다 (1.55)" in flat)
check("I5) 남은 길을 지목한다", "상승과 하락을 갈라주는" in flat)
check("I6) 그 자리가 계속 실패한 자리라고 밝힌다",
      "계속 실패한 자리다" in flat)
check("I7) 실거래가 0.29 로 지금 전략보다 나빴다고 잇는다",
      "실거래가 지금 전략보다 나빴다" in flat)
check("I8) 목표를 바꿔도 결론이 같다고 정리한다",
      "목표를 바꾸어도 결론이 같은\n쪽으로 간다" in src
      or "목표를 바꾸어도 결론이 같은 쪽으로 간다" in flat)

# =====================================================================
# J) 한계를 밝혔는가
# =====================================================================
check("J1) 다섯 칸을 봤다고 밝힌다", "다섯 칸을 봤다" in flat)
check("J2) 200만원 기준이라고 밝힌다", "200만원 기준의 결과다" in flat)
check("J3) 시기에 묶여 있다고 밝힌다", "이 결론은 시기에\n묶여 있다" in src
      or "이 결론은 시기에 묶여 있다" in flat)
check("J4) 포착률이 평균 기준이라고 밝힌다",
      "일수익률 평균 기준이다" in flat)

# =====================================================================
# K) 구성 - 종목 수 하나만 움직이는가
# =====================================================================
check("K1) 다섯 칸이다", len(M.BOXES) == 5)
check("K2) 기준선이 저변동 10종목", M.BASE_BOX == "저변동 10종목")
check("K3) 종목수가 10/30/50/100/200",
      [p for _n, p, _f in M.BOXES] == [10, 30, 50, 100, 200])
check("K4) 선정은 low_vol 과 all 둘뿐",
      {f for _n, _p, f in M.BOXES} == {"low_vol", "all"})
check("K5) 주기가 120일 하나", M.PERIOD == 120)
check("K6) 종목 수 하나만 움직인다고 적었다",
      "다른 것은 **종목 수 하나뿐**이다" in src
      or "다른 것은 종목 수 하나뿐이다" in flat)

# =====================================================================
# L) 산수 / 안전
# =====================================================================
check("L1) 일수익률 계산",
      abs(M.daily_rets([100.0, 110.0])[0] - 0.1) < 1e-12,
      str(M.daily_rets([100.0, 110.0])))
check("L2) 0 으로 안 나눈다", M.daily_rets([0.0, 10.0]) == [0.0])
check("L3) 최악 1년 - 구간이 짧으면 전체로 본다",
      abs(M.worst_year([100.0, 50.0]) - (-50.0)) < 1e-9)
check("L4) 최악 1년을 찾는다",
      abs(M.worst_year([100.0] * 10 + [50.0], days=10) - (-50.0)) < 1e-9)
check("L5) 빈 곡선이어도 안 터진다", M.worst_year([]) == 0.0)
check("L6) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"L7) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# M) 실제 패널 (--slow)
# =====================================================================
if "--slow" in sys.argv:
    import strategy as S
    dates, pnl = S.load_panel(verbose=False)
    orders = {f: M.ranks_for(dates, pnl, f)
              for f in {f for _n, _p, f in M.BOXES}}
    mk = M.market_index(dates, pnl, orders["low_vol"])
    ann = ((mk[max(mk)] / 100.0) ** (M.DAYS_PER_YEAR / (len(mk) - 1)) - 1) * 100
    check("M1) 맨 지수가 연 -7.0% (문서와 같다)",
          abs(ann - (-7.0)) < 0.2, f"{ann:.2f}%")
    c10, _f, fl10 = M.run(dates, pnl, orders["low_vol"], M.BASE_DI, 10)
    import analyze_fundamentals as F
    check("M2) 저변동 10종목이 22.3% 대",
          22.0 <= F.annualized(c10) <= 22.6, f"{F.annualized(c10):.2f}%")
    uc, dc, nu, nd = M.capture(c10, mk, M.BASE_DI)
    check("M3) 저변동 10종목 상승 포착 0.39 대",
          abs(uc - 0.39) < 0.03, f"{uc:.3f}")
    check("M4) 하락 포착 0.25 대", abs(dc - 0.25) < 0.03, f"{dc:.3f}")
    check("M5) 비대칭이 1.5 를 넘는다", M.asymmetry(uc, dc) > 1.5,
          f"{M.asymmetry(uc, dc):.2f}")
    _c200, _f2, fl200 = M.run(dates, pnl, orders["all"], M.BASE_DI, 200)
    # 표의 78 은 시작일 5개를 모두 모은 중앙값이고, 여기는 시작일 하나다.
    # 시작일마다 회차 날짜가 달라 채워지는 수가 조금씩 다르므로 폭을 둔다.
    check("M6) 200종목은 70~85종목만 채워진다 (표는 5개 시작일 합산 78)",
          70 <= st.median(fl200) <= 85, f"{st.median(fl200):.0f}종목")
    check("M7) 목표의 절반도 못 찬다 (문서의 핵심)",
          st.median(fl200) < 100, f"{st.median(fl200):.0f}")
else:
    check("M0) 느린 검사는 --slow 로 따로 돈다 (기본은 건너뜀)", True)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
