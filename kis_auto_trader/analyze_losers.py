"""전략대로 샀는데 손실이 난 회차들의 지표 공통점을 찾아본다.

(2026-09-17 신설) 사용자 요청: "전략대로 샀을 때 하락한 날들의 지표 공통점을
찾고, 앞으로 투자를 모의로 진행했을 때 그 지표가 작동하는지 지켜보자."

이전 열세 번의 시도와 뭐가 다른가:

  이전  지표로 '시장 전체의 그날 등락' 을 맞히려 했다. 안 됐다.
  이번  지표로 '저변동 10종목을 산 회차의 수익' 을 맞히려 한다.
        목표가 다르므로 다시 볼 가치가 있다. 시장이 빠질 때 저변동
        종목은 덜 빠지므로 같은 지표가 다르게 작동할 수 있다.

표본을 어떻게 다루나:
  회차를 20일마다 끊으면 62개뿐이다. 그래서 '매일 진입했다면' 으로 회차를
  겹쳐 만들어 관측치를 1,200개로 늘린다. 다만 겹치므로 독립 표본은 여전히
  (일수 / 보유일) 이다. 둘 다 출력한다.

무엇을 확인하나:
  1) 전반부에서 손실 회차와 이익 회차의 지표 평균이 갈리는가
  2) 그 방향이 후반부에서도 유지되는가  <- 여기서 떨어진다
  3) 13개 지표를 보면 우연히 몇 개가 유지되는가 (기준선: 절반)
  4) 전반부에서 만든 종합 점수를 후반부에 적용하면 상관이 얼마인가

결과 (2026-09-17 실행):

  보유 20일  겹치는 회차 1,196개 (독립 표본 약 59개), 손실 507개(42.4%)
    전반부에서 가장 크게 갈린 지표      kr_vol20  상관 +0.222
    그 지표의 후반부 상관               -0.204   <- 부호가 뒤집혔다
    13개 중 부호 유지                    7개      (우연이면 6.5개)
    종합 점수 상관  전반부 +0.187  ->   후반부 -0.102
  보유 5일   겹치는 회차 1,210개 (독립 표본 약 242개), 손실 565개(46.7%)
    13개 중 부호 유지                    4개      (우연보다 적다)
    종합 점수 상관  전반부 +0.082  ->   후반부 -0.047

  그리고 후반부에서 하위 X% 를 쉬어도 '최악 회차' 는 모든 기준에서 똑같았다
  (20일 -13.97%, 5일 -14.41%). 걸러내려던 그 회차가 안 걸러졌다.

결론: 손실난 회차의 공통점은 과거 구간에서 찾을 수 있지만 다음 구간에서
유지되지 않는다. 그래서 과거를 더 파는 대신 paper_trade.py 로 기준을 얼려
앞으로 채점한다.

주문은 내지 않는다. 패널 CSV 만 읽는다.

실행:
    python analyze_losers.py            # 보유 20일
    python analyze_losers.py --hold 5
"""
import argparse
import math
import statistics as st
import sys

import market_indicators as mi
import strategy as S

TOP_N = 10
FACTOR = "low_vol"


def corr(xs, ys, min_n: int = 10):
    if len(xs) < min_n:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def split_gap(rows, day_vals, key):
    """손실 회차와 이익 회차의 지표 평균 차이를 표준편차 단위로.

    양수면 '손실난 회차에서 이 지표가 더 컸다' 는 뜻이다.
    """
    lose = [day_vals[d][key] for d, r in rows if r < 0]
    win = [day_vals[d][key] for d, r in rows if r >= 0]
    if not lose or not win:
        return None
    sd = st.pstdev([day_vals[d][key] for d, _r in rows]) or 1.0
    return (st.mean(lose) - st.mean(win)) / sd


def build_rounds(dates, panel, hold: int) -> list:
    """매일 진입한 회차를 다 만든다 -> [(진입일, 수익률%)]. 겹친다."""
    out = []
    start = max(140, S.LIQUIDITY_DAYS + 2)
    for di in range(start, len(dates) - hold):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(S.factor_score(panel, c, di, FACTOR), c) for c in cand]
        sc = [(s, c) for s, c in sc if s is not None]
        if len(sc) < TOP_N:
            continue
        sc.sort(reverse=True)
        rets = []
        for _s, c in sc[:TOP_N]:
            r, _cut = S.trade_return(panel, c, di, di + hold)
            if r is not None:
                rets.append(r)
        if rets:
            out.append((dates[di], st.mean(rets) - S.FEE_ROUND_TRIP_PCT))
    return out


