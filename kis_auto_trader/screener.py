"""
장 마감 후 실행: 그날 상승·하락률 상위 종목들을 모아서, 다음날 감시목록
후보를 추천한다. 두 가지 선정 기준(mode) 중 골라 쓸 수 있다.

  --mode volatility (기본) : 오늘 하루 변동폭(고가-저가/현재가)이 큰 순 (전체 시장 대상)
  --mode dip                : 최근 N일 고점 대비 하락폭이 큰 순 (전체 시장 대상)
                              (기존에 써온 "하락폭 매수" 전략과 같은 기준)
  --mode ai                 : AI_THEME_STOCKS 에 직접 등록해둔 AI 관련주만 대상으로,
                              오늘 하루 변동폭이 큰 순

  python screener.py --mode dip          # 상위 5개로 config.yaml watchlist 교체
  python screener.py --mode dip --dry-run  # 후보만 보고 config.yaml 은 안 건드림

거래대금이 너무 낮은(유동성 부족) 종목은 제외한다 - 이런 종목에서
시장가 주문거부(폴라리스오피스 사례)가 잦았기 때문이다.

주의: KIS API 에는 "고점 대비 하락폭 순위"를 바로 조회하는 기능이 없다.
그래서 오늘 등락률 상위/하위 종목(약 60개)을 먼저 후보군으로 추리고,
그 안에서만 각각 과거 시세를 조회해 하락폭을 계산한다 - 전체 종목을
다 조회하면 너무 오래 걸리기 때문에 이렇게 절충했다.
"""
import argparse
import dataclasses
import re

import requests

import api_client
import blocklist
import news
import loss_cooldown
import sold_today
import volatility
import watch_state
from auth import get_access_token
from common import CONFIG_PATH, load_config

MIN_TRADE_VALUE = 3_000_000_000  # 최소 거래대금(원). 이 밑으로는 유동성 부족으로 제외.
TOP_N = 3  # (2026-08-13) 슬롯 5개->3개로 줄이면서 감시종목 수도 맞춤
DIP_LOOKBACK_DAYS = 20  # "고점"을 계산할 기간

# AI 관련주 후보군 (직접 관리하는 목록). KIS 순위 API 에는 "테마/섹터별 조회"가
# 없어서, 종목을 지정해서 하나씩 조회하는 방식으로만 가능하다. 새로 상장되거나
# 테마가 바뀐 종목이 있으면 이 목록에 직접 추가/삭제하면 된다.
#
# (2026-08-11) 네이버/카카오/삼성전자/SK하이닉스는 뺐다 - 이 전략은 소형주 변동성을
# 노리는데, 이 넷은 시가총액 기준 대형주라 성격이 안 맞는다. 2단계 예산 필터(주가가
# 슬롯 예산보다 낮아야 함)만으로는 대형주가 안 걸러진다 - 주가와 시가총액은 별개라
# 삼성전자처럼 액면분할해서 주당가는 낮아도 시총은 큰 경우가 있다. 한미반도체는
# 대형주보다는 성장/장비주 성격이 강하다고 보고 남겨둠.
AI_THEME_STOCKS = [
    ("042700", "한미반도체"),
    ("402030", "코난테크놀로지"),
    ("347860", "알체라"),
    ("108860", "셀바스AI"),
    ("377480", "마인즈랩"),
    ("304100", "솔트룩스"),
    ("328130", "루닛"),
    ("338220", "뷰노"),
    ("315640", "딥노이드"),
    ("322510", "제이엘케이"),
    ("289220", "자이언트스텝"),
    ("300120", "라온피플"),
    ("047560", "이스트소프트"),
    ("065370", "위세아이텍"),
]

# 레버리지/인버스 상품은 매일 재조정되며 복리로 가치가 깎이는 구조라, 일반
# 개별주의 "하락하면 반등한다"는 전제로 만든 이 전략에 맞지 않는다. 이름으로 걸러낸다.
# (일반 ETN/ETF 자체는 제외 대상이 아니고, 레버리지·인버스 배율이 붙은 것만 제외)
EXCLUDE_KEYWORDS = ["레버리지", "인버스", "곱버스", "2X", "3X"]


def _fetch_ranking(cfg, sort_code: str) -> list[dict]:
    res = requests.get(
        f"{cfg.base_url}/uapi/domestic-stock/v1/ranking/fluctuation",
        headers={
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {get_access_token(cfg)}",
            "appkey": cfg.app_key,
            "appsecret": cfg.app_secret,
            "tr_id": "FHPST01700000",
            "custtype": "P",
        },
        params={
            "fid_cond_mrkt_div_code": "J", "fid_cond_scr_div_code": "20170",
            "fid_input_iscd": "0000", "fid_rank_sort_cls_code": sort_code,
            "fid_input_cnt_1": "0", "fid_prc_cls_code": "0",
            "fid_input_price_1": "", "fid_input_price_2": "", "fid_vol_cnt": "",
            "fid_trgt_cls_code": "0", "fid_trgt_exls_cls_code": "0", "fid_div_cls_code": "0",
            "fid_rsfl_rate1": "", "fid_rsfl_rate2": "",
        },
        timeout=10,
    )
    res.raise_for_status()
    body = res.json()
    if body.get("rt_cd") != "0":
        raise RuntimeError(f"순위 조회 실패: {body.get('msg1')}")
    return body.get("output", [])


