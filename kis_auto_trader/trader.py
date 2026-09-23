"""
하루 여러 회차 실행을 전제로 한 관찰 + 다중 팩터 가상매매 로직.

(2026-09-04 대개편) 사용자가 계좌 자금을 전부 인출하고 실전투자를 완전히
접은 뒤, 이 프로그램을 가상투자용 데이터 수집 전용으로 쓰기로 했다.
api_client.py 에서 실제 주문을 낼 수 있는 함수 자체를 삭제했고, dip_buy
진입신호(strategy.py)도 삭제했다 - 이미 실패로 확인된 전략이라 새 팩터
기반 전략으로 교체할 예정이었다.

(2026-09-05 확장) "감시종목 수를 늘리고, 여러 투자 방식을 실제로 했다면
어떤 데이터가 나올지 보고 싶다"는 요청으로:

  1) 관찰 대상을 감시종목(5개) + 오늘 등락률 상위/하위 종목(screener의
     기존 순위 API, 약 60종목)으로 넓혔다.
  2) 국내외 논문 조사(주말 대화 참고) 기준 네 가지 팩터 전략을 동시에
     가상매매로 시험한다 - 모멘텀/추세추종/저변동성/밸류(factors.py 참고).
     전략마다 독립된 가상 포지션 장부를 갖는다(virtual_positions.py).
     같은 손절/익절 기준(cfg.stop_loss_pct/take_profit_pct)을 네 전략에
     똑같이 적용해서, "진입 조건만 다를 때 어느 쪽이 나은가"를 공정하게
     비교할 수 있게 했다 - 청산 기준까지 다르면 뭐가 차이를 만들었는지
     구분이 안 되므로.

실제 계좌 잔고는 정보용으로만 조회한다 - 혹시 예상과 달리 아직 보유 중인
종목이 있으면(과거 잔량 등) 경고만 남기고 절대 자동으로 매도를 시도하지
않는다(그럴 수 있는 코드 자체가 더 이상 없음) - 있다면 KIS 앱에서 직접
확인/매도해야 한다.
"""
from datetime import datetime

import api_client
import backup
import candidate_snapshot
import factors
import market
import screener
import virtual_positions
from common import Config

# 동시에 시험할 팩터 전략 목록. 하나씩 늘리고 검증하라는 원칙과 별개로,
# 지금 단계는 "여러 방식을 돌렸을 때 어떤 경향이 나오는지" 데이터부터
# 쌓는 탐색 단계라서 넷을 동시에 관찰한다 - 결론은 나중에 이 데이터를
# 발견/검증 기간으로 나눠서 낸다 (오늘 당장 어느 게 이긴다고 판단 안 함).
FACTOR_STRATEGIES = ["momentum", "trend", "low_vol", "value"]
TOP_PCT = 0.2  # 모멘텀/저변동성/밸류: 상위(또는 하위) 이 비율 안에 들면 후보


