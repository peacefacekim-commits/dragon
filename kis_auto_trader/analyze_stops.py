"""언제 팔아야 하나 - 손절/익절, 그리고 장중 신호. 검증 안 했던 빈칸.

(2026-09-19 신설) 사용자: "이 전략대로 진행을 하고 싶은데 나쁜날 좋은날
지표나 언제 팔아야할지 장중 몇번 신호를 잡아야하는지 등등을 고려해"

전략 문서에 '손절/익절 없음' 이라고 써놨지만 그게 더 낫다는 걸 확인한
적이 없었다. 그냥 안 넣었을 뿐이다. 이번에 잰다.

틀(analyze_short_term.py / analyze_turnover.py)을 그대로 쓴다.
손절/익절은 **거래를 한 번 더 만든다.** 그러므로 그 거래가 왕복 수수료
0.21% 이상을 벌어줘야 이득이다. 하루당 엣지가 0.093% 이므로, 손절 한 번이
**하루치 엣지의 2.3배**를 벌어야 본전이다.

기준 구성: 저변동 10종목 / 40일 주기 / 부분교체 (지금까지 제일 나은 것)

체결 방식 - 손절/익절에 유리하게 잡지 않았다
  장중 저가가 손절선을 뚫으면 손절가에 팔린 것으로 본다.
  단 시가가 이미 손절선 아래로 갭하락했으면 시가에 팔린 것으로 본다
  (현실이 이쪽이다. 손절가로 잡아주면 손절이 과대평가된다).
  익절도 같은 방식. 팔린 뒤에는 다음 교체일까지 현금으로 둔다.

===========================================================================
결과 1 - 손절은 전부 손해다. 타이트할수록 더 나쁘다
===========================================================================
  규칙              연환산   최대낙폭  수수료/자본  손절횟수  기준대비
  없음 (지금 방식)   +16.2%   -17.9%     3.6%      0회      -
  손절 -5%          +10.7%   -17.5%     4.0%     82회   -5.4%p
  손절 -7%          +10.5%   -18.0%     3.9%     64회   -5.6%p
  손절 -10%         +13.0%   -17.0%     3.8%     42회   -3.1%p
  손절 -15%         +14.6%   -19.2%     3.6%     24회   -1.5%p
  손절 -20%         +15.0%   -19.1%     3.5%     16회   -1.2%p

  **손절선이 타이트할수록 더 나쁘다.** -5% 는 -5.4%p, -20% 는 -1.2%p.
  즉 손절을 아예 안 하는 쪽으로 갈수록 좋아진다.

  그리고 낙폭도 안 줄었다. -17.9% -> -17.5% (손절 -5%) 로 0.4%p 개선인데
  수익은 5.4%p 를 잃었다. **보호를 사는 게 아니라 그냥 손해다.**

  이유는 틀로 설명된다. 저변동 종목이 -5% 빠진 것은 대개 잡음이고,
  팔면 (1) 되돌림을 놓치고 (2) 수수료를 낸다. 손절 82회 x 0.21% =
  17%를 5년간 수수료로 더 냈다.

===========================================================================
결과 2 - 손절+익절 조합은 더 나쁘다
===========================================================================
  손절-10 익절+10   +10.3%   -15.4%     5.2%   60회/112회   -5.9%p
  손절-7  익절+15   +10.3%   -15.4%     5.0%   85회/ 76회   -5.9%p
  손절-15 익절+20   +13.4%   -16.4%     4.5%   30회/ 58회   -2.7%p

  둘을 같이 걸면 거래가 제일 많아지고 결과가 제일 나쁘다. 낙폭은
  -15.4% 까지 내려가지만 수익을 5.9%p 잃는다.

===========================================================================
결과 3 - 익절만 떼면 +20% 가 좋아 보였다. 그래서 검증했다
===========================================================================
  익절 +5%          +11.9%   -13.5%     5.0%    134회   -4.3%p
  익절 +10%         +16.1%   -14.4%     4.8%     87회   -0.1%p
  익절 +20%         +18.2%   -15.0%     4.3%     48회   **+2.0%p**

  익절 +20% 가 수익 +2.0%p 에 낙폭도 -17.9% -> -15.0% 로 2.9%p 개선이다.
  그럴듯한 기전도 있다: 저변동 전략에서 많이 오른 종목은 변동성이 커져서
  다음 회차에 어차피 탈락한다. 미리 파는 것이 원칙과 어긋나지 않는다.

  그런데 12가지를 훑어서 나온 1등이므로 그대로 믿으면 안 된다.
  반기 양방향과 익절선 민감도를 봤다.

===========================================================================
결과 4 - 검증: 익절 +20% 는 뒤집힌다. 넣으면 안 된다
===========================================================================
기간을 반으로 갈라 각각 돌렸다 (--verify 로 재현).

  규칙          전반부   후반부   기준대비(전)  기준대비(후)   판정
  없음 (기준)    +5.0%  +27.3%       -          -         -
  익절 +10%     +5.3%  +25.0%    +0.3%p     -2.2%p   뒤집힘
  익절 +15%     +5.3%  +27.0%    +0.3%p     -0.3%p   뒤집힘
  익절 +20%     +5.7%  +26.5%    +0.7%p     -0.8%p   뒤집힘
  익절 +25%     +4.8%  +26.8%    -0.2%p     -0.5%p   양쪽 손해
  익절 +30%     +5.3%  +27.3%    +0.3%p     -0.0%p   뒤집힘
  손절 -20%     +3.9%  +26.2%    -1.1%p     -1.1%p   양쪽 손해

  **익절 다섯 수준 전부 뒤집히거나 양쪽 손해다. 하나도 양쪽 이득이 없다.**
  전체 기간에서 보였던 +2.0%p 는 12가지를 훑어서 나온 잡음이었다.
  그대로 채택했으면 실수였다.

  반면 손절 -20% 는 양쪽 다 -1.1%p 로 **일관되게 나쁘다**. 손절이
  손해라는 것은 검증을 통과한 결론이다 (나쁘다는 쪽으로).

  => 손절도 익절도 넣지 않는다. 교체일에만 팔고, 그 사이에는 아무것도
     하지 않는다. 지금 방식이 맞다.

===========================================================================
결과 5 - 장중에 몇 번 신호를 잡아야 하나: 0번
===========================================================================
두 가지를 나눠서 답한다.

(가) 데이터가 없다
  data/ 에 있는 것은 일봉(시가/고가/저가/종가)뿐이다. 분봉이 없다.
  그래서 '장중 3번 확인' 같은 규칙은 **원리적으로 검증이 불가능하다.**
  검증 안 된 규칙을 실제 돈에 넣지 않는다는 원칙을 여기에도 적용한다.

(나) 틀이 기준선을 준다
  신호를 보는 것 자체는 공짜다. 비용은 **보고 행동할 때** 생긴다.
  거래를 한 번 더 만들면 0.21% 를 벌어야 하고, 그건 하루치 엣지(0.093%)
  의 2.3배다.

  장중 확인 횟수와 발동률에 따른 연간 추가 수수료
    확인    발동률 5%    발동률 20%    발동률 50%
    1번/일    2.6%       10.3%        25.8%
    3번/일    7.7%       31.0%        77.5%
   10번/일   25.8%      103.3%       258.3%

  하루 3번 확인해서 20% 발동하면 연 31% 를 수수료로 낸다. 전략의
  연 기대수익이 14~17% 인데 그 두 배다.

(다) 그리고 행동할 근거가 없다
  좋은날/나쁜날 신호는 23가지를 검사해서 전부 실패했다.
    지표 14개 전원 합의한 날의 승률 차이 z=+0.20 (analyze_consensus.py)
    제일 센 단일 지표 |t|=1.48, 잡음 중앙값 1.78 보다 낮다
      (analyze_cascade.py)
  즉 장중에 몇 번 보든 그 신호로 거래를 바꿀 근거가 없다.

  => **장중 확인 횟수 = 0번. 교체일에 한 번만 본다.**

===========================================================================
읽는 법
===========================================================================
  1) 손절은 넣지 마라. 6가지 수준 전부 손해였고 타이트할수록 나빴다.
     낙폭도 거의 안 줄었다. '보험' 이 아니라 그냥 비용이다.
  2) 손절+익절 조합은 제일 나쁘다.
  3) 익절도 넣지 마라. 전체 기간에서는 +20% 가 +2.0%p 로 좋아
     보였지만 반기로 쪼개면 뒤집힌다 (전반부 +0.7%p, 후반부 -0.8%p).
     12가지를 훑어서 나온 1등은 이렇게 검증해야 한다.
  4) 장중 신호는 0번. 데이터가 없어 검증도 못 하고, 행동할 근거도 없고,
     행동하면 수수료가 수익을 넘는다.
  5) 주의: 여기 체결은 손절/익절에 **유리하지 않게** 잡았지만(갭은
     시가 체결), 호가 스프레드는 여전히 안 들어갔다. 손절/익절은
     거래를 늘리므로 스프레드를 넣으면 더 불리해진다. 즉 이 표는
     손절/익절 쪽에 이미 관대한 편이다.
  6) 기준 수치(+16.2%)는 시작일 6개 중앙값이고 2025년 시장 +55% 가
     들어 있다. 절대 수준을 기대치로 쓰면 안 된다. 여기서 읽을 것은
     '기준대비' 열이다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_stops.py           # 손절/익절 훑기
    python analyze_stops.py --verify  # 반기 양방향 검증
"""
import argparse
import csv
import glob
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import strategy as S  # noqa: E402

