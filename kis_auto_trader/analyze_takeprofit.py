"""익절 문턱을 끝까지 올려본다 - "900% 올랐으면 그냥 파는 게 이득 아니야?"

(2026-09-21 신설) 사용자의 반박이 출발점이다. 그 앞에서 나는 '기대수익의
k배 넘으면 매도' 를 k=1~3 으로만 재고 "이 계열은 안 된다" 고 말했다.
k=1~3 은 보유 5일이면 문턱이 0.45%, 120일이어도 32% 다. 즉 **큰 이익
구간을 한 번도 건드리지 않았다.** 그 상태로 계열 전체를 부정한 것은
과한 말이었다. 그래서 문턱을 +1000% 까지 올려서 다시 잰다.

두 가지를 잰다.
  1) 보유 중에 실제로 얼마나 오르나 (도달 분포)
  2) 문턱을 올릴수록 성과가 어떻게 변하나 (문턱 쓸기)

===========================================================================
1 - 이 종목들은 900% 가 안 오른다
===========================================================================
2021~2026, 저변동 10종목 / 120일 / 부분교체. 보유 구간 43건에서 **보유
중에 찍은 최고 평가수익** 의 분포:

    중앙       +22.0%
    상위 25%   +46.5%
    상위 10%   +61.4%
    최고      +203.0%

  문턱 도달 건수 (43건 중)
    +10%  이상   35건  (81.40%)
    +20%  이상   23건  (53.49%)
    +30%  이상   18건  (41.86%)
    +50%  이상    8건  (18.60%)
    +100% 이상    3건  ( 6.98%)
    +200% 이상    1건  ( 2.33%)
    +300% 이상    0건  ( 0.00%)
    +900% 이상    0건  ( 0.00%)

5.7년 동안 한 번도 +300% 에 닿은 적이 없다. 이건 우연이 아니라 선정
기준 때문이다. 저변동은 **크게 안 흔들리는 종목을 고르는 규칙** 이므로
900% 가 오를 만한 종목은 애초에 후보에서 빠진다. 설령 하나가 폭등했다면
그 순간 변동성이 커져서 다음 교체일에 순위 밖으로 밀려 자동으로 팔린다.

===========================================================================
2 - 그래도 문턱을 올리면 사용자 말이 맞는 쪽으로 간다
===========================================================================
'평가수익이 X% 넘으면 즉시 매도' (시작일 5개 중앙값)

    규칙          연수익%   낙폭%   매도수   기준 이긴
    없음           22.0    -15.9      0        -
    +20% 익절      17.6    -14.4     33      0/5
    +30% 익절      18.4    -13.1     24      1/5
    +50% 익절      18.2    -15.8     11      1/5
    +100% 익절     20.5    -15.7      3      3/5
    +200% 익절     22.4    -15.9      1      3/5
    +500% 익절     22.0    -15.9      0      0/5
    +1000% 익절    22.0    -15.9      0      0/5

**방향은 사용자가 맞다.** 문턱이 낮을수록 손해가 크고(-4.4%p), 올릴수록
손해가 줄고, +200% 에서는 근소하게 앞선다. "조금 벌었다고 파는 건 나쁘고
크게 벌었으면 파는 게 낫다" 는 직관이 숫자에도 그대로 있다.

다만 +200% 의 +0.4%p 는 **거래 1건** 이 만든 것이다. 5.7년에 한 번
걸린 종목 하나다. 반띵도 못 하고 신뢰구간도 못 그린다. 이걸 근거로
규칙을 넣는 것은 표본 1개로 결론 내는 것이다.

그리고 +500% 이상은 **매도 0건** 이다. 곡선이 '없음' 과 소수점까지
같다. 이건 규칙이 나쁘다는 뜻이 아니라 **한 번도 켜지지 않는다** 는
뜻이다.

===========================================================================
3 - 900% 는 발동하지 않는 규칙이다
===========================================================================
"900% 올랐으면 판다" 는 틀린 규칙이 아니다. **한 번도 발동하지 않는
규칙** 이다. 넣어도 성과가 안 변하고 빼도 안 변한다.

앞에서 내가 "이 계열은 안 된다" 고 한 것은 **잰 범위 안에서만** 맞는
말이었다. 정확히는 이렇다.

    문턱이 한 자릿수~수십 % 면 확실히 손해다 (0/5, 1/5).
    문턱이 세 자릿수면 손해가 사라지지만 발동을 거의 안 한다.

===========================================================================
3b - 그런데 2절의 표에는 군더더기가 하나 붙어 있었다 (--forward)
===========================================================================
2절은 판 돈을 **다음 교체일까지 현금으로** 둔다. 그래서 그 표는
"파는 게 나은가" 가 아니라 "팔고 현금으로 있는 게 나은가" 를 쟀다.
사용자의 질문("40일 뒤에 무조건 더 오른다고 확신하냐")에 맞는 것은
**문턱을 넘은 그 날부터 그 종목이 어떻게 되는가** 다.

  (시작일 5개를 합친 보유 구간 253건, 교체일까지의 수익률)
    조건               건수    평균    중앙   떨어진 비율
    +10% 넘은 날부터    199   13.94    5.28     34.7%
    +20% 넘은 날부터    142   11.56    4.76     35.9%
    +30% 넘은 날부터    107    8.06    1.52     43.9%
    +50% 넘은 날부터     51    8.65   -1.62     56.9%
    +100% 넘은 날부터    15    0.27    1.67     46.7%

**확신할 수 없다. 100% 가 아니다.** +50% 를 넘은 뒤로는 오히려 떨어지는
쪽이 더 많다 (56.9%, 중앙값 -1.62%). 교체일에 뭔가 터지는 구조가 아니고
교체일은 특별한 날이 아니다. 그냥 미리 정해둔 날일 뿐이다.

그런데도 들고 있는 게 이기는 이유는 **평균과 중앙값이 갈라지기** 때문
이다. +50% 구간의 중앙값은 -1.62% 인데 평균은 +8.65% 다. 대부분은 조금
지고 소수가 크게 이긴다. 10종목을 담으면 받는 것은 중앙값이 아니라
평균이다. 그래서 '거의 매번 파는 게 나았다' 와 '안 파는 게 낫다' 가
동시에 참일 수 있다.

===========================================================================
3c - 군더더기를 걷으면 익절이 기준을 넘는다 (--swap)
===========================================================================
현금으로 두지 말고 **팔자마자 다음 순위 종목을 산다.** 익절의 제일 강한
형태다.

    문턱      중앙   최소   5개중   전반   후반   반띵
    없음      22.0   16.7     -     8.5   15.6
    +20%      21.7   19.2   3/5     9.9   26.4   양쪽 이김
    +25%      20.6   16.2   3/5     7.8   33.8   뒤집힘
    +30%      22.8   19.4   4/5     8.9   33.4   양쪽 이김
    +35%      21.6   20.5   3/5     9.8   28.3   양쪽 이김
    +40%      20.2   13.8   2/5     9.1   25.3   양쪽 이김

+30% 가 기준 22.0% 를 넘는다 (22.8%, 4/5). 반띵도 통과한다. 그리고
**회전 대조군도 통과한다**: 같은 횟수(31건)를 아무거나 파는 것을 씨앗
20개로 돌리면 17.5 ~ 22.0 인데, 이익 규칙 22.8 은 20개 전부보다 위다.
즉 '이익이 났다' 는 조건 자체가 정보를 갖는다. 거울 규칙(-30% 손실이면
판다)은 21.6% 로 못 넘는다.

이 저장소에서 익절 계열이 대조군을 넘은 것은 이번이 처음이다.

**그래도 채택하지 않는다.** 이유가 셋이다.
  1) 이웃 문턱이 같이 안 움직인다. +25% 는 20.6% 로 기준에 지고 반띵도
     뒤집힌다. +35% 도 21.6% 로 진다. 진짜 효과라면 +-5% 에서 사라지지
     않는다. 22.8 은 봉우리 하나다 (analyze_knobs.py 의 채택 조건 1번).
  2) 최대낙폭이 나빠진다 (-15.9% -> -17.6%). 사용자의 목적은 '큰 이득을
     포기하더라도 큰 손해를 피한다' 이므로 방향이 반대다.
  3) 이득이 후반부에 몰려 있다. 전반부는 8.9 vs 8.5 로 사실상 차이가
     없고 후반부만 33.4 vs 15.6 이다. 시기 하나에 기댄 결과다.

즉 익절이 해로운 이유는 '파는 것' 자체가 아니라 **판 돈이 놀기** 때문
이었다. 그걸 고치면 해롭지 않게는 되는데, 기준을 확실히 이기지는
못한다.

===========================================================================
4 - 시간비례 문턱 (--slope)
===========================================================================
사용자의 원래 표현은 "이미 벌 수 있는 것 이상으로 이윤이 나면 판다"
였다. 고정 %가 아니라 **보유일에 비례하는 문턱** 이다.

    문턱 = 보유일 x 0.0896%/일 x k        (0.0896 은 analyze_why.py)

    규칙          연수익%   낙폭%   매도수   기준 이긴
    없음           22.0    -15.9      0        -
    기대의 1.0배     3.8     -8.8     76      0/5
    기대의 1.5배     5.0     -8.6     77      0/5
    기대의 2.0배     5.4     -7.9     73      0/5
    기대의 3.0배     6.0     -8.1     62      0/5

전부 크게 졌다. 이유는 2절과 같다. 보유 5일이면 문턱이 0.45% 라서
사실상 '조금만 오르면 판다' 가 되고, 그건 +20% 익절보다도 이르다.
낙폭이 작아진 것은 개선이 아니라 **현금으로 도망가 있는 시간이 길어서**
다 (매도 76건).

===========================================================================
읽는 법
===========================================================================
1) 43건은 적다. 시작일 하나(base=250)에서 센 보유 구간 수다. 분포의
   꼬리(+200% 1건)는 표본 1개이므로 확률 추정이 아니다.
2) 2021~2026 한국 시장이다. 폭등 종목이 흔한 시장이나 시기라면 분포가
   달라진다. 다만 그런 종목은 저변동 선정에 안 걸린다는 구조는 남는다.
3) 시간비례 문턱(기대의 k배)은 analyze_stops.py 의 고정 익절과 같은
   방향으로 졌다. 아래 --slope 로 재현한다.
4) 다중검정: 여기서 훑은 것은 고정 문턱 7개 + k 4개 + 재투자 문턱 5개
   = 16개다. 채택한 것은 없다(규칙을 추가하지 않는다).
5) 3c 는 **미해결로 남긴다.** 대조군을 넘은 것은 사실이고, 이웃이 안
   따라오는 것도 사실이다. 데이터가 더 쌓이면 다시 재볼 값이다.
   다시 잴 때의 조건을 미리 적어둔다: +25%/+30%/+35% 가 **셋 다**
   기준을 넘고, 낙폭이 -15.9% 보다 나빠지지 않을 것.

실행:
  python analyze_takeprofit.py            # 도달 분포 + 문턱 쓸기
  python analyze_takeprofit.py --slope    # 시간비례 문턱 (기대의 k배)
  python analyze_takeprofit.py --forward  # 문턱을 넘은 뒤로 더 오르나
  python analyze_takeprofit.py --swap     # 팔고 바로 다음 순위를 산다
"""
import pathlib
import random
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import analyze_knobs as K  # noqa: E402
import strategy as S  # noqa: E402

