"""선물 신호 검증 - 그리고 '휴일 표본' 이라는 함정 기록.

(2026-09-16) 열세 번째 가설이었다. 논리는 이랬다.

  지금까지 열두 번 막힌 이유는 시차다. 나쁜 날은 예측되는데(시험 구간 상관
  0.26~0.33) 그 예측되는 부분이 전부 시가 갭에 들어가 버려서, 시가에 사는
  사람은 못 먹는다. 종가대비 +0.317% / 시가대비 -0.052%.

  그런데 미국 지수 선물은 한국 장중에도 거래된다. 한국시간 14시 봉까지 보면
  한국 종가(15:30) 전에 신호가 확정된다. 즉 '종가에 사서 갭을 먹는' 게
  원리적으로 가능하다. 이게 시차 벽을 우회하는 유일한 경로였다.

결과: 안 된다. 그런데 안 되는 방식이 기록해둘 만하다.

1) 처음 돌렸을 때
     ES=F 다음날 갭 상관 +0.184  (전반부 +0.169 / 후반부 +0.213)
     NQ=F 다음날 갭 상관 +0.213  (전반부 +0.191 / 후반부 +0.236)
   열두 번 중 처음으로 분할 검증을 통과했다.

2) 그런데 표본에 '한국 휴일' 이 섞여 있었다.
   선물은 한국 공휴일에도 거래된다. 그런 날은 한국 종가가 없으니 살 수가
   없다. 게다가 휴일 동안 선물에는 미국장 여러 날치 움직임이 쌓이고, 그게
   다음 한국 거래일 갭에 한꺼번에 반영된다. 관계는 진짜지만 매매는 불가능한
   관계다.

3) 신호일이 한국 거래일인 경우만 남기면 (607일 -> 473일)
     ES=F 다음날 갭 상관 +0.184 -> +0.019
     NQ=F 다음날 갭 상관 +0.213 -> +0.049
   신호가 사실상 전부 사라진다. 즉 1)의 상관은 못 쓰는 날이 만든 것이었다.

4) 수수료까지 넣어 매매로 환산하면 12개 설정 전부 필터가 더 나쁘다.
   (신호일 종가 매수, 왕복 0.21%, 동일가중)
     하위20% 제외 /  1일 보유: 전체 -0.165% -> 필터 -0.197%
     하위20% 제외 /  5일 보유: 전체 +0.051% -> 필터 -0.079%
     하위20% 제외 / 20일 보유: 전체 +0.902% -> 필터 +0.670%
     하위40% 제외로 더 세게 걸러도 전부 더 나빠진다.
   전·후반부 모두 같은 방향이라, 우연이 아니라 일관되게 해롭다.

5) 새 정보였는지도 따로 봤다. 선물 장중 변화는 그날 한국 시장 움직임과
   상관 +0.24~0.29 로 겹친다. 한국 당일 움직임을 회귀로 제거한 잔차만
   써도 다음날 갭 상관은 +0.03~0.06 이다. 남는 게 없다.

교훈: 표본에 '실제로는 매매할 수 없는 날' 이 섞이면 상관이 부풀고, 분할
검증마저 통과한다. 분할 검증은 과최적화는 잡아주지만 표본 자체가 잘못된
것은 잡아주지 못한다. 앞으로 어떤 신호든 "그 날 정말 주문을 낼 수 있었나"
를 먼저 확인한다.

실행:
    python analyze_futures.py
"""
import argparse
import bisect
import statistics as st
import sys

import yearly_csv
from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
FEE_ROUND_TRIP_PCT = 0.21
MIN_STOCKS_PER_DAY = 30