def _base_candidates(cfg) -> list[dict]:
    """상승률 상위 + 하락률 상위를 합쳐서, 유동성 필터만 적용한 원본 후보군."""
    rows = _fetch_ranking(cfg, "0") + _fetch_ranking(cfg, "1")

    seen = set()
    candidates = []
    for r in rows:
        code = r["stck_shrn_iscd"]
        if code in seen:
            continue
        seen.add(code)

        # (2026-08-11) 실제로 "경쟁매매 거래 불가"(관리종목/정리매매 등)로
        # 주문이 거부됐던 종목은 다시 후보로 넣지 않는다 - blocklist.py 참고.
        if blocklist.is_blocked(code):
            continue

        price = float(r["stck_prpr"])
        high = float(r["stck_hgpr"])
        low = float(r["stck_lwpr"])
        volume = int(r["acml_vol"])
        trade_value = price * volume  # 대략치 (정확한 거래대금 필드가 아니라 근사)

        if trade_value < MIN_TRADE_VALUE or price <= 0:
            continue

        name = r["hts_kor_isnm"]
        if any(kw in name for kw in EXCLUDE_KEYWORDS):
            continue

        candidates.append({
            "code": code,
            "name": name,
            "price": price,
            "change_pct": float(r["prdy_ctrt"]),  # 이 필드는 이미 부호(+/-)가 포함되어 있음
            "day_range_pct": (high - low) / price * 100,
            "trade_value": trade_value,
        })
    return candidates


def _ai_theme_candidates(cfg) -> list[dict]:
    """AI_THEME_STOCKS 목록을 하나씩 직접 조회해서 후보군을 만든다.
    (전체 시장 순위가 아니라 지정된 종목만 보는 거라 유동성 필터만 적용한다)"""
    candidates = []
    for code, name in AI_THEME_STOCKS:
        if blocklist.is_blocked(code):
            continue
        try:
            q = api_client.get_quote(cfg, code)
        except Exception as e:
            print(f"  [!] {name}({code}) 조회 실패, 건너뜀: {e}")
            continue

        trade_value = q["price"] * q["volume"]
        if trade_value < MIN_TRADE_VALUE or q["price"] <= 0:
            continue

        candidates.append({
            "code": code,
            "name": name,
            "price": q["price"],
            "change_pct": q["change_pct"],
            "day_range_pct": (q["high"] - q["low"]) / q["price"] * 100,
            "trade_value": trade_value,
        })
    return candidates


def find_news_candidates(cfg) -> list[dict]:
    """AI_THEME_STOCKS 각각의 최근 뉴스를 모아 Claude 에게 호재/악재/중립을 판단시키고,
    '호재'로 나온 종목만 후보로 남긴다. (Anthropic API 과금 발생 - 종목당 1회 호출)"""
    candidates = []
    for code, name in AI_THEME_STOCKS:
        try:
            price = api_client.get_current_price(cfg, code)
        except Exception as e:
            print(f"  [!] {name}({code}) 시세 조회 실패, 건너뜀: {e}")
            continue

        try:
            news_items = news.fetch_recent_news(code)
            verdict = news.judge_sentiment(name, news_items)
        except Exception as e:
            print(f"  [!] {name}({code}) 뉴스 판단 실패, 건너뜀: {e}")
            continue

        print(f"  {name:12s} ({code}) -> {verdict['verdict']:2s} : {verdict['reason']}")
        if verdict["verdict"] == "호재":
            candidates.append({"code": code, "name": name, "price": price, **verdict})
    return candidates


