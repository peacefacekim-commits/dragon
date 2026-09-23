"""간단한 거래 전략 백테스트

역사 데이터를 이용해 전략의 성과를 시뮬레이션합니다.

전략:
- 약세 신호 + OVN 음수 → BUY (+0.592% 기대)
- 약세 신호 + OVN 양수 → HOLD
- 강세 신호 → HOLD (손실 회피)
"""
import csv
import statistics as st
from datetime import datetime
from pathlib import Path

import strategy as S


def calculate_ovn(panel, picks, di):
    """OVN 계산."""
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


def calculate_yesterday_signal(panel, picks, di):
    """전일 신호 판정."""
    daily_rets = []
    for code in picks:
        s = panel[code]
        if di in s.pos:
            o = s.open[s.pos[di]]
            c = s.close[s.pos[di]]
            if o > 0:
                ret = (c - o) / o
                daily_rets.append(ret)

    if not daily_rets:
        return None, None

    avg_ret = st.mean(daily_rets)
    return "bearish" if avg_ret < 0 else "bullish", avg_ret


def calculate_actual_return(panel, picks, di):
    """당일 실제 수익률 계산."""
    if di >= len(list(panel.values())[0].close):
        return None

    rets = []
    for code in picks:
        s = panel[code]
        if di in s.pos:
            o = s.open[s.pos[di]]
            c = s.close[s.pos[di]]
            if o > 0:
                ret = (c - o) / o
                rets.append(ret)

    if not rets:
        return None

    return st.mean(rets)


def simulate_strategy(dates, panel, rebal_interval=20, lookback=250):
    """전략 시뮬레이션."""
    top_n = 10
    trades = []

    rebal_dates = [i for i in range(lookback, len(dates), rebal_interval)]

    for di in rebal_dates:
        # 종목 선택
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        scored = [(S.factor_score(panel, c, di, "low_vol"), c) for c in cand]
        scored = [(s, c) for s, c in scored if s is not None]

        if len(scored) < top_n:
            continue

        scored.sort(reverse=True)
        picks = [c for _s, c in scored[:top_n]]

        # 전일 신호
        yesterday_signal, signal_strength = calculate_yesterday_signal(panel, picks, di)
        if yesterday_signal is None:
            continue

        # OVN
        ovn = calculate_ovn(panel, picks, di)

        # 거래 결정
        if yesterday_signal == "bearish":
            if ovn is not None and ovn < 0:
                decision = "BUY"
                confidence = 85
                expected_return = 0.00592
            elif ovn is not None and ovn >= 0:
                decision = "HOLD"
                confidence = 50
                expected_return = 0.002
            else:
                decision = "HOLD"
                confidence = 60
                expected_return = 0.00592
        else:  # bullish
            decision = "HOLD"
            confidence = 55
            expected_return = -0.0022

        # 실제 수익률
        actual_return = calculate_actual_return(panel, picks, di)

        # 거래 기록
        trade_record = {
            "date": dates[di],
            "di": di,
            "signal": yesterday_signal,
            "signal_strength": signal_strength,
            "ovn": ovn,
            "decision": decision,
            "confidence": confidence,
            "expected_return": expected_return,
            "actual_return": actual_return,
            "hit": actual_return > expected_return * 0.9 if actual_return is not None else None,
        }

        trades.append(trade_record)

    return trades


