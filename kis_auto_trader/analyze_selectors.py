"""종목별 지표를 선정에 쓸 수 있나. (기준만 먼저 - 결과 미기입)

(2026-09-21 신설) 사용자: "그럼 종목 선정에 지표들을 써봤으면 좋겠거든"

===========================================================================
먼저 갈라야 할 것 - 14개 지표는 선정에 못 쓴다
===========================================================================
market_indicators 의 14개(미국지수 / VIX / 환율 / 금리 / 국내 변동성 /
상승종목비율 / 수급합계)는 전부 **하루에 한 줄, 시장 전체** 값이다.
종목마다 다른 값이 아니므로 "어느 종목을 살까" 에는 쓸 수가 없다.
그래서 analyze_timing / consensus / cascade 가 전부 타이밍으로만 썼고,
전부 탈락했다.

종목마다 다른 값을 주는 것은 이것뿐이다.
  krx_panel  시/고/저/종/거래량       -> 저변동, 모멘텀, 추세, 반전, 거래대금  (시험 완료)
  krx_flow   외국인/기관/개인/기타법인 -> 수급 횡단면                          (시험 완료)
  krx_fund   PER / PBR / 배당         -> 재무                                (시험 완료)
  krx_cap    시가총액/상장주식수/거래대금 -> **한 번도 안 썼다**

krx_cap 은 1,813종목 / 1,401일 / 226만행으로 패널과 같은 범위인데
수집만 해놓고 분석에 안 썼다. 시가총액은 금융에서 가장 오래된 팩터
중 하나다. 여기가 진짜 빈칸이다.

===========================================================================
미리 못 박는 것 - 데이터를 보기 전에 쓴다
===========================================================================
이 파일은 **한 번도 돌려보기 전에** 작성했고, 결과가 나오기 전에
커밋했다. git log 로 확인할 수 있다.

시험할 것은 **다섯 가지뿐이다.** 늘리지 않는다.

  size        시가총액이 작은 순          krx_cap.market_cap
  turnover    회전율이 낮은 순            trade_value / market_cap
  downside    하방변동성이 낮은 순        음수 수익률만 모은 표준편차
  past_mdd    과거 최대낙폭이 작은 순     최근 120일 고점 대비
  beta        시장 민감도가 낮은 순       120일 공분산 / 시장분산

방향도 미리 정한다. 다섯 다 "낮을수록/작을수록 좋다" 다. 양방향을
시험하면 가짓수가 두 배가 되므로 한 방향만 본다. 방향을 이렇게 잡은
이유는 사용자의 목표가 '큰 이득을 포기하더라도 큰 손해를 피한다' 이고,
이 저장소에서 작동한 유일한 신호(저변동)도 같은 성격이기 때문이다.

방식은 **저변동과 결합하는 것 하나만** 본다 (alone 은 안 본다).
  이유: analyze_fundamentals 에서 재무를 단독으로 쓰면 여섯 중 여섯이
  졌다. 저변동이 뼈대이고 새 지표는 그 위에 얹는 것인지를 묻는 게
  맞는 질문이다. alone 을 같이 보면 가짓수만 두 배가 된다.

  => 최대 5가지. 아래 1단계에서 더 줄어든다.

---------------------------------------------------------------------------
1단계 - 새 정보인가 (성과를 안 본다. 다중검정에 안 들어간다)
---------------------------------------------------------------------------
저변동 순위와 각 지표 순위의 순위상관을 잰다. 하방변동성이나 베타는
변동성과 거의 같은 것일 수 있다. 그러면 '새 지표' 가 아니라 '저변동의
재포장' 이고, 성과가 좋아 보여도 새 정보가 아니다.

  |상관| >= 0.70  ->  재포장으로 보고 성과 시험을 하지 않는다
  |상관| <  0.70  ->  2단계로 보낸다

이 문턱을 미리 박는 이유: 결과를 보고 "0.75 면 그래도 다르지" 라고
할 수 있기 때문이다. analyze_consensus 에서 지표 14개의 실질 독립
차원이 6.3개였던 것과 같은 문제다.

---------------------------------------------------------------------------
2단계 - 채택 조건 (넷 다 넘어야 한다)
---------------------------------------------------------------------------
  1) 시작일 5개 중 4개 이상에서 기준선(저변동)을 이긴다
  2) 반띵 양방향 모두에서 기준선을 이긴다
  3) 무작위 대조군 500회를 넘는다 (p < 0.05)
  4) **연도별 지속성** - 양수인 해가 과반을 넘고, 최고 해 하나를 빼도
     나머지 평균이 양수다

4번이 이번에 새로 들어갔다. analyze_fundamentals 에서 PER/PBR 이
1~3번을 전부 통과했는데 해마다 쪼개니 2025년 한 해가 전부였다
(pbr 은 그 해를 빼면 -3.6%p). 1~3번이 서로 독립이 아니었기 때문이다.
시작일 5개는 37일 간격이라 전부 같은 해를 통과하고, 반띵의 후반부는
그 해를 통째로 품고, 대조군은 전 구간을 한 덩어리로 본다.
저변동은 이 검사를 6/6 으로 통과했다 (analyze_decay.py).

하나라도 걸리면 넣지 않는다. 그리고 "아깝다" 며 조건을 고치지 않는다.

미리 정해두는 처리 방식
  시가총액 <= 0      제외 (값이 뜻을 잃는다)
  상장주식수 <= 0    제외 (회전율을 못 구한다)
  값이 없는 날       그 종목은 그 회차에서 제외. 앞의 값을 끌어다 쓰지
                     않는다 - 그러면 없는 정보를 만들어내게 된다.
  미래 정보          di - 1 까지만 본다. 가격 신호와 같은 규칙이다.
  시장 수익률        그날 후보 종목들의 동일가중 평균 (지수를 따로
                     안 쓴다 - 패널 안에서 닫아두기 위해서다)

===========================================================================
결과 (2026-09-21) - 다섯 다 탈락
===========================================================================
1단계 - 저변동과의 순위상관 (문턱 0.70)

    지표        상관      판정
    size      -0.722   재포장 - 시험 안 함
    turnover  +0.788   재포장 - 시험 안 함
    downside  +0.834   재포장 - 시험 안 함
    past_mdd  +0.537   새 정보 - 시험한다
    beta      +0.530   새 정보 - 시험한다

**다섯 중 셋이 저변동의 다른 이름이었다.** 성과를 재보기도 전에 걸렀고,
그만큼 다중검정이 줄었다. 문턱을 미리 박아둔 것이 실제로 일을 했다.

특히 size 가 -0.722 인 것이 중요하다. 부호가 음수라는 것은 **시가총액이
작을수록 변동성이 크다** 는 뜻이다. 즉 '소형주를 고른다' 는 사실상
'고변동을 고른다' 와 거의 같다. 이 저장소에서 고변동 10종목은 연
-41.5% 였다 (analyze_knobs.py --flip). 소형주 프리미엄을 쫓았다면
그쪽으로 갔을 것이다.

downside(+0.834)가 걸린 것도 뜻이 있다. '하락할 때만의 변동성' 은
직관적으로 저변동과 다른 것 같지만 실제로는 같은 것을 재고 있었다.

2단계 - 남은 둘의 성과 (기준 저변동 22.3%, 낙폭 -15.9%)

    지표        연수익%   낙폭%   시작일
    past_mdd    20.0    -19.2    2/5
    beta        17.7    -19.5    2/5

둘 다 조건 1(4/5)에서 탈락했다. 조건 2, 3, 4 는 돌리지 않았다.
**맞교환조차 없다** - 수익이 낮으면서 낙폭도 더 나쁘다.

읽는 법
  1) 베타가 지는 것이 조금 뜻밖이다. '시장에 덜 흔들리는 종목' 은
     저변동과 통하는 말인데, 상관이 0.530 으로 낮았고 성과는 나빴다.
     즉 베타가 잡는 '시장과의 관계' 는 저변동이 잡는 '자기 흔들림' 과
     다른 것이고, 작동하는 쪽은 후자다.
  2) 다중검정: 사전 등록 5개 중 실제로 성과를 잰 것은 2개다.
  3) 2021~2026 한국 시장이다.
  4) 이것으로 **지금 가진 데이터로 만들 수 있는 종목별 선정 신호를
     다 써봤다.** krx_panel / krx_flow / krx_fund / krx_cap 넷 다.
     남은 것은 새 데이터를 구하는 것뿐이다.

실행:
  python analyze_selectors.py            # 1단계 (저변동과 얼마나 겹치나)
  python analyze_selectors.py --run      # 2단계까지
"""
import argparse
import csv
import glob
import pathlib
import random
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import analyze_fundamentals as F  # noqa: E402
import strategy as S  # noqa: E402

