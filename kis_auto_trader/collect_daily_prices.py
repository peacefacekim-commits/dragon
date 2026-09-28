"""매일 KIS API로 최신 시세 데이터 수집

실행: 매일 08:00 (시장 개장 1시간 30분 전)
→ 전날 마감 데이터를 수집하여 krx_panel 업데이트
"""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

import strategy as S
from auth import get_access_token, get_hashkey
from common import Config as _Config


load_dotenv()


class SimpleConfig:
    """KIS API 호출용 최소 설정."""
    def __init__(self):
        self.mode = "mock"  # 시세 조회는 모의/실전 동일
        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")
        self.base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")


def get_daily_price(cfg, code: str, date: str = None) -> dict | None:
    """단일 종목의 최신 1일 데이터 조회."""
    url = f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"

    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {get_access_token(cfg)}",
        "appkey": cfg.app_key,
        "appsecret": cfg.app_secret,
        "tr_id": "FHKST03010100",  # 일봉
        "custtype": "P",
    }

    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": code,
        "fid_org_adj_prc": "0",
        "fid_period_div_code": "D",
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()

        if data.get("rt_cd") != "0":
            return None

        items = data.get("output", [])
        if not items:
            return None

        latest = items[0]  # 최신부터 내림차순
        return {
            'date': latest.get('stck_bsop_date'),
            'open': int(latest.get('stck_oprc', 0)),
            'close': int(latest.get('stck_clpr', 0)),
            'high': int(latest.get('stck_hgpr', 0)),
            'low': int(latest.get('stck_lwpr', 0)),
            'volume': int(latest.get('cntg_vol', 0)),
        }
    except Exception as e:
        print(f"  ✗ {code}: {e}")
        return None


def validate_csv_integrity(csv_path: Path) -> bool:
    """CSV 파일 무결성 검증"""
    if not csv_path.exists():
        return False

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return False

        # 헤더 검증
        required_fields = ['date', 'code', 'open', 'close', 'high', 'low', 'volume']
        if reader.fieldnames is None or not all(f in reader.fieldnames for f in required_fields):
            print(f"  ✗ CSV 헤더 오류: {reader.fieldnames}")
            return False

        # 마지막 행 데이터 검증
        last_row = rows[-1]
        if not last_row.get('date') or len(last_row['date']) != 8:
            print(f"  ✗ 날짜 형식 오류: {last_row.get('date')}")
            return False

        return True
    except Exception as e:
        print(f"  ✗ CSV 검증 실패: {e}")
        return False

def collect_and_append_prices():
    """KIS API로 최신 시세를 받아 krx_panel에 추가."""
    cfg = SimpleConfig()
    dates, panel = S.load_panel(verbose=False)

    # CSV 무결성 검증 추가
    csv_path = Path(S.DATA_DIR) / f"{S.PANEL_PREFIX}_2026.csv"
    if not validate_csv_integrity(csv_path):
        print(f"  ✗ CSV 파일이 손상되었습니다: {csv_path}")
        print(f"  파일을 확인하거나 백업에서 복구해주세요.")
        return

    last_date = dates[-1]
    last_year = int(last_date[:4])

    # krx_panel_YYYY.csv 파일 경로
    csv_path = S.DATA_DIR / f"{S.PANEL_PREFIX}_{last_year}.csv"

    print(f"마지막 기록: {last_date}")
    print(f"수집 대상: {len(panel)}개 종목")
    print(f"저장 파일: {csv_path.name}\n")

    # 종목별로 최신 가격 수집
    new_records = []
    failed = []

    codes = sorted(panel.keys())
    for i, code in enumerate(codes, 1):
        price = get_daily_price(cfg, code)

        if price:
            new_date = price['date']

            # 이미 수집한 날짜면 스킵
            if new_date == last_date:
                continue

            new_records.append({
                'date': new_date,
                'code': code,
                'open': price['open'],
                'close': price['close'],
                'high': price['high'],
                'low': price['low'],
                'volume': price['volume'],
            })
        else:
            failed.append(code)

        if i % 100 == 0:
            print(f"  [{i}/{len(codes)}] 진행 중... (신규: {len(new_records)})")

    print(f"\n✅ 수집 완료: {len(new_records)}개 신규 데이터")

    if failed:
        print(f"⚠️  실패: {len(failed)}개")

    if not new_records:
        print("신규 데이터 없음 (이미 최신)")
        return

    # CSV 저장
    fieldnames = ['date', 'code', 'open', 'close', 'high', 'low', 'volume']

    if csv_path.exists():
        # 기존 파일에 append
        with open(csv_path, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerows(new_records)
        print(f"✅ CSV 추가: {csv_path.name} (+{len(new_records)}행)")
    else:
        # 새 파일 생성
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(new_records)
        print(f"✅ CSV 생성: {csv_path.name} ({len(new_records)}행)")


def main():
    print("\n" + "=" * 80)
    print("일봉 시세 데이터 수집 (Daily Prices)")
    print("=" * 80)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        collect_and_append_prices()
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "=" * 80)
    print("[완료]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
