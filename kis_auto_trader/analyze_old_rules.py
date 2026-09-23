"""옛 선정 규칙 둘을 5.7년으로 재현해서 잰다. (기준만 먼저 - 결과 미기입)

(2026-09-22 신설) 사용자: "왜 골랐는지는 데드 크로스 골드 크로스 얘기하면서
정했던 거 같은데"

이 말이 대책의 E 항목을 뒤집었다. 어제까지 "선정 기준이 기록에 없어서
표본을 더 만들 수 없다" 고 적었는데, 찾아보니 **기록이 있다.**

===========================================================================
0 - 먼저 바로잡을 것: 그 88건은 골든크로스가 아니었다
===========================================================================
기록을 찾아보니 이렇다.

  README.md:71     "전략: 5일선/20일선 골든크로스 매수, 데드크로스 매도"
  common.py:49     entry_mode: "ma_cross" | "dip_buy" | "news_buy"
  config.yaml:18   entry_mode: dip_buy        <- 지금 값
  DECISIONS.md     8/19 이전  dip (하락폭 기준)
                   8/21 전후  volatility (일중 변동폭)
                   8/26 이후  dip 으로 복귀

즉 **그 88건(7/29~9/4)의 선정은 골든크로스가 아니라 dip(하락폭)** 이었다.
골든크로스는 README 의 초기 설명이고, `ma_cross` 는 코드에 이름만 남아
있다 (계산 분기는 strategy.py 를 새로 쓸 때 사라졌다).

그래도 **둘 다 정의가 명확해서 재현할 수 있다.** 그게 중요한 점이다.
33건이 아니라 5.7년 일봉으로 잴 수 있다.

===========================================================================
1 - 무엇을 재는가. 둘뿐이다
===========================================================================
  dip         최근 20일 고점 대비 -10% 이상 하락하고, 그 저점 대비 +3%
              이상 반등한 종목. config.yaml 의 실제 값을 그대로 쓴다
              (dip_buy_pct -10.0 / dip_lookback_days 20 /
               rebound_confirm_pct 3.0). 거래량 조건은 지금 꺼져 있으므로
              (volume_multiplier 0) 넣지 않는다.

  golden      5일선이 20일선 위에 있는 종목. README 의 5/20 을 쓴다.
              '교차한 그 날' 이 아니라 '위에 있는 상태' 로 잰다 - 교차일만
              사면 표본이 너무 적고, 실제로도 그 상태를 유지하는 동안
              들고 있었다.

늘리지 않는다. 방향도 고정이다 (dip 은 많이 떨어진 순, golden 은 이격이
큰 순). 양방향을 보면 가짓수가 두 배가 된다.

===========================================================================
2 - 이게 기존에 잰 것과 다른가 (먼저 확인한다)
===========================================================================
비슷한 것을 이미 쟀다. 겹치면 새로 재는 게 아니다.

  reversal   -(20일 전 대비 수익률). dip 과 방향이 같지만 **반등 확인이
             없다.** dip 은 떨어진 뒤 되돌아서기 시작한 것만 고른다.
  trend      120일선 대비 이격. golden 과 방향이 같지만 **기간이 6배**다.
             analyze_styles 에서 연 -30.9% 로 탈락했다.

그래서 1단계로 저변동/추세/반전과의 순위상관을 먼저 본다.
|상관| >= 0.70 이면 재포장으로 보고 성과를 재지 않는다
(analyze_selectors.py 와 같은 문턱).

===========================================================================
3 - 채택 조건 넷 (전제.md 의 규약대로)
===========================================================================
  1) 시작일 5개 중 4개 이상에서 기준선(저변동)을 이긴다
  2) 반띵 양방향 모두에서 이긴다
  3) 무작위 대조군 500회를 넘는다 (p < 0.05)
  4) 연도별 지속성 - 양수인 해가 과반이고, 최고 해를 빼도 평균이 양수다

하나라도 걸리면 넣지 않는다. 결과를 보고 조건을 고치지 않는다.

미리 정해두는 처리
  값이 없는 날   그 종목은 그 회차에서 제외. 앞 값을 끌어오지 않는다.
  미래 정보      di - 1 종가까지만 본다.
  조건을 만족하는 종목이 PICK 보다 적은 날은 그 회차를 건너뛴다.
                 (dip 은 조건부 신호라서 이런 날이 생긴다. 억지로 채우면
                  '조건에 안 맞는 종목' 을 사게 되어 규칙이 달라진다.)

===========================================================================
결과 - 둘 다 탈락. 하나는 1단계에서, 하나는 2단계 첫 조건에서
===========================================================================
1단계 (문턱 |상관| >= 0.70)

  신호       low_vol     trend  reversal   판정
  dip         -0.356    +0.028    +0.165   새 정보
  golden      -0.497    +0.588    -0.750   재포장

golden 은 reversal 과 -0.750 이다. reversal 은 -(20일 수익률)이니
**golden 은 20일 모멘텀과 +0.750** 이라는 뜻이다. trend(120일 이격)와도
+0.588 이다. 성과를 재지 않는다 - 규약대로다.

여기서 그냥 '모른다' 로 끝나지 않는 이유: golden 이 겹친 상대가
**이미 재서 진 팩터**다. analyze_styles.py 에서 추세 120일이 연 -30.9%,
낙폭 -88.3% 였다. golden 은 그 짧은 기간 판이다. '안 재봤다' 가 아니라
'가장 가까운 친척이 크게 졌다' 다.

2단계 (기준 저변동 120일 = 연 +22.3%)

  신호       연수익%   낙폭%   시작일
  dip         -29.6   -85.0     0/5

조건 1(시작일 4/5)에서 0/5 다. 조건 2~4 는 돌리지 않았다. 여기서 끝이고
조건을 고치지 않는다. 기준선과의 차이는 **51.9%p** 다.

===========================================================================
왜 졌나 - dip 은 사실 '고변동 고르기' 였다
===========================================================================
dip 이 고른 10종목이 유니버스 200종목 안에서 어디쯤 있나 봤다
(변동성 백분위. 0 = 가장 많이 흔들리는 종목, 100 = 가장 안 흔들리는 종목).

  dip     27 12 14 13 11 18 32 11 24 18   중앙 **16**
  golden  21 25 16 19 12 22  8 16  9 23   중앙 **17**

dip 은 가장 흔들리는 16% 안에서 고른다. 10회 전부 33 미만이다.
golden 도 17 이다. **옛 규칙 둘 다 사실은 고변동 고르기였다.**
(golden 의 성과는 1단계에서 걸렸으므로 재지 않았다. 여기 백분위는
성과가 아니라 '무엇을 고르는 체인가' 다.)

그러면 -29.6% 가 설명된다. analyze_styles.py 의 고변동 120일이 -41.5%,
추세 120일이 -30.9% 였다. dip 의 -29.6% 는 그 사이다. 새 정보이긴 했지만
(1단계 통과) **새로운 방향은 아니었다.** 많이 떨어진 종목을 고르면
대개 많이 흔들리는 종목을 고르게 된다.

반등 확인(+3%)이 reversal 과의 차이라고 적었고 실제로 상관은 +0.165로
낮았다. 그런데 **낮은 상관이 좋은 성과를 뜻하지 않는다.** 다르게 골라도
같은 종류의 종목을 집었다.

조건을 만족하는 종목은 교체일마다 중앙 dip 42개 / golden 122개 (200개 중)
= **21% / 61%** 였다. 10개 미만인 날은 둘 다 10회 중 0회다. 즉 '드물게
오는 기회' 가 아니라 상시 5분의 1(또는 5분의 3)을 고르는 체다.
문턱을 넘는 게 흔하면 문턱이 고르는 일을 거의 안 한다.

===========================================================================
이게 실거래 5주에 대해 말해주는 것과 말해주지 않는 것
===========================================================================
말해주는 것
  그 5주에 쓴 선정 규칙(dip)은 5.7년 일봉에서 연 -29.6% 다. 같은 기간
  저변동은 +22.3% 다. -108,551원이 운이 나빴던 것이라고 보기 어렵다.
  analyze_real_trades.py 에서 편향 없는 33건의 수수료 전 수익률이
  -0.023% 로 '엣지가 0' 이었던 것과 방향이 맞는다.

말해주지 않는 것
  - 일봉으로 쟀다. 실거래는 10분 체결이었다. 같은 규칙이라도 같은 것이
    아니다.
  - 88건이 한 규칙이 아니다. dip 75건 / volatility 13건이다
    (8/21 전후에 바꿨다가 8/26 에 되돌렸다).
  - 그러므로 "그 5주의 손실이 dip 탓이다" 까지는 말하지 못한다.
    말할 수 있는 것은 "dip 은 오래 돌려도 지는 규칙이다" 다.

===========================================================================
남는 것
===========================================================================
옛 규칙 둘 다 쓸 이유가 없다. 검증된 선정은 여전히 저변동 하나뿐이다
(analyze_styles.py 6/6 해 양수, +22.3%).

대책의 D(저변동 선정 + 당일 청산)는 그대로 남는다. 이번 결과는 D 의
'선정을 저변동으로 바꿔서 잰다' 를 더 뒷받침한다 - 실거래가 쓰던 선정이
직접 재보니 -29.6% 였으므로.

실행:
  python analyze_old_rules.py         # 1단계 (기존 신호와 겹치나)
  python analyze_old_rules.py --run   # 2단계까지
  python analyze_old_rules.py --why   # 고른 종목이 얼마나 흔들리나
"""
import argparse
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import analyze_fundamentals as F  # noqa: E402
import analyze_selectors as SEL  # noqa: E402
import strategy as S  # noqa: E402