def _safe_float(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _build_universe(cfg: Config) -> list[dict]:
    """감시종목(config.yaml) + 오늘 등락률 상위/하위 종목(screener 기존 순위
    API)을 합쳐 관찰 대상을 넓힌다. 순위 API 조회가 실패해도 감시종목만으로는
    계속 진행한다(fail-open)."""
    seen: dict[str, dict] = {}
    for item in cfg.watchlist:
        seen[item.code] = {"code": item.code, "name": item.name}
    try:
        for c in screener._base_candidates(cfg):
            seen.setdefault(c["code"], {"code": c["code"], "name": c["name"]})
    except Exception as e:
        print(f"[!] 후보군 확장 조회 실패 (감시종목 {len(seen)}개만으로 계속 진행): {e}")
    return list(seen.values())


def _percentile_cutoff(values: list[float], pct: float, from_top: bool) -> float | None:
    """values를 정렬해서 상위(from_top=True)/하위(False) pct 지점의 값을 돌려준다.
    values가 비어있으면 None."""
    if not values:
        return None
    ordered = sorted(values, reverse=from_top)
    idx = max(int(len(ordered) * pct) - 1, 0)
    return ordered[idx]


def _qualifies(strategy: str, e: dict, cutoffs: dict) -> bool:
    if strategy == "momentum":
        return (e["momentum"] is not None and cutoffs.get("momentum") is not None
                and e["momentum"] >= cutoffs["momentum"])
    if strategy == "trend":
        return e["above_ma"] is True
    if strategy == "low_vol":
        return (e["volatility"] is not None and cutoffs.get("low_vol") is not None
                and e["volatility"] <= cutoffs["low_vol"])
    if strategy == "value":
        return (e["pbr"] is not None and e["pbr"] > 0 and cutoffs.get("value") is not None
                and e["pbr"] <= cutoffs["value"])
    return False


def run_once(cfg: Config):
    print(f"=== 관찰 회차 시작 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")

    # (2026-09-04) 실제 주문 코드가 없으니 이 조회는 순수 정보 확인용이다.
    try:
        holdings = api_client.get_holdings(cfg)
        if holdings:
            print(
                f"[!!!] 계좌에 아직 보유 중인 종목이 {len(holdings)}개 있습니다: "
                f"{', '.join(h.get('name', c) for c, h in holdings.items())} - "
                f"이 프로그램은 더 이상 실제 매도 주문을 낼 수 없으니 KIS 앱에서 직접 확인/매도하세요."
            )
        else:
            print("현재 실제 보유 종목: 없음")
    except Exception as e:
        print(f"[!] 잔고 조회 실패 (정보용 조회라 관찰은 계속 진행합니다): {e}")

    # 코스피/코스닥, 투자자동향, 상하한가 - 시장 전체 데이터는 그대로 계속 쌓는다.
    index_closes = market.fetch_kospi_kosdaq_closes(cfg)
    market.log_index_snapshot(index_closes)
    market.log_investor_snapshot(market.fetch_investor_flows(cfg))
    market.log_uplow_snapshot(market.fetch_uplow_counts(cfg))

    universe = _build_universe(cfg)
    print(f"관찰 대상 {len(universe)}종목 (감시종목 {len(cfg.watchlist)}개 + 오늘 등락률 상위/하위 확장)")

    vstate = virtual_positions.load_state()

    enriched = []
    for c in universe:
        code, name = c["code"], c["name"]
        try:
            quote = api_client.get_quote(cfg, code)
            candidate_snapshot.log_snapshot(code, name, quote)
        except Exception as e:
            print(f"  [!] {name}({code}) 조회 실패, 건너뜁니다: {e}")
            continue

        try:
            daily_rows = api_client.get_daily_prices(cfg, code, lookback_days=90)
        except Exception:
            daily_rows = []

        raw = quote.get("raw") or {}
        enriched.append({
            "code": code, "name": name, "price": quote["price"],
            "momentum": factors.momentum_return_pct(daily_rows),
            "above_ma": factors.is_above_moving_average(daily_rows),
            "volatility": factors.volatility_stdev_pct(daily_rows),
            "pbr": _safe_float(raw.get("pbr")),
        })

    print(f"팩터 계산 완료: {len(enriched)}종목")

    cutoffs = {
        "momentum": _percentile_cutoff(
            [e["momentum"] for e in enriched if e["momentum"] is not None], TOP_PCT, from_top=True),
        "low_vol": _percentile_cutoff(
            [e["volatility"] for e in enriched if e["volatility"] is not None], TOP_PCT, from_top=False),
        "value": _percentile_cutoff(
            [e["pbr"] for e in enriched if e["pbr"] is not None and e["pbr"] > 0], TOP_PCT, from_top=False),
    }
    by_code = {e["code"]: e for e in enriched}

    for strategy in FACTOR_STRATEGIES:
        # 1) 기존 가상 포지션 청산 확인 (네 전략 다 같은 손절/익절 기준)
        keys_for_strategy = [k for k in list(vstate.keys()) if k.startswith(f"{strategy}:")]
        for key in keys_for_strategy:
            code = vstate[key]["code"]
            current = by_code.get(code)
            if current is None:
                continue  # 이번 회차에 조회 안 된 종목 - 다음 회차에 다시 시도
            virtual_positions.check_and_close(
                cfg, vstate, code, current["price"],
                cfg.stop_loss_pct, cfg.take_profit_pct, strategy=strategy,
            )

        # 2) 신규 진입 - 슬롯 여유 있고 조건 만족하는 종목만 (실제 max_positions와
        #    같은 슬롯 수를 각 전략이 독립적으로 씀)
        open_count = virtual_positions.count_open(vstate, strategy)
        for e in enriched:
            if open_count >= cfg.max_positions:
                break
            if virtual_positions.has_position(vstate, strategy, e["code"]):
                continue
            if not _qualifies(strategy, e, cutoffs):
                continue
            budget = cfg.total_capital / max(cfg.max_positions, 1)
            qty = int(budget // e["price"]) if e["price"] > 0 else 0
            if qty < 1:
                continue
            virtual_positions.open_virtual(vstate, e["code"], e["name"], e["price"], qty, strategy=strategy)
            open_count += 1
            print(f"  -> [가상:{strategy}] {e['name']}({e['code']}) {qty}주 진입 (현재가 {e['price']:,.0f}원)")

    virtual_positions.save_state(vstate)
    backup.backup_trade_data()

    print("\n=== 관찰 회차 종료 ===")
