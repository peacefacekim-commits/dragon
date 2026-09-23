"""
한국투자증권(KIS) REST API 최소 래퍼.

시세 조회(일봉/현재가)는 모의/실전 상관없이 같은 tr_id 를 쓰지만,
계좌·주문 관련 API 는 모의(V로 시작)와 실전(T로 시작) 의 tr_id 가 다릅니다.

주의: 아래 tr_id/파라미터는 KIS 공식 문서 기준으로 작성했지만,
실제 계좌로 처음 연결할 때는 반드시 모의투자로 한 번씩 호출해보고
응답 구조가 예상과 같은지 확인한 뒤 실전으로 넘어가세요. 증권사 API는
문서와 실제 응답이 미묘하게 다른 경우가 있습니다.
"""
import time
from datetime import datetime, timedelta

import requests

from auth import get_access_token, get_hashkey
from common import Config


class KisApiError(RuntimeError):
    pass


def _headers(cfg: Config, tr_id: str, extra: dict | None = None) -> dict:
    h = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {get_access_token(cfg)}",
        "appkey": cfg.app_key,
        "appsecret": cfg.app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }
    if extra:
        h.update(extra)
    return h


# (2026-09-13 추가) KIS 실전계좌 유량제한은 초당 20건이다. 지금까지는 한 회차에
# 조회하는 종목이 몇 개뿐이라 신경 쓸 일이 없었는데, 일봉 과거치 일괄 수집
# (panel.py)은 "종목 200개 x 기간 조각 여러 개" = 수천 번을 연속 호출하므로
# 제한에 걸릴 수 있다. 여유를 두고 초당 8건으로 스스로 속도를 늦춘다
# (8건/초면 2000번 호출에 4분 남짓이라 실용적으로 충분히 빠르다).
# 모든 조회가 이 함수를 지나가므로 여기 한 곳에만 넣으면 된다.
_MIN_CALL_INTERVAL_SEC = 1.0 / 8
_last_call_at = 0.0


def _throttle() -> None:
    global _last_call_at
    wait = _last_call_at + _MIN_CALL_INTERVAL_SEC - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def _get_with_retry(url: str, headers: dict, params: dict, retries: int = 2, backoff: float = 1.5):
    """조회(GET)는 여러 번 반복해도 안전하므로, 거래소 일시 오류(5xx)면 잠깐 쉬었다 재시도한다.
    (주문 같은 POST 는 중복 제출 위험이 있어 여기서 재시도하지 않는다)"""
    last_error = None
    for attempt in range(retries + 1):
        try:
            _throttle()
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code >= 500 and attempt < retries:
                time.sleep(backoff)
                continue
            res.raise_for_status()
            return res
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < retries:
                time.sleep(backoff)
                continue
            raise
    raise last_error


def _split_account(account_no: str) -> tuple[str, str]:
    cano, prdt = account_no.split("-")
    return cano, prdt