def _filter_affordable(cfg, candidates: list[dict]) -> list[dict]:
    """총 투자금을 max_positions 개로 똑같이 나눴을 때 1주도 못 사는(현재가가 배정
    예산보다 비싼) 종목은 애초에 후보에서 제외한다. (아무리 좋은 종목이어도 못 사면
    의미 없음)

    (2026-08-24 버그수정) 원래 이 함수는 "몇 개를 반환할지"(top_n)를 그대로 슬롯
    개수로도 같이 썼다. find_mixed_ai_dip_candidates/find_mixed_ai_volatility_candidates
    는 문제 없었지만(top_n이 대개 max_positions), replace_blocked_stock() 은 실제
    빈 슬롯 개수가 아니라 검색 여유폭으로 부풀린 len(exclude)+15(오늘 실제로는 100
    안팎)를 top_n으로 넘긴다. 그러면 total_capital을 100으로 나눠 1종목당 예산이
    2만원 근처까지 쪼그라들고, 실제 거래 단가(보통 수만~수십만원)의 종목이 전부
    "너무 비쌈"으로 걸러져서 대체 후보를 하나도 못 찾는 사고로 이어졌다 (실제 계좌
    로그로 확인: 2026-08-24 예산 18,868원 vs 실제 거래단가 9,270~17,850원대 다수 -
    total_capital 2,000,000원을 len(exclude)+15≈106으로 나눈 값과 정확히 일치).
    실제 매수 시점 예산 배분(trader.py)은 항상 max_positions 개 슬롯 기준이므로,
    "몇 개를 반환할지"(top_n)와 "예산을 몇 등분할지"(max_positions)를 아예 분리해서
    후자는 top_n과 무관하게 항상 cfg.max_positions로 고정한다.

    (2026-09-03 추가) 여기에 주가 하한선(cfg.min_stock_price)도 같이 적용한다.
    원래 이 함수엔 상한선("예산보다 비싸면 제외")만 있고 하한선이 아예 없었는데,
    실거래 78건을 분석해보니 저가주에서 손실이 집중돼 있었다:

      매수단가 1만원 미만 38건 -198,901원 (승률 31.6%)
      매수단가 1만원 이상 40건  +81,450원 (승률 67.5%)

    9월 급락 구간이 저가주에 몰려 있어서 "9월이 나빴던 것뿐 아니냐"는 교란을
    의심했는데, 8월만 따로 봐도 방향이 같았다(1만원 이상 68.4% vs 미만 37.9%,
    1만원 이상 26승/38건이 동전던지기로 나올 확률 1.7%). 경계선을 5천/7천/1만/
    1.5만/2만원으로 바꿔가며 봐도 전부 같은 방향이라, 임계값 하나에 끼워맞춘
    결과가 아니라 연속적인 경향으로 판단했다. 사용자와 상의해 5,000원으로 시작한다
    (데이터상 가장 세게 갈리는 건 1만원이지만 표본 40건에서 나온 최적점이라
    과최적화 위험이 있고, 코스닥 후보 풀도 지나치게 줄어든다).

    다만 주가 자체가 진짜 원인이 아닐 수 있다 - 저가주는 대개 시총이 작고
    유동성이 낮아서, 그쪽이 진짜 원인이고 주가는 따라다니는 대리 지표일 가능성이
    높다. 어느 쪽이든 이 필터로 같이 걸러지므로 실용적으로는 유효하고, 정확한
    원인 구분은 logs/candidate_snapshot.csv 가 쌓인 뒤에 다시 본다.

    cfg.min_stock_price 가 0이면 하한선은 꺼진 것으로 본다 (하위 호환)."""
    min_price = getattr(cfg, "min_stock_price", 0) or 0
    if min_price > 0:
        before = len(candidates)
        candidates = [c for c in candidates if c["price"] >= min_price]
        cheap = before - len(candidates)
        if cheap:
            print(f"  (주가 {min_price:,.0f}원 미만이라 제외된 종목 {cheap}개)")

    slots = cfg.max_positions
    if slots <= 0:
        return candidates
    budget_per_slot = cfg.total_capital / slots
    affordable = [c for c in candidates if c["price"] <= budget_per_slot]
    excluded = len(candidates) - len(affordable)
    if excluded:
        print(f"  (예산 1종목당 {budget_per_slot:,.0f}원 초과라 제외된 종목 {excluded}개)")
    return affordable


def find_candidates(cfg, mode: str = "volatility", dip_lookback_days: int = DIP_LOOKBACK_DAYS) -> list[dict]:
    """mode: 'volatility'(오늘 일중 변동폭 큰 순) / 'dip'(최근 N일 고점 대비 하락폭 큰 순)
    / 'ai'(AI 관련주 중 오늘 변동폭 큰 순) / 'ai-dip'(AI 관련주 중 고점 대비 하락폭 큰 순 -
    두 조건(AI 관련 + 하락폭)을 동시에 본다)."""
    use_ai_pool = mode in ("ai", "ai-dip")
    use_dip_ranking = mode in ("dip", "ai-dip")

    candidates = _ai_theme_candidates(cfg) if use_ai_pool else _base_candidates(cfg)

    if use_dip_ranking:
        print(f"후보 {len(candidates)}개의 최근 {dip_lookback_days}일 고점 대비 하락폭 계산 중...")
        for c in candidates:
            try:
                rows = api_client.get_daily_prices(cfg, c["code"], lookback_days=dip_lookback_days + 15)
                recent = rows[-dip_lookback_days:]
                recent_high = max(r["high"] for r in recent)
                c["decline_from_high_pct"] = (c["price"] - recent_high) / recent_high * 100
            except Exception:
                c["decline_from_high_pct"] = 0.0  # 조회 실패한 종목은 순위에서 밀려나도록
        candidates.sort(key=lambda c: c["decline_from_high_pct"])  # 가장 많이 떨어진(가장 음수) 순
        # 하락폭 순위만 매기고 끝내면, 정작 지금 매수 기준(dip_buy_pct)에 못 미치는
        # 종목까지 상위권에 들어와버린다 (예: 기준 -15% 인데 -8%짜리도 순위엔 낌).
        # 지금 당장 매수 신호가 뜨는 것만 남긴다.
        before = len(candidates)
        candidates = [c for c in candidates if c["decline_from_high_pct"] <= cfg.dip_buy_pct]
        skipped = before - len(candidates)
        if skipped:
            print(f"  (매수 기준 {cfg.dip_buy_pct}% 에 못 미쳐 제외된 종목 {skipped}개)")
    else:
        candidates.sort(key=lambda c: c["day_range_pct"], reverse=True)

    return candidates


