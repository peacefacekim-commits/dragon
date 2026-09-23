"""당일 거래 실행 스크립트

10:05 이후 BUY 신호 검증 후
선택된 종목에 매수 주문을 넣고
실시간 모니터링을 시작합니다.

이 스크립트는 데모 버전입니다.
실제 거래는 KIS API 연동이 필요합니다.
"""
import json
import csv
import glob
from datetime import datetime, timedelta
from pathlib import Path
import statistics as st

import strategy as S


def load_latest_decision():
    """가장 최신 거래 결정 로드."""
    data_dir = S.BASE_DIR / "data"

    # 오늘 결정 찾기
    decision_files = sorted(glob.glob(str(data_dir / "trade_decision_*.json")))
    if not decision_files:
        print("⚠️  오늘 거래 결정 파일 없음")
        return None

    latest_file = decision_files[-1]

    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            decision = json.load(f)
        print(f"✅ 최신 거래 결정 로드: {Path(latest_file).name}")
        return decision
    except Exception as e:
        print(f"⚠️  거래 결정 로드 오류: {e}")
        return None


def get_stock_picks(panel, rebal_interval=20, lookback=250):
    """오늘의 종목 추출 (Top 10 low-volatility)."""
    dates, _ = S.load_panel(verbose=False)
    top_n = 10

    di = len(dates) - 1
    if di < lookback:
        print("⚠️  데이터 부족")
        return []

    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    scored = [(S.factor_score(panel, c, di, "low_vol"), c) for c in cand]
    scored = [(s, c) for s, c in scored if s is not None]

    if len(scored) < top_n:
        print("⚠️  충분한 후보 종목 없음")
        return []

    scored.sort(reverse=True)
    picks = [c for _s, c in scored[:top_n]]

    return picks


def get_current_prices(codes):
    """현재 가격 조회 (데모: 마지막 데이터 사용)."""
    """실제 거래에서는 KIS API로 실시간 가격 조회."""
    prices = {}

    for code in codes:
        # 데모: 마지막 종가 사용
        # 실제로는 KIS API로 현재 가격 조회
        prices[code] = None  # placeholder

    return prices


def calculate_position_sizing(capital, num_stocks, risk_pct=0.02):
    """포지션 크기 계산.

    초소자본(100만원) 기준:
    - 10종목에 동일 분배
    - 종목당 10만원 (1% 위험)
    """
    per_stock_capital = capital / num_stocks
    per_stock_risk = capital * risk_pct / num_stocks

    return {
        "total_capital": capital,
        "per_stock_capital": per_stock_capital,
        "per_stock_risk": per_stock_risk,
        "num_stocks": num_stocks,
    }


def create_order_batch(codes, entry_price_map, sizing, expected_return, win_rate):
    """거래 배치 생성 (실제 주문 전 검증용)."""
    orders = []

    for code in codes:
        entry_price = entry_price_map.get(code)
        if entry_price is None or entry_price <= 0:
            continue

        # 목표가와 손절가 계산
        # 기대 수익률: +0.592% (약세 신호일 때)
        # 손실 제한: -1% (보수적)
        target_price = entry_price * (1 + expected_return)
        stop_price = entry_price * 0.99  # -1% stop loss

        # 수량 계산
        quantity = int(sizing["per_stock_capital"] / entry_price)

        if quantity <= 0:
            continue

        orders.append({
            "code": code,
            "entry_price": entry_price,
            "quantity": quantity,
            "target_price": target_price,
            "stop_price": stop_price,
            "target_return": expected_return,
            "position_value": quantity * entry_price,
            "expected_profit": quantity * entry_price * expected_return,
            "expected_loss": quantity * entry_price * (-0.01),
        })

    return orders


def simulate_order_execution(orders):
    """주문 실행 시뮬레이션 (데모)."""
    print("\n" + "=" * 80)
    print("주문 시뮬레이션 (DEMO 모드)")
    print("=" * 80)
    print("\n⚠️  경고: 이것은 시뮬레이션입니다")
    print("실제 거래를 위해서는 KIS API 연동이 필요합니다\n")

    total_value = 0

    print(f"{'코드':<8} {'진입가':<10} {'수량':<8} {'목표가':<10} {'손절':<10} {'포지션':<12} {'기대수익':<12}")
    print("-" * 90)

    for order in orders:
        print(
            f"{order['code']:<8} "
            f"{order['entry_price']:>9.0f} "
            f"{order['quantity']:>7} "
            f"{order['target_price']:>9.0f} "
            f"{order['stop_price']:>9.0f} "
            f"{order['position_value']:>11,.0f} "
            f"{order['expected_profit']:>11,.0f}"
        )
        total_value += order['position_value']

    print("-" * 90)
    print(f"{'총 포지션 가치':<40} {total_value:>11,.0f}")
    print(f"{'기대 총 수익':<40} {sum(o['expected_profit'] for o in orders):>11,.0f}")

    return {
        "total_position_value": total_value,
        "total_expected_profit": sum(o['expected_profit'] for o in orders),
        "num_orders": len(orders),
    }