def get_daily_prices(
    cfg: Config, code: str, lookback_days: int = 90,
    start_date: str | None = None, end_date: str | None = None,
) -> list[dict]:
    """일봉(날짜/종가/고가/저가/거래량)을 오래된 순으로 반환.

    start_date/end_date("YYYYMMDD")를 주면 그 기간을 그대로 조회한다 (백테스트용).
    안 주면 예전처럼 오늘 기준 최근 lookback_days 일을 조회한다.

    주의: KIS 이 API는 한 번 호출에 최대 약 100건까지만 돌려준다. 6개월 이상처럼
    긴 기간을 조회하면 앞부분이 잘려서 나올 수 있으니, 리턴된 행 수가 예상보다
    훨씬 적으면(예: 정확히 100건) 그 기간을 여러 번 나눠 호출해야 할 수 있다."""
    end = datetime.strptime(end_date, "%Y%m%d") if end_date else datetime.now()
    start = datetime.strptime(start_date, "%Y%m%d") if start_date else end - timedelta(days=lookback_days)

    res = _get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
        headers=_headers(cfg, "FHKST03010100"),
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code,
            "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0",
        },
    )
    body = res.json()
    if body.get("rt_cd") != "0":
        raise KisApiError(f"일봉 조회 실패 ({code}): {body.get('msg1')}")

    rows = body.get("output2", [])
    parsed = [
        {
            "date": r["stck_bsop_date"],
            "close": float(r["stck_clpr"]),
            "high": float(r["stck_hgpr"]),
            "low": float(r["stck_lwpr"]),
            # (2026-08-31 추가) 시가 - "매수 시점에 이미 그날 시가보다 올라있었나"를
            # 백테스트(backtest.py)에서 확인해보려고 추가. 기존에 쓰던 값이 아니라
            # 새 필드만 추가하는 거라 기존 코드(strategy.py 등)에는 영향 없음.
            # 필드가 없거나 0이면(응답 구조가 예상과 다른 경우) None - 종가로 대충
            # 채우면 "시가와 종가가 같다(등락 0%)"는 가짜 신호가 생기므로, 차라리
            # 없으면 없다고 그대로 두어서, 쓰는 쪽이 그 거래를 집계에서 뺄 수 있게 한다.
            "open": float(r["stck_oprc"]) if r.get("stck_oprc") else None,
            # (2026-08-20, 거래량 확인 조건) 이 날의 누적거래량. 장중에 조회하면
            # 오늘 날짜 행은 그 시점까지의 누적치라 하루 전체 값보다 작게 나온다 -
            # strategy.compute_dip_signal 이 오늘 행은 평균 계산에서 빼고 쓴다.
            "volume": int(r.get("acml_vol", 0)),
        }
        for r in rows
        if r.get("stck_bsop_date")
    ]
    parsed.sort(key=lambda r: r["date"])
    return parsed


# KIS 일봉 API가 한 번 호출에 돌려주는 최대 건수(관측값 기준 약 100건).
DAILY_PRICE_MAX_ROWS = 100
# 한 조각의 길이(달력 기준 일수). 120일이면 영업일로 약 82일이라 위 상한(100건)
# 밑으로 충분히 여유가 있다. 여유 없이 딱 맞추면 연휴 배치에 따라 잘릴 수 있다.
DAILY_PRICE_CHUNK_DAYS = 120


def get_daily_prices_range(
    cfg: Config, code: str, start_date: str, end_date: str,
    chunk_days: int = DAILY_PRICE_CHUNK_DAYS,
    on_truncated=None,
) -> list[dict]:
    """긴 기간의 일봉을 여러 조각으로 나눠 조회해서 하나로 이어붙인다.

    (2026-09-13 추가) get_daily_prices 는 한 번 호출에 약 100건까지만 받아올 수
    있어서, 그동안 팩터 계산 창을 60일로 줄여 쓸 수밖에 없었다(factors.py 참고 -
    논문 기준인 12개월 모멘텀/200일 이동평균을 못 쓰고 있었다). 기간을 조각내서
    여러 번 부르면 몇 년치도 받을 수 있으므로, 그 조각내기를 여기서 담당한다.

    start_date/end_date 는 "YYYYMMDD". 반환은 get_daily_prices 와 같은 형식이고
    오래된 순으로 정렬, 날짜 중복은 제거된다(조각 경계가 겹쳐도 안전).

    상장 전 구간처럼 데이터가 아예 없는 조각이 연속으로 나오면 거기서 멈춘다 -
    2015년부터 받으라고 했는데 2023년 상장 종목이면 앞쪽 수십 번의 호출이 전부
    빈 응답이라, 그걸 끝까지 다 부르면 시간만 버린다.

    on_truncated(code, chunk_start, chunk_end, n) 을 주면, 한 조각이 상한선까지
    꽉 차서 돌아왔을 때(= 잘렸을 수 있음) 호출된다. 조각 길이를 잘못 잡은 걸
    조용히 넘어가지 않고 알리기 위한 것이다.
    """
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    if start > end:
        return []

    by_date: dict[str, dict] = {}
    empty_streak = 0

    # 최근 -> 과거 순으로 거슬러 올라간다. 상장 전 구간에서 일찍 멈추려면
    # 과거부터가 아니라 최근부터 가야 한다.
    chunk_end = end
    while chunk_end >= start:
        chunk_start = max(start, chunk_end - timedelta(days=chunk_days - 1))
        rows = get_daily_prices(
            cfg, code,
            start_date=chunk_start.strftime("%Y%m%d"),
            end_date=chunk_end.strftime("%Y%m%d"),
        )
        if rows:
            empty_streak = 0
            for r in rows:
                by_date[r["date"]] = r
            if len(rows) >= DAILY_PRICE_MAX_ROWS and on_truncated is not None:
                on_truncated(code, chunk_start.strftime("%Y%m%d"),
                             chunk_end.strftime("%Y%m%d"), len(rows))
        else:
            empty_streak += 1
            # 이미 받아온 게 있는데 빈 조각이 2번 연속이면 상장 전으로 보고 멈춘다.
            # (아직 아무것도 못 받은 상태라면 그냥 최근에 거래가 없는 종목일 수도
            #  있으니 조금 더 가본다)
            if by_date and empty_streak >= 2:
                break

        chunk_end = chunk_start - timedelta(days=1)

    return [by_date[d] for d in sorted(by_date)]