CAPITAL = E.CAPITAL
FEE_ONE_WAY = E.FEE_ONE_WAY
BASE_DI = 250
PERIOD = 120
PICK = 10
DAYS_PER_YEAR = 246
N_STARTS, START_GAP = 5, 37

# 문턱 쓸기. 세 자릿수까지 올려야 사용자의 900% 질문이 범위 안에 든다.
THRESHOLDS = (20, 30, 50, 100, 200, 500, 1000)
# 시간비례 문턱: 기대수익 = 보유일 x EDGE. 그 k 배를 넘으면 판다.
EDGE_PER_DAY = 0.0896   # analyze_why.py 에서 잰 하루 평균 %
KS = (1.0, 1.5, 2.0, 3.0)
# 앞 문턱들과 그 이웃. 이웃이 같이 안 움직이면 봉우리 하나는 잡음이다.
NEIGHBORS = (20, 25, 30, 35, 40)
FWD_LEVELS = (10, 20, 30, 50, 100)
N_CONTROL_SEEDS = 20


def threshold_at(held, k, edge=EDGE_PER_DAY):
    """시간비례 문턱%. 보유일이 늘면 문턱도 같이 올라간다.

    고정 익절과 다른 점이 여기다. 5일 보유면 0.45%, 120일이면 10.8%
    (k=1). 사용자의 '벌 수 있는 것 이상으로 벌면 판다' 를 그대로 옮긴
    것이다.
    """
    return edge * held * k


