"""'나쁜 날에 쉰다' 는 규칙을 검사하는 두 가지 대조군.

(2026-09-17 신설) 사용자 제안: "일관성 있어보이는 지표들을 다 조건으로
삼아서 모든 조건에 만족하면 투자를 안하는 식으로 짜면 작동할 법한데?"

이 제안은 내가 전에 테스트한 것과 수학적으로 다르다.

  이전  지표를 표준화해 '평균' 낸 점수 -> 선형. 상관으로 측정된다.
  제안  지표가 모두 나쁠 때만 발동 -> 비선형 교집합. 개별 상관이 0이어도
        작동할 수 있다. 상관 0 은 AND 조건의 실패를 증명하지 않는다.

그래서 제대로 탐색했다. 그런데 이런 탐색은 반드시 뭔가를 찾아내므로,
'찾았다' 를 주장하려면 대조군이 두 개 필요하다. 이 파일은 그 두 개다.

  대조군 1  어긋나게 밀어놓기 (shift_baseline)
    같은 탐색을 '수익률을 통째로 밀어 짝을 어긋나게 한' 데이터에서 반복한다.
    아무 관계가 없을 때 이 탐색이 찾아내는 성적의 분포가 나온다. 실제 성적이
    그 안에 있으면 찾은 게 아니다.
    무작위로 섞지 않고 미는 이유: 섞으면 회차끼리의 자기상관이 깨져서
    기준선이 실제보다 좁아진다. 밀면 양쪽의 내부 구조는 그대로다.

  대조군 2  무작위로 같은 만큼 쉬기 (exposure_baseline)
    쉬는 규칙은 노출을 줄인다. 노출이 줄면 결과가 달라지는데, 방향과 크기가
    데이터에 따라 다르다. 실제 5일 보유 데이터에서는 무작위로 43% 를 쉬기만
    해도 최대낙폭 중간값이 -33.4% -> -23.6% 로 줄었지만, 오르는 회차가 빠져
    회복이 사라지면 오히려 깊어질 수도 있다 (테스트의 합성 데이터에서 확인).
    그래서 '투자를 덜 하면 낙폭이 줄어든다' 고 가정하지 말고 계산해야 한다.
    비교 대상은 '전부 투자' 라는 점 하나가 아니라 '무작위로 같은 개수만큼
    쉰 경우' 의 분포다 - 그 분포는 넓다. 무작위로 쉬어도 같은 결과가 나오면
    지표는 아무 일도 안 한 것이다.

(2026-09-17 추가) 사용자 제안 2: "좋은 날에만 투자를 해도 될텐데 그 기준까지
합하면 뭔가 찾을 수 있지 않을까?"

이것도 안 본 공간이었다. side="bad" 탐색에서 투자하는 집합은 언제나 AND 의
여집합, 즉 OR 이다. 'AND 로 정의된 투자 집합' 은 한 번도 보지 않았다.
그래서 side="good" 을 따로 만들어 훑었다. 결과는 아래 세 번째 묶음에 있다.
요점은 좋은 쪽이 나쁜 쪽보다 훨씬 좋아 보이면서 동시에 더 분명히 우연이라는
것이다 - 적게 고르면 평균이 크게 흔들리기 때문이다.

이 두 대조군을 붙여 검사한 결과 (2026-09-17):

  [AND 조건 탐색]  지표 13개의 2~5개 조합 x 임계값 5가지 = 11,830가지
    보유 20일  최고 조합 us_vix_chg AND flow_inst (나쁜 쪽 50%)
               190회 발동, 쉬면 평균 +0.387%p 상승
               밀어놓은 데이터의 중간값이 +0.385%p, 48.0% 가 더 좋았다
    보유  5일  최고 +0.099%p, 밀어놓기 중간값 +0.165%p, 92.0% 가 더 좋았다
    보유  1일  최고 +0.074%p, 밀어놓기 중간값 +0.064%p, 34.5% 가 더 좋았다
    세 경우 모두 최악 회차는 전혀 바뀌지 않았다 (-13.97 / -14.41 / -6.08%).

  [전날 하락이면 쉼]  가장 맥박이 있었던 규칙
    보유 1일에서 연도별 부호가 6/6 유지되고 전체 t=-2.39 였다.
    보유 5일로 쓰면 누적 +38.3% -> +45.1%, MDD -33.4% -> -16.8% 로 둘 다
    좋아 보였다. 그런데 무작위로 같은 43% 를 쉬어도 18.0% 는 누적이 더
    좋았고 12.7% 는 MDD 가 더 좋았다. 노출을 줄인 것과 구별되지 않는다.

  [좋은 날에만 투자]  같은 11,830가지를 side="good" 으로 훑었다
    보유 20일  us_dow AND flow_foreign AND flow_inst (좋은 쪽 30%)
               10회 투자(떨어진 덩어리 6개) 평균 +8.609% vs 나머지 +2.137%
               평균 +6.364%p 상승, 최악 -13.97% -> +0.66% (손실 회차 없음)
               그런데 평균의 표준오차가 2.81%p 이고,
               밀어놓기 중간값 +5.670%p, 35.0%가 실제보다 좋았다
    보유  5일  us_sox AND kr_ret5 (좋은 쪽 10%)
               13회 투자(덩어리 10개) 평균 +2.811% vs +0.403%, +2.357%p
               밀어놓기 중간값 +2.268%p, 42.0%가 더 좋았다
    보유  1일  us_sox AND kr_vol20 AND kr_ret5 (좋은 쪽 10%)
               10회 투자 평균 +1.236% vs -0.081%, +1.295%p
               밀어놓기 중간값 +0.999%p, 18.5%가 더 좋았다

    나쁜 쪽(+0.387%p)보다 숫자가 열여섯 배 크지만 우연 비율은 더 나쁘다.
    적게 고르면 평균이 크게 흔들려서, 우연도 그만큼 크게 나오기 때문이다.
    '최악 회차가 없어졌다' 도 마찬가지다 - 10회만 고르면 그 안에 큰 손실이
    안 들어갈 확률 자체가 높다.

    그리고 빡빡한 임계값은 표본이 없어 확인 자체가 불가능했다. 좋은 쪽
    10% 짜리 조합 2,366개 중 후반부에서 10회 이상 나오는 것이 23개뿐이다
    (보유 20일). 즉 '드물게 완벽한 날' 은 5년 데이터로는 판정할 수 없다.
    탐색했다고 말할 수 있는 건 느슨한 임계값(30~50%)까지다.

  [손실 직후]  보유 1일, 독립 표본 1,257개에서 자기상관 +0.002.
    표본이 충분해서 이건 '못 찾았다' 가 아니라 '없다' 에 가깝다
    (상관의 표준오차가 약 0.028 이므로 +0.002 는 0 과 구별되지 않는다).
    보유 20일은 -0.166 이지만 독립 표본이 61개라 판정할 수 없다.

주문은 내지 않는다. 패널 CSV 만 읽는다.

실행:
    python analyze_skip_rules.py --hold 20
    python analyze_skip_rules.py --hold 5 --max-k 3
"""
import argparse
import itertools
import statistics as st
import sys

