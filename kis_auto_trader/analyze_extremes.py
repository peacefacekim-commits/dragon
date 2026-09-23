"""극단만 보면 갈리나 + 평소엔 들고 있다가 조건이 다 맞을 때만 사고팔기.

(2026-09-17 신설) 사용자 설계

  "진짜 나쁜날 진짜 좋은날을 가를만한 조짐" 을 찾아서
  - 진짜 나쁜날에 매수, 진짜 좋은날 + 적정 수익률 이상이면 매도
  - 그 사이에는 그냥 들고 있는다 (수수료가 줄고 보유가 길어진다)
  - 개인+기관+외국인처럼 여러 조건을 AND 로 묶는다 (기회가 드물어지므로
    보유가 더 길어진다)

이전 시도와 다른 점 셋
  1) 지금까지는 한 지점에서 잘랐다. 그러면 '중간은 안 갈리는데 양 극단은
     갈린다' 는 모양을 놓친다. 상관계수도 같은 이유로 놓친다. 그래서 십분위
     와 상·하위 20/10/5/2% 를 따로 본다 (decile_table).
  2) '쉰다/투자한다' 가 아니라 '기본이 보유' 다. 조건이 안 맞으면 계속 들고
     있으므로 상승장을 놓치지 않는다 - 앞선 실패의 큰 원인이 그거였다.
  3) 매도에 수익률 조건을 붙인다. 손실 중에는 좋은 날이 와도 안 판다.

===========================================================================
결과 1 - 극단으로 좁히면 더 갈리나 (2026-09-17)
===========================================================================

지표 16개(시장 13 + 전날등락 + 종목별 기관/외국인)의 십분위별 다음 20거래일
수익을 전·후반부 따로 냈다. 끝칸(10분위-1분위) 차이의 부호가 양쪽에서 같은
지표는 6/16개 - 우연이면 8개다. 상·하위 20% 기준으로 세면 8/16, 정확히 우연.

극단으로 좁히면 숫자는 커지지만 표본이 같이 줄어 못 읽는다.
  us_vix_level 상하위 2%: 전반부 -0.28%p / 후반부 +6.79%p  (부호 반대)
  kr_vol20     상하위 2%: 전반부 +4.75%p / 후반부 -3.88%p  (부호 반대)
  상하위 2% 는 표본 12일이고 겹치는 회차라 독립 표본이 1개 미만이다.

부호가 네 임계값(20/10/5/2%) 전부에서 양쪽 반기 모두 일관된 것은 셋이다.
  stk_inst  (종목별 기관 순매수)  전부 음수 - 기관이 팔았을 때가 좋다
  flow_inst (시장 전체 기관)      전부 음수 - 같은 방향
  stk_frgn  (종목별 외국인)       전부 양수 - 외국인이 샀을 때가 좋다
기관과 외국인이 반대 방향이라는 것이 이 셋의 내용이다. 다만 네 임계값은
같은 데이터를 겹쳐 자른 것이라 독립된 증거 네 개가 아니다. 실질 증거는
반기당 부호 하나씩, 즉 2개다. 16개 지표 중 8개가 그 정도는 우연히 맞는다.

===========================================================================
결과 2 - 평소엔 보유, AND 조건에서만 매매 (종목별 기관/외국인/개인)
===========================================================================

보유 중에는 20거래일마다 종목을 다시 뽑는다 (검증된 전략과 같게). 기준선도
'항상 보유 + 20일 리밸런스' 이므로 수수료 조건이 같고 차이는 타이밍뿐이다.

  [정방향] 전반부에서 방향 -> 후반부 채점
    기준선 항상보유        누적  +87.5%  평가MDD -17.3%
    기관 하위20%/목표5%   누적 +129.4%  평가MDD  -8.2%  12거래
                          평균보유 41일  최장 104일  시장체류 78%
    신호 밀어놓기 200번: 중간값 +112.7%, 실제보다 좋은 우연 20.0%   탈락

  [역방향] 후반부에서 방향 -> 전반부 채점
    기준선                누적   +4.1%  평가MDD -17.9%
    최고 설정             누적   +9.4%  평가MDD -16.0%  거래 1회, 보유 416일
    거래가 한 번이면 표본이 1개다. 판정할 수 없다.

읽는 법 - 여기가 이번 분석의 핵심이다

  사용자 설계는 실제로 기준선을 크게 이겼다 (+129.4% vs +87.5%, 낙폭도
  -8.2% vs -17.3%). 그런데 **신호를 어긋나게 밀어놓아도 중간값이 +112.7%**
  다. 기준선보다 25%p 높다. 즉 그 이득의 대부분은 지표가 아니라 **설계
  자체** 가 만든 것이다.

  설계가 하는 일은 둘이다.
    (1) 시장에 78% 만 머문다
    (2) 손실 중에는 절대 팔지 않는다 (목표 수익률 조건)
  상승장에서 (2)는 기계적으로 아름답다. 실현된 거래는 전부 플러스이므로
  '거래 기준 MDD' 가 0.0% 로 나온다 - 그건 측정 착각이고, 평가금액으로
  재면 -8.2% 다. 이 파일이 두 가지 MDD 를 다 내는 이유다.

  그리고 (2)의 실패 방식이 역방향에 그대로 나왔다. 하락장에서는 매도 조건이
  영영 안 걸려서 한 번 사고 416거래일(1년 8개월)을 들고 있었다. '안 되면
  안 판다' 는 상승장에서 아름답고 하락장에서 영원히 물려 있게 만든다.

  다만 사용자 예측 하나는 맞았다. AND 조건을 걸면 보유기간이 실제로 길어진다
  (평균 41~88일, 최장 104~190일, 역방향은 416일). 수수료는 문제가 아니게 된다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_extremes.py --what deciles
    python analyze_extremes.py --what hold
"""
import argparse
import csv
import glob
import math
import statistics as st
import sys

