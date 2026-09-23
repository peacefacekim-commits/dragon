"""
사업 갈아타기 이력이 있는 종목들이 실제로 사토시룰(최근5일 평균 변동폭 10% 이상)
기준에 걸리는지 확인하는 스크립트. 조회만 하고 매매는 전혀 안 함.

각 종목의 실제 매수일 기준으로, 그 전날까지 5거래일 평균 일중변동폭을 계산한다
(volatility.py의 evaluate_candidates와 같은 방식).

사용법: kis_auto_trader 폴더에 넣고 그 폴더에서 실행
  python check_pivot_volatility.py
"""
import common
import api_client
import volatility

cfg = common.load_config()

# (종목명, 코드, 매수일 YYYYMMDD, 실현손익)
TARGETS = [
    ("캔버스엔", "210120", "20260902", -28602),
    ("금호에이치티", "214330", "20260826", -11210),
    ("모아라이프플러스", "142760", "20260902", -18482),
    ("휴림에이텍", "078590", "20260825", 5710),
    ("넥사다이내믹스", "351320", "20260828", 12487),
]

print(f"{'종목':<14}{'매수일':<10}{'5일평균변동폭':>14}{'사토시룰 해당':>14}{'실현손익':>12}")
print("-" * 70)

for name, code, buy_date, pnl in TARGETS:
    try:
        rows = api_client.get_daily_prices(cfg, code, end_date=buy_date, lookback_days=20)
    except Exception as e:
        print(f"{name}: 조회 실패 - {e}")
        continue
    # buy_date 당일 행까지 포함해서 받아온 뒤, 매수 당일은 빼고(그 전날까지) 계산
    v = volatility.compute_recent_range_pct(rows, days=5, exclude_last=True)
    if v is None:
        print(f"{name}: 데이터 부족")
        continue
    flagged = volatility.is_high_volatility(v)
    print(f"{name:<14}{buy_date:<10}{v:>13.1f}%{'예' if flagged else '아니오':>14}{pnl:>+11,.0f}원")
