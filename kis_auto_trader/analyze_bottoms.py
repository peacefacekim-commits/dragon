"""완벽한 바닥에서 사고 천장에서 팔았다고 가정하면 - 그리고 왜 못 쓰는지.

(2026-09-18 신설) 사용자: "억지로 시나리오를 만들어보자. 특정 종목이 내릴 때
사고 오를 때 팔았다고 가정하고 그 시기 시기 마다의 공통점을 한번 탐구해줘"

지금까지와 방향이 반대다.
  지금까지  날짜를 고정(20일마다)하고 '결과가 좋았나' 를 봤다
  이번      사후적으로 완벽한 바닥·천장을 찾아놓고 '그때 지표가 어땠나' 를 본다

착각 위험이 최대인 틀이다 - 정답을 이미 보고 특징을 찾으니 특징은 반드시
나온다. 그래서 네 단계로 나눴다.

===========================================================================
A) 천장 - 완벽한 타이밍이 대체 얼마 가치인가  (run_scenario)
===========================================================================
바닥/천장 = 앞뒤 20거래일 중 종가가 가장 낮은/높은 날. 바닥에서 사고 다음
천장에서 판다. 저변동에 자주 뽑힌 6종목:

  종목        바닥  천장      완벽매매      사놓기         차이
  KT&G        25   24   +1102.3%   +107.3%   + 994.9%
  SK텔레콤     25   24   +1059.5%   +116.5%   + 943.0%
  KT          22   22   + 841.8%   +121.6%   + 720.2%
  삼성전자우    27   23   +2845.6%   +154.1%   +2691.5%
  우리금융     21   27   +3206.5%   +281.5%   +2925.0%
  삼성전자     27   23   +4540.3%   +201.6%   +4338.7%

완벽한 타이밍은 10~45배 가치가 있다. 상금이 크다는 것은 확인됐다.

===========================================================================
B) 프로파일 - 바닥은 실제로 아주 특징적이다  (run_scenario)
===========================================================================
바닥 1,191건 / 천장 1,194건 / 무작위 1,404건. 잡음배수 = (바닥-무작위) /
무작위 표본 평균의 표준편차.

  지표              바닥     천장    무작위   잡음배수
  종목 5일수익      -4.27   +4.73   +0.08   -29.05
  종목 20일수익     -7.48   +9.75   +0.53   -25.71
  종목 개인수급      +0.12   -0.11   +0.00   +19.44
  시장 20일수익     -2.76   +3.17   +0.72   -16.17
  종목 기관수급      -0.08   +0.08   -0.00   -15.88
  VIX수준          20.89   18.01   18.81   +12.91
  (21개 중 15개가 잡음배수 |8| 초과)

===========================================================================
C) 판정 - 부호 일치 19/21 (우연이면 10.5)
===========================================================================
전반부 바닥의 특징을 후반부 바닥도 거의 다 갖고 있다. 이 프로젝트에서
나온 최고 수치다. 그런데 바로 이 지점에서 의심해야 한다.

===========================================================================
D) 정밀도 - 여기서 무너진다  (run_precision)
===========================================================================

순환논리였다. '바닥' 을 "앞뒤 20일 중 최저" 로 정의했으니 바닥까지 가격이
내려온 것은 **정의상 당연하다**. "바닥의 20일 수익이 -7.48%" 는 발견이
아니라 정의를 다시 말한 것이다. 기관이 팔고 개인이 사는 것도 가격이
내려가는 동안 벌어지는 일 그 자체다.

진짜 질문은 "20일간 7% 빠진 날들 중 어느 것이 바닥이고 어느 것이 더
빠지나" 다. 그래서 정밀도를 봤다.

종목-일 69,394건 중 바닥 1,287건 (1.85%)

  조건                                해당일    정밀도  기본대비  20일후  전체대비
  20일수익 < -5%                     17,389   4.45%   2.40x  +1.723  +0.502
  20일수익 < -10%                     7,085   5.28%   2.85x  +2.369  +1.148
  20일수익 < -15%                     2,712   5.53%   2.98x  +2.891  +1.670
  기관수급 하위                        25,078   2.88%   1.55x  +1.338  +0.117
  20일 -10% AND 기관매도 AND 개인매수    2,356   6.92%   3.73x  +1.714  +0.493
  52주저점 +5% 이내                    9,044   4.20%   2.27x  +0.609  -0.612

조건이 바닥 확률을 1.85% -> 6.92% 로 3.7배 올린다. 이건 진짜다. 그런데
**6.92% 는 열세 번 틀리고 한 번 맞는다는 뜻이다.**

그리고 실전 검사에서 완전히 무너진다. 같은 조건을 전반부/후반부로 나눠
'그날 사서 20거래일 뒤 팔기' 수익을 기준선과 비교하면:

  조건                          전반부 대비    후반부 대비   부호
  20일수익 < -15%                 +5.02%p      -0.65%p    X
  20일수익 < -10%                 +3.05%p      -0.12%p    X
  20일수익 < -7.5%                +2.25%p      -0.27%p    X
  20일 -10% AND 기관 AND 개인      +2.35%p      -0.79%p    X
  52주저점 이내                     +0.67%p      -1.43%p    X
  (검사한 12개 조건 전부 X. 0/12 일치)

전반부 기준선 -0.041% / 후반부 기준선 +2.018%

이유가 분명하다. **'내릴 때 사기' 는 하락장에서 통하고 상승장에서 손해다.**
전반부(2021~2024)는 시장이 빠진 구간이라 빠진 것을 사면 회복했다. 후반부
(2024~2026)는 오르는 구간이라, 빠진 종목은 그냥 뒤처진 종목이었고 아무거나
들고 있는 것(+2.018%)보다 못했다.

그리고 어느 장세인지 미리 아는 것이 바로 우리가 20번 실패한 그 문제다.

===========================================================================
결론
===========================================================================
  1) 상금은 크다 (완벽한 타이밍 10~45배)
  2) 바닥은 아주 특징적으로 보이고 그 특징은 양쪽 반기에서 일치한다 (19/21)
  3) 그런데 그 특징은 '바닥' 의 정의를 다시 말한 것이다 (순환논리)
  4) 특징을 조건으로 쓰면 바닥 확률이 3.7배 오른다 - 하지만 6.92% 다
  5) 돈으로 재면 12개 조건 전부 반기 사이에 부호가 뒤집힌다
  6) 즉 "내릴 때 사기" 는 전략이 아니라 **장세에 대한 베팅** 이다

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_bottoms.py                  # A,B,C 시나리오와 프로파일
    python analyze_bottoms.py --what precision # D 정밀도와 실전 검사
"""
import pathlib as _pathlib
# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = str(_pathlib.Path(__file__).resolve().parent)
import argparse
import sys as _sys


