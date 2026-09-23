"""고정 유니버스의 PER/PBR/외국인지분율 등을 하루 1회 기록한다.

(2026-09-14 신설) 왜 지금부터 쌓아야 하는가:

일봉은 과거치를 지금 당장 받아올 수 있다(panel.py). 그런데 PER/PBR 같은 값은
"지금 얼마인가"만 조회되고 과거 시계열이 없다. 그래서 밸류 팩터는 과거
백테스트가 불가능하고, 오늘부터 하루 1회씩 남기지 않으면 1년 뒤에도 여전히
검증할 수 없다. 하루 미루면 그 하루는 영구히 비는 셈이다.

즉 이 파일이 쌓이는 속도가 밸류/퀄리티 계열 종목선정 기준을 언제부터 검증할
수 있는지를 결정한다. 그래서 종목선정 기준을 바꿔보려는 지금 시점에 넣는다.

받아오는 값은 새 엔드포인트가 아니다 - api_client.get_quote() 응답(raw)에 이미
같이 오는 필드들이다(candidate_snapshot.py 가 회차마다 쓰는 것과 같은 출처).
새 TR을 추가하면 실전 계좌로 확인 전까지 필드명이 맞는지 확신할 수 없는데,
이 필드들은 이미 실전에서 쓰이고 있는 응답에서 나온다.

한계:
- 종목별 "외국인 순매수량"(frgn_ntby_qty)은 이 응답에 오기는 하는데 실제로는
  거의 항상 0이다 (2026-09-13 확인: 1,460행 중 1,448행이 0, 0이 아닌 12행은
  한 종목 하루가 중복 기록된 것). 그래서 외국인 '흐름'은 이 파일로 알 수 없고,
  들어오는 건 외국인 '지분율'(hts_frgn_ehrt)이라는 수준값이다. 매일 같은
  종목을 찍으므로 그 지분율의 일별 변화로 흐름을 간접 추정할 수는 있다.
- 종목별 '기관' 순매수는 이 응답에 아예 없다. 기관 수급은 시장 전체 단위로만
  있다(market.py 의 investor_history.csv).
- 프로그램매매 순매수(pgtr_ntby_qty)는 종목별 수급 필드 중 유일하게 제대로
  들어오므로(97%) 같이 남긴다. 프로그램매매는 기관·외국인 쪽 주문이 큰 비중을
  차지하지만 그것만은 아니라서, '기관 수급'과 같은 것으로 취급하면 안 된다.
- ROE/부채비율 같은 재무비율은 여기 없다. DART 오픈API 등 별도 출처가 필요하다.
- 시가총액(hts_avls)은 응답에 있을 때만 채워진다. 비어 있으면 비어 있는 채로
  두고 대신 넣지 않는다 - 없는 값을 추정해 채우면 나중에 그게 실제 값인지
  구분할 수 없게 된다.
"""
from datetime import datetime

import yearly_csv
from common import BASE_DIR, Config

DATA_DIR = BASE_DIR / "data"
PREFIX = "fundamentals"
# 컬럼을 추가할 때는 반드시 맨 끝에 붙인다 (yearly_csv 문서 참고).
FIELDNAMES = [
    "date", "code", "name", "price",
    "per", "pbr", "eps", "bps",
    "hts_frgn_ehrt", "vol_tnrt", "whol_loan_rmnd_rate",
    "hts_avls", "lstn_stcn",
    "w52_hgpr_vrss_prpr_ctrt",
    # (2026-09-15 추가, 반드시 맨 끝에) 종목별 수급.
    # pgtr_ntby_qty(프로그램매매 순매수)는 종목별 수급 필드 중 유일하게 제대로
    # 들어온다(candidate_snapshot 2,395행 중 97.1%). 4거래일 105 종목-일로 봤을 때
    # 순매수인 종목이 그날 마감까지 +0.15%, 순매도인 종목이 -2.18%로 방향이
    # 갈렸는데, 정작 고정 유니버스 쪽에는 이 값이 안 남고 있었다.
    # frgn_ntby_qty(외국인 순매수)는 거의 항상 0으로 오지만(1,460행 중 1,448행),
    # 종목이 바뀐 뒤에도 계속 0인지 확인할 수 있게 같이 남긴다 - 안 남기면
    # "여전히 안 오는지"조차 알 수 없다.
    "pgtr_ntby_qty", "frgn_ntby_qty",
]

# get_quote 응답(raw)에서 그대로 가져올 필드들
_RAW_FIELDS = [
    "per", "pbr", "eps", "bps",
    "hts_frgn_ehrt", "vol_tnrt", "whol_loan_rmnd_rate",
    "hts_avls", "lstn_stcn", "w52_hgpr_vrss_prpr_ctrt",
    "pgtr_ntby_qty", "frgn_ntby_qty",
]


def load_rows() -> dict:
    return yearly_csv.load_rows(DATA_DIR, PREFIX)


def coverage() -> dict:
    return yearly_csv.coverage(DATA_DIR, PREFIX)


def append(rows: list[dict]) -> int:
    return yearly_csv.append(DATA_DIR, PREFIX, FIELDNAMES, rows)


def collect(cfg: Config, stocks: list[dict], verbose: bool = True) -> dict:
    """유니버스 종목의 오늘자 재무지표를 한 번씩 조회해서 기록한다.

    이미 오늘 기록이 있는 종목은 다시 조회하지 않는다 - 하루에 여러 번 실행돼도
    API 호출이 늘어나지 않게. (단 값 자체는 하루 중 언제 찍혔는지에 따라 달라질
    수 있어서, 장 마감 뒤에 한 번 도는 걸 전제로 한다.)
    """
    import api_client

    today = datetime.now().strftime("%Y%m%d")
    have_today = {code for (date, code) in load_rows() if date == today}

    rows, failed = [], 0
    todo = [s for s in stocks if s["code"] not in have_today]
    for i, s in enumerate(todo, 1):
        try:
            quote = api_client.get_quote(cfg, s["code"])
        except Exception as e:
            failed += 1
            if verbose and failed <= 3:
                print(f"  [!] {s['code']} {s.get('name','')} 재무지표 조회 실패: {e}")
            continue
        raw = quote.get("raw") or {}
        row = {"date": today, "code": s["code"], "name": s.get("name", ""),
               "price": quote.get("price", "")}
        for f in _RAW_FIELDS:
            row[f] = raw.get(f, "")
        rows.append(row)
        if verbose and (i % 50 == 0 or i == len(todo)):
            print(f"  ...{i}/{len(todo)}종목 조회")

    added = append(rows)
    result = {"requested": len(todo), "fetched": len(rows),
              "added": added, "failed": failed, "skipped": len(stocks) - len(todo)}
    if verbose:
        print(f"[재무지표] {len(rows)}종목 기록 (새 행 {added}개, 실패 {failed}건, "
              f"오늘 이미 있어서 건너뜀 {result['skipped']}종목)")
    return result


def summary() -> str:
    cov = coverage()
    if not cov:
        return "재무지표 데이터 없음"
    total = sum(v[2] for v in cov.values())
    return (f"재무지표: {len(cov)}종목, {total:,}행, "
            f"{min(v[0] for v in cov.values())}~{max(v[1] for v in cov.values())}")


if __name__ == "__main__":
    print(summary())
