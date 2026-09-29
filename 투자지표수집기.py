"""투자 지표 수집 프로그램 (Windows PC용 독립형)

매일 실행해서 다음 지표들을 수집:
- 일봉 시세 (종목별 OHLCV)
- 시장 지표 (코스피, 코스닥, 외국인, 기관, 개인 등)
- 미국 시장 (S&P500, 나스닥, VIX 등)

실행: python 투자지표수집기.py
"""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import os

import requests
from dotenv import load_dotenv

load_dotenv()


class KisConfig:
    """KIS API 설정."""
    def __init__(self):
        self.app_key = os.getenv("KIS_REAL_APP_KEY") or os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_REAL_APP_SECRET") or os.getenv("KIS_APP_SECRET")
        self.base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")

        if not self.app_key or not self.app_secret:
            raise ValueError("❌ .env에 필요: KIS_REAL_APP_KEY + KIS_REAL_APP_SECRET")


def get_access_token(cfg: KisConfig) -> Optional[str]:
    """토큰 획득."""
    url = f"{cfg.base_url}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": cfg.app_key,
        "appsecret": cfg.app_secret,
    }
    try:
        res = requests.post(url, json=body, timeout=10)
        res.raise_for_status()
        return res.json().get("access_token")
    except Exception as e:
        print(f"  ✗ 토큰 획득 실패: {e}")
        return None


def get_daily_price(cfg: KisConfig, token: str, code: str) -> Optional[dict]:
    """단일 종목 일봉 데이터."""
    url = f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": cfg.app_key,
        "appsecret": cfg.app_secret,
        "tr_id": "FHKST03010100",
        "custtype": "P",
    }
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": code,
        "fid_input_date_1": "20000101",
        "fid_input_date_2": "20991231",
        "fid_org_adj_prc": "0",
        "fid_period_div_code": "D",
    }
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()

        print(f"  [DEBUG] {code}: 전체 응답 = {json.dumps(data, ensure_ascii=False)[:800]}")

        if data.get("rt_cd") != "0":
            msg = data.get("msg1", data.get("msg", "알 수 없는 오류"))
            print(f"  ✗ {code}: API 오류 [{data.get('rt_cd')}] {msg}")
            return None

        items = data.get("output", [])
        if not items:
            print(f"  ✗ {code}: 데이터 없음 (output 비어있음)")
            return None

        latest = items[0]
        return {
            'date': latest.get('stck_bsop_date'),
            'open': int(latest.get('stck_oprc', 0)),
            'close': int(latest.get('stck_clpr', 0)),
            'high': int(latest.get('stck_hgpr', 0)),
            'low': int(latest.get('stck_lwpr', 0)),
            'volume': int(latest.get('cntg_vol', 0)),
        }
    except Exception as e:
        print(f"  ✗ {code}: 예외 발생 - {type(e).__name__}: {str(e)[:300]}")
        return None


def collect_indicators(codes: list, output_dir: Optional[Path] = None):
    """투자 지표 수집."""
    cfg = KisConfig()

    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n" + "=" * 80)
    print("투자 지표 수집 프로그램")
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
            print(f"  ✓ {code}: {price['date']} (종가: {price['close']:,}원)")
        else:
            failed.append(code)

        if i % 50 == 0:
            print(f"  → [{i}/{len(codes)}] 진행 중...")

    print(f"\n✅ 수집 완료: {len(records)}개 데이터")
    if failed:
        print(f"⚠️  실패: {len(failed)}개")

    if not records:
        print("신규 데이터 없음")
        return False

    # CSV 저장
    csv_path = output_dir / "투자_지표.csv"
    fieldnames = ['date', 'code', 'open', 'close', 'high', 'low', 'volume']

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"✅ CSV 저장: {csv_path.name} ({len(records)}행)\n")
    return True


def main():
    # 수집할 종목 코드 (필요에 따라 추가)
    codes = [
        "005930",  # 삼성전자
        "000660",  # SK하이닉스
        "005380",  # 현대차
        "051910",  # LG화학
        "207940",  # SK바이오팜
    ]

    # 실행
    success = collect_indicators(codes)
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
