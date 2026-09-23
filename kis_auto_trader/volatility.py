"""
"사토시룰" - 감시종목 중 유독 크게 흔들리는 종목을 표시해서, 매도 감시를
빠른 루프(watch_positions.py)로 돌리게 한다 (2026-09-01 추가).

계기: 9/1 사토시홀딩스(223310) - 매수 10분 만에 -4.3% 손절. 눌림목 전략의
10분 주기 감시 사이(최대 10분) 급락을 놓칠 수 있다는 게 확인됐다. 근데 보유
종목 전부를 짧은 주기로 보면 API 호출/동시실행 충돌 위험이 커지므로, "유독
잘 흔들리는 종목만" 골라서 그것만 빠르게 본다.

매수 여부에는 전혀 관여하지 않는다 - strategy.compute_entry_signal() 이 여전히
그 판단을 전담하고, 여기서는 "이미 매수하기로 정해진 종목을 산 뒤 얼마나 자주
들여다볼지"만 정한다.

기준값(SATOSHI_RULE_THRESHOLD_PCT): 실제 데이터로 정함 - 2026-08-25~08-31
5거래일 평균 일중변동폭이 사토시홀딩스 12.6%, 성호전자 9.0%, 루닛 3.8%였다.
사토시홀딩스와 나머지를 뚜렷하게 가르는 지점이라 10%로 잡았다. 매매 판단
자체(살지 말지)에 쓰는 게 아니라 감시 속도만 정하는 값이라, 코스닥 슬롯
기준(risk.py)만큼 엄격하게 검증할 필요는 없다고 보고 우선 이 값으로 시작한다.
"""
import csv
import json
from datetime import datetime

import api_client
from common import BASE_DIR, CANDIDATE_VOLATILITY_LOG_PATH, Config

SATOSHI_RULE_THRESHOLD_PCT = 10.0

VOLATILITY_FLAG_PATH = BASE_DIR / "volatility_flags.json"
# (2026-09-01) 나중에 "코스닥 지표와 개별 종목 변동성 사이에 관계가 있는지"도
# 검증해보기로 해서, 사토시룰 판정 여부와 무관하게 계산할 때마다 전부 기록한다.
# 백업 대상 로그 파일이라(backup.py) 경로는 common.py에서 중앙 관리한다 -
# market_history.csv/investor_history.csv 등 다른 분석용 로그와 동일한 패턴.
VOLATILITY_LOG_PATH = CANDIDATE_VOLATILITY_LOG_PATH


def compute_recent_range_pct(daily_rows: list[dict], days: int = 5, exclude_last: bool = True) -> float | None:
    """최근 `days`거래일의 평균 일중 변동폭(%) = 평균((고가-저가)/종가 * 100).

    exclude_last=True 면 가장 최근 1행을 빼고 계산한다 - 장중에 조회하면 오늘
    행의 고가/저가가 아직 확정 전이라(하루가 안 끝났으므로) 낮게 잡혀 왜곡될 수
    있어서다 (replace_blocked_stock처럼 장중에 부르는 곳에서 씀). 반대로 저녁
    스크리닝(장마감 후, evening_screen.py)처럼 오늘 하루가 이미 끝난 시점에
    부르는 곳에서는 exclude_last=False로 불러서 오늘자 데이터도 포함시킨다.

    daily_rows는 api_client.get_daily_prices()가 돌려주는 형식(오래된 순, close/high/low
    포함)을 그대로 받는다. days거래일치를 못 채우면(데이터 부족) None."""
    rows = daily_rows[:-1] if exclude_last and len(daily_rows) > 1 else daily_rows
    recent = rows[-days:]
    if len(recent) < days:
        return None
    ranges = [(r["high"] - r["low"]) / r["close"] * 100 for r in recent if r.get("close")]
    if len(ranges) < days:
        return None
    return sum(ranges) / len(ranges)