CAPITAL = E.CAPITAL
BASE_DI = 250
PICK = 10
PERIOD = 120
N_STARTS, START_GAP = 5, 37
N_PERM = 500
SEED = 20260922

SIGNALS = ("dip", "golden")
# config.yaml 의 실제 값. 바꾸지 않는다 - 그때 쓰던 규칙을 재현하는 것이다.
DIP_PCT = -10.0
DIP_LOOKBACK = 20
REBOUND_PCT = 3.0
MA_SHORT, MA_LONG = 5, 20

REDUNDANT_CORR = SEL.REDUNDANT_CORR      # 0.70, 같은 문턱을 쓴다
COMPARE_TO = ("low_vol", "trend", "reversal")
MIN_START_WINS = 4
PERM_ALPHA = 0.05


def dip_score(panel, code, di, pct=DIP_PCT, back=DIP_LOOKBACK,
              rebound=REBOUND_PCT):
    """dip 규칙. 조건을 만족하면 '얼마나 떨어졌나' 를 점수로, 아니면 None.

    조건 둘을 같이 본다.
      (1) 최근 back 일 고점 대비 pct% 이상 하락했다
      (2) 그 구간 저점 대비 rebound% 이상 되돌아섰다

    (2)가 reversal 팩터와의 차이다. reversal 은 떨어진 것을 그냥 사고,
    dip 은 떨어진 뒤 돌아서기 시작한 것만 산다.

    점수는 '고점 대비 하락폭' 이다. 많이 떨어진 것을 먼저 고른다 -
    screener.py 가 그랬던 방식이다.
    """
    s = panel.get(code)
    if s is None:
        return None
    j = s.pos.get(di - 1)
    if j is None or j < back:
        return None
    win = s.close[j - back + 1:j + 1]
    hi, lo = max(win), min(win)
    if not hi or not lo:
        return None
    now = s.close[j]
    if (now / hi - 1) * 100 > pct:        # 충분히 안 떨어졌다
        return None
    if (now / lo - 1) * 100 < rebound:    # 아직 안 돌아섰다
        return None
    return -(now / hi - 1) * 100          # 많이 떨어진 순


