"""뉴스/실물경제 정보가 도움이 될 여지가 얼마나 있나 - 천장과 검증 기간.

(2026-09-18 신설) 사용자: "그럼 이건 어떨까. 주식시장 상황뿐 아니라 뉴스
기사등 외적인 실물경제 정보까지 고려한다면"

먼저 못 하는 것을 분명히 해둔다.

  뉴스는 백테스트가 불가능하다. news.py 는 네이버 금융에서 **최근** 뉴스만
  긁어온다. 과거 기록을 저장한 파일이 data/ 에 없다 (확인함). 2021년 어느
  날의 뉴스 제목을 지금 다시 가져올 방법이 없으므로, 뉴스 신호는 과거
  62회차에 적용해볼 수가 없다. 앞으로 모으는 것 말고는 길이 없다.

  실물경제 지표 중 지금 가진 것(VIX, 환율, 미국지수 4개, 수급 3종)은 이미
  analyze_best_rounds.py 의 25개 지표 싹 훑기에 들어가 있었고 부호 일치
  9/25 로 우연(12.5)보다 낮았다. '실물경제를 더 보자' 는 방향은 이미
  한 번 답이 나온 셈이다.

그래서 질문을 바꿨다. 뉴스를 검증할 수 없으니, **검증할 수 있는 형태로
바꿔서** 묻는다.

  "뉴스가 바스켓 10종목 중 나쁠 놈을 골라낼 수 있다고 치자.
   얼마나 정확해야 이득이고, 그걸 확인하는 데 몇 년이 걸리나?"

이건 뉴스 없이도 지금 데이터로 답이 나온다. 뉴스의 성능은 모르지만,
뉴스가 놓인 자리의 크기는 잴 수 있다.

중요한 차이: 지금까지 실패한 21개 타이밍 가설은 모두 '언제 살까' 였다.
이건 '10개 중 무엇을 뺄까' 다. 같은 회차 안에서의 비교이므로 시장 등락이
상쇄된다(짝지은 비교). 그래서 필요한 표본이 훨씬 적다.

===========================================================================
결과 1 - 바스켓 안에 골라낼 여지가 있나: 있다
===========================================================================
  회차 안 종목간 표준편차   중앙값 4.97%p  (최소 1.82 / 최대 16.27)
  최고 - 최악 벌어짐        중앙값 17.24%p  (최소 5.01 / 최대 54.68)

  10종목이 같이 움직이지 않는다. 한 회차 안에서 최고와 최악이 중앙값
  17%p 벌어진다. 골라낼 여지 자체는 넉넉하다.

===========================================================================
결과 2 - 천장과 바닥 (사후 판단이므로 실현 불가)
===========================================================================
  10종목 다 갖기   +1.054%/회차

  뺄 개수     천장   천장-전체      바닥   바닥-전체   찍기 적중률
     1     +2.041    +0.987    -0.037    -1.091      10%
     2     +2.841    +1.787    -0.897    -1.951      20%
     3     +3.627    +2.574    -1.634    -2.688      30%

  위아래가 거의 대칭이다. 뉴스로 잘 고르면 회차당 +1.8%p 를 얻고,
  잘못 고르면 -2.0%p 를 잃는다. 공짜 옵션이 아니다. 많이 뺄수록
  천장도 바닥도 같이 커진다 - 판단이 나쁘면 많이 뺄수록 더 나쁘다.

===========================================================================
결과 3 - 핵심: 몇 % 맞춰야 이득이고, 확인에 몇 년 걸리나
===========================================================================
h = '뺀 종목이 실제로 최악 2개 안에 있을 확률'. 아무 정보 없이 찍으면 20%.

  적중률 h   회차 평균   10종목 대비   누적(62회)   차이 표준편차  필요 회차  몇 년
     20%      +1.056      +0.002      + 80.0%      1.018        -       -
     30%      +1.278      +0.224      +106.0%      1.067      179    14.6
     40%      +1.503      +0.449      +136.2%      1.092       46     3.8
     50%      +1.723      +0.669      +169.9%      1.096       21     1.7
     60%      +1.945      +0.891      +208.7%      1.078       11     0.9
     80%      +2.394      +1.340      +304.5%      0.972        4     0.3
    100%      +2.841      +1.787      +428.6%      0.734        1     0.1

반기로 쪼개면 골라낼 여지 자체는 양쪽에 다 있다.
  전반부 31회차  다갖기 -0.134  천장 +1.438  바닥 -1.528  흩어짐 4.17%p
  후반부 31회차  다갖기 +2.242  천장 +2.135  바닥 -2.374  흩어짐 5.90%p
여지는 시기의 산물이 아니다. (여지가 있다는 것이지, 뉴스가 그걸 잡아낸다는
증거는 전혀 아니다 - 그건 아직 아무 증거도 없다)

  h=20% 줄이 +0.002 로 나오는 것이 이 계산의 검산이다. 찍기는 10종목
  다 갖기와 같아야 하고, 실제로 같게 나왔다.

  손익분기는 h > 20% 다. 20% 를 넘기만 하면 넘은 만큼 벌린다.

===========================================================================
결과 4 - 이게 왜 지금까지와 다른가
===========================================================================
이 세션에서 실패한 가설들의 검증 기간과 비교해보면

  월간 타이밍 신호 (+1%p 효과)        167회차 = 13년   사실상 불가능
  뉴스로 종목 빼기 (h=50%)             21회차 = 1.7년   가능
  뉴스로 종목 빼기 (h=40%)             46회차 = 3.8년   가능
  뉴스로 종목 빼기 (h=30%)            179회차 = 14.6년  불가능

  차이는 짝지은 비교라는 데서 온다. '언제 살까' 는 시장 등락 전체가
  잡음으로 들어오지만(회차 표준편차 4.62%), '무엇을 뺄까' 는 같은 회차
  안에서 비교하므로 시장이 상쇄되고 표준편차가 1.0%p 로 줄어든다.

  즉 **뉴스가 이 세션에서 나온 아이디어 중 검증이 손에 닿는 첫 번째다.**
  단 조건이 있다: 적중률이 40% 는 돼야 한다 (찍기의 두 배). 30% 면
  이득이긴 하지만 확인하는 데 15년이 걸려서 확인 못 한 채로 쓰게 된다.

===========================================================================
읽는 법 / 다음에 할 일
===========================================================================
  1) 뉴스가 쓸모없다는 뜻이 아니다. **지금은 모른다**는 뜻이다.
     과거 기록이 없어서 재볼 수가 없다.
  2) 재보려면 지금부터 모아야 한다. 매 회차 10종목의 뉴스 제목과
     호재/악재 판단을 날짜와 함께 저장하고, 20거래일 뒤 실제 수익과
     맞춰본다. 이건 paper_trade.py 가 이미 하는 일의 확장이다.
  3) 판단만 저장하면 안 되고 **제목 원문도 같이 저장**해야 한다.
     나중에 판단 기준을 바꿔서 다시 채점할 수 있어야 한다. 판단만
     남기면 그 한 번의 판단이 맞았나만 알 수 있다.
  4) 목표는 h >= 40%. 12.3회차/년이니 4년쯤 걸린다. 그 전에는
     뉴스로 종목을 빼면 안 된다 - 틀리면 -2%p 쪽이다.
  5) 뺀다/안 뺀다 두 갈래를 같이 기록해두면(뺐을 때와 안 뺐을 때를
     둘 다 계산) 실제 돈을 걸지 않고도 같은 4년으로 채점할 수 있다.
     실물 투자는 10종목 다 갖기로 하고, 뉴스 쪽은 장부상으로만
     돌리는 게 맞다.

DROP(몇 개를 뺄까) 과 반기 분할 결과는 실행하면 표로 나온다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_news_ceiling.py
"""
import math
import pathlib
import statistics as st
import sys