def run(dates, panel, order, start, tp=None, k=None, upto=None, collect=None):
    """부분교체 + 익절 문턱. (곡선, 매도횟수)

    tp      고정 문턱%. 평가수익이 넘으면 즉시 매도.
    k       시간비례 문턱. threshold_at(보유일, k) 를 넘으면 매도.
    collect 리스트를 주면 보유 구간마다 (보유중최고%, 나갈때%, 보유일) 기록.

    tp 와 k 는 같이 쓰지 않는다.
    """
    n = upto or len(dates)
    cash, hold, basis, entry, peak = float(CAPITAL), {}, {}, {}, {}
    curve, di, nsell = [], start, 0
    while di < n:
        if (di - start) % PERIOD == 0 and di in order:
            new = order[di][:PICK]
            for c in [c for c in hold if c not in new]:
                v = E.price(panel, c, di)
                if v:
                    cash += hold[c] * v * (1 - FEE_ONE_WAY)
                if collect is not None and basis.get(c):
                    out = (v / basis[c] - 1) * 100 if v else 0.0
                    collect.append((peak.get(c, 0.0), out, di - entry[c]))
            keep = {c: q for c, q in hold.items() if c in new}
            add = [c for c in new if c not in hold]
            got, cash, _f = (E.buy_greedy(panel, cash, add, di) if add
                             else ({}, cash, 0.0))
            for c in got:
                basis[c] = E.price(panel, c, di) or 0
                entry[c] = di
                peak[c] = 0.0
            hold = {**keep, **got}
        for c in list(hold):
            px = E.price(panel, c, di, "close")
            if not px or not basis.get(c):
                continue
            gain = (px / basis[c] - 1) * 100
            if gain > peak.get(c, 0.0):
                peak[c] = gain
            held = di - entry[c]
            line = (tp if tp is not None else
                    (threshold_at(held, k) if k is not None and held >= 1
                     else None))
            if line is not None and gain > line:
                cash += hold[c] * px * (1 - FEE_ONE_WAY)
                del hold[c]
                nsell += 1
                if collect is not None:
                    collect.append((peak[c], gain, held))
        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, nsell