def get_index_price(cfg: Config, index_code: str = "0001") -> float:
    """지수 현재값. index_code 0001 = 코스피, 1001 = 코스닥."""
    res = _get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-index-price",
        headers=_headers(cfg, "FHPUP02100000"),
        params={"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": index_code},
    )
    body = res.json()
    if body.get("rt_cd") != "0":
        raise KisApiError(f"지수 조회 실패 ({index_code}): {body.get('msg1')}")
    return float(body["output"]["bstp_nmix_prpr"])


def get_index_daily_prices(
    cfg: Config, index_code: str = "0001", lookback_days: int = 90,
    start_date: str | None = None, end_date: str | None = None,
) -> list[dict]:
    """지수 일봉(날짜/종가)을 오래된 순으로 반환.
    start_date/end_date("YYYYMMDD")를 주면 그 기간을 그대로 조회한다 (백테스트용).
    get_daily_prices 와 마찬가지로 한 번에 최대 약 100건 제한이 있을 수 있다."""
    end = datetime.strptime(end_date, "%Y%m%d") if end_date else datetime.now()
    start = datetime.strptime(start_date, "%Y%m%d") if start_date else end - timedelta(days=lookback_days)

    res = _get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice",
        headers=_headers(cfg, "FHKUP03500100"),
        params={
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": index_code,
            "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": "D",
        },
    )
    body = res.json()
    if body.get("rt_cd") != "0":
        raise KisApiError(f"지수 일봉 조회 실패 ({index_code}): {body.get('msg1')}")

    parsed = [
        {"date": r["stck_bsop_date"], "close": float(r["bstp_nmix_prpr"])}
        for r in body.get("output2", [])
        if r.get("stck_bsop_date")
    ]
    parsed.sort(key=lambda r: r["date"])
    return parsed


