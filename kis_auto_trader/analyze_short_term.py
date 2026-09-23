"""짧게 사고팔아 시세차익을 노리는 형태가 되나 - 보유기간 훑기.

(2026-09-19 신설) 사용자: "짧게 거래해서 시세차익을 노리는 형태는?"

지금까지 검사한 보유기간은 전부 20일 이상이었다. 짧은 쪽은 안 봤으므로
이건 진짜 빈칸이었다. 짧은 쪽은 표본이 많아 검정력이 좋다 (1일 보유면
회차가 1,257개). 대신 수수료를 자주 낸다.

  왕복 수수료 0.21% 기준 연간 부담
    1일 보유  연 246회  수수료 51.7%
    5일 보유  연  49회  수수료 10.3%
   20일 보유  연  12회  수수료  2.6%
  본전 기준은 어느 쪽이든 같다. **회당 총수익 > 0.21%**

===========================================================================
결과 1 - 짧을수록 손해다. 저변동은 20일이 1일보다 낫다
===========================================================================
'풀 대비' 는 같은 회차에서 유니버스 전체를 동일가중으로 산 것과의 차이다
(그날 시장이 좋았는지가 상쇄된다).

  신호            보유   회차   회당총수익   수수료뺀   풀대비    연환산(순)
  저변동           1일  1257   +0.082%  -0.128%  +0.102%   -27.0%
  저변동           2일   628   +0.150%  -0.060%  +0.193%    -7.2%
  저변동           3일   419   +0.245%  +0.035%  +0.312%    +2.9%
  저변동           5일   251   +0.368%  +0.158%  +0.478%    +8.1%
  저변동          10일   125   +0.603%  +0.393%  +0.851%   +10.1%
  저변동          20일    62   +1.264%  +1.054%  +1.490%   +13.8%

  1일 보유는 연 -27.0%, 20일 보유는 연 +13.8% 다. 같은 신호인데
  짧게 굴리면 손해로 바뀐다.

===========================================================================
결과 2 - 왜 그런가: 엣지는 쌓이고 수수료는 거래마다 고정이다
===========================================================================
  보유    풀대비 엣지   하루당 엣지   수수료   엣지/수수료   순엣지
   1일   +0.102%   +0.102%   0.21%    0.49x  -0.108%
   2일   +0.193%   +0.096%   0.21%    0.92x  -0.017%
   3일   +0.312%   +0.104%   0.21%    1.49x  +0.102%
   5일   +0.478%   +0.096%   0.21%    2.28x  +0.268%
  10일   +0.851%   +0.085%   0.21%    4.05x  +0.641%
  20일   +1.490%   +0.075%   0.21%    7.10x  +1.280%

  **하루당 엣지가 0.075~0.104% 로 거의 일정하다** (평균 0.093%).
  즉 엣지 = 하루당 0.093% x 보유일수 로 시간에 비례해 쌓인다.
  반면 수수료는 거래할 때마다 0.21% 씩 고정으로 나간다.

  => 손익분기 보유기간 = 0.21 / 0.093 = **2.3일**
     그보다 짧으면 수수료가 엣지를 이긴다.
  => 그리고 길수록 엣지/수수료 비율이 계속 좋아진다 (20일이면 7.1배).
     짧게 굴릴 이유가 수학적으로 없다.

  이게 '짧게 거래해서 시세차익' 이 안 되는 이유다. 신호가 없어서가
  아니라 - 신호는 1일에도 살아 있다(+0.102%) - 그 크기가 수수료보다
  작기 때문이다.

===========================================================================
결과 3 - 단기 반전도 모멘텀도 안 된다
===========================================================================
교과서에 나오는 단기 효과를 같이 봤다. 안 보면 빠뜨리는 것이다.

  신호                 보유   풀대비     연환산(순)
  5일 반전(떨어진것)      1일  +0.038%    -37.9%
  5일 반전(떨어진것)      5일  -0.135%    -20.5%
  5일 반전(떨어진것)     20일  -2.831%    -33.8%
  5일 모멘텀(오른것)      1일  -0.334%    -75.2%
  5일 모멘텀(오른것)      5일  -1.238%    -54.0%
  1일 반전              1일  -0.200%    -65.5%
  1일 반전              5일  -0.393%    -30.1%
  20일 반전             1일  +0.026%    -39.9%
  20일 반전             5일  +0.339%     +0.3%

  단기 반전은 1일에서 +0.038% 로 사실상 0 이고 길어지면 마이너스다.
  모멘텀(최근 오른 것 사기)은 전 구간에서 크게 마이너스다 - 이 유니버스
  에서는 최근 많이 오른 종목을 사면 진다. 저변동이 이기는 것과 같은
  이야기의 뒷면이다.

  '20일 반전 / 5일 보유' 가 +0.339% 로 유일하게 플러스인데, 신호 5개 x
  보유 6개 = 30가지를 훑었으므로 우연히 하나쯤 나오는 크기다 (5% 기준
  이면 30개 중 1.5개가 우연히 통과한다). 대조군 통과율도 4.7% 로
  경계선이다. 이것만 떼어 쓰면 안 된다.

===========================================================================
결과 4 - 대조군: 저변동 엣지는 짧은 쪽에서도 진짜다
===========================================================================
회차마다 신호값을 종목끼리 섞어서 '이 신호로 고르는 것의 값' 만 남겼다.

  신호        보유   회차   실제 엣지   대조군 통과율   판정
  저변동       3일   419  +0.312%      0.3%   눈여겨볼 값
  저변동       5일   251  +0.478%      0.6%   눈여겨볼 값
  저변동      20일    62  +1.490%      2.1%   눈여겨볼 값
  20일 반전    5일   251  +0.328%      4.7%   경계선 (30가지 훑음)

  저변동 엣지는 3일/5일에서도 대조군을 통과한다. **신호가 짧은 쪽에서
  죽는 게 아니다.** 다만 그 크기가 수수료를 못 넘을 뿐이다.

===========================================================================
읽는 법
===========================================================================
  1) 짧게 거래하는 형태는 안 된다. 신호가 없어서가 아니라 수수료
     때문이다. 손익분기가 2.3일이고, 길수록 계속 유리하다.
  2) 그러므로 '짧게 vs 길게' 는 취향 문제가 아니라 계산 문제다.
     하루당 엣지 0.093% 와 거래당 수수료 0.21% 가 정해져 있으면
     답은 '길게' 하나뿐이다.
  3) (2026-09-19 정정) 처음에 '수수료가 절반이어도' 라고 썼는데 그건
     현실에서 불가능한 가정이었다. 0.21% 의 구성은
       매수 수수료 0.015% + 매도 수수료 0.015% + 매도 증권거래세 0.180%
     즉 **86% 가 세금이다.** 증권사 수수료를 0 으로 만들어도 0.18% 가
     남고 손익분기는 2.3일 -> 1.9일로 거의 안 변한다.
     수수료를 깎아서 짧은 거래를 성립시킬 수는 없다.
  4) 단기 반전/모멘텀은 이 유니버스에서 작동하지 않는다. 특히 모멘텀은
     크게 마이너스다.
  5) 주의: 여기 회차는 겹치지 않게 잡았고, 매수/매도 모두 시가 기준이다.
     실제로는 호가 스프레드와 체결 미끄러짐이 더 붙으므로 짧은 쪽이
     여기 계산보다 **더** 불리해진다. 이 표는 짧은 쪽에 유리하게
     기울어져 있는데도 안 된다는 뜻이다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_short_term.py
"""
import pathlib
import statistics as st
import sys