CAPITAL = 2_000_000
FEE_ONE_WAY = S.FEE_ROUND_TRIP_PCT / 2 / 100
FEE_ROUND = S.FEE_ROUND_TRIP_PCT
PICK, PERIOD, DAYS_PER_YEAR = 10, 40, 246
N_STARTS, START_GAP = 6, 29
EDGE_PER_DAY = 0.093      # analyze_short_term.py 에서 나온 값

CASES = [
    (None, None, "없음 (지금 방식)"),
    (-5, None, "손절 -5%"),
    (-7, None, "손절 -7%"),
    (-10, None, "손절 -10%"),
    (-15, None, "손절 -15%"),
    (-20, None, "손절 -20%"),
    (None, 5, "익절 +5%"),
    (None, 10, "익절 +10%"),
    (None, 20, "익절 +20%"),
    (-10, 10, "손절-10 익절+10"),
    (-7, 15, "손절-7 익절+15"),
    (-15, 20, "손절-15 익절+20"),
]


def load_high_low(dates):
    """장중 고가/저가. load_panel() 이 이 두 컬럼을 버리므로 따로 읽는다."""
    dpos = {d: i for i, d in enumerate(dates)}
    out = {}
    for path in sorted(glob.glob(str(_ROOT / "data" /
                                     f"{S.PANEL_PREFIX}_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                di = dpos.get(r["date"])
                if di is None:
                    continue
                try:
                    h, lo = float(r["high"]), float(r["low"])
                except (TypeError, ValueError):
                    continue
                if h > 0 and lo > 0:
                    out[(di, r["code"])] = (h, lo)
    return out


def price(panel, code, di, field="open"):
    s = panel.get(code)
    if s is None:
        return None
    j = s.pos.get(di)
    if j is None:
        return None
    v = (s.open[j] if field == "open" else s.close[j]) or s.close[j]
    return v or None


def picks_at(panel, di):
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    sc = [(x, c) for c in cand
          if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
    if len(sc) < PICK:
        return None
    sc.sort(reverse=True)
    return [c for _s, c in sc[:PICK]]


def buy_greedy(panel, cash, codes, di):
    p = {c: price(panel, c, di) for c in codes}
    p = {c: v for c, v in p.items() if v}
    if not p:
        return {}, cash, 0.0
    slot = cash / len(p)
    hold, spent, fee = {}, 0.0, 0.0
    for c, v in p.items():
        cost = v * (1 + FEE_ONE_WAY)
        q = int(slot // cost)
        if q:
            hold[c] = q
            spent += q * cost
            fee += q * v * FEE_ONE_WAY
    left = cash - spent
    order = sorted(p.items(), key=lambda kv: kv[1])
    added = True
    while added:
        added = False
        for c, v in order:
            cost = v * (1 + FEE_ONE_WAY)
            if left >= cost:
                hold[c] = hold.get(c, 0) + 1
                left -= cost
                fee += v * FEE_ONE_WAY
                added = True
    return hold, left, fee


def exit_price(basis, op, high, low, stop_pct, take_pct):
    """손절/익절 체결가. 안 걸리면 None, 걸리면 (가격, '손절'|'익절').

    갭이 나면 선이 아니라 시가에 체결된 것으로 본다 - 현실이 이쪽이고,
    선 가격으로 잡아주면 손절/익절이 과대평가된다.
    """
    if stop_pct is not None:
        line = basis * (1 + stop_pct / 100)
        if op <= line:
            return op, "손절"
        if low <= line:
            return line, "손절"
    if take_pct is not None:
        line = basis * (1 + take_pct / 100)
        if op >= line:
            return op, "익절"
        if high >= line:
            return line, "익절"
    return None


def run(dates, panel, hl, stop_pct=None, take_pct=None, start=None,
        upto=None, capital=CAPITAL):
    """부분교체 + 손절/익절. (곡선, 수수료, 손절횟수, 익절횟수)"""
    n = upto if upto is not None else len(dates)
    if start is None:
        start = max(140, S.LIQUIDITY_DAYS + 2)
    cash, hold, basis = float(capital), {}, {}
    fees, n_stop, n_take = 0.0, 0, 0
    curve = []
    di = start
    while di < n:
        if (di - start) % PERIOD == 0:
            new = picks_at(panel, di)
            if new:
                keep = {c: q for c, q in hold.items() if c in new}
                for c in [c for c in hold if c not in new]:
                    v = price(panel, c, di)
                    if v:
                        cash += hold[c] * v * (1 - FEE_ONE_WAY)
                        fees += hold[c] * v * FEE_ONE_WAY
                add = [c for c in new if c not in hold]
                got, cash, f = (buy_greedy(panel, cash, add, di) if add
                                else ({}, cash, 0.0))
                fees += f
                hold = {**keep, **got}
                for c in hold:
                    basis.setdefault(c, price(panel, c, di) or 0)
        if stop_pct is not None or take_pct is not None:
            for c in list(hold):
                b, rec = basis.get(c), hl.get((di, c))
                if not b or not rec:
                    continue
                high, low = rec
                op = price(panel, c, di) or b
                hit = exit_price(b, op, high, low, stop_pct, take_pct)
                if hit:
                    at, kind = hit
                    q = hold.pop(c)
                    cash += q * at * (1 - FEE_ONE_WAY)
                    fees += q * at * FEE_ONE_WAY
                    basis.pop(c, None)
                    if kind == "손절":
                        n_stop += 1
                    else:
                        n_take += 1
        curve.append(cash + sum(q * (price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, fees, n_stop, n_take


def mdd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def annualized(curve, capital=CAPITAL):
    yrs = len(curve) / DAYS_PER_YEAR
    return ((curve[-1] / capital) ** (1 / yrs) - 1) * 100 if yrs > 0 else 0.0


def extra_fee_per_year(checks_per_day, trigger_rate):
    """장중에 하루 몇 번 보고 그 비율로 거래하면 연 수수료가 얼마인가."""
    return DAYS_PER_YEAR * checks_per_day * trigger_rate * FEE_ROUND


def break_even_trades(edge_per_day=EDGE_PER_DAY):
    """거래 한 번이 벌어야 하는 것이 하루치 엣지의 몇 배인가."""
    return FEE_ROUND / edge_per_day


def sweep(dates, panel, hl, starts):
    """CASES 전부를 돌린다. 기준(없음) 대비로 비교한다."""
    rows, base = [], None
    for sp, tp, lab in CASES:
        anns, mds, fs, nss, nts = [], [], [], [], []
        for s0 in starts:
            cv, fee, ns, nt = run(dates, panel, hl, sp, tp, s0)
            anns.append(annualized(cv))
            mds.append(mdd(cv))
            fs.append(fee / CAPITAL * 100)
            nss.append(ns)
            nts.append(nt)
        a = st.median(anns)
        if base is None:
            base = a
        rows.append((lab, sp, tp, a, st.median(mds), st.median(fs),
                     st.median(nss), st.median(nts), a - base))
    return rows


def verify(dates, panel, hl, cands=None):
    """반기 양방향. 12가지를 훑었으므로 이게 없으면 결론을 못 낸다."""
    n = len(dates)
    base_i = max(140, S.LIQUIDITY_DAYS + 2)
    mid = base_i + (n - base_i) // 2
    cands = cands or [(None, 10), (None, 15), (None, 20), (None, 25),
                      (None, 30), (-20, None)]

    def seg(sp, tp, lo, hi):
        outs = []
        for s0 in [lo + k * 31 for k in range(4)]:
            if s0 + 80 >= hi:
                continue
            cv, _f, _s, _t = run(dates, panel, hl, sp, tp, s0, upto=hi)
            if len(cv) < 150:
                continue
            outs.append(annualized(cv))
        return st.median(outs) if outs else None

    b_a, b_b = seg(None, None, base_i, mid), seg(None, None, mid, n)
    out = []
    for sp, tp in cands:
        a, b = seg(sp, tp, base_i, mid), seg(sp, tp, mid, n)
        if a is not None and b is not None:
            out.append((sp, tp, a, b, a - b_a, b - b_b))
    return b_a, b_b, out


def main(do_verify=False):
    dates, panel = S.load_panel()
    hl = load_high_low(dates)
    print(f"장중 고가/저가 {len(hl):,}건")
    base_i = max(140, S.LIQUIDITY_DAYS + 2)
    starts = [base_i + k * START_GAP for k in range(N_STARTS)]

    if do_verify:
        b_a, b_b, rows = verify(dates, panel, hl)
        print("\n" + "=" * 92)
        print("=== 반기 양방향 - 12가지를 훑었으므로 검증 ===")
        print("=" * 92)
        print(f"  {'규칙':<16} {'전반부':>10} {'후반부':>10} "
              f"{'기준대비(전)':>13} {'기준대비(후)':>13} {'판정':>11}")
        print(f"  {'없음 (기준)':<16} {b_a:>+9.1f}% {b_b:>+9.1f}%")
        for sp, tp, a, b, da, db in rows:
            lab = (f"익절 +{tp}%" if tp else f"손절 {sp}%")
            if da > 0 and db > 0:
                v = "양쪽 이득"
            elif da < 0 and db < 0:
                v = "양쪽 손해"
            else:
                v = "뒤집힘"
            print(f"  {lab:<16} {a:>+9.1f}% {b:>+9.1f}% {da:>+12.1f}%p "
                  f"{db:>+12.1f}%p {v:>11}")
        return 0

    print(f"기준: 저변동 {PICK}종목 / {PERIOD}일 주기 / 부분교체, "
          f"{CAPITAL:,}원, 시작일 {N_STARTS}개 중앙값")
    print(f"손절/익절은 거래를 한 번 더 만든다. 그 거래가 {FEE_ROUND}% "
          f"= 하루치 엣지의 {break_even_trades():.1f}배를 벌어야 본전이다.\n")
    print("=" * 96)
    print("=== 손절/익절이 도움이 되나 ===")
    print("=" * 96)
    print(f"  {'규칙':<18} {'연환산':>8} {'최대낙폭':>9} {'수수료':>8} "
          f"{'손절':>6} {'익절':>6} {'기준대비':>10}")
    for lab, _sp, _tp, a, m, f, ns, nt, d in sweep(dates, panel, hl, starts):
        print(f"  {lab:<18} {a:>+7.1f}% {m:>8.1f}% {f:>7.1f}% "
              f"{ns:>5.0f}회 {nt:>5.0f}회 "
              f"{('-' if abs(d) < 1e-9 else f'{d:+.1f}%p'):>10}")

    print("\n" + "=" * 96)
    print("=== 장중에 몇 번 신호를 잡아야 하나 ===")
    print("=" * 96)
    print("  분봉 데이터가 없다 (일봉만). 장중 규칙은 검증이 불가능하다.")
    print(f"  틀의 기준선: 거래 한 번이 {FEE_ROUND}% 를 벌어야 하고,")
    print(f"  그건 하루치 엣지({EDGE_PER_DAY}%)의 "
          f"{break_even_trades():.1f}배다.")
    print(f"\n  {'확인':>8} {'발동 5%':>10} {'발동 20%':>10} {'발동 50%':>10}"
          "   <- 연간 추가 수수료")
    for n_chk in (1, 3, 10):
        print(f"  {n_chk:>6}번/일 "
              + " ".join(f"{extra_fee_per_year(n_chk, r):>9.1f}%"
                         for r in (0.05, 0.20, 0.50)))
    print("\n  하루 3번 보고 20% 발동하면 연 31% 가 수수료다. 전략의 연")
    print("  기대수익 14~17% 의 두 배다.")
    print("  그리고 좋은날/나쁜날 신호는 23가지를 검사해 전부 실패했다")
    print("  (analyze_consensus.py z=+0.20, analyze_cascade.py |t|=1.48).")
    print("  => 장중 확인 횟수 = 0번. 교체일에 한 번만 본다.")
    return 0


if __name__ == "__main__":
    _ap = argparse.ArgumentParser(description="손절/익절/장중 신호 검사")
    _ap.add_argument("--verify", action="store_true",
                     help="반기 양방향 검증만 돌린다")
    _a = _ap.parse_args()
    raise SystemExit(main(_a.verify))