def get_investor_flows(cfg: Config, market_code: str = "1001", market_iscd: str = "KSQ") -> dict:
    """오늘 기준 시장 전체(기본값 코스닥)의 개인/외국인/기관계 순매수 수량(주 단위).
    {"prsn": 개인, "frgn": 외국인, "orgn": 기관계}.

    market_code: 업종코드 (0001=코스피, 1001=코스닥 - get_index_price 와 동일한 코드 체계).
    market_iscd: KSP=코스피, KSQ=코스닥.

    (2026-08-31 추가, 2026-09-02 개인만 쓰다가 외국인/기관계까지 같이 뽑도록 확장 -
    응답 자체엔 처음부터 셋 다 들어있었는데 개인만 골라 쓰고 있었음) KIS 공식 샘플
    (examples_llm/domestic_stock/inquire_investor_daily_by_market) 기준으로 작성.
    샘플은 시작일/종료일을 항상 같은 날짜로 넣도록 돼 있어서(과거 날짜 범위 조회
    방식이 아님), 여기서도 오늘 날짜 하나만 넣는다 - 그래서 "전날 값"이 필요하면
    이 함수가 아니라 매 회차 쌓이는 로그(logs/investor_history.csv)에서 어제 마지막 기록을
    찾아 써야 한다 (다른 종목/일봉 API처럼 과거 날짜를 직접 조회하는 방식이 아닐 수 있음 -
    아직 실전 응답으로 검증 전이라 로그 전용으로만 우선 쓴다)."""
    today = datetime.now().strftime("%Y%m%d")
    res = _get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market",
        headers=_headers(cfg, "FHPTJ04040000"),
        params={
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": market_code,
            "FID_INPUT_DATE_1": today,
            "FID_INPUT_ISCD_1": market_iscd,
            "FID_INPUT_DATE_2": today,
            "FID_INPUT_ISCD_2": market_code,
        },
    )
    body = res.json()
    if body.get("rt_cd") != "0":
        raise KisApiError(f"투자자별 매매동향 조회 실패 ({market_iscd}): {body.get('msg1')}")
    rows = body.get("output", [])
    if not rows:
        raise KisApiError(f"투자자별 매매동향 응답이 비어있습니다 ({market_iscd})")
    row = rows[0]
    return {
        "prsn": float(row["prsn_ntby_qty"]),
        "frgn": float(row["frgn_ntby_qty"]),
        "orgn": float(row["orgn_ntby_qty"]),
    }


def get_uplow_price_count(cfg: Config, market_code: str = "1001") -> dict:
    """지금 이 순간 시장(기본값 코스닥)에서 상한가/하한가 종목이 몇 개인지.
    {"up": 상한가 종목수, "down": 하한가 종목수}.

    market_code: 0000=전체, 0001=코스피, 1001=코스닥.

    (2026-08-31 추가) KIS 공식 샘플(examples_llm/domestic_stock/capture_uplowprice) 기준.
    이 API는 "지금 이 순간" 스냅샷만 주고 과거 날짜 조회가 안 되므로, "전날 값"이 필요하면
    매 회차 로그(logs/uplow_history.csv)에 쌓아서 어제 마지막 기록을 찾아 써야 한다."""
    def _count(prc_cls_code: str) -> int:
        res = _get_with_retry(
            f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/capture-uplowprice",
            headers=_headers(cfg, "FHKST130000C0"),
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_COND_SCR_DIV_CODE": "11300",
                "FID_PRC_CLS_CODE": prc_cls_code,
                "FID_DIV_CLS_CODE": "0",
                "FID_INPUT_ISCD": market_code,
                "FID_TRGT_CLS_CODE": "",
                "FID_TRGT_EXLS_CLS_CODE": "",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
            },
        )
        body = res.json()
        if body.get("rt_cd") != "0":
            raise KisApiError(f"상한가/하한가 조회 실패: {body.get('msg1')}")
        return len(body.get("output", []))

    return {"up": _count("0"), "down": _count("1")}


def get_current_price(cfg: Config, code: str) -> float:
    return get_quote(cfg, code)["price"]


