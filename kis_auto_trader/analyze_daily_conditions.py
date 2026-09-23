"""
날짜별 실제 매매 순손익과, 그날/전날 코스피·코스닥 등락률의 관계를 본다
(2026-09-03 추가).

계기: logs/market_history.csv로 요일별 패턴을 봤더니 월요일만 4번 다 이득
이었는데, 그 로그가 8/28부터만 남아있어서 코스닥 등락률과 엮은 분석은
표본이 4일뿐이었다. market_history.csv(회차마다 쌓은 스냅샷)에 의존하지
않고, api_client.get_index_daily_prices()로 코스피/코스닥 실제 과거 일봉을
직접 받아오면 거래 기록 전체(7/29~) 기간을 다 커버할 수 있다.

  python analyze_daily_conditions.py
"""
import csv
from collections import defaultdict
from datetime import datetime

import api_client
from common import LOG_DIR, load_config

TRADES_PATH = LOG_DIR / "trades.csv"


def load_daily_pnl() -> dict:
    """날짜(YYYY-MM-DD) -> (순손익 합계, 매도건수)."""
    pnl = defaultdict(float)
    count = defaultdict(int)
    with open(TRADES_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["side"] == "sell" and row.get("realized_pnl"):
                try:
                    p = float(row["realized_pnl"])
                except ValueError:
                    continue
                d = row["timestamp"][:10]
                pnl[d] += p
                count[d] += 1
    return {d: (pnl[d], count[d]) for d in pnl}


def main():
    cfg = load_config()
    daily = load_daily_pnl()
    if not daily:
        print("거래 기록이 없습니다.")
        return

    trade_dates = sorted(daily.keys())
    start = trade_dates[0].replace("-", "")
    end = trade_dates[-1].replace("-", "")
    # 등락률 계산에 "그 전 거래일"이 필요하니 앞쪽으로 여유있게 당겨서 조회
    fetch_start = (datetime.strptime(start, "%Y%m%d")).strftime("%Y%m%d")

    print(f"코스피/코스닥 실제 일봉 조회 중 ({trade_dates[0]} ~ {trade_dates[-1]}, 앞쪽 여유 포함)...")
    kospi_rows = api_client.get_index_daily_prices(cfg, "0001", start_date="20260701", end_date=end)
    kosdaq_rows = api_client.get_index_daily_prices(cfg, "1001", start_date="20260701", end_date=end)
    kospi_by_date = {r["date"]: r["close"] for r in kospi_rows}
    kosdaq_by_date = {r["date"]: r["close"] for r in kosdaq_rows}
    kospi_dates = sorted(kospi_by_date.keys())
    kosdaq_dates = sorted(kosdaq_by_date.keys())

    def prior_change(by_date: dict, dates_sorted: list, d: str):
        if d not in dates_sorted:
            return None
        idx = dates_sorted.index(d)
        if idx < 1:
            return None
        prev = by_date[dates_sorted[idx - 1]]
        cur = by_date[dates_sorted[idx]]
        return (cur - prev) / prev * 100

    rows = []
    for d in trade_dates:
        pnl, n = daily[d]
        d8 = d.replace("-", "")
        wd = datetime.fromisoformat(d).strftime("%a")
        kospi_ch = prior_change(kospi_by_date, kospi_dates, d8)
        kosdaq_ch = prior_change(kosdaq_by_date, kosdaq_dates, d8)
        rows.append({
            "date": d, "weekday": wd, "trades": n, "pnl": pnl,
            "kospi_prior_change": kospi_ch, "kosdaq_prior_change": kosdaq_ch,
        })

    print(f"\n{'날짜':<12}{'요일':<6}{'매도건수':>6}{'순손익':>14}{'전날코스피등락':>14}{'전날코스닥등락':>14}")
    for r in rows:
        kospi_s = f"{r['kospi_prior_change']:+.2f}%" if r["kospi_prior_change"] is not None else "?"
        kosdaq_s = f"{r['kosdaq_prior_change']:+.2f}%" if r["kosdaq_prior_change"] is not None else "?"
        print(f"{r['date']:<12}{r['weekday']:<6}{r['trades']:>6}{r['pnl']:>14,.0f}{kospi_s:>14}{kosdaq_s:>14}")

    good = [r for r in rows if r["pnl"] > 0]
    bad = [r for r in rows if r["pnl"] <= 0]
    print(f"\n이득 본 날 {len(good)}일 / 손해 본 날 {len(bad)}일 (총 {len(rows)}일)")

    def avg(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    print("\n--- 이득 본 날 vs 손해 본 날, 전날 지수 등락률 평균 ---")
    for label, group in [("이득", good), ("손해", bad)]:
        k1 = avg([r["kospi_prior_change"] for r in group])
        k2 = avg([r["kosdaq_prior_change"] for r in group])
        n_tagged = sum(1 for r in group if r["kospi_prior_change"] is not None)
        print(f"  {label}({len(group)}일, 지수데이터 있는 {n_tagged}일): "
              f"전날 코스피 평균 {k1:+.2f}%" if k1 is not None else f"  {label}: 코스피 데이터 없음")
        if k2 is not None:
            print(f"         전날 코스닥 평균 {k2:+.2f}%")

    from collections import Counter
    print("\n--- 요일별 ---")
    for label, group in [("이득", good), ("손해", bad)]:
        c = Counter(r["weekday"] for r in group)
        print(f"  {label}: {dict(c)}")

    print(
        "\n참고: 거래일 수 자체가 26일 안팎으로 적습니다. 방향성 참고 정도로만 보고, "
        "이 결과만으로 요일/시장조건 규칙을 확정하지 마세요."
    )


if __name__ == "__main__":
    main()
