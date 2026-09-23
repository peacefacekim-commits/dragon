"""안 흔들리는 종목을 전제로 - 얼마나 자주 갈아탈까, 그 안에서 뭘 고를까.

(2026-09-18 신설) 사용자: "안흔들리는 종목을 전제로 검증을 해볼래? 그 종목에서
얻을 수 있는 지표 그리고 샀다 팔았다 하는 것보다 그냥 계속 가지고 있는게 더
나은지"

두 가지를 본다. 저변동 종목을 고르는 것 자체는 이미 검증됐으므로 전제로 둔다.

===========================================================================
(1) 얼마나 자주 갈아타야 하나  --what rebal
===========================================================================

전에 "매달 갈아타기 +79.8% vs 처음 10종목 사놓기 +57.8% = +22.0%p" 라고
보고했는데 그건 **시작일 하나** 로만 계산한 값이었다. 시작일이 운이었을 수
있으므로 시작일을 20개로 바꿔가며 다시 쟀다. 낙폭은 일별 평가금액으로 잰다.

!! 아래 표에도 결함이 있다 (2026-09-18 확인). 시작일 20개가 142~161일째,
   즉 2021년 7~8월의 연속된 20일이고 전부 끝까지 달린다. 사실상 같은 5년
   기간 하나를 20번 센 것이다. 그래서 '범위' 는 서로 다른 장세가 아니라
   며칠에 들어갔나의 잔차이고, 20개가 다 양수인 것도 같은 기간을 20번
   센 결과다. 서로 다른 장세를 보려면 analyze_windows.py 를 볼 것 -
   거기서는 1년 창 51개 중 16개(31%)가 손실로 끝났다.
   아래 '갈아타기 주기 비교' 자체는 같은 기간 안에서 주기만 바꾼 비교라
   여전히 쓸모가 있다 (같은 조건에서 20일 vs 120일). 다만 절대 수익 숫자를
   '이 전략의 기대수익' 으로 읽으면 안 된다.

결과 (약 5.0년, 시작일 20개의 중간값과 범위)

  방식              누적(중간값)   범위               연평균  최악낙폭  수수료 교체
  20일마다 (지금)     + 94.7%  [+85.7 ~ +162.6]   +14.2%  -21.0%  13.2%  63회
  60일마다 (3달)      + 93.0%  [+73.1 ~ +124.6]   +14.0%  -18.0%   4.4%  21회
  120일마다 (6달)     +105.9%  [+73.7 ~ +148.2]   +15.4%  -20.5%   2.3%  11회
  250일마다 (1년)     +105.1%  [+78.9 ~ +126.5]   +15.4%  -33.2%   1.1%   5회
  한 번 사고 끝까지    + 87.0%  [+57.6 ~ +151.3]   +13.3%  -31.5%   0.2%   1회

같은 시작일끼리 짝지어 비교 (갈아타기 - 사놓기. 시작일 운이 상쇄된다)

  20일마다    중간값 +12.5%p  범위 [-42.4 ~ +83.7]  사놓기를 이긴 시작일 14/20
  60일마다    중간값 + 1.6%p  범위 [-53.9 ~ +41.3]                      12/20
  120일마다   중간값 +16.1%p  범위 [-30.8 ~ +57.2]                      12/20
  250일마다   중간값 +14.8%p  범위 [-56.9 ~ +58.9]                      14/20

읽는 법

  a) 갈아타는 게 낫긴 하지만 차이가 작고 불안정하다. 20/20 이 아니라
     12~14/20 이고, 시작일에 따라 -50%p ~ +80%p 까지 벌어진다. 전에 보고한
     +22.0%p 는 운 좋은 시작일 하나였고, 정직한 중간값은 +12.5%p 다.
  b) **120일(6개월)마다가 제일 낫다.** 누적이 가장 높고(+105.9%) 수수료는
     2.3% 로 20일 방식(13.2%)의 1/6 이다. 20일마다 갈아타며 내는 수수료
     11%p 가 그냥 낭비였다.
  c) 한 번 사고 끝까지는 낙폭이 -31.5% 로 크게 나빠진다. 시간이 지나면
     그 종목들이 더 이상 '안 흔들리는 종목' 이 아니게 되기 때문이다. 즉
     갈아타기의 값은 수익이 아니라 **낙폭 관리** 에 있다.
  d) 250일(1년)마다도 수익은 같지만 낙폭이 -33.2% 다. 1년은 너무 길다.

===========================================================================
(2) 저변동 풀 안에서 뭘 고를까  --what signals
===========================================================================

저변동 60종목을 후보로 고정하고, 그 안에서 10종목을 고르는 데 쓸 수 있는
지표 14개를 전부 훑었다. 대조군은 회차마다 풀 안에서 그 지표값만 무작위로
섞기 - '이 지표로 고르는 것' 과 '풀에서 아무거나 10개' 의 차이만 남는다.

결과 (55회차. hi52/12개월모멘텀이 1년 이력을 요구해서 62회차보다 적다)
풀 전체 동일가중 +1.155%/회차 (누적 +71.0%)

  지표            방향     평균    풀대비     누적    낙폭 | 전반부  후반부 부호 | 우연
  hi52         높은쪽  +2.084  +0.929  +171.0  -19.8 | +0.081 +1.747  O |  1.7% O
  12개월모멘텀    높은쪽  +1.953  +0.798  +148.0  -24.9 | +0.165 +1.409  O |  2.3% O
  개인수급        높은쪽  +1.768  +0.613  +134.8  -17.1 | +0.882 +0.353  O |  6.9%
  회전율         높은쪽  +1.702  +0.548  +124.3  -21.6 | +0.426 +0.665  O | 10.3%
  변동성         낮은쪽  +1.522  +0.367  +115.6  -12.8 | +0.521 +0.219  O | 19.4%
  price        낮은쪽  +1.477  +0.322   +92.0  -29.6 | +0.495 +0.155  O | 21.4%
  외국인수급      낮은쪽  +1.459  +0.304   +99.6  -19.4 | +0.542 +0.075  O | 23.8%
  기관수급        낮은쪽  +1.350  +0.195   +90.3  -24.7 | +0.078 +0.307  O | 30.1%
  gap_pct      낮은쪽  +1.317  +0.162   +89.1  -20.7 | +0.280 +0.048  O | 36.3%
  5일수익        낮은쪽  +1.240  +0.085   +72.1  -22.9 | +0.427 -0.244  X | 39.7%
  beta         낮은쪽  +0.961  -0.194   +54.6  -18.1 | +0.593 -0.953  X | 66.7%
  20일수익       낮은쪽  +0.918  -0.237   +44.0  -26.0 | +0.105 -0.567  X | 71.3%
  vol_surge    낮은쪽  +0.770  -0.385   +34.0  -25.4 | -0.035 -0.723  O | 85.3%
  거래대금        낮은쪽  +0.586  -0.568   +17.2  -29.1 | +0.058 -1.172  X | 92.0%

  통과 2/14 (우연 기대값 0.7). 부호 양쪽 일치 10/14 (우연이면 7.0).

읽는 법

  a) 새로 통과한 둘 - hi52(52주 고점 근처)와 12개월모멘텀 - 은 사실상
     같은 것이다. '최근 1년 잘 오른 종목' 을 두 방식으로 잰 것이라
     독립된 증거 두 개가 아니다.
  b) 그 둘은 효과가 후반부에 몰려 있다 (hi52 전반부 +0.081 / 후반부
     +1.747). 부호는 양쪽 같지만 크기가 20배 차이다. 고르게 나오는 쪽이
     믿을 만한데 그렇지 않다.
  c) 14개를 봤으므로 보정하면 1.7% x 14 = 24%, 2.3% x 14 = 32% 다. 둘 다
     보정 후에는 유의하지 않다.
  d) **어제 통과한 개인수급이 여기서는 6.9% 로 탈락했다.** 바뀐 것은
     회차 수뿐이다 (62 -> 55. hi52 계산에 1년 이력이 필요해서 앞쪽 회차가
     빠졌다). 표본을 7개 뺐더니 1.3% 가 6.9% 가 됐다는 뜻이고, 어제의
     결과가 그만큼 약하다는 신호다.
  e) 주목할 대비: 전체 200종목에서 모멘텀으로 고르면 최악이었다
     (-3.657%/회차, strategy.py). 그런데 저변동 풀 안에서는 모멘텀이
     양수다. '안 흔들리는 종목 중에 잘 오르던 것' 과 '전체에서 잘 오르던
     것' 은 다른 물건이다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_lowvol.py --what rebal     # 얼마나 자주 갈아탈까
    python analyze_lowvol.py --what signals   # 뭘 고를까
"""
import pathlib as _pathlib
# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = str(_pathlib.Path(__file__).resolve().parent)
import argparse
import sys


