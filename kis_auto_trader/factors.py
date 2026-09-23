"""
여러 유명 투자전략(팩터)이 요구하는 지표를 종목별 일봉 데이터에서 계산한다.
(2026-09-05 추가) 사용자 요청: "여러 투자 방식을 실제로 했다면 어떤 데이터가
나올지를 보고 싶은데" - 모멘텀/추세추종/저변동성/밸류 네 가지를 후보군 전체에
동시에 계산해서, trader.py가 각각을 독립된 가상매매 전략으로 동시에 시험한다.

국내외 논문 조사(주말 대화 참고) 결과 이 셋을 우선순위로 잡았다:
  - 모멘텀: 최근 수익률이 좋은 종목이 계속 간다 (Jegadeesh & Titman 1993)
  - 추세추종: 이동평균 위에 있는 종목만 (하락장 방어 효과 위주)
  - 저변동성: 변동성 낮은 종목이 위험대비 수익 좋음 (국내 논문도 확인 - 고봉찬·김진우)
  - 밸류(저PER/PBR)는 candidate_snapshot에 이미 있는 값을 그대로 쓴다 (여기선 계산 없음)

한계 - 정직하게 밝혀둠: KIS 일봉 조회 API는 한 번 호출에 최대 약 100건까지만
주므로, 학계에서 흔히 쓰는 12개월 모멘텀/200일 이동평균을 그대로는 못 쓴다.
여기서는 최근 약 60거래일(3개월)치만 쓴다 - 여러 번 나눠 호출하는 페이지네이션은
아직 안 만들었다. 그래서 "모멘텀"은 3개월 모멘텀, "추세추종"은 60일 이동평균
기준이다. 나중에 필요하면 페이지네이션을 추가해 기간을 늘릴 수 있다.
"""

MOMENTUM_LOOKBACK_DAYS = 60
TREND_MA_DAYS = 60
VOLATILITY_LOOKBACK_DAYS = 20


def momentum_return_pct(daily_rows: list[dict], lookback: int = MOMENTUM_LOOKBACK_DAYS) -> float | None:
    """최근 lookback 거래일 수익률(%). daily_rows는 오래된 순(get_daily_prices 형식).
    데이터가 부족하면 None."""
    if len(daily_rows) < lookback + 1:
        return None
    old_close = daily_rows[-lookback - 1]["close"]
    new_close = daily_rows[-1]["close"]
    if old_close <= 0:
        return None
    return (new_close - old_close) / old_close * 100


def is_above_moving_average(daily_rows: list[dict], ma_days: int = TREND_MA_DAYS) -> bool | None:
    """현재가가 ma_days 이동평균보다 위인지. 데이터가 부족하면 None."""
    if len(daily_rows) < ma_days:
        return None
    closes = [r["close"] for r in daily_rows[-ma_days:]]
    ma = sum(closes) / len(closes)
    current = daily_rows[-1]["close"]
    return current > ma


def volatility_stdev_pct(daily_rows: list[dict], days: int = VOLATILITY_LOOKBACK_DAYS) -> float | None:
    """최근 days 거래일 일별수익률의 표준편차(%) - 저변동성 팩터용.
    낮을수록 "저변동성" 종목. 데이터가 부족하면 None."""
    if len(daily_rows) < days + 1:
        return None
    recent = daily_rows[-days - 1:]
    rets = []
    for i in range(1, len(recent)):
        prev_close = recent[i - 1]["close"]
        cur_close = recent[i]["close"]
        if prev_close > 0:
            rets.append((cur_close - prev_close) / prev_close * 100)
    if len(rets) < days - 2:  # 결측(휴장 등)이 너무 많으면 신뢰 못 함
        return None
    mean = sum(rets) / len(rets)
    variance = sum((r - mean) ** 2 for r in rets) / len(rets)
    return variance ** 0.5
