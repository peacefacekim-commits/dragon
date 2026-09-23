"""KRX 업종분류를 받는다. 종목이 어느 업종인지, 그 시점 기준으로.

(2026-09-22 신설) 사용자: "업종 데이터도 받아주고 좀 확실히 정하자"

===========================================================================
0 - 왜 날짜별로 받나 (이게 이 파일의 핵심 설계)
===========================================================================
업종은 고정이 아니다. 회사가 사업을 바꾸면 분류가 바뀌고, 상장폐지된
종목은 지금 조회하면 아예 안 나온다.

그래서 **오늘 받은 업종을 5.7년 과거에 그대로 갖다 붙이면 안 된다.**
그건 생존편향과 같은 종류의 실수다 - 지금 남아 있는 회사의, 지금의
분류만 보게 된다.

pykrx 의 get_market_sector_classifications(date, market) 는 **날짜를
받는다.** 그래서 과거 시점의 분류를 그 시점 기준으로 받을 수 있다.
이 파일은 그걸 쓴다. 교체일마다(또는 분기마다) 한 번씩 받아두면
"그때 그 종목은 그때 무슨 업종이었나" 를 정확히 쓸 수 있다.

===========================================================================
1 - 표준 업종만 받는다. 테마는 안 받는다
===========================================================================
받는 것    KRX 표준 업종분류 (전기전자, 화학, 금융업, 서비스업 ...)
안 받는 것  AI / 2차전지 / 바이오 같은 **테마**

테마는 KRX 표준 분류에 없다. 증권사마다 다르고 시기마다 바뀐다.
표준 업종은 사실이고 테마는 해석이라, 섞어두면 나중에 무엇이 데이터고
무엇이 내 판단인지 가릴 수 없게 된다.

테마가 필요하면 이 파일이 만든 업종 위에 **따로** 얹는다. 그때도 파일을
나눠서, 어느 쪽이 사실인지 항상 보이게 한다.

===========================================================================
2 - 스키마
===========================================================================
  data/krx_sector_YYYY.csv
  date, code, name, market, sector

  date    조회 기준일 (YYYYMMDD). 그 시점의 분류라는 뜻이다.
  market  KOSPI / KOSDAQ
  sector  KRX 업종명 그대로. 우리가 고치지 않는다.

(date, code) 가 열쇠다. 같은 날 같은 종목을 두 번 받아도 안 늘어난다.
컬럼을 더할 일이 생기면 **맨 끝에** 붙인다 (yearly_csv 규약).

===========================================================================
3 - 얼마나 자주 받나
===========================================================================
업종은 자주 안 바뀌므로 매일 받을 필요가 없다. 기본은 **분기마다 한 번**
(3, 6, 9, 12월 중순). 5.7년이면 24번쯤이고 한 번에 다 받아도 몇 분이다.

  python fetch_krx_sector.py --backfill      # 2021~올해, 분기마다
  python fetch_krx_sector.py                 # 오늘 것만
  python fetch_krx_sector.py --date 20240617 # 특정 날짜

매일 실행.bat 에는 **안 넣는다.** 분기마다 한 번이면 되는 것을 매일
돌리면 KRX 에 부담만 준다. 대신 --backfill 을 가끔 돌리면 빠진 분기가
자동으로 채워진다 (이미 있는 날짜는 건너뛴다).

===========================================================================
4 - 이 파일이 답할 수 있는 것 / 없는 것
===========================================================================
답할 수 있다
  - 저변동 10종목이 어느 업종에 쏠려 있나 (그 시점 기준으로)
  - 업종 쏠림이 시기마다 달라졌나
  - 특정 업종을 빼면/넣으면 결과가 달라지나 (사전 등록해서 재야 한다)

답할 수 없다
  - "AI 관련주" 같은 테마. 표준 분류에 없다.
  - 업종이 수익을 예측하나. 그건 재야 아는 것이고, 이 파일은 재료만
    만든다. 재는 것은 사전 등록한 analyze_* 가 한다.

===========================================================================
5 - KRX 로그인이 필요하다
===========================================================================
KRX_ID / KRX_PW 환경 변수가 있어야 한다 (fetch_krx_history.py 와 같다).
없으면 안내만 하고 그냥 끝낸다 - 다른 수집을 막지 않는다.

실행:
  python fetch_krx_sector.py --backfill
"""
import argparse
import csv
import datetime as dt
import pathlib
import sys
import time

_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

DATA_DIR = _ROOT / "data"
PREFIX = "krx_sector"
FIELDS = ["date", "code", "name", "market", "sector"]
MARKETS = ("KOSPI", "KOSDAQ")
# 분기마다 한 번. 업종은 자주 안 바뀌므로 매일 받을 이유가 없다.
QUARTER_MONTHS = (3, 6, 9, 12)
QUARTER_DAY = 15
FIRST_YEAR = 2021
SLEEP_SEC = 0.5          # KRX 에 부담 주지 않으려고 호출 사이에 쉰다