def find_mixed_ai_dip_candidates(cfg, top_n: int, dip_lookback_days: int = DIP_LOOKBACK_DAYS) -> list[dict]:
    """AI 관련주와 전체 시장 후보를 합쳐서, 하락폭 조건(+예산)을 만족하는 종목 중
    하락폭이 가장 큰 순으로 top_n개를 고른다 (2026-08-13, AI 우선순위 제거 -
    특정 업종에 쏠리지 않고 전체 시장에서 조건에 가장 잘 맞는 종목을 고르도록
    변경. AI_THEME_STOCKS 도 여전히 후보 풀에는 포함되지만 더 이상 우선권은
    없다 - 조건이 더 좋은 다른 업종 종목이 있으면 그쪽이 먼저 뽑힌다).

    (2026-08-21) 최근 계속 손실만 낸 종목 + 지금까지 전체 기록상 누적 손실인
    종목(loss_cooldown 참고 - 예: 셀바스AI가 08-14/08-18/08-21 세 번 다 손실,
    누적 -35,920원)은 가격+거래량 조건을 만족해도 여기서 걸러낸다 - 이 필터를
    find_mixed_ai_dip_candidates() 안에 두면 저녁 스크리닝(다음날 감시목록
    선정)과 장중 슬롯 교체(replace_blocked_stock) 양쪽 다 자동으로 적용된다."""
    ai_candidates = find_candidates(cfg, mode="ai-dip", dip_lookback_days=dip_lookback_days)
    market_candidates = find_candidates(cfg, mode="dip", dip_lookback_days=dip_lookback_days)

    merged: dict[str, dict] = {}
    for c in market_candidates + ai_candidates:
        merged.setdefault(c["code"], c)

    cooldown = loss_cooldown.excluded_codes()
    combined = sorted(
        (c for c in merged.values() if c["code"] not in cooldown),
        key=lambda c: c["decline_from_high_pct"],
    )

    combined = _filter_affordable(cfg, combined)
    return combined[:top_n]


MIN_TRADE_VALUE_VOLATILITY = 5_000_000_000  # 변동성 모드 전용 거래대금 하한(50억원, 2026-08-24: 100억->50억)


def find_mixed_ai_volatility_candidates(cfg, top_n: int, dip_lookback_days: int = DIP_LOOKBACK_DAYS) -> list[dict]:
    """AI 관련주와 전체 시장 후보를 합쳐서, 오늘 일중 변동폭(day_range_pct)이
    가장 큰 순으로 top_n개를 고른다 (2026-08-21, "변동성 큰 종목 위주로 활발하게
    거래하고 싶다"는 요청으로 추가). find_mixed_ai_dip_candidates() 와 반대로
    "고점 대비 얼마나 빠졌나"가 아니라 "오늘 하루 얼마나 출렁였나"만 본다 -
    실제 매수 트리거는 여전히 strategy.compute_dip_signal() 이 담당하므로,
    여기서 후보로 뽑혔다고 바로 사는 건 아니고 dip_buy_pct/rebound_confirm_pct
    조건은 그대로 적용된다 (이 모드에 맞게 그 값들도 함께 낮춰 쓰는 걸 권장).

    (2026-08-21 추가, 2026-08-24 100억->50억으로 완화) 변동성만 보고 뽑으면
    거래대금이 기본 하한선(30억원)을 겨우 넘는, 얇게 거래되는 종목도 "오늘
    변동폭이 크다"는 이유로 상위권에 들 수 있다. 이 모드는 목표 수익폭이
    1%대로 작아서 슬리피지(원하는 가격에 정확히 체결 안 되는 것)에 특히
    취약하므로, 기본 하한선보다 높은 MIN_TRADE_VALUE_VOLATILITY를 추가로
    요구한다 - 변동성도 크고 실제로 거래도 활발한 종목만 남긴다. (2026-08-24)
    처음엔 100억원으로 잡았는데, 그날 매매가 1건뿐이었던 이유 중 하나로
    의심돼 50억원으로 완화 - 다만 그날 활발하지 않았던 진짜 큰 원인은 슬롯
    3개 버그였고, 이 기준 자체의 영향은 아직 데이터로 확인 안 됨(그래서
    바로 아래에서 몇 종목이 이 기준 때문에 걸러졌는지 로그를 남긴다).

    dip_lookback_days 인자는 find_mixed_ai_dip_candidates() 와 시그니처를
    맞추기 위해 받지만 여기서는 쓰지 않는다(변동성 순위는 하락폭 계산이 필요
    없음)."""
    ai_candidates = find_candidates(cfg, mode="ai")
    market_candidates = find_candidates(cfg, mode="volatility")

    merged: dict[str, dict] = {}
    for c in market_candidates + ai_candidates:
        merged.setdefault(c["code"], c)

    cooldown = loss_cooldown.excluded_codes()
    after_cooldown = [c for c in merged.values() if c["code"] not in cooldown]
    liquid_enough = [c for c in after_cooldown if c.get("trade_value", 0) >= MIN_TRADE_VALUE_VOLATILITY]
    # (2026-08-24) "50억으로 낮추면 몇 개나 더 뽑히나"를 나중에 실제 데이터로
    # 확인할 수 있도록, 이 기준 때문에 걸러진 개수를 남긴다.
    skipped_by_liquidity = len(after_cooldown) - len(liquid_enough)
    if skipped_by_liquidity:
        print(f"  (변동성 후보 중 거래대금 {MIN_TRADE_VALUE_VOLATILITY/1e8:.0f}억원 미만이라 "
              f"제외된 종목 {skipped_by_liquidity}개)")

    combined = sorted(liquid_enough, key=lambda c: c["day_range_pct"], reverse=True)

    combined = _filter_affordable(cfg, combined)
    return combined[:top_n]