import numpy as np

import analyze_losers
import market_indicators as mi
import strategy as S

PCTS = (0.10, 0.20, 0.30, 0.40, 0.50)
MIN_FIRE = 10
N_SHIFT = 200
N_TRIAL = 1000
SEED = 20260917


# --------------------------------------------------------------- 기본 산수
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


# ------------------------------------------------- 대조군 2: 노출만 줄인 경우
def exposure_baseline(rets, n_skip: int, n_trial: int = N_TRIAL, seed=SEED):
    """무작위로 n_skip 개를 쉰 경우의 누적/최대낙폭 분포.

    쉰 회차는 수익 0 으로 둔다 (현금). 쉬는 규칙을 평가할 때 '전부 투자'
    와만 비교하면 노출 감소 효과를 지표의 공로로 착각한다.
    """
    rng = np.random.default_rng(seed)
    n = len(rets)
    cums, mdds = [], []
    for _ in range(n_trial):
        pick = set(rng.choice(n, size=n_skip, replace=False).tolist())
        g = [0.0 if i in pick else r for i, r in enumerate(rets)]
        cums.append(cumulative(g))
        mdds.append(max_drawdown(g))
    return sorted(cums), sorted(mdds)


def judge_exposure(rets, skip_mask, n_trial: int = N_TRIAL, seed=SEED) -> dict:
    """쉬는 규칙 하나를 노출 대조군과 비교한다."""
    n_skip = sum(skip_mask)
    gated = [0.0 if s else r for r, s in zip(rets, skip_mask)]
    cums, mdds = exposure_baseline(rets, n_skip, n_trial, seed)
    g_cum, g_mdd = cumulative(gated), max_drawdown(gated)
    return {
        "n": len(rets), "n_skip": n_skip,
        "all_cum": cumulative(rets), "all_mdd": max_drawdown(rets),
        "rule_cum": g_cum, "rule_mdd": g_mdd,
        "rand_cum_med": cums[len(cums) // 2],
        "rand_mdd_med": mdds[len(mdds) // 2],
        # 무작위가 규칙보다 좋았던 비율. 0.05 미만이어야 지표의 공로다.
        "beat_cum": sum(1 for c in cums if c >= g_cum) / len(cums),
        "beat_mdd": sum(1 for m in mdds if m >= g_mdd) / len(mdds),
    }


# ------------------------------------------- 대조군 1: 어긋나게 밀어놓은 경우
def _fit_bad_side(rounds_train, day_vals, keys):
    """각 지표의 '나쁜 방향' 과 분위 기준을 학습 구간에서만 정한다."""
    ys = np.array([r for _d, r in rounds_train])
    bad_dir, cuts = {}, {}
    for k in keys:
        xs = np.array([day_vals[d][k] for d, _r in rounds_train])
        cov = float(((xs - xs.mean()) * (ys - ys.mean())).sum())
        bad_dir[k] = -1 if cov >= 0 else +1   # -1: 작을 때 나쁨
        cuts[k] = {p: float(np.quantile(xs, p if bad_dir[k] == -1 else 1 - p))
                   for p in PCTS}
    return bad_dir, cuts


def and_gate_search(rounds, day_vals, keys, hold: int, max_k: int = 5,
                    n_shift: int = N_SHIFT, seed=SEED,
                    side: str = "bad") -> dict:
    """AND 조합을 전부 훑고, 어긋나게 밀어놓은 기준선과 비교한다.

    side="bad"   나쁜 조건이 다 맞으면 쉰다. 투자하는 집합은 그 여집합(OR).
    side="good"  좋은 조건이 다 맞을 때만 투자한다. 투자 집합 자체가 AND.

    이 둘은 다른 공간이다. AND 의 여집합은 OR 이므로, side="bad" 로 훑어도
    'AND 로 정의된 투자 집합' 은 한 번도 보지 않는다. 그래서 따로 돌린다.
    """
    if side not in ("bad", "good"):
        raise ValueError(f"side 는 bad 또는 good: {side}")
    half = len(rounds) // 2
    tr, te = rounds[:half], rounds[half:]
    bad_dir, cuts_bad = _fit_bad_side(tr, day_vals, keys)
    # 좋은 쪽은 나쁜 쪽의 반대 꼬리다. 방향은 여전히 전반부에서만 정한다.
    good_dir = {k: -v for k, v in bad_dir.items()}
    cuts_good = {}
    for k in keys:
        xs = np.array([day_vals[d][k] for d, _r in tr])
        cuts_good[k] = {p: float(np.quantile(xs, p if good_dir[k] == -1
                                             else 1 - p))
                        for p in PCTS}
    direction = bad_dir if side == "bad" else good_dir
    cuts = cuts_bad if side == "bad" else cuts_good

    te_rets = np.array([r for _d, r in te])
    n = len(te_rets)
    flag = {}
    for k in keys:
        xs = np.array([day_vals[d][k] for d, _r in te])
        for p in PCTS:
            flag[(k, p)] = (xs <= cuts[k][p] if direction[k] == -1
                            else xs >= cuts[k][p])

    combos = []
    for kk in range(2, max_k + 1):
        combos.extend(itertools.combinations(keys, kk))

    masks, labels = [], []
    # 임계값별로 몇 개가 표본 부족으로 빠지는지 센다. 빡빡한 임계값이 전부
    # 빠지면 '드물게 완벽한 날' 은 탐색된 게 아니라 확인 자체가 불가능한
    # 것이므로, 그걸 결론에 섞지 않으려면 알고 있어야 한다.
    by_pct = {p: {"tried": 0, "kept": 0} for p in PCTS}
    for combo in combos:
        for p in PCTS:
            m = flag[(combo[0], p)].copy()
            for k in combo[1:]:
                m &= flag[(k, p)]
            c = int(m.sum())
            by_pct[p]["tried"] += 1
            if c < MIN_FIRE or c > n - MIN_FIRE:
                continue
            by_pct[p]["kept"] += 1
            masks.append(m)
            labels.append((combo, p, c))
    if not masks:
        return {"side": side, "tried": len(combos) * len(PCTS), "kept": 0,
                "by_pct": by_pct}

    M = np.array(masks, dtype=np.float64)
    counts = M.sum(axis=1)

    def best(rets):
        # 선택 집합은 지표에서만 나오므로 순열마다 다시 만들 필요가 없다.
        total = rets.sum()
        fired_sum = M @ rets
        if side == "bad":       # 투자하는 쪽은 발동하지 않은 회차
            sel_sum, sel_n = total - fired_sum, n - counts
        else:                   # 투자하는 쪽이 발동한 회차 그 자체
            sel_sum, sel_n = fired_sum, counts
        gains = sel_sum / sel_n - total / n
        i = int(np.argmax(gains))
        return float(gains[i]), i

    real_gain, ri = best(te_rets)
    combo, p, c = labels[ri]
    m = masks[ri]
    sel_mask = ~m if side == "bad" else m
    sel = te_rets[sel_mask]
    oth = te_rets[~sel_mask]

    # 고른 날들이 서로 hold 일 안에 붙어 있으면 사실상 같은 거래다. 떨어져
    # 있는 덩어리 수를 세야 '몇 번의 서로 다른 거래인가' 를 알 수 있다.
    # 좋은 쪽 탐색에서 특히 중요하다 - 며칠 연속으로 고르면 10회처럼
    # 보여도 실제로는 한 번의 거래일 수 있다.
    sel_idx = np.flatnonzero(sel_mask)
    blocks = 1 if len(sel_idx) else 0
    for a, b in zip(sel_idx, sel_idx[1:]):
        if b - a >= hold:
            blocks += 1
    sel_se = (float(sel.std(ddof=1)) / blocks ** 0.5) if blocks > 1 else None

    rng = np.random.default_rng(seed)
    lo, hi = hold, max(hold + 1, n - hold)
    gains = [best(np.roll(te_rets, int(o)))[0]
             for o in rng.integers(lo, hi, size=n_shift)]
    gains = np.sort(np.array(gains))

    return {
        "side": side,
        "tried": len(combos) * len(PCTS), "kept": len(labels),
        "by_pct": by_pct,
        "n_test": n, "n_independent": n // hold,
        "base_mean": float(te_rets.mean()), "base_worst": float(te_rets.min()),
        "combo": combo, "pct": p, "n_fire": c,
        "n_invest": int(len(sel)),
        "n_blocks": blocks, "se_invest": sel_se,
        "std_invest": float(sel.std(ddof=1)) if len(sel) > 1 else None,
        "mean_invest": float(sel.mean()), "mean_other": float(oth.mean()),
        "worst_invest": float(sel.min()),
        # 예전 이름과의 호환 (side="bad" 기준)
        "mean_fire": float(te_rets[m].mean()),
        "mean_keep": float(te_rets[~m].mean()),
        "worst_keep": float(te_rets[~m].min()),
        "gain": real_gain,
        "shift_med": float(np.quantile(gains, 0.5)),
        "shift_p95": float(np.quantile(gains, 0.95)),
        "shift_max": float(gains[-1]),
        # 밀어놓은 데이터가 실제보다 좋았던 비율. 0.05 미만이어야 발견이다.
        "beat": float((gains >= real_gain).sum()) / len(gains),
    }


# ----------------------------------------------------------- 자기상관 (손실 직후)
def autocorr(rounds, hold: int) -> dict:
    """겹치지 않는 회차로만 본다. 겹치면 같은 날을 공유해 상관이 부풀려진다."""
    seq = [r for _d, r in rounds[::hold]]
    if len(seq) < 20:
        return {"n": len(seq)}
    prev, nxt = seq[:-1], seq[1:]
    c = analyze_losers.corr(prev, nxt)
    a = [x for p, x in zip(prev, nxt) if p < 0]
    b = [x for p, x in zip(prev, nxt) if p >= 0]
    out = {"n": len(seq), "corr": c,
           "se": (1.0 / len(seq) ** 0.5) if seq else None,
           "n_after_loss": len(a), "n_after_win": len(b)}
    if len(a) >= 5 and len(b) >= 5:
        va, vb = st.pvariance(a) / len(a), st.pvariance(b) / len(b)
        out["after_loss"] = st.mean(a)
        out["after_win"] = st.mean(b)
        out["t"] = ((st.mean(a) - st.mean(b)) / (va + vb) ** 0.5
                    if va + vb else None)
    return out


def analyze(hold: int = 20, max_k: int = 5, verbose: bool = True) -> dict:
    dates, panel = S.load_panel(verbose=verbose)
    day_vals = S.load_day_scores()
    keys = mi.PREDICTOR_FIELDS
    rounds = analyze_losers.build_rounds(dates, panel, hold)
    rounds = [(d, r) for d, r in rounds
              if d in day_vals and all(day_vals[d][k] is not None for k in keys)]

    out = {"hold": hold,
           "autocorr": autocorr(rounds, hold),
           "and_gate": and_gate_search(rounds, day_vals, keys, hold, max_k,
                                       side="bad"),
           "and_good": and_gate_search(rounds, day_vals, keys, hold, max_k,
                                       side="good")}
    if verbose:
        _report(out)
    return out


def _report(o: dict) -> None:
    hold = o["hold"]
    a = o["autocorr"]
    print(f"\n=== 보유 {hold}거래일 ===")
    print(f"\n[1] 자기상관 - 손해 본 다음 회차를 예측할 수 있나")
    print(f"  겹치지 않는 회차 {a['n']}개")
    if a.get("corr") is not None:
        print(f"  지난 회차 -> 다음 회차 상관 {a['corr']:+.3f} "
              f"(표준오차 약 {a['se']:.3f})")
        if abs(a["corr"]) < 2 * a["se"]:
            print("  -> 0 과 구별되지 않는다")
    if "after_loss" in a:
        print(f"  손실 직후 {a['n_after_loss']:>4}회 평균 {a['after_loss']:+.3f}%")
        print(f"  이익 직후 {a['n_after_win']:>4}회 평균 {a['after_win']:+.3f}%")
        print(f"  차이 {a['after_loss']-a['after_win']:+.3f}%p"
              + (f"  t={a['t']:+.2f}" if a.get("t") is not None else ""))

    _report_side(o.get("and_gate"), 2, "지표가 다 나쁠 때만 쉰다", "나쁜")
    _report_side(o.get("and_good"), 3, "지표가 다 좋을 때만 투자한다", "좋은")
    print(CAUTION)


def _report_side(g, no: int, title: str, word: str) -> None:
    print(f"\n[{no}] AND 조건 탐색 - {title}")
    if not g or not g.get("kept"):
        print(f"  {(g or {}).get('tried', 0):,}가지 중 표본을 채우는 조합이 없음")
        return
    print(f"  {g['tried']:,}가지 중 {MIN_FIRE}회 이상 나오는 "
          f"{g['kept']:,}가지를 전부 봤다")
    # 임계값별로 몇 개가 살아남았는지. 빡빡한 임계값이 전부 빠졌다면
    # '드물게 완벽한 날' 은 확인 자체가 불가능했다는 뜻이다.
    per = "  ".join(f"{int(p*100)}%:{v['kept']}/{v['tried']}"
                    for p, v in sorted(g["by_pct"].items()))
    print(f"    임계값별 생존 {per}")
    print(f"  후반부 {g['n_test']}회차 (독립 약 {g['n_independent']}개), "
          f"평균 {g['base_mean']:+.3f}%  최악 {g['base_worst']:+.2f}%")
    print(f"  최고 조합: {' AND '.join(g['combo'])} "
          f"(각 지표의 {word} 쪽 {int(g['pct']*100)}%)")
    print(f"    투자 {g['n_invest']}회 평균 {g['mean_invest']:+.3f}% / "
          f"나머지 {g['mean_other']:+.3f}%")
    # 고른 날이 서로 붙어 있으면 사실상 같은 거래다. 덩어리 수가 실제
    # '서로 다른 거래' 횟수이고, 평균의 표준오차는 그 수로 계산해야 한다.
    if g.get("se_invest") is not None:
        print(f"    떨어진 덩어리 {g['n_blocks']}개 "
              f"= 서로 다른 거래 {g['n_blocks']}번, "
              f"평균의 표준오차 {g['se_invest']:.2f}%p")
    else:
        print(f"    떨어진 덩어리 {g['n_blocks']}개 - 사실상 한 번의 거래다")
    print(f"    평균이 {g['gain']:+.3f}%p 올라간다")
    print(f"    최악 회차 {g['base_worst']:+.2f}% -> {g['worst_invest']:+.2f}%"
          + ("   (안 바뀜)"
             if abs(g['worst_invest'] - g['base_worst']) < 1e-9 else ""))
    print(f"  [대조군] 어긋나게 밀어놓고 같은 탐색을 {N_SHIFT}번")
    print(f"    중간값 {g['shift_med']:+.3f}%p / 상위5% {g['shift_p95']:+.3f}%p "
          f"/ 최고 {g['shift_max']:+.3f}%p")
    print(f"    실제보다 좋은 '우연' 이 {g['beat']*100:.1f}%")
    print("    -> " + ("우연으로 충분히 나온다. 찾은 게 아니다."
                       if g["beat"] > 0.05 else
                       "우연으로는 드물다. 더 볼 가치가 있다."))


CAUTION = """
[결과를 볼 때]
  - 조합을 11,830가지 훑으면 아무 관계가 없어도 '최고' 는 반드시 나온다.
    그래서 '어긋나게 밀어놓은 데이터에서 같은 탐색이 찾아내는 성적' 과
    비교해야 한다. 그 분포 안에 있으면 발견이 아니다.
  - 쉬는 규칙을 '전부 투자' 와만 비교하면 안 된다. 노출이 줄면 그것만으로
    결과가 달라지고, 그 폭이 넓다. judge_exposure 로 '무작위로 같은 만큼
    쉰 경우' 의 분포와 비교할 것.
  - 최악 회차가 안 바뀌었는지 본다. 목적이 '큰 손해를 피하는 것' 이라면
    평균이 올라가도 최악이 그대로면 목적을 달성하지 못했다.
  - 회차가 겹치므로 독립 표본은 (회차 / 보유일) 이다.
  - 적게 고르는 규칙(좋은 날에만 투자)은 평균이 크게 흔들린다. 숫자가
    커 보이는 것 자체가 표본이 작다는 신호일 수 있으므로, '떨어진 덩어리
    수' 와 '평균의 표준오차' 를 먼저 본다. 붙어 있는 날들은 같은 거래라서
    새 정보가 아니다.
  - '임계값별 생존' 에서 빡빡한 쪽이 거의 다 빠졌으면, 그 영역은 탐색한
    것이 아니라 확인이 불가능한 것이다. 결론에 섞지 말 것.
"""


def main() -> int:
    p = argparse.ArgumentParser(description="쉬는 규칙을 대조군과 비교")
    p.add_argument("--hold", type=int, default=20, help="보유 거래일, 기본 %(default)s")
    p.add_argument("--max-k", type=int, default=5, help="AND 조합 최대 개수")
    a = p.parse_args()
    analyze(hold=a.hold, max_k=a.max_k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
