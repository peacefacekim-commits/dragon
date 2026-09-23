"""바스켓 자신의 움직임으로 타이밍을 잡을 수 있나 - 20번째 가설.

(2026-09-17 신설) 사용자: "종목을 선정한 상태에서 더 타이밍은 절대 잡을 수
없다는 거야? 시장전체가 아니라 우리가 특정종목을 선택한 상태에서 그걸
예측하는 거"

먼저 확실히 해둘 것: 앞선 19번의 타이밍 테스트는 이미 '뽑은 10종목의 수익'
을 목표로 했다. 시장지수를 맞히려던 게 아니다. 그건 맞다.

그런데 **신호** 로 쓴 것은 전부 외부 지표였다 - 미국지수, VIX, 환율, 시장폭,
시장 전체 수급, 종목별 수급. **바스켓 자신의 가격 움직임은 한 번도 안 썼다.**
이건 다른 정보다. 은행·통신 바스켓이 자기가 5% 빠진 상태라는 것은 시장이
5% 빠진 것과 같지 않다 (저변동 종목은 시장과 덜 움직이므로). 그 구멍을 메운다.

신호 6개 (전부 전날 종가까지만 본다)
  self_ret5/20/60  바스켓의 최근 5/20/60거래일 수익
  self_dd          최근 60일 고점에서 내려온 낙폭
  self_vol20       바스켓의 최근 20일 변동성
  self_disp        바스켓 안 종목 간 20일 수익률 표준편차 (분산도)

결과 (2026-09-17). 겹치지 않는 62회차.

  [반기 양방향] 채점 구간 상관과 부호 일치
    self_ret5    +0.174 -> -0.064   X
    self_ret20   +0.034 -> -0.269   X
    self_ret60   -0.123 -> -0.056   O
    self_dd      -0.157 -> +0.010   X
    self_vol20   +0.168 -> -0.061   X
    self_disp    +0.013 -> -0.183   X
    부호 유지 1/6 (우연이면 3개)

  정방향에서는 '신호가 유리한 절반만 투자' 가 여섯 개 모두 전부 투자보다
  나빴다 (-0.026 ~ -1.111%p). 걸러내는 것 자체가 손해였다.

  [전체 62회차 + 대조군] 신호를 회차 사이에서 무작위로 섞기 2000번
    self_ret5   상관 +0.016  우연 25.7%  탈락
    self_ret20  상관 -0.116  우연 49.5%  탈락
    self_ret60  상관 +0.026  우연 31.3%  탈락
    self_dd     상관 -0.011  우연 68.7%  탈락
    self_vol20  상관 +0.072  우연 19.2%  탈락
    self_disp   상관 +0.000  우연 20.4%  탈락

  상관이 전부 0 근처다 (+0.000 ~ -0.116). 여섯 개 다 탈락.

왜 시계열은 안 되고 횡단면은 되는가 - 구조적인 이유

  시계열  독립 표본이 62개뿐이다. 회차당 표준편차가 4.62% 인데 그 대부분이
          시장 변동이고, 찾는 효과는 1%p 급이다. +1%p 를 확인하려면 회차
          167개 = 13년이 필요하다. 못 찾은 게 아니라 **이 표본으로는 확인
          자체가 불가능** 하다.
  횡단면  관측치가 62회차 x 60종목 = 3,720개다. 그리고 상위10-하위10 차이를
          보면 시장 변동이 상쇄된다. 남는 표준오차가 0.8%p 로 시계열의
          1/6 이다. 그래서 같은 크기의 효과가 보인다.

  즉 '절대 불가능' 이 아니라 '이 데이터로는 확인 불가능' 이다. 단 하루
  단위는 독립 표본 1,257개로 표본이 충분했고, 거기서는 자기상관 +0.002
  (표준오차 0.028) 로 '없다' 에 가깝게 나왔다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_self_signal.py
"""
import pathlib as _pathlib
# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = str(_pathlib.Path(__file__).resolve().parent)
import math
import statistics as st
import sys

import numpy as np

sys.path.insert(0, _ROOT)
import strategy as S  # noqa: E402

PICKS = None   # 캐시를 쓰지 않고 패널에서 직접 계산한다
HOLD = 20
FEE = S.FEE_ROUND_TRIP_PCT
N_PERM = 2000
rng = np.random.default_rng(20260924)

import analyze_timing as T

dates, panel = S.load_panel()
picks = T.build_picks(dates, panel)
dmap = {d: i for i, d in enumerate(dates)}


def basket_ret(codes, i_from, i_to):
    """종가 기준 바스켓 평균 수익 (신호 계산용, 수수료 없음)."""
    rs = []
    for c in codes:
        s = panel.get(c)
        if s is None:
            continue
        a, b = s.pos.get(i_from), s.pos.get(i_to)
        if a is None or b is None:
            continue
        rs.append(s.close[b] / s.close[a] - 1)
    return st.mean(rs) * 100 if rs else None


def trade_ret(entry_d, exit_d):
    """시가 -> 시가, 수수료 차감. strategy.py 와 같은 보수적 가정."""
    return T.trade_return(panel, picks.get(entry_d) or [], entry_d, exit_d,
                          dmap, FEE)