def annualized(curve, capital=CAPITAL):
    if not curve:
        return 0.0
    return ((curve[-1] / capital) ** (DAYS_PER_YEAR / len(curve)) - 1) * 100


def mdd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def reach_counts(peaks, levels=(10, 20, 30, 50, 100, 200, 300, 900)):
    """각 문턱에 도달한 보유 구간 수. 900% 가 몇 건인지가 질문의 핵심이다."""
    return [(t, sum(1 for p in peaks if p >= t)) for t in levels]


def quantile(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    return sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))]


def _starts():
    return [BASE_DI + i * START_GAP for i in range(N_STARTS)]


def report_distribution(dates, panel, order):
    rec = []
    run(dates, panel, order, BASE_DI, collect=rec)
    rec = [r for r in rec if r[2] > 0]
    peaks = sorted(r[0] for r in rec)
    print(f"\n[1] 보유 구간 {len(peaks)}건 - 보유 중 찍은 최고 평가수익")
    for q, name in ((0.5, "중앙"), (0.75, "상위25%"),
                    (0.9, "상위10%"), (1.0, "최고")):
        print(f"  {name:<8}{quantile(peaks, q):>9.1f}%")
    print("  문턱 도달 건수")
    for t, n in reach_counts(peaks):
        pct = n / len(peaks) * 100 if peaks else 0.0
        print(f"    +{t}% 이상 : {n:>4}건 ({pct:>5.2f}%)")
    return peaks