def golden_score(panel, code, di, short=MA_SHORT, long=MA_LONG):
    """골든크로스 상태. 5일선이 20일선 위면 그 이격%, 아니면 None.

    '교차한 그 날' 이 아니라 '위에 있는 상태' 로 잰다. 교차일만 사면
    표본이 너무 적고, 실제로도 그 상태가 유지되는 동안 들고 있었다.
    """
    s = panel.get(code)
    if s is None:
        return None
    j = s.pos.get(di - 1)
    if j is None or j < long:
        return None
    ms = st.mean(s.close[j - short + 1:j + 1])
    ml = st.mean(s.close[j - long + 1:j + 1])
    if not ml or ms <= ml:
        return None
    return (ms / ml - 1) * 100            # 이격이 큰 순


def score_of(panel, code, di, signal):
    if signal == "dip":
        return dip_score(panel, code, di)
    if signal == "golden":
        return golden_score(panel, code, di)
    return None


def picks_at(panel, di, signal, pick=PICK):
    """그 시점에 살 종목. 조건을 만족하는 게 pick 보다 적으면 None.

    억지로 채우지 않는 이유: dip 은 조건부 신호다. 조건에 안 맞는 종목을
    끌어와 채우면 '그때 쓰던 규칙' 이 아니게 된다.
    """
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    sc = [(x, c) for c in cand
          if (x := score_of(panel, c, di, signal)) is not None]
    if len(sc) < pick:
        return None
    sc.sort(reverse=True)
    return [c for _s, c in sc[:pick]]


