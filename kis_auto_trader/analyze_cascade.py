"""서열이 있는 방식 - 중요한 지표 하나로 걸러내고 나머지로 확인.

(2026-09-18 신설) 사용자: "매일 지표를 볼 필요는 없지 가장 중요한 지표
하나만 탐지하고 그게 통과되면 나머지들을 보면 돼지"

먼저 앞에서 내가 쓴 약한 논거를 취소한다.
  analyze_rare_trading.py 의 비교표에 '조짐을 기다리면 매일 지표를 봐야
  한다' 라고 썼는데, 이건 반론이 못 된다. 프로그램이 자동으로 하는 일이고,
  사용자 말대로 싼 지표 하나로 먼저 걸러내면 비용이 거의 없다. 그 줄은
  틀렸다. 감시 비용은 이 아이디어의 문제가 아니다.

그런데 사용자 말에는 아직 검사하지 않은 가설이 들어 있다. '가장 중요한
지표 하나' 라는 말은 지표에 **서열** 이 있고 하나가 주도하며 나머지는
확인용이라는 뜻이다. 이건 앞의 '몇 개가 일치하나'(analyze_consensus.py)
와 다른 구조다. 그래서 따로 잰다.

  1단계: 가장 중요한 지표가 문턱을 넘나 (위험회피 쪽 상위 30%)
  2단계: 넘은 날에만, 나머지 13개 중 과반이 동의하나

===========================================================================
결과 A - 개별 지표 14개 중 |t| 2 를 넘는 것이 하나도 없다
===========================================================================
  지표              상관      t     상위20%날 수익  하위20%날 수익
  kr_ret5         +0.046  +1.48      +0.2567%      +0.0998%
  kr_breadth5     +0.038  +1.21      +0.1171%      +0.0458%
  kr_vol20        +0.035  +1.13      +0.1467%      +0.0265%
  us_vix_level    +0.035  +1.13      +0.1258%      +0.0328%
  fx_krw          +0.028  +0.89      +0.1369%      +0.0452%
  us_sox          -0.026  -0.83      +0.0456%      +0.1356%
  us_vix_chg      -0.026  -0.83      +0.0680%      +0.1919%
  mkt_value       -0.025  -0.81      -0.0022%      +0.1201%
  us_nasdaq       -0.024  -0.78      +0.1776%      +0.1726%
  us_dow          -0.022  -0.71      +0.1222%      +0.1773%
  us_sp500        -0.021  -0.69      +0.1400%      +0.1997%
  flow_inst       +0.016  +0.51      +0.1317%      +0.1380%
  flow_indiv      +0.007  +0.24      +0.2409%      +0.1630%
  flow_foreign    +0.006  +0.18      +0.0137%      +0.0264%

  제일 센 것이 kr_ret5 의 +1.48 이다. 방향은 사용자 직관과 같다 -
  시장이 5일간 빠진 쪽(위험회피)이 다음날 더 올랐다(+0.2567% vs
  +0.0998%). '나쁜 날에 사라' 가 방향으로는 맞는 쪽이다. 다만 t=1.48
  이라 우연과 구별되지 않는다.

===========================================================================
결과 B - 결정적: 실제 최고가 잡음의 평범한 값보다도 낮다
===========================================================================
지표 14개 중 제일 센 것을 골랐으니, 어긋난 데이터에서도 14개 중
제일 센 것을 골라 비교해야 공평하다. 500번 돌렸다.

  실제 데이터: 14개 중 최고 |t| = 1.48 (kr_ret5)
  어긋난 데이터 500번: 중앙값 1.78 / 95%지점 2.70 / 최대 3.44
  어긋난 데이터가 실제보다 좋았던 비율 = 72.8%

  **실제 데이터의 최고가 잡음의 중앙값(1.78)보다 낮다.** 아무 관계 없는
  데이터를 넣으면 보통 1.78 이 나오는데 진짜 데이터로는 1.48 이 나왔다.
  '14개 중에 하나는 쓸 만한 게 있겠지' 가 성립하지 않는다.

===========================================================================
결과 C - 2단계(확인)가 값을 더하지 않고 깎는다. 6개 전부
===========================================================================
1단계만 vs 1단계+2단계. 1단계로 쓸 지표는 위에서 센 순서로 6개.

  1단계 지표       통과일   1단계만 전체대비 | 2단계 통과일  전체대비  2단계가 더한 것
  kr_ret5          330    +0.1073%       |      211    -0.0028%    -0.0028%p
  kr_breadth5      315    +0.0432%       |      202    +0.0068%    -0.0364%p
  kr_vol20         364    +0.0414%       |      179    -0.0977%    -0.1391%p
  us_vix_level     301    +0.0168%       |      195    -0.0254%    -0.0422%p
  fx_krw           312    +0.0436%       |      161    +0.0162%    -0.0274%p
  us_sox           293    -0.0372%       |      227    -0.0416%    -0.0043%p

  2단계가 더한 값: -0.0028, -0.0364, -0.1391, -0.0422, -0.0274, -0.0043
  음수 6/6개. 전부 음수일 확률(동전던지기) = 1.6%. 평균 -0.0420%p.

  **확인 단계가 일관되게 깎는다.** 나머지 지표들이 동의하는 날로 좁히면
  거래일이 절반쯤 줄어드는데(330 -> 211 등) 남은 날이 더 좋지 않다.
  정보를 더하는 게 아니라 날만 줄인다.

  이유는 analyze_consensus.py 에서 나온 것과 같다. 나머지 13개가 1번
  지표와 독립이 아니다. 실질 독립 지표는 14개 중 6.3개뿐이다. 1번이
  이미 말해준 것을 다시 묻는 셈이라 새 정보가 없고, 표본만 깎인다.

===========================================================================
결과 D - '가장 중요한 지표' 가 시기마다 바뀐다
===========================================================================
어느 지표가 1번인지 미리 알 수 없다. 그래서 한쪽에서 고르고 다른 쪽에서
써봐야 한다.

  [전반부에서 고름] 1번 = us_vix_chg (고른 쪽 t=-2.18)
    1단계만   고른 쪽 -0.1300%p -> 다른 쪽 +0.0059%p   부호 뒤집힘
    1+2단계  고른 쪽 -0.0671%p -> 다른 쪽 -0.0213%p   양쪽 다 손해

  [후반부에서 고름] 1번 = mkt_value (고른 쪽 t=-1.26)
    1단계만   고른 쪽 -0.1050%p -> 다른 쪽 +0.0240%p   부호 뒤집힘
    1+2단계  고른 쪽 -0.2067%p -> 다른 쪽 -0.1156%p   양쪽 다 손해

  두 가지가 드러난다.
  1) 1번 지표가 전반부는 us_vix_chg, 후반부는 mkt_value 로 **바뀐다**.
     고정된 서열이 없다.
  2) 1단계만 쓰면 부호가 양쪽 다 뒤집힌다. 2단계까지 쓰면 부호는
     유지되는데 **양쪽 다 마이너스** 다 - 꾸준히 손해라는 뜻이고
     좋은 소식이 아니다. (부호가 같다는 말에 속으면 안 된다)

===========================================================================
읽는 법
===========================================================================
  1) 감시 비용 이야기는 취소한다. 사용자 말이 맞다. 싼 지표 하나로
     먼저 걸러내면 매일 다 볼 필요가 없고, 어차피 프로그램이 한다.
  2) 그런데 막는 것은 감시 비용이 아니었다. 두 가지다.
       하나, 1단계로 쓸 만한 지표가 없다. 14개 중 최고가 |t|=1.48 이고
       이건 잡음의 중앙값 1.78 보다 낮다.
       둘, 2단계가 값을 깎는다. 6/6 음수, 평균 -0.0420%p.
  3) 2단계가 깎이는 이유가 구조적이다. 나머지 지표가 1번과 독립이 아니라
     (실질 6.3개) 새 정보가 없는데 표본만 줄어든다. 지표를 더 넣어도
     같은 일이 일어난다.
  4) 방향만은 사용자 직관과 맞다. kr_ret5 상위(시장이 빠진 쪽)의 다음날이
     +0.2567%, 하위가 +0.0998% 다. '나쁜 날에 산다' 가 방향으로는 맞는
     쪽이다. 크기가 우연과 구별되지 않을 뿐이다. 이건 '틀렸다' 가 아니라
     '이 데이터로는 확인이 안 된다' 다.
  5) 1일 앞 표본이 1,041개라 일별로는 검정력이 충분하다. 20일 앞은
     유효표본 50개 근처라 여전히 '알 수 없다' 다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_cascade.py
"""
import math
import pathlib
import statistics as st
import sys