import numpy as np

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import strategy as S  # noqa: E402

FEE = S.FEE_ROUND_TRIP_PCT
PICK = 10
N_PERM = 1000
SEED = 20260919
DAYS_PER_YEAR = 246
HOLDS = (1, 2, 3, 5, 10, 20)


def trade_ret(panel, code, a, b):
    """a 시가에 사서 b 시가에 판 수익률(%). 미래 정보 없음."""
    s = panel.get(code)
    if s is None:
        return None
    ja, jb = s.pos.get(a), s.pos.get(b)
    if ja is None or jb is None:
        return None
    pa = s.open[ja] or s.close[ja]
    pb = s.open[jb] or s.close[jb]
    if not pa or not pb:
        return None
    return (pb / pa - 1) * 100


def past_ret(panel, code, di, w):
    """di 전날까지의 w일 수익률. 전날까지만 보므로 미래 정보가 없다."""
    s = panel.get(code)
    if s is None:
        return None
    j, j0 = s.pos.get(di - 1), s.pos.get(di - 1 - w)
    if j is None or j0 is None:
        return None
    if not s.close[j] or not s.close[j0]:
        return None
    return (s.close[j] / s.close[j0] - 1) * 100


def score_of(panel, code, di, signal):
    """signal 이 'low_vol' 이면 변동성 점수, 숫자면 그 기간 과거수익."""
    if signal == "low_vol":
        return S.factor_score(panel, code, di, "low_vol")
    return past_ret(panel, code, di, signal)


