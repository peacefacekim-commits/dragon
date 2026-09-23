"""기본 전략 - 살아남은 규칙 + 종목 선정 + 나쁜날 게이트.

(2026-09-16 신설)

왜 이 파일이 있나. 열세 번의 가설 검증에서 '예측' 은 전부 실패했다. 살아남은
것은 예측이 아니라 산수와 실거래 기록에서 나온 규칙 여섯 개뿐이다.

  1. 자주 거래하면 진다        일일회전 수수료만 연 52.5%
  2. 익절 3.5%/손절 -4% 는 진다 필요 승률 53~57%, 실제 43~49%
  3. 5,000원 미만은 피한다      실거래 34건 -198,401원 / 승률 26.5%
  4. 당일 강제청산은 수수료만    세전 -12,663원, 수수료 -18,516원
  5. 고정 비중 > 변동성 조절     +29.4% vs +0.5% (같은 평균 비중)
  6. 개입하지 않는다            실거래 26일 동안 시장 +20.83% / 본인 -6.53%

이 파일은 그 여섯 개를 코드로 굳힌 것이다. 예측하지 않고, 규칙만 지킨다.

구성:
  유니버스   거래대금 상위 N (20일 평균 종가x거래량), 매월 다시 뽑음
             종가 5,000원 이상
  종목 선정  팩터 점수 상위 top_n, 동일가중 (고정 비중)
  진입       리밸런스일 시가. 신호는 전일 종가까지로만 계산한다
  청산       hold_days 거래일 뒤 시가. 익절/손절 없음 (규칙 2)
  수수료     왕복 0.21%
  나쁜날     market_indicators 점수가 임계값 미만이면 그 회차를 쉰다
             (기본 꺼짐 - 아래 '나쁜날 게이트에 대하여' 참고)

생존편향:
  유니버스를 krx_panel 에서 매달 다시 뽑는다. krx_panel 에는 상장폐지/거래정지
  종목이 그대로 들어 있고, 폐지되면 그 이후 날짜에 안 나타난다. 그래서 '그
  시점에 실제로 살 수 있었던 종목' 만 후보가 된다. 보유 중 데이터가 끊긴
  종목은 마지막 종가로 청산 처리하되, 몇 건인지 따로 보고한다 - 실제 폐지는
  마지막 종가보다 훨씬 나쁘므로 이 처리는 결과를 낙관적으로 만든다.
  --delisting-loss 로 그 낙관을 벗겨낸 값도 볼 수 있다.

나쁜날 게이트에 대하여:
  "나쁜 날을 미리 알아내 그 날은 쉰다" 는 열세 번 검증해서 전부 실패했다.
  마지막으로 보유기간을 늘려(1일->5일->20일) 다시 재봤고, 시험 구간 상관은
  +0.028 / +0.010 / +0.054 였다. 평균도, 아래쪽 꼬리도, 최대낙폭도 나아지지
  않았다 (20일 기준 유효 표본 33개).

  그래서 게이트는 코드로 만들어 두되 기본값은 꺼짐이다. 켜면 매 회차의 점수와
  쉼/투자 결정을 기록하므로, 앞으로 데이터가 쌓이면 '미리 정한 기준으로'
  채점할 수 있다. 지금 켜는 것은 검증된 규칙이 아니라 가설을 얹는 것이다.

실행:
    python strategy.py --hold 20
    python strategy.py --sweep
"""
import argparse
import collections
import csv
import glob
import statistics as st
import sys
from dataclasses import dataclass, field

from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
PANEL_PREFIX = "krx_panel"
FEE_ROUND_TRIP_PCT = 0.21
MIN_PRICE = 5000                 # 규칙 3
UNIVERSE_SIZE = 200
LIQUIDITY_DAYS = 20              # 거래대금 평균 기간
MIN_STOCKS_TO_TRADE = 10

FACTORS = ("momentum", "trend", "low_vol", "reversal", "liquidity", "all")


@dataclass(slots=True)
class Series:
    """한 종목의 시계열. i 번째 원소가 dates[di[i]] 에 해당한다."""
    di: list = field(default_factory=list)      # 전체 날짜 배열에서의 인덱스
    open: list = field(default_factory=list)
    close: list = field(default_factory=list)
    value: list = field(default_factory=list)   # 종가 x 거래량 (거래대금 근사)
    pos: dict = field(default_factory=dict)     # 날짜인덱스 -> 몇 번째 원소


