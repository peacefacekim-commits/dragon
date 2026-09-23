"""수급 선택이 저변동 풀 밖에서도 작동하나 - 독립 재현 검사.

(2026-09-18 신설) 어제 결과: 저변동 60종목 풀에서 개인 순매수 높은 10개를
고르면 +1.621%/회차 (기준 +1.054%), 누적 +140.8% (기준 +79.8%), 대조군
1.3% 통과, 반기 분할 양쪽 양수.

그런데 선택 방법을 10가지 봤으므로 보정하면 1.3% x 10 = 13% 다. 다중검정은
보정으로 푸는 것보다 **독립 재현** 으로 푸는 게 낫다. 같은 신호를 신호를
찾은 곳이 아닌 다른 풀에서 돌려본다. 저변동 풀에서 우연히 걸린 것이면 다른
풀에서는 안 나온다.

풀 다섯 개 (모두 거래대금 상위 200, 종가 5,000원 이상에서 뽑는다)
  저변동60    원래 찾은 곳. 재현 증거가 아니라 기준점이다
  고변동60    변동성이 가장 높은 60 (반대쪽 극단)
  중간변동60  변동성 중간 60
  거래대금60  거래대금 상위 60 (대형주)
  전체200     필터 없이 200종목 전부

대조군: 같은 풀에서 신호값만 무작위로 섞기. 풀의 성격, 그 회차의 좋고 나쁨,
시장 등락이 전부 상쇄되고 '이 신호로 고르는 것의 값' 만 남는다.

===========================================================================
결과 (2026-09-18). 겹치지 않는 62회차. 숫자는 '풀 전체 동일가중 대비' 초과분
===========================================================================

  풀          풀자체/회차    기관            외국인          개인
  저변동60      +0.730   +0.299 (21.5%)  +0.551 ( 7.6%)  +0.891 ( 1.3%) O
  고변동60      -2.721   +1.076 (10.6%)  +1.038 (11.8%)  +1.585 ( 3.7%) O
  중간변동60    +0.760   +0.363 (28.6%)  -0.886 (91.5%)  +0.230 (37.5%)
  거래대금60    -0.007   +0.665 (15.1%)  +0.980 ( 7.6%)  +1.063 ( 6.0%)
  전체200      -0.443   +1.329 ( 2.8%) O +0.358 (31.1%)  +1.044 ( 7.2%)
  (괄호는 무작위 대조군에서 우연이 실제보다 좋았던 비율. O 는 5% 미만)

읽는 법

  1) 방향은 다섯 풀 전부에서 같다. 개인 높은쪽 초과분이 5/5 양수
     (+0.891 +1.585 +0.230 +1.063 +1.044), 기관 낮은쪽도 5/5 양수
     (+0.299 +1.076 +0.363 +0.665 +1.329). 풀이 서로 겹치므로 독립된 다섯
     증거는 아니지만, 어느 풀에서도 부호가 뒤집히지 않았다.

  2) 통과는 15검정 중 3개다 (개인@저변동 1.3%, 개인@고변동 3.7%,
     기관@전체200 2.8%). 우연 기대값 0.75개보다 많지만 압도적이지 않다.

  3) 개인 순매수는 저변동 풀 밖에서 3곳 중 1곳만 깔끔히 재현됐다
     (고변동 3.7% 통과 / 거래대금 6.0% 경계 / 중간변동 37.5% 탈락).
     '저변동 풀에서만 나온 우연' 은 아니지만 확정도 아니다.

  4) 가장 중요한 실용적 한계: **이 신호는 상대적이다.** 고변동60 에서
     개인 선택은 초과분 +1.585%p 를 내지만 풀 자체가 -2.721%/회차라 결과는
     여전히 -1.135%/회차(누적 -69.9%)다. 신호가 좋아도 못 쓴다. 절대
     수익이 플러스이면서 대조군을 통과한 조합은 여전히 **저변동60 + 개인
     순매수 하나뿐** 이다 (+1.621%/회차, 누적 +140.8%).

  5) 새로 나온 것: 기관@전체200 이 2.8% 로 통과하고 반기 분할도 양쪽
     양수다 (+1.017 / +1.640). 어제 저변동 풀에서는 기관이 21.5% 로
     탈락했는데 풀을 넓히면 나온다. 다만 절대 수익 +0.886%/회차는 현재
     전략(+1.054%)보다 낮아서 갈아탈 이유가 없다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_pools.py
"""
import pathlib as _pathlib
# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = str(_pathlib.Path(__file__).resolve().parent)
import csv
import glob
import math
import statistics as st
import sys

import numpy as np

sys.path.insert(0, _ROOT)
import strategy as S  # noqa: E402

HOLD, PICK = 20, 10
POOL_N = 60
FEE = S.FEE_ROUND_TRIP_PCT
N_PERM = 2000
rng = np.random.default_rng(20260925)

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
print(f"수급 {len(flow):,}건")

