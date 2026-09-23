"""
실제로 샀던 종목들(trades.csv)을 그대로 가져와서, "당일청산 대신 5거래일(약
1주일) 들고 있었으면 어떻게 됐을지" 계산하고, 그중 이득 봤을 종목과 손해 봤을
종목의 공통점(하락폭/반등폭 등)을 비교한다 (2026-09-03 추가).

analyze_week_hold_conditions.py와 다른 점: 그건 AI테마 14종목을 기계적으로
쭉 훑은 것이고, 이건 실제로 사용자가(정확히는 이 봇이) 실제 판단으로 산
종목들만 대상으로 한다 - "이미 통과된 신호"들 중에서 결과가 갈린 이유를 본다.

  python analyze_actual_trades_week_hold.py                 # 5거래일(기본) 뒤 기준
  python analyze_actual_trades_week_hold.py --forward-days 5
"""
import argparse
import csv
from datetime import datetime, timedelta

import api_client
from common import LOG_DIR, load_config

TRADES_PATH = LOG_DIR / "trades.csv"

# (2026-09-03) 처음엔 decisions.csv에 남은 매수 사유 텍스트에서 하락폭/반등폭을
# 긁어오려고 했는데, decisions.csv가 8/31부터만 남아있고(그 전 기록은 없음)
# 그 이후 매수는 반대로 forward_days 데이터가 아직 없어서 스킵되는 경우가
# 많아서, 두 조건을 동시에 만족하는 표본이 거의 없었다(전부 "?"로 나옴).
# decisions.csv 보존기간에 의존하지 않도록, 이미 조회한 시세 데이터에서
# strategy.compute_dip_signal과 같은 방식으로 하락폭/반등폭을 직접 계산한다.
DECLINE_LOOKBACK_DAYS = 20
REBOUND_WINDOW_DAYS = 3