def find_watchlist_candidates(cfg, top_n: int, dip_lookback_days: int = DIP_LOOKBACK_DAYS) -> list[dict]:
    """cfg.candidate_selection 에 따라 알맞은 후보 선정 함수로 보내는 진입점.
    auto_pick_and_apply()/replace_blocked_stock() 둘 다 이걸 거치므로, config.yaml
    에서 candidate_selection 값만 바꾸면 저녁 스크리닝과 장중 슬롯 교체 양쪽 다
    같이 바뀐다."""
    if cfg.candidate_selection == "volatility":
        return find_mixed_ai_volatility_candidates(cfg, top_n, dip_lookback_days=dip_lookback_days)
    return find_mixed_ai_dip_candidates(cfg, top_n, dip_lookback_days=dip_lookback_days)


def replace_blocked_stock(cfg, blocked_code: str, dip_lookback_days: int = DIP_LOOKBACK_DAYS) -> dict | None:
    """감시목록 중 blocked_code 하나를, 장중에 바로 찾은 다른 종목으로 교체한다
    (2026-08-11 추가). 거래 불가로 확인된 종목 자리를 그냥 비워두지 않고 채운다.

    지금 감시 중인 종목 + 오늘 이미 블록된 종목은 전부 후보에서 제외한 뒤 새로
    찾는다. watchlist 만 바꾸므로(entry_mode/dip_buy_pct 등 위험 설정은 그대로),
    evening_screen 의 자동 교체와 마찬가지로 REAL 재확인 없이 다음 회차부터
    바로 적용된다. 대체할 만한 종목이 없으면 None 을 반환하고, blocked_code 는
    watchlist 에서 그냥 빼버린다(자리를 비워둠).

    (2026-08-20 버그수정) 예전엔 대체 후보가 없으면 watchlist 를 아예 안 건드리고
    그냥 None 만 반환했는데, 그러면 blocked_code 가 watchlist 에 그대로 남아있어서
    다음 회차에 다시 조건을 만족하면 재매수될 수 있었다. 특히 방금 손절로 판
    직후라면, 그 하락 자체가 dip_buy 진입 조건(하락+반등)을 새로 만족시켜서
    바로 재매수 -> 같은 종목에서 손실이 반복되는 사고로 이어졌다(2026-08-20
    바이오니아: 11:55 손절 후 12:05 재매수). "매도되면 그 슬롯은 그 종목과 끝"
    이라는 방침을 지키려면, 대체를 못 찾아도 최소한 원래 종목은 빼야 한다.

    (2026-08-20 추가 버그수정, "당일 재진입 금지") 위 수정으로 원래 종목 자체는
    watchlist 에서 빠지게 됐지만, "대체 후보를 찾는" 이 함수 자체가 오늘 이미
    판 종목은 후보에서 계속 빼야 한다는 걸 놓치고 있었다. 예를 들어 A를 팔고
    빈 슬롯에 B를 넣었는데, 그 다음 회차에 B가 막혀서 다시 교체할 때 후보
    검색에 A가 다시 걸리면(A가 여전히 하락+반등 조건을 만족하면) A를 도로
    사버릴 수 있었다 - watchlist 제외 목록엔 "지금 감시 중인 종목"만 있고
    "오늘 이미 팔았던 종목"은 없었기 때문. sold_today 모듈로 오늘 판 종목을
    전부 제외 대상에 넣어서 막는다.

    주의: cfg 대신 config.yaml을 파일에서 새로 읽어서 현재 감시목록 기준으로
    계산한다 (2026-08-11 버그수정) - 원래 인자로 받은 cfg.watchlist를 그대로
    쓰면, 한 회차 안에서 여러 종목이 연달아 막혔을 때 뒤에 처리된 교체가
    앞서 처리된 교체를 파일에서 되돌려버리는 문제가 있었다 (먼저 바뀐 내용을
    무시하고 항상 "최초 로드 시점의" 목록을 기준으로 다시 썼기 때문)."""
    current_cfg = load_config()  # 지금 파일에 실제로 쓰여있는 최신 상태
    current_codes = {w.code for w in current_cfg.watchlist}
    exclude = current_codes | set(blocklist.all_blocked().keys()) | sold_today.all_sold_today()

    # (2026-08-24) 여백을 +3으로 작게 잡아뒀었는데(예전 슬롯 3개 시절), 지금은
    # 슬롯도 5개로 늘고 loss_cooldown(최근/누적 손실 종목 제외)까지 겹쳐서 실제로
    # 조건을 만족하는 전체 후보 풀 자체가 exclude 크기 근처까지 줄어드는 날엔
    # "대체 후보 없음"이 자주 나서 슬롯이 비어있는 시간이 늘어난다 - 이것도 오늘
    # "매매가 활발하지 않다"의 원인 중 하나로 보인다. 여백을 넉넉히 키운다
    # (API 호출 몇 번 더 느는 것 외엔 부작용 없음).
    candidates = find_watchlist_candidates(cfg, len(exclude) + 15, dip_lookback_days=dip_lookback_days)
    fresh = [c for c in candidates if c["code"] not in exclude]
    if not fresh:
        remaining = [
            {"code": w.code, "name": w.name} for w in current_cfg.watchlist if w.code != blocked_code
        ]
        if len(remaining) != len(current_cfg.watchlist):
            apply_to_config(remaining)
        return None
    replacement = fresh[0]

    new_watchlist = [
        {"code": replacement["code"], "name": replacement["name"]}
        if w.code == blocked_code else {"code": w.code, "name": w.name}
        for w in current_cfg.watchlist
    ]
    apply_to_config(new_watchlist)
    # (2026-09-01, 사토시룰) 장중 교체는 오늘 하루가 아직 안 끝났으므로
    # exclude_last=True(기본값)로 오늘자 미확정 데이터는 빼고 계산한다.
    volatility.evaluate_candidates(cfg, [replacement])
    return replacement


