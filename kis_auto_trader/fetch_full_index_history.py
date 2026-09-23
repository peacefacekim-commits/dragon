"""
전체 거래 기간(7월 말~9월)의 코스피/코스닥 일봉 종가를 받아온다.
market_history.csv는 8/27부터만 있어서, 그 이전 거래들도 지수와 비교할 수
있게 KIS 과거 일봉 API로 더 긴 기간을 따로 받는다. 조회만 하고 매매는 안 함.

사용법: kis_auto_trader 폴더에 넣고 그 폴더에서 실행
  python fetch_full_index_history.py
결과는 index_history_full.csv 로 저장됨 - 이 파일을 그대로 다시 보내주면 됨.
"""
import csv
import common
import api_client

cfg = common.load_config()

kospi = api_client.get_index_daily_prices(cfg, "0001", start_date="20260715", end_date="20260902")
kosdaq = api_client.get_index_daily_prices(cfg, "1001", start_date="20260715", end_date="20260902")

kosdaq_by_date = {r["date"]: r["close"] for r in kosdaq}

with open("index_history_full.csv", "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["date", "kospi_close", "kosdaq_close"])
    for r in kospi:
        writer.writerow([r["date"], r["close"], kosdaq_by_date.get(r["date"], "")])

print(f"코스피 {len(kospi)}건, 코스닥 {len(kosdaq)}건 -> index_history_full.csv 저장 완료")
