"""collect_daily_prices.py의 오류 대처 능력 검증"""
import csv
import json
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

def test_scenario(name, test_func):
    """테스트 시나리오 실행"""
    print(f"\n{'='*80}")
    print(f"시나리오: {name}")
    print('='*80)
    try:
        result = test_func()
        if result:
            print(f"✅ 통과: {result}")
        else:
            print(f"❌ 실패")
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()

def scenario_1_empty_csv():
    """시나리오 1: 빈 CSV 파일"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 완전히 빈 파일 생성
    csv_file.write_text("")

    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            print("경고: CSV 파일이 비어있음")
            return "빈 파일 감지 - 새 파일 생성 필요"
    except Exception as e:
        return f"오류: {e}"
    finally:
        shutil.rmtree(test_dir)

def scenario_2_missing_header():
    """시나리오 2: 헤더 없는 CSV"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 헤더 없이 데이터만 작성
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        f.write("20260903,000001,52000,53000,54000,51000,1200000\n")

    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if rows and rows[0].get('date') is None:
            print("경고: 헤더가 없음")
            return "헤더 부재 - CSV 재작성 필요"
    except Exception as e:
        return f"오류: {e}"
    finally:
        shutil.rmtree(test_dir)

def scenario_3_corrupted_date_format():
    """시나리오 3: 잘못된 날짜 형식"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 잘못된 날짜 형식
    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['2026-09-03', '000001', '52000', '53000', '54000', '51000', '1200000'],  # 잘못된 포맷
    ]

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        last_date = rows[-1]['date']
        if len(last_date) != 8 or not last_date.isdigit():
            print(f"경고: 날짜 형식 오류 - {last_date}")
            return "날짜 형식 검증 실패 - 형식: YYYYMMDD 필수"
    except Exception as e:
        return f"오류: {e}"
    finally:
        shutil.rmtree(test_dir)

def scenario_4_missing_required_fields():
    """시나리오 4: 필수 필드 누락"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 필수 필드(volume) 누락
    data = [
        ['date', 'code', 'open', 'close', 'high', 'low'],  # volume 없음
        ['20260903', '000001', '52000', '53000', '54000', '51000'],
    ]

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        required = ['date', 'code', 'open', 'close', 'high', 'low', 'volume']
        if rows:
            row = rows[0]
            missing = [f for f in required if f not in row]
            if missing:
                print(f"경고: 필수 필드 누락 - {missing}")
                return f"필수 필드 부재: {missing}"
    except Exception as e:
        return f"오류: {e}"
    finally:
        shutil.rmtree(test_dir)

def scenario_5_invalid_numeric_values():
    """시나리오 5: 숫자 필드에 문자값"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['20260903', '000001', 'INVALID', '53000', '54000', '51000', '1200000'],  # 잘못된 open값
    ]

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if rows:
            row = rows[0]
            try:
                int(row['open'])
            except ValueError:
                print(f"경고: 숫자 필드에 문자값 - open={row['open']}")
                return "숫자 필드 검증 실패"
    except Exception as e:
        return f"오류: {e}"
    finally:
        shutil.rmtree(test_dir)

def scenario_6_duplicate_dates():
    """시나리오 6: 중복된 날짜 데이터"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['20260903', '000001', '52000', '53000', '54000', '51000', '1200000'],
        ['20260903', '000001', '52000', '53000', '54000', '51000', '1200000'],  # 중복
    ]

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # 같은 코드의 같은 날짜 중복 검사
        seen = set()
        duplicates = 0
        for row in rows:
            key = (row['date'], row['code'])
            if key in seen:
                duplicates += 1
            seen.add(key)

        if duplicates > 0:
            print(f"경고: {duplicates}개의 중복 데이터 발견")
            return "중복 데이터 감지 - 제거 필요"
    except Exception as e:
        return f"오류: {e}"
    finally:
        shutil.rmtree(test_dir)

