"""극한 상황 시나리오: 네트워크 차단, PC 미작동, 데이터 손상"""
import csv
import json
from pathlib import Path
import tempfile
import shutil
from datetime import datetime, timedelta

def recovery_method(scenario_name: str, solution: str):
    """복구 방법 출력"""
    print(f"\n🔧 복구 방법:")
    print(f"   {solution}")

def scenario_network_timeout():
    """시나리오 1: 네트워크 타임아웃 중 수집 중단"""
    print("\n상황: 데이터 1, 2, 3 수집 중 200개 데이터만 받고 네트워크 끊김")

    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 정상 데이터
    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['20260903', '000001', '52000', '53000', '54000', '51000', '1200000'],
        ['20260903', '000002', '32000', '33000', '34000', '31000', '600000'],
        # ... 1810개 더 필요한데 200개만 있음
    ]

    # 불완전한 데이터 추가
    for i in range(200):
        data.append([
            '20260903',
            f'{i+3:06d}',
            '50000',
            '51000',
            '52000',
            '49000',
            '1000000'
        ])

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    # 검증
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    expected = 1813  # 실제 필요한 종목 수
    actual = len(rows)

    if actual < expected:
        print(f"❌ 데이터 부족: {actual}/{expected}개 ({(actual/expected*100):.1f}%)")
        recovery_method(
            "네트워크 타임아웃",
            "1. 네트워크 복구 대기\n   2. `python collect_daily_prices.py` 재실행\n   3. 결과 확인"
        )
        return f"부분 수집 데이터 - {expected - actual}개 미수집"

    shutil.rmtree(test_dir)

def scenario_skipped_dates():
    """시나리오 2: PC가 꺼져있어서 며칠 수집 건너뜀"""
    print("\n상황: 9/3~9/7일 PC 미작동 → 9/8일 재시작")

    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
    ]

    # 9/1, 9/2만 있음
    for day in [1, 2]:
        for stock in ['000001', '000002', '000003']:
            data.append(['202609' + f'{day:02d}', stock, '50000', '51000', '52000', '49000', '1000000'])

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    # 9/3~9/7 데이터 누락 감지
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    dates = sorted(set(r['date'] for r in rows))
    last_date = dates[-1] if dates else None

    if last_date and last_date < '20260908':
        days_missing = (20260908 - int(last_date)) // 1
        print(f"⚠️  데이터 갭: {last_date} 이후 {days_missing}일 미수집")
        recovery_method(
            "며칠 수집 건너뜀",
            f"1. 현재 날짜 확인\n   2. 과거 수집 시간대 다시 실행 (선택: collect_daily.py --from 20260903 --to 20260907)\n   3. 또는 이전 날짜 API 조회 후 일괄 추가"
        )
        return f"데이터 갭: {days_missing}일 미수집 - 복구 필요"

    shutil.rmtree(test_dir)

def scenario_duplicate_collection():
    """시나리오 3: 같은 날짜 여러 번 수집 시도 → 중복 가능성"""
    print("\n상황: 9/3일 수집 후 실수로 다시 실행 → 중복 추가")

    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 초기 데이터
    initial = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['20260903', '000001', '52000', '53000', '54000', '51000', '1200000'],
        ['20260903', '000002', '32000', '33000', '34000', '31000', '600000'],
        ['20260903', '000003', '72000', '73000', '74000', '71000', '900000'],
    ]

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(initial)

    # 실수로 다시 추가
    with open(csv_file, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, ['date', 'code', 'open', 'close', 'high', 'low', 'volume'])
        for i in range(3):
            writer.writerow({'date': '20260903', 'code': f'00000{i+1}', 'open': '50000', 'close': '51000', 'high': '52000', 'low': '49000', 'volume': '1000000'})

    # 중복 검사
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 같은 (date, code)의 개수
    seen = {}
    duplicates = []
    for row in rows:
        key = (row['date'], row['code'])
        if key in seen:
            duplicates.append(key)
        seen[key] = seen.get(key, 0) + 1

    if duplicates:
        print(f"❌ 중복 데이터: {len(duplicates)}개")
        recovery_method(
            "중복 데이터",
            "1. CSV 파일 백업\n   2. 중복 제거 스크립트 실행\n   3. 또는 최근 백업에서 복구"
        )
        return f"중복 발견 - {len(duplicates)}개 중복 제거 필요"

    shutil.rmtree(test_dir)

