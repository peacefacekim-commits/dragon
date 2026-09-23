"""상관성 검증 스크립트 (Correlation Validation)

종이거래 신호 데이터에서 예측값과 실제값의 상관성을 검증합니다.
상관성이 충분하면 실거래를 시작할 수 있습니다.

실행: 주단위 또는 충분한 데이터 모인 후
"""
import csv
import json
from pathlib import Path
from scipy import stats
import statistics as st
import numpy as np

import strategy as S


def load_paper_signals():
    """종이거래 신호 CSV 로드."""
    data_dir = S.BASE_DIR / "data"
    csv_file = data_dir / "paper_signals.csv"

    if not csv_file.exists():
        print("⚠️  paper_signals.csv 파일 없음")
        return []

    records = []
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 실제 수익률이 있는 경우만 포함
                if row.get('actual_return') and row['actual_return'] != 'N/A':
                    try:
                        records.append({
                            "date": row["date"],
                            "signal": row["yesterday_signal"],
                            "ovn": float(row["ovn"]) if row["ovn"] != 'N/A' else None,
                            "predicted_return": float(row["predicted_return"]),
                            "confidence": int(row["predicted_confidence"]),
                            "actual_return": float(row["actual_return"]),
                            "hit_target": row["hit_target"].lower() == 'true' if row["hit_target"] else None,
                        })
                    except (ValueError, TypeError):
                        pass
    except Exception as e:
        print(f"⚠️  파일 읽기 오류: {e}")

    return records


def validate_correlation(records):
    """상관성 검증."""
    if len(records) < 10:
        print(f"⚠️  데이터 부족 ({len(records)}개, 최소 10개 필요)")
        return None

    print("\n" + "=" * 100)
    print("📊 상관성 검증 분석")
    print("=" * 100)

    # 데이터 추출
    predicted = [r["predicted_return"] for r in records]
    actual = [r["actual_return"] for r in records]

    print(f"\n📈 샘플 수: {len(records)}개")
    print(f"   기간: {records[0]['date']} ~ {records[-1]['date']}")

    # 피어슨 상관계수
    try:
        pearson_r, pearson_p = stats.pearsonr(predicted, actual)
        print(f"\n[1] 피어슨 상관계수:")
        print(f"    r = {pearson_r:.4f}, p-value = {pearson_p:.4f}")
        if pearson_p < 0.05:
            print(f"    ✓ 통계적으로 유의미 (p < 0.05)")
        else:
            print(f"    ✗ 통계적으로 유의미하지 않음")
    except Exception as e:
        print(f"\n[1] 피어슨 상관계수: 계산 오류 ({e})")
        pearson_r, pearson_p = None, None

    # 스피어만 순위 상관
    try:
        spearman_r, spearman_p = stats.spearmanr(predicted, actual)
        print(f"\n[2] 스피어만 순위 상관:")
        print(f"    r = {spearman_r:.4f}, p-value = {spearman_p:.4f}")
        if spearman_p < 0.05:
            print(f"    ✓ 통계적으로 유의미")
        else:
            print(f"    ✗ 통계적으로 유의미하지 않음")
    except Exception as e:
        print(f"\n[2] 스피어만 순위 상관: 계산 오류 ({e})")
        spearman_r, spearman_p = None, None

    # 기술 통계
    print(f"\n[3] 기술 통계:")
    print(f"    예측 수익률: 평균 {st.mean(predicted)*100:+.3f}%, 중앙값 {st.median(predicted)*100:+.3f}%")
    print(f"    실제 수익률: 평균 {st.mean(actual)*100:+.3f}%, 중앙값 {st.median(actual)*100:+.3f}%")

    if len(predicted) > 1:
        print(f"    예측 표준편차: {st.stdev(predicted)*100:.3f}%")
        print(f"    실제 표준편차: {st.stdev(actual)*100:.3f}%")

    # 신호별 분석
    print(f"\n[4] 신호별 분석:")

    bearish_records = [r for r in records if r["signal"] == "bearish"]
    bullish_records = [r for r in records if r["signal"] == "bullish"]

    if bearish_records:
        bearish_actual = [r["actual_return"] for r in bearish_records]
        bearish_predicted = [r["predicted_return"] for r in bearish_records]

        print(f"\n    약세 신호 ({len(bearish_records)}일):")
        print(f"      예측: {st.mean(bearish_predicted)*100:+.3f}%")
        print(f"      실제: {st.mean(bearish_actual)*100:+.3f}%")
        print(f"      승률: {sum(1 for r in bearish_actual if r > 0)/len(bearish_actual)*100:.1f}%")

    if bullish_records:
        bullish_actual = [r["actual_return"] for r in bullish_records]
        bullish_predicted = [r["predicted_return"] for r in bullish_records]

        print(f"\n    강세 신호 ({len(bullish_records)}일):")
        print(f"      예측: {st.mean(bullish_predicted)*100:+.3f}%")
        print(f"      실제: {st.mean(bullish_actual)*100:+.3f}%")
        print(f"      승률: {sum(1 for r in bullish_actual if r > 0)/len(bullish_actual)*100:.1f}%")

    # R²
    try:
        correlation_matrix = np.corrcoef(predicted, actual)
        r_squared = correlation_matrix[0, 1] ** 2
        print(f"\n[5] R² (설명력): {r_squared*100:.2f}%")
    except:
        r_squared = None

    return {
        "sample_size": len(records),
        "pearson_r": pearson_r,
        "pearson_p": pearson_p,
        "spearman_r": spearman_r,
        "spearman_p": spearman_p,
        "r_squared": r_squared,
        "records": records,
    }