def annualize(per_round_net, hold):
    """회차 순수익(%)을 연환산. 수수료를 뺀 값을 넣어야 한다."""
    return ((1 + per_round_net / 100) ** (DAYS_PER_YEAR / hold) - 1) * 100


def break_even_hold(edge_per_day, fee=FEE):
    """하루당 엣지와 거래당 수수료로 손익분기 보유기간을 낸다.

    엣지는 시간에 비례해 쌓이고 수수료는 거래마다 고정이므로
    edge_per_day * H = fee 가 되는 H 가 손익분기다.
    """
    if edge_per_day <= 0:
        return float("inf")
    return fee / edge_per_day


def sweep(dates, panel, hold, signal, side, base):
    """겹치지 않는 회차로 훑는다. (뽑은것 수익, 풀 전체 수익)"""
    picks_r, pool_r = [], []
    n = len(dates)
    di = base
    while di + hold < n:
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := score_of(panel, c, di, signal)) is not None]
        if len(sc) < PICK * 2:
            di += hold
            continue
        sc.sort(reverse=True)
        sel = [c for _s, c in (sc[:PICK] if side == "high" else sc[-PICK:])]
        rs = [r for c in sel
              if (r := trade_ret(panel, c, di, di + hold)) is not None]
        alls = [r for _s, c in sc
                if (r := trade_ret(panel, c, di, di + hold)) is not None]
        if len(rs) >= PICK // 2 and alls:
            picks_r.append(st.mean(rs))
            pool_r.append(st.mean(alls))
        di += hold
    return picks_r, pool_r


def perm_test(dates, panel, hold, signal, side, base, rng):
    """회차 안에서 신호값만 섞는 대조군.

    '그날 시장이 좋았나' 가 상쇄되고 '이 신호로 고르는 것의 값' 만 남는다.
    """
    real, perms = [], [[] for _ in range(N_PERM)]
    n = len(dates)
    di = base
    while di + hold < n:
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = []
        for c in cand:
            x = score_of(panel, c, di, signal)
            r = trade_ret(panel, c, di, di + hold)
            if x is not None and r is not None:
                sc.append((x, r))
        if len(sc) < PICK * 2:
            di += hold
            continue
        xs = np.array([a for a, _b in sc])
        rs = np.array([b for _a, b in sc])
        order = np.argsort(-xs) if side == "high" else np.argsort(xs)
        real.append(rs[order[:PICK]].mean() - rs.mean())
        for p in range(N_PERM):
            idx = rng.permutation(len(rs))
            perms[p].append(rs[idx[:PICK]].mean() - rs.mean())
        di += hold
    if not real:
        return 0.0, 1.0, 0
    r_mean = st.mean(real)
    p_means = [st.mean(p) for p in perms]
    beat = sum(1 for v in p_means if v >= r_mean) / len(p_means)
    return r_mean, beat, len(real)