def apply_to_config(picked: list[dict], entry_mode: str | None = None, dip_buy_pct: float | None = None):
    """watchlist 섹션만 텍스트로 교체한다. (yaml.safe_load/dump 왕복은 파일 곳곳의
    설명 주석을 전부 날려버려서, 그 대신 watchlist: 블록만 정규식으로 갈아끼운다.)
    entry_mode/dip_buy_pct 를 주면 strategy 의 해당 줄도 그 값으로 같이 바꾼다."""
    text = CONFIG_PATH.read_text(encoding="utf-8")

    if picked:
        # (2026-08-20) picked 가 빈 리스트일 수 있다 - replace_blocked_stock 이
        # 대체 후보를 못 찾고 마지막 남은 종목 하나를 빼는 경우. 0으로 나누면
        # 안 되므로 분기한다.
        ratio = round(1.0 / len(picked), 4)
        lines = ["watchlist:"]
        for c in picked:
            lines.append(f'  - code: "{c["code"]}"')
            lines.append(f'    name: "{c["name"]}"')
            lines.append(f"    invest_ratio: {ratio}")
        new_block = "\n".join(lines) + "\n"
    else:
        new_block = "watchlist: []\n"

    # (2026-08-25 버그수정) 원래 r"^watchlist:\n" 이라 "watchlist:" 바로 뒤에 개행이
    # 와야만 매치됐다. 그런데 이 함수 자신이 대체 후보를 못 찾으면 "watchlist: []\n"
    # (콜론 뒤에 " []" 가 붙어 같은 줄에 있음) 형태로 쓰는데, 그 형태는 이 정규식이
    # 아예 못 찾아서 다음 호출에서 "watchlist 섹션을 찾지 못했습니다" 로 죽어버렸다.
    # 실제 계좌에서 확인됨: 2026-08-24 낮에 대체 실패가 반복되며 watchlist가
    # "[]" 로 비었고, 그 상태에서 evening_screen.py 를 다시 돌리자마자 이 에러로
    # 크래시 - 정작 이 함수가 고쳐야 할 상황을 이 함수 자신이 못 고치는 상태였다.
    # "watchlist:" 뒤에 같은 줄에 뭐가 오든(" []" 포함, 또는 아무것도 없든) 다
    # 받아들이도록 .* 를 추가한다.
    pattern = re.compile(r"^watchlist:.*\n(?:[ \t].*\n?)*", re.MULTILINE)
    new_text, n = pattern.subn(new_block, text, count=1)
    if n == 0:
        raise RuntimeError("config.yaml에서 watchlist 섹션을 찾지 못했습니다.")

    if entry_mode is not None:
        new_text, n = re.subn(
            r"^(\s*entry_mode:\s*)\w+", rf"\g<1>{entry_mode}", new_text, count=1, flags=re.MULTILINE
        )
        if n == 0:
            raise RuntimeError("config.yaml에서 entry_mode 를 찾지 못했습니다.")

    if dip_buy_pct is not None:
        new_text, n = re.subn(
            r"^(\s*dip_buy_pct:\s*)-?[\d.]+", rf"\g<1>{dip_buy_pct}", new_text, count=1, flags=re.MULTILINE
        )
        if n == 0:
            raise RuntimeError("config.yaml에서 dip_buy_pct 를 찾지 못했습니다.")

    CONFIG_PATH.write_text(new_text, encoding="utf-8")


