"""미국 지수 선물의 '한국 장중' 움직임을 받는다 - 시차 공백을 메우는 유일한 경로.

(2026-09-16 신설) 왜 필요한가:

오늘 열두 번 시도해서 열두 번 같은 벽에 부딪혔다. 정리하면 이렇다.

  나쁜 날은 예측된다      시험 구간 상관 0.32, 나쁜 날 71% 적중
  그런데 먹을 수 없다     예측되는 부분이 전부 시가 갭에 반영됨
                         종가대비 +0.317% / 시가대비 -0.052%

원인은 시차다. 정보(미국장)가 생기는 시점과 살 수 있는 시점이 어긋나 있다.

  한국 종가 15:30  <- 여기서 사야 갭을 먹는다
  미국장 23:30~06:00  <- 정보가 여기서 생긴다
  한국 시가 09:00  <- 알 수 있지만 이미 반영됨

그런데 **미국 지수 선물은 한국 장중에도 거래된다.** 정규장은 안 겹치지만
선물은 거의 24시간 돌아간다. 그래서 한국 15:00 시점의 선물 움직임을 보면,
한국 장이 닫히기 전에 "오늘 밤 미국이 어떨지"를 일부 알 수 있다.

이 파일은 그 데이터를 받는다. 검증할 가설:
  한국 장중(09:00~15:00) 선물 변화 -> 다음날 한국 시가 갭

제약 (미리 밝혀둠):
  - yfinance 의 1시간봉은 약 2년치까지만 받을 수 있다 (일봉은 전체).
    거래일 약 500일이라, 오늘 1,376일로 검증한 것의 3분의 1이다.
    방향은 볼 수 있지만 결론을 내기에는 약하다.
  - 이 아이디어는 국내에서 널리 쓰인다("미국 선물 보고 판단한다").
    널리 쓰인다는 건 이미 가격에 반영돼 있을 수 있다는 뜻도 된다.

시간대 처리 (여기가 틀리면 전부 무의미해진다):
  yfinance 는 미국 티커의 1시간봉 인덱스를 미국 시간대로 준다. 이걸 한국
  시간으로 바꿔서 날짜를 가른다. 그리고 '한국 종가 전에 알 수 있는 값'만
  쓰려면, 한국시간 15:00 까지 '마감된' 봉만 봐야 한다 - 15:00~16:00 봉은
  16시에 끝나므로 한국 종가(15:30) 시점에는 아직 확정되지 않았다.

실행:
    pip install yfinance
    python fetch_us_futures.py
"""
import argparse
import sys
from datetime import datetime

import yearly_csv
from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
PREFIX = "us_futures"
FIELDS = ["date", "ticker", "kr_open", "kr_mid", "kr_close", "kr_session_chg", "bars"]

TICKERS = {
    "ES=F": "S&P500 선물",
    "NQ=F": "나스닥 선물",
}

# 한국 장중에서 쓸 시각 (한국시간). 종가(15:30) 전에 확정된 봉만 쓴다.
KR_OPEN_HOUR = 9     # 09:00~10:00 봉 -> 10시에 마감
KR_MID_HOUR = 12
KR_CUTOFF_HOUR = 14  # 14:00~15:00 봉 -> 15시에 마감. 이게 마지막 안전한 값.


def _to_kst(df):
    """인덱스를 한국시간으로 바꾼다. 시간대 정보가 없으면 UTC 로 가정한다."""
    idx = df.index
    if getattr(idx, "tz", None) is None:
        df = df.tz_localize("UTC")
    return df.tz_convert("Asia/Seoul")


def collect(start: str, end: str, verbose: bool = True) -> dict:
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf
    from fetch_us_market import _flatten, _num

    have = {t for (_d, t) in yearly_csv.load_rows(
        DATA_DIR, PREFIX, key_fields=("date", "ticker"))}

    rows, ok, failed = [], 0, 0
    for ticker, name in TICKERS.items():
        if ticker in have:
            if verbose:
                print(f"  {name}({ticker}): 이미 있음, 건너뜀")
            ok += 1
            continue
        try:
            df = yf.download(ticker, start=_dash(start), end=_dash(end),
                             interval="1h", progress=False, auto_adjust=True)
        except Exception as e:
            failed += 1
            print(f"  [!] {name}({ticker}) 실패: {e}")
            continue
        if df is None or len(df) == 0:
            failed += 1
            print(f"  [!] {name}({ticker}): 빈 결과. 1시간봉은 약 2년치까지만 "
                  f"받을 수 있으니 --start 를 늦춰보세요.")
            continue

        df = _flatten(df)
        try:
            df = _to_kst(df)
        except Exception as e:
            failed += 1
            print(f"  [!] {name}({ticker}) 시간대 변환 실패: {e}")
            continue

        # 한국 날짜별로 모은다
        byday = {}
        for ts, r in df.iterrows():
            c = _num(r, "Close")
            if c is None or c <= 0:
                continue
            # 한국시간 15:00 까지 마감된 봉만 (그 이후는 한국 종가 시점에 미확정)
            if ts.hour > KR_CUTOFF_HOUR:
                continue
            byday.setdefault(ts.strftime("%Y%m%d"), []).append((ts.hour, c))

        n = 0
        for d, vals in sorted(byday.items()):
            vals.sort()
            hours = dict(vals)
            o = hours.get(KR_OPEN_HOUR) or (vals[0][1] if vals else None)
            m = hours.get(KR_MID_HOUR)
            cl = hours.get(KR_CUTOFF_HOUR) or vals[-1][1]
            if o is None or cl is None or o <= 0:
                continue
            rows.append({
                "date": d, "ticker": ticker,
                "kr_open": round(o, 3), "kr_mid": round(m, 3) if m else "",
                "kr_close": round(cl, 3),
                "kr_session_chg": round((cl / o - 1) * 100, 4),
                "bars": len(vals),
            })
            n += 1
        ok += 1
        if verbose:
            print(f"  {name}({ticker}): {n:,}일 (한국 09시~15시 봉만)")

    added = yearly_csv.append(DATA_DIR, PREFIX, FIELDS, rows,
                              key_fields=("date", "ticker")) if rows else 0
    if verbose:
        print(f"\n[선물] {ok}개 성공, {failed}개 실패, 새 행 {added:,}개")
    return {"ok": ok, "failed": failed, "added": added, "fetched": len(rows)}


def _dash(s):
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def main():
    ap = argparse.ArgumentParser(description="미국 지수 선물의 한국 장중 움직임")
    ap.add_argument("--start", default=None,
                    help="시작일. 1시간봉은 약 2년치까지만 되므로 기본값은 2년 전")
    ap.add_argument("--end", default=None)
    args = ap.parse_args()
    end = args.end or datetime.now().strftime("%Y%m%d")
    if args.start:
        start = args.start
    else:
        from datetime import timedelta
        start = (datetime.now() - timedelta(days=720)).strftime("%Y%m%d")

    try:
        import yfinance  # noqa: F401
    except ImportError:
        print("yfinance 가 없습니다:  pip install yfinance")
        return 1

    print(f"=== 미국 지수 선물 (1시간봉) {start} ~ {end} ===")
    print("    한국시간 09~15시 봉만 씁니다 - 한국 종가(15:30) 전에 확정된 값만.")
    for t, n in TICKERS.items():
        print(f"    {n} ({t})")
    print()
    r = collect(start, end)
    if r["ok"] == 0:
        print("\n[!] 하나도 못 받았습니다.")
        return 1
    print("\n완료. data/us_futures_*.csv 를 커밋하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
