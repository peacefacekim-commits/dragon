"""나쁜 날에 사고 좋은 날에 파는 전략 - 진입/청산 시점을 신호로 정한다.

(2026-09-17 신설) 사용자 설명: "될 수 있다면 나쁜날을 예측해서 그때 사고
좋은 날에 파는 거"

이건 지금까지의 테스트와 부호가 반대다.
  지금까지  나쁜 날 = 피할 날 (쉰다)
  이번      나쁜 날 = 싸게 사는 날 (산다), 좋은 날 = 파는 날

근거가 있었다. 20일 보유 후반부에서 종합 점수와 수익의 상관이 -0.102 였다.
점수가 낮은 날(나쁜 날)에 산 회차가 더 좋았다는 뜻이고, 사용자가 말한
방향과 맞는다. 쉬는 데 써서 실패한 신호를 사는 데 쓰면 다를 수 있다.

이 방식의 구조적 장점: 팔고 나서 다시 사므로 거래가 겹치지 않는다. 거래
하나가 독립 표본 하나다. 20일 고정 보유의 '겹치는 1,238회차 = 독립 61개'
문제가 사라진다.

규칙
  현금 상태에서 점수 <= 낮은기준        -> 그날 시가에 매수
  보유 상태에서 점수 >= 높은기준        -> 그날 시가에 매도
  보유 상태에서 max_hold 거래일 경과   -> 강제 매도 (영원히 들고 있지 않게)

결과 (2026-09-17). 격자 45가지, 부호와 기준은 학습 구간에서만 정한다.

  [정방향] 전반부(2021~2024)에서 부호 -> 후반부(2024~2026) 채점
    최고 50%/90%/20일  43거래 평균 +1.844%(표준오차 0.592) 누적 +113.0%
                       MDD -10.5% 최악 -4.99% 시장체류 70%
    기준선 20일 고정   31회 평균 +1.946% 누적 +76.7% MDD -5.4%
    반대 규칙(좋은날 사고 나쁜날 팔기) 누적 -13.7% MDD -20.2%
    점수 밀어놓기 200번: 실제보다 좋은 우연 2.0%      <- 통과
    같은 횟수 무작위 진입 500번: 무작위가 더 좋았던 비율 1.4%  <- 통과

  [역방향] 후반부에서 부호 -> 전반부 채점
    같은 설정 50%/90%/20일 이 45개 중 44등
                       72거래 평균 -0.458% 누적 -29.1% MDD -39.5%
    이 방향의 최고 10%/80%/60일 은 누적 +5.3% 뿐이고
    밀어놓기 대조군에서 37.0%가 더 좋았다                <- 탈락
    (그 최고 설정 10%/80%/60일 은 정방향에서 37/45등이다)
    기준선 20일 고정   누적 -5.5% MDD -17.8%

  [지표 부호] 양쪽 학습 구간에서 같은 부호로 정해진 지표 6/13
             (우연이면 6.5개)

읽는 법: 한쪽 방향에서는 대조군을 통과했고 반대 방향에서는 크게 깨졌다.
같은 설정이 1등과 44등을 오간다. 부호도 우연 수준으로만 일치한다. 이건
'꾸준한 우위' 가 아니라 '장세에 걸린 베팅' 의 모양이다. 후반부는 상승장이고
'싸게 사서 오르면 판다' 는 상승장에서 기계적으로 유리하다. 전반부는 시장이
빠진 구간이고 거기서는 -29.1% 였다.

한 가지 일관된 것은 있다. **반대 규칙(좋은 날 사고 나쁜 날 파는 쪽)은 양쪽
모두 손실이다** (-13.7% / -12.9%). 즉 추세를 따라 타이밍을 잡는 것은 꾸준히
나쁘고, 거꾸로 잡는 것은 장세에 따라 다르다. 비대칭이 한쪽으로만 있다.

그리고 정방향에서조차 최대낙폭은 기준선보다 나빴다 (-10.5% vs -5.4%).
'큰 손해를 피한다' 는 목적에서는 통과한 방향에서도 실패했다.

주문은 내지 않는다. 패널 CSV 만 읽는다.

실행:
    python analyze_timing.py              # 양방향 다 본다
    python analyze_timing.py --no-shift   # 대조군 생략 (빠르게)
"""
import argparse
import math
import statistics as st
import sys

