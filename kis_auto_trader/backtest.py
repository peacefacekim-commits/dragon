"""쌓아둔 일봉 패널 위에서 전략을 돌려보는 백테스트 (API 호출 없음).

(2026-09-13 신설) 이 파일이 새 구조의 핵심이다. 패널(panel.py)만 쌓여 있으면
여기서 팩터·보유기간·손절폭·종목 수를 마음대로 바꿔가며 같은 데이터에 몇 번이든
다시 돌려볼 수 있다. 전략을 바꿀 때마다 처음부터 다시 모을 필요가 없다.

미래 정보를 쓰지 않기 위해 지킨 것 (이게 틀리면 결과 전체가 무의미해진다):

  - 팩터는 재조정일 d 의 종가까지만 써서 계산한다.
  - 매수는 d 의 종가가 아니라 '그 다음 거래일 시가'에 한다. d 종가로 사면
    "그날 종가를 보고 그날 종가에 산다"가 되어 현실에서 불가능한 거래가 된다.
  - 매도도 같은 이유로 보유기간이 끝난 다음 거래일 시가에 한다.
  - 손절은 그날의 저가가 손절선 밑으로 내려갔는지로 판단하고, 체결가는
    손절선으로 잡는다 (갭하락이면 그 날 시가로 - 손절선보다 불리한 쪽).

사용법:
  python backtest.py                       # 기본 조합 몇 개를 비교
  python backtest.py --sweep               # 조합을 쓸어서 표로 출력
  python backtest.py --factor momentum --hold 20 --top 10 --stop -8
"""
import argparse
import bisect
import statistics
from dataclasses import dataclass

import panel as panel_mod

FACTORS = ["momentum", "trend", "low_vol", "reversal"]


# slots=True 가 핵심이다. 생존편향을 걷어내려고 유니버스를 1,813종목(약 226만
# 행)으로 늘렸더니, 일반 dataclass 로는 로드에 2.6GB 를 썼다 - 사용자 PC에서
# 터질 수 있는 크기다. slots 를 주면 인스턴스마다 __dict__ 를 안 만들어서
# 메모리가 크게 줄어든다. (2026-09-15)
@dataclass(slots=True)
class Bar:
    date: str
    open: float | None
    high: float
    low: float
    close: float
    volume: int


class Panel:
    """백테스트가 쓰기 좋은 형태로 정리한 패널."""

    def __init__(self, by_code: dict):
        bars_by_code: dict[str, list[Bar]] = {}
        for code, rows in by_code.items():
            bars = []
            for r in rows:
                try:
                    close = float(r["close"])
                    if close <= 0:
                        continue
                    bars.append(Bar(
                        date=r["date"],
                        open=float(r["open"]) if r.get("open") not in ("", None) else None,
                        high=float(r["high"]), low=float(r["low"]),
                        close=close, volume=int(float(r.get("volume") or 0)),
                    ))
                except (ValueError, KeyError):
                    continue
            if bars:
                bars_by_code[code] = bars
        self._finalize(bars_by_code)

    def _finalize(self, bars_by_code: dict) -> None:
        for bs in bars_by_code.values():
            bs.sort(key=lambda b: b.date)
        self.bars = bars_by_code
        self.dates_of = {c: [b.date for b in bs] for c, bs in bars_by_code.items()}
        all_dates = set()
        for ds in self.dates_of.values():
            all_dates.update(ds)
        self.dates: list[str] = sorted(all_dates)

    @classmethod
    def load(cls, codes: list[str] | None = None) -> "Panel":
        """CSV에서 곧바로 Bar 로 읽어들인다.

        (2026-09-15) 원래는 panel.load_by_code() 로 {(날짜,종목): {필드8개}} 딕셔너리를
        먼저 만들고 그걸 Bar 로 바꿨다. 79종목일 때는 문제가 없었는데, 생존편향을
        걷어내려고 1,813종목(약 226만 행)으로 늘리자 그 중간 딕셔너리만으로
        2.5GB를 썼다. 중간 단계를 없애고 한 줄씩 바로 Bar 로 만든다.
        """
        import csv as _csv

        import yearly_csv
        wanted = set(codes) if codes else None
        bars_by_code: dict[str, list[Bar]] = {}

        for path in yearly_csv.paths(panel_mod.DATA_DIR, panel_mod.PREFIX):
            with open(path, encoding="utf-8-sig", newline="") as f:
                reader = _csv.reader(f)
                header = next(reader, None)
                if not header:
                    continue
                try:
                    i_date, i_code = header.index("date"), header.index("code")
                    i_o, i_h = header.index("open"), header.index("high")
                    i_l, i_c = header.index("low"), header.index("close")
                    i_v = header.index("volume")
                except ValueError:
                    print(f"[!] {path.name} 의 컬럼이 예상과 다릅니다: {header}")
                    continue
                for row in reader:
                    if len(row) <= i_v:
                        continue
                    code = row[i_code]
                    if wanted is not None and code not in wanted:
                        continue
                    try:
                        close = float(row[i_c])
                        if close <= 0:
                            continue
                        bar = Bar(
                            date=row[i_date],
                            open=float(row[i_o]) if row[i_o] not in ("", None) else None,
                            high=float(row[i_h]), low=float(row[i_l]),
                            close=close, volume=int(float(row[i_v] or 0)),
                        )
                    except ValueError:
                        continue
                    bars_by_code.setdefault(code, []).append(bar)

        obj = cls.__new__(cls)
        obj._finalize(bars_by_code)
        return obj

    def pos_at(self, code: str, date: str) -> int:
        """code 의 봉 중 date 이하인 마지막 봉의 위치. 없으면 -1."""
        ds = self.dates_of.get(code)
        if not ds:
            return -1
        return bisect.bisect_right(ds, date) - 1

    def pos_after(self, code: str, date: str) -> int:
        """date 보다 뒤인 첫 봉의 위치. 없으면 -1."""
        ds = self.dates_of.get(code)
        if not ds:
            return -1
        i = bisect.bisect_right(ds, date)
        return i if i < len(ds) else -1

    def entry_price(self, code: str, i: int) -> float | None:
        """i 번째 봉에서 실제로 체결됐다고 볼 가격 - 시가가 있으면 시가."""
        b = self.bars[code][i]
        return b.open if b.open else b.close