def run_rebal():
    import statistics as st
    import sys

    sys.path.insert(0, _ROOT)
    import strategy as S  # noqa: E402

    FEE = S.FEE_ROUND_TRIP_PCT
    POOL_PICK = 10
    N_STARTS = 20

    dates, panel = S.load_panel()
    N = len(dates)
    START0 = max(140, S.LIQUIDITY_DAYS + 2)


    def picks_at(di):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(v, c) for c in cand
              if (v := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(sc) < POOL_PICK:
            return []
        sc.sort(reverse=True)
        return [c for _s, c in sc[:POOL_PICK]]


    def basket_curve(codes, i0, i1):
        """i0 시가에 사서 i1 까지 들고 있을 때의 일별 평가배수 + 끊김 수.

        데이터가 끊긴 종목은 마지막 종가에서 얼어붙는다 (실제 폐지는 더 나쁘다).
        """
        entry, last = {}, {}
        for c in codes:
            s = panel.get(c)
            j = s.pos.get(i0) if s else None
            if j is None or not s.open[j]:
                continue
            entry[c] = s.open[j]
            last[c] = s.close[j]
        if not entry:
            return None, 0
        curve, cut = [], 0
        for i in range(i0, i1 + 1):
            vals = []
            for c in entry:
                s = panel[c]
                j = s.pos.get(i)
                if j is not None:
                    last[c] = s.close[j]
                vals.append(last[c] / entry[c])
            curve.append(st.mean(vals))
        for c in entry:
            s = panel[c]
            if s.pos.get(i1) is None:
                cut += 1
        return curve, cut


    def run_scheme(i0, i1, period):
        """period 거래일마다 갈아타기. period=None 이면 갈아타지 않는다.

        -> (일별 평가배수, 리밸런스 횟수, 끊김 누적)
        """
        equity, curve, n_rebal, cuts = 1.0, [], 0, 0
        i = i0
        while i < i1:
            j = i1 if period is None else min(i + period, i1)
            codes = picks_at(i)
            if not codes:
                i = j
                continue
            seg, cut = basket_curve(codes, i, j)
            if seg is None:
                i = j
                continue
            cuts += cut
            # 매수·매도 수수료는 구간 시작에 한 번
            base = equity * (1 - FEE / 100)
            curve.extend(base * v for v in seg[:-1])
            equity = base * seg[-1]
            n_rebal += 1
            i = j
        curve.append(equity)
        return curve, n_rebal, cuts


    def mdd(curve):
        peak, worst = curve[0], 0.0
        for v in curve:
            peak = max(peak, v)
            worst = min(worst, v / peak - 1)
        return worst * 100


    SCHEMES = [("20일마다 (지금)", 20), ("60일마다 (3달)", 60),
               ("120일마다 (6달)", 120), ("250일마다 (1년)", 250),
               ("한 번 사고 끝까지", None)]

    starts = [START0 + k for k in range(N_STARTS)]
    i1 = N - 1
    years = (i1 - START0) / 250

    print(f"기간 {dates[START0]} ~ {dates[i1]}  약 {years:.1f}년")
    print(f"시작일 {N_STARTS}개로 각각 계산해서 중간값과 범위를 본다\n")
    print("=" * 96)
    print(f"  {'방식':<20} {'누적수익':>26} {'연평균':>8} "
          f"{'최악낙폭':>22} {'교체':>5} {'수수료':>7} {'끊김':>5}")
    print("=" * 96)

    for label, period in SCHEMES:
        cums, mdds, nrs, cutss = [], [], [], []
        for i0 in starts:
            curve, nr, cuts = run_scheme(i0, i1, period)
            cums.append((curve[-1] - 1) * 100)
            mdds.append(mdd(curve))
            nrs.append(nr)
            cutss.append(cuts)
        cums.sort()
        mdds.sort()
        med = cums[len(cums) // 2]
        annual = ((1 + med / 100) ** (1 / years) - 1) * 100
        print(f"  {label:<20} {med:>+8.1f}% [{cums[0]:>+7.1f} ~ {cums[-1]:>+7.1f}] "
              f"{annual:>+7.1f}% {mdds[len(mdds)//2]:>+8.1f}% "
              f"[{mdds[0]:>+6.1f} ~ {mdds[-1]:>+6.1f}] "
              f"{st.mean(nrs):>5.0f} {st.mean(nrs)*FEE:>6.1f}% "
              f"{st.mean(cutss):>5.1f}")

    print("\n" + "=" * 96)
    print("=== 같은 시작일끼리 짝지어 비교: 갈아타기 - 사놓기 ===")
    print("=== (시작일이 같으므로 운이 상쇄된다. 양수면 갈아타기가 나은 것) ===")
    print("=" * 96)
    base_by_start = {}
    for i0 in starts:
        curve, _nr, _c = run_scheme(i0, i1, None)
        base_by_start[i0] = (curve[-1] - 1) * 100

    for label, period in SCHEMES[:-1]:
        diffs = []
        for i0 in starts:
            curve, _nr, _c = run_scheme(i0, i1, period)
            diffs.append((curve[-1] - 1) * 100 - base_by_start[i0])
        diffs.sort()
        wins = sum(1 for d in diffs if d > 0)
        print(f"  {label:<20} 중간값 {diffs[len(diffs)//2]:>+8.1f}%p  "
              f"범위 [{diffs[0]:>+8.1f} ~ {diffs[-1]:>+8.1f}]  "
              f"사놓기를 이긴 시작일 {wins}/{len(diffs)}")


def run_signals():
    import csv
    import glob
    import math
    import statistics as st
    import sys

    import numpy as np

    sys.path.insert(0, _ROOT)
    import strategy as S  # noqa: E402

    HOLD, POOL, PICK = 20, 60, 10
    FEE = S.FEE_ROUND_TRIP_PCT
    N_PERM = 1500
    rng = np.random.default_rng(20260926)

    dates, panel = S.load_panel()
    N = len(dates)
    START = max(140, S.LIQUIDITY_DAYS + 2)

    flow = {}
    for path in sorted(glob.glob(f"{_ROOT}/data/krx_flow_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    flow[(r["date"], r["code"])] = (
                        float(r["inst"]), float(r["foreign"]), float(r["indiv"]))
                except (TypeError, ValueError):
                    pass


    def rec_for(code, di, pool_ret):
        """di 진입일 기준, 전날까지만 쓰는 지표들."""
        s = panel.get(code)
        if s is None:
            return None
        j = s.pos.get(di - 1)
        if j is None or j < 260 or not s.value[j] or not s.close[j]:
            return None
        f = flow.get((dates[di - 1], code))
        if f is None:
            return None
        r, _cut = S.trade_return(panel, code, di, di + HOLD)
        if r is None:
            return None
        v, px = s.value[j], s.close[j]
        out = {"code": code, "ret": r}

        # --- 수급 3종 (어제 것)
        out["기관수급"] = f[0] / v
        out["외국인수급"] = f[1] / v
        out["개인수급"] = f[2] / v

        # --- 가격에서 나오는 것들
        j5, j20, j60, j250 = (s.pos.get(di - 6), s.pos.get(di - 21),
                              s.pos.get(di - 61), s.pos.get(di - 251))
        if None in (j5, j20, j60, j250):
            return None
        out["5일수익"] = (px / s.close[j5] - 1) * 100
        out["20일수익"] = (px / s.close[j20] - 1) * 100
        out["12개월모멘텀"] = (s.close[j5] / s.close[j250] - 1) * 100

        win = [s.close[k] for k in range(max(0, j - 59), j + 1)]
        drs = [win[k] / win[k - 1] - 1 for k in range(1, len(win))]
        if len(drs) < 30:
            return None
        out["변동성"] = st.pstdev(drs) * 100
        out["hi52"] = px / max(s.close[k] for k in range(j250, j + 1))

        # 거래량 급증
        v5 = st.mean([s.value[k] for k in range(j - 4, j + 1)])
        v60 = st.mean([s.value[k] for k in range(j - 59, j + 1)])
        out["vol_surge"] = v5 / v60 if v60 else 1.0

        # 갭 (시가 - 전일종가). 패널에 고가/저가가 없어서 일중 변동폭은 못 낸다.
        gp = []
        for k in range(j - 19, j + 1):
            if k > 0 and s.close[k - 1] and s.open[k]:
                gp.append(abs(s.open[k] / s.close[k - 1] - 1) * 100)
        if len(gp) < 10:
            return None
        out["gap_pct"] = st.mean(gp)

        # 시장(풀 평균) 대비 민감도
        mk = pool_ret
        if len(mk) == len(drs):
            mm, dm = st.mean(mk), st.mean(drs)
            varm = sum((x - mm) ** 2 for x in mk)
            out["beta"] = (sum((x - mm) * (y - dm) for x, y in zip(mk, drs))
                           / varm) if varm else 1.0
        else:
            out["beta"] = 1.0

        out["price"] = px
        out["거래대금"] = v
        out["회전율"] = v / px if px else 0.0     # = 거래량
        return out


    KEYS = ["기관수급", "외국인수급", "개인수급", "5일수익", "20일수익",
            "12개월모멘텀", "변동성", "hi52", "vol_surge",
            "gap_pct", "beta", "price", "거래대금", "회전율"]

    rounds = []
    di = START
    while di + HOLD < N:
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        vols = [(v, c) for c in cand
                if (v := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(vols) < POOL:
            di += HOLD
            continue
        vols.sort(reverse=True)
        pool = [c for _s, c in vols[:POOL]]

        # 풀 평균 일간수익 (beta 계산용)
        series = []
        for k in range(di - 60, di - 1):
            rs = []
            for c in pool:
                s = panel[c]
                a, b = s.pos.get(k), s.pos.get(k + 1)
                if a is not None and b is not None and s.close[a]:
                    rs.append(s.close[b] / s.close[a] - 1)
            series.append(st.mean(rs) if rs else 0.0)

        recs = [r for c in pool if (r := rec_for(c, di, series)) is not None]
        if len(recs) >= 2 * PICK:
            rounds.append((dates[di], recs))
        di += HOLD

    print(f"회차 {len(rounds)}개, 회차당 평균 "
          f"{st.mean([len(r) for _d, r in rounds]):.0f}종목")
    print(f"지표 {len(KEYS)}개를 본다 -> 통과한 것의 우연 비율에 "
          f"{len(KEYS)}을 곱해서 읽어야 한다\n")

    base = [st.mean([r["ret"] for r in recs]) - FEE for _d, recs in rounds]
    half = len(rounds) // 2


    def top(recs, key, sign):
        xs = sorted(recs, key=lambda r: -sign * r[key])
        return st.mean([r["ret"] for r in xs[:PICK]]) - FEE


    def cum(xs):
        v = 1.0
        for x in xs:
            v *= (1 + x / 100)
        return (v - 1) * 100


    def mdd(xs):
        v, peak, worst = 1.0, 1.0, 0.0
        for x in xs:
            v *= (1 + x / 100)
            peak = max(peak, v)
            worst = min(worst, v / peak - 1)
        return worst * 100


    print("=" * 104)
    print(f"=== 저변동 {POOL}종목 중 {PICK}개 고르기. 풀 전체 동일가중 "
          f"{st.mean(base):+.3f}%/회차 (누적 {cum(base):+.1f}%) ===")
    print("=" * 104)
    print(f"  {'지표':<14} {'방향':>6} {'평균':>8} {'풀대비':>8} {'누적':>9} "
          f"{'낙폭':>8} | {'전반부':>8} {'후반부':>8} {'부호':>5} | {'우연':>7}")

    rowsout = []
    for k in KEYS:
        # 방향은 전반부에서만 정한다
        a_hi = st.mean([top(recs, k, +1) for _d, recs in rounds[:half]])
        a_lo = st.mean([top(recs, k, -1) for _d, recs in rounds[:half]])
        sign = +1 if a_hi >= a_lo else -1
        real = [top(recs, k, sign) for _d, recs in rounds]
        real_m = st.mean(real)
        h1 = st.mean(real[:half]) - st.mean(base[:half])
        h2 = st.mean(real[half:]) - st.mean(base[half:])
        perm = []
        for _ in range(N_PERM):
            tot = 0.0
            for _d, recs in rounds:
                order = rng.permutation(len(recs))
                sh = [{**r, k: recs[order[i]][k]} for i, r in enumerate(recs)]
                tot += top(sh, k, sign)
            perm.append(tot / len(rounds))
        perm.sort()
        beat = sum(1 for x in perm if x >= real_m) / len(perm)
        rowsout.append((k, sign, real_m, real_m - st.mean(base), cum(real),
                        mdd(real), h1, h2, beat))

    for k, sign, m, ex, c, d, h1, h2, beat in sorted(rowsout, key=lambda t: t[8]):
        print(f"  {k:<14} {'높은쪽' if sign > 0 else '낮은쪽':>6} {m:>+8.3f} "
              f"{ex:>+8.3f} {c:>+9.1f} {d:>+8.1f} | {h1:>+8.3f} {h2:>+8.3f} "
              f"{'O' if (h1 > 0) == (h2 > 0) else 'X':>5} | "
              f"{beat*100:>6.1f}%" + ("  탈락" if beat > 0.05 else "  통과"))

    n_pass = sum(1 for r in rowsout if r[8] <= 0.05)
    print(f"\n  통과 {n_pass}/{len(KEYS)}개. 우연 기대값 {len(KEYS)*0.05:.1f}개.")
    print(f"  부호 양쪽 일치 {sum(1 for r in rowsout if (r[6] > 0) == (r[7] > 0))}"
          f"/{len(KEYS)}개 (우연이면 {len(KEYS)/2:.1f}개)")


def main() -> int:
    p = argparse.ArgumentParser(
        description="저변동 전제: 갈아타기 주기와 종목 선택 지표")
    p.add_argument("--what", choices=("rebal", "signals", "both"),
                   default="both")
    a = p.parse_args()
    if a.what in ("rebal", "both"):
        run_rebal()
    if a.what in ("signals", "both"):
        run_signals()
    return 0


if __name__ == "__main__":
    sys.exit(main())