def report_sweep(dates, panel, order, slope=False):
    starts = _starts()
    base_r = [annualized(run(dates, panel, order, s)[0]) for s in starts]
    base_d = [mdd(run(dates, panel, order, s)[0]) for s in starts]
    title = "기대의 k배 넘으면 매도" if slope else "평가수익 X% 넘으면 즉시 매도"
    print(f"\n[2] '{title}' (시작일 {N_STARTS}개 중앙값)")
    print(f"{'규칙':<18}{'연수익%':>9}{'낙폭%':>9}{'매도수':>8}{'기준 이긴':>10}")
    print(f"{'없음':<18}{st.median(base_r):>9.1f}{st.median(base_d):>9.1f}"
          f"{0:>8}{'-':>10}")
    rows = []
    for x in (KS if slope else THRESHOLDS):
        rs, ds, ns = [], [], []
        for s in starts:
            kw = {"k": x} if slope else {"tp": x}
            c, nse = run(dates, panel, order, s, **kw)
            rs.append(annualized(c))
            ds.append(mdd(c))
            ns.append(nse)
        wins = sum(1 for i in range(len(starts)) if rs[i] > base_r[i])
        label = f"기대의 {x}배" if slope else f"+{x}% 익절"
        rows.append((label, st.median(rs), st.median(ds), st.median(ns), wins))
        print(f"{label:<18}{rows[-1][1]:>9.1f}{rows[-1][2]:>9.1f}"
              f"{rows[-1][3]:>8.0f}{f'{wins}/{len(starts)}':>10}", flush=True)
    return rows


def segments(dates, panel, order, start):
    """규칙 없는 지금 방식의 보유 구간 (종목, 진입di, 청산di, 기준가).

    '문턱을 넘은 뒤로 더 오르나' 를 재려면 먼저 실제 보유 구간이 있어야
    한다. 곡선이 아니라 구간을 돌려준다.
    """
    n = len(dates)
    cash, hold, basis, entry = float(CAPITAL), {}, {}, {}
    segs, di = [], start
    while di < n:
        if (di - start) % PERIOD == 0 and di in order:
            new = order[di][:PICK]
            for c in [c for c in hold if c not in new]:
                v = E.price(panel, c, di)
                if v:
                    cash += hold[c] * v * (1 - FEE_ONE_WAY)
                segs.append((c, entry[c], di, basis[c]))
            keep = {c: q for c, q in hold.items() if c in new}
            add = [c for c in new if c not in hold]
            got, cash, _f = (E.buy_greedy(panel, cash, add, di) if add
                             else ({}, cash, 0.0))
            for c in got:
                basis[c] = E.price(panel, c, di) or 0
                entry[c] = di
            hold = {**keep, **got}
        di += 1
    for c in hold:
        segs.append((c, entry[c], n - 1, basis[c]))
    return [s for s in segs if s[2] > s[1] and s[3]]


def forward_after(panel, segs, level):
    """문턱을 처음 넘은 날부터 청산일까지의 수익률% 목록.

    사용자의 질문 그대로다: 넘은 다음에 더 오르나, 떨어지나. 여기에는
    '판 돈을 현금으로 둔다' 는 군더더기가 안 붙는다.
    """
    out = []
    for c, e, x, bs in segs:
        hit = None
        for d in range(e + 1, x):
            p = E.price(panel, c, d, "close")
            if p and (p / bs - 1) * 100 >= level:
                hit = d
                break
        if hit is None:
            continue
        a = E.price(panel, c, hit, "close")
        b = E.price(panel, c, x, "close")
        if a and b:
            out.append((b / a - 1) * 100)
    return out


