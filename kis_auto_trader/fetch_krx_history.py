"""생존편향을 걷어내기 위한 KRX 과거 데이터 수집 (PC에서 한 번 실행).

(2026-09-15 신설) 왜 필요한가:

지금 유니버스(universe.json)는 **2026년 9월에** 거래대금 상위인 종목으로 만들었다.
그 목록으로 2021년부터 백테스트를 돌리면, 5년을 살아남아 커진 종목만 보게 된다.
그 사이 상장폐지됐거나 거래가 죽은 종목은 애초에 목록에 없다. 투자대회 순위표가
이긴 사람만 보여주는 것과 똑같은 문제다(생존편향).

실제로 측정해보니 이 편향이 성과를 대략 절반쯤 부풀리고 있었다:
  원래 측정값                     +6.46%p (40일 보유 초과수익)
  5년 대박 20종목을 빼면          +3.96%p
  생존 필터가 거의 없는 최근 구간   +3.17%p

제대로 고치려면 "그 시점에 실제로 고를 수 있었던 종목 전부"가 필요하다.
KIS API로는 상장폐지 종목을 조회할 수 없어서 KRX 데이터를 쓴다.

무엇을 하는가:

  1) 월말마다 그날의 전 종목 거래대금 순위를 받아서 상위 N개를 기록한다.
     -> 2021년 3월의 상위 200종목은 '그때 기준'이다. 지금 관점이 안 들어간다.
  2) 5년간 한 번이라도 상위 N에 든 종목을 전부 모은다 (나중에 상장폐지된 것 포함).
  3) 그 종목들의 일봉을 전부 받는다.

그러면 백테스트가 "2021년 3월에 내가 실제로 볼 수 있었던 종목들" 중에서만
고르게 되고, 그중 나중에 망한 종목도 표본에 들어온다.

사전 준비 - KRX 계정이 필요하다 (2026-09-15 확인):

  pykrx 1.2.8 부터 KRX 데이터 서비스 로그인이 있어야 조회가 된다. 계정 없이
  돌리면 KRX 가 JSON 대신 로그인 페이지를 돌려주고, pykrx 가 그걸 파싱하다
  실패해서 모든 조회가 빈 결과로 끝난다 (에러 메시지는 컬럼이 없다는 엉뚱한
  내용이라 원인을 찾기 어렵다).

    1) http://data.krx.co.kr 에서 회원가입 (무료)
    2) 환경변수 설정
         PowerShell:  $env:KRX_ID="아이디";  $env:KRX_PW="비밀번호"
         영구 설정:   setx KRX_ID "아이디"  /  setx KRX_PW "비밀번호"
                      (setx 는 새 창부터 적용됨)

실행 (PC에서, 인터넷 되는 환경):

    pip install pykrx
    python fetch_krx_history.py --universe-only   # 규모부터 확인
    python fetch_krx_history.py                   # 일봉까지 수집

  - 중간에 끊겨도 다시 실행하면 이어서 받는다 (이미 받은 종목은 건너뜀).
  - 시간이 꽤 걸린다. 종목 수에 따라 30분~2시간.
  - 다 받으면 data/krx_*.csv 가 생기고, 그걸 커밋하면 된다.
"""
import argparse
import csv
import sys
import time
from datetime import date, datetime, timedelta

import yearly_csv
from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
UNIVERSE_HISTORY_PATH = DATA_DIR / "krx_universe_history.csv"
PANEL_PREFIX = "krx_panel"

UNIVERSE_FIELDS = ["date", "code", "name", "trade_value", "rank"]
# panel.py 와 같은 스키마로 맞춘다 - 백테스트가 그대로 읽을 수 있게.
PANEL_FIELDS = ["date", "code", "name", "open", "high", "low", "close", "volume"]

# KRX 서버에 부담을 주지 않도록 호출 사이에 쉬는 시간(초).
# 너무 빨리 부르면 차단될 수 있어서 넉넉히 잡는다.
SLEEP_SEC = 0.4