# ---------------------------------------------------------------- 팩터

def factor_score(p: Panel, code: str, date: str, factor: str,
                 lookback: int, skip: int, vol_days: int) -> float | None:
    """재조정일 date 기준 팩터 점수. 클수록 좋은 종목. 계산 불가면 None.

    date 이하의 봉만 쓴다 - 미래 정보 차단.
    """
    i = p.pos_at(code, date)
    if i < 0:
        return None
    bars = p.bars[code]

    if factor == "momentum":
        # 최근 skip 일은 빼고 본다 (단기 반전 효과를 피하는 표준 12-1 방식).
        end = i - skip
        start = end - lookback
        if start < 0 or end < 0:
            return None
        if bars[start].close <= 0:
            return None
        return bars[end].close / bars[start].close - 1.0

    if factor == "reversal":
        s = factor_score(p, code, date, "momentum", lookback, skip, vol_days)
        return None if s is None else -s

    if factor == "trend":
        if i - lookback + 1 < 0:
            return None
        window = [b.close for b in bars[i - lookback + 1: i + 1]]
        ma = sum(window) / len(window)
        if ma <= 0:
            return None
        return bars[i].close / ma - 1.0

    if factor == "low_vol":
        if i - vol_days < 0:
            return None
        closes = [b.close for b in bars[i - vol_days: i + 1]]
        rets = [closes[k] / closes[k - 1] - 1.0 for k in range(1, len(closes))
                if closes[k - 1] > 0]
        if len(rets) < 2:
            return None
        sd = statistics.pstdev(rets)
        return -sd  # 변동성이 낮을수록 점수가 높게

    raise ValueError(f"모르는 팩터: {factor}")


# ---------------------------------------------------------------- 한 종목 보유

def hold_return(p: Panel, code: str, signal_date: str, hold_days: int,
                stop_loss_pct: float | None) -> float | None:
    """signal_date 다음 거래일 시가에 사서 hold_days 거래일 뒤 시가에 판다.
    손절선이 있으면 그 전에 잘린다. 수수료 제외한 총수익률(소수)."""
    ei = p.pos_after(code, signal_date)
    if ei < 0:
        return None
    bars = p.bars[code]
    buy = p.entry_price(code, ei)
    if not buy or buy <= 0:
        return None

    exit_i = min(ei + hold_days, len(bars) - 1)
    if exit_i <= ei:
        return None  # 팔 날이 아직 없음 (패널 끝) - 집계에서 뺀다

    if stop_loss_pct is not None:
        stop = buy * (1 + stop_loss_pct / 100.0)
        for k in range(ei, exit_i + 1):
            if bars[k].low <= stop:
                # 갭하락으로 시가부터 손절선 밑이면 시가에 체결된 걸로 본다
                # (손절선에 체결됐다고 치면 실제보다 좋게 나온다).
                fill = bars[k].open if (bars[k].open and bars[k].open < stop) else stop
                return fill / buy - 1.0

    return p.entry_price(code, exit_i) / buy - 1.0