def run_swap(dates, panel, order, start, tp=None, mode="win",
             upto=None, seed=0, prob=0.0):
    """팔면 현금으로 두지 않고 곧바로 다음 순위 종목을 산다.

    mode 는 대조군을 위한 것이다.
      win   평가수익이 +tp% 를 넘으면 판다 (사용자의 규칙)
      lose  평가수익이 -tp% 밑이면 판다 (거울)
      rand  같은 빈도로 아무거나 판다 (회전 자체의 효과)

    rand 가 핵심이다. '이익이 났으니 판다' 가 버는 건지, 그냥 새 저변동
    종목으로 갈아타는 회전이 버는 건지 갈라야 하기 때문이다.
    """
    rng = random.Random(seed)
    n = upto or len(dates)
    cash, hold, basis = float(CAPITAL), {}, {}
    banned = set()
    curve, di, nsell = [], start, 0
    while di < n:
        if (di - start) % PERIOD == 0 and di in order:
            new = order[di][:PICK]
            for c in [c for c in hold if c not in new]:
                v = E.price(panel, c, di)
                if v:
                    cash += hold[c] * v * (1 - FEE_ONE_WAY)
            keep = {c: q for c, q in hold.items() if c in new}
            add = [c for c in new if c not in hold]
            got, cash, _f = (E.buy_greedy(panel, cash, add, di) if add
                             else ({}, cash, 0.0))
            for c in got:
                basis[c] = E.price(panel, c, di) or 0
            hold = {**keep, **got}
            banned = set()
        elif tp is not None and di in order:
            for c in list(hold):
                px = E.price(panel, c, di, "close")
                if not px or not basis.get(c):
                    continue
                gain = (px / basis[c] - 1) * 100
                fire = (gain > tp if mode == "win" else
                        gain < -tp if mode == "lose" else
                        rng.random() < prob)
                if not fire:
                    continue
                cash += hold[c] * px * (1 - FEE_ONE_WAY)
                del hold[c]
                nsell += 1
                banned.add(c)
                nxt = [x for x in order[di]
                       if x not in hold and x not in banned]
                if nxt:
                    got, cash, _f = E.buy_greedy(panel, cash, nxt[:1], di)
                    for c2 in got:
                        basis[c2] = E.price(panel, c2, di) or 0
                    hold.update(got)
        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, nsell


def match_prob(dates, panel, order, starts, target, lo=0.0, hi=0.02, rounds=25):
    """무작위 대조군이 이익 규칙과 같은 횟수를 팔도록 확률을 맞춘다.

    횟수가 다르면 수수료와 회전량이 달라져서 비교가 안 된다.
    """
    prob = 0.0
    for _ in range(rounds):
        prob = (lo + hi) / 2
        m = st.median(run_swap(dates, panel, order, s, tp=30, mode="rand",
                               seed=11, prob=prob)[1] for s in starts)
        if m < target:
            lo = prob
        else:
            hi = prob
    return prob


def report_forward(dates, panel, order):
    """[3] 문턱을 넘은 그 날부터 청산일까지 - 사용자 질문에 직접 답한다."""
    starts = _starts()
    segs = []
    for s in starts:
        segs += segments(dates, panel, order, s)
    print(f"\n[3] 문턱을 넘은 날부터 교체일까지 ({len(segs)}개 보유 구간)")
    print(f"{'조건':<22}{'건수':>6}{'평균':>9}{'중앙':>9}{'떨어진 비율':>12}")
    rows = []
    for t in FWD_LEVELS:
        v = forward_after(panel, segs, t)
        if not v:
            continue
        down = sum(1 for x in v if x < 0) / len(v) * 100
        rows.append((t, len(v), st.mean(v), st.median(v), down))
        print(f"{'+'+str(t)+'% 넘은 날부터':<22}{len(v):>6}{st.mean(v):>9.2f}"
              f"{st.median(v):>9.2f}{down:>11.1f}%", flush=True)
    return rows