def determine_readiness(validation):
    """실거래 준비 상태 판정."""
    if validation is None:
        return "NOT_READY", "데이터 부족"

    print("\n" + "=" * 100)
    print("🚀 실거래 준비 상태 판정")
    print("=" * 100)

    pearson_r = validation["pearson_r"]
    pearson_p = validation["pearson_p"]
    spearman_r = validation["spearman_r"]
    spearman_p = validation["spearman_p"]
    sample_size = validation["sample_size"]

    checks = []

    # 체크 1: 데이터 충분성
    if sample_size >= 30:
        checks.append(("데이터 충분성", True, "30개 이상"))
    else:
        checks.append(("데이터 충분성", False, f"{sample_size}개 (최소 30개)"))

    # 체크 2: 상관계수
    if pearson_r is not None:
        if abs(pearson_r) >= 0.3:
            checks.append(("상관계수 크기", True, f"|r| = {abs(pearson_r):.3f}"))
        else:
            checks.append(("상관계수 크기", False, f"|r| = {abs(pearson_r):.3f} (최소 0.3)"))

    # 체크 3: p-value
    if pearson_p is not None:
        if pearson_p < 0.05:
            checks.append(("통계적 유의성", True, f"p = {pearson_p:.4f}"))
        else:
            checks.append(("통계적 유의성", False, f"p = {pearson_p:.4f} (최소 0.05)"))

    print(f"\n✅ 체크리스트:")
    for name, passed, detail in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}: {detail}")

    # 최종 판정
    passed_count = sum(1 for _, p, _ in checks if p)
    total_count = len(checks)

    if passed_count == total_count:
        status = "READY"
        message = "실거래 시작 가능!"
    elif passed_count >= 2:
        status = "MONITOR"
        message = "추가 데이터 수집 중 (충분히 준비됨)"
    else:
        status = "NOT_READY"
        message = "더 많은 데이터 필요"

    print(f"\n📊 판정: {status} ({passed_count}/{total_count})")
    print(f"   {message}")

    return status, message


def save_validation_report(validation, status, message):
    """검증 결과 저장."""
    data_dir = S.BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)

    report = {
        "timestamp": str(__import__('datetime').datetime.now().isoformat()),
        "status": status,
        "message": message,
        "analysis": {
            "sample_size": validation["sample_size"] if validation else 0,
            "pearson_r": validation["pearson_r"] if validation else None,
            "pearson_p": validation["pearson_p"] if validation else None,
            "spearman_r": validation["spearman_r"] if validation else None,
            "spearman_p": validation["spearman_p"] if validation else None,
            "r_squared": validation["r_squared"] if validation else None,
        },
    }

    report_file = data_dir / f"validation_report_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.json"

    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 검증 보고서 저장: {report_file.name}")
    except Exception as e:
        print(f"⚠️  저장 오류: {e}")


def main():
    print("\n" + "=" * 100)
    print("상관성 검증 (Correlation Validation)")
    print("=" * 100)

    # 1. 데이터 로드
    print("\n[1] 종이거래 신호 데이터 로드...")
    records = load_paper_signals()
    print(f"✅ {len(records)}개 기록 로드")

    if len(records) == 0:
        print("⚠️  데이터가 없습니다. collect_paper_signals.py를 먼저 실행하세요.")
        return 1

    # 2. 상관성 검증
    print("\n[2] 상관성 검증...")
    validation = validate_correlation(records)

    # 3. 준비 상태 판정
    print("\n[3] 준비 상태 판정...")
    status, message = determine_readiness(validation)

    # 4. 결과 저장
    print("\n[4] 결과 저장...")
    save_validation_report(validation, status, message)

    # 최종 메시지
    print("\n" + "=" * 100)
    print("📌 다음 단계")
    print("=" * 100)

    if status == "READY":
        print("\n✅ 실거래 준비 완료!")
        print("   python trade_decision_simple.py")
        print("   python trade_execute_intraday.py")
    elif status == "MONITOR":
        print("\n🟡 추가 데이터 수집 중...")
        print("   계속 collect_paper_signals.py 실행")
        print("   주 1회 이 스크립트로 진행도 확인")
    else:
        print("\n🔴 더 많은 데이터 필요")
        print("   최소 30개 이상의 데이터 포인트 필요")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