import numpy as np

import market_indicators as mi
import strategy as S
from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
REBAL = 20
FEE = S.FEE_ROUND_TRIP_PCT
TAIL_PCTS = (0.20, 0.10, 0.05, 0.02)
QS = (0.20, 0.30, 0.40)
TARGETS = (0.0, 3.0, 5.0, 10.0)
COMBOS = [("기관",), ("기관", "외국인"), ("기관", "외국인", "개인"),
          ("외국인",), ("외국인", "개인"), ("기관", "개인")]
FLOW_IDX = {"기관": 0, "외국인": 1, "개인": 2}
N_SHIFT = 200
SEED = 20260922


# --------------------------------------------------------------- 공통 산수
def mdd_from_curve(curve) -> float:
    """일별 평가금액에서 낙폭. 보유 중 평가손실을 포함한다 - 청산된 거래만
    세면 '손실 중에는 안 판다' 는 규칙 때문에 낙폭이 0으로 보인다."""
    if not curve:
        return 0.0
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def mdd_from_trades(rets) -> float:
    """청산된 거래만 이어붙인 낙폭. 위와 비교해 착각을 드러내는 데 쓴다."""
    v, peak, worst = 1.0, 1.0, 0.0
    for x in rets:
        v *= (1 + x / 100)
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def load_stock_flow(codes) -> dict:
    want = set(codes)
    out = {}
    for path in sorted(glob.glob(str(DATA_DIR / "krx_flow_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["code"] not in want:
                    continue
                try:
                    out[(r["date"], r["code"])] = (
                        float(r["inst"]), float(r["foreign"]),
                        float(r["indiv"]))
                except (TypeError, ValueError):
                    pass
    return out


def basket_flow_signal(dates, panel, picks, flow, which: str) -> dict:
    """날짜 -> 바스켓 10종목의 (전날 순매수 / 전날 거래대금) 평균.

    전날을 보는 이유: 수급은 장 마감 후 확정된다. 같은 날을 쓰면 미래 정보다.
    거래대금으로 나누는 이유: 큰 종목의 수급만 보는 지표가 되지 않게.
    """
    k = FLOW_IDX[which]
    dmap = {d: i for i, d in enumerate(dates)}
    out = {}
    for d, codes in picks.items():
        i = dmap[d]
        if i == 0:
            continue
        pi = i - 1
        prev = dates[pi]
        vals = []
        for c in codes:
            f = flow.get((prev, c))
            s = panel.get(c)
            if f is None or s is None:
                continue
            j = s.pos.get(pi)
            if j is None or not s.value[j]:
                continue
            vals.append(f[k] / s.value[j])
        if len(vals) >= 5:
            out[d] = st.mean(vals)
    return out


# ------------------------------------------------------- 결과 1: 십분위/극단
def decile_table(days, vals, outcome, n: int = 10):
    vs = [(vals[d], outcome[d]) for d in days
          if vals.get(d) is not None and d in outcome]
    if len(vs) < 100:
        return None
    vs.sort()
    size = len(vs) // n
    out = []
    for i in range(n):
        lo = i * size
        hi = (i + 1) * size if i < n - 1 else len(vs)
        chunk = [y for _x, y in vs[lo:hi]]
        out.append((len(chunk), st.mean(chunk)))
    return out


def tail_gap(days, vals, outcome, pct: float):
    """상위 pct 평균 - 하위 pct 평균. 표본수도 같이 돌려준다."""
    vs = [(vals[d], outcome[d]) for d in days
          if vals.get(d) is not None and d in outcome]
    if len(vs) < 100:
        return None
    vs.sort()
    k = max(3, int(len(vs) * pct))
    lo = [y for _x, y in vs[:k]]
    hi = [y for _x, y in vs[-k:]]
    return {"n": k, "lo": st.mean(lo), "hi": st.mean(hi),
            "gap": st.mean(hi) - st.mean(lo),
            "n_independent": max(1, k // REBAL)}


# ------------------------------------- 결과 2: 평소 보유 + AND 조건 매매
def fit_directions(fit_days, sigs, outcome) -> dict:
    """각 지표의 '유리한 방향' 을 학습 구간에서만 정한다.

    사용자는 "다 안좋을 때 매수" 라고 했지만 십분위에서 기관은 팔았을 때가,
    외국인은 샀을 때가 좋았다. 방향이 지표마다 다르므로 데이터가 정하게 한다.
    """
    out = {}
    for name, sig in sigs.items():
        xs, ys = [], []
        for d in fit_days:
            if sig.get(d) is None or d not in outcome:
                continue
            xs.append(sig[d])
            ys.append(outcome[d])
        if len(xs) < 50:
            out[name] = 1.0
            continue
        mx, my = st.mean(xs), st.mean(ys)
        out[name] = 1.0 if sum((x - mx) * (y - my)
                               for x, y in zip(xs, ys)) >= 0 else -1.0
    return out


def hold_simulate(days, sigs, keys, dirs, cuts, q, target, seg, seg_nf):
    """기본은 보유. 모두 유리하면 매수, 모두 불리 + 수익 target 이상이면 매도.

    -> (거래목록, 일별 평가금액, 최종 배수)
    """
    trades, curve = [], []
    equity, pos = 1.0, None

    def value(pos_, n):
        v = pos_[2]
        if pos_[1] < n:
            r = seg_nf(days[pos_[1]], days[n])
            if r is not None:
                v *= (1 + r / 100)
        return v

    for n, d in enumerate(days):
        vals = [sigs[k].get(d) for k in keys]
        if any(v is None for v in vals):
            curve.append(equity if pos is None else equity * value(pos, n))
            continue
        fav = all((v >= cuts[k][1 - q]) if dirs[k] > 0 else
                  (v <= cuts[k][q]) for k, v in zip(keys, vals))
        unfav = all((v <= cuts[k][q]) if dirs[k] > 0 else
                    (v >= cuts[k][1 - q]) for k, v in zip(keys, vals))
        if pos is None:
            if fav:
                pos = [n, n, 1.0]
        else:
            if n - pos[1] >= REBAL:          # 보유 중 리밸런스 (수수료 포함)
                r = seg(days[pos[1]], days[n])
                if r is not None:
                    pos[2] *= (1 + r / 100)
                pos[1] = n
            if unfav and (value(pos, n) - 1) * 100 >= target:
                v = value(pos, n) * (1 - FEE / 100)
                trades.append((days[pos[0]], days[n], n - pos[0],
                               (v - 1) * 100))
                equity *= v
                pos = None
        curve.append(equity if pos is None else equity * value(pos, n))
    if pos is not None:
        n = len(days) - 1
        v = value(pos, n) * (1 - FEE / 100)
        trades.append((days[pos[0]], days[n], n - pos[0], (v - 1) * 100))
        equity *= v
    return trades, curve, equity


def baseline_curve(days, seg, seg_nf):
    """항상 보유 + 20일 리밸런스의 일별 평가금액."""
    curve, equity, last = [], 1.0, 0
    for n in range(len(days)):
        if n - last >= REBAL:
            r = seg(days[last], days[n])
            if r is not None:
                equity *= (1 + r / 100)
            last = n
        v = equity
        if last < n:
            r = seg_nf(days[last], days[n])
            if r is not None:
                v = equity * (1 + r / 100)
        curve.append(v)
    return curve


def _prep(verbose=True):
    import analyze_timing as T
    dates, panel = S.load_panel(verbose=verbose)
    picks = T.build_picks(dates, panel, verbose)
    dmap = {d: i for i, d in enumerate(dates)}
    codes = {c for ps in picks.values() for c in ps}

    def seg(a, b):
        return T.trade_return(panel, picks.get(a) or [], a, b, dmap, FEE)

    def seg_nf(a, b):
        return T.trade_return(panel, picks.get(a) or [], a, b, dmap, 0.0)

    outcome = {}
    for d in sorted(picks):
        i = dmap[d]
        if i + REBAL < len(dates):
            r = seg(d, dates[i + REBAL])
            if r is not None:
                outcome[d] = r
    return dates, panel, picks, dmap, codes, seg, seg_nf, outcome


def run_deciles(verbose=True) -> dict:
    dates, panel, picks, dmap, codes, seg, _snf, outcome = _prep(verbose)
    flow = load_stock_flow(codes)
    day_vals = S.load_day_scores()

    sigs = {}
    for k in mi.PREDICTOR_FIELDS:
        sigs[k] = {d: v.get(k) for d, v in day_vals.items()}
    for which, label in (("기관", "stk_inst"), ("외국인", "stk_frgn"),
                         ("개인", "stk_indiv")):
        sigs[label] = basket_flow_signal(dates, panel, picks, flow, which)

    usable = [d for d in sorted(outcome) if d in day_vals]
    half = len(usable) // 2
    A, B = usable[:half], usable[half:]
    out = {"n": len(usable), "keys": {}}
    for k, sig in sigs.items():
        da, db = (decile_table(A, sig, outcome), decile_table(B, sig, outcome))
        if da is None or db is None:
            continue
        ga, gb = da[-1][1] - da[0][1], db[-1][1] - db[0][1]
        tails = {}
        for p in TAIL_PCTS:
            ta, tb = tail_gap(A, sig, outcome, p), tail_gap(B, sig, outcome, p)
            if ta and tb:
                tails[p] = (ta, tb)
        out["keys"][k] = {"dec_a": da, "dec_b": db, "gap_a": ga, "gap_b": gb,
                          "same": (ga > 0) == (gb > 0), "tails": tails}
    if verbose:
        _report_deciles(out, A, B, outcome)
    return out


def _report_deciles(o, A, B, outcome):
    print(f"\n쓸 수 있는 날 {o['n']}일 (겹치는 회차, 각 반기 독립 표본 약 "
          f"{len(A)//REBAL}개)")
    print(f"  전반부 평균 {st.mean([outcome[d] for d in A]):+.3f}% / "
          f"후반부 평균 {st.mean([outcome[d] for d in B]):+.3f}%")
    print(f"\n{'='*92}")
    print("=== 끝칸 차이 (10분위 - 1분위), 전·후반부 부호 일치 여부 ===")
    print(f"{'='*92}")
    rows = sorted(o["keys"].items(), key=lambda kv: -abs(kv[1]["gap_b"]))
    for k, v in rows:
        print(f"  {k:<14} 전반부 {v['gap_a']:+7.2f}%p  후반부 "
              f"{v['gap_b']:+7.2f}%p   {'O' if v['same'] else 'X'}")
    same = sum(1 for _k, v in rows if v["same"])
    print(f"\n  같은 방향 {same}/{len(rows)}개 (우연이면 {len(rows)/2:.1f}개)")

    print(f"\n{'='*92}")
    print("=== 극단으로 좁히면 더 갈리나 (상위 - 하위). n 은 표본일, 괄호는 "
          "독립 표본 ===")
    print(f"{'='*92}")
    for k, v in rows:
        if not v["tails"]:
            continue
        cells = []
        for p in TAIL_PCTS:
            if p not in v["tails"]:
                continue
            ta, tb = v["tails"][p]
            cells.append(f"{int(p*100):>2}%(n={ta['n']:>3},독립{ta['n_independent']:>2}) "
                         f"전{ta['gap']:+6.2f} 후{tb['gap']:+6.2f}")
        print(f"  {k:<14} " + " | ".join(cells))
    print(CAUTION_DEC)


def run_hold(n_shift: int = N_SHIFT, verbose=True) -> dict:
    dates, panel, picks, dmap, codes, seg, seg_nf, outcome = _prep(verbose)
    flow = load_stock_flow(codes)
    sigs = {w: basket_flow_signal(dates, panel, picks, flow, w)
            for w in FLOW_IDX}
    usable = sorted(set.intersection(*(set(s) for s in sigs.values())))
    half = len(usable) // 2
    out = {"n": len(usable), "dirs": {}, "runs": {}}

    for dirname, fit, test in (("forward", usable[:half], usable[half:]),
                               ("reverse", usable[half:], usable[:half])):
        dirs = fit_directions(fit, sigs, outcome)
        cuts = {}
        for k, sig in sigs.items():
            fv = sorted(v for d in fit if (v := sig.get(d)) is not None)
            cuts[k] = {}
            for q in QS:
                cuts[k][q] = fv[int(len(fv) * q)]
                cuts[k][1 - q] = fv[int(len(fv) * (1 - q))]

        bc = baseline_curve(test, seg, seg_nf)
        rows = []
        for keys in COMBOS:
            for q in QS:
                for tg in TARGETS:
                    tds, curve, eq = hold_simulate(test, sigs, keys, dirs,
                                                   cuts, q, tg, seg, seg_nf)
                    if not tds:
                        continue
                    hs = [t[2] for t in tds]
                    rows.append({
                        "keys": keys, "q": q, "target": tg, "n": len(tds),
                        "cum": (eq - 1) * 100,
                        "mdd_trades": mdd_from_trades([t[3] for t in tds]),
                        "mdd_curve": mdd_from_curve(curve),
                        "hold": st.mean(hs), "hold_max": max(hs),
                        "inmkt": sum(hs) / len(test) * 100})
        rows.sort(key=lambda r: -r["cum"])
        d = {"fit_span": (fit[0], fit[-1]), "test_span": (test[0], test[-1]),
             "dirs": dirs, "rows": rows,
             "base_cum": (bc[-1] - 1) * 100, "base_mdd": mdd_from_curve(bc)}

        if rows and n_shift and dirname == "forward":
            rng = np.random.default_rng(SEED)
            nt = len(test)
            saved = {k: dict(s) for k, s in sigs.items()}
            bests = []
            for off in rng.integers(REBAL, max(REBAL + 1, nt - REBAL),
                                    size=n_shift):
                shifted = {}
                for k, s in saved.items():
                    vals = [s.get(x) for x in test]
                    shifted[k] = {test[j]: vals[(j + int(off)) % nt]
                                  for j in range(nt)}
                top = None
                for keys in COMBOS:
                    for q in QS:
                        for tg in TARGETS:
                            _t, _c, eq = hold_simulate(test, shifted, keys,
                                                       dirs, cuts, q, tg,
                                                       seg, seg_nf)
                            if not _t:
                                continue
                            c = (eq - 1) * 100
                            if top is None or c > top:
                                top = c
                if top is not None:
                    bests.append(top)
            bests.sort()
            if bests:
                d["shift"] = {
                    "n": len(bests), "med": bests[len(bests) // 2],
                    "p95": bests[int(len(bests) * 0.95)],
                    "beat": sum(1 for b in bests
                                if b >= rows[0]["cum"]) / len(bests)}
        out["runs"][dirname] = d
    if verbose:
        _report_hold(out)
    return out


def _report_hold(o):
    for dirname, label in (("forward", "정방향: 전반부에서 방향 -> 후반부 채점"),
                           ("reverse", "역방향: 후반부에서 방향 -> 전반부 채점")):
        d = o["runs"].get(dirname)
        if not d:
            continue
        print(f"\n{'='*100}")
        print(f"=== {label}  (채점 {d['test_span'][0]}~{d['test_span'][1]}) ===")
        print(f"{'='*100}")
        print("  유리한 방향(학습 구간): " +
              ", ".join(f"{k}={'높을때' if v > 0 else '낮을때'}"
                        for k, v in d["dirs"].items()))
        print(f"\n  [기준선] 항상 보유 + {REBAL}일 리밸런스  "
              f"누적 {d['base_cum']:+.1f}%  평가MDD {d['base_mdd']:+.1f}%")
        print(f"\n  {'조건':<20} {'q':>4} {'목표':>5} {'거래':>4} {'누적':>8} "
              f"{'거래MDD':>8} {'평가MDD':>8} {'평균보유':>8} {'최장':>7} {'체류':>6}")
        for r in d["rows"][:6]:
            print(f"  {'+'.join(r['keys']):<20} {int(r['q']*100):>3}% "
                  f"{r['target']:>4.0f}% {r['n']:>4} {r['cum']:>+8.1f} "
                  f"{r['mdd_trades']:>+8.1f} {r['mdd_curve']:>+8.1f} "
                  f"{r['hold']:>7.0f}일 {r['hold_max']:>6}일 {r['inmkt']:>5.0f}%")
        sh = d.get("shift")
        if sh:
            print(f"\n  [대조군] 신호 밀어놓기 {sh['n']}번: 중간값 {sh['med']:+.1f}% "
                  f"상위5% {sh['p95']:+.1f}%")
            print(f"    실제 최고 {d['rows'][0]['cum']:+.1f}% 보다 좋은 우연 "
                  f"{sh['beat']*100:.1f}%"
                  + ("   <- 탈락" if sh["beat"] > 0.05 else "   <- 통과"))
            if sh["med"] > d["base_cum"]:
                print(f"    밀어놓기 중간값({sh['med']:+.1f}%)이 기준선"
                      f"({d['base_cum']:+.1f}%)보다 높다 - 그 차이는 지표가 "
                      f"아니라 설계가 만든 것이다.")
    print(CAUTION_HOLD)


CAUTION_DEC = """
[결과를 볼 때]
  - 겹치는 회차다. 상·하위 2% 는 표본 12일이고 독립 표본은 1개 미만이다.
    숫자가 커 보이는 것 자체가 표본이 작다는 신호다.
  - 네 임계값(20/10/5/2%)은 같은 데이터를 겹쳐 자른 것이라 독립된 증거 네
    개가 아니다. 실질 증거는 반기당 부호 하나씩, 즉 2개다.
  - 지표 16개 중 절반은 부호가 우연히 맞는다. 몇 개가 일관돼 보인다고
    발견이 아니다.
"""

CAUTION_HOLD = """
[결과를 볼 때]
  - '거래MDD' 와 '평가MDD' 를 반드시 같이 본다. 매도에 수익률 조건이 걸리면
    실현된 거래는 전부 플러스여서 거래MDD 가 0.0% 로 나온다. 그건 측정
    착각이고, 보유 중 평가손실을 포함한 평가MDD 가 실제 위험이다.
  - 밀어놓기 중간값을 기준선과 비교할 것. 중간값이 기준선보다 높으면 그
    차이는 지표가 아니라 설계(덜 머무르기 + 손실 중 안 팔기)가 만든 것이다.
  - '손실 중에는 안 판다' 의 실패 방식은 하락장에서 드러난다. 매도 조건이
    영영 안 걸려 한 번 사고 400거래일 넘게 들고 있게 된다. 거래 횟수가
    1~2회로 떨어지면 그건 전략이 아니라 표본 1개다.
  - AND 조건은 보유기간을 실제로 늘린다 (평균 41~88일). 수수료는 문제가
    아니게 되지만, 그만큼 거래 수가 줄어 판정이 어려워진다.
"""


def main() -> int:
    p = argparse.ArgumentParser(description="극단 진단 + 평소보유 AND 전략")
    p.add_argument("--what", choices=("deciles", "hold", "both"),
                   default="both")
    p.add_argument("--no-shift", action="store_true")
    a = p.parse_args()
    if a.what in ("deciles", "both"):
        run_deciles()
    if a.what in ("hold", "both"):
        run_hold(n_shift=0 if a.no_shift else N_SHIFT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