# ---------------------------------------------------------------- 백테스트

@dataclass
class Result:
    label: str
    periods: int
    trades: int
    mean_period_ret: float
    win_rate: float
    cumulative: float
    max_drawdown: float
    bench_mean: float
    bench_cumulative: float

    def line(self) -> str:
        return (f"{self.label:38s} 기간{self.periods:4d} 거래{self.trades:5d} "
                f"평균{self.mean_period_ret * 100:+6.2f}% 승률{self.win_rate * 100:5.1f}% "
                f"누적{self.cumulative * 100:+8.1f}% MDD{self.max_drawdown * 100:5.1f}% "
                f"| 벤치평균{self.bench_mean * 100:+6.2f}% 누적{self.bench_cumulative * 100:+8.1f}%")


def run(p: Panel, factor: str = "momentum", rebalance_days: int = 20,
        hold_days: int = 20, top_n: int = 10, stop_loss_pct: float | None = None,
        lookback: int = 120, skip: int = 5, vol_days: int = 60,
        fee_pct: float = 0.21, min_candidates: int | None = None,
        label: str | None = None) -> Result | None:
    """팩터 상위 top_n 종목을 rebalance_days 마다 새로 골라 hold_days 동안 보유.

    fee_pct 는 왕복 비용(매수수수료+매도수수료+거래세) 합계 %.
    벤치마크는 같은 시점에 '조건을 만족하는 전 종목을 똑같이 나눠 산' 경우다 -
    팩터가 아무 일도 안 했을 때와 비교하기 위한 것.
    """
    # (2026-09-14 버그수정) min_candidates 기본값이 20 으로 박혀 있어서, 유니버스가
    # 아직 11종목이던 실제 패널에서는 모든 재조정일이 "후보 부족"으로 건너뛰어지고
    # 결과가 통째로 안 나왔다. 게다가 실패 메시지가 "패널 기간이 짧다"고 엉뚱한
    # 원인을 가리켜서 한참 헤맸다. 이제 매수 종목 수에 맞춰 자동으로 정한다.
    if min_candidates is None:
        min_candidates = max(top_n * 2, 5)

    dates = p.dates
    if len(dates) < lookback + hold_days + 5:
        return None

    period_rets, bench_rets = [], []
    trades = 0

    # 재조정일: 팩터 계산에 필요한 과거가 쌓인 뒤부터, 보유기간이 끝날 수
    # 있는 날까지만.
    first = lookback + skip + 1
    last = len(dates) - hold_days - 2
    for di in range(first, last, rebalance_days):
        d = dates[di]
        scored = []
        for code in p.bars:
            s = factor_score(p, code, d, factor, lookback, skip, vol_days)
            if s is not None:
                scored.append((s, code))
        if len(scored) < min_candidates:
            continue

        scored.sort(reverse=True)
        picked = [c for _, c in scored[:top_n]]

        rets = [r for r in (hold_return(p, c, d, hold_days, stop_loss_pct) for c in picked)
                if r is not None]
        if not rets:
            continue
        trades += len(rets)
        period_rets.append(sum(rets) / len(rets) - fee_pct / 100.0)

        all_rets = [r for r in (hold_return(p, c, d, hold_days, None) for _, c in scored)
                    if r is not None]
        bench_rets.append((sum(all_rets) / len(all_rets) - fee_pct / 100.0) if all_rets else 0.0)

    if not period_rets:
        return None

    def compound(rs):
        acc = 1.0
        for r in rs:
            acc *= (1 + r)
        return acc - 1.0

    peak, mdd, acc = 1.0, 0.0, 1.0
    for r in period_rets:
        acc *= (1 + r)
        peak = max(peak, acc)
        mdd = max(mdd, (peak - acc) / peak)

    sl = "없음" if stop_loss_pct is None else f"{stop_loss_pct:g}%"
    return Result(
        label=label or f"{factor} 보유{hold_days}일 상위{top_n} 손절{sl}",
        periods=len(period_rets), trades=trades,
        mean_period_ret=sum(period_rets) / len(period_rets),
        win_rate=sum(1 for r in period_rets if r > 0) / len(period_rets),
        cumulative=compound(period_rets), max_drawdown=mdd,
        bench_mean=sum(bench_rets) / len(bench_rets) if bench_rets else 0.0,
        bench_cumulative=compound(bench_rets),
    )