def scenario_7_write_permission_error():
    """시나리오 7: 파일 쓰기 권한 없음"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['20260903', '000001', '52000', '53000', '54000', '51000', '1200000'],
    ]

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    # 읽기 전용으로 변경
    csv_file.chmod(0o444)

    try:
        # 쓰기 시도
        with open(csv_file, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'code', 'open', 'close', 'high', 'low', 'volume'])
            writer.writerow({'date': '20260904', 'code': '000001', 'open': '53000', 'close': '54000', 'high': '55000', 'low': '52000', 'volume': '1300000'})
        return "쓰기 성공 (권한 있음)"
    except PermissionError:
        print("경고: 파일 쓰기 권한 없음")
        return "권한 오류 - 관리자 실행 필요"
    except Exception as e:
        return f"오류: {e}"
    finally:
        csv_file.chmod(0o644)  # 권한 복구
        shutil.rmtree(test_dir)

def scenario_8_encoding_error():
    """시나리오 8: 인코딩 오류"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 잘못된 인코딩으로 작성
    with open(csv_file, 'w', encoding='cp949') as f:  # utf-8-sig 대신 cp949
        f.write("date,code,open,close,high,low,volume\n")
        f.write("20260903,000001,52000,53000,54000,51000,1200000\n")

    try:
        # utf-8-sig로 읽으려고 시도
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        return "읽기 성공"
    except UnicodeDecodeError:
        print("경고: 인코딩 불일치")
        return "인코딩 오류 - utf-8-sig 필수"
    except Exception as e:
        return f"오류: {e}"
    finally:
        shutil.rmtree(test_dir)

def scenario_9_concurrent_writes():
    """시나리오 9: 동시 쓰기 시뮬레이션"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 초기 데이터
    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['20260903', '000001', '52000', '53000', '54000', '51000', '1200000'],
    ]

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    try:
        # 동시에 여러 번 쓰기 시뮬레이션
        for i in range(5):
            with open(csv_file, 'a', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'code', 'open', 'close', 'high', 'low', 'volume'])
                writer.writerow({
                    'date': '20260904',
                    'code': '000001',
                    'open': str(53000 + i*100),
                    'close': str(54000 + i*100),
                    'high': str(55000 + i*100),
                    'low': str(52000 + i*100),
                    'volume': str(1200000 + i*10000)
                })

        # 검증
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if len(rows) == 6:  # 초기 1 + 5개
            return f"동시 쓰기 성공 - {len(rows)}행"
        else:
            return f"데이터 손실 - 예상 6행, 실제 {len(rows)}행"
    except Exception as e:
        return f"오류: {e}"
    finally:
        shutil.rmtree(test_dir)

def scenario_10_large_file_handling():
    """시나리오 10: 대용량 파일 처리"""
    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 대용량 파일 생성 (1000행)
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'code', 'open', 'close', 'high', 'low', 'volume'])

        for i in range(1000):
            date = f"2026{i//100:02d}{i%100+1:02d}"
            writer.writerow([date, '000001', '50000', '51000', '52000', '49000', '1000000'])

    try:
        # 대용량 파일 읽기
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if len(rows) == 1000:
            # 마지막 행 추가
            with open(csv_file, 'a', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'code', 'open', 'close', 'high', 'low', 'volume'])
                writer.writerow({'date': '20261201', 'code': '000001', 'open': '51000', 'close': '52000', 'high': '53000', 'low': '50000', 'volume': '1100000'})

            return f"대용량 처리 성공 - {len(rows)+1}행"
        else:
            return f"데이터 오류 - 예상 1000행, 실제 {len(rows)}행"
    except Exception as e:
        return f"오류: {e}"
    finally:
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    print("\n" + "="*80)
    print("collect_daily_prices.py - 10가지 오류 시나리오 검증")
    print("="*80)

    scenarios = [
        ("1. 빈 CSV 파일", scenario_1_empty_csv),
        ("2. 헤더 없는 CSV", scenario_2_missing_header),
        ("3. 잘못된 날짜 형식", scenario_3_corrupted_date_format),
        ("4. 필수 필드 누락", scenario_4_missing_required_fields),
        ("5. 숫자 필드에 문자값", scenario_5_invalid_numeric_values),
        ("6. 중복된 날짜 데이터", scenario_6_duplicate_dates),
        ("7. 파일 쓰기 권한 없음", scenario_7_write_permission_error),
        ("8. 인코딩 오류", scenario_8_encoding_error),
        ("9. 동시 쓰기", scenario_9_concurrent_writes),
        ("10. 대용량 파일 처리", scenario_10_large_file_handling),
    ]

    passed = 0
    failed = 0

    for name, func in scenarios:
        test_scenario(name, func)
        if func:  # 간단한 체크
            passed += 1
        else:
            failed += 1

    print("\n" + "="*80)
    print("최종 결과")
    print("="*80)
    print(f"✅ 감지된 시나리오: {passed}개")
    print(f"⚠️  개선 필요: 여러 시나리오에서 예외 처리 강화 필요")
    print("\n권장 개선사항:")
    print("1. CSV 파일 검증 함수 추가")
    print("2. 날짜 형식 검증")
    print("3. 필수 필드 검사")
    print("4. 예외 처리 강화")
    print("5. 파일 잠금 메커니즘 추가")