import numpy as np

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import strategy as S  # noqa: E402

HOLD, PICK = 20, 10
FEE = S.FEE_ROUND_TRIP_PCT
N_SIM = 4000
SEED = 20260918
# 검출에 필요한 표본: 양쪽 5% 유의 + 80% 검출력 -> (1.96+0.84)^2 = 7.85
Z2 = 7.85
ROUNDS_PER_YEAR = 246 / HOLD

rng = np.random.default_rng(SEED)


def build_rounds():
    """겹치지 않는 회차마다 저변동 10종목의 개별 수익을 모은다.

    종목 선정은 di 시점까지의 정보만, 수익은 di ~ di+HOLD 구간만 쓴다.
    """
    dates, panel = S.load_panel()
    n = len(dates)
    start = max(140, S.LIQUIDITY_DAYS + 2)
    out = []
    di = start
    while di + HOLD < n:
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(sc) < PICK:
            di += HOLD
            continue
        sc.sort(reverse=True)
        picks = [c for _s, c in sc[:PICK]]
        rs = []
        for c in picks:
            r, _cut = S.trade_return(panel, c, di, di + HOLD)
            if r is not None:
                rs.append(r)
        if len(rs) == PICK:
            out.append((dates[di], rs))
        di += HOLD
    return out


def hold_all(rounds):
    """10종목 다 갖는 경우의 회차 평균."""
    return st.mean([st.mean(rs) - FEE for _d, rs in rounds])