def auto_pick_and_apply(cfg, top_n: int | None = None, dip_lookback_days: int = DIP_LOOKBACK_DAYS) -> list[dict]:
    """사람의 GO 확인 없이 그대로 적용한다 (daemon 이 매일 저녁 자동으로 호출하는 용도).

    entry_mode/dip_buy_pct 같은 위험 관련 설정은 안 건드리고 watchlist 만 바꾼다 -
    그래야 main.py 의 REAL 재확인 지문(위험설정에서 watchlist 는 제외됨, 2026-08-04)에
    걸리지 않고 다음날 아침 바로 매매에 들어간다. 위험 설정 자체를 바꾸고 싶으면
    사람이 config.yaml 을 직접 수정하거나 --dip-buy-pct 옵션으로 GO 확인을 거쳐야 한다.

    (2026-08-24 버그수정) top_n 기본값이 예전엔 TOP_N(3, 2026-08-13에 슬롯이 3개였을
    때 고정된 상수)이었는데, max_positions 를 5로 늘려도 이 기본값은 안 따라가서
    daemon 이 매일 저녁 인자 없이 부르면 계속 3종목만 뽑혔다(evening_screen.py 에서
    실제로 발생 확인, 2026-08-24). top_n 을 안 주면 그때그때 cfg.max_positions 를
    따라가게 해서, "슬롯 수의 진짜 기준은 max_positions 하나뿐"이 되게 한다 - 이
    함수 자체를 top_n 없이 불러도 더 이상 상수 때문에 어긋나지 않는다."""
    if top_n is None:
        top_n = cfg.max_positions
    picked = find_watchlist_candidates(cfg, top_n, dip_lookback_days=dip_lookback_days)
    if not picked:
        print("조건을 만족하는 종목이 없어 watchlist 를 바꾸지 않았습니다.")
        return picked
    apply_to_config(picked)
    # (2026-08-19) 감시목록을 통째로 새로 짰으니, 어제자 관찰 카운터(watch_state)가
    # 오늘 남아있으면 안 된다 - 전부 초기화한다.
    watch_state.clear_all()
    # (2026-08-20) "오늘 판 종목" 기록도 새 거래일 시작 전에 지운다 - 어제 판
    # 종목이 오늘까지 재진입 금지로 남으면 안 된다.
    sold_today.clear_all()
    # (2026-09-01, 사토시룰) 어제자 변동성 표시도 새 감시목록 기준으로 다시 잡는다.
    # 저녁 시점엔 오늘 하루가 이미 끝났으므로 exclude_last=False로 오늘자 데이터도 포함.
    volatility.clear_all()
    volatility.evaluate_candidates(cfg, picked, exclude_last=False)
    print(f"watchlist 를 아래 {len(picked)}개 종목으로 교체했습니다 (entry_mode/dip_buy_pct 는 그대로 유지):")
    for c in picked:
        # (2026-08-21 버그수정) candidate_selection: volatility 로 뽑힌 후보는
        # decline_from_high_pct 가 아니라 day_range_pct 를 갖고 있어서, dip 모드
        # 전용 필드를 그대로 찍으면 KeyError 로 죽었다 - auto_pick_and_apply()가
        # daemon 이 매일 저녁 자동으로 부르는 함수라, 이 버그는 volatility 모드로
        # 바꾼 첫날 저녁 스크리닝을 통째로 실패시켰을 것이다.
        if "decline_from_high_pct" in c:
            print(f"  - {c['name']}({c['code']}) 고점대비 {c['decline_from_high_pct']:+.1f}%")
        else:
            print(f"  - {c['name']}({c['code']}) 오늘 변동폭 {c['day_range_pct']:.1f}%")
    return picked