def analyze(hold: int = 20, verbose: bool = True) -> dict:
    dates, panel = S.load_panel(verbose=verbose)
    day_vals = S.load_day_scores()
    keys = mi.PREDICTOR_FIELDS

    rounds = build_rounds(dates, panel, hold)
    usable = [(d, r) for d, r in rounds
              if d in day_vals and all(day_vals[d][k] is not None for k in keys)]
    if len(usable) < 100:
        if verbose:
            print(f"[!] 표본이 {len(usable)}개뿐입니다.")
        return {"n": len(usable)}

    half = len(usable) // 2
    tr, te = usable[:half], usable[half:]

    gaps = []
    for k in keys:
        g1, g2 = split_gap(tr, day_vals, k), split_gap(te, day_vals, k)
        if g1 is None or g2 is None:
            continue
        c1 = corr([day_vals[d][k] for d, _r in tr], [r for _d, r in tr])
        c2 = corr([day_vals[d][k] for d, _r in te], [r for _d, r in te])
        gaps.append({"key": k, "gap_train": g1, "gap_test": g2,
                     "corr_train": c1, "corr_test": c2,
                     "same_sign": (g1 > 0) == (g2 > 0)})
    gaps.sort(key=lambda g: -abs(g["gap_train"]))
    kept = sum(g["same_sign"] for g in gaps)

    # 전반부에서 만든 종합 점수를 후반부에 그대로 적용한다.
    sub = {d: {k: day_vals[d][k] for k in keys} for d, _r in usable}
    gate = S.build_day_gate(sub, [d for d, _r in tr], dict(tr))
    comp = {}
    if gate is not None:
        for name, part in (("train", tr), ("test", te)):
            pairs = [(gate["score"](d), r) for d, r in part
                     if gate["score"](d) is not None]
            comp[name] = corr([s for s, _r in pairs], [r for _s, r in pairs])
        pairs = [(gate["score"](d), r) for d, r in te
                 if gate["score"](d) is not None]
        srt = sorted(s for s, _r in pairs)
        comp["skip"] = []
        for pct in (0.0, 0.1, 0.2, 0.3, 0.5):
            cut = srt[int(len(srt) * pct)] if pct else -float("inf")
            keep = [r for s, r in pairs if s >= cut]
            if keep:
                comp["skip"].append((pct, len(keep), st.mean(keep), min(keep)))

    out = {"hold": hold, "n": len(usable), "n_independent": len(usable) // hold,
           "losers": sum(1 for _d, r in usable if r < 0),
           "gaps": gaps, "kept": kept, "comp": comp,
           "train_span": (tr[0][0], tr[-1][0]),
           "test_span": (te[0][0], te[-1][0])}
    if verbose:
        _report(out)
    return out


def _report(o: dict) -> None:
    print(f"\n=== 보유 {o['hold']}거래일, 저변동 {TOP_N}종목, 매일 진입 ===")
    print(f"  겹치는 회차 {o['n']}개 (독립 표본은 약 {o['n_independent']}개)")
    print(f"  손실 회차 {o['losers']}개 ({o['losers']/o['n']*100:.1f}%)")
    print(f"  전반부 {o['train_span'][0]}~{o['train_span'][1]} / "
          f"후반부 {o['test_span'][0]}~{o['test_span'][1]}")

    print("\n  [손실 회차 - 이익 회차 지표 평균 차이, 표준편차 단위]")
    print(f"  {'지표':<14} {'전반부':>9} {'후반부':>9} {'부호':>6} "
          f"{'전반부상관':>11} {'후반부상관':>11}")
    for g in o["gaps"]:
        print(f"  {g['key']:<14} {g['gap_train']:>+9.2f} {g['gap_test']:>+9.2f} "
              f"{'O' if g['same_sign'] else 'X':>6} "
              f"{g['corr_train'] or 0:>+11.3f} {g['corr_test'] or 0:>+11.3f}")
    n = len(o["gaps"])
    print(f"\n  부호 유지 {o['kept']}/{n}개. 우연이면 약 {n/2:.1f}개가 "
          f"유지된다 - 그보다 많아야 의미가 있다.")

    c = o.get("comp") or {}
    if c.get("train") is not None:
        print(f"\n  [전반부에서 만든 종합 점수를 후반부에 적용]")
        print(f"    전반부 상관 {c['train']:+.3f}  ->  후반부 상관 "
              f"{c['test']:+.3f}")
        for pct, n_, mean, worst in c.get("skip", []):
            label = "후반부 전체" if pct == 0 else f"하위 {int(pct*100)}% 쉼"
            print(f"    {label:<14} {n_:>4}회 평균 {mean:+.3f}% "
                  f"최악 {worst:+.2f}%")
    print(CAUTION)


CAUTION = """
[결과를 볼 때]
  - '전반부 상관' 은 그 구간에 맞춘 값이라 성능이 아니다. 후반부 값만 본다.
  - 회차가 겹치므로 독립 표본은 (회차 / 보유일) 이다. 보유 20일이면
    1,200개처럼 보여도 실제로는 60개다.
  - 지표 13개를 늘어놓고 가장 큰 것을 고르면, 아무 관계가 없어도 뭔가
    고르게 된다. 그래서 '후반부에서 부호가 유지되는 개수' 를 우연 기준선
    (절반) 과 비교하는 것이 요점이다.
  - 최악 회차가 모든 기준에서 같은지 본다. 같으면 걸러내려던 바로 그
    회차를 못 걸렀다는 뜻이고, 평균이 좋아져도 목적을 달성하지 못했다.
"""


def main() -> int:
    p = argparse.ArgumentParser(description="손실 회차의 지표 공통점 찾기")
    p.add_argument("--hold", type=int, default=20, help="보유 거래일, 기본 %(default)s")
    a = p.parse_args()
    analyze(hold=a.hold)
    return 0


if __name__ == "__main__":
    sys.exit(main())
