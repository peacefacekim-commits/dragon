"""일일 거래 결과 분석 스크립트

장 종료 후(15:30~16:00) 실행하여
실제 수익률과 기대 수익률을 비교합니다.

이는 전략의 효과를 실시간으로 검증하는 역할을 합니다.
"""
import json
import glob
from datetime import datetime, timedelta
from pathlib import Path
import statistics as st
import csv

import strategy as S


def load_today_execution_log():
    """오늘의 거래 실행 기록 로드."""
    data_dir = S.BASE_DIR / "data"

    # 오늘 실행 기록 찾기
    today_str = datetime.now().strftime('%Y%m%d')
    execution_files = sorted(glob.glob(str(data_dir / f"trade_execution_{today_str}_*.json")))

    if not execution_files:
        print("⚠️  오늘 거래 실행 기록 없음")
        return None

    latest_file = execution_files[-1]

    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            execution = json.load(f)
        print(f"✅ 거래 실행 기록 로드: {Path(latest_file).name}")
        return execution
    except Exception as e:
        print(f"⚠️  기록 로드 오류: {e}")
        return None


def get_closing_prices(codes, panel):
    """종가 조회."""
    prices = {}

    for code in codes:
        if code in panel:
            s = panel[code]
            if len(s.close) > 0:
                prices[code] = s.close[-1]

    return prices


def calculate_actual_returns(execution, panel):
    """실제 수익률 계산."""
    orders = execution.get("orders", [])
    closing_prices = get_closing_prices([o["code"] for o in orders], panel)

    results = []
    total_entry_value = 0
    total_exit_value = 0
    total_actual_profit = 0

    for order in orders:
        code = order["code"]
        closing_price = closing_prices.get(code)

        if closing_price is None:
            continue

        entry_price = order["entry_price"]
        quantity = order["quantity"]
        entry_value = quantity * entry_price
        exit_value = quantity * closing_price
        actual_profit = exit_value - entry_value
        actual_return = (closing_price - entry_price) / entry_price

        total_entry_value += entry_value
        total_exit_value += exit_value
        total_actual_profit += actual_profit

        results.append({
            "code": code,
            "entry_price": entry_price,
            "closing_price": closing_price,
            "quantity": quantity,
            "entry_value": entry_value,
            "exit_value": exit_value,
            "actual_profit": actual_profit,
            "actual_return": actual_return,
            "expected_return": order.get("target_return", 0),
            "hit_target": closing_price >= order.get("target_price", 0),
            "hit_stop": closing_price <= order.get("stop_price", 0),
        })

    return {
        "orders": results,
        "total_entry_value": total_entry_value,
        "total_exit_value": total_exit_value,
        "total_actual_profit": total_actual_profit,
        "total_actual_return": total_actual_profit / total_entry_value if total_entry_value > 0 else 0,
        "total_expected_profit": execution.get("execution", {}).get("total_expected_profit", 0),
        "num_winners": sum(1 for r in results if r["actual_return"] > 0),
        "num_losers": sum(1 for r in results if r["actual_return"] < 0),
        "win_rate": sum(1 for r in results if r["actual_return"] > 0) / len(results) * 100 if results else 0,
    }