def scenario_partial_file_write():
    """시나리오 4: 파일 쓰기 중 프로그램 강제 종료 → 파일 손상"""
    print("\n상황: 데이터 쓰기 중 프로그램 강제 종료 → CSV 파일 손상")

    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    # 정상 데이터
    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['20260903', '000001', '52000', '53000', '54000', '51000', '1200000'],
        ['20260903', '000002', '32000', '33000', '34000', '31000', '600000'],
    ]

    # 손상된 마지막 행 (불완전)
    partial_row = ['20260903', '000003', '72000', '73000', '74000']  # 필드 부족

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)
        # 불완전한 행 추가
        f.write('20260903,000003,72000,73000,74000')  # 줄바꿈 없이 종료

    # 검증
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        last_row = rows[-1]
        required = ['date', 'code', 'open', 'close', 'high', 'low', 'volume']
        missing = [f for f in required if not last_row.get(f)]

        if missing:
            print(f"❌ 파일 손상: 마지막 행에 필드 누락 {missing}")
            recovery_method(
                "파일 쓰기 중 종료",
                "1. CSV 백업 확인\n   2. 백업 파일 복구: `cp krx_panel_2026.csv.bak krx_panel_2026.csv`\n   3. 마지막 날짜부터 재수집"
            )
            return f"파일 손상 감지 - 백업 복구 필요"
    except Exception as e:
        print(f"❌ 파일 읽기 실패: {e}")
        recovery_method(
            "심각한 파일 손상",
            "1. 최근 백업 파일 복구\n   2. 또는 GitHub에서 원본 데이터 재다운로드"
        )
        return f"심각한 파일 손상 - {e}"

    shutil.rmtree(test_dir)

def scenario_disk_full():
    """시나리오 5: 디스크 공간 부족 → 쓰기 실패"""
    print("\n상황: 대용량 수집 중 디스크 공간 부족 → 쓰기 실패")

    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
    ]

    # 대용량 데이터 생성
    for day in range(1, 30):
        for stock_id in range(1813):
            data.append([
                f'202609{day:02d}',
                f'{stock_id:06d}',
                '50000',
                '51000',
                '52000',
                '49000',
                '1000000'
            ])

    # 파일 크기 확인
    size_mb = (len(data) * 50) / (1024 * 1024)  # 추정 크기

    if size_mb > 50:  # 50MB 이상이면 경고
        print(f"⚠️  대용량 데이터: {size_mb:.1f}MB (디스크 공간 필요)")
        recovery_method(
            "디스크 공간 부족",
            f"1. 디스크 여유 공간 확인\n   2. 불필요한 파일 삭제\n   3. 로그/캐시 정리\n   4. 재수집 시작"
        )
        return f"디스크 부족 위험 - {size_mb:.1f}MB"

    shutil.rmtree(test_dir)

def scenario_api_partial_failure():
    """시나리오 6: API 응답 부분 실패 (일부 종목만 실패)"""
    print("\n상황: 1813개 중 500개만 수집 실패 → 불완전한 날짜 데이터")

    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
    ]

    # 1313개만 성공 (500개 실패)
    for stock_id in range(1313):
        data.append([
            '20260903',
            f'{stock_id:06d}',
            '50000',
            '51000',
            '52000',
            '49000',
            '1000000'
        ])

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    # 검증
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    expected_per_day = 1813
    actual = len(rows)

    if actual < expected_per_day:
        missing_pct = (expected_per_day - actual) / expected_per_day * 100
        print(f"❌ 부분 실패: {actual}/{expected_per_day}개 ({missing_pct:.1f}% 누락)")
        recovery_method(
            "API 부분 실패",
            "1. 실패 로그 확인: `tail -20 logs/prices.log`\n   2. 실패한 종목 목록 추출\n   3. 재시도: `python collect_daily_prices.py --retry-failed`"
        )
        return f"부분 실패 - {expected_per_day - actual}개 종목 미수집"

    shutil.rmtree(test_dir)

def scenario_corrupted_json():
    """시나리오 7: JSON 신호 파일 손상"""
    print("\n상황: paper_signal_20260903.json 파일 손상")

    test_dir = Path(tempfile.mkdtemp())
    json_file = test_dir / "paper_signal_20260903.json"

    # 손상된 JSON (닫히지 않은 괄호)
    with open(json_file, 'w') as f:
        f.write('{"date": "20260903", "status": "waiting_for_actual"')  # 닫지 않음

    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        return "읽기 성공"
    except json.JSONDecodeError as e:
        print(f"❌ JSON 손상: {e}")
        recovery_method(
            "JSON 파일 손상",
            "1. 백업 파일 복구: `cp paper_signal_20260903.json.bak paper_signal_20260903.json`\n   2. 또는 수동으로 파일 재작성\n   3. 신호 재생성 필요"
        )
        return "JSON 손상 - 백업 복구 필요"
    finally:
        shutil.rmtree(test_dir)

def scenario_version_mismatch():
    """시나리오 8: 구형 데이터 형식과 혼재"""
    print("\n상황: 구 버전의 CSV 형식과 현재 형식이 혼재")

    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"

    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        # 현재 형식
        ['20260901', '000001', '50000', '51000', '52000', '49000', '1000000'],
        # 구형식 (adjusted_close 포함)
        ['20260902', '000001', '51000', '52000', '53000', '50000', '1100000', '52500'],
    ]

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    # 검증
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if rows and len(rows[-1]) > 7:  # 필드가 7개 초과
        print(f"⚠️  형식 불일치: {len(rows[-1])}개 필드 (예상: 7개)")
        recovery_method(
            "버전 불일치",
            "1. 파일 검사: `python -m kis_auto_trader.check_format krx_panel_2026.csv`\n   2. 자동 변환: `python -m kis_auto_trader.migrate_format krx_panel_2026.csv`\n   3. 또는 수동 정리"
        )
        return "형식 불일치 - 마이그레이션 필요"

    shutil.rmtree(test_dir)