import numpy as np

import market_indicators as mi
import strategy as S

FACTOR = "low_vol"
TOP_N = 10
LOWQ = (0.1, 0.2, 0.3, 0.5)
HIGHQ = (0.5, 0.7, 0.8, 0.9)
MAX_HOLDS = (5, 20, 60)
SIGN_FIT_HOLD = 20          # 부호를 정할 때 쓰는 기준 보유기간
MIN_TRADES = 5
N_SHIFT = 200
SEED = 20260918


def cumulative(rets) -> float:
    v = 1.0
    for x in rets:
        v *= (1 + x / 100)
    return (v - 1) * 100


def max_drawdown(rets) -> float:
    v, peak, worst = 1.0, 1.0, 0.0
    for x in rets:
        v *= (1 + x / 100)
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def build_picks(dates, panel, verbose: bool = True) -> dict:
    """날짜 -> 뽑힌 종목 10개. 종목 선정은 진입/청산 규칙과 무관하므로
    한 번만 계산해 재사용한다 (격자 x 대조군으로 수백 번 돌기 때문)."""
    out = {}
    start = max(140, S.LIQUIDITY_DAYS + 2)
    for di in range(start, len(dates)):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(S.factor_score(panel, c, di, FACTOR), c) for c in cand]
        sc = [(s, c) for s, c in sc if s is not None]
        if len(sc) < TOP_N:
            continue
        sc.sort(reverse=True)
        out[dates[di]] = [c for _s, c in sc[:TOP_N]]
    if verbose:
        print(f"종목 선정 {len(out)}일 계산 완료")
    return out


def trade_return(panel, codes, entry_d, exit_d, dmap,
                 fee=S.FEE_ROUND_TRIP_PCT):
    """entry_d 에 뽑은 종목을 entry_d 시가에 사서 exit_d 시가에 판다.

    dmap 은 날짜 -> 날짜인덱스. 갭은 일부러 안 먹는다 (시가에 사고 시가에
    팔므로) - strategy.py 와 같은 보수적 가정이다.
    """
    ei, xi = dmap[entry_d], dmap[exit_d]
    rs = []
    for c in codes:
        s = panel.get(c)
        if s is None:
            continue
        je, jx = s.pos.get(ei), s.pos.get(xi)
        if je is None or jx is None:
            continue
        a, b = s.open[je], s.open[jx]
        if a and b:
            rs.append((b / a - 1) * 100)
    return st.mean(rs) - fee if rs else None


def build_score(day_vals, keys, fit_days, ret_at):
    """부호와 표준화를 fit_days 에서만 정한다. 높을수록 '좋은 날'."""
    pairs = [(d, ret_at(d)) for d in fit_days]
    pairs = [(d, r) for d, r in pairs if r is not None]
    if len(pairs) < 50:
        return None, None
    ys = np.array([r for _d, r in pairs])
    signs, stats = {}, {}
    for k in keys:
        xs = np.array([day_vals[d][k] for d, _r in pairs])
        cov = float(((xs - xs.mean()) * (ys - ys.mean())).sum())
        signs[k] = 1.0 if cov >= 0 else -1.0
        stats[k] = (float(xs.mean()), float(xs.std()) or 1.0)

    def score(d):
        v = day_vals.get(d)
        if not v or any(v.get(k) is None for k in keys):
            return None
        return st.mean([signs[k] * (v[k] - stats[k][0]) / stats[k][1]
                        for k in keys])
    return score, signs