def ceiling_floor(rounds, drop):
    """최악 drop개를 뺀 경우(천장)와 최고 drop개를 뺀 경우(바닥).

    둘 다 사후 판단이다. 실현 가능한 값이 아니라 여지의 크기를 본다.
    """
    top = st.mean([st.mean(sorted(rs)[drop:]) - FEE for _d, rs in rounds])
    bot = st.mean([st.mean(sorted(rs)[:-drop]) - FEE for _d, rs in rounds])
    return top, bot


def simulate(rounds, drop, h):
    """적중률 h 로 drop개를 뺐을 때의 회차별 기대수익과 뽑기 분산.

    h = 뺀 종목이 실제 최악 drop개 안에 있을 확률.
    정보가 없으면 h = drop/PICK 이고, 그때 결과는 10종목 다 갖기와 같아야
    한다 - 이게 이 함수의 검산이다.
    """
    means, within = [], []
    for _d, rs in rounds:
        idx = np.argsort(rs)
        bad = set(int(i) for i in idx[:drop])
        good = [i for i in range(PICK) if i not in bad]
        draws = []
        for _ in range(N_SIM):
            dropped = set()
            for _k in range(drop):
                if rng.random() < h:
                    pool = [i for i in bad if i not in dropped]
                    if not pool:
                        pool = [i for i in good if i not in dropped]
                else:
                    pool = [i for i in good if i not in dropped]
                    if not pool:
                        pool = [i for i in bad if i not in dropped]
                dropped.add(int(rng.choice(pool)))
            keep = [rs[i] for i in range(PICK) if i not in dropped]
            draws.append(st.mean(keep) - FEE)
        means.append(st.mean(draws))
        within.append(st.pvariance(draws))
    return means, within


def needed_rounds(rounds, means, within, base):
    """효과를 통계적으로 확인하는 데 필요한 회차 수.

    한 회차 차이의 흩어짐은 두 몫으로 이루어진다.
      회차마다 기대값이 다른 몫 + 그 회차 안에서 무엇을 뽑았나의 운
    앞의 것만 쓰면(N_SIM 평균) 분산이 사라져서 '1회차면 된다' 는 엉터리
    값이 나온다. 둘을 합쳐야 한다.
    """
    diffs = [m - (st.mean(rs) - FEE) for m, (_d, rs) in zip(means, rounds)]
    dsd = math.sqrt(st.pvariance(diffs) + st.mean(within))
    eff = st.mean(means) - base
    if abs(eff) < 1e-6 or dsd <= 0:
        return dsd, None, None
    need = Z2 * dsd * dsd / (eff * eff)
    return dsd, need, need / ROUNDS_PER_YEAR