def load_actual_buys() -> list[dict]:
    buys = []
    with open(TRADES_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["side"] == "buy":
                buys.append({
                    "timestamp": row["timestamp"], "code": row["code"], "name": row["name"],
                    "price": float(row["price"]), "qty": int(row["qty"]),
                })
    return buys


def compute_forward_returns(cfg, buys: list[dict], forward_days: int) -> list[dict]:
    results = []

    for buy in buys:
        buy_date = buy["timestamp"][:10].replace("-", "")
        # 매수일 기준 하락폭(최근 20거래일 고점 대비) 계산에 필요한 과거 데이터까지
        # 넉넉히 당겨서 한 번에 받는다 (달력일 기준이라 주말/공휴일 감안해 여유있게).
        fetch_start = (datetime.strptime(buy_date, "%Y%m%d") - timedelta(days=45)).strftime("%Y%m%d")
        try:
            rows = api_client.get_daily_prices(cfg, buy["code"], start_date=fetch_start)
        except Exception as e:
            print(f"  [!] {buy['name']}({buy['code']}) {buy_date}: 시세 조회 실패, 건너뜀 ({e})")
            continue
        dates = sorted({r["date"] for r in rows})
        by_date = {r["date"]: r for r in rows}
        if buy_date not in dates:
            print(f"  [!] {buy['name']}({buy['code']}) {buy_date}: 그날 일봉이 없음, 건너뜀 (상장폐지/거래정지 등 가능)")
            continue
        idx = dates.index(buy_date)
        if idx < DECLINE_LOOKBACK_DAYS:
            print(f"  [!] {buy['name']}({buy['code']}) {buy_date}: 하락폭 계산에 필요한 과거 데이터 부족, 건너뜀")
            continue
        if idx + forward_days >= len(dates):
            print(f"  [!] {buy['name']}({buy['code']}) {buy_date}: {forward_days}거래일 뒤 데이터가 아직 없음, 건너뜀")
            continue

        window20 = dates[idx - DECLINE_LOOKBACK_DAYS: idx + 1]
        recent_high = max(by_date[h]["high"] for h in window20)
        drop_pct = (buy["price"] - recent_high) / recent_high * 100

        window3 = dates[max(0, idx - REBOUND_WINDOW_DAYS + 1): idx + 1]
        short_low = min(by_date[h]["low"] for h in window3)
        rebound_pct = (buy["price"] - short_low) / short_low * 100 if short_low > 0 else None

        fwd_date = dates[idx + forward_days]
        fwd_price = by_date[fwd_date]["close"]
        fwd_return_pct = (fwd_price - buy["price"]) / buy["price"] * 100

        weekday = datetime.fromisoformat(buy["timestamp"]).strftime("%a")

        results.append({
            **buy, "fwd_return_pct": fwd_return_pct, "fwd_date": fwd_date,
            "drop_pct": drop_pct, "rebound_pct": rebound_pct, "weekday": weekday,
        })
    return results


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def report(results: list[dict]) -> None:
    if not results:
        print("계산된 표본이 없습니다.")
        return

    wins = [r for r in results if r["fwd_return_pct"] > 0]
    losses = [r for r in results if r["fwd_return_pct"] <= 0]
    print(f"\n=== 실제 매수 {len(results)}건을 1주일 보유로 재계산 ===")
    print(f"이득 {len(wins)}건 / 손해 {len(losses)}건 (이득 비율 {len(wins)/len(results)*100:.1f}%)")
    print(f"평균 수익률: {_avg([r['fwd_return_pct'] for r in results]):+.2f}%")

    print("\n--- 종목별 상세 ---")
    for r in sorted(results, key=lambda x: x["fwd_return_pct"], reverse=True):
        drop_s = f"{r['drop_pct']:.1f}%" if r["drop_pct"] is not None else "?"
        rebound_s = f"{r['rebound_pct']:+.1f}%" if r["rebound_pct"] is not None else "?"
        print(f"  {r['fwd_return_pct']:+7.2f}%  {r['name']}({r['code']})  "
              f"매수 {r['timestamp'][:10]}({r['weekday']}) @ {r['price']:,.0f} -> {r['fwd_date']} 종가 기준  "
              f"[하락폭 {drop_s}, 반등폭 {rebound_s}]")

    print("\n--- 이득 그룹 vs 손해 그룹 평균 비교 (표본이 적어 참고용) ---")
    for label, group in [("이득", wins), ("손해", losses)]:
        n = len(group)
        avg_drop = _avg([r["drop_pct"] for r in group])
        avg_rebound = _avg([r["rebound_pct"] for r in group])
        print(f"  {label}({n}건): 평균 하락폭 "
              + (f"{avg_drop:.1f}%" if avg_drop is not None else "?")
              + ", 평균 반등폭 "
              + (f"{avg_rebound:+.1f}%" if avg_rebound is not None else "?"))

    from collections import Counter
    print("\n--- 요일별 (표본이 적으니 경향만 참고) ---")
    for label, group in [("이득", wins), ("손해", losses)]:
        c = Counter(r["weekday"] for r in group)
        print(f"  {label}: {dict(c)}")

    print(
        "\n참고: 표본이 적으면(특히 그룹별로 10건 미만) 이 비교 자체가 우연에 크게 좌우됩니다. "
        "숫자 차이가 크더라도 바로 규칙으로 확정하지 말고, 방향성 참고 정도로만 보세요."
    )


def main():
    parser = argparse.ArgumentParser(description="실제 매수 이력을 1주일 보유로 재계산")
    parser.add_argument("--forward-days", type=int, default=5, help="며칠(거래일) 뒤 기준으로 볼지 (기본 5=약1주일)")
    args = parser.parse_args()

    cfg = load_config()
    buys = load_actual_buys()
    print(f"실제 매수 기록 {len(buys)}건 로드. 종목별 {args.forward_days}거래일 뒤 시세 조회 중...")
    results = compute_forward_returns(cfg, buys, args.forward_days)
    report(results)


if __name__ == "__main__":
    main()