def load_market() -> tuple[dict, dict]:
    """일별 동일가중 결과와 종목별 종가를 돌려준다.

    kr[날짜] = (갭%, 시가대비%, 종가대비%)  - 전일 종가 기준
    """
    byday: dict[str, dict[str, tuple[float, float]]] = {}
    for (date, code), r in yearly_csv.load_rows(
            DATA_DIR, "krx_panel", key_fields=("date", "code")).items():
        try:
            o, c = float(r["open"]), float(r["close"])
        except (TypeError, ValueError):
            continue
        if o > 0 and c > 0:
            byday.setdefault(date, {})[code] = (o, c)

    dates = sorted(byday)
    kr = {}
    for i in range(1, len(dates)):
        prev, cur = dates[i - 1], dates[i]
        pm = byday[prev]
        gap, o2c, c2c = [], [], []
        for code, (o, c) in byday[cur].items():
            p = pm.get(code)
            if not p:
                continue
            gap.append((o / p[1] - 1) * 100)
            o2c.append((c / o - 1) * 100)
            c2c.append((c / p[1] - 1) * 100)
        if len(gap) >= MIN_STOCKS_PER_DAY:
            kr[cur] = (st.mean(gap), st.mean(o2c), st.mean(c2c))
    return kr, byday


def load_futures() -> dict:
    fut: dict[str, dict[str, float]] = {}
    for (date, ticker), r in yearly_csv.load_rows(
            DATA_DIR, "us_futures", key_fields=("date", "ticker")).items():
        try:
            fut.setdefault(ticker, {})[date] = float(r["kr_session_chg"])
        except (TypeError, ValueError):
            continue
    return fut


def corr(xs, ys, min_n=10):
    if len(xs) < min_n:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if not dx or not dy:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (dx * dy)


def residual(xs, controls):
    """controls 로 xs 를 회귀해 남은 잔차. '새 정보인가' 를 보는 데 쓴다."""
    mc, mx = st.mean(controls), st.mean(xs)
    sxx = sum((v - mc) ** 2 for v in controls)
    b = (sum((a - mx) * (v - mc) for a, v in zip(xs, controls)) / sxx
         if sxx else 0.0)
    return [a - (mx + b * (v - mc)) for a, v in zip(xs, controls)]


def hold_return(byday, kr_dates, start_date, hold_days):
    """신호일 종가 매수 -> hold_days 거래일 뒤 종가 매도, 동일가중, 수수료 차감."""
    i = bisect.bisect_right(kr_dates, start_date) + hold_days - 1
    if not 0 <= i < len(kr_dates):
        return None
    s0, s1 = byday.get(start_date), byday.get(kr_dates[i])
    if not s0 or not s1:
        return None
    rs = [(s1[c][1] / s0[c][1] - 1) * 100
          for c in s0 if c in s1 and s0[c][1] > 0]
    if len(rs) < MIN_STOCKS_PER_DAY:
        return None
    return st.mean(rs) - FEE_ROUND_TRIP_PCT


def analyze(tradeable_only: bool = True, verbose: bool = True) -> dict:
    kr, byday = load_market()
    kr_dates = sorted(kr)
    # 매매 가능 판정은 '결과를 계산할 수 있는 날' 이 아니라 '실제 거래일' 로
    # 해야 한다. 첫 거래일은 전일이 없어 kr 에 없지만 종가는 있으므로 살 수
    # 있다. 이걸 휴일로 세면 표본이 틀린다.
    trade_days = set(byday)
    fut = load_futures()

    def next_kr(d):
        i = bisect.bisect_right(kr_dates, d)
        return kr_dates[i] if i < len(kr_dates) else None

    out = {}
    for ticker, series in sorted(fut.items()):
        rows, holiday = [], 0
        for d, chg in sorted(series.items()):
            if d not in trade_days:
                holiday += 1
                if tradeable_only:
                    continue
            nd = next_kr(d)
            if nd is None:
                continue
            same_day = kr[d][2] if d in kr else None
            rows.append((d, chg, same_day, kr[nd]))
        if not rows:
            continue
        xs = [r[1] for r in rows]
        gap = [r[3][0] for r in rows]
        o2c = [r[3][1] for r in rows]
        c2c = [r[3][2] for r in rows]
        res = {"n": len(rows), "holiday_days": holiday,
               "gap": corr(xs, gap), "o2c": corr(xs, o2c), "c2c": corr(xs, c2c)}
        # 한국 당일 움직임을 제거해도 남는가
        have_same = [(r[1], r[2], r[3][0]) for r in rows if r[2] is not None]
        if len(have_same) >= 30:
            xf = [a for a, _b, _c in have_same]
            xk = [b for _a, b, _c in have_same]
            gg = [c for _a, _b, c in have_same]
            res["same_day_gap"] = corr(xk, gg)
            res["overlap"] = corr(xf, xk)
            res["residual_gap"] = corr(residual(xf, xk), gg)
        # 수수료 후 매매 환산
        thresholds = sorted(xs)
        res["trades"] = {}
        for pct in (0.20, 0.40):
            thr = thresholds[int(len(thresholds) * pct)]
            for hold in (1, 5, 20):
                allr, filt = [], []
                for d, chg, _sd, _nx in rows:
                    r = hold_return(byday, kr_dates, d, hold)
                    if r is None:
                        continue
                    allr.append(r)
                    if chg >= thr:
                        filt.append(r)
                if allr and filt:
                    res["trades"][(pct, hold)] = (
                        len(allr), st.mean(allr), len(filt), st.mean(filt))
        out[ticker] = res

    if verbose:
        _report(out, tradeable_only)
    return out