SIGS = {"기관": 0, "외국인": 1, "개인": 2}
DIRS = {"기관": -1, "외국인": -1, "개인": +1}   # 어제 정한 방향 그대로


def rec_for(code, di):
    s = panel.get(code)
    if s is None:
        return None
    j = s.pos.get(di - 1)
    if j is None or not s.value[j]:
        return None
    f = flow.get((dates[di - 1], code))
    if f is None:
        return None
    r, _cut = S.trade_return(panel, code, di, di + HOLD)
    if r is None:
        return None
    v = s.value[j]
    return {"code": code, "ret": r, "value": v,
            "기관": f[0] / v, "외국인": f[1] / v, "개인": f[2] / v}


# ------------------------------------------------------- 회차별 풀 다섯 개
POOLS = ("저변동60", "고변동60", "중간변동60", "거래대금60", "전체200")
rounds = {p: [] for p in POOLS}
di = START
while di + HOLD < N:
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    vols = [(sc, c) for c in cand
            if (sc := S.factor_score(panel, c, di, "low_vol")) is not None]
    if len(vols) < POOL_N * 2:
        di += HOLD
        continue
    vols.sort(reverse=True)                # 높은 점수 = 저변동
    n = len(vols)
    mid = (n - POOL_N) // 2
    by_value = sorted(cand, key=lambda c: -(panel[c].value[panel[c].pos[di - 1]]
                                            if di - 1 in panel[c].pos else 0))
    sel = {
        "저변동60": [c for _s, c in vols[:POOL_N]],
        "고변동60": [c for _s, c in vols[-POOL_N:]],
        "중간변동60": [c for _s, c in vols[mid:mid + POOL_N]],
        "거래대금60": by_value[:POOL_N],
        "전체200": cand,
    }
    for p, codes in sel.items():
        recs = [r for c in codes if (r := rec_for(c, di)) is not None]
        if len(recs) >= 2 * PICK:
            rounds[p].append((dates[di], recs))
    di += HOLD

for p in POOLS:
    print(f"  {p}: {len(rounds[p])}회차, 회차당 평균 "
          f"{st.mean([len(r) for _d, r in rounds[p]]):.0f}종목")


def top_mean(recs, which):
    d = DIRS[which]
    xs = sorted(recs, key=lambda r: -d * r[which])
    return st.mean([r["ret"] for r in xs[:PICK]]) - FEE


def pool_mean(recs):
    """풀 전체 동일가중 - 참고용."""
    return st.mean([r["ret"] for r in recs]) - FEE


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


print("\n" + "=" * 100)
print("=== 풀마다 '개인/기관/외국인 순매수로 10종목 고르기' vs '같은 풀에서 "
      "무작위 10종목' ===")
print("=== 대조군 2000번. 통과 기준 5%. 저변동60 은 신호를 찾은 곳이라 "
      "재현 증거가 아니다 ===")
print("=" * 100)

for p in POOLS:
    rs = rounds[p]
    if len(rs) < 30:
        print(f"\n  [{p}] 회차 부족 ({len(rs)})")
        continue
    pool_series = [pool_mean(recs) for _d, recs in rs]
    half = len(rs) // 2
    print(f"\n  [{p}]  {len(rs)}회차   풀 전체 동일가중 "
          f"{st.mean(pool_series):+.3f}%/회차 (누적 {cum(pool_series):+.1f}%, "
          f"MDD {mdd(pool_series):+.1f}%)")
    print(f"    {'신호':<8} {'평균':>8} {'표준오차':>8} {'누적':>9} {'MDD':>8} "
          f"{'풀대비':>8} | {'전반부':>8} {'후반부':>8} {'부호':>5} | {'우연':>7}")
    for which in SIGS:
        real = [top_mean(recs, which) for _d, recs in rs]
        real_m = st.mean(real)
        se = st.stdev(real) / math.sqrt(len(real))
        h1 = st.mean(real[:half]) - st.mean(pool_series[:half])
        h2 = st.mean(real[half:]) - st.mean(pool_series[half:])
        perm = []
        for _ in range(N_PERM):
            tot = 0.0
            for _d, recs in rs:
                order = rng.permutation(len(recs))
                sh = [{**r, which: recs[order[i]][which]}
                      for i, r in enumerate(recs)]
                tot += top_mean(sh, which)
            perm.append(tot / len(rs))
        perm.sort()
        beat = sum(1 for x in perm if x >= real_m) / len(perm)
        print(f"    {which:<8} {real_m:>+8.3f} {se:>8.3f} {cum(real):>+9.1f} "
              f"{mdd(real):>+8.1f} {real_m - st.mean(pool_series):>+8.3f} | "
              f"{h1:>+8.3f} {h2:>+8.3f} "
              f"{'O' if (h1 > 0) == (h2 > 0) else 'X':>5} | "
              f"{beat*100:>6.1f}%" + ("  탈락" if beat > 0.05 else "  통과"))
