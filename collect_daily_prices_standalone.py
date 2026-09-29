"""KIS API를 통한 일일 주가 데이터 수집 (로컬 독립형)

실행: python collect_daily_prices_standalone.py
- 환경 변수: KIS_REAL_APP_KEY, KIS_REAL_APP_SECRET, KIS_BASE_URL (from .env)
- 또는: KIS_APP_KEY, KIS_APP_SECRET (모의투자용)
- 수집 대상: 명시한 종목 코드 리스트
"""
import csv
import json
import base64
import hashlib
import hmac
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
import os

load_dotenv()


class KisConfig:
    """KIS API 호출용 설정."""
    def __init__(self):
        self.app_key = os.getenv("KIS_REAL_APP_KEY") or os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_REAL_APP_SECRET") or os.getenv("KIS_APP_SECRET")
        self.base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")

        if not self.app_key or not self.app_secret:
            raise ValueError("❌ .env에 다음이 필요합니다: KIS_REAL_APP_KEY + KIS_REAL_APP_SECRET (또는 KIS_APP_KEY + KIS_APP_SECRET)")


def get_access_token(cfg: KisConfig) -> Optional[str]:
    """KIS API 접근 토큰 획득."""
    url = f"{cfg.base_url}/oauth2/tokenP"

    headers = {
        "content-type": "application/json",
    }

    body = {
        "grant_type": "client_credentials",
        "appkey": cfg.app_key,
        "appsecret": cfg.app_secret,
    }

    try:
        res = requests.post(url, headers=headers, json=body, timeout=10, verify=False)
        res.raise_for_status()
        data = res.json()

        return data.get("access_token")
    except Exception as e:
        print(f"  ✗ 토큰 획득 실패: {e}")
        return None


def get_daily_price(cfg: KisConfig, token: str, code: str) -> Optional[dict]:
    """단일 종목의 최신 1일 데이터 조회."""
    url = f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"

    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
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
        res = requests.get(url, headers=headers, params=params, timeout=10, verify=False)
        res.raise_for_status()
        data = res.json()

        if data.get("rt_cd") != "0":
            msg = data.get("msg", "알 수 없는 오류")
            print(f"  ✗ {code}: API 오류 [{data.get('rt_cd')}] {msg}")
            print(f"     응답: {json.dumps(data, ensure_ascii=False)[:300]}")
            return None

        items = data.get("output", [])
        if not items:
            print(f"    [DEBUG] {code}: 데이터 없음")
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
        print(f"  ✗ {code}: {type(e).__name__}: {str(e)[:200]}")
        return None


def collect_prices(codes: list, output_dir: Optional[Path] = None):
    """주가 데이터 수집 및 CSV 저장."""
    cfg = KisConfig()

    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n" + "=" * 80)
    print("일봉 시세 데이터 수집 (Daily Prices)")
    print("=" * 80)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"저장 폴더: {output_dir}\n")

    # 토큰 획득
    token = get_access_token(cfg)
    if not token:
        print("❌ 토큰 획득 실패")
        return False

    print(f"✅ 토큰 획득 성공\n")
    print(f"수집 대상: {len(codes)}개 종목\n")

    # 데이터 수집
    records = []
    failed = []

    for i, code in enumerate(codes, 1):
        price = get_daily_price(cfg, token, code)

        if price:
            records.append({
                'date': price['date'],
                'code': code,
                'open': price['open'],
                'close': price['close'],
                'high': price['high'],
                'low': price['low'],
                'volume': price['volume'],
            })
            print(f"  ✓ {code}: {price['date']} (종가: {price['close']})")
        else:
            failed.append(code)
            print(f"  ✗ {code}: 데이터 조회 실패")

        if i % 50 == 0:
            print(f"  → [{i}/{len(codes)}] 진행 중...")

    print(f"\n✅ 수집 완료: {len(records)}개 데이터")
    if failed:
        print(f"⚠️  실패: {len(failed)}개")

    if not records:
        print("신규 데이터 없음")
        return False

    # CSV 저장
    csv_path = output_dir / "prices.csv"
    fieldnames = ['date', 'code', 'open', 'close', 'high', 'low', 'volume']

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"✅ CSV 저장: {csv_path.name} ({len(records)}행)\n")
    return True


def main():
    # 예제: 수집할 종목 코드 (실제 코드로 변경 필요)
    # Format: "005930" (삼성전자), "000660" (SK하이닉스) 등
    codes = [
        "005930",  # 삼성전자
        "000660",  # SK하이닉스
    ]

    print(f"코드를 수정해서 실행하세요: {codes}")
    print("collect_prices() 함수 내 codes 리스트를 변경하면 원하는 종목을 수집할 수 있습니다.\n")

    # 실행: 현재 폴더에 저장
    success = collect_prices(codes)

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