# 마지막 날이 이 비율보다 적은 종목만 갖고 있으면 '아직 다 안 받은 날' 로
# 보고 버린다. 573/1712 = 0.33 이었으므로 0.6 이면 넉넉히 잡힌다.
# 반장(단축매매)일에도 상장 종목 수는 그대로이므로 오탐이 안 난다.
INCOMPLETE_TAIL_RATIO = 0.6
INCOMPLETE_TAIL_REF_DAYS = 20


def _drop_incomplete_tail(dates, raw, verbose=True,
                          ratio=INCOMPLETE_TAIL_RATIO,
                          ref=INCOMPLETE_TAIL_REF_DAYS):
    """뒤쪽에 있는 '아직 다 안 받은 날' 을 잘라낸다. (남은 날짜, 버린 수)

    (2026-09-22 추가) 실제로 당했다. 장 시작 전(08:36)에 수집이 돌아서
    20260922 가 573종목만 들어왔다 (전날 1,712종목). 그게 패널의 마지막
    날이 되자 보유 종목 대부분이 그날 가격을 못 찾고, 포트폴리오 평가액이
    현금 수준으로 주저앉았다. 그 결과 확립돼 있던 연 +22.0% 가 -21.6%
    로 보였다. 데이터가 아니라 마지막 한 줄이 만든 값이다.

    분석 모듈 30개가 전부 load_panel 을 지나가므로 여기서 한 번 막는다.
    조용히 버리지 않는다 - 버렸으면 반드시 화면에 적는다. 그래야 '왜
    어제 숫자와 다르지' 를 헤매지 않는다.
    """
    if len(dates) < ref + 2:
        return dates, 0
    per_day = collections.Counter(d for recs in raw.values() for d, *_ in recs)
    out, n_drop = list(dates), 0
    while len(out) > ref + 1:
        prev = [per_day.get(d, 0) for d in out[-ref - 1:-1]]
        base = st.median(prev) if prev else 0
        if base and per_day.get(out[-1], 0) < base * ratio:
            if verbose:
                print(f"[!] {out[-1]} 는 {per_day.get(out[-1], 0):,}종목뿐입니다 "
                      f"(앞 {ref}일 중앙 {base:,.0f}종목). 아직 다 안 받은 "
                      f"날로 보고 제외합니다.")
            out.pop()
            n_drop += 1
        else:
            break
    return out, n_drop


def load_panel(verbose: bool = True) -> tuple[list, dict]:
    raw = {}
    all_dates = set()
    files = sorted(glob.glob(str(DATA_DIR / f"{PANEL_PREFIX}_*.csv")))
    if not files:
        raise SystemExit(f"{PANEL_PREFIX} 데이터가 없습니다: {DATA_DIR}")
    for path in files:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    o = float(r["open"]); c = float(r["close"])
                    v = float(r["volume"])
                except (TypeError, ValueError, KeyError):
                    continue
                if o <= 0 or c <= 0:
                    continue
                d = r["date"]
                all_dates.add(d)
                raw.setdefault(r["code"], []).append((d, o, c, c * v))

    dates = sorted(all_dates)
    dates, dropped = _drop_incomplete_tail(dates, raw, verbose)
    if dropped:
        keep = set(dates)
        raw = {code: [t for t in recs if t[0] in keep]
               for code, recs in raw.items()}
        raw = {c: r for c, r in raw.items() if r}
    idx = {d: i for i, d in enumerate(dates)}
    panel = {}
    for code, recs in raw.items():
        recs.sort()
        s = Series()
        for d, o, c, val in recs:
            s.pos[idx[d]] = len(s.di)
            s.di.append(idx[d])
            s.open.append(o)
            s.close.append(c)
            s.value.append(val)
        panel[code] = s
    if verbose:
        print(f"패널: {len(panel):,}종목 / {len(dates):,}거래일 "
              f"({dates[0]} ~ {dates[-1]})")
    return dates, panel