def run(dates, panel, signal, start, upto=None, capital=CAPITAL, pick=PICK):
    """부분교체. 다른 신호들과 같은 규칙으로 돌린다.

    조건을 만족하는 종목이 모자란 교체일은 **건너뛴다** (그대로 들고 있다).
    """
    n = upto if upto is not None else len(dates)
    cash, hold = float(capital), {}
    curve, di, skipped = [], start, 0
    while di < n:
        if (di - start) % PERIOD == 0:
            new = picks_at(panel, di, signal, pick)
            if new is None:
                skipped += 1
            else:
                keep = {c: q for c, q in hold.items() if c in new}
                for c in [c for c in hold if c not in new]:
                    v = E.price(panel, c, di)
                    if v:
                        cash += hold[c] * v * (1 - E.FEE_ONE_WAY)
                add = [c for c in new if c not in hold]
                got, cash, _f = (E.buy_greedy(panel, cash, add, di) if add
                                 else ({}, cash, 0.0))
                hold = {**keep, **got}
        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, skipped


def _starts():
    return [BASE_DI + k * START_GAP for k in range(N_STARTS)]


def corr_with(dates, panel, signal, other, base=BASE_DI, period=PERIOD):
    """그 신호와 기존 팩터의 순위상관 평균. 겹치면 새로 재는 게 아니다."""
    vals = []
    for di in range(base, len(dates), period):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        a = {c: x for c in cand
             if (x := score_of(panel, c, di, signal)) is not None}
        b = {c: x for c in cand
             if (x := S.factor_score(panel, c, di, other)) is not None}
        if len(a) >= 3 and len(b) >= 3:
            vals.append(SEL.spearman(a, b))
    return st.mean(vals) if vals else 0.0


def vol_percentile(panel, di, picks):
    """고른 종목이 유니버스 안에서 얼마나 흔들리나. 0=가장 흔들림, 100=가장 안.

    -29.6% 가 왜 나왔나를 보려고 넣었다. low_vol 점수는 -표준편차라서
    작을수록 많이 흔들린다. 그래서 오름차순 순위가 그대로 '흔들리는 순' 이다.
    """
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    vol = {c: x for c in cand
           if (x := S.factor_score(panel, c, di, "low_vol")) is not None}
    if len(vol) < 20:
        return None, len(vol)
    order = sorted(vol, key=vol.get)          # 변동 큰 것부터
    rank = {c: i for i, c in enumerate(order)}
    got = [rank[c] / (len(order) - 1) * 100 for c in picks if c in rank]
    return (st.mean(got) if got else None), len(vol)


def why_lost(dates, panel, signal, base=BASE_DI, period=PERIOD, pick=PICK):
    """(교체일별 변동성 백분위, 조건 만족 종목수, 유니버스 크기)."""
    pcts, cnt, univ = [], [], []
    for di in range(base, len(dates), period):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = {c: x for c in cand
              if (x := score_of(panel, c, di, signal)) is not None}
        if len(sc) < pick:
            continue
        picks = sorted(sc, key=sc.get, reverse=True)[:pick]
        p, n = vol_percentile(panel, di, picks)
        if p is None:
            continue
        pcts.append(p)
        cnt.append(len(sc))
        univ.append(len(cand))
    return pcts, cnt, univ