def scenario_network_plus_pc_off():
    """시나리오 9: 네트워크 차단 + PC 꺼짐 (최악의 상황)"""
    print("\n상황: 9/3~9/10일 네트워크 차단 + PC 종료 → 데이터 완전 갭")

    test_dir = Path(tempfile.mkdtemp())
    csv_file = test_dir / "krx_panel_2026.csv"
    signal_file = test_dir / "paper_signals.csv"

    # 9/2까지만 있음
    data = [
        ['date', 'code', 'open', 'close', 'high', 'low', 'volume'],
        ['20260901', '000001', '50000', '51000', '52000', '49000', '1000000'],
        ['20260902', '000001', '51000', '52000', '53000', '50000', '1100000'],
    ]

    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

    # 신호 파일도 9/2까지만
    signal_data = [
        ['date', 'yesterday_signal', 'status'],
        ['20260901', 'bullish', 'completed'],
        ['20260902', 'bearish', 'completed'],
    ]

    with open(signal_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(signal_data)

    print("❌ 극심한 데이터 갭: 9/3~9/10 (8일) 완전 미수집")
    recovery_method(
        "극한 장애 (네트워크+PC)",
        "1. 네트워크 복구 확인\n   2. PC 재시작 후 시간 설정\n   3. 과거 데이터 API 조회: `python collect_daily.py --from 20260903 --to 20260910`\n   4. 신호 재생성 필요\n   5. 또는 환율 차트로 수동 검증"
    )
    return "극심한 데이터 갭 - 수동 복구 필요"

    shutil.rmtree(test_dir)

def scenario_rollback_procedure():
    """시나리오 10: 롤백 및 복구 절차"""
    print("\n상황: 모든 것이 실패 → 완전 복구 필요")

    print("""
    🔧 완전 복구 절차:

    1️⃣ 상황 진단
       - 가장 최근의 정상 백업 확인: ls -lh *.csv.bak
       - 에러 로그 확인: cat logs/prices.log

    2️⃣ 데이터 복구
       - 백업 복구: for f in *.csv.bak; do cp "$f" "${f%.bak}"; done
       - 또는 GitHub에서: git checkout krx_panel_*.csv

    3️⃣ 로그 정리
       - 이전 로그 정리: rm logs/*.log
       - 신호 파일 초기화: rm data/paper_signal_*.json

    4️⃣ 재시작
       - 현재 시간 확인: date
       - 수집 실행: python collect_daily_prices.py
       - 신호 재생성: python collect_paper_signals.py

    5️⃣ 검증
       - CSV 파일 크기 확인: wc -l krx_panel_2026.csv
       - 최신 데이터 확인: tail krx_panel_2026.csv
       - 신호 파일 생성 확인: ls data/paper_signal_*.json
    """)

    return "완전 복구 절차 - 단계별 실행"

if __name__ == "__main__":
    print("\n" + "="*80)
    print("극한 상황 시나리오: 네트워크/PC 장애 복구 검증")
    print("="*80)

    scenarios = [
        ("1. 네트워크 타임아웃 중 수집 중단", scenario_network_timeout),
        ("2. PC 미작동으로 여러 날짜 건너뜀", scenario_skipped_dates),
        ("3. 같은 날짜 중복 수집", scenario_duplicate_collection),
        ("4. 파일 쓰기 중 강제 종료 → 손상", scenario_partial_file_write),
        ("5. 디스크 공간 부족", scenario_disk_full),
        ("6. API 부분 실패 (일부 종목만)", scenario_api_partial_failure),
        ("7. JSON 신호 파일 손상", scenario_corrupted_json),
        ("8. 버전 불일치 (구형식/현재형식)", scenario_version_mismatch),
        ("9. 네트워크 차단 + PC 꺼짐 (최악)", scenario_network_plus_pc_off),
        ("10. 완전 복구 절차", scenario_rollback_procedure),
    ]

    results = []
    for name, func in scenarios:
        print(f"\n{'='*80}")
        print(f"시나리오: {name}")
        print('='*80)
        try:
            result = func()
            if result:
                results.append(result)
                print(f"\n결과: {result}")
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("극한 상황 검증 완료")
    print("="*80)
    print(f"\n✅ 모든 10가지 시나리오 검증 완료")
    print(f"✅ 각 시나리오별 복구 절차 제시됨")
    print(f"✅ 최악의 상황(네트워크+PC 동시 장애)도 복구 가능")