def main():
    rounds = build_rounds()
    print(f"회차 {len(rounds)}개 ({rounds[0][0]} ~ {rounds[-1][0]})")
    print(f"각 회차 {PICK}종목, 보유 {HOLD}거래일, 겹치지 않음\n")

    base = hold_all(rounds)

    # ------------------------------------------- 1) 바스켓 안의 흩어짐
    print("=" * 92)
    print("=== 1) 바스켓 10종목의 수익이 얼마나 흩어지나 ===")
    print("=== (다 같이 움직이면 골라낼 여지가 애초에 없다) ===")
    print("=" * 92)
    sds = [st.pstdev(rs) for _d, rs in rounds]
    spr = [max(rs) - min(rs) for _d, rs in rounds]
    print(f"  회차 안 종목간 표준편차   중앙값 {st.median(sds):.2f}%p"
          f"  (최소 {min(sds):.2f} / 최대 {max(sds):.2f})")
    print(f"  최고 - 최악 벌어짐        중앙값 {st.median(spr):.2f}%p"
          f"  (최소 {min(spr):.2f} / 최대 {max(spr):.2f})")
    print(f"\n  10종목 다 갖는 경우 회차 평균 {base:+.3f}%")

    # ------------------------------------ 2) 천장/바닥 (DROP 개수별)
    print("\n" + "=" * 92)
    print("=== 2) 완벽히 최악을 뺐다면 / 최고를 잘못 뺐다면 (몇 개를 뺄까별) ===")
    print("=== 사후 판단이므로 실현 불가능하다. 여지의 크기만 본다 ===")
    print("=" * 92)
    print(f"  {'뺄 개수':>7} {'천장':>9} {'천장-전체':>11} "
          f"{'바닥':>9} {'바닥-전체':>11} {'찍기 적중률':>11}")
    for drop in (1, 2, 3):
        top, bot = ceiling_floor(rounds, drop)
        print(f"  {drop:>7} {top:>+9.3f} {top-base:>+11.3f} "
              f"{bot:>+9.3f} {bot-base:>+11.3f} {drop/PICK*100:>10.0f}%")
    print("\n  위아래가 거의 대칭이다. 공짜 옵션이 아니라 틀리면 그만큼 잃는다.")

    # ---------------------------- 3) 적중률별 기대수익과 필요 검증기간
    for drop in (2,):
        print("\n" + "=" * 92)
        print(f"=== 3) 적중률 h 로 {drop}개를 뺐을 때 - 몇 % 맞춰야 하고 "
              f"확인에 몇 년 걸리나 ===")
        print(f"=== h = 뺀 종목이 실제 최악 {drop}개 안에 있을 확률. "
              f"찍으면 {drop/PICK*100:.0f}% ===")
        print("=" * 92)
        print(f"  {'적중률 h':>9} {'회차 평균':>10} {'전체 대비':>10} "
              f"{'누적':>9} {'차이 표준편차':>12} {'필요 회차':>10} "
              f"{'= 몇 년':>8} {'판정':>14}")
        for h in (drop / PICK, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00):
            means, within = simulate(rounds, drop, h)
            dsd, need, yrs = needed_rounds(rounds, means, within, base)
            cum = 1.0
            for x in means:
                cum *= (1 + x / 100)
            eff = st.mean(means) - base
            tag = ("찍는 것과 같음" if abs(h - drop / PICK) < 1e-9
                   else ("이득" if eff > 0 else "손해"))
            # 효과가 0 에 가까우면 필요 표본이 발산한다. 둘 다 '-' 로 낸다.
            ok = need is not None and need < 1e6
            ns = f"{need:,.0f}" if ok else "-"
            ys = f"{yrs:,.1f}" if ok else "-"
            print(f"  {h*100:>8.0f}% {st.mean(means):>+10.3f} {eff:>+10.3f} "
                  f"{(cum-1)*100:>+8.1f}% {dsd:>12.3f} {ns:>10} {ys:>8} "
                  f"{tag:>14}")
        print(f"\n  h={drop/PICK*100:.0f}% 줄이 0 으로 나오는 것이 검산이다. "
              f"찍기는 다 갖기와 같아야 한다.")
        print(f"  손익분기는 h > {drop/PICK*100:.0f}%. 넘은 만큼만 벌린다.")

    # ------------------------------------------- 4) 반기 분할 (천장이 안정적인가)
    print("\n" + "=" * 92)
    print("=== 4) 반기 분할: 골라낼 여지가 시기에 따라 달라지나 ===")
    print("=" * 92)
    half = len(rounds) // 2
    for label, seg in (("전반부", rounds[:half]), ("후반부", rounds[half:])):
        b = hold_all(seg)
        top, bot = ceiling_floor(seg, 2)
        sd = st.median([st.pstdev(rs) for _d, rs in seg])
        print(f"  {label} {len(seg):>2}회차 ({seg[0][0]} ~ {seg[-1][0]})  "
              f"다갖기 {b:>+7.3f}  천장 {top-b:>+7.3f}  바닥 {bot-b:>+7.3f}  "
              f"흩어짐 {sd:>5.2f}%p")
    print("\n  양쪽 모두 천장이 양수이고 크기가 비슷하면, 골라낼 여지는")
    print("  특정 시기의 산물이 아니라는 뜻이다. (여지의 안정성이지,")
    print("  뉴스가 그걸 잡아낸다는 증거는 아니다)")

    print("\n" + "=" * 92)
    print("=== 결론 ===")
    print("=" * 92)
    print("  뉴스는 지금 재볼 수 없다. 과거 뉴스 기록이 없다.")
    print("  다만 뉴스가 놓일 자리는 넉넉하고(회차당 최대 +1.8%p),")
    print("  검증 기간도 짧다(적중률 40% 면 약 4년). 지금까지 실패한")
    print("  타이밍 가설들이 13년을 요구했던 것과 다르다. 같은 회차 안에서")
    print("  비교하므로 시장 등락이 상쇄되기 때문이다.")
    print("  그래서 할 일은 '뉴스를 써서 투자' 가 아니라 '뉴스를 모아서")
    print("  장부상으로 채점' 이다. 적중률 40% 가 확인되기 전에는 실제로")
    print("  종목을 빼면 안 된다 - 틀리면 회차당 -2%p 쪽이다.")


if __name__ == "__main__":
    main()