def main():
    dates, panel = S.load_panel()
    base = max(140, S.LIQUIDITY_DAYS + 2)
    rng = np.random.default_rng(SEED)

    print(f"왕복 수수료 {FEE}%. 회당 총수익이 이걸 넘어야 본전.")
    print(f"  {'보유':>5} {'연 거래횟수':>10} {'연 수수료':>10}")
    for h in HOLDS:
        print(f"  {h:>4}일 {DAYS_PER_YEAR/h:>10.0f}회 "
              f"{DAYS_PER_YEAR/h*FEE:>9.1f}%")

    SIGNALS = (("low_vol", "high", "저변동"),
               (5, "low", "5일 반전(떨어진것)"),
               (5, "high", "5일 모멘텀(오른것)"),
               (1, "low", "1일 반전"),
               (20, "low", "20일 반전"))

    print("\n" + "=" * 98)
    print("=== 1) 보유기간별: 회당 총수익이 수수료를 넘나 ===")
    print("=== '풀 대비' 는 유니버스 전체를 산 것과의 차이 (시장 등락 상쇄) ===")
    print("=" * 98)
    print(f"  {'신호':<18} {'보유':>5} {'회차':>6} {'회당총수익':>11} "
          f"{'수수료뺀':>10} {'풀대비':>9} {'연환산(순)':>11} {'판정':>9}")
    lowvol = []
    for signal, side, label in SIGNALS:
        for hold in HOLDS:
            pr, pl = sweep(dates, panel, hold, signal, side, base)
            if len(pr) < 30:
                continue
            gross = st.mean(pr)
            net = gross - FEE
            edge = st.mean([a - b for a, b in zip(pr, pl)])
            print(f"  {label:<18} {hold:>4}일 {len(pr):>6} {gross:>+10.3f}% "
                  f"{net:>+9.3f}% {edge:>+8.3f}% {annualize(net, hold):>+10.1f}% "
                  f"{'본전 넘음' if net > 0 else '손해':>9}")
            if signal == "low_vol":
                lowvol.append((hold, edge))
        print()

    # ------------------------------------------- 2) 구조
    print("=" * 98)
    print("=== 2) 왜 짧으면 불리한가 - 엣지는 쌓이고 수수료는 거래마다 고정 ===")
    print("=" * 98)
    print(f"  {'보유':>5} {'풀대비 엣지':>12} {'하루당 엣지':>12} "
          f"{'수수료':>8} {'엣지/수수료':>11} {'순엣지':>10}")
    for hold, edge in lowvol:
        print(f"  {hold:>4}일 {edge:>+11.3f}% {edge/hold:>+11.3f}% "
              f"{FEE:>7.2f}% {edge/FEE:>10.2f}x {edge-FEE:>+9.3f}%")
    perday = [e / h for h, e in lowvol]
    avg = st.mean(perday)
    be = break_even_hold(avg)
    print(f"\n  하루당 엣지가 {min(perday):.3f}~{max(perday):.3f}% 로 "
          f"거의 일정하다 (평균 {avg:.3f}%).")
    print(f"  엣지 = 하루당 {avg:.3f}% x 보유일수. 수수료 = 거래당 "
          f"{FEE}% 고정.")
    print(f"  => 손익분기 보유기간 = {FEE}/{avg:.3f} = **{be:.1f}일**")
    print("  => 길수록 엣지/수수료가 계속 좋아진다. 짧게 굴릴 이유가 없다.")
    print(f"\n  수수료가 절반({FEE/2}%)이어도 손익분기는 "
          f"{break_even_hold(avg, FEE/2):.1f}일로 내려갈 뿐,")
    print("  20일이 1일보다 나은 것은 그대로다.")

    # ------------------------------------------- 3) 대조군
    print("\n" + "=" * 98)
    print("=== 3) 짧은 쪽 엣지가 진짜인가 - 회차 안에서 신호를 섞는 대조군 ===")
    print("=" * 98)
    print(f"  {'신호':<14} {'보유':>5} {'회차':>6} {'실제 엣지':>11} "
          f"{'통과율':>9} {'판정':>12}")
    for signal, side, label, hold in (("low_vol", "high", "저변동", 3),
                                      ("low_vol", "high", "저변동", 5),
                                      ("low_vol", "high", "저변동", 20),
                                      (20, "low", "20일 반전", 5)):
        rm, beat, n = perm_test(dates, panel, hold, signal, side, base, rng)
        print(f"  {label:<14} {hold:>4}일 {n:>6} {rm:>+10.3f}% "
              f"{beat*100:>8.1f}% "
              f"{'눈여겨볼 값' if beat < 0.05 else '구별 안 됨':>12}")
    print("\n  저변동 엣지는 3일/5일에서도 대조군을 통과한다.")
    print("  신호가 짧은 쪽에서 죽는 게 아니라, 크기가 수수료를 못 넘는다.")
    print("  (신호 5개 x 보유 6개 = 30가지를 훑었으므로 5% 기준이면")
    print("   30개 중 1.5개는 우연히 통과한다. 경계선 값은 믿지 말 것)")

    print("\n" + "=" * 98)
    print("=== 결론 ===")
    print("=" * 98)
    print("  짧게 거래하는 형태는 안 된다. 신호가 없어서가 아니라")
    print(f"  수수료 때문이다. 손익분기 {be:.1f}일, 길수록 계속 유리하다.")
    print("  단기 반전과 모멘텀은 이 유니버스에서 작동하지 않는다.")
    print("  특히 모멘텀(최근 오른 것 사기)은 크게 마이너스다.")
    print("\n  그리고 이 표는 짧은 쪽에 유리하게 기울어 있다 - 호가")
    print("  스프레드와 체결 미끄러짐을 안 넣었다. 실제로는 더 불리하다.")


if __name__ == "__main__":
    main()