def _report(out, tradeable_only):
    scope = ("신호일이 한국 거래일인 경우만" if tradeable_only
             else "선물 거래일 전부 (한국 휴일 포함 - 매매 불가능)")
    print(f"=== 한국 장중(09~14시) 선물 변화 -> 다음 한국 거래일 ===")
    print(f"    표본: {scope}\n")
    print(f"{'선물':8} {'표본':>5} {'갭':>8} {'시가~종가':>10} {'종가~종가':>10}")
    for t, r in sorted(out.items()):
        print(f"{t:8} {r['n']:>5} {r['gap']:>8.3f} {r['o2c']:>10.3f} "
              f"{r['c2c']:>10.3f}")
    print()
    for t, r in sorted(out.items()):
        if "residual_gap" not in r:
            continue
        print(f"[{t}] 새 정보인가")
        print(f"   선물 -> 다음날 갭            {r['gap']:+.3f}")
        print(f"   한국 당일 움직임 -> 다음날 갭 {r['same_day_gap']:+.3f}")
        print(f"   선물 <-> 한국 당일 (중복도)   {r['overlap']:+.3f}")
        print(f"   한국 당일 제거한 잔차 -> 갭   {r['residual_gap']:+.3f}")
    print()
    print(f"=== 수수료 후 (신호일 종가 매수, 왕복 {FEE_ROUND_TRIP_PCT}%) ===")
    for t, r in sorted(out.items()):
        print(f"[{t}]")
        for (pct, hold), (na, ma, nf, mf) in sorted(r["trades"].items()):
            print(f"  하위{int(pct*100)}% 제외 / {hold:>2}일 보유: "
                  f"전체 {na:>3}회 {ma:+.3f}%  ->  필터 {nf:>3}회 {mf:+.3f}%  "
                  f"(차이 {mf - ma:+.3f}%p)")
    print()
    print(CAUTION)


CAUTION = """[결과를 볼 때]
  - 1시간봉은 약 2년치까지만 받을 수 있어 표본이 473거래일이다. 다른 검증에
    쓴 1,376일의 3분의 1이다.
  - 이 아이디어("미국 선물 보고 판단한다")는 국내에서 널리 쓰인다. 널리
    쓰인다는 건 이미 가격에 반영돼 있을 수 있다는 뜻이다.
  - --include-holidays 로 돌리면 상관이 부풀어 보인다. 그 날은 한국 종가가
    없어서 주문을 낼 수 없는 날이다. 비교용으로만 쓸 것."""


def main():
    ap = argparse.ArgumentParser(
        description="한국 장중 선물 신호 -> 다음 한국 거래일 검증")
    ap.add_argument("--include-holidays", action="store_true",
                    help="한국 휴일도 표본에 넣는다 (매매 불가능. 함정 재현용)")
    args = ap.parse_args()
    analyze(tradeable_only=not args.include_holidays)
    return 0


if __name__ == "__main__":
    sys.exit(main())