def by_year(dates, panel, signal, ranks, base=BASE_DI, min_days=100):
    """해마다 따로. 채택 조건 4번의 재료."""
    years = {}
    for i, d in enumerate(dates):
        years.setdefault(d[:4], []).append(i)
    out = []
    for y in sorted(years):
        idx = years[y]
        lo, hi = max(idx[0], base), idx[-1] + 1
        if hi - lo < min_days:
            continue
        ref = F.annualized(E.run_calendar(dates, panel, ranks, PERIOD, lo,
                                          upto=hi)[0])
        sig = F.annualized(run(dates, panel, signal, lo, upto=hi)[0])
        out.append((y, ref, sig, sig - ref))
    return out


def accepted(start_wins, first_beats, second_beats, perm_p,
             years_pos, years_total, rest_mean):
    """채택 조건 넷. 전제.md 의 규약과 같다."""
    return (start_wins >= MIN_START_WINS
            and first_beats and second_beats
            and perm_p < PERM_ALPHA
            and years_total > 0
            and years_pos * 2 > years_total
            and rest_mean > 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description="옛 선정 규칙을 5.7년으로 잰다")
    ap.add_argument("--run", action="store_true", help="2단계(성과)까지")
    ap.add_argument("--why", action="store_true",
                    help="고른 종목이 얼마나 흔들리나 (왜 졌나)")
    args = ap.parse_args(argv)

    dates, panel = S.load_panel()
    starts = _starts()

    if args.why:
        print("\n=== 고른 종목이 유니버스 안에서 얼마나 흔들리나 ===")
        print("  (백분위 0 = 가장 많이 흔들림, 100 = 가장 안 흔들림)")
        for sig in SIGNALS:
            pcts, cnt, univ = why_lost(dates, panel, sig)
            if not pcts:
                print(f"  {sig:<10}잴 수 있는 교체일이 없다")
                continue
            print(f"  {sig:<10}교체일 {len(pcts)}회, 백분위 중앙 "
                  f"{st.median(pcts):.0f}")
            print(f"  {'':<10}회차별: "
                  + " ".join(f"{x:.0f}" for x in pcts))
            print(f"  {'':<10}조건 만족 {st.median(cnt):.0f}종목 / "
                  f"유니버스 {st.median(univ):.0f}종목 = "
                  f"{st.median(cnt) / st.median(univ) * 100:.0f}%")
        return 0

    print(f"\n=== 1단계: 기존 신호와 겹치나 (문턱 |상관| >= {REDUNDANT_CORR}) ===")
    print(f"{'신호':<10}" + "".join(f"{o:>12}" for o in COMPARE_TO) + "  판정")
    fresh = []
    for sig in SIGNALS:
        cs = [corr_with(dates, panel, sig, o) for o in COMPARE_TO]
        red = any(abs(c) >= REDUNDANT_CORR for c in cs)
        if not red:
            fresh.append(sig)
        print(f"{sig:<10}" + "".join(f"{c:>+12.3f}" for c in cs)
              + ("  재포장" if red else "  새 정보"))

    # 조건을 만족하는 종목이 몇 날이나 모자라는지 - dip 은 조건부 신호다
    print(f"\n=== 회차를 건너뛰는 날이 얼마나 되나 ===")
    for sig in SIGNALS:
        _c, sk = run(dates, panel, sig, BASE_DI)
        tot = (len(dates) - BASE_DI) // PERIOD + 1
        print(f"  {sig:<10}{sk}/{tot} 회차 건너뜀"
              + ("  <- 조건을 만족하는 종목이 10개 미만인 날" if sk else ""))

    if not args.run:
        print(f"\n2단계로 보낼 신호: {fresh}")
        print("--run 을 붙이면 성과까지 잽니다.")
        return 0
    if not fresh:
        print("\n전부 기존 신호의 재포장이다. 성과를 재지 않는다.")
        return 0

    ranks, _r = E.daily_ranks(dates, panel, BASE_DI)
    base_r = [F.annualized(E.run_calendar(dates, panel, ranks, PERIOD, s)[0])
              for s in starts]
    print(f"\n=== 2단계: 성과 (기준 저변동 {st.median(base_r):.1f}%) ===")
    print(f"{'신호':<10}{'연수익%':>9}{'낙폭%':>9}{'시작일':>8}")
    box = {}
    for sig in fresh:
        curves = [run(dates, panel, sig, s)[0] for s in starts]
        rs = [F.annualized(c) for c in curves]
        ds = [F.mdd(c) for c in curves]
        wins = sum(1 for i in range(len(starts)) if rs[i] > base_r[i])
        box[sig] = (st.median(rs), st.median(ds), wins)
        print(f"{sig:<10}{st.median(rs):>9.1f}{st.median(ds):>9.1f}"
              f"{f'{wins}/{len(starts)}':>8}", flush=True)

    passed = [s for s in fresh if box[s][2] >= MIN_START_WINS]
    if not passed:
        print(f"\n조건 1({MIN_START_WINS}/{len(starts)})을 넘은 것이 없다."
              " 여기서 끝. 조건을 고치지 않는다.")
        return 0

    half = BASE_DI + (len(dates) - BASE_DI) // 2
    print(f"\n조건 2 - 반띵 (신호 / 기준)")
    halves = {}
    for sig in passed:
        row = []
        for s, upto in ((BASE_DI, half), (half, None)):
            a = F.annualized(run(dates, panel, sig, s, upto=upto)[0])
            b = F.annualized(E.run_calendar(dates, panel, ranks, PERIOD, s,
                                            upto=upto)[0])
            row.append((a, b))
        halves[sig] = row
        (s1, r1), (s2, r2) = row
        v = ("양쪽 이김" if s1 > r1 and s2 > r2 else
             "뒤집힘" if (s1 > r1) != (s2 > r2) else "양쪽 짐")
        print(f"  {sig:<10}전반 {s1:>6.1f}/{r1:<6.1f}"
              f"후반 {s2:>6.1f}/{r2:<6.1f}  {v}", flush=True)

    print(f"\n조건 3 - 무작위 대조군 {N_PERM}회")
    ps = {}
    for sig in passed:
        ps[sig] = F.control_p(dates, panel, starts, box[sig][0],
                              n_perm=N_PERM, seed=SEED)
        print(f"  {sig:<10}관측 {box[sig][0]:>6.1f}  p = {ps[sig]:.4f}",
              flush=True)

    print(f"\n조건 4 - 연도별 (기준 대비 %p)")
    years = {}
    for sig in passed:
        rows = by_year(dates, panel, sig, ranks)
        years[sig] = rows
        diffs = [d for _y, _r, _s, d in rows]
        pos, rest = F.one_year_story(diffs)
        print(f"  {sig:<10}" + " ".join(f"{y}:{d:+.1f}"
                                        for y, _r, _s, d in rows))
        print(f"  {'':<10}양수 {pos}/{len(diffs)}, 최고 해 빼면 {rest:+.1f}%p",
              flush=True)

    print(f"\n{'신호':<10}{'조건1':>7}{'조건2':>8}{'조건3':>8}{'조건4':>8}  판정")
    for sig in passed:
        (s1, r1), (s2, r2) = halves[sig]
        diffs = [d for _y, _r, _s, d in years[sig]]
        pos, rest = F.one_year_story(diffs)
        ok = accepted(box[sig][2], s1 > r1, s2 > r2, ps[sig],
                      pos, len(diffs), rest)
        print(f"{sig:<10}{f'{box[sig][2]}/{len(starts)}':>7}"
              f"{'통과' if s1 > r1 and s2 > r2 else '탈락':>8}"
              f"{'통과' if ps[sig] < PERM_ALPHA else '탈락':>8}"
              f"{'통과' if pos * 2 > len(diffs) and rest > 0 else '탈락':>8}"
              f"  {'채택' if ok else '탈락'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
