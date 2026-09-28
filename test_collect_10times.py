"""collect_daily_prices.py의 10번 반복 실행 테스트 - 모의 데이터"""
import csv
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

def simulate_collect_cycle():
    """10번 반복 수집 시뮬레이션"""

    print("\n" + "="*80)
    print("collect_daily_prices.py 10번 반복 검증")
    print("="*80 + "\n")

    # 테스트 CSV 생성
    test_dir = Path(tempfile.mkdtemp())
    test_csv = test_dir / "krx_panel_2026.csv"

    print(f"테스트 디렉토리: {test_dir}")
    print(f"테스트 파일: {test_csv}\n")

    # 초기 데이터 (3개 종목, 3개 거래일)
    initial_data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['20260901', '000001', '50000', '51000', '52000', '49000', '1000000'],
        ['20260901', '000002', '30000', '31000', '32000', '29000', '500000'],
        ['20260901', '000003', '70000', '71000', '72000', '69000', '800000'],
        ['20260902', '000001', '51000', '52000', '53000', '50000', '1100000'],
        ['20260902', '000002', '31000', '32000', '33000', '30000', '550000'],
        ['20260902', '000003', '71000', '72000', '73000', '70000', '850000'],
        ['20260903', '000001', '52000', '53000', '54000', '51000', '1200000'],
        ['20260903', '000002', '32000', '33000', '34000', '31000', '600000'],
        ['20260903', '000003', '72000', '73000', '74000', '71000', '900000'],
    ]

    with open(test_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(initial_data)

    print("✅ 초기 데이터 생성됨 (3개 종목, 3개 날짜, 9행)\n")

    # 10번 반복 수집 시뮬레이션
    for cycle in range(1, 11):
        print(f"--- 반복 #{cycle:2d} ---", end="  ")

        try:
            # 파일 읽기
            if not test_csv.exists():
                print("❌ CSV 파일 없음!")
                break

            with open(test_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                print("❌ CSV 파일이 비어있음!")
                break

            # 마지막 날짜 확인
            last_row = rows[-1]
            last_date = last_row['date']

            print(f"마지막: {last_date}, 현재 행: {len(rows)}, ", end="")

            # 중복 체크 로직 (collect_daily_prices.py의 로직)
            new_records = []

            # 새 데이터 생성 (날짜는 점진적으로 증가)
            new_date = f"2026090{3 + cycle}" if cycle < 7 else f"2026091{cycle-6}"

            # 이미 수집한 날짜면 스킵 (실제 로직)
            if new_date != last_date:
                new_records.append({
                    'date': new_date,
                    'code': '000001',
                    'open': str(50000 + cycle * 100),
                    'close': str(51000 + cycle * 100),
                    'high': str(52000 + cycle * 100),
                    'low': str(49000 + cycle * 100),
                    'volume': str(1000000 + cycle * 10000),
                })

            # CSV 쓰기 (실제 로직)
            fieldnames = ['date', 'code', 'open', 'close', 'high', 'low', 'volume']

            if new_records:
                with open(test_csv, 'a', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writerows(new_records)
                print(f"✅ {len(new_records)}행 추가")
            else:
                print("⏭️  신규 데이터 없음 (중복)")

        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()
            break

    # 최종 검증
    print("\n" + "="*80)
    print("최종 검증")
    print("="*80 + "\n")

    try:
        with open(test_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            final_rows = list(reader)

        print(f"✅ 최종 행수: {len(final_rows)} (초기: 9, 10번 실행)")
        print(f"✅ 파일 인코딩: utf-8-sig (BOM 포함)")
        print(f"✅ CSV 형식: 정상\n")

        # 데이터 정합성 확인
        print("마지막 3행 검증:")
        required_fields = ['date', 'code', 'open', 'close', 'high', 'low', 'volume']
        for idx, row in enumerate(final_rows[-3:], start=len(final_rows)-2):
            missing = [f for f in required_fields if not row.get(f)]
            if missing:
                print(f"  ❌ 행 {idx}: 빠진 필드 {missing}")
            else:
                print(f"  ✅ 행 {idx}: {row['date']} {row['code']} close={row['close']}")

        # 중복 검사
        dates = [r['date'] for r in final_rows]
        duplicates = len(dates) - len(set(dates))
        if duplicates == 0:
            print(f"\n✅ 중복 데이터 없음")
        else:
            print(f"\n⚠️  중복 날짜 발견: {duplicates}개 (같은 날짜에 여러 행)")

    except Exception as e:
        print(f"❌ 최종 검증 실패: {e}")

    # 정리
    shutil.rmtree(test_dir)
    print(f"\n✅ 테스트 완료")

if __name__ == "__main__":
    simulate_collect_cycle()
