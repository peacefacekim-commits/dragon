"""
감시종목별로 회차마다 얻을 수 있는 투자자 동향/보조지표를 전부 기록해둔다.
(2026-09-03 추가, 사용자 요청: "외국인이 얼마나 사는지 개인들은 어떻게
반응하는지 등등... 얻을 수 있는 자료는 다 보관해줘")

api_client.get_quote()가 회차마다 종목당 한 번씩 부르는 현재가 조회 응답에는
지금까지 실제로 쓰는 필드(가격/고가/저가/거래량/관리종목 여부 등) 말고도
외국인순매수량(frgn_ntby_qty), 프로그램매매 순매수량(pgtr_ntby_qty), 외국인
보유율(hts_frgn_ehrt), 거래량회전율(vol_tnrt), 신용잔고율(whol_loan_rmnd_rate),
VI발동여부(vi_cls_code), PER/PBR, 52주/250일 고점 대비 등락률 같은 필드가 이미
같이 온다 (quote["raw"] - api_client.get_quote 문서 참고). 새 API 호출을 추가로
만들지 않고, 이미 매 회차 받아오는 응답에서 지금까지 안 쓰고 버리던 필드만
골라 기록한다 - 새 엔드포인트를 추가하면 실전 계좌로 검증 전까지는 필드명이
맞는지 확신할 수 없는데, 이 필드들은 이미 blocklist.market_warning_reason()이
실전에서 쓰고 있는 것과 같은 응답에서 나온다.

한계 - 미리 밝혀둠: 이 응답(inquire-price)에는 종목별 외국인 순매수는
있지만, 종목별 "개인" 순매수는 들어있지 않다 (그건 시장 전체 단위로만
market.py의 investor_history.csv가 이미 기록 중). 그래서 "개인 반응"은 여기서
거래량회전율(vol_tnrt)·거래량·등락률로만 간접적으로 유추할 수 있고, 종목별
개인 순매수 수치 자체는 이 로그에 없다.

슬롯 결정이나 매매 판단에는 전혀 안 쓴다 - market.py의 investor_history.csv/
uplow_history.csv, volatility.py의 candidate_volatility.csv와 같은 성격의
"나중에 데이터로 검증해볼" 순수 기록용 로그. 조회/기록 실패는 그 건만
건너뛰고 절대 예외를 던지지 않는다 (매매 감시를 막으면 안 되므로).
"""
import csv
from datetime import datetime

from common import CANDIDATE_SNAPSHOT_LOG_PATH

FIELDNAMES = [
    "timestamp", "code", "name", "price", "change_pct", "volume",
    "frgn_ntby_qty", "pgtr_ntby_qty", "hts_frgn_ehrt",
    "vol_tnrt", "whol_loan_rmnd_rate", "vi_cls_code",
    "per", "pbr", "w52_hgpr_vrss_prpr_ctrt", "d250_hgpr_vrss_prpr_rate",
]


def log_snapshot(code: str, name: str, quote: dict) -> None:
    """quote는 api_client.get_quote()의 반환값 그대로 받는다 (그 안의 raw 딕셔너리에서
    필요한 필드만 뽑아 씀 - 별도 API 호출 없음)."""
    try:
        raw = quote.get("raw") or {}
        write_header = not CANDIDATE_SNAPSHOT_LOG_PATH.exists()
        with open(CANDIDATE_SNAPSHOT_LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if write_header:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "code": code,
                "name": name,
                "price": quote.get("price", ""),
                "change_pct": quote.get("change_pct", ""),
                "volume": quote.get("volume", ""),
                "frgn_ntby_qty": raw.get("frgn_ntby_qty", ""),
                "pgtr_ntby_qty": raw.get("pgtr_ntby_qty", ""),
                "hts_frgn_ehrt": raw.get("hts_frgn_ehrt", ""),
                "vol_tnrt": raw.get("vol_tnrt", ""),
                "whol_loan_rmnd_rate": raw.get("whol_loan_rmnd_rate", ""),
                "vi_cls_code": raw.get("vi_cls_code", ""),
                "per": raw.get("per", ""),
                "pbr": raw.get("pbr", ""),
                "w52_hgpr_vrss_prpr_ctrt": raw.get("w52_hgpr_vrss_prpr_ctrt", ""),
                "d250_hgpr_vrss_prpr_rate": raw.get("d250_hgpr_vrss_prpr_rate", ""),
            })
    except Exception:
        return