# ------------------------------------------------------------------ 유니버스
def universe_at(panel, di, size=UNIVERSE_SIZE, min_price=MIN_PRICE):
    """di 번째 날의 '전일까지' 정보로 후보를 뽑는다. 미래를 안 본다.

    거래대금 20일 평균 상위 size 개, 그리고 종가 min_price 이상.
    """
    scored = []
    for code, s in panel.items():
        j = s.pos.get(di - 1)
        if j is None or j < LIQUIDITY_DAYS:
            continue
        if s.close[j] < min_price:
            continue
        scored.append((st.mean(s.value[j - LIQUIDITY_DAYS + 1:j + 1]), code))
    scored.sort(reverse=True)
    return [c for _v, c in scored[:size]]


# ------------------------------------------------------------------ 팩터
def factor_score(panel, code, di, factor, lookback=120, skip=5, vol_days=60):
    """di 일 시가에 살 종목을 고르기 위한 점수. di-1 종가까지만 쓴다."""
    s = panel[code]
    j = s.pos.get(di - 1)
    if j is None:
        return None
    if factor == "momentum":
        if j < lookback + skip:
            return None
        return s.close[j - skip] / s.close[j - skip - lookback] - 1
    if factor == "trend":
        if j < lookback:
            return None
        ma = st.mean(s.close[j - lookback + 1:j + 1])
        return s.close[j] / ma - 1 if ma else None
    if factor == "low_vol":
        if j < vol_days:
            return None
        rets = [s.close[k] / s.close[k - 1] - 1
                for k in range(j - vol_days + 1, j + 1)]
        sd = st.pstdev(rets)
        return -sd
    if factor == "reversal":
        if j < 20:
            return None
        return -(s.close[j] / s.close[j - 20] - 1)
    if factor == "liquidity":
        if j < LIQUIDITY_DAYS:
            return None
        return st.mean(s.value[j - LIQUIDITY_DAYS + 1:j + 1])
    if factor == "all":
        return 0.0                 # 유니버스 전체 동일가중 (기준선)
    raise ValueError(f"모르는 팩터: {factor}")


# ------------------------------------------------------------------ 보유 수익
def trade_return(panel, code, entry_di, exit_di, delisting_loss=None):
    """entry_di 시가 매수 -> exit_di 시가 매도. (수익률%, 데이터끊김여부)"""
    s = panel[code]
    je = s.pos.get(entry_di)
    if je is None:
        return None, False
    jx = s.pos.get(exit_di)
    if jx is not None:
        return (s.open[jx] / s.open[je] - 1) * 100, False
    # 보유 중 데이터가 끊겼다 = 폐지/거래정지 가능성
    last = None
    for k in range(len(s.di) - 1, je - 1, -1):
        if s.di[k] <= exit_di:
            last = k
            break
    if last is None or last == je:
        return None, False
    if delisting_loss is not None:
        return -abs(delisting_loss), True
    return (s.close[last] / s.open[je] - 1) * 100, True


