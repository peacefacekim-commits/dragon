"""고정 유니버스의 일봉을 모아두는 저장소(패널 데이터).

(2026-09-13 신설) 왜 이런 구조인가:

그동안은 "전략을 하나 정해서 앞으로 굴려본다"는 구조였다. 그러면 손절 기준을
-4%에서 -8%로 바꿔보고 싶을 때, 보유기간을 하루에서 한 달로 바꿔보고 싶을 때
매번 처음부터 다시 쌓아야 한다. 실제로 지금까지 쌓인 가상매매 기록은 17건이고
그중 같은 종목 반복을 빼면 독립적인 판단은 11건뿐이라, 무엇도 판단할 수 없다.

반대로 "고정된 종목들의 일봉"만 쌓아두면, 나중에 어떤 보유기간이든 어떤 손절
기준이든 어떤 팩터든 같은 데이터에 다시 돌려볼 수 있다. 그래서 매매를
실시간으로 흉내내는 대신 일봉 패널을 쌓는다.

그리고 중요한 점 하나 - 일봉은 과거치를 지금 당장 받아올 수 있다. 하루씩
모으기를 기다릴 필요가 없다. 처음 한 번 몇 년치를 통째로 받아두면 그날 바로
백테스트를 돌릴 수 있고, 그 뒤로는 매일 하루치씩 이어붙이기만 하면 된다.

파일은 연도별로 나눠서 저장한다(data/panel_2026.csv 등). 한 파일에 다 넣으면
매일 수십 MB짜리 파일이 통째로 다시 커밋돼서 저장소가 금방 불어난다. 연도별로
나누면 매일 바뀌는 건 올해 파일 하나뿐이고 지난 연도는 그대로 멈춰 있다.
"""
from datetime import datetime, timedelta

import yearly_csv
from common import BASE_DIR, Config

DATA_DIR = BASE_DIR / "data"
PREFIX = "panel"
# 컬럼을 추가할 때는 반드시 맨 끝에 붙인다 (yearly_csv 문서 참고).
FIELDNAMES = ["date", "code", "name", "open", "high", "low", "close", "volume"]


def load_rows() -> dict:
    """저장된 전부를 {(date, code): row} 로 읽는다."""
    return yearly_csv.load_rows(DATA_DIR, PREFIX)


def load_by_code(only: list[str] | None = None) -> dict:
    """{code: [row, ...]} (날짜 오름차순). 백테스트가 쓰는 형태."""
    wanted = set(only) if only else None
    by_code: dict[str, list[dict]] = {}
    for (date, code), r in load_rows().items():
        if wanted is not None and code not in wanted:
            continue
        by_code.setdefault(code, []).append(r)
    for rows in by_code.values():
        rows.sort(key=lambda r: r["date"])
    return by_code


def append(new_rows: list[dict]) -> int:
    """일봉 행들을 저장소에 합친다. (date, code) 가 같으면 새 값으로 덮어쓴다.

    덮어쓰는 이유: 장중에 조회한 오늘 행은 그 시점까지의 값이라 종가/거래량이
    미완성이다. 다음 날 다시 받아서 덮어써야 제대로 된 값이 된다.

    반환값은 '새로 생긴 행 수'(덮어쓴 건 세지 않음).
    """
    return yearly_csv.append(DATA_DIR, PREFIX, FIELDNAMES, new_rows)


def coverage() -> dict:
    """{code: (첫날, 마지막날, 행수)}"""
    return yearly_csv.coverage(DATA_DIR, PREFIX)


def _missing_ranges(have: tuple | None, start: str, end: str) -> list[tuple[str, str]]:
    """이미 가진 구간을 빼고, 새로 받아와야 할 (시작, 끝) 구간들을 돌려준다.

    가운데 구멍(휴장일이 아닌 진짜 결측)은 신경 쓰지 않는다 - 일봉에서 가운데가
    비는 건 거의 다 휴장/거래정지라서, 다시 받아도 똑같이 비어 있다.
    """
    if have is None:
        return [(start, end)]
    first, last, _ = have
    ranges = []
    if start < first:
        prev = (datetime.strptime(first, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
        if start <= prev:
            ranges.append((start, prev))
    # 마지막 날은 다시 받는다 - 장중에 받아둔 미완성 행일 수 있으므로.
    if last <= end:
        ranges.append((last, end))
    return ranges


def backfill(cfg: Config, stocks: list[dict], start_date: str | None = None,
             end_date: str | None = None, verbose: bool = True) -> dict:
    """유니버스 종목들의 빠진 일봉을 받아서 저장소에 채운다.

    stocks 는 [{"code":..., "name":...}, ...]. 이미 있는 구간은 다시 받지 않으므로
    매일 돌려도 되고(그날 하루치만 받는다), 처음 한 번은 몇 년치를 받는다.
    """
    import api_client

    start_date = start_date or cfg.panel_start_date
    end_date = end_date or datetime.now().strftime("%Y%m%d")
    have = coverage()

    truncations = []

    def on_truncated(code, cs, ce, n):
        truncations.append((code, cs, ce, n))

    fetched_rows = []
    ok, failed = 0, 0
    for i, s in enumerate(stocks, 1):
        code, name = s["code"], s.get("name", "")
        ranges = _missing_ranges(have.get(code), start_date, end_date)
        got = 0
        for rs, re_ in ranges:
            try:
                bars = api_client.get_daily_prices_range(
                    cfg, code, rs, re_, on_truncated=on_truncated)
            except Exception as e:
                failed += 1
                if verbose:
                    print(f"  [!] {code} {name} {rs}~{re_} 조회 실패: {e}")
                continue
            for b in bars:
                fetched_rows.append({
                    "date": b["date"], "code": code, "name": name,
                    "open": b["open"] if b["open"] is not None else "",
                    "high": b["high"], "low": b["low"],
                    "close": b["close"], "volume": b["volume"],
                })
                got += 1
        if got:
            ok += 1
        if verbose and (i % 20 == 0 or i == len(stocks)):
            print(f"  ...{i}/{len(stocks)}종목 처리 (누적 {len(fetched_rows)}행)")

    added = append(fetched_rows)

    if truncations and verbose:
        print(f"  [!] 한 번에 받을 수 있는 최대치까지 꽉 찬 조각이 {len(truncations)}건 "
              f"있었습니다 - 그 구간은 앞부분이 잘렸을 수 있습니다 "
              f"(api_client.DAILY_PRICE_CHUNK_DAYS 를 줄여야 합니다). "
              f"예: {truncations[0]}")

    result = {"stocks": len(stocks), "fetched": len(fetched_rows), "added": added,
              "ok": ok, "failed": failed, "truncated": len(truncations)}
    if verbose:
        print(f"[패널] {result['stocks']}종목 처리, 새 행 {added}개 추가 "
              f"(받아온 행 {len(fetched_rows)}개, 실패 {failed}건)")
    return result


def summary() -> str:
    cov = coverage()
    if not cov:
        return "패널 데이터 없음 - collect_daily.py 를 한 번 실행하세요."
    total = sum(v[2] for v in cov.values())
    first = min(v[0] for v in cov.values())
    last = max(v[1] for v in cov.values())
    return (f"패널: {len(cov)}종목, {total:,}행, {first}~{last}\n"
            f"종목당 평균 {total // len(cov):,}일치")


if __name__ == "__main__":
    print(summary())