def simulate(days, sig, low, high, max_hold, ret_fn, invert=False):
    """현금<->보유를 오간다. 거래가 겹치지 않으므로 거래 하나가 표본 하나다."""
    trades, entry = [], None
    for n, d in enumerate(days):
        s = sig.get(d)
        if s is None:
            continue
        buy = (s >= high) if invert else (s <= low)
        sell = (s <= low) if invert else (s >= high)
        if entry is None:
            if buy:
                entry = (d, n)
        elif sell or n - entry[1] >= max_hold:
            r = ret_fn(entry[0], d)
            if r is not None:
                trades.append((entry[0], d, n - entry[1], r))
            entry = None
    return trades


def _grid(days, sig, qf, ret_fn):
    rows = []
    for lq in LOWQ:
        for hq in HIGHQ:
            if qf(lq) >= qf(hq):
                continue
            for mh in MAX_HOLDS:
                tds = simulate(days, sig, qf(lq), qf(hq), mh, ret_fn)
                if len(tds) < MIN_TRADES:
                    continue
                rs = [t[3] for t in tds]
                rows.append({
                    "cfg": (lq, hq, mh), "n": len(rs), "mean": st.mean(rs),
                    "se": st.stdev(rs) / math.sqrt(len(rs)) if len(rs) > 1
                    else None,
                    "cum": cumulative(rs), "mdd": max_drawdown(rs),
                    "worst": min(rs),
                    "inmkt": sum(t[2] for t in tds) / len(days) * 100})
    rows.sort(key=lambda r: -r["cum"])
    return rows


