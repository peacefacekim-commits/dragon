"""수급(외국인/기관/개인) + 재무(PER/PBR) + 시가총액을 KRX에서 받는다.

(2026-09-15 신설) 왜 필요한가:

오늘 일봉만으로 만들 수 있는 지표를 거의 다 시험했는데 전부 막혔다.

  모멘텀으로 고르기        생존편향 걷으니 -4.76%p
  나쁜 날 피하기           당일 지표조차 구분 안 됨 (최악일 vs 최고일 시장등락 차이 0.005%p)
  익절/손절 조합           최선이 -0.045%, 플러스 없음
  보유기간 조정            벤치마크 대비 부호가 왔다갔다 (신호 없음)

막힌 이유가 매번 같았다. 가격과 거래량에서 유도한 지표들은 서로 비슷한 정보를
담고 있어서, 어느 쪽으로 조합해도 같은 벽에 부딪힌다.

수급(누가 사고 누가 파는가)은 가격에서 유도할 수 없는 독립적인 정보라
지금까지와 다를 가능성이 있다. 국내에서 가장 널리 쓰이는 지표이기도 하다.
사용자가 처음부터 "외국인이냐 기관이냐 개인이냐"를 물었는데, KIS 응답에는
종목별 외국인 순매수가 거의 항상 0으로 와서(1,460행 중 1,448행) 못 보고 있었다.
KRX 에는 있다.

받는 것 (종목당 1회씩 호출, 기간 전체를 한 번에):

  수급    get_market_trading_value_by_date  -> 기관합계/기타법인/개인/외국인합계 (원 단위)
  재무    get_market_fundamental_by_date    -> BPS/PER/PBR/EPS/DIV/DPS
  시총    get_market_cap_by_date            -> 시가총액/거래량/거래대금/상장주식수

사전 준비: fetch_krx_history.py 와 같다 (KRX 계정 + KRX_ID/KRX_PW 환경변수).

실행:
    python fetch_krx_extra.py --limit 3        # 형식 확인 (1분)
    python fetch_krx_extra.py --what flow      # 수급만
    python fetch_krx_extra.py                  # 셋 다 (종목당 3회 호출)

걸리는 시간 (2026-09-20 실측으로 정정)
  종목당 약 20초다. 1,813종목이면 한 종류에 **약 10시간**, 셋 다면 하루를
  넘는다. 밤에 걸어두고 자는 편이 낫다.

  원래 여기 "5,439회 호출, 70분" 이라고 적혀 있었는데 틀린 값이었다.
  SLEEP_SEC(0.4초)만 곱하고 응답 자체에 걸리는 시간을 안 셌다. 실제로는
  종목당 5.7년치(약 1,340행)를 받아오므로 요청 한 번이 20초 가까이
  걸린다. 호출 횟수가 아니라 받아오는 양이 시간을 정한다.
중간에 끊겨도 다시 실행하면 이미 받은 종목은 건너뛴다.
"""
import argparse
import csv
import sys
import time
from datetime import datetime

import yearly_csv
from common import BASE_DIR
from fetch_krx_history import CREDENTIAL_HELP, SLEEP_SEC, check_credentials

DATA_DIR = BASE_DIR / "data"
UNIVERSE_HISTORY_PATH = DATA_DIR / "krx_universe_history.csv"

# 연속 실패 몇 번에 멈출지. 한 종목도 못 받았으면 설정 문제이므로 일찍
# 멈춰야 하고(COLD), 이미 받은 게 있으면 일시적인 오류일 가능성이 크므로
# 넉넉히 버텨야 한다(WARM). 자세한 경위는 collect() 안의 주석에 있다.
ABORT_STREAK_COLD = 5
ABORT_STREAK_WARM = 30
RETRY_SLEEP_SEC = 2.0

# 종목 하나를 받는 데 실제로 걸린 시간(초). 2026-09-20 에 재무 1,150종목을
# 받으면서 잰 값이다 (elapsed/i 가 825종목 지점과 1,150종목 지점에서
# 똑같이 20.2초였다). 쉬는 시간이 아니라 5.7년치 응답을 받는 데 걸린다.
SEC_PER_CODE = 20.2