def self_signals(d):
    """그날 뽑힌 바스켓의, 전날까지의 자기 움직임."""
    i = dmap[d]
    codes = picks.get(d)
    if not codes or i < 62:
        return None
    j = i - 1                       # 전날
    out = {}
    for label, back in (("self_ret5", 5), ("self_ret20", 20),
                        ("self_ret60", 60)):
        r = basket_ret(codes, j - back, j)
        if r is None:
            return None
        out[label] = r
    # 최근 60일 고점 대비 낙폭
    path = []
    v = 1.0
    for k in range(j - 60, j):
        r = basket_ret(codes, k, k + 1)
        if r is None:
            return None
        v *= (1 + r / 100)
        path.append(v)
    peak = max(path)
    out["self_dd"] = (path[-1] / peak - 1) * 100
    # 최근 20일 바스켓 변동성
    dr = []
    for k in range(j - 20, j):
        r = basket_ret(codes, k, k + 1)
        if r is None:
            return None
        dr.append(r)
    out["self_vol20"] = st.pstdev(dr)
    # 종목 간 분산도 (최근 20일 수익의 표준편차)
    each = []
    for c in codes:
        s = panel.get(c)
        a, b = (s.pos.get(j - 20), s.pos.get(j)) if s else (None, None)
        if a is not None and b is not None:
            each.append((s.close[b] / s.close[a] - 1) * 100)
    if len(each) < 5:
        return None
    out["self_disp"] = st.pstdev(each)
    return out


KEYS = ["self_ret5", "self_ret20", "self_ret60", "self_dd",
        "self_vol20", "self_disp"]

# 겹치지 않는 62회차
rounds = []
di = max(140, S.LIQUIDITY_DAYS + 2)
while di + HOLD < len(dates):
    d = dates[di]
    sg = self_signals(d)
    r = trade_ret(d, dates[di + HOLD]) if sg else None
    if sg and r is not None:
        rounds.append((d, sg, r))
    di += HOLD

print(f"겹치지 않는 회차 {len(rounds)}개 ({rounds[0][0]} ~ {rounds[-1][0]})")
HALF = len(rounds) // 2
print(f"  전반부 {HALF}회 평균 {st.mean([r for _d,_s,r in rounds[:HALF]]):+.3f}% / "
      f"후반부 {len(rounds)-HALF}회 평균 "
      f"{st.mean([r for _d,_s,r in rounds[HALF:]]):+.3f}%")
print(f"\n※ 신호 6개. 방향은 학습 구간에서만 정한다.\n")


def corr(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


print("=" * 88)
print("=== 반기 양방향: 상관과, '유리한 쪽 절반만 투자' 의 성적 ===")
print("=" * 88)
for label, A, B in (("정방향", rounds[:HALF], rounds[HALF:]),
                    ("역방향", rounds[HALF:], rounds[:HALF])):
    print(f"\n  [{label}] 학습 {A[0][0]}~{A[-1][0]} -> 채점 {B[0][0]}~{B[-1][0]}")
    base = [r for _d, _s, r in B]
    print(f"    기준(전부 투자): {len(base)}회 평균 {st.mean(base):+.3f}% "
          f"(±{st.stdev(base)/math.sqrt(len(base)):.3f})")
    print(f"    {'신호':<12} {'학습상관':>9} {'채점상관':>9} {'부호':>5} "
          f"{'유리절반 평균':>13} {'기준대비':>9}")
    for k in KEYS:
        ca = corr([s[k] for _d, s, _r in A], [r for _d, _s, r in A])
        cb = corr([s[k] for _d, s, _r in B], [r for _d, _s, r in B])
        sign = 1 if ca >= 0 else -1
        med = st.median([s[k] * sign for _d, s, _r in A])
        good = [r for _d, s, r in B if s[k] * sign >= med]
        m = st.mean(good) if len(good) >= 5 else float("nan")
        print(f"    {k:<12} {ca:>+9.3f} {cb:>+9.3f} "
              f"{'O' if (ca > 0) == (cb > 0) else 'X':>5} "
              f"{m:>+13.3f} {m - st.mean(base):>+9.3f}")

# ---------------------------------------- 전체 62회차 + 대조군
print("\n" + "=" * 88)
print("=== 전체 62회차: '신호 유리한 절반만 투자' vs 전부 투자 ===")
print("=== 대조군: 신호를 회차 사이에서 무작위로 섞기 (2000번) ===")
print("=" * 88)
allr = [r for _d, _s, r in rounds]
print(f"  전부 투자: {len(allr)}회 평균 {st.mean(allr):+.3f}%")
for k in KEYS:
    xs = [s[k] for _d, s, _r in rounds]
    c = corr(xs, allr)
    sign = 1 if c >= 0 else -1
    med = st.median([x * sign for x in xs])
    real = st.mean([r for (_d, s, r) in rounds if s[k] * sign >= med])
    perm = []
    for _ in range(N_PERM):
        order = rng.permutation(len(rounds))
        sh = [xs[order[i]] for i in range(len(rounds))]
        m2 = st.median([x * sign for x in sh])
        sel = [allr[i] for i in range(len(rounds)) if sh[i] * sign >= m2]
        if len(sel) >= 5:
            perm.append(st.mean(sel))
    perm.sort()
    above = sum(1 for p in perm if p >= real) / len(perm)
    print(f"  {k:<12} 상관 {c:+.3f}  유리절반 {real:+.3f}%  "
          f"무작위 중간값 {perm[len(perm)//2]:+.3f}%  "
          f"우연 {above*100:>5.1f}%" + ("  탈락" if above > 0.05 else "  통과"))