def run_direction(dates, panel, day_vals, keys, fit_days, test_days,
                  label: str, n_shift: int = N_SHIFT, seed=SEED) -> dict:
    dmap = {d: i for i, d in enumerate(dates)}
    picks = day_vals["__picks__"]

    def ret_fn(a, b):
        return trade_return(panel, picks.get(a) or [], a, b, dmap,
                             S.FEE_ROUND_TRIP_PCT)

    def ret_at(d):
        i = dmap[d]
        if i + SIGN_FIT_HOLD >= len(dates):
            return None
        return ret_fn(d, dates[i + SIGN_FIT_HOLD])

    dv = {d: day_vals[d] for d in fit_days + test_days if d in day_vals}
    score, signs = build_score(dv, keys, fit_days, ret_at)
    if score is None:
        return {"label": label, "n_fit": len(fit_days), "error": "표본 부족"}

    fit_vals = sorted(v for d in fit_days if (v := score(d)) is not None)

    def qf(p):
        return fit_vals[min(int(len(fit_vals) * p), len(fit_vals) - 1)]

    # 기준선: 고정 리밸런스
    fixed, i = [], dmap[test_days[0]]
    end = dmap[test_days[-1]]
    while i + SIGN_FIT_HOLD <= end:
        r = ret_fn(dates[i], dates[i + SIGN_FIT_HOLD])
        if r is not None:
            fixed.append(r)
        i += SIGN_FIT_HOLD

    sig = {d: score(d) for d in test_days}
    rows = _grid(test_days, sig, qf, ret_fn)
    if not rows:
        return {"label": label, "signs": signs, "rows": [],
                "fixed": {"n": len(fixed)}}
    best = rows[0]
    lq, hq, mh = best["cfg"]
    inv = simulate(test_days, sig, qf(lq), qf(hq), mh, ret_fn, invert=True)
    irs = [t[3] for t in inv]

    out = {
        "label": label, "signs": signs, "rows": rows, "best": best,
        "fixed": {"n": len(fixed), "mean": st.mean(fixed) if fixed else None,
                  "cum": cumulative(fixed) if fixed else None,
                  "mdd": max_drawdown(fixed) if fixed else None,
                  "worst": min(fixed) if fixed else None},
        "invert": ({"n": len(irs), "mean": st.mean(irs),
                    "cum": cumulative(irs), "mdd": max_drawdown(irs)}
                   if len(irs) >= MIN_TRADES else None),
        "fit_span": (fit_days[0], fit_days[-1]),
        "test_span": (test_days[0], test_days[-1]),
    }

    if n_shift:
        # 점수를 통째로 밀어 짝만 어긋나게 한다. 격자 탐색을 그대로 반복해서
        # '아무 관계가 없을 때 이 탐색이 찾아내는 최고 성적' 을 만든다.
        rng = np.random.default_rng(seed)
        nte = len(test_days)
        vals = [sig.get(d) for d in test_days]
        bests = []
        for off in rng.integers(SIGN_FIT_HOLD,
                                max(SIGN_FIT_HOLD + 1, nte - SIGN_FIT_HOLD),
                                size=n_shift):
            sh = {test_days[j]: vals[(j + int(off)) % nte] for j in range(nte)}
            g = _grid(test_days, sh, qf, ret_fn)
            if g:
                bests.append(g[0]["cum"])
        if bests:
            bests.sort()
            out["shift"] = {
                "n": len(bests),
                "med": bests[len(bests) // 2],
                "p95": bests[int(len(bests) * 0.95)],
                "max": bests[-1],
                "beat": sum(1 for b in bests if b >= best["cum"]) / len(bests),
            }
    return out


def analyze(n_shift: int = N_SHIFT, verbose: bool = True) -> dict:
    dates, panel = S.load_panel(verbose=verbose)
    keys = mi.PREDICTOR_FIELDS
    day_vals = S.load_day_scores()
    picks = build_picks(dates, panel, verbose)
    usable = [d for d in sorted(picks)
              if d in day_vals and all(day_vals[d][k] is not None
                                       for k in keys)]
    half = len(usable) // 2
    A, B = usable[:half], usable[half:]
    day_vals["__picks__"] = picks

    out = {
        "n_days": len(usable),
        "forward": run_direction(dates, panel, day_vals, keys, A, B,
                                 "정방향: 전반부에서 부호 -> 후반부 채점",
                                 n_shift),
        "reverse": run_direction(dates, panel, day_vals, keys, B, A,
                                 "역방향: 후반부에서 부호 -> 전반부 채점",
                                 n_shift),
    }
    if verbose:
        _report(out, keys)
    return out


def _report(o: dict, keys) -> None:
    for which in ("forward", "reverse"):
        d = o[which]
        print(f"\n{'='*74}")
        print(f"=== {d['label']} ===")
        if d.get("error"):
            print(f"  {d['error']}")
            continue
        print(f"  부호 정하기 {d['fit_span'][0]}~{d['fit_span'][1]} / "
              f"채점 {d['test_span'][0]}~{d['test_span'][1]}")
        print(f"{'='*74}")
        f = d["fixed"]
        if f.get("mean") is not None:
            print(f"\n  [기준선] {SIGN_FIT_HOLD}일 고정  {f['n']}회 "
                  f"평균 {f['mean']:+.3f}% 누적 {f['cum']:+.1f}% "
                  f"MDD {f['mdd']:+.1f}% 최악 {f['worst']:+.2f}%")
        print(f"\n  {'낮은/높은/최대':<16} {'거래':>4} {'평균':>8} {'표준오차':>8} "
              f"{'누적':>9} {'MDD':>8} {'최악':>8} {'체류':>6}")
        for r in d["rows"][:5]:
            lq, hq, mh = r["cfg"]
            print(f"  {int(lq*100):>3}%/{int(hq*100):>3}%/{mh:>3}일   "
                  f"{r['n']:>4} {r['mean']:>+8.3f} {(r['se'] or 0):>8.3f} "
                  f"{r['cum']:>+9.1f} {r['mdd']:>+8.1f} {r['worst']:>+8.2f} "
                  f"{r['inmkt']:>5.0f}%")
        # 반대 방향에서 뽑힌 설정이 여기서 몇 등인지 - 같은 설정이 1등과
        # 꼴등을 오가면 그 자체가 결론이다.
        other = o["reverse" if which == "forward" else "forward"]
        if other.get("best"):
            want = other["best"]["cfg"]
            hit = next((i for i, r in enumerate(d["rows"])
                        if r["cfg"] == want), None)
            if hit is not None:
                r = d["rows"][hit]
                print(f"\n  반대 방향의 최고 설정 "
                      f"{int(want[0]*100)}%/{int(want[1]*100)}%/{want[2]}일 은 "
                      f"여기서 {hit+1}/{len(d['rows'])}등: "
                      f"{r['n']}거래 평균 {r['mean']:+.3f}% "
                      f"누적 {r['cum']:+.1f}% MDD {r['mdd']:+.1f}%")
        if d.get("invert"):
            iv = d["invert"]
            print(f"  [반대 규칙] 좋은 날 사고 나쁜 날 팔기: {iv['n']}회 "
                  f"평균 {iv['mean']:+.3f}% 누적 {iv['cum']:+.1f}% "
                  f"MDD {iv['mdd']:+.1f}%")
        if d.get("shift"):
            s = d["shift"]
            print(f"  [대조군] 점수 밀어놓기 {s['n']}번: 중간값 {s['med']:+.1f}% "
                  f"상위5% {s['p95']:+.1f}% 최고 {s['max']:+.1f}%")
            print(f"    실제 {d['best']['cum']:+.1f}% 보다 좋은 우연 "
                  f"{s['beat']*100:.1f}%")
            print("    -> " + ("우연으로 충분히 나온다. 찾은 게 아니다."
                               if s["beat"] > 0.05 else "우연으로는 드물다."))

    sa = o["reverse"].get("signs")
    sb = o["forward"].get("signs")
    if sa and sb:
        same = sum(1 for k in keys if sa[k] == sb[k])
        print(f"\n=== 양쪽 학습 구간에서 부호가 같게 정해진 지표 "
              f"{same}/{len(keys)}개 (우연이면 {len(keys)/2:.1f}개) ===")
        for k in keys:
            print(f"  {k:<14} 전반부적합 {'+' if sb[k] > 0 else '-'}  "
                  f"후반부적합 {'+' if sa[k] > 0 else '-'}  "
                  f"{'O' if sa[k] == sb[k] else 'X'}")
    print(CAUTION)


CAUTION = """
[결과를 볼 때]
  - 한 방향만 보면 안 된다. 앞뒤를 바꿔서도 남는지 봐야 한다. 같은 설정이
    한쪽에서 1등이고 반대쪽에서 꼴등이면, 그건 우위가 아니라 장세에 걸린
    베팅이다.
  - 상승장에서는 '싸게 사서 오르면 판다' 가 기계적으로 유리하다. 채점
    구간이 상승장이었는지 먼저 확인할 것 (기준선 수익을 보면 된다).
  - 격자 45가지의 최고만 보고하면 안 된다. 점수를 어긋나게 밀어놓은
    데이터에서 같은 탐색이 찾아내는 성적과 비교해야 한다.
  - 밀어놓기 대조군의 통과(5% 미만)는 '그 구간 안에서 짝이 우연이 아니다'
    를 말할 뿐, 다음 구간에서도 남는다는 뜻이 아니다. 양방향 검사가
    그것까지 본다.
  - 최대낙폭을 기준선과 비교할 것. 수익이 늘어도 낙폭이 깊어지면 '큰
    손해를 피한다' 는 목적에는 실패다.
  - 거래가 겹치지 않으므로 거래 수가 곧 독립 표본 수다. 40거래면 평균의
    표준오차가 0.5%p 안팎이다 - 평균 차이를 그 폭 안에서 읽어야 한다.
"""


def main() -> int:
    p = argparse.ArgumentParser(description="나쁜 날 매수 / 좋은 날 매도 검증")
    p.add_argument("--no-shift", action="store_true", help="대조군 생략 (빠르게)")
    a = p.parse_args()
    analyze(n_shift=0 if a.no_shift else N_SHIFT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