def print_daily_results(execution, results):
    """일일 결과 출력."""
    print("\n" + "=" * 100)
    print("일일 거래 결과 분석")
    print("=" * 100)

    decision = execution.get("decision", {})

    print(f"\n[거래 신호]")
    print(f"  신호: {decision.get('decision')}")
    print(f"  신뢰도: {decision.get('confidence'):.1f}%")
    print(f"  기대 수익률: {decision.get('expected_return')*100:+.3f}%")
    print(f"  기대 승률: {decision.get('win_rate'):.1f}%")

    print(f"\n[개별 주문 결과]")
    print(f"{'코드':<8} {'진입가':<10} {'종가':<10} {'수익':<12} {'수익률':<12} {'기대대비':<12} {'목표도달':<10}")
    print("-" * 100)

    for order in results["orders"]:
        target_hit = "✓" if order["hit_target"] else "✗"
        stop_hit = "STOP" if order["hit_stop"] else ""
        status = f"{target_hit} {stop_hit}" if stop_hit else target_hit

        vs_expected = order["actual_return"] - order["expected_return"]
        vs_str = f"{vs_expected:+.3f}%" if order["expected_return"] != 0 else "N/A"

        print(
            f"{order['code']:<8} "
            f"{order['entry_price']:>9.0f} "
            f"{order['closing_price']:>9.0f} "
            f"{order['actual_profit']:>11,.0f} "
            f"{order['actual_return']*100:>11.3f}% "
            f"{vs_str:>11} "
            f"{status:>9}"
        )

    print("-" * 100)

    print(f"\n[종합 결과]")
    print(f"  총 진입값: {results['total_entry_value']:>15,.0f}원")
    print(f"  총 종가값: {results['total_exit_value']:>15,.0f}원")
    print(f"  실제 수익: {results['total_actual_profit']:>15,.0f}원 ({results['total_actual_return']*100:+.3f}%)")
    print(f"  기대 수익: {results['total_expected_profit']:>15,.0f}원")
    print(f"  수익/손실: {results['num_winners']}/{len(results['orders'])}승 (승률 {results['win_rate']:.1f}%)")

    # vs 기대값
    profit_vs_expected = results['total_actual_profit'] - results['total_expected_profit']
    print(f"\n[기대값 대비]")
    print(f"  기대 수익: {results['total_expected_profit']:>15,.0f}원")
    print(f"  실제 수익: {results['total_actual_profit']:>15,.0f}원")
    print(f"  차이: {profit_vs_expected:>15,.0f}원")

    if profit_vs_expected > 0:
        print(f"  ✅ 기대값 초과 달성!")
    elif profit_vs_expected < -0.5 * results['total_expected_profit']:
        print(f"  ⚠️  기대값 대비 상당한 부족")
    else:
        print(f"  ⚠️  기대값 미달")


def save_daily_results(execution, results):
    """일일 결과 저장."""
    data_dir = S.BASE_DIR / "data"

    result_data = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "timestamp": datetime.now().isoformat(),
        "decision": execution.get("decision"),
        "execution": execution.get("execution"),
        "results": results,
    }

    result_file = data_dir / f"daily_results_{datetime.now().strftime('%Y%m%d')}.json"

    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 일일 결과 저장: {result_file}")
    except Exception as e:
        print(f"⚠️  결과 저장 오류: {e}")

    # CSV에도 기록 (누적 데이터)
    save_to_csv(result_data)


def save_to_csv(result_data):
    """CSV 파일에 누적 기록."""
    data_dir = S.BASE_DIR / "data"
    csv_file = data_dir / "trading_log.csv"

    row = {
        "date": result_data["date"],
        "signal": result_data.get("decision", {}).get("decision", "N/A"),
        "confidence": result_data.get("decision", {}).get("confidence", 0),
        "expected_return": result_data.get("decision", {}).get("expected_return", 0),
        "expected_profit": result_data.get("execution", {}).get("total_expected_profit", 0),
        "actual_profit": result_data["results"].get("total_actual_profit", 0),
        "actual_return": result_data["results"].get("total_actual_return", 0),
        "win_count": result_data["results"].get("num_winners", 0),
        "total_orders": len(result_data["results"].get("orders", [])),
        "win_rate": result_data["results"].get("win_rate", 0),
    }

    try:
        # 파일이 없으면 헤더 작성
        if not csv_file.exists():
            with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                writer.writeheader()

        # 데이터 추가
        with open(csv_file, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            writer.writerow(row)

        print(f"✅ CSV 기록 업데이트: {csv_file}")
    except Exception as e:
        print(f"⚠️  CSV 저장 오류: {e}")


def calculate_strategy_metrics(csv_file=None):
    """누적 전략 메트릭 계산."""
    if csv_file is None:
        data_dir = S.BASE_DIR / "data"
        csv_file = data_dir / "trading_log.csv"

    if not csv_file.exists():
        return None

    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))

        if not rows:
            return None

        # 계산
        total_days = len(rows)
        total_profit = sum(float(r.get("actual_profit", 0)) for r in rows)
        total_return = sum(float(r.get("actual_return", 0)) for r in rows)
        total_expected_profit = sum(float(r.get("expected_profit", 0)) for r in rows)

        win_days = sum(1 for r in rows if float(r.get("actual_profit", 0)) > 0)

        return {
            "total_days": total_days,
            "win_days": win_days,
            "win_rate": win_days / total_days * 100 if total_days > 0 else 0,
            "total_profit": total_profit,
            "total_return": total_return,
            "avg_daily_return": total_return / total_days if total_days > 0 else 0,
            "total_expected_profit": total_expected_profit,
            "profit_vs_expected": total_profit - total_expected_profit,
        }
    except Exception as e:
        print(f"⚠️  전략 메트릭 계산 오류: {e}")
        return None