def main():
    parser = argparse.ArgumentParser(description="변동성/하락폭 상위 종목 스크리너")
    parser.add_argument(
        "--mode", choices=["volatility", "dip", "ai", "ai-dip", "ai-dip-mixed", "news"], default="volatility",
        help="volatility: 오늘 변동폭 큰 순 / dip: 최근 고점 대비 하락폭 큰 순 "
             "/ ai: AI 관련주 중 오늘 변동폭 큰 순 "
             "/ ai-dip: AI 관련주 중 고점 대비 하락폭 큰 순 (AI + 하락폭 동시 고려) "
             "/ ai-dip-mixed: ai-dip 로 채우고 모자란 자리는 전체시장 dip 후보로 채움 "
             "/ news: AI 관련주 중 최근 뉴스가 호재로 판단된 종목만 (Anthropic API 과금)",
    )
    parser.add_argument("--dip-days", type=int, default=DIP_LOOKBACK_DAYS,
                         help="dip 모드에서 고점을 계산할 기간(일), 기본 %(default)s")
    parser.add_argument("--dip-buy-pct", type=float, default=None,
                         help="이 값을 주면 config.yaml 의 dip_buy_pct 대신 이 기준으로 후보를 뽑고, "
                              "적용 시 config.yaml 의 dip_buy_pct 도 이 값으로 같이 바꾼다")
    parser.add_argument("--dry-run", action="store_true", help="후보만 보여주고 설정은 안 바꿈")
    parser.add_argument("--top", type=int, default=TOP_N, help="몇 개를 고를지 (기본 %(default)s)")
    args = parser.parse_args()

    cfg = load_config()
    if args.dip_buy_pct is not None:
        cfg = dataclasses.replace(cfg, dip_buy_pct=args.dip_buy_pct)
    print(f"[{args.mode} 모드] 후보 종목 조회 중...")

    if args.mode == "news":
        print(f"AI 관련주 {len(AI_THEME_STOCKS)}개 뉴스 판단 중 (종목당 API 호출 1회)...")
        candidates = find_news_candidates(cfg)
        candidates = _filter_affordable(cfg, candidates)
        picked = candidates[: args.top]
        print(f"\n=== 뉴스 호재로 판단된 종목 {len(picked)}개 ===")
        for i, c in enumerate(picked, 1):
            print(f"  {i}. {c['name']:12s} ({c['code']}) 현재가 {c['price']:>8,.0f}원 - {c['reason']}")

        if not picked:
            print("\n호재로 판단된 종목이 없어 config.yaml 을 바꾸지 않습니다.")
            return
        if args.dry_run:
            print("\n--dry-run 이라 config.yaml 은 그대로 뒀습니다.")
            return

        print(f"\n위 {len(picked)}개 종목으로 config.yaml 의 watchlist 를 교체하고, "
              f"entry_mode 도 news_buy 로 바꿉니다 (각 {100/len(picked):.0f}%).")
        answer = input("정말 교체하려면 GO 를 입력하세요: ").strip()
        if answer != "GO":
            print("취소되었습니다.")
            return

        apply_to_config(picked, entry_mode="news_buy")
        print("config.yaml 갱신 완료 (watchlist + entry_mode: news_buy). "
              "다음 실행에서 이 종목들이 바로 매수됩니다.")
        print("(위험 관련 설정이 바뀐 걸로 인식되어, 다음 main.py 실행 시 REAL 재확인이 필요합니다)")
        return

    if args.mode == "ai-dip-mixed":
        candidates = find_mixed_ai_dip_candidates(cfg, args.top, dip_lookback_days=args.dip_days)
    else:
        candidates = find_candidates(cfg, mode=args.mode, dip_lookback_days=args.dip_days)
        candidates = _filter_affordable(cfg, candidates)

    picked = candidates[: args.top]
    if args.mode in ("dip", "ai-dip", "ai-dip-mixed"):
        label = {
            "ai-dip": "AI 관련주 중 고점 대비 하락폭 상위",
            "ai-dip-mixed": "AI 관련주+전체시장 합쳐 하락폭 상위",
        }.get(args.mode, "최근 고점 대비 하락폭 상위")
        print(f"\n=== {label} {len(picked)}개 (최근 {args.dip_days}일 기준, "
              f"거래대금 {MIN_TRADE_VALUE/1e8:.0f}억원 이상만) ===")
        for i, c in enumerate(picked, 1):
            print(
                f"  {i}. {c['name']:12s} ({c['code']}) 현재가 {c['price']:>8,.0f}원 "
                f"고점대비 {c['decline_from_high_pct']:+6.1f}% 등락 {c['change_pct']:+6.2f}% "
                f"거래대금 {c['trade_value']/1e8:,.0f}억"
            )
    else:
        label = "AI 관련주 중 변동폭 상위" if args.mode == "ai" else "변동폭 상위"
        print(f"\n=== {label} {len(picked)}개 (거래대금 {MIN_TRADE_VALUE/1e8:.0f}억원 이상만) ===")
        for i, c in enumerate(picked, 1):
            print(
                f"  {i}. {c['name']:12s} ({c['code']}) 현재가 {c['price']:>8,.0f}원 "
                f"등락 {c['change_pct']:+6.2f}% 일중변동폭 {c['day_range_pct']:5.1f}% "
                f"거래대금 {c['trade_value']/1e8:,.0f}억"
            )

    if args.dry_run:
        print("\n--dry-run 이라 config.yaml 은 그대로 뒀습니다.")
        return

    extra_note = f", dip_buy_pct 도 {args.dip_buy_pct}% 로" if args.dip_buy_pct is not None else ""
    print(f"\n위 {len(picked)}개 종목으로 config.yaml 의 watchlist 를 교체{extra_note} 합니다 (각 {100/len(picked):.0f}%).")
    answer = input("정말 교체하려면 GO 를 입력하세요: ").strip()
    if answer != "GO":
        print("취소되었습니다.")
        return

    apply_to_config(picked, dip_buy_pct=args.dip_buy_pct)
    print("config.yaml 갱신 완료. 다음 실행부터 이 종목들이 감시목록이 됩니다.")
    print("(위험 관련 설정이 바뀐 걸로 인식되어, 다음 main.py 실행 시 REAL 재확인이 필요합니다)")


if __name__ == "__main__":
    main()