# 컬럼은 항상 맨 끝에 추가한다 (yearly_csv 문서 참고).
SPECS = {
    "flow": {
        "prefix": "krx_flow",
        "fields": ["date", "code", "inst", "corp", "indiv", "foreign"],
        # pykrx 반환 컬럼 -> 우리 컬럼
        "map": {"기관합계": "inst", "기타법인": "corp",
                "개인": "indiv", "외국인합계": "foreign"},
        "desc": "수급(외국인/기관/개인 순매수, 원)",
    },
    "fundamental": {
        "prefix": "krx_fund",
        "fields": ["date", "code", "bps", "per", "pbr", "eps", "div", "dps"],
        "map": {"BPS": "bps", "PER": "per", "PBR": "pbr",
                "EPS": "eps", "DIV": "div", "DPS": "dps"},
        "desc": "재무(PER/PBR/BPS/EPS/배당)",
    },
    "cap": {
        "prefix": "krx_cap",
        "fields": ["date", "code", "market_cap", "volume", "trade_value", "shares"],
        "map": {"시가총액": "market_cap", "거래량": "volume",
                "거래대금": "trade_value", "상장주식수": "shares"},
        "desc": "시가총액/상장주식수",
    },
}


def universe_codes() -> list[str]:
    if not UNIVERSE_HISTORY_PATH.exists():
        print(f"{UNIVERSE_HISTORY_PATH} 가 없습니다. 먼저 fetch_krx_history.py 를 실행하세요.")
        return []
    codes = set()
    with open(UNIVERSE_HISTORY_PATH, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("code"):
                codes.add(r["code"])
    return sorted(codes)


def _fetch(stock, what: str, code: str, start: str, end: str):
    if what == "flow":
        return stock.get_market_trading_value_by_date(start, end, code)
    if what == "fundamental":
        return stock.get_market_fundamental_by_date(start, end, code)
    if what == "cap":
        return stock.get_market_cap_by_date(start, end, code)
    raise ValueError(what)


def collect(stock, what: str, codes: list[str], start: str, end: str,
            verbose: bool = True) -> dict:
    spec = SPECS[what]
    prefix, fields, colmap = spec["prefix"], spec["fields"], spec["map"]

    have = yearly_csv.codes_in(DATA_DIR, prefix)
    todo = [c for c in codes if c not in have]
    if verbose:
        print(f"\n[{spec['desc']}] {len(codes)}종목 중 {len(todo)}종목을 받습니다 "
              f"(이미 받은 {len(codes) - len(todo)}종목은 건너뜀).")
    if not todo:
        return {"requested": 0, "ok": 0, "failed": 0, "written": 0}

    ok = failed = written = fail_streak = 0
    warned_cols = False
    started = time.time()
    with yearly_csv.StreamWriter(DATA_DIR, prefix, fields) as out:
        for i, code in enumerate(todo, 1):
            # (2026-09-19 수정) 원래는 연속 5번 실패하면 무조건 멈추고
            # "계정 문제" 안내를 찍었다. 그 판정이 두 가지를 섞고 있었다.
            #
            #   설정이 틀렸다      -> 첫 종목부터 전부 실패한다. 일찍 멈춰야
            #                        1,800번 헛돌지 않는다. (원래 의도)
            #   일시적인 오류다    -> 이미 여러 종목을 받은 뒤에 몇 개 연속
            #                        실패하는 경우. 여기서 멈추면 25분짜리
            #                        수집이 통째로 날아간다.
            #
            # 실제로 재무 수집이 29종목에서 멈춰 있었고, 계정은 멀쩡했다
            # (같은 계정으로 수급 1,707종목을 받았다). 그래서 한 번이라도
            # 성공했으면 기준을 크게 늘리고 안내 문구도 바꾼다.
            limit = ABORT_STREAK_COLD if ok == 0 else ABORT_STREAK_WARM
            if fail_streak >= limit:
                print(f"\n  [!] {fail_streak}종목 연속 실패로 중단합니다.")
                if ok == 0:
                    print(CREDENTIAL_HELP)
                else:
                    print(f"      {ok}종목은 이미 받았으므로 계정 문제는 아닙니다.")
                    print("      네트워크나 KRX 쪽 문제로 보입니다. 잠시 뒤에 다시 "
                          "실행하면 받은 종목은 건너뛰고 이어서 받습니다.")
                break
            try:
                df = _fetch(stock, what, code, start, end)
            except Exception as e:
                # 한 번은 다시 해본다. 일시적인 오류로 종목을 잃지 않게.
                time.sleep(RETRY_SLEEP_SEC)
                try:
                    df = _fetch(stock, what, code, start, end)
                except Exception:
                    failed += 1
                    fail_streak += 1
                    if failed <= 5:
                        print(f"  [!] {code} 실패: {e}")
                    time.sleep(SLEEP_SEC)
                    continue
            fail_streak = 0

            if df is not None and len(df):
                if not warned_cols:
                    missing = [k for k in colmap if k not in df.columns]
                    if missing:
                        print(f"  [!] 예상한 컬럼이 없습니다: {missing}")
                        print(f"      실제 컬럼: {list(df.columns)}")
                        print("      이대로 두면 그 값은 빈칸으로 저장됩니다.")
                    warned_cols = True
                rows = []
                for idx, r in df.iterrows():
                    d = idx.strftime("%Y%m%d") if hasattr(idx, "strftime") else str(idx)
                    row = {"date": d, "code": code}
                    for src, dst in colmap.items():
                        try:
                            row[dst] = r[src]
                        except (KeyError, TypeError):
                            row[dst] = ""
                    rows.append(row)
                written += out.write_rows(rows)
                ok += 1

            if i % 25 == 0:
                out.flush()
                if verbose:
                    el = time.time() - started
                    eta = el / i * (len(todo) - i) / 60
                    print(f"  ...{i}/{len(todo)}종목 (성공 {ok}, 실패 {failed}, "
                          f"{written:,}행, 남은 시간 약 {eta:.0f}분)")
            time.sleep(SLEEP_SEC)

    if verbose:
        print(f"[{spec['desc']}] 완료: {ok}종목, {written:,}행, 실패 {failed}종목")
    return {"requested": len(todo), "ok": ok, "failed": failed, "written": written}


def main():
    ap = argparse.ArgumentParser(description="KRX 수급/재무/시가총액 수집")
    ap.add_argument("--start", default="20210101")
    ap.add_argument("--end", default=None)
    ap.add_argument("--what", choices=list(SPECS) + ["all"], default="all",
                    help="받을 종류 (기본: 전부)")
    ap.add_argument("--limit", type=int, default=None,
                    help="이 개수의 종목만. 처음엔 --limit 3 으로 형식 확인")
    args = ap.parse_args()
    end = args.end or datetime.now().strftime("%Y%m%d")

    try:
        from pykrx import stock
    except ImportError:
        print("pykrx 가 없습니다:  pip install pykrx")
        return 1
    if not check_credentials():
        return 1

    codes = universe_codes()
    if not codes:
        return 1

    kinds = list(SPECS) if args.what == "all" else [args.what]

    if args.limit:
        # (2026-09-19 수정) 원래는 유니버스 앞에서 그냥 잘랐다. 그런데
        # 앞쪽 종목은 이미 받아둔 것일 가능성이 높아서, 형식 확인을
        # 돌리면 "0종목 받습니다 (이미 받은 3종목은 건너뜀)" 으로 끝났다.
        # 확인하려던 것(응답 형식이 맞는가)을 하나도 확인하지 못한다.
        # 그래서 아직 안 받은 종목 중에서 고른다.
        have = set()
        for what in kinds:
            have |= yearly_csv.codes_in(DATA_DIR, SPECS[what]["prefix"])
        fresh = [c for c in codes if c not in have]
        if not fresh:
            print(f"--limit {args.limit} 인데 안 받은 종목이 없습니다. "
                  f"이미 다 모였다는 뜻이므로 확인할 것이 없습니다.")
            return 0
        codes = fresh[:args.limit]
        print(f"--limit {args.limit} 이라 아직 안 받은 종목 중 "
              f"{len(codes)}개만 받습니다 (형식 확인용): {', '.join(codes)}")
    print(f"=== KRX 추가 수집 {args.start}~{end}, {len(codes)}종목 x {len(kinds)}종류 ===")
    if not args.limit:
        # (2026-09-20 정정) SLEEP_SEC 만 곱하면 실제의 1/50 이 나온다.
        # 시간을 정하는 건 쉬는 시간이 아니라 받아오는 양이다.
        n_call = len(codes) * len(kinds)
        print(f"    예상 호출 {n_call:,}회, "
              f"약 {n_call * SEC_PER_CODE / 3600:.1f}시간 "
              f"(종목당 {SEC_PER_CODE:.0f}초, 2026-09-20 실측)\n")

    total_ok = total_req = 0
    for what in kinds:
        r = collect(stock, what, codes, args.start, end)
        total_ok += r["ok"]
        total_req += r["requested"]

    # (2026-09-19 수정) 원래는 total_ok == 0 이면 무조건 실패로 봤다.
    # 그런데 "받을 게 없어서 0" 과 "전부 실패해서 0" 은 다르다. 앞의
    # 경우까지 실패로 돌려주면 .bat 가 거기서 멈춘다 - 실제로 그렇게
    # 멈췄다. 요청한 종목이 있었는데 하나도 못 받았을 때만 실패다.
    if total_req == 0:
        print("\n받을 것이 없습니다 (요청한 종목을 이미 다 받아뒀습니다).")
        return 0
    if total_ok == 0:
        print("\n[!] 요청한 종목을 한 개도 못 받았습니다. 위 에러를 확인하세요.")
        return 1
    if args.limit:
        print("\n형식 확인 완료. 이상 없으면 --limit 없이 다시 실행하세요.")
    else:
        print("\n완료. data/krx_*.csv 를 커밋하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