def get_quote(cfg: Config, code: str) -> dict:
    """현재가 + 당일 고가/저가/등락률/거래량. 스크리너에서 임의 종목의
    당일 변동폭을 계산할 때 쓴다 (순위 API 는 종목을 지정해서 조회할 수 없어서)."""
    res = _get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=_headers(cfg, "FHKST01010100"),
        params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code},
    )
    body = res.json()
    if body.get("rt_cd") != "0":
        raise KisApiError(f"현재가 조회 실패 ({code}): {body.get('msg1')}")
    out = body["output"]
    return {
        "price": float(out["stck_prpr"]),
        "high": float(out["stck_hgpr"]),
        "low": float(out["stck_lwpr"]),
        "change_pct": float(out["prdy_ctrt"]),
        "volume": int(out["acml_vol"]),
        # (2026-09-03 추가) 관리종목/투자유의/투자경고/단기과열/거래정지 여부.
        # 지금까지 이 응답에 실제로 오는지 확인 안 하고 버리고 있었는데,
        # 175250(아이큐어)이 mang_issu_cls_code='Y'(관리종목)인 채로 그냥 매수된
        # 사고로 실제로 확인됨 - blocklist.market_warning_reason() 이 이 값들을 씀.
        "mang_issu_cls_code": out.get("mang_issu_cls_code", "N"),
        "mrkt_warn_cls_code": out.get("mrkt_warn_cls_code", "00"),
        "invt_caful_yn": out.get("invt_caful_yn", "N"),
        "short_over_yn": out.get("short_over_yn", "N"),
        "temp_stop_yn": out.get("temp_stop_yn", "N"),
        # (2026-09-03 추가) 이 응답엔 위에서 뽑는 것 말고도 PER/PBR/외국인보유율/
        # 프로그램매매순매수/신용잔고비율/VI발동여부/52주고저 등 80여개 필드가 더
        # 온다. 지금 당장 뭐가 승률과 관련 있을지 몰라서 미리 고르지 않고, 원본을
        # 통째로 같이 돌려준다 - paper_screen.py가 이걸 그대로 기록해두면 나중에
        # 뭘 볼지는 그때 데이터로 정할 수 있다 (기존 호출부들은 위 필드만 쓰고
        # "raw"는 안 건드리니 하위호환에 영향 없음).
        "raw": out,
    }


def get_holdings(cfg: Config) -> dict[str, dict]:
    """보유 종목 {종목코드: {qty, avg_price, name}} 형태로 반환."""
    tr_id = "VTTC8434R" if cfg.mode == "mock" else "TTTC8434R"
    cano, prdt = _split_account(cfg.account_no)

    res = _get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/trading/inquire-balance",
        headers=_headers(cfg, tr_id),
        params={
            "CANO": cano,
            "ACNT_PRDT_CD": prdt,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        },
    )
    body = res.json()
    if body.get("rt_cd") != "0":
        raise KisApiError(f"잔고 조회 실패: {body.get('msg1')}")

    holdings = {}
    for row in body.get("output1", []):
        qty = int(row.get("hldg_qty", 0))
        if qty > 0:
            holdings[row["pdno"]] = {
                "qty": qty,
                "avg_price": float(row.get("pchs_avg_pric", 0)),
                "name": row.get("prdt_name", row["pdno"]),
            }
    return holdings


def get_buyable_cash(cfg: Config, code: str) -> float:
    """지금 이 종목을 시장가로 살 때 실제 주문 가능한 현금(원).

    총 투자금(total_capital)은 config.yaml 에 적힌 장부상 숫자일 뿐이고, 이미 다른
    종목에 돈이 묶여있으면 실제로는 그보다 훨씬 적은 현금만 남아있을 수 있다.
    그래서 매수 수량 계산 전에 반드시 이 값을 실제로 조회해서 확인해야 한다.

    output.nrcvb_buy_amt (미수 없는 매수가능금액) 을 쓴다 - 아직 결제(T+2) 전인
    매도대금까지 재사용해서 매수하되, 실제로 빚(미수금)이 생기지는 않는 한도.
    output.ord_psbl_cash(정산 완료된 출금가능 현금, 더 보수적)보다 크게 나올 수 있다."""
    tr_id = "VTTC8908R" if cfg.mode == "mock" else "TTTC8908R"
    cano, prdt = _split_account(cfg.account_no)

    res = _get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-order",
        headers=_headers(cfg, tr_id),
        params={
            "CANO": cano,
            "ACNT_PRDT_CD": prdt,
            "PDNO": code,
            "ORD_UNPR": "0",
            "ORD_DVSN": "01",
            "CMA_EVLU_AMT_ICLD_YN": "N",
            "OVRS_ICLD_YN": "N",
        },
    )
    body = res.json()
    if body.get("rt_cd") != "0":
        raise KisApiError(f"주문가능금액 조회 실패 ({code}): {body.get('msg1')}")
    return float(body["output"]["nrcvb_buy_amt"])


