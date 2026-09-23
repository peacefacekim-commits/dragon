"""미국 지수/환율을 받는다 - 한국장 시작 전에 알 수 있는 유일한 외부 정보.

(2026-09-15 신설) 왜 필요한가:

오늘 한국 데이터로 만들 수 있는 지표를 거의 다 시험했는데 여덟 번 연속 막혔다.
모멘텀, 나쁜 날 피하기, 익절/손절 조합, 변동성 타이밍, 비중 조절, 계절성,
요일, 재조정 주기 - 전부 가격·거래량에서 유도한 지표라 서로 비슷한 정보를
담고 있었고, 같은 벽에 부딪혔다.

유일하게 방향이 나온 게 '시가 갭'이었다. 갭은 한국 주가 시계열에서 계산해낼
수 없는 정보(간밤 미국 시장, 환율, 글로벌 뉴스)가 반영된 값이다.

  갭 상위 10% 인 날만 투자:  누적 +21.6%, 최대낙폭 10.1% (항상 투자는 -98.6%, 98.7%)
  갭 상위 20% 인 날 5일 보유: 누적 +91.9%, 최대낙폭 22.4%

그런데 여기에 치명적인 문제가 있다. **갭은 시가가 정해진 뒤에야 알 수 있다.**
동시호가에 주문을 넣으려면 그 전에 판단해야 하는데, 그때는 갭을 모른다.
즉 위 결과는 "시가를 보고 시가에 산다"는 불가능한 가정일 수 있다.

그래서 갭 대신 **전날 미국 종가 등락률**로 같은 계산을 해야 한다. 그건 한국장이
열리기 몇 시간 전에 확정되므로 실제로 쓸 수 있다. 이 파일이 그 데이터를 받는다.

날짜 맞추기 (여기가 틀리면 전부 무의미해진다):

  미국 9/10 장은 한국시간 9/11 새벽 6시경에 끝난다.
  따라서 미국 9/10 종가는 한국 9/11 장에 영향을 준다.
  -> 미국 날짜 T 를 한국 날짜 T 이후 첫 거래일에 붙인다.
  이 파일은 미국 날짜 그대로 저장하고, 붙이는 건 분석하는 쪽에서 한다
  (한국 휴장일을 알아야 하는데 그건 패널에 있으므로).

실행 (PC에서):
    pip install yfinance
    python fetch_us_market.py
몇 초면 끝난다. 종목이 아니라 지수 몇 개라서 호출이 몇 번뿐이다.
"""
import argparse
import sys
from datetime import datetime

import yearly_csv
from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
PREFIX = "us_market"
FIELDS = ["date", "ticker", "open", "high", "low", "close", "volume"]

# 받을 것. 한국 시장에 영향을 준다고 흔히 이야기되는 것들.
TICKERS = {
    "^GSPC": "S&P500",
    "^IXIC": "나스닥",
    "^DJI": "다우",
    "^VIX": "변동성지수(VIX)",
    "KRW=X": "달러/원 환율",
    "^SOX": "필라델피아 반도체",   # 한국 반도체 비중이 커서 같이 본다
    # (2026-09-18 추가) 사용자가 금리도 보자고 해서 넣었다. 미국 10년
    # 국채금리. 이 티커는 '수익률 x10' 으로 나온다 (4.2% -> 42.0).
    # 받아오기만 하고 해석은 market_indicators.py 쪽에서 한다.
    "^TNX": "미국 10년 국채금리",
}


def _flatten(df):
    """yfinance 가 돌려주는 MultiIndex 컬럼을 평평하게 만든다.

    (2026-09-16 버그수정) yfinance 는 티커가 하나여도 컬럼을 (필드, 티커)
    2단으로 돌려준다. 그 상태에서 r["Volume"] 을 하면 스칼라가 아니라 Series 가
    나오고, 그걸 비교문에 쓰면 "The truth value of a Series is ambiguous" 로
    죽는다. 실제 PC 에서 이 에러가 났다.
    """
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df


def _num(row, key):
    """행에서 숫자 하나를 안전하게 꺼낸다. 없거나 NaN 이면 None."""
    try:
        v = row[key]
    except (KeyError, IndexError, TypeError):
        return None
    # 혹시 아직 Series 로 남아있으면 첫 값을 쓴다
    if hasattr(v, "iloc"):
        if len(v) == 0:
            return None
        v = v.iloc[0]
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f      # NaN 제외


def collect(start: str, end: str, verbose: bool = True) -> dict:
    import warnings
    warnings.filterwarnings("ignore")
    import yfinance as yf

    have = set()
    for (d, t) in yearly_csv.load_rows(DATA_DIR, PREFIX, key_fields=("date", "ticker")):
        have.add(t)

    rows, ok, failed = [], 0, 0
    for ticker, name in TICKERS.items():
        if ticker in have:
            if verbose:
                print(f"  {name}({ticker}): 이미 있음, 건너뜀")
            ok += 1
            continue
        try:
            df = yf.download(ticker, start=_dash(start), end=_dash(end),
                             progress=False, auto_adjust=True)
        except Exception as e:
            failed += 1
            print(f"  [!] {name}({ticker}) 실패: {e}")
            continue
        if df is None or len(df) == 0:
            failed += 1
            print(f"  [!] {name}({ticker}): 빈 결과")
            continue
        df = _flatten(df)
        n = 0
        for idx, r in df.iterrows():
            close = _num(r, "Close")
            if close is None or close <= 0:
                continue
            vol = _num(r, "Volume")
            rows.append({
                "date": idx.strftime("%Y%m%d"), "ticker": ticker,
                "open": _num(r, "Open") if _num(r, "Open") is not None else "",
                "high": _num(r, "High") if _num(r, "High") is not None else "",
                "low": _num(r, "Low") if _num(r, "Low") is not None else "",
                "close": close,
                "volume": int(vol) if vol is not None else 0,
            })
            n += 1
        ok += 1
        if verbose:
            print(f"  {name}({ticker}): {n:,}행")

    added = yearly_csv.append(DATA_DIR, PREFIX, FIELDS, rows,
                             key_fields=("date", "ticker")) if rows else 0
    if verbose:
        print(f"\n[미국시장] {ok}개 성공, {failed}개 실패, 새 행 {added:,}개")
    return {"ok": ok, "failed": failed, "added": added, "fetched": len(rows)}


def _dash(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


def main():
    ap = argparse.ArgumentParser(description="미국 지수/환율 수집")
    ap.add_argument("--start", default="20201201",
                    help="시작일. 한국 패널(2021-01-04)보다 앞서야 "
                         "첫날부터 전날 미국 데이터가 있다")
    ap.add_argument("--end", default=None)
    args = ap.parse_args()
    end = args.end or datetime.now().strftime("%Y%m%d")

    try:
        import yfinance  # noqa: F401
    except ImportError:
        print("yfinance 가 없습니다. 먼저 설치하세요:  pip install yfinance")
        return 1

    print(f"=== 미국 지수/환율 수집 {args.start} ~ {end} ===")
    for t, n in TICKERS.items():
        print(f"    {n} ({t})")
    print()
    r = collect(args.start, end)
    if r["ok"] == 0:
        print("\n[!] 하나도 못 받았습니다. 인터넷 연결을 확인하세요.")
        return 1
    print("\n완료. data/us_market_*.csv 를 커밋하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