def quarter_dates(first_year=FIRST_YEAR, today=None):
    """받을 날짜들. 분기 중순, 오늘을 넘지 않는 것만."""
    today = today or dt.date.today()
    out = []
    for y in range(first_year, today.year + 1):
        for m in QUARTER_MONTHS:
            d = dt.date(y, m, QUARTER_DAY)
            if d <= today:
                out.append(d.strftime("%Y%m%d"))
    return out


def existing_dates():
    """이미 받은 날짜. 다시 안 받으려고."""
    got = set()
    for path in sorted(DATA_DIR.glob(f"{PREFIX}_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("date"):
                    got.add(r["date"])
    return got


def to_rows(df, date, market):
    """pykrx 결과 -> [[date, code, name, market, sector]].

    컬럼 이름이 버전마다 다를 수 있어서 있는 것만 쓴다. 없으면 빈칸으로
    두고, 0 이나 '기타' 로 메우지 않는다 - 메우면 가짜 분류가 생긴다.
    """
    rows = []
    for code, rec in df.iterrows():
        d = {str(k): v for k, v in rec.items()}
        name = d.get("종목명") or d.get("name") or ""
        sector = d.get("업종명") or d.get("업종") or d.get("sector") or ""
        rows.append([date, str(code), str(name), market, str(sector)])
    return rows


def append_rows(rows):
    """해별 파일에 덧붙인다. (date, code) 가 이미 있으면 건너뛴다."""
    if not rows:
        return 0
    import yearly_csv
    by_year = {}
    for r in rows:
        by_year.setdefault(r[0][:4], []).append(r)
    total = 0
    for year, rs in sorted(by_year.items()):
        path = DATA_DIR / f"{PREFIX}_{year}.csv"
        have = set()
        if path.exists():
            with open(path, encoding="utf-8-sig", newline="") as fh:
                for r in csv.DictReader(fh):
                    have.add((r.get("date"), r.get("code")))
        new = [r for r in rs if (r[0], r[1]) not in have]
        if not new:
            continue
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        first = not path.exists()
        with open(path, "a", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            if first:
                w.writerow(FIELDS)
            w.writerows(new)
        total += len(new)
    return total


def fetch_one(stock, date):
    """한 날짜의 모든 시장. (행 목록, 실패한 시장 수)."""
    rows, failed = [], 0
    for market in MARKETS:
        try:
            df = stock.get_market_sector_classifications(date, market)
        except Exception as e:
            print(f"  {date} {market} 실패: {type(e).__name__}: {str(e)[:80]}")
            failed += 1
            continue
        if df is None or len(df) == 0:
            continue
        rows.extend(to_rows(df, date, market))
        time.sleep(SLEEP_SEC)
    return rows, failed


def main(argv=None):
    ap = argparse.ArgumentParser(description="KRX 업종분류 수집")
    ap.add_argument("--backfill", action="store_true",
                    help=f"{FIRST_YEAR}년부터 분기마다 (빠진 것만)")
    ap.add_argument("--date", help="특정 날짜 (YYYYMMDD)")
    ap.add_argument("--first-year", type=int, default=FIRST_YEAR)
    args = ap.parse_args(argv)

    try:
        from pykrx import stock
    except Exception as e:
        print(f"[!] pykrx 를 못 불러옵니다: {e}")
        return 1

    if args.date:
        dates = [args.date]
    elif args.backfill:
        dates = quarter_dates(args.first_year)
    else:
        dates = [dt.date.today().strftime("%Y%m%d")]

    have = existing_dates()
    todo = [d for d in dates if d not in have]
    print(f"=== KRX 업종분류 수집 ===")
    print(f"대상 {len(dates)}개 날짜 중 이미 받은 것 {len(dates) - len(todo)}개, "
          f"받을 것 {len(todo)}개")
    if not todo:
        print("받을 것이 없습니다.")
        return 0

    total, n_fail = 0, 0
    for i, date in enumerate(todo, 1):
        rows, failed = fetch_one(stock, date)
        n_fail += failed
        wrote = append_rows(rows)
        total += wrote
        print(f"  [{i}/{len(todo)}] {date}: {wrote:,}행 저장 "
              f"(받은 {len(rows):,}행)", flush=True)

    print(f"\n{total:,}행 저장. 실패한 호출 {n_fail}회.")
    if total == 0:
        print("[!] 저장된 행이 0입니다.")
        print("    KRX_ID / KRX_PW 환경 변수를 확인하세요.")
        return 1
    # 무엇이 들어왔는지 보여준다 (10분봉 사고 때 이게 없어서 몰랐다)
    secs = {}
    for path in sorted(DATA_DIR.glob(f"{PREFIX}_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                secs.setdefault(r.get("sector", ""), set()).add(r.get("code"))
    print(f"\n지금까지 모인 업종 {len(secs)}개 (종목 수 상위 10개)")
    for s, cs in sorted(secs.items(), key=lambda kv: -len(kv[1]))[:10]:
        print(f"  {s or '(빈칸)':<20}{len(cs):>5}종목")
    return 0


if __name__ == "__main__":
    sys.exit(main())
