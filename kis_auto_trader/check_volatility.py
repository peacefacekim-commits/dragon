"""
"변동성 슬롯" 기준값을 정하기 위해, 오늘 실제로 매매된 종목들의 최근 일중 변동폭을
비교해보는 1회성 확인 스크립트. 매매에는 전혀 관여하지 않고 조회만 한다.

사용법: 이 파일을 kis_auto_trader 폴더 안에 넣고 그 폴더에서 실행
  python check_volatility.py
"""
import common
import api_client

cfg = common.load_config()

# 오늘(9/1) 실제로 매매된 종목들 - 사토시홀딩스(변동성 커서 문제였던 종목) vs 비교군
CODES = [
    ("223310", "사토시홀딩스"),
    ("328130", "루닛"),
    ("043260", "성호전자"),
]

print(f"{'종목':<12}{'날짜':<10}{'고가':>10}{'저가':>10}{'종가':>10}{'일중변동폭%':>12}")
print("-" * 66)

for code, name in CODES:
    rows = api_client.get_daily_prices(cfg, code, lookback_days=15)
    if not rows:
        print(f"{name}: 데이터 없음")
        continue
    # 오늘(진행 중인 날)은 아직 하루가 안 끝나서 고가/저가가 왜곡될 수 있으니 제외하고,
    # "그 전날까지" 최근 5거래일만 본다 - evening_screen.py가 저녁에 다음날 후보를
    # 고를 때도 그 시점까지의 과거 데이터만 볼 수 있으므로, 같은 조건으로 비교하려는 것.
    past_rows = rows[:-1] if len(rows) > 1 else rows
    recent = past_rows[-5:]

    ranges = []
    for r in recent:
        rng_pct = (r["high"] - r["low"]) / r["close"] * 100 if r["close"] else 0
        ranges.append(rng_pct)
        print(f"{name:<12}{r['date']:<10}{r['high']:>10,.0f}{r['low']:>10,.0f}{r['close']:>10,.0f}{rng_pct:>11.1f}%")

    avg_range = sum(ranges) / len(ranges) if ranges else 0
    print(f"  -> {name} 최근 {len(recent)}일 평균 일중변동폭: {avg_range:.1f}%\n")