def analyze_results(trades):
    """결과 분석."""
    print("\n" + "=" * 120)
    print("📊 모의 투자 시뮬레이션 결과")
    print("=" * 120)

    # 전체 거래
    print(f"\n[전체 거래]")
    print(f"  총 거래 일수: {len(trades)}일")

    # 의사결정별 분석
    buy_trades = [t for t in trades if t["decision"] == "BUY"]
    hold_trades = [t for t in trades if t["decision"] == "HOLD"]

    print(f"  BUY 신호: {len(buy_trades)}일")
    print(f"  HOLD 신호: {len(hold_trades)}일")

    # BUY 거래 분석
    if buy_trades:
        print(f"\n[BUY 거래 ({len(buy_trades)}일)]")
        buy_actual = [t["actual_return"] for t in buy_trades if t["actual_return"] is not None]

        if buy_actual:
            mean_return = st.mean(buy_actual)
            median_return = st.median(buy_actual)
            win_count = sum(1 for r in buy_actual if r > 0)
            win_rate = win_count / len(buy_actual) * 100 if buy_actual else 0

            print(f"  평균 수익률: {mean_return*100:+.3f}%")
            print(f"  중앙값 수익률: {median_return*100:+.3f}%")
            print(f"  승률: {win_rate:.1f}% ({win_count}/{len(buy_actual)})")

            if len(buy_actual) > 1:
                stdev = st.stdev(buy_actual)
                print(f"  표준편차: {stdev*100:.3f}%")

            # 누적 수익
            cumulative = sum(buy_actual)
            print(f"  누적 수익률: {cumulative*100:+.3f}%")

            # 신뢰도별 분석
            high_conf_buy = [t for t in buy_trades if t["confidence"] >= 80]
            if high_conf_buy:
                high_conf_actual = [t["actual_return"] for t in high_conf_buy if t["actual_return"] is not None]
                if high_conf_actual:
                    print(f"\n  신뢰도 80%+ ({len(high_conf_actual)}일):")
                    print(f"    평균: {st.mean(high_conf_actual)*100:+.3f}%")
                    print(f"    승률: {sum(1 for r in high_conf_actual if r > 0)/len(high_conf_actual)*100:.1f}%")

    # HOLD 거래 분석
    if hold_trades:
        print(f"\n[HOLD 거래 ({len(hold_trades)}일)]")
        hold_actual = [t["actual_return"] for t in hold_trades if t["actual_return"] is not None]

        if hold_actual:
            mean_return = st.mean(hold_actual)
            win_rate = sum(1 for r in hold_actual if r > 0) / len(hold_actual) * 100 if hold_actual else 0

            print(f"  평균 수익률: {mean_return*100:+.3f}%")
            print(f"  승률: {win_rate:.1f}%")
            print(f"  누적 수익률: {sum(hold_actual)*100:+.3f}%")

    # 신호별 분석
    print(f"\n[신호별 분석]")

    # 약세 신호
    bearish_trades = [t for t in trades if t["signal"] == "bearish"]
    if bearish_trades:
        print(f"\n  약세 신호 ({len(bearish_trades)}일):")
        bearish_actual = [t["actual_return"] for t in bearish_trades if t["actual_return"] is not None]
        if bearish_actual:
            print(f"    평균 수익률: {st.mean(bearish_actual)*100:+.3f}%")
            print(f"    승률: {sum(1 for r in bearish_actual if r > 0)/len(bearish_actual)*100:.1f}%")

            # BUY vs HOLD
            bearish_buy = [t for t in bearish_trades if t["decision"] == "BUY"]
            bearish_hold = [t for t in bearish_trades if t["decision"] == "HOLD"]

            if bearish_buy:
                bb_actual = [t["actual_return"] for t in bearish_buy if t["actual_return"] is not None]
                if bb_actual:
                    print(f"      └ BUY ({len(bb_actual)}일): {st.mean(bb_actual)*100:+.3f}%")

            if bearish_hold:
                bh_actual = [t["actual_return"] for t in bearish_hold if t["actual_return"] is not None]
                if bh_actual:
                    print(f"      └ HOLD ({len(bh_actual)}일): {st.mean(bh_actual)*100:+.3f}%")

    # 강세 신호
    bullish_trades = [t for t in trades if t["signal"] == "bullish"]
    if bullish_trades:
        print(f"\n  강세 신호 ({len(bullish_trades)}일):")
        bullish_actual = [t["actual_return"] for t in bullish_trades if t["actual_return"] is not None]
        if bullish_actual:
            print(f"    평균 수익률: {st.mean(bullish_actual)*100:+.3f}%")
            print(f"    승률: {sum(1 for r in bullish_actual if r > 0)/len(bullish_actual)*100:.1f}%")

    # 전체 시뮬레이션 성과
    print(f"\n[시뮬레이션 성과]")

    all_actual = [t["actual_return"] for t in trades if t["actual_return"] is not None]
    if all_actual:
        total_return = sum(all_actual)
        avg_return = st.mean(all_actual)
        win_rate_all = sum(1 for r in all_actual if r > 0) / len(all_actual) * 100

        print(f"  총 거래: {len(all_actual)}회")
        print(f"  누적 수익률: {total_return*100:+.3f}%")
        print(f"  평균 수익률: {avg_return*100:+.3f}% / 회")
        print(f"  전체 승률: {win_rate_all:.1f}%")

        # 월 단위 추정
        print(f"\n  추정 월 성과 (월 20거래 기준):")
        monthly_return = avg_return * 20
        print(f"    월 수익률: {monthly_return*100:+.3f}%")
        print(f"    연 수익률: {monthly_return*12*100:+.3f}%")

        # 초기 자본 기준
        initial_capital = 1000000  # 100만원
        final_capital = initial_capital * (1 + total_return)
        print(f"\n  100만원 기준:")
        print(f"    최종 자본: {final_capital:,.0f}원")
        print(f"    수익: {final_capital - initial_capital:+,.0f}원")

    return trades


def save_backtest_report(trades):
    """백테스트 결과 저장."""
    data_dir = S.BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)

    # CSV 저장
    csv_file = data_dir / "backtest_results.csv"

    fieldnames = [
        "date", "signal", "signal_strength", "ovn", "decision",
        "confidence", "expected_return", "actual_return", "hit"
    ]

    try:
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for trade in trades:
                row = {
                    "date": trade["date"],
                    "signal": trade["signal"],
                    "signal_strength": f"{trade['signal_strength']:.6f}",
                    "ovn": f"{trade['ovn']:.6f}" if trade["ovn"] is not None else "N/A",
                    "decision": trade["decision"],
                    "confidence": trade["confidence"],
                    "expected_return": f"{trade['expected_return']:.6f}",
                    "actual_return": f"{trade['actual_return']:.6f}" if trade["actual_return"] is not None else "N/A",
                    "hit": trade["hit"],
                }
                writer.writerow(row)

        print(f"\n✅ 백테스트 결과 저장: {csv_file}")
    except Exception as e:
        print(f"⚠️  저장 오류: {e}")


def main():
    print("\n" + "=" * 120)
    print("백테스트: 간단한 거래 전략 시뮬레이션")
    print("=" * 120)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 데이터 로드
    print("[1] 패널 데이터 로드...")
    dates, panel = S.load_panel(verbose=False)
    print(f"✅ {len(dates)}개 거래일, {len(panel)}개 종목 로드")

    # 2. 시뮬레이션
    print("\n[2] 전략 시뮬레이션 실행...")
    trades = simulate_strategy(dates, panel)
    print(f"✅ {len(trades)}개 거래 시뮬레이션 완료")

    # 3. 결과 분석
    print("\n[3] 결과 분석...")
    analyze_results(trades)

    # 4. 결과 저장
    print("\n[4] 결과 저장...")
    save_backtest_report(trades)

    print("\n" + "=" * 120)
    print("📌 참고사항")
    print("=" * 120)
    print("\n이것은 모의 투자 시뮬레이션입니다.")
    print("- 과거 데이터 기반 분석")
    print("- 실제 거래 시 변수 있음 (슬리피지, 수수료 등)")
    print("- Phase 1 수집 데이터로 재검증 필요")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