def is_high_volatility(volatility_pct: float | None) -> bool:
    return volatility_pct is not None and volatility_pct >= SATOSHI_RULE_THRESHOLD_PCT


def _load_flags() -> dict:
    if VOLATILITY_FLAG_PATH.exists():
        try:
            return json.loads(VOLATILITY_FLAG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_flags(data: dict) -> None:
    VOLATILITY_FLAG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def set_flag(code: str, name: str, flagged: bool) -> None:
    """code를 사토시룰 대상으로 표시(flagged=True)하거나 표시를 뺀다(False)."""
    data = _load_flags()
    if flagged:
        data[code] = name
    else:
        data.pop(code, None)
    _save_flags(data)


def flagged_codes() -> set:
    """지금 사토시룰(변동성 슬롯)로 표시된 종목코드들. watch_positions.py가 이걸
    보유종목과 교집합해서 빠른 감시 대상을 정한다."""
    return set(_load_flags().keys())


def clear_all() -> None:
    """저녁스크리닝으로 감시목록을 통째로 새로 짤 때 표시를 전부 지운다
    (sold_today.py/watch_state.py와 같은 패턴 - 어제 표시가 오늘까지 남으면 안 됨)."""
    _save_flags({})


def log_volatility(code: str, name: str, volatility_pct: float | None, flagged: bool) -> None:
    """분석용 기록 - 매 회 계산할 때마다 남긴다. market.log_index_snapshot과
    동일하게, 조회/기록 실패는 그 건만 건너뛰고 절대 예외를 던지지 않는다
    (매매 감시를 막으면 안 되므로)."""
    try:
        write_header = not VOLATILITY_LOG_PATH.exists()
        with open(VOLATILITY_LOG_PATH, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "code", "name", "volatility_pct", "flagged"])
            if write_header:
                writer.writeheader()
            writer.writerow({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "code": code,
                "name": name,
                "volatility_pct": f"{volatility_pct:.1f}" if volatility_pct is not None else "",
                "flagged": "Y" if flagged else "N",
            })
    except Exception:
        return


def evaluate_candidates(cfg: Config, picked: list[dict], exclude_last: bool = True) -> None:
    """확정된 감시종목들(picked - 저녁스크리닝이면 전체, 장중 교체면 새로 들어온
    1종목)의 변동성을 계산해서 로그에 남기고, 사토시룰 기준을 넘으면 빠른
    매도감시 대상으로 표시한다.

    picked는 보통 최대 5~6개라 종목당 일봉 조회가 하나씩 추가로 나가도 부담이
    작다 - screener.py의 기존 후보선정 로직(이미 복잡하고 검증된 코드)은 전혀
    건드리지 않기 위해 일부러 여기서 독립적으로 다시 조회한다.

    개별 종목 조회 실패는 그 종목만 건너뛴다 (fail-open) - 변동성 표시를 못
    해도 그냥 평소처럼 10분 주기로만 감시되는 것뿐이라, 매매 자체를 막을
    정도로 심각한 문제는 아니다."""
    for c in picked:
        code, name = c.get("code"), c.get("name", "")
        if not code:
            continue
        try:
            rows = api_client.get_daily_prices(cfg, code, lookback_days=15)
            volatility_pct = compute_recent_range_pct(rows, days=5, exclude_last=exclude_last)
        except Exception as e:
            print(f"  [!] {name}({code}) 변동성 계산 실패, 건너뜁니다: {e}")
            continue
        flagged = is_high_volatility(volatility_pct)
        set_flag(code, name, flagged)
        log_volatility(code, name, volatility_pct, flagged)
        if flagged:
            print(
                f"  [사토시룰] {name}({code}) 최근 5일 평균 변동폭 {volatility_pct:.1f}% "
                f"(기준 {SATOSHI_RULE_THRESHOLD_PCT}% 이상) -> 매도 시 빠른 감시(watch_positions.py) 대상"
            )