def _month_ends(start: str, end: str) -> list[str]:
    """start~end 사이 각 달의 마지막 날(달력 기준) 목록.

    그 날이 휴장일이면 KRX가 빈 결과를 주는데, 부르는 쪽이 그 달을 건너뛴다.
    월말 하루를 놓쳐도 유니버스 구성은 거의 안 바뀌므로 그대로 둔다.
    """
    out = []
    y, m = int(start[:4]), int(start[4:6])
    ey, em = int(end[:4]), int(end[4:6])
    while (y, m) <= (ey, em):
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        d = date(ny, nm, 1) - timedelta(days=1)
        ds = d.strftime("%Y%m%d")
        if start <= ds <= end:
            out.append(ds)
        y, m = ny, nm
    return out


def _load_universe_history() -> dict:
    """{(date, code): row}"""
    if not UNIVERSE_HISTORY_PATH.exists():
        return {}
    out = {}
    with open(UNIVERSE_HISTORY_PATH, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("date") and r.get("code"):
                out[(r["date"], r["code"])] = r
    return out


def _save_universe_history(rows: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    tmp = UNIVERSE_HISTORY_PATH.with_suffix(".csv.tmp")
    ordered = sorted(rows.values(), key=lambda r: (r["date"], int(r["rank"])))
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=UNIVERSE_FIELDS)
        w.writeheader()
        for r in ordered:
            w.writerow({k: r.get(k, "") for k in UNIVERSE_FIELDS})
    tmp.replace(UNIVERSE_HISTORY_PATH)


CREDENTIAL_HELP = """
KRX 조회가 되지 않습니다. 거의 대부분 로그인 문제입니다.

pykrx 1.2.8 부터 KRX 데이터 서비스 계정이 있어야 조회가 됩니다. 계정 없이
돌리면 KRX 가 JSON 대신 로그인 페이지를 돌려주고, 그걸 파싱하다 실패해서
"'시가','고가','저가','종가' 컬럼이 없다" 같은 엉뚱한 에러가 납니다.

  1) http://data.krx.co.kr 에서 회원가입 (무료)
  2) 환경변수 설정 후 다시 실행
       PowerShell:  $env:KRX_ID="아이디"; $env:KRX_PW="비밀번호"
       영구 설정:   setx KRX_ID "아이디"   (새 창부터 적용)

맨 처음 줄에 "KRX 로그인 완료." 가 떠야 정상입니다.
"""


def check_credentials() -> bool:
    """KRX 계정이 설정돼 있는지 먼저 확인한다.

    (2026-09-15 추가) 이게 없으면 68번의 조회가 전부 같은 이유로 실패하는데,
    진짜 원인(로그인 실패)은 맨 첫 줄에 한 번만 찍히고 그 뒤 68줄의 엉뚱한
    에러에 묻힌다. 실제로 그렇게 한 번 헛돌렸다. 시작 전에 막는다.
    """
    import os
    if os.getenv("KRX_ID") and os.getenv("KRX_PW"):
        return True
    print(CREDENTIAL_HELP)
    return False


def collect_universe_history(stock, start: str, end: str, top_n: int,
                             verbose: bool = True) -> dict:
    """월말마다 거래대금 상위 top_n 종목을 기록한다 (그 시점 기준)."""
    have = _load_universe_history()
    done_dates = {d for (d, _) in have}
    targets = [d for d in _month_ends(start, end) if d not in done_dates]

    if verbose:
        print(f"[유니버스] 기준일 {len(_month_ends(start, end))}개 중 "
              f"{len(targets)}개를 새로 받습니다.")

    # 연속 실패가 이만큼 쌓이면 멈춘다 - 설정 문제면 끝까지 돌려봐야 의미가 없다.
    fail_streak = 0
    for i, date in enumerate(targets, 1):
        if fail_streak >= 3:
            print(f"\n  [!] 조회가 {fail_streak}번 연속 실패해서 중단합니다.")
            print(CREDENTIAL_HELP)
            break
        try:
            df = stock.get_market_ohlcv_by_ticker(date, market="ALL")
        except Exception as e:
            fail_streak += 1
            print(f"  [!] {date} 조회 실패: {e}")
            time.sleep(SLEEP_SEC)
            continue
        if df is None or len(df) == 0:
            # 휴장일이면 빈 결과가 온다 - 그 달은 건너뛴다.
            # 다만 계속 비어 있으면 휴장이 아니라 설정 문제다.
            fail_streak += 1
            if verbose:
                print(f"  {date}: 데이터 없음(휴장일이거나 로그인 문제)")
            time.sleep(SLEEP_SEC)
            continue
        fail_streak = 0

        col = "거래대금" if "거래대금" in df.columns else None
        if col is None:
            print(f"  [!] {date}: '거래대금' 컬럼이 없습니다. 컬럼={list(df.columns)}")
            break

        top = df.sort_values(col, ascending=False).head(top_n)
        for rank, (code, row) in enumerate(top.iterrows(), 1):
            have[(date, str(code))] = {
                "date": date, "code": str(code), "name": "",
                "trade_value": int(row[col]), "rank": rank,
            }
        if verbose and (i % 6 == 0 or i == len(targets)):
            print(f"  ...{i}/{len(targets)} 기준일 처리 (누적 {len(have)}행)")
        _save_universe_history(have)   # 중간에 끊겨도 이어받을 수 있게 매번 저장
        time.sleep(SLEEP_SEC)

    return have


def last_panel_date() -> str | None:
    """krx_panel 에 저장된 가장 늦은 날짜 (YYYYMMDD). 비어 있으면 None.

    (2026-09-19 추가) 행 전체를 dict 으로 올리지 않고 date 열만 훑는다 -
    coverage() 는 226만 행을 메모리에 올리므로 이 용도로는 못 쓴다.
    """
    best = None
    for path in yearly_csv.paths(DATA_DIR, PANEL_PREFIX):
        with open(path, encoding="utf-8-sig", newline="") as f:
            r = csv.reader(f)
            header = next(r, None)
            if not header or "date" not in header:
                continue
            di = header.index("date")
            for row in r:
                if len(row) > di and row[di] and (best is None or row[di] > best):
                    best = row[di]
    return best


def collect_panel(stock, codes: list[str], start: str, end: str,
                  verbose: bool = True, since: str | None = None) -> dict:
    """종목들의 일봉을 받아 krx_panel_YYYY.csv 에 저장한다.

    (2026-09-15 수정) 원래는 5만 행마다 yearly_csv.append 를 불렀는데, 그건
    매번 저장된 전체를 읽어서 합치고 다시 쓰는 방식이라 226만 행 규모에서는
    O(n^2)이 되어 안 끝난다. 실제로 1,813종목(약 226만 행, 125MB)을 받아야
    하는 상황이 되어서 StreamWriter 로 바꿨다 - 읽지 않고 이어 쓰기만 한다.

    이미 받은 종목은 건너뛰므로 중간에 끊겨도 다시 실행하면 이어진다.

    (2026-09-19 추가) since 를 주면 **이미 받은 종목도** since 부터 다시
    받는다. 왜 필요한가: 이 함수는 원래 한 번 받고 끝나는 backfill 용이라
    '받은 종목은 건너뜀' 만 있었다. 그래서 며칠 뒤에 다시 실행해도 새로
    생긴 거래일이 절대 들어오지 않는다 - krx_panel 이 20260915 에서 멈춰
    있는데 다시 돌려도 "1,744종목 건너뜀" 만 나오는 상태가 된다. 전략과
    모든 분석이 이 패널을 읽으므로 전진 기록이 아예 안 쌓인다.

    StreamWriter 는 중복을 지우지 않으므로 같은 (날짜,종목)을 두 번 쓰면
    그 종목의 그날 수익률이 두 번 세어진다. since 를 부르는 쪽 말만 믿으면
    안 된다 - 실제로 테스트에서 지난번 since 를 그대로 다시 넘겼더니
    중복이 생겼다. 그래서 여기서 저장된 마지막 날짜를 직접 읽어서
    since 를 '마지막 날 다음날' 이상으로 끌어올린다. 그러면 새로 쓰는 행은
    모두 저장된 것보다 뒤라서 겹칠 수가 없다.
    """
    have = yearly_csv.codes_in(DATA_DIR, PANEL_PREFIX)
    fresh = [c for c in codes if c not in have]

    if since is None:
        todo = [(c, start) for c in fresh]
        if verbose:
            print(f"[일봉] 전체 {len(codes)}종목 중 {len(todo)}종목을 새로 받습니다 "
                  f"(이미 받은 {len(codes) - len(todo)}종목은 건너뜀).")
    else:
        # 중복 방지는 부르는 쪽에 맡기지 않는다 (위 설명 참고).
        last = last_panel_date()
        if last is not None:
            floor = (datetime.strptime(last, "%Y%m%d")
                     + timedelta(days=1)).strftime("%Y%m%d")
            if since < floor:
                if verbose:
                    print(f"[일봉] since {since} 는 이미 저장된 {last} 이전이라 "
                          f"{floor} 로 올립니다 (같은 날을 두 번 쓰면 중복이 됩니다).")
                since = floor
        # 이미 있는 종목은 since 부터(빠진 날만), 처음 보는 종목은 start 부터(전체).
        todo = [(c, since if c in have else start) for c in codes]
        if verbose:
            print(f"[일봉] {len(codes)}종목: 기존 {len(codes) - len(fresh)}종목은 "
                  f"{since} 부터 빠진 날만, 새 {len(fresh)}종목은 {start} 부터 전체를 받습니다.")

    ok, failed, written, fail_streak = 0, 0, 0, 0
    started = time.time()
    with yearly_csv.StreamWriter(DATA_DIR, PANEL_PREFIX, PANEL_FIELDS) as out:
        for i, (code, code_start) in enumerate(todo, 1):
            # (2026-09-15) 응답 형식이 예상과 다르면 1,813종목을 12분 내내
            # 헛돌게 된다. 유니버스 수집에 넣은 것과 같은 안전장치를 여기에도 둔다.
            if fail_streak >= 5:
                print(f"\n  [!] {fail_streak}종목 연속 실패로 중단합니다.")
                print(CREDENTIAL_HELP)
                break
            try:
                df = stock.get_market_ohlcv_by_date(code_start, end, code)
            except Exception as e:
                failed += 1
                fail_streak += 1
                if failed <= 5:
                    print(f"  [!] {code} 조회 실패: {e}")
                time.sleep(SLEEP_SEC)
                continue
            fail_streak = 0

            if df is not None and len(df):
                try:
                    name = stock.get_market_ticker_name(code)
                except Exception:
                    name = ""   # 상장폐지 종목은 이름 조회가 안 될 수 있다 - 비워둔다
                rows = []
                for idx, r in df.iterrows():
                    d = idx.strftime("%Y%m%d") if hasattr(idx, "strftime") else str(idx)
                    try:
                        close = float(r["종가"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if close <= 0:
                        continue   # 거래정지일 등 - 0이면 수익률 계산이 깨진다
                    rows.append({
                        "date": d, "code": code, "name": name,
                        "open": float(r.get("시가", 0)) or "",
                        "high": float(r.get("고가", 0)) or "",
                        "low": float(r.get("저가", 0)) or "",
                        "close": close,
                        "volume": int(r.get("거래량", 0) or 0),
                    })
                written += out.write_rows(rows)
                ok += 1

            if i % 25 == 0:
                out.flush()   # 중간에 끊겨도 여기까지는 파일에 남게
                if verbose:
                    el = time.time() - started
                    eta = el / i * (len(todo) - i) / 60
                    print(f"  ...{i}/{len(todo)}종목 (성공 {ok}, 실패 {failed}, "
                          f"{written:,}행, 남은 시간 약 {eta:.0f}분)")
            time.sleep(SLEEP_SEC)

    result = {"requested": len(todo), "ok": ok, "failed": failed, "written": written}
    if verbose:
        print(f"[일봉] 완료: {ok}종목 성공, {failed}종목 실패, {written:,}행 저장")
    return result


def main():
    ap = argparse.ArgumentParser(description="KRX 과거 데이터 수집 (생존편향 제거용)")
    ap.add_argument("--start", default="20210101", help="시작일 YYYYMMDD")
    ap.add_argument("--end", default=None, help="종료일 YYYYMMDD (기본: 오늘)")
    ap.add_argument("--top", type=int, default=200,
                    help="매월 거래대금 상위 몇 종목을 유니버스에 넣을지 (기본 %(default)s)")
    ap.add_argument("--universe-only", action="store_true",
                    help="유니버스 목록만 받고 일봉은 받지 않는다 (규모 확인용)")
    ap.add_argument("--limit", type=int, default=None,
                    help="일봉을 이 개수의 종목만 받는다. 처음 돌릴 때 "
                         "--limit 5 로 형식이 맞는지 먼저 확인하는 용도")
    ap.add_argument("--update", action="store_true",
                    help="이미 받은 종목도 '저장된 마지막 날 다음날'부터 다시 받는다. "
                         "매일/매주 전진 기록을 이어 쌓는 용도 (옵션 없이 다시 "
                         "돌리면 받은 종목을 전부 건너뛰어서 새 거래일이 안 들어온다)")
    args = ap.parse_args()
    end = args.end or datetime.now().strftime("%Y%m%d")

    since = None
    if args.update:
        last = last_panel_date()
        if last is None:
            print("[갱신] krx_panel 이 비어 있어서 --update 가 의미 없습니다. "
                  "옵션 없이 처음부터 받으세요.")
            return 1
        since = (datetime.strptime(last, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
        print(f"[갱신] 저장된 마지막 날 {last} -> {since} 부터 {end} 까지 받습니다.")
        if since > end:
            print("[갱신] 이미 최신입니다. 받을 게 없습니다.")
            return 0

    try:
        from pykrx import stock
    except ImportError:
        print("pykrx 가 없습니다. 먼저 설치하세요:  pip install pykrx")
        return 1

    if not check_credentials():
        return 1

    print(f"=== KRX 과거 데이터 수집 {args.start} ~ {end}, 매월 상위 {args.top}종목 ===")
    print("   (이 목록은 '그 시점 기준'이라 나중에 상장폐지된 종목도 포함됩니다)\n")

    hist = collect_universe_history(stock, args.start, end, args.top)
    codes = sorted({c for (_, c) in hist})
    dates = sorted({d for (d, _) in hist})
    print(f"\n[유니버스] 기준일 {len(dates)}개, 한 번이라도 상위 {args.top}에 든 종목 {len(codes)}개")

    if dates:
        first_set = {c for (d, c) in hist if d == dates[0]}
        last_set = {c for (d, c) in hist if d == dates[-1]}
        gone = first_set - last_set
        print(f"[유니버스] {dates[0]} 상위권 중 {dates[-1]} 상위권에 없는 종목: "
              f"{len(gone)}/{len(first_set)}개")
        print("           (이 종목들이 바로 지금 유니버스에서 빠져 있던 것들입니다)")

    if args.universe_only:
        print("\n--universe-only 라 일봉은 받지 않았습니다. "
              "규모를 보고 괜찮으면 옵션 없이 다시 실행하세요.")
        return 0

    if args.limit:
        codes = codes[:args.limit]
        print(f"\n[일봉] --limit {args.limit} 이라 {len(codes)}종목만 받습니다 (형식 확인용).")
    else:
        est_min = len(codes) * SLEEP_SEC / 60
        print(f"\n[일봉] {len(codes)}종목의 일봉을 받습니다 (최소 {est_min:.0f}분 예상)")

    r = collect_panel(stock, codes, args.start, end, since=since)
    if r["ok"] == 0:
        print("\n[!] 한 종목도 못 받았습니다. 위 에러를 확인하세요.")
        return 1
    if args.limit:
        print(f"\n형식 확인 완료 ({r['ok']}종목 {r['written']:,}행). "
              f"이상 없으면 --limit 없이 다시 실행하세요.")
    else:
        print("\n완료. data/krx_*.csv 를 커밋하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
