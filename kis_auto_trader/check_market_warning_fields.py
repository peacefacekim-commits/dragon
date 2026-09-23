"""
KIS 현재가 조회(FHKST01010100) 응답에 시장경고코드(관리종목/투자경고/투자위험/
단기과열 등) 관련 필드가 실제로 오는지 확인하는 진단 스크립트 (2026-09-03 추가).

api_client.get_quote()는 지금 가격/거래량 몇 개만 뽑고 나머지 필드는 버리고
있는데, 관리종목/투자경고/단기과열 종목을 사전에 걸러내는 로직이 코드 어디에도
없다는 게 확인됐다. KIS 문서 기준으로는 이 응답에 시장경고코드류 필드가 같이
올 가능성이 있지만, 실제로 어떤 필드명으로 오는지는 진짜 API 응답을 봐야 안다
(이 세션엔 실계좌 키가 없어서 여기선 확인 불가).

  python check_market_warning_fields.py 004770       # 종목 코드 하나
  python check_market_warning_fields.py 004770 950200 175250 376900   # 여러 개

출력되는 raw output 딕셔너리를 그대로 캡처해서 다시 보여주면, 어떤 필드를
파싱해서 매수 전에 걸러야 할지 판단할 수 있다."""
import sys

import api_client
from auth import get_access_token
from common import load_config


def dump_quote_raw(cfg, code: str) -> None:
    res = api_client._get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=api_client._headers(cfg, "FHKST01010100"),
        params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code},
    )
    body = res.json()
    out = body.get("output", {})
    print(f"\n=== {code} raw output ({len(out)}개 필드) ===")
    # 이름에 경고/관리/과열/유의/정지 느낌이 나는 필드를 먼저 강조해서 보여준다.
    hint_keys = [
        k for k in out
        if any(h in k for h in ["warn", "caful", "over", "admn", "cls_code", "mang", "stop"])
    ]
    if hint_keys:
        print("-- 이름에 경고/관리/과열/유의 관련 단어가 들어간 필드 (우선 확인) --")
        for k in hint_keys:
            print(f"  {k}: {out[k]!r}")
        print("-- 전체 필드 --")
    for k, v in out.items():
        print(f"  {k}: {v!r}")


def main():
    codes = sys.argv[1:]
    if not codes:
        print("사용법: python check_market_warning_fields.py <종목코드> [종목코드2] ...")
        print("예:     python check_market_warning_fields.py 004770 950200 175250 376900")
        sys.exit(1)

    cfg = load_config()
    get_access_token(cfg)  # 토큰 캐시 미리 채워서, 아래 반복 호출에서 매번 재발급 안 하게
    for code in codes:
        try:
            dump_quote_raw(cfg, code)
        except Exception as e:
            print(f"{code}: 조회 실패 - {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