def main():
    print("\n" + "=" * 100)
    print("일일 거래 결과 분석 (15:30 ~ 16:00)")
    print("=" * 100)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 거래 실행 기록 로드
    print("[1] 거래 실행 기록 로드...")
    execution = load_today_execution_log()
    if not execution:
        print("❌ 거래 실행 기록 없음")
        return 1

    # 2. 종가 데이터 로드
    print("\n[2] 종가 데이터 로드...")
    dates, panel = S.load_panel(verbose=False)
    print(f"✅ 패널 로드 완료 ({len(dates)}개 거래일)")

    # 3. 수익률 계산
    print("\n[3] 수익률 계산...")
    results = calculate_actual_returns(execution, panel)
    print(f"✅ {len(results['orders'])}개 주문 결과 계산 완료")

    # 4. 결과 출력
    print_daily_results(execution, results)

    # 5. 결과 저장
    print("\n[4] 결과 저장...")
    save_daily_results(execution, results)

    # 6. 누적 전략 메트릭
    print("\n[5] 누적 전략 메트릭...")
    data_dir = S.BASE_DIR / "data"
    metrics = calculate_strategy_metrics(data_dir / "trading_log.csv")

    if metrics:
        print("\n" + "=" * 100)
        print("📊 누적 전략 성과 (전체 기간)")
        print("=" * 100)
        print(f"  거래 일수: {metrics['total_days']}일")
        print(f"  수익일: {metrics['win_days']}일 (승률 {metrics['win_rate']:.1f}%)")
        print(f"  총 수익: {metrics['total_profit']:>15,.0f}원")
        print(f"  누적 수익률: {metrics['total_return']*100:>14.3f}%")
        print(f"  일평균 수익률: {metrics['avg_daily_return']*100:>13.3f}%")
        print(f"\n  기대 수익: {metrics['total_expected_profit']:>15,.0f}원")
        print(f"  실제 vs 기대: {metrics['profit_vs_expected']:>14,.0f}원")

        if metrics['profit_vs_expected'] > 0:
            print(f"  ✅ 기대값 초과 달성!")
        else:
            print(f"  ⚠️  기대값 대비 {abs(metrics['profit_vs_expected']):,.0f}원 미달")

    print("\n" + "=" * 100)
    print("📌 다음 단계")
    print("=" * 100)
    print("\n1. 다음 거래일(내일):")
    print("   09:30 - python collect_intraday_signals.py")
    print("   10:00 - python compare_signals_intraday.py")
    print("   10:05 - python trade_execute_intraday.py (BUY 신호 시)")
    print("   16:00 - python analyze_daily_results.py")

    print("\n2. 주간 검토:")
    print("   python analyze_weekly_performance.py")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