# ------------------------------------------------------------------ 나쁜날
def load_day_scores():
    """market_indicators 에서 날짜별 예측용 지표를 읽는다."""
    import market_indicators as mi
    out = {}
    for path in sorted(glob.glob(str(DATA_DIR / f"{mi.PREFIX}_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                vals = {}
                for k in mi.PREDICTOR_FIELDS:
                    try:
                        vals[k] = float(r[k])
                    except (TypeError, ValueError, KeyError):
                        vals[k] = None
                out[r["date"]] = vals
    return out


def build_day_gate(day_vals, train_dates, train_outcome):
    """전반부에서만 부호와 표준화를 정한다. 후반부에 그대로 적용한다.

    train_outcome[d] = 그 날 진입했을 때의 실제 수익률. 이걸로 각 지표의
    방향을 정한다. 후반부 데이터는 쳐다보지 않는다.
    """
    keys = [k for k in next(iter(day_vals.values()))]
    usable = [d for d in train_dates
              if d in day_vals and d in train_outcome
              and all(day_vals[d][k] is not None for k in keys)]
    if len(usable) < 50:
        return None
    stats, signs = {}, {}
    ys = [train_outcome[d] for d in usable]
    my = st.mean(ys)
    for k in keys:
        xs = [day_vals[d][k] for d in usable]
        m, sd = st.mean(xs), (st.pstdev(xs) or 1.0)
        stats[k] = (m, sd)
        cov = sum((x - m) * (y - my) for x, y in zip(xs, ys))
        signs[k] = 1.0 if cov >= 0 else -1.0

    def score(d):
        v = day_vals.get(d)
        if not v or any(v[k] is None for k in keys):
            return None
        return st.mean([signs[k] * (v[k] - stats[k][0]) / stats[k][1]
                        for k in keys])

    scores = sorted(s for s in (score(d) for d in usable) if s is not None)
    return {"score": score, "train_scores": scores, "signs": signs}


# ------------------------------------------------------------------ 실행
def run(dates, panel, factor="momentum", hold_days=20, top_n=10,
        universe_size=UNIVERSE_SIZE, min_price=MIN_PRICE,
        fee_pct=FEE_ROUND_TRIP_PCT, delisting_loss=None,
        gate=None, gate_pct=0.0, start_di=None, end_di=None, label=None,
        min_stocks=MIN_STOCKS_TO_TRADE, verbose=True) -> dict:
    """리밸런스마다 top_n 종목을 동일가중으로 사고 hold_days 뒤 판다."""
    first = start_di if start_di is not None else max(140, LIQUIDITY_DAYS + 2)
    last = len(dates) if end_di is None else min(end_di, len(dates))
    rounds, skipped, delisted = [], 0, 0
    di = first
    while di + hold_days < last:
        if gate is not None and gate_pct > 0:
            sc = gate["score"](dates[di])
            thr = gate["train_scores"][int(len(gate["train_scores"]) * gate_pct)]
            if sc is None or sc < thr:
                skipped += 1
                di += 1                    # 쉬면 다음날 다시 본다
                continue

        cand = universe_at(panel, di, universe_size, min_price)
        scored = []
        for code in cand:
            sc = factor_score(panel, code, di, factor)
            if sc is not None:
                scored.append((sc, code))
        if len(scored) < max(top_n, min_stocks):
            di += 1
            continue
        if factor == "all":
            # 기준선: 유니버스 전체 동일가중. 점수가 전부 같으므로 상위 N 을
            # 자르면 종목코드 순으로 잘려 '기준선' 이 되지 못한다.
            picks = [c for _s, c in scored]
        else:
            scored.sort(reverse=True)
            picks = [c for _s, c in scored[:top_n]]

        rets = []
        for code in picks:
            r, cut = trade_return(panel, code, di, di + hold_days,
                                  delisting_loss)
            if r is None:
                continue
            if cut:
                delisted += 1
            rets.append(r)
        if not rets:
            di += 1
            continue
        rounds.append({"date": dates[di], "exit": dates[di + hold_days],
                       "n": len(rets), "ret": st.mean(rets) - fee_pct})
        di += hold_days

    if not rounds:
        # 키를 빼면 호출하는 쪽이 KeyError 로 죽는다. 회차가 0이어도
        # '무슨 일이 있었는지'(쉼/끊김)는 알려줘야 한다.
        return {"rounds": [], "label": label or factor, "n": 0,
                "skipped": skipped, "delisted": delisted}

    rs = [r["ret"] for r in rounds]
    eq, peak, worst = 1.0, 1.0, 0.0
    for r in rs:
        eq *= (1 + r / 100)
        peak = max(peak, eq)
        worst = min(worst, eq / peak - 1)
    res = {
        "label": label or f"{factor}/{hold_days}일/{top_n}종목",
        "rounds": rounds, "n": len(rs), "mean": st.mean(rs),
        "median": st.median(rs), "win": sum(1 for v in rs if v > 0) / len(rs),
        "worst": min(rs), "best": max(rs), "sd": st.pstdev(rs),
        "total": (eq - 1) * 100, "mdd": worst * 100,
        "skipped": skipped, "delisted": delisted,
        "first": rounds[0]["date"], "last": rounds[-1]["exit"],
    }
    if verbose:
        print(fmt(res))
    return res


def fmt(r) -> str:
    if not r.get("rounds"):
        return f"  {r['label']:28} 매매 회차가 없습니다"
    return (f"  {r['label']:28} {r['n']:>3}회 "
            f"평균 {r['mean']:+6.3f}% 중간 {r['median']:+6.3f}% "
            f"승률 {r['win']*100:>4.1f}% "
            f"최악 {r['worst']:+7.2f}% MDD {r['mdd']:+6.1f}% "
            f"누적 {r['total']:+8.1f}%"
            + (f" 쉼{r['skipped']}" if r["skipped"] else "")
            + (f" 끊김{r['delisted']}" if r["delisted"] else ""))


CAUTION = """[결과를 볼 때]
  - 보유 20일이면 5.5년에 리밸런스가 60여 회뿐이다. 회차가 곧 표본이다.
    평균이 0.5%p 달라 보여도 60개 표본에서는 우연히 나올 수 있는 폭이다.
  - 여러 팩터를 나란히 비교한 결과를 맹신하면 안 된다. 6개 중 1등은 항상
    나오고, 그 1등이 다음 5년의 1등이라는 보장은 없다.
  - 보유 중 데이터가 끊긴 종목('끊김')은 마지막 종가로 팔았다고 처리한다.
    실제 상장폐지는 그보다 훨씬 나쁘다. --delisting-loss 50 으로 다시 돌려
    결과가 뒤집히는지 확인할 것.
  - 나쁜날 게이트를 켠 결과는 '전반부에서 정한 기준을 후반부에 적용' 한
    것이라야 의미가 있다. --oos 없이 전체 구간에 맞춘 값은 참고용이다."""


def main():
    ap = argparse.ArgumentParser(description="기본 전략 백테스트")
    ap.add_argument("--factor", default="momentum", choices=FACTORS)
    ap.add_argument("--hold", type=int, default=20, help="보유 거래일")
    ap.add_argument("--top", type=int, default=10, help="종목 수")
    ap.add_argument("--universe", type=int, default=UNIVERSE_SIZE)
    ap.add_argument("--min-price", type=int, default=MIN_PRICE)
    ap.add_argument("--delisting-loss", type=float, default=None,
                    help="보유 중 데이터가 끊긴 종목을 이 손실률(%%)로 처리")
    ap.add_argument("--gate-pct", type=float, default=0.0,
                    help="나쁜날 게이트: 전반부 점수 하위 이 비율은 쉰다 (0=끔)")
    ap.add_argument("--oos", action="store_true",
                    help="후반부만 채점 (게이트 기준은 전반부에서 정함)")
    ap.add_argument("--sweep", action="store_true",
                    help="팩터 x 보유기간 전부 비교")
    args = ap.parse_args()

    dates, panel = load_panel()
    start_di = max(140, LIQUIDITY_DAYS + 2)
    half_di = len(dates) // 2

    gate = None
    if args.gate_pct > 0:
        day_vals = load_day_scores()
        if not day_vals:
            print("[!] market_indicators 데이터가 없어 게이트를 못 만듭니다.")
            return 1
        # 전반부에서만 방향을 정한다. 결과는 '그 날 진입한 회차의 수익률'.
        base = run(dates, panel, factor=args.factor, hold_days=args.hold,
                   top_n=args.top, universe_size=args.universe,
                   min_price=args.min_price, start_di=start_di,
                   delisting_loss=args.delisting_loss, verbose=False)
        train_outcome = {r["date"]: r["ret"] for r in base["rounds"]
                         if r["date"] < dates[half_di]}
        gate = build_day_gate(day_vals, [r["date"] for r in base["rounds"]],
                              train_outcome)
        if gate is None:
            print(f"[!] 전반부 회차가 {len(train_outcome)}개뿐이라 게이트를 "
                  f"만들 수 없습니다 (50개 이상 필요). 보유기간을 줄이거나 "
                  f"--gate-pct 0 으로 돌리세요.")
            return 1

    scope = half_di if args.oos else start_di
    if args.oos:
        print(f"후반부만 채점: {dates[half_di]} 이후\n")

    if args.sweep:
        print(f"{'':30}{'회차':>5} {'평균':>13} {'중간':>12} {'승률':>7} "
              f"{'최악':>9} {'MDD':>8} {'누적':>10}")
        for hold in (5, 20, 60):
            print(f"\n[보유 {hold}거래일]")
            for f in FACTORS:
                run(dates, panel, factor=f, hold_days=hold, top_n=args.top,
                    universe_size=args.universe, min_price=args.min_price,
                    delisting_loss=args.delisting_loss, start_di=scope,
                    label=f"{f}")
    else:
        print(f"{'':30}{'회차':>5} {'평균':>13} {'중간':>12} {'승률':>7} "
              f"{'최악':>9} {'MDD':>8} {'누적':>10}")
        run(dates, panel, factor=args.factor, hold_days=args.hold,
            top_n=args.top, universe_size=args.universe,
            min_price=args.min_price, delisting_loss=args.delisting_loss,
            gate=gate, gate_pct=args.gate_pct, start_di=scope)

    print()
    print(CAUTION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
