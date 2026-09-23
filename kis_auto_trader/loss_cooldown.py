"""
투자 기록(trades.csv)을 종목 선정 판단에 반영하는 필터 (2026-08-21).

당일 재진입 금지(sold_today.py)는 "같은 날 다시 사는 것"만 막지, 날짜가
바뀌면 다시 후보로 뽑히는 건 못 막는다. 그런데 실제로 셀바스AI(108860)처럼
날짜를 바꿔가며 계속 손실만 내는 종목이 있었다 (08-14 -6,200원, 08-18 -8,200원,
08-21 -21,780원+-4,780원 - 거래할 때마다 매번 손실). 가격+거래량 조건만
보고 종목을 고르면, "이 종목은 지금까지 이 전략으로 계속 안 맞았다"는 경험을
전혀 반영을 못 한다. 두 가지 신호를 같이 본다:

  1) recent_loss_excluded_codes: 최근 며칠 안에 손실이 몰린 종목 (일시적으로
     쉬게 함 - 승리가 쌓이거나 기간이 지나면 자동으로 풀림)
  2) lifetime_loss_excluded_codes: 지금까지 전체 거래 기록상 이 종목에서
     누적으로 손해를 봤는지 (거래 횟수가 늘면서 계속 다시 계산됨 - 나중에
     이 종목에서 이겨서 누적이 플러스로 넘어가면 자동으로 풀림)

거래 기록(trades.csv)은 이미 있는 데이터라 별도 상태 파일 없이, 매번 그
자리에서 다시 계산한다.
"""
import csv
from datetime import datetime, timedelta

from common import TRADE_LOG_PATH

LOOKBACK_TRADING_DAYS = 3  # 최근 이 거래일 수 안에서
# (2026-08-26 변경) 2 -> 1: 원래는 손실이 2번 반복돼야 제외했는데, 그러면 "어제
# 1번 잃은 종목"은 오늘 하루 더 기회를 얻는다. 실제로 이건홀딩스가 08-25 손실
# (-4,655원) 뒤 08-26 아침에 다시 뽑혀서 재매수됐고, 그날 더 큰 손실(-11,560원)로
# 이어졌다 (이노메트리도 같은 패턴으로 같은 날 재매수됨). "한 번 더 기회"의
# 대가가 크다고 판단해 손실 1번만 나도 바로(최근 3거래일 동안) 제외하도록
# 좁힌다 - 대신 진짜 괜찮은 종목이 어쩌다 한 번 진 것도 3일간은 걸러진다는
# 트레이드오프가 있음(사용자 확인 후 반영).
MIN_LOSSES = 1              # 손실 거래가 이 횟수 이상이면 제외
MIN_LIFETIME_TRADES = 2    # 전체 기록 판단에 필요한 최소 거래 횟수 (표본 1개로 성급히 판단 안 함)


def _recent_trading_dates(n: int, today: datetime | None = None) -> set:
    """오늘부터 거꾸로, 주말을 뺀 최근 n개 거래일 날짜("YYYY-MM-DD")를 돌려준다.
    공휴일까지는 반영 못 한다(달력 데이터가 따로 없음) - 대략치."""
    d = (today or datetime.now()).date()
    dates = set()
    cursor = d
    while len(dates) < n:
        if cursor.weekday() < 5:
            dates.add(cursor.strftime("%Y-%m-%d"))
        cursor -= timedelta(days=1)
    return dates


def recent_loss_excluded_codes(
    lookback_trading_days: int = LOOKBACK_TRADING_DAYS,
    min_losses: int = MIN_LOSSES,
    today: datetime | None = None,
) -> set:
    """최근 lookback_trading_days 거래일 안에서 손실 매도가 min_losses 번 이상
    난 종목 코드 집합을 돌려준다. trades.csv 가 없으면 빈 집합."""
    if not TRADE_LOG_PATH.exists():
        return set()

    window_dates = _recent_trading_dates(lookback_trading_days, today)
    loss_counts: dict = {}
    with open(TRADE_LOG_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("side") != "sell" or not row.get("realized_pnl"):
                continue
            date = row["timestamp"][:10]
            if date not in window_dates:
                continue
            try:
                pnl = float(row["realized_pnl"])
            except ValueError:
                continue
            if pnl < 0:
                loss_counts[row["code"]] = loss_counts.get(row["code"], 0) + 1

    return {code for code, cnt in loss_counts.items() if cnt >= min_losses}


def lifetime_loss_excluded_codes(min_trades: int = MIN_LIFETIME_TRADES) -> set:
    """지금까지 기록된 전체 매매에서, 이 종목의 누적 실현손익(realized_pnl 합)이
    마이너스인 종목 코드 집합을 돌려준다. 거래 횟수가 min_trades 미만이면
    표본이 너무 적어(예: 수동 테스트 1건) 판단하지 않고 제외 대상에서 뺀다."""
    if not TRADE_LOG_PATH.exists():
        return set()

    totals: dict = {}
    counts: dict = {}
    with open(TRADE_LOG_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("side") != "sell" or not row.get("realized_pnl"):
                continue
            try:
                pnl = float(row["realized_pnl"])
            except ValueError:
                continue
            code = row["code"]
            totals[code] = totals.get(code, 0.0) + pnl
            counts[code] = counts.get(code, 0) + 1

    return {code for code, total in totals.items() if counts[code] >= min_trades and total < 0}


def excluded_codes(today: datetime | None = None) -> set:
    """종목 선정 시 제외할 전체 코드 집합 (최근 반복 손실 + 전체 기록 누적 손실)."""
    return recent_loss_excluded_codes(today=today) | lifetime_loss_excluded_codes()