# (2026-09-04 삭제) 실제 주문 제출 함수들(_submit_order, get_order_fill_price,
# _try_on_exchange, place_order, place_order_and_verify, api_get_holding_qty)을
# 여기 있던 자리에서 전부 없앴다. 사용자가 실전투자를 완전히 접고 이 프로그램을
# 순수 데이터 수집(가상투자) 전용으로 쓰기로 하면서, "설정으로 끄는" 수준이 아니라
# "코드 자체에 실제 주문을 낼 방법이 없게" 만들어달라고 명시적으로 요청했다.
# 시세조회/일봉/잔고조회 등 읽기 전용 함수는 데이터 수집에 계속 쓰이므로 그대로
# 남겨뒀다.


# ===========================================================================
# (2026-09-21 추가) 당일 분봉. 사용자: "그럼 내일부터 10분 씩 거래를 기록하자."
#
# 왜 필요한가: 이 저장소의 패널은 일봉이라 하루 안의 사고팔기를 재현할 수
# 없다. analyze_intraday.py 가 시/고/저/종으로 상한을 따져보는 것까지가
# 한계였다. 10분 매매를 실제로 채점하려면 분 단위 가격이 있어야 한다.
#
# 가장 중요한 제약: 이 API 는 **오늘 것만** 준다. 과거 분봉을 소급해서
# 받을 방법이 없다. 그래서 하루를 빠뜨리면 그날은 영구히 없다. 매 거래일
# 장 마감 뒤에 반드시 돌려야 한다.
#
# 한 번 호출에 기준시각 이전 30건(1분봉 30개)까지 돌려준다. 그래서 하루
# (09:00~15:30, 390분)를 다 받으려면 30분 간격으로 13번 부른다.
MINUTE_ROWS_PER_CALL = 30


def get_minute_prices(cfg: Config, code: str, anchor_hhmmss: str) -> list[dict]:
    """기준시각 이전의 1분봉을 오래된 순으로 반환 (최대 30건).

    anchor_hhmmss 는 "HHMMSS". 그 시각까지의 30분을 돌려준다.

    응답 필드가 예상과 다를 수 있으므로, 없는 값은 None 으로 두고 채우지
    않는다. 종가로 대충 메우면 '움직이지 않았다' 는 가짜 신호가 생긴다
    (get_daily_prices 의 open 처리와 같은 이유다).
    """
    res = _get_with_retry(
        f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
        headers=_headers(cfg, "FHKST03010200"),
        params={
            "FID_ETC_CLS_CODE": "",
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code,
            "FID_INPUT_HOUR_1": anchor_hhmmss,
            "FID_PW_DATA_INCU_YN": "N",
        },
    )
    body = res.json()
    if body.get("rt_cd") != "0":
        raise KisApiError(f"분봉 조회 실패 ({code} {anchor_hhmmss}): {body.get('msg1')}")

    def num(r, key, cast=float):
        try:
            v = r.get(key)
            return cast(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    out = []
    for r in body.get("output2", []):
        hhmm = r.get("stck_cntg_hour")
        if not hhmm:
            continue
        out.append({
            "date": r.get("stck_bsop_date"),
            "time": hhmm,
            "open": num(r, "stck_oprc"),
            "high": num(r, "stck_hgpr"),
            "low": num(r, "stck_lwpr"),
            "close": num(r, "stck_prpr"),
            "volume": num(r, "cntg_vol", int),
        })
    out.sort(key=lambda x: (x["date"] or "", x["time"]))
    return out
