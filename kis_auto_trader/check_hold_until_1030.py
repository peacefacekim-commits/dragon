"""
"10시반 이전에 사고, 팔지 않고 기다렸다가 10시반부터 매도 판단을 시작했다면
어땠을까"를 과거 분봉으로 대략 확인해보는 스크립트. 정확한 백테스트가 아니라
경향 파악용 - 실제 매매에는 전혀 관여하지 않고 조회만 한다.

trades.csv에서 10시반 이전에 매수해서 1만원 이상 손실난 거래들을 찾아서,
각각 KIS 분봉 API(과거 날짜 지원)로 매수시각~10시반 사이 가격 흐름을 가져온다.

사용법: kis_auto_trader 폴더에 넣고 그 폴더에서 실행
  python check_hold_until_1030.py
"""
import csv
from datetime import datetime, time

import common
import api_client

CUTOFF = time(10, 30)
BIG_LOSS_THRESHOLD = -10000


def find_candidates():
    rows = list(csv.DictReader(open(common.TRADE_LOG_PATH, encoding="utf-8-sig")))
    last_buy = {}
    candidates = []
    for r in rows:
        ts = datetime.fromisoformat(r["timestamp"])
        code = r["code"]
        if r["side"] == "buy":
            last_buy[code] = (ts, float(r["price"]), int(r["qty"]))
        elif r["side"] == "sell" and r.get("realized_pnl"):
            buy = last_buy.get(code)
            if buy is None:
                continue
            buy_ts, buy_price, qty = buy
            pnl = float(r["realized_pnl"])
            if buy_ts.time() < CUTOFF and pnl <= BIG_LOSS_THRESHOLD:
                candidates.append({
                    "code": code, "name": r["name"], "date": buy_ts.strftime("%Y%m%d"),
                    "buy_time": buy_ts, "buy_price": buy_price, "qty": qty,
                    "actual_sell_price": float(r["price"]), "actual_pnl": pnl,
                })
    return candidates


def fetch_minute_bars(cfg, code, date_str, anchor_hour="110000"):
    """과거 특정 날짜의 분봉(최대 120개, anchor_hour 기준 이전 데이터)을 가져온다."""
    res = api_client._get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice",
        headers=api_client._headers(cfg, "FHKST03010230"),
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code,
            "FID_INPUT_HOUR_1": anchor_hour,
            "FID_INPUT_DATE_1": date_str,
            "FID_PW_DATA_INCU_YN": "Y",
            "FID_FAKE_TICK_INCU_YN": "",
        },
    )
    body = res.json()
    if body.get("rt_cd") != "0":
        raise RuntimeError(f"분봉 조회 실패: {body.get('msg1')}")
    rows = body.get("output2", [])
    parsed = [
        {
            "time": r["stck_cntg_hour"],  # HHMMSS
            "price": float(r["stck_prpr"]),
        }
        for r in rows if r.get("stck_cntg_hour")
    ]
    parsed.sort(key=lambda r: r["time"])
    return parsed


def main():
    cfg = common.load_config()
    candidates = find_candidates()
    print(f"10시반 이전 매수 + 1만원 이상 손실 거래: {len(candidates)}건\n")

    results = []
    for c in candidates:
        try:
            bars = fetch_minute_bars(cfg, c["code"], c["date"])
        except Exception as e:
            print(f"[!] {c['name']}({c['code']}, {c['date']}) 분봉 조회 실패, 건너뜀: {e}")
            continue

        buy_hhmmss = c["buy_time"].strftime("%H%M%S")
        window = [b for b in bars if buy_hhmmss <= b["time"] <= "103000"]
        if not window:
            print(f"[!] {c['name']}({c['code']}, {c['date']}) - 매수시각~10:30 구간 분봉 없음 "
                  f"(보관 기간 밖이거나 데이터 없음), 건너뜀")
            continue

        low = min(b["price"] for b in window)
        at_1030 = window[-1]["price"]  # 10:30에 가장 가까운 마지막 값
        pct_at_1030 = (at_1030 - c["buy_price"]) / c["buy_price"] * 100
        pct_low = (low - c["buy_price"]) / c["buy_price"] * 100
        hypothetical_pnl_at_1030 = (at_1030 - c["buy_price"]) * c["qty"]

        results.append({
            **c, "low": low, "at_1030": at_1030,
            "pct_at_1030": pct_at_1030, "pct_low": pct_low,
            "hypothetical_pnl_at_1030": hypothetical_pnl_at_1030,
        })

        print(f"{c['date']} {c['name']:12s}({c['code']}) 매수 {c['buy_time'].strftime('%H:%M')}@{c['buy_price']:,.0f}")
        print(f"  실제: {c['actual_sell_price']:,.0f}원에 매도, 실현손익 {c['actual_pnl']:+,.0f}원")
        print(f"  만약 10:30까지 들고 있었다면: 그 구간 최저 {low:,.0f}원({pct_low:+.1f}%), "
              f"10:30 시점 {at_1030:,.0f}원({pct_at_1030:+.1f}%) "
              f"-> 그 시점 매도 시 가상손익 {hypothetical_pnl_at_1030:+,.0f}원")
        print()

    if results:
        n = len(results)
        still_loss = sum(1 for r in results if r["hypothetical_pnl_at_1030"] < 0)
        avg_actual = sum(r["actual_pnl"] for r in results) / n
        avg_hypo = sum(r["hypothetical_pnl_at_1030"] for r in results) / n
        print("=" * 60)
        print(f"확인된 {n}건 중 {still_loss}건은 10:30에도 여전히 마이너스")
        print(f"실제 평균손익: {avg_actual:+,.0f}원  vs  10:30까지 들고 있었을 때 평균손익: {avg_hypo:+,.0f}원")


if __name__ == "__main__":
    main()