def report_swap(dates, panel, order):
    """[4] 판 돈을 놀리지 않는 판 - 익절의 제일 강한 형태."""
    starts = _starts()
    half = BASE_DI + (len(dates) - BASE_DI) // 2
    base_r = [annualized(run_swap(dates, panel, order, s)[0]) for s in starts]
    ba = annualized(run_swap(dates, panel, order, BASE_DI, upto=half)[0])
    bb = annualized(run_swap(dates, panel, order, half)[0])
    print(f"\n[4] '+X% 넘으면 팔고 곧바로 다음 순위를 산다'")
    print(f"{'문턱':<10}{'중앙':>8}{'최소':>8}{'5개중':>8}{'전반':>8}{'후반':>8}  반띵")
    print(f"{'없음':<10}{st.median(base_r):>8.1f}{min(base_r):>8.1f}"
          f"{'-':>8}{ba:>8.1f}{bb:>8.1f}")
    for tp in NEIGHBORS:
        rs = [annualized(run_swap(dates, panel, order, s, tp=tp)[0])
              for s in starts]
        w = sum(1 for i in range(len(starts)) if rs[i] > base_r[i])
        x = annualized(run_swap(dates, panel, order, BASE_DI, tp=tp,
                                upto=half)[0])
        y = annualized(run_swap(dates, panel, order, half, tp=tp)[0])
        v = ("양쪽 이김" if x > ba and y > bb else
             "뒤집힘" if (x > ba) != (y > bb) else "양쪽 짐")
        print(f"{'+'+str(tp)+'%':<10}{st.median(rs):>8.1f}{min(rs):>8.1f}"
              f"{f'{w}/{len(starts)}':>8}{x:>8.1f}{y:>8.1f}  {v}", flush=True)

    # 회전 대조군 - 이익 조건이 정보를 갖는지
    win = st.median(annualized(run_swap(dates, panel, order, s, tp=30)[0])
                    for s in starts)
    nsw = st.median(run_swap(dates, panel, order, s, tp=30)[1] for s in starts)
    prob = match_prob(dates, panel, order, starts, nsw)
    vals = sorted(
        st.median(annualized(run_swap(dates, panel, order, s, tp=30,
                                      mode="rand", seed=sd, prob=prob)[0])
                  for s in starts)
        for sd in range(100, 100 + N_CONTROL_SEEDS))
    above = sum(1 for v in vals if v >= win)
    print(f"\n  회전 대조군 (같은 횟수 {nsw:.0f}건을 아무거나 판다, "
          f"씨앗 {N_CONTROL_SEEDS}개)")
    print(f"    최소 {vals[0]:.1f}  중앙 {st.median(vals):.1f}  "
          f"최대 {vals[-1]:.1f}   <->  이익 규칙 {win:.1f}")
    print(f"    이익 규칙 이상인 무작위: {above}/{len(vals)}개")
    mir = st.median(annualized(run_swap(dates, panel, order, s, tp=30,
                                        mode="lose")[0]) for s in starts)
    print(f"  거울 규칙 (-30% 손실 나면 판다): {mir:.1f}%")
    return vals, win


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    slope = "--slope" in argv
    dates, panel = S.load_panel()
    print("순위 계산 중...", flush=True)
    order = K.ranks(dates, panel, BASE_DI)
    if slope:
        report_sweep(dates, panel, order, slope=True)
        print("\n시간비례 문턱은 k=1~3 전부 졌다. 문턱이 작아서 (보유 5일이면"
              " 0.45%)\n오를 여지가 남은 종목을 곧바로 내보내기 때문이다.")
        return 0
    if "--forward" in argv:
        report_forward(dates, panel, order)
        print("\n+50% 를 넘으면 그 뒤로 떨어지는 쪽이 더 많다 (56.9%). 그런데"
              " 평균은\n+8.65% 다. 10종목을 담으면 받는 것은 중앙값이 아니라"
              " 평균이다.")
        return 0
    if "--swap" in argv:
        report_swap(dates, panel, order)
        print("\n판 돈을 놀리지 않으면 익절이 기준을 넘는다 (+30%, 22.8%)."
              " 회전 대조군도\n넘는다. 다만 이웃 문턱이 같이 안 움직이고"
              " 낙폭은 나빠진다. 채택 안 한다.")
        return 0
    report_distribution(dates, panel, order)
    report_sweep(dates, panel, order)
    print("\n+500% 이상은 매도 0건 - 규칙이 나쁜 게 아니라 한 번도 켜지지"
          " 않는다.\n낮은 문턱은 확실히 손해다. 높은 문턱은 하는 일이 없다.")
    print("판 돈을 현금으로 두는 판이다. --swap 으로 재투자하는 판도 보라.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