def run_scenario():
    import csv
    import glob
    import math
    import statistics as st
    import sys

    import numpy as np

    sys.path.insert(0, _ROOT)
    import strategy as S  # noqa: E402

    W = 20                  # 앞뒤 W 거래일 중 최저/최고면 바닥/천장
    FEE = S.FEE_ROUND_TRIP_PCT
    N_PERM = 2000
    rng = np.random.default_rng(20260930)

    dates, panel = S.load_panel()
    N = len(dates)
    START = max(140, S.LIQUIDITY_DAYS + 2)
    dpos = {d: i for i, d in enumerate(dates)}

    # ------------------------------------------------ 저변동에 뽑힌 종목 모으기
    picked = set()
    di = START
    while di + W < N:
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(sc) >= 10:
            sc.sort(reverse=True)
            picked.update(c for _s, c in sc[:10])
        di += W
    print(f"저변동에 한 번이라도 뽑힌 종목 {len(picked)}개")

    # ------------------------------------------------------------ 시장 지표
    raw = {}
    for path in sorted(glob.glob(f"{_ROOT}/data/market_indicators_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                raw[r["date"]] = r
    md = sorted(raw)
    mdpos = {d: i for i, d in enumerate(md)}


    def g(d, key):
        try:
            return float(raw[d][key])
        except (TypeError, ValueError, KeyError):
            return None


    idx, v = {}, 100.0
    for d in md:
        c = g(d, "result_c2c")
        if c is not None:
            v *= (1 + c / 100)
        idx[d] = v

    flow = {}
    for path in sorted(glob.glob(f"{_ROOT}/data/krx_flow_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["code"] in picked:
                    try:
                        flow[(r["date"], r["code"])] = (
                            float(r["inst"]), float(r["foreign"]), float(r["indiv"]))
                    except (TypeError, ValueError):
                        pass
    print(f"수급 {len(flow):,}건")


    # --------------------------------------------------- 바닥/천장 찾기 (사후적)
    def extrema(code):
        """(바닥 날짜인덱스 목록, 천장 날짜인덱스 목록)"""
        s = panel.get(code)
        if s is None:
            return [], []
        lows, highs = [], []
        for n, di_ in enumerate(s.di):
            if n < W or n + W >= len(s.di):
                continue
            win = s.close[n - W:n + W + 1]
            if s.close[n] == min(win):
                lows.append(di_)
            if s.close[n] == max(win):
                highs.append(di_)
        return lows, highs


    def sigs(code, di_):
        """di_ 날의 전날까지 확정된 지표. 종목 것 + 시장 것."""
        s = panel.get(code)
        if s is None:
            return None
        j = s.pos.get(di_ - 1)
        if j is None or j < 260:
            return None
        d_prev = dates[di_ - 1]
        i = mdpos.get(d_prev)
        if i is None or i < 255:
            return None
        px = s.close[j]
        if not px or not s.value[j]:
            return None
        f = flow.get((d_prev, code))
        if f is None:
            return None
        out = {}

        # --- 종목 자신
        for w, label in ((5, "종목 5일수익"), (20, "종목 20일수익"),
                         (60, "종목 60일수익")):
            jj = s.pos.get(di_ - 1 - w)
            if jj is None:
                return None
            out[label] = (px / s.close[jj] - 1) * 100
        hi = max(s.close[k] for k in range(j - 250, j + 1))
        lo = min(s.close[k] for k in range(j - 250, j + 1))
        out["종목 52주고점대비"] = (px / hi - 1) * 100 if hi else 0.0
        out["종목 52주저점대비"] = (px / lo - 1) * 100 if lo else 0.0
        win = [s.close[k] for k in range(j - 59, j + 1)]
        drs = [win[k] / win[k - 1] - 1 for k in range(1, len(win))]
        out["종목 변동성"] = st.pstdev(drs) * 100
        v5 = st.mean([s.value[k] for k in range(j - 4, j + 1)])
        v60 = st.mean([s.value[k] for k in range(j - 59, j + 1)])
        out["종목 거래량 5/60"] = v5 / v60 if v60 else 1.0
        vv = s.value[j]
        out["종목 기관수급"] = f[0] / vv
        out["종목 외국인수급"] = f[1] / vv
        out["종목 개인수급"] = f[2] / vv

        # --- 시장 대비
        mk20 = (idx[d_prev] / idx[md[i - 21]] - 1) * 100
        out["종목-시장 20일"] = out["종목 20일수익"] - mk20

        # --- 시장 전체
        lv = idx[d_prev]
        ma60 = st.mean([idx[md[k]] for k in range(i - 61, i)])
        out["시장 지수/60일"] = (lv / ma60 - 1) * 100 if ma60 else 0.0
        out["시장 20일수익"] = mk20
        out["시장 상승비율"] = g(d_prev, "kr_breadth5")
        out["시장 변동성"] = g(d_prev, "kr_vol20")
        out["시장 기관"] = g(d_prev, "flow_inst")
        out["시장 외국인"] = g(d_prev, "flow_foreign")
        for key, label in (("us_sp500", "S&P500"), ("us_vix_level", "VIX수준"),
                           ("us_vix_chg", "VIX변화"), ("fx_krw", "달러/원")):
            out[label] = g(d_prev, key)
        if any(x is None for x in out.values()):
            return None
        return out


    # ------------------------------------ A) 천장: 완벽한 타이밍의 가치
    print("\n" + "=" * 96)
    print("=== A) 완벽한 타이밍이 얼마 가치인가 (사후적 바닥->천장) ===")
    print("=" * 96)
    print(f"  {'종목':<10} {'바닥':>5} {'천장':>5} {'완벽매매':>12} {'사놓기':>12} "
          f"{'차이':>12}")


    def cum(xs):
        v_ = 1.0
        for x in xs:
            v_ *= (1 + x / 100)
        return (v_ - 1) * 100


    tops = sorted(picked)[:0]  # 자리만
    freq = {}
    di = START
    while di + W < N:
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(sc) >= 10:
            sc.sort(reverse=True)
            for _s, c in sc[:10]:
                freq[c] = freq.get(c, 0) + 1
        di += W
    main = [c for c, _n in sorted(freq.items(), key=lambda kv: -kv[1])[:6]]

    all_lows, all_highs = {}, {}
    for code in picked:
        lo_, hi_ = extrema(code)
        all_lows[code] = lo_
        all_highs[code] = hi_

    for code in main:
        s = panel[code]
        lo_, hi_ = all_lows[code], all_highs[code]
        # 바닥에서 사고 다음 천장에서 팔기
        trades, pos = [], None
        events = sorted([(x, "L") for x in lo_] + [(x, "H") for x in hi_])
        for di_, kind in events:
            if pos is None and kind == "L":
                pos = di_
            elif pos is not None and kind == "H":
                a, b = s.pos.get(pos), s.pos.get(di_)
                if a is not None and b is not None and s.close[a]:
                    trades.append((s.close[b] / s.close[a] - 1) * 100 - FEE)
                pos = None
        j0, j1 = s.pos.get(s.di[0]), s.pos.get(s.di[-1])
        hold = (s.close[j1] / s.close[j0] - 1) * 100 - FEE
        print(f"  {code:<10} {len(lo_):>5} {len(hi_):>5} {cum(trades):>+11.1f}% "
              f"{hold:>+11.1f}% {cum(trades)-hold:>+11.1f}%")

    # ------------------------------------------ B) 프로파일 + C) 판정
    recs_low, recs_high, recs_rand = [], [], []
    rand_days = []
    for code in picked:
        s = panel[code]
        for di_ in all_lows[code]:
            sg = sigs(code, di_)
            if sg:
                recs_low.append((dates[di_], code, sg))
        for di_ in all_highs[code]:
            sg = sigs(code, di_)
            if sg:
                recs_high.append((dates[di_], code, sg))
        # 무작위 날 (같은 개수)
        cand_di = [d_ for d_ in s.di if d_ > START]
        if cand_di:
            for di_ in rng.choice(cand_di, size=min(len(all_lows[code]) or 1,
                                                    len(cand_di)), replace=False):
                sg = sigs(code, int(di_))
                if sg:
                    recs_rand.append((dates[int(di_)], code, sg))

    KEYS = list(recs_low[0][2])
    print(f"\n바닥 {len(recs_low)}건 / 천장 {len(recs_high)}건 / "
          f"무작위 {len(recs_rand)}건, 지표 {len(KEYS)}개")

    print("\n" + "=" * 96)
    print("=== B) 바닥 vs 천장 vs 무작위 날 (전날 지표) ===")
    print("=== 잡음배수 = (바닥-무작위) / 무작위 표본 평균의 표준편차 ===")
    print("=" * 96)
    print(f"  {'지표':<18} {'바닥':>10} {'천장':>10} {'무작위':>10} {'잡음배수':>9}")
    prof = []
    for k in KEYS:
        a = st.mean([s[k] for _d, _c, s in recs_low])
        b = st.mean([s[k] for _d, _c, s in recs_high])
        r_ = [s[k] for _d, _c, s in recs_rand]
        c_ = st.mean(r_)
        se = st.pstdev(r_) / math.sqrt(len(recs_low)) or 1.0
        prof.append((k, a, b, c_, (a - c_) / se))
    for k, a, b, c_, z in sorted(prof, key=lambda t: -abs(t[4])):
        print(f"  {k:<18} {a:>10.2f} {b:>10.2f} {c_:>10.2f} {z:>+9.2f}")

    print("\n" + "=" * 96)
    print("=== C) 판정: 전반부 바닥의 특징을 후반부 바닥도 갖고 있나 ===")
    print("=" * 96)
    mid = dates[N // 2]
    lowA = [r for r in recs_low if r[0] < mid]
    lowB = [r for r in recs_low if r[0] >= mid]
    randA = [r for r in recs_rand if r[0] < mid]
    randB = [r for r in recs_rand if r[0] >= mid]
    print(f"  전반부 바닥 {len(lowA)}건 / 후반부 바닥 {len(lowB)}건")
    print(f"\n  {'지표':<18} {'전반부 차이':>12} {'후반부 차이':>12} {'부호':>5}")
    rows = []
    for k in KEYS:
        if not randA or not randB:
            continue
        da = (st.mean([s[k] for _d, _c, s in lowA])
              - st.mean([s[k] for _d, _c, s in randA]))
        db = (st.mean([s[k] for _d, _c, s in lowB])
              - st.mean([s[k] for _d, _c, s in randB]))
        rows.append((k, da, db, (da > 0) == (db > 0)))
    for k, da, db, ok in sorted(rows, key=lambda t: (not t[3], -abs(t[2]))):
        print(f"  {k:<18} {da:>+12.2f} {db:>+12.2f} {'O' if ok else 'X':>5}")
    same = sum(1 for r in rows if r[3])
    print(f"\n  부호 일치 {same}/{len(rows)}개 (우연이면 {len(rows)/2:.1f}개)")


def run_precision():
    import csv
    import glob
    import math
    import statistics as st
    import sys

    import numpy as np

    sys.path.insert(0, _ROOT)
    import strategy as S  # noqa: E402

    W = 20
    FEE = S.FEE_ROUND_TRIP_PCT
    rng = np.random.default_rng(20261001)

    dates, panel = S.load_panel()
    N = len(dates)
    START = max(140, S.LIQUIDITY_DAYS + 2)

    picked, freq = set(), {}
    di = START
    while di + W < N:
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(sc) >= 10:
            sc.sort(reverse=True)
            for _s, c in sc[:10]:
                picked.add(c)
                freq[c] = freq.get(c, 0) + 1
        di += W

    flow = {}
    for path in sorted(glob.glob(f"{_ROOT}/data/krx_flow_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["code"] in picked:
                    try:
                        flow[(r["date"], r["code"])] = (
                            float(r["inst"]), float(r["foreign"]), float(r["indiv"]))
                    except (TypeError, ValueError):
                        pass

    # ------------------------- 모든 종목-일에 대해 (지표, 바닥여부, 20일후 수익)
    rows = []
    for code in picked:
        s = panel.get(code)
        if s is None:
            continue
        for n, di_ in enumerate(s.di):
            if n < 261 or n + W >= len(s.di) or di_ <= START:
                continue
            j = n - 1                      # 전날
            if j < 260 or not s.close[j] or not s.value[j]:
                continue
            d_prev = dates[di_ - 1]
            f = flow.get((d_prev, code))
            if f is None:
                continue
            px = s.close[j]
            j20 = s.pos.get(di_ - 21)
            j5 = s.pos.get(di_ - 6)
            if j20 is None or j5 is None:
                continue
            r20 = (px / s.close[j20] - 1) * 100
            r5 = (px / s.close[j5] - 1) * 100
            lo250 = min(s.close[k] for k in range(j - 250, j + 1))
            frombot = (px / lo250 - 1) * 100 if lo250 else 0.0
            vv = s.value[j]
            is_bottom = s.close[n] == min(s.close[n - W:n + W + 1])
            # 그날 종가에 사서 20거래일 뒤 종가에 팔면
            fwd = (s.close[n + W] / s.close[n] - 1) * 100 - FEE
            rows.append({
                "date": dates[di_], "code": code, "bottom": is_bottom, "fwd": fwd,
                "r20": r20, "r5": r5, "frombot": frombot,
                "inst": f[0] / vv, "indiv": f[2] / vv,
            })

    print(f"종목-일 {len(rows):,}건, 그중 바닥 "
          f"{sum(1 for r in rows if r['bottom']):,}건 "
          f"({sum(1 for r in rows if r['bottom'])/len(rows)*100:.2f}%)")
    print(f"참고: 앞뒤 {W}일 기준이면 기본 확률이 약 "
          f"{1/(2*W+1)*100:.2f}% 다\n")

    base_rate = sum(1 for r in rows if r["bottom"]) / len(rows)
    base_fwd = st.mean([r["fwd"] for r in rows])
    print(f"전체 20일 후 평균 수익 {base_fwd:+.3f}%\n")

    print("=" * 100)
    print("=== 정밀도: 조건을 만족한 날 중 실제 바닥의 비율 ===")
    print("=== 기본 확률과 비슷하면 그 조건은 아무것도 안 알려준다 ===")
    print("=" * 100)
    print(f"  {'조건':<34} {'해당일':>8} {'바닥':>7} {'정밀도':>8} "
          f"{'기본대비':>8} | {'20일후 평균':>11} {'전체대비':>9}")

    CONDS = [
        ("20일수익 < -5%", lambda r: r["r20"] < -5),
        ("20일수익 < -7.5%", lambda r: r["r20"] < -7.5),
        ("20일수익 < -10%", lambda r: r["r20"] < -10),
        ("20일수익 < -15%", lambda r: r["r20"] < -15),
        ("5일수익 < -4%", lambda r: r["r5"] < -4),
        ("52주저점 +5% 이내", lambda r: r["frombot"] < 5),
        ("기관수급 하위(음수 큰쪽)", lambda r: r["inst"] < -0.05),
        ("개인수급 상위", lambda r: r["indiv"] > 0.05),
        ("20일 -7.5% AND 기관매도",
         lambda r: r["r20"] < -7.5 and r["inst"] < -0.05),
        ("20일 -7.5% AND 개인매수",
         lambda r: r["r20"] < -7.5 and r["indiv"] > 0.05),
        ("20일 -10% AND 기관매도 AND 개인매수",
         lambda r: r["r20"] < -10 and r["inst"] < -0.05 and r["indiv"] > 0.05),
        ("52주저점 이내 AND 기관매도",
         lambda r: r["frombot"] < 5 and r["inst"] < -0.05),
    ]

    for label, fn in CONDS:
        hit = [r for r in rows if fn(r)]
        if len(hit) < 30:
            print(f"  {label:<34} {len(hit):>8}  해당일 부족")
            continue
        nb = sum(1 for r in hit if r["bottom"])
        prec = nb / len(hit)
        fwd = st.mean([r["fwd"] for r in hit])
        print(f"  {label:<34} {len(hit):>8} {nb:>7} {prec*100:>7.2f}% "
              f"{prec/base_rate:>7.2f}x | {fwd:>+10.3f}% {fwd-base_fwd:>+8.3f}%p")

    # ------------------------------------------------- 실전: 반기 양방향
    print("\n" + "=" * 100)
    print("=== 실전 검사: 전반부에서 조건을 정하고 후반부에 사면 ===")
    print("=== (같은 조건, 같은 종목 풀. 무작위로 같은 개수 사는 것과 비교) ===")
    print("=" * 100)
    mid = dates[N // 2]
    A = [r for r in rows if r["date"] < mid]
    B = [r for r in rows if r["date"] >= mid]
    print(f"  전반부 {len(A):,}건 / 후반부 {len(B):,}건")
    print(f"  전반부 20일후 평균 {st.mean([r['fwd'] for r in A]):+.3f}% / "
          f"후반부 {st.mean([r['fwd'] for r in B]):+.3f}%")
    print(f"\n  {'조건':<34} {'전반부':>20} | {'후반부':>20} | {'부호':>5}")
    print(f"  {'':<34} {'해당':>7}{'평균':>7}{'대비':>6} | "
          f"{'해당':>7}{'평균':>7}{'대비':>6} |")
    for label, fn in CONDS:
        ha = [r for r in A if fn(r)]
        hb = [r for r in B if fn(r)]
        if len(ha) < 30 or len(hb) < 30:
            continue
        ea = st.mean([r["fwd"] for r in ha]) - st.mean([r["fwd"] for r in A])
        eb = st.mean([r["fwd"] for r in hb]) - st.mean([r["fwd"] for r in B])
        print(f"  {label:<34} {len(ha):>7}{st.mean([r['fwd'] for r in ha]):>+7.2f}"
              f"{ea:>+6.2f} | {len(hb):>7}"
              f"{st.mean([r['fwd'] for r in hb]):>+7.2f}{eb:>+6.2f} | "
              f"{'O' if (ea > 0) == (eb > 0) else 'X':>5}")


def main() -> int:
    p = argparse.ArgumentParser(description="완벽한 바닥 시나리오와 그 한계")
    p.add_argument("--what", choices=("scenario", "precision", "both"),
                   default="both")
    a_ = p.parse_args()
    if a_.what in ("scenario", "both"):
        run_scenario()
    if a_.what in ("precision", "both"):
        run_precision()
    return 0


if __name__ == "__main__":
    _sys.exit(main())