def save_execution_log(decision, picks, orders, execution_result):
    """거래 실행 기록 저장."""
    data_dir = S.BASE_DIR / "data"

    log_data = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime('%Y-%m-%d'),
        "decision": {
            "decision": decision["decision"],
            "confidence": decision["confidence"],
            "agreement_rate": decision["agreement_rate"],
            "expected_return": decision["expected_return"],
            "win_rate": decision["win_rate"],
        },
        "picks": picks,
        "orders": orders,
        "execution": execution_result,
    }

    log_file = data_dir / f"trade_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 거래 실행 기록 저장: {log_file}")
        return log_file
    except Exception as e:
        print(f"⚠️  기록 저장 오류: {e}")
        return None


def main():
    print("\n" + "=" * 80)
    print("당일 거래 실행 (10:05 ~ 시장 종가)")
    print("=" * 80)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 거래 결정 확인
    print("[1] 거래 결정 확인...")
    decision = load_latest_decision()
    if not decision:
        print("❌ 거래 결정 없음 - 종료")
        return 1

    if decision["decision"] != "BUY":
        print(f"⚠️  거래 신호: {decision['decision']} → 매수 스킵")
        return 0

    print(f"✅ BUY 신호 확인")
    print(f"   신뢰도: {decision['confidence']:.1f}%")
    print(f"   기대 수익률: {decision['expected_return']*100:+.3f}%")

    # 2. 종목 선택
    print("\n[2] 종목 선택...")
    dates, panel = S.load_panel(verbose=False)
    picks = get_stock_picks(panel)
    if not picks:
        print("❌ 종목 선택 실패")
        return 1

    print(f"✅ {len(picks)}개 종목 선택 완료")

    # 3. 현재 가격 조회 (데모)
    print("\n[3] 가격 조회...")
    prices = get_current_prices(picks)
    print("⚠️  데모 모드: 마지막 데이터 사용")

    # 데모용으로 마지막 종가 사용
    entry_price_map = {}
    for code in picks:
        if code in panel:
            s = panel[code]
            if len(s.close) > 0:
                entry_price_map[code] = s.close[-1]  # 마지막 종가

    if not entry_price_map:
        print("❌ 가격 정보 없음")
        return 1

    print(f"✅ {len(entry_price_map)}개 종목 가격 조회 완료")

    # 4. 포지션 크기 결정
    print("\n[4] 포지션 크기 결정...")
    # 데모: 100만원 초소자본 가정
    demo_capital = 1000000  # 100만원
    sizing = calculate_position_sizing(demo_capital, len(picks))

    print(f"   총 자본: {sizing['total_capital']:,.0f}원")
    print(f"   종목당: {sizing['per_stock_capital']:,.0f}원")
    print(f"   종목 수: {sizing['num_stocks']}개")

    # 5. 주문 생성
    print("\n[5] 주문 생성...")
    orders = create_order_batch(
        picks,
        entry_price_map,
        sizing,
        decision["expected_return"],
        decision["win_rate"]
    )

    if not orders:
        print("❌ 주문 생성 실패")
        return 1

    print(f"✅ {len(orders)}개 주문 생성 완료")

    # 6. 실행 (시뮬레이션)
    print("\n[6] 주문 실행...")
    execution_result = simulate_order_execution(orders)

    # 7. 기록 저장
    print("\n[7] 기록 저장...")
    save_execution_log(decision, picks, orders, execution_result)

    # 최종 요약
    print("\n" + "=" * 80)
    print("📊 거래 실행 완료")
    print("=" * 80)
    print(f"\n총 포지션 가치: {execution_result['total_position_value']:,.0f}원")
    print(f"기대 총 수익: {execution_result['total_expected_profit']:>+,.0f}원 ({execution_result['total_expected_profit']/execution_result['total_position_value']*100:+.3f}%)")
    print(f"주문 수: {execution_result['num_orders']}개")

    print("\n" + "=" * 80)
    print("📌 다음 단계")
    print("=" * 80)
    print("\n1. 실시간 모니터링:")
    print(f"   - 목표가 도달 시 매도")
    print(f"   - 손절가 도달 시 손절")
    print(f"   - 장 종료 시 전량 매도 (또는 익일 보유)")

    print("\n2. 일일 결과 분석:")
    print("   python analyze_daily_results.py")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
