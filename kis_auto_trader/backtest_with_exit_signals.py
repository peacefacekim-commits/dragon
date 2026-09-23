"""±5% 익절/손절 기반 백테스트

지표(Bearish+음수OVN)로 매수 신호를 선정하고,
각 거래마다 +5% 익절 또는 -5% 손절에 도달할 때까지 추적합니다.
"""
import statistics as st
from datetime import datetime
from pathlib import Path

import strategy as S


def calculate_ovn(panel, picks, di):
    """OVN 계산 (전일 종가 → 당일 시가)."""
    if di < 1:
        return None

    ovn_vals = []
    for code in picks:
        s = panel[code]
        if di - 1 in s.pos and di in s.pos:
            prev_close = s.close[s.pos[di - 1]]
            curr_open = s.open[s.pos[di]]
            if prev_close > 0:
                ovn = (curr_open - prev_close) / prev_close
                ovn_vals.append(ovn)

    if not ovn_vals:
        return None

    return st.mean(ovn_vals)


def get_yesterday_signal(panel, picks, di):
    """어제 신호 판정 (어제의 일중 수익률)."""
    if di < 1:
        return None

    di_prev = di - 1
    rets = []

    for code in picks:
        s = panel[code]
        if di_prev in s.pos:
            o = s.open[s.pos[di_prev]]
            c = s.close[s.pos[di_prev]]
            if o > 0:
                ret = (c - o) / o
                rets.append(ret)

    if not rets:
        return None

    avg_ret = st.mean(rets)
    return "bearish" if avg_ret < 0 else "bullish"


def get_daily_prices(panel, picks, di):
    """당일 시가/종가 평균."""
    prices = []

    for code in picks:
        s = panel[code]
        if di in s.pos:
            idx = s.pos[di]
            o = s.open[idx]
            c = s.close[idx]

            if o > 0:
                prices.append({'open': o, 'close': c})

    if not prices:
        return None, None

    avg_open = st.mean([p['open'] for p in prices])
    avg_close = st.mean([p['close'] for p in prices])

    return avg_open, avg_close


def find_exit_price(panel, picks, entry_di, entry_price, dates):
    """익절(+5%) 또는 손절(-5%) 도달 시점 찾기."""
    target_high = entry_price * 1.05  # +5% 익절
    target_low = entry_price * 0.95   # -5% 손절

    # entry_di부터 이후 거래일들을 순회 (최대 20일)
    for check_di in range(entry_di + 1, min(entry_di + 21, len(dates))):
        avg_open, avg_close = get_daily_prices(panel, picks, check_di)

        if avg_open is None:
            continue

        # 종가로 판정
        # 익절: 종가가 +5% 이상
        if avg_close >= target_high:
            return check_di - entry_di, 0.05, "익절"

        # 손절: 종가가 -5% 이하
        if avg_close <= target_low:
            return check_di - entry_di, -0.05, "손절"

    # 20일 이내에 도달 못하면 None
    return None, None, None


def simulate_strategy(dates, panel):
    """전략 시뮬레이션."""
    top_n = 10
    trades = []

    # 모든 거래일 순회
    for di in range(250, len(dates) - 20):  # 250일 이후, 마지막 20일 제외
        # 종목 선택
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        scored = [(S.factor_score(panel, c, di, "low_vol"), c) for c in cand]
        scored = [(s, c) for s, c in scored if s is not None]

        if len(scored) < top_n:
            continue

        scored.sort(reverse=True)
        picks = [c for _s, c in scored[:top_n]]

        # 어제 신호 + OVN 계산
        yesterday_signal = get_yesterday_signal(panel, picks, di)
        ovn = calculate_ovn(panel, picks, di)

        if yesterday_signal is None or ovn is None:
            continue

        # BUY 신호 판정 (Bearish + 음수OVN)
        if yesterday_signal == "bearish" and ovn < 0:
            # 매수가
            avg_open, _ = get_daily_prices(panel, picks, di)

            if avg_open is None:
                continue

            entry_price = avg_open

            # 익절/손절 추적
            days_to_exit, exit_return, exit_type = find_exit_price(
                panel, picks, di, entry_price, dates
            )

            if exit_return is not None:
                trade_record = {
                    "date": dates[di],
                    "di": di,
                    "signal": yesterday_signal,
                    "ovn": ovn,
                    "entry_price": entry_price,
                    "exit_return": exit_return,
                    "exit_type": exit_type,
                    "days_held": days_to_exit,
                    "hit": exit_return > 0,
                }

                trades.append(trade_record)

    return trades


def analyze_results(trades):
    """결과 분석."""
    print("\n" + "=" * 100)
    print("📊 ±5% 익절/손절 백테스트 결과")
    print("=" * 100)

    if not trades:
        print("거래 없음")
        return

    print(f"\n[전체 거래]")
    print(f"  총 거래: {len(trades)}회")

    # 승패 분석
    wins = [t for t in trades if t["hit"]]
    losses = [t for t in trades if not t["hit"]]

    win_rate = len(wins) / len(trades) * 100 if trades else 0

    print(f"  익절: {len(wins)}회 ({win_rate:.1f}%)")
    print(f"  손절: {len(losses)}회 ({100-win_rate:.1f}%)")

    # 거래 기간
    days_held = [t["days_held"] for t in trades if t["days_held"] is not None]
    if days_held:
        avg_days = st.mean(days_held)
        median_days = st.median(days_held)
        print(f"\n[거래 기간]")
        print(f"  평균: {avg_days:.1f}일")
        print(f"  중앙값: {median_days:.1f}일")

    # 수익 분석 (익절은 +5%, 손절은 -5%)
    print(f"\n[수익 분석]")
    total_return = sum(t["exit_return"] for t in trades)
    avg_return = st.mean([t["exit_return"] for t in trades])

    print(f"  누적 수익률: {total_return*100:+.2f}%")
    print(f"  평균 수익률/거래: {avg_return*100:+.2f}%")

    # 월/연 추정 (월 20거래 기준)
    print(f"\n[추정 성과 (월 20거래 기준)]")
    monthly_return = avg_return * 20
    annual_return = monthly_return * 12

    print(f"  월 수익률: {monthly_return*100:+.2f}%")
    print(f"  연 수익률: {annual_return*100:+.2f}%")

    # 초기 자본 기준
    print(f"\n[100만원 기준 추정]")
    initial = 1000000
    # 월 수익률 기반 누적
    final = initial * (1 + monthly_return) ** 12

    print(f"  1년 후: {final:,.0f}원")
    print(f"  수익: {final - initial:+,.0f}원")


def main():
    print("\n" + "=" * 100)
    print("±5% 익절/손절 백테스트 (지표 기반 매수)")
    print("=" * 100)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 데이터 로드
    print("[1] 패널 데이터 로드...")
    dates, panel = S.load_panel(verbose=False)
    print(f"✅ {len(dates)}개 거래일, {len(panel)}개 종목 로드")

    # 2. 시뮬레이션
    print("\n[2] 전략 시뮬레이션...")
    trades = simulate_strategy(dates, panel)
    print(f"✅ {len(trades)}개 거래 완료")

    # 3. 결과 분석
    print("\n[3] 결과 분석...")
    analyze_results(trades)

    print("\n" + "=" * 100)
    print("[완료]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
