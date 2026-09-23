"""
거래 자체가 막힌 종목(관리종목·정리매매 등)을 기억해두는 곳 (2026-08-11 추가).

2026-08-11에 하락폭 스크리너가 "경쟁매매 거래 불가 종목"(관리종목/정리매매 등으로
추정)을 계속 골라오는 바람에, 하루 종일 매수 시도 -> 실패가 반복됐다. 시장가로
막히면 지정가로 재시도하는 것과는 다른 문제라, 지정가로도 해결이 안 된다.

이런 종목은 주문이 이 사유로 거부되는 순간 여기 기록해두고,
  - trader.py: 오늘 안에 같은 종목을 또 매수 시도하지 않도록 건너뜀
  - screener.py: 다음날 이후 감시목록 후보에서 아예 제외
하도록 쓴다. KIS API에 "관리종목 여부"를 미리 조회하는 필드가 확실치 않아서,
예방적으로 거르는 대신 "실제로 거부당한 종목을 기억해서 다시 안 건드리는" 방식을
택했다.
"""
import json

from common import BLOCKLIST_PATH

# 이 문구가 주문 실패 메시지에 포함되면 "일시적 오류"가 아니라 "이 종목 자체가
# 정상적으로 거래될 수 없는 상태"로 판단한다. 지정가 재시도로도 해결이 안 되므로
# 재시도하지 말고 블록리스트에 올린다.
UNTRADABLE_MARKERS = [
    "경쟁매매 거래 불가",
    "관리종목",
    "정리매매",
    "거래정지",
    "거래가 불가능한",
    # (2026-08-18 추가) 알트(459550)에서 반복 확인됨 - 이 계좌에 명시적으로 지정한
    # EXCG_ID_DVSN_CD=SOR(_submit_order 참고)을 이 종목은 안 받는 것으로 보인다.
    # 지정가로 바꿔도 안 풀리는 문제라 다른 오류들과 동일하게 블록 처리한다.
    "거래소구분코드 오류",
]


def is_untradable_error(message: str) -> bool:
    return any(marker in message for marker in UNTRADABLE_MARKERS)


# (2026-09-03 추가) 위 UNTRADABLE_MARKERS는 "주문 자체가 거부되는" 사후 대응이다.
# 관리종목/투자유의/투자경고/단기과열은 대부분 주문이 정상적으로 들어가버려서
# 그 방식으로 안 걸러진다 - 175250(아이큐어)이 관리종목(mang_issu_cls_code='Y')
# 상태 그대로 매수되고 그날 제일 크게 손실난 사고로 실제로 확인됨. 매수 전에
# api_client.get_quote() 응답으로 미리 확인해서 사전에 거른다.
def market_warning_reason(quote: dict) -> str | None:
    """quote(api_client.get_quote 반환값)에 담긴 관리종목/경고 관련 필드를 보고,
    매수를 피해야 할 사유가 있으면 사람이 읽을 문구를, 없으면 None을 돌려준다."""
    if quote.get("mang_issu_cls_code") == "Y":
        return "관리종목"
    if quote.get("temp_stop_yn") == "Y":
        return "거래정지"
    warn_code = quote.get("mrkt_warn_cls_code", "00")
    if warn_code == "01":
        return "투자주의"
    if warn_code == "02":
        return "투자경고"
    if warn_code == "03":
        return "투자위험"
    if quote.get("invt_caful_yn") == "Y":
        return "투자유의"
    if quote.get("short_over_yn") == "Y":
        return "단기과열"
    return None


def _load() -> dict:
    if BLOCKLIST_PATH.exists():
        try:
            return json.loads(BLOCKLIST_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    BLOCKLIST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add(code: str, name: str, reason: str) -> None:
    data = _load()
    data[code] = {"name": name, "reason": reason}
    _save(data)


def is_blocked(code: str) -> bool:
    return code in _load()


def all_blocked() -> dict:
    return _load()