CAPITAL = E.CAPITAL
BASE_DI = 250
PICK = 10
PERIOD = 120
DAYS_PER_YEAR = 246
N_STARTS, START_GAP = 5, 37
N_PERM = 500
SEED = 20260921

# 미리 정한 다섯. 늘리지 않는다.
SIGNALS = ("size", "turnover", "downside", "past_mdd", "beta")
VOL_DAYS = 60
MDD_DAYS = 120
BETA_DAYS = 120

# 1단계 문턱
REDUNDANT_CORR = 0.70
# 2단계 채택 조건
MIN_START_WINS = 4
PERM_ALPHA = 0.05


def load_cap(dates):
    """krx_cap_*.csv 를 {(di, code): {cap, tvalue, shares}} 로 읽는다."""
    dpos = {d: i for i, d in enumerate(dates)}
    out = {}
    for path in sorted(glob.glob(str(_ROOT / "data" / "krx_cap_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                di = dpos.get(r["date"])
                if di is None:
                    continue
                rec = {}
                for key, col in (("cap", "market_cap"),
                                 ("tvalue", "trade_value"),
                                 ("shares", "shares")):
                    try:
                        rec[key] = float(r[col])
                    except (KeyError, TypeError, ValueError):
                        rec[key] = None
                out[(di, r["code"])] = rec
    return out


def _returns(series, j, days):
    if j < days:
        return None
    return [series.close[k] / series.close[k - 1] - 1
            for k in range(j - days + 1, j + 1)
            if series.close[k - 1]]


def sel_score(panel, cap, code, di, signal, market=None):
    """di 일 시가에 살 종목을 고르기 위한 점수. di-1 까지만 본다.

    높을수록 좋은 값으로 맞춘다 (저변동 점수와 방향을 같게 하려고).
    다섯 다 '낮을수록/작을수록 좋다' 이므로 부호를 뒤집는다.
    """
    s = panel.get(code)
    if s is None:
        return None
    j = s.pos.get(di - 1)
    if j is None:
        return None

    if signal in ("size", "turnover"):
        rec = cap.get((di - 1, code))
        if rec is None:
            return None
        c = rec.get("cap")
        if not c or c <= 0:
            return None
        if signal == "size":
            return -c                       # 작을수록 좋다
        tv = rec.get("tvalue")
        if tv is None:
            return None
        return -(tv / c)                    # 회전율이 낮을수록 좋다

    if signal == "downside":
        rets = _returns(s, j, VOL_DAYS)
        if not rets:
            return None
        down = [x for x in rets if x < 0]
        if len(down) < 2:
            return None
        return -st.pstdev(down)             # 낮을수록 좋다

    if signal == "past_mdd":
        if j < MDD_DAYS:
            return None
        win = s.close[j - MDD_DAYS + 1:j + 1]
        peak, worst = win[0], 0.0
        for v in win:
            peak = max(peak, v)
            if peak:
                worst = min(worst, v / peak - 1)
        return worst                        # 0 에 가까울수록 좋다 (음수)

    if signal == "beta":
        rets = _returns(s, j, BETA_DAYS)
        if not rets or market is None or len(market) != len(rets):
            return None
        mvar = st.pvariance(market)
        if not mvar:
            return None
        mbar, sbar = st.mean(market), st.mean(rets)
        cov = sum((a - mbar) * (b - sbar)
                  for a, b in zip(market, rets)) / len(rets)
        return -(cov / mvar)                # 낮을수록 좋다
    return None


def market_returns(panel, codes, di, days=BETA_DAYS):
    """그날 후보들의 동일가중 평균 수익률. 지수를 따로 안 쓴다.

    패널 밖의 데이터를 안 들여오려는 것이다. 지수를 쓰면 구성종목이
    패널과 달라서 비교가 흐려진다.
    """
    cols = []
    for c in codes:
        r = _returns(panel[c], panel[c].pos.get(di - 1, -1), days) \
            if panel[c].pos.get(di - 1) is not None else None
        if r and len(r) == days:
            cols.append(r)
    if not cols:
        return None
    return [st.mean(col[k] for col in cols) for k in range(days)]


def spearman(a, b):
    """순위상관. 값의 단위가 다르므로 등수로 비교한다."""
    common = [k for k in a if k in b]
    if len(common) < 3:
        return 0.0
    ra = {c: i for i, c in enumerate(sorted(common, key=lambda c: a[c]))}
    rb = {c: i for i, c in enumerate(sorted(common, key=lambda c: b[c]))}
    n = len(common)
    d2 = sum((ra[c] - rb[c]) ** 2 for c in common)
    return 1 - 6 * d2 / (n * (n * n - 1))


def redundant(corr, thresh=REDUNDANT_CORR):
    """저변동의 재포장인가. 문턱을 미리 박아둔다."""
    return abs(corr) >= thresh


def accepted(start_wins, first_beats, second_beats, perm_p,
             years_pos, years_total, rest_mean):
    """채택 조건 네 개를 전부 넘겼나.

    4번(연도별)이 2026-09-21 에 추가됐다. analyze_fundamentals 에서
    1~3번을 전부 통과한 신호가 해마다 쪼개니 한 해짜리였기 때문이다.
    """
    return (start_wins >= MIN_START_WINS
            and first_beats and second_beats
            and perm_p < PERM_ALPHA
            and years_total > 0
            and years_pos * 2 > years_total
            and rest_mean > 0)


def picks_at(panel, cap, di, signal, market=None):
    """그 시점에 살 PICK 종목. 저변동 순위와 평균해서 고른다."""
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    ss = [(x, c) for c in cand
          if (x := sel_score(panel, cap, c, di, signal, market)) is not None]
    vs = [(x, c) for c in cand
          if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
    if len(ss) < PICK or len(vs) < PICK:
        return None
    sr, vr = F.rank_map(ss), F.rank_map(vs)
    both = [c for c in sr if c in vr]
    if len(both) < PICK:
        return None
    both.sort(key=lambda c: (sr[c] + vr[c]) / 2)
    return both[:PICK]


def run(dates, panel, cap, signal, start, upto=None, capital=CAPITAL):
    """부분교체. 다른 신호들과 같은 규칙으로 돌린다."""
    n = upto if upto is not None else len(dates)
    cash, hold = float(capital), {}
    curve, di = [], start
    while di < n:
        if (di - start) % PERIOD == 0:
            market = None
            if signal == "beta":
                cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
                market = market_returns(panel, cand, di)
            new = picks_at(panel, cap, di, signal, market)
            if new:
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
    return curve


def by_year(dates, panel, cap, signal, ranks, base_di=BASE_DI, min_days=100):
    """해마다 따로 돌린다. 조건 4 의 재료다.

    analyze_fundamentals.by_year 와 같은 방식인데, 거기는 fund 를 받고
    여기는 cap 을 받아서 따로 둔다.
    """
    years = {}
    for i, d in enumerate(dates):
        years.setdefault(d[:4], []).append(i)
    out = []
    for y in sorted(years):
        idx = years[y]
        lo, hi = max(idx[0], base_di), idx[-1] + 1
        if hi - lo < min_days:
            continue
        ref = F.annualized(E.run_calendar(dates, panel, ranks, PERIOD, lo,
                                          upto=hi)[0])
        sig = F.annualized(run(dates, panel, cap, signal, lo, upto=hi))
        out.append((y, ref, sig, sig - ref))
    return out


def main():
    ap = argparse.ArgumentParser(description="종목별 지표를 선정에 쓸 수 있나")
    ap.add_argument("--run", action="store_true",
                    help="2단계(성과)까지 돌린다")
    args = ap.parse_args()

    dates, panel = S.load_panel()
    cap = load_cap(dates)
    print(f"\n[시총 데이터] {len({c for _d, c in cap}):,}종목 / "
          f"{len({d for d, _c in cap}):,}일")

    print(f"\n=== 1단계: 저변동과 얼마나 겹치나 (문턱 |상관| >= "
          f"{REDUNDANT_CORR}) ===")
    print(f"{'지표':<12}{'저변동과 순위상관':>18}  판정")
    starts = [BASE_DI + k * START_GAP for k in range(N_STARTS)]
    corrs, fresh = {}, []
    for signal in SIGNALS:
        vals = []
        for di in range(BASE_DI, len(dates), PERIOD):
            cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
            market = (market_returns(panel, cand, di)
                      if signal == "beta" else None)
            a = {c: x for c in cand
                 if (x := sel_score(panel, cap, c, di, signal, market))
                 is not None}
            b = {c: x for c in cand
                 if (x := S.factor_score(panel, c, di, "low_vol")) is not None}
            if len(a) >= 3 and len(b) >= 3:
                vals.append(spearman(a, b))
        corr = st.mean(vals) if vals else 0.0
        corrs[signal] = corr
        red = redundant(corr)
        if not red:
            fresh.append(signal)
        print(f"{signal:<12}{corr:>18.3f}  "
              f"{'재포장 - 시험 안 함' if red else '새 정보 - 시험한다'}")

    print(f"\n2단계로 보낼 지표: {len(fresh)}개 {fresh}")
    if not args.run:
        print("\n--run 을 붙이면 2단계(성과)까지 돌립니다.")
        return 0
    if not fresh:
        print("전부 저변동의 재포장이다. 성과를 시험하지 않는다.")
        return 0

    ranks, _ = E.daily_ranks(dates, panel, BASE_DI)
    base = [F.annualized(E.run_calendar(dates, panel, ranks, PERIOD, s)[0])
            for s in starts]
    print(f"\n=== 2단계: 성과 (기준 저변동 {st.median(base):.1f}%, "
          f"낙폭 {st.median(F.mdd(E.run_calendar(dates, panel, ranks, PERIOD, s)[0]) for s in starts):.1f}%) ===")
    print(f"{'지표':<12}{'연수익%':>9}{'낙폭%':>9}{'시작일':>8}")
    box = {}
    for signal in fresh:
        curves = [run(dates, panel, cap, signal, s) for s in starts]
        rs = [F.annualized(c) for c in curves]
        ds = [F.mdd(c) for c in curves]
        wins = sum(1 for i in range(len(starts)) if rs[i] > base[i])
        box[signal] = (st.median(rs), st.median(ds), wins)
        print(f"{signal:<12}{st.median(rs):>9.1f}{st.median(ds):>9.1f}"
              f"{f'{wins}/{len(starts)}':>8}", flush=True)

    # 조건 1 을 넘은 것만 뒤로 보낸다 (대조군이 오래 걸린다).
    passed = [s for s in fresh if box[s][2] >= MIN_START_WINS]
    if not passed:
        print(f"\n조건 1({MIN_START_WINS}/{len(starts)})을 넘은 것이 없다."
              " 여기서 끝. 조건을 고치지 않는다.")
        return 0

    half = BASE_DI + (len(dates) - BASE_DI) // 2
    print(f"\n조건 2 - 반띵 (신호 / 기준)")
    halves = {}
    for signal in passed:
        row = []
        for s, upto in ((BASE_DI, half), (half, None)):
            sig = F.annualized(run(dates, panel, cap, signal, s, upto=upto))
            ref = F.annualized(E.run_calendar(dates, panel, ranks, PERIOD, s,
                                              upto=upto)[0])
            row.append((sig, ref))
        halves[signal] = row
        (s1, r1), (s2, r2) = row
        v = ("양쪽 이김" if s1 > r1 and s2 > r2 else
             "뒤집힘" if (s1 > r1) != (s2 > r2) else "양쪽 짐")
        print(f"  {signal:<12}전반 {s1:>6.1f} / {r1:<6.1f}"
              f"후반 {s2:>6.1f} / {r2:<6.1f}  {v}", flush=True)

    print(f"\n조건 3 - 무작위 대조군 {N_PERM}회")
    ps = {}
    for signal in passed:
        ps[signal] = F.control_p(dates, panel, starts, box[signal][0],
                                 n_perm=N_PERM, seed=SEED)
        print(f"  {signal:<12}관측 {box[signal][0]:>6.1f}   "
              f"p = {ps[signal]:.4f}", flush=True)

    print(f"\n조건 4 - 연도별 지속성 (기준 대비 %p)")
    years = {}
    for signal in passed:
        rows = by_year(dates, panel, cap, signal, ranks)
        years[signal] = rows
        diffs = [d for _y, _r, _s, d in rows]
        pos, rest = F.one_year_story(diffs)
        print(f"  {signal:<12}" + " ".join(f"{y}:{d:+.1f}"
                                           for y, _r, _s, d in rows))
        print(f"  {'':<12}양수인 해 {pos}/{len(diffs)}, "
              f"최고 해를 빼면 나머지 평균 {rest:+.1f}%p", flush=True)

    print(f"\n{'지표':<12}{'조건1':>7}{'조건2':>8}{'조건3':>8}{'조건4':>8}  판정")
    for signal in passed:
        (s1, r1), (s2, r2) = halves[signal]
        diffs = [d for _y, _r, _s, d in years[signal]]
        pos, rest = F.one_year_story(diffs)
        ok = accepted(box[signal][2], s1 > r1, s2 > r2, ps[signal],
                      pos, len(diffs), rest)
        print(f"{signal:<12}{f'{box[signal][2]}/{len(starts)}':>7}"
              f"{'통과' if s1 > r1 and s2 > r2 else '탈락':>8}"
              f"{'통과' if ps[signal] < PERM_ALPHA else '탈락':>8}"
              f"{'통과' if pos*2 > len(diffs) and rest > 0 else '탈락':>8}"
              f"  {'채택' if ok else '탈락'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