CAUTION = """
[결과를 볼 때]
- 여기 나오는 '기간' 수가 곧 실질 표본 수다. 거래 건수가 몇백 건이어도 같은
  달에 산 종목들은 같이 움직이므로 서로 독립이 아니다. 기간이 30~40개면
  방향 참고까지고, 확정 근거로 쓰기에는 모자란다.
- 조합을 여러 개 돌리면 그중 제일 좋은 건 우연히 좋았을 가능성이 항상 있다.
  1등이 뭔지보다, 인접한 설정들(보유 15/20/25일 등)이 같은 방향인지를 봐라.
- 유니버스가 '2026년 9월에 거래가 활발했던 종목'으로 만들어졌다는 편향이
  그대로 들어있다(universe.py 참고). 그래서 과거 성적은 실제보다 좋게 나온다.
- 여기서 고른 전략은 그 다음에 몇 달간 앞으로(가상매매로) 한 번 더 통과시켜야
  한다. 과거에 맞춘 것이 미래에도 되는지는 별개 문제다.
"""


def main():
    ap = argparse.ArgumentParser(description="패널 데이터 위에서 전략 백테스트")
    ap.add_argument("--factor", choices=FACTORS, default=None)
    ap.add_argument("--hold", type=int, default=20, help="보유 거래일 수 (20일 ~ 한 달)")
    ap.add_argument("--rebalance", type=int, default=None, help="재조정 간격(거래일), 기본=보유기간")
    ap.add_argument("--top", type=int, default=10, help="매수 종목 수")
    ap.add_argument("--stop", type=float, default=None, help="손절 %% (예: -8). 생략하면 손절 없음")
    ap.add_argument("--lookback", type=int, default=120, help="팩터 계산 창(거래일)")
    ap.add_argument("--sweep", action="store_true", help="여러 조합을 쓸어서 비교")
    ap.add_argument("--source", default=None,
                    help="이 출처로 들어온 유니버스 종목만 쓴다 "
                         "(예: 거래대금상위). 종목 선정 출처가 결과를 바꾸는지 "
                         "비교할 때. 생략하면 패널에 있는 전 종목")
    args = ap.parse_args()

    only = None
    if args.source:
        import universe
        only = universe.codes(source=args.source)
        if not only:
            import universe as u
            print(f"출처 '{args.source}' 로 들어온 종목이 없습니다. "
                  f"지금 있는 출처: {u.source_counts()}")
            return

    p = Panel.load(only)
    if not p.bars:
        print("패널 데이터가 없습니다. 먼저 collect_daily.py 를 실행하세요.")
        return
    src = f", 출처 '{args.source}' 만" if args.source else ""
    print(f"패널: {len(p.bars)}종목, {len(p.dates)}거래일 "
          f"({p.dates[0]}~{p.dates[-1]}){src}\n")

    results = []
    if args.sweep:
        for factor in FACTORS:
            for hold in (5, 20, 60):
                for stop in (None, -8.0):
                    r = run(p, factor=factor, rebalance_days=hold, hold_days=hold,
                            top_n=args.top, stop_loss_pct=stop, lookback=args.lookback)
                    if r:
                        results.append(r)
    else:
        factors = [args.factor] if args.factor else FACTORS
        for factor in factors:
            r = run(p, factor=factor, rebalance_days=args.rebalance or args.hold,
                    hold_days=args.hold, top_n=args.top, stop_loss_pct=args.stop,
                    lookback=args.lookback)
            if r:
                results.append(r)

    if not results:
        # 왜 안 나왔는지 원인을 구분해서 알려준다 (예전엔 항상 "기간이 짧다"고만
        # 말해서, 실제 원인이 종목 수 부족일 때 엉뚱한 데를 보게 만들었다).
        need_days = args.lookback + args.hold + 5
        print("돌릴 수 있는 조합이 없습니다.")
        if len(p.dates) < need_days:
            print(f"  원인: 패널 기간 부족 - 지금 {len(p.dates)}거래일, "
                  f"최소 {need_days}거래일 필요 (--lookback 을 줄여보세요)")
        else:
            print(f"  원인: 종목 수 부족 - 지금 {len(p.bars)}종목. "
                  f"매수 {args.top}종목을 고르려면 후보가 최소 "
                  f"{max(args.top * 2, 5)}종목은 있어야 합니다.")
            print(f"  유니버스가 목표치까지 차면 해결됩니다 (python universe.py 로 확인). "
                  f"지금 당장 보려면 --top 을 줄이세요 (예: --top 2).")
        return

    for r in sorted(results, key=lambda r: -r.mean_period_ret):
        print(r.line())
    print(CAUTION)


if __name__ == "__main__":
    main()