import numpy as np

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_consensus as AC  # noqa: E402
import strategy as S  # noqa: E402

LOOK = AC.LOOK
KEYS = AC.KEYS
RISK_OFF = AC.RISK_OFF
GATE_Q = 0.70           # 1단계: 위험회피 쪽 상위 30%
CONFIRM_Q = 0.50        # 2단계: 나머지가 중앙값 넘으면 '동의'
N_SHIFT = 500
SEED = 20260918
TOP_N = 6               # 1단계 후보로 볼 지표 개수


def corr_t(xs, ys):
    """상관과 t. 1일 앞은 겹치지 않으므로 겹침 보정이 필요 없다."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    if xs.std() == 0 or len(xs) < 4:
        return 0.0, 0.0
    r = float(np.corrcoef(xs, ys)[0, 1])
    se = 1 / math.sqrt(len(xs) - 2)
    return r, r / se


def build(dates=None, panel=None):
    """각 날의 지표별 '위험회피 퍼센타일' 과 다음날 바스켓 수익.

    퍼센타일은 과거 LOOK일 분포에서만 잰다 (미래 정보 없음).
    1.0 에 가까울수록 위험회피 쪽 극단이다.
    """
    if dates is None or panel is None:
        dates, panel = S.load_panel()
    mkt = AC.market_value_ratio(dates, panel)
    rows = AC.load_indicators(mkt)
    basket = AC.basket_daily(dates, panel)
    bd = sorted(basket)
    bpos = {d: i for i, d in enumerate(bd)}

    out = []
    for n in range(LOOK, len(rows)):
        d, v = rows[n]
        i = bpos.get(d)
        if i is None or i + 1 >= len(bd):
            continue
        pct = {}
        for k in KEYS:
            x = v[k] * RISK_OFF[k]
            hist = [rows[m][1][k] * RISK_OFF[k] for m in range(n - LOOK, n)]
            pct[k] = sum(1 for h in hist if h < x) / len(hist)
        out.append((d, pct, basket[bd[i + 1]]))
    return out


def rank_indicators(recs):
    """개별 지표를 예측력 순으로. (지표, 상관, t, 상위20%평균, 하위20%평균)"""
    ys = np.array([r[2] for r in recs], float)
    out = []
    for k in KEYS:
        r, t = corr_t([rc[1][k] for rc in recs], ys)
        hi = [rc[2] for rc in recs if rc[1][k] >= 0.80]
        lo = [rc[2] for rc in recs if rc[1][k] <= 0.20]
        out.append((k, r, t,
                    st.mean(hi) if hi else float("nan"),
                    st.mean(lo) if lo else float("nan")))
    return sorted(out, key=lambda x: -abs(x[2]))


def stage1(recs, key):
    """1단계 통과한 날."""
    return [r for r in recs if r[1][key] >= GATE_Q]


def stage2(recs, key):
    """1단계 통과한 날 중 나머지 지표 과반이 동의한 날."""
    others = [o for o in KEYS if o != key]
    return [r for r in stage1(recs, key)
            if sum(1 for o in others if r[1][o] >= CONFIRM_Q) > len(others) / 2]


def excess(sub, recs):
    """전체 평균 대비 초과분. sub 가 너무 작으면 None."""
    if len(sub) < 15:
        return None
    base = st.mean([r[2] for r in recs])
    return st.mean([r[2] for r in sub]) - base


def best_of_n(mat, ys):
    """열 여러 개 중 최고 |t|. 대조군과 똑같은 고르기를 해야 공평하다."""
    best = 0.0
    for j in range(mat.shape[1]):
        _r, t = corr_t(mat[:, j], ys)
        best = max(best, abs(t))
    return best


def main():
    recs = build()
    ys = np.array([r[2] for r in recs], float)
    print(f"표본 {len(recs):,}일 ({recs[0][0]} ~ {recs[-1][0]})")
    print(f"다음날 수익 평균 {ys.mean():+.4f}%, 표준편차 {ys.std():.3f}%")

    # ------------------------------------------------ A) 개별 순위
    print("\n" + "=" * 92)
    print(f"=== A) 개별 지표 {len(KEYS)}개: 다음날 수익 예측력 순위 ===")
    print(f"=== |t|>2 여야 눈여겨볼 값. {len(KEYS)}개를 봤으니 "
          f"하나쯤은 우연히 넘는다 ===")
    print("=" * 92)
    ranked = rank_indicators(recs)
    print(f"  {'지표':<16} {'상관':>8} {'t':>7} "
          f"{'상위20%날':>13} {'하위20%날':>13}")
    for k, r, t, hm, lm in ranked:
        print(f"  {k:<16} {r:>+8.3f} {t:>+7.2f} {hm:>+12.4f}% {lm:>+12.4f}%")
    top_k, _r0, top_t, top_hi, top_lo = ranked[0]
    print(f"\n  제일 센 것: {top_k} (|t| = {abs(top_t):.2f})")
    print(f"  방향은 '나쁜 날에 사라' 쪽이다: 상위20% {top_hi:+.4f}% vs "
          f"하위20% {top_lo:+.4f}%")
    over2 = [k for k, _r, t, _h, _l in ranked if abs(t) > 2]
    print(f"  |t|>2 인 지표: {over2 if over2 else '없음'}")

    # ------------------------------------------------ B) 대조군
    print("\n" + "=" * 92)
    print(f"=== B) 대조군: '{len(KEYS)}개 중 제일 센 것' 이 "
          f"어긋난 데이터에서는 얼마나 나오나 ===")
    print("=== 실제에서 골랐으니 대조군에서도 똑같이 골라야 공평하다 ===")
    print("=" * 92)
    rng = np.random.default_rng(SEED)
    mat = np.array([[r[1][k] for k in KEYS] for r in recs], float)
    real = best_of_n(mat, ys)
    vals = []
    for _ in range(N_SHIFT):
        sh = int(rng.integers(20, len(ys) - 20))
        vals.append(best_of_n(np.roll(mat, sh, axis=0), ys))
    vals.sort()
    beat = sum(1 for v in vals if v >= real) / len(vals)
    med = vals[len(vals) // 2]
    print(f"  실제 데이터: 최고 |t| = {real:.2f} ({top_k})")
    print(f"  어긋난 데이터 {N_SHIFT}번: 중앙값 {med:.2f} / "
          f"95%지점 {vals[int(len(vals)*0.95)]:.2f} / 최대 {vals[-1]:.2f}")
    print(f"  어긋난 데이터가 실제보다 좋았던 비율 = {beat*100:.1f}%")
    if real < med:
        print(f"  -> 실제 최고({real:.2f})가 잡음의 중앙값({med:.2f})보다 "
              f"**낮다**.")
        print("     '여러 개 중 하나는 쓸 만한 게 있겠지' 가 성립하지 않는다.")
    elif beat < 0.05:
        print("  -> 5% 미만. 눈여겨볼 값")
    else:
        print("  -> 어긋난 데이터에서도 흔하다. 찾은 게 아니다")

    # ------------------------------------------------ C) 2단계가 더하나
    print("\n" + "=" * 92)
    print("=== C) 1단계만 vs 1단계+2단계 - 확인 단계가 값을 더하나 ===")
    print(f"=== 1단계: 상위 {(1-GATE_Q)*100:.0f}% / "
          f"2단계: 나머지 {len(KEYS)-1}개 중 과반 동의 ===")
    print("=" * 92)
    print(f"  {'1단계 지표':<16} {'1단계일':>8} {'1단계 초과':>11} | "
          f"{'2단계일':>8} {'2단계 초과':>11} {'2단계가 더한 것':>16}")
    deltas = []
    for k, _r, _t, _h, _l in ranked[:TOP_N]:
        s1, s2 = stage1(recs, k), stage2(recs, k)
        e1, e2 = excess(s1, recs), excess(s2, recs)
        if e1 is None:
            continue
        if e2 is None:
            print(f"  {k:<16} {len(s1):>8} {e1:>+10.4f}% | "
                  f"{len(s2):>8} {'표본 부족':>11}")
            continue
        d = e2 - e1
        deltas.append((k, d))
        print(f"  {k:<16} {len(s1):>8} {e1:>+10.4f}% | "
              f"{len(s2):>8} {e2:>+10.4f}% {d:>+15.4f}%p")
    if deltas:
        neg = sum(1 for _k, d in deltas if d < 0)
        print(f"\n  2단계가 더한 값: "
              + ", ".join(f"{d:+.4f}" for _k, d in deltas))
        print(f"  음수 {neg}/{len(deltas)}개. 전부 한쪽일 확률"
              f"(동전던지기) = {0.5**len(deltas)*100:.1f}%")
        print(f"  평균 {st.mean([d for _k, d in deltas]):+.4f}%p")
        if neg == len(deltas):
            print("\n  확인 단계가 일관되게 깎는다. 거래일이 절반쯤 줄어드는데")
            print("  남은 날이 더 좋지 않다. 정보를 더하는 게 아니라 날만 줄인다.")
            print(f"  이유는 구조적이다 - 나머지 지표가 1번과 독립이 아니다")
            print("  (analyze_consensus.py: 실질 독립은 14개 중 6.3개).")

    # ------------------------------------------------ D) 반기 양방향
    print("\n" + "=" * 92)
    print("=== D) 반기 양방향 - 1번 지표를 한쪽에서 고르고 다른 쪽에서 쓴다 ===")
    print("=== 어느 지표가 1번인지 미리 모르므로 고르는 비용을 물어야 한다 ===")
    print("=" * 92)
    half = len(recs) // 2
    A, B = recs[:half], recs[half:]
    picks = []
    for lab, fit, test in (("전반부에서 고름", A, B), ("후반부에서 고름", B, A)):
        rk = rank_indicators(fit)
        k, t = rk[0][0], rk[0][2]
        picks.append(k)
        print(f"\n  [{lab}] 1번 = {k} (고른 쪽 t={t:+.2f})")
        for stage, fn in (("1단계만", stage1), ("1+2단계", stage2)):
            ef, et = excess(fn(fit, k), fit), excess(fn(test, k), test)
            if ef is None or et is None:
                print(f"    {stage:<8} 표본 부족")
                continue
            if (ef > 0) != (et > 0):
                verdict = "부호 뒤집힘"
            elif ef > 0:
                verdict = "양쪽 다 이득"
            else:
                # 부호가 같아도 둘 다 마이너스면 좋은 소식이 아니다
                verdict = "양쪽 다 손해"
            print(f"    {stage:<8} 고른 쪽 {ef:>+8.4f}%p "
                  f"({len(fn(fit, k))}일) -> 다른 쪽 {et:>+8.4f}%p "
                  f"({len(fn(test, k))}일)  {verdict}")
    print(f"\n  1번 지표가 전반부 {picks[0]}, 후반부 {picks[1]} 로 "
          f"{'바뀐다' if picks[0] != picks[1] else '같다'}.")
    if picks[0] != picks[1]:
        print("  고정된 서열이 없다. '가장 중요한 지표' 를 미리 정할 수 없다.")

    print("\n" + "=" * 92)
    print("=== 결론 ===")
    print("=" * 92)
    print("  감시 비용 이야기는 취소한다. 싼 지표 하나로 먼저 걸러내면")
    print("  매일 다 볼 필요가 없고, 어차피 프로그램이 한다. 그건 문제가")
    print("  아니었다.")
    print("  막는 것은 두 가지다.")
    print(f"    하나, 1단계로 쓸 만한 지표가 없다 (최고 |t|={real:.2f}, "
          f"잡음 중앙값 {med:.2f}).")
    print("    둘, 2단계가 값을 깎는다 (6/6 음수).")
    print("  2단계가 깎이는 것은 구조적이다. 나머지 지표가 1번과 독립이")
    print("  아니라 새 정보 없이 표본만 줄어든다. 지표를 더 넣어도 같다.")
    print("\n  다만 방향은 맞다: 시장이 빠진 쪽의 다음날이 더 올랐다")
    print("  ('나쁜 날에 산다'). 크기가 우연과 구별되지 않을 뿐이다.")
    print("  이건 '틀렸다' 가 아니라 '이 데이터로는 확인이 안 된다' 다.")


if __name__ == "__main__":
    main()
