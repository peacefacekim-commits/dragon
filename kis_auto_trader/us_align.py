"""미국 시장 날짜를 한국 거래일에 붙인다.

(2026-09-15 신설) 이 파일의 존재 이유는 하나다 - **날짜를 잘못 맞추면 미래
정보를 쓰게 되고, 그러면 백테스트 결과 전체가 거짓이 된다.**

시차:
  미국 9/10(목) 장은 한국시간 9/11(금) 새벽 5~6시에 끝난다.
  따라서 미국 9/10 종가는 한국 9/11 장이 열리기 몇 시간 전에 확정돼 있다.
  -> 미국 날짜 T 의 정보는 'T 보다 뒤인 첫 한국 거래일'에 쓸 수 있다.

흔한 실수 두 가지를 여기서 막는다:
  1) 미국 T 를 한국 T 에 붙이기 - 한국 T 는 미국 T 보다 먼저 끝나므로
     아직 없는 정보를 쓰는 셈이다 (미래 정보 누수).
  2) 한국 휴일을 무시하기 - 금요일 미국 장 결과는 월요일 한국 장에 쓰이고,
     그 사이 월요일이 휴장이면 화요일로 밀린다.
"""
import bisect
import csv
import collections


def load_us(data_dir, prefix="us_market") -> dict:
    """{ticker: {date: {open, high, low, close, volume}}}"""
    import yearly_csv
    out: dict[str, dict] = collections.defaultdict(dict)
    for (date, ticker), r in yearly_csv.load_rows(
            data_dir, prefix, key_fields=("date", "ticker")).items():
        try:
            out[ticker][date] = {k: float(r[k]) for k in ("open", "high", "low", "close")
                                 if r.get(k) not in ("", None)}
        except ValueError:
            continue
    return dict(out)


def next_kr_day(kr_dates: list[str], us_date: str) -> str | None:
    """미국 날짜 us_date 정보를 쓸 수 있는 첫 한국 거래일.

    us_date 와 같은 날은 안 된다 - 한국 장이 먼저 끝나기 때문이다.
    반드시 그보다 뒤인 날이어야 한다.
    """
    i = bisect.bisect_right(kr_dates, us_date)
    return kr_dates[i] if i < len(kr_dates) else None


def us_signal_for(kr_dates: list[str], us_series: dict) -> dict:
    """{한국거래일: 그 직전에 확정된 미국 등락률(%)}

    us_series 는 {date: {...close...}} 형태. 각 미국 날짜의 전일 대비 등락률을
    계산해서, 그 정보를 쓸 수 있는 첫 한국 거래일에 붙인다.

    같은 한국 거래일에 여러 미국 날짜가 매핑되면(연휴 등) 가장 최근 것을 쓴다.
    """
    us_days = sorted(us_series)
    out: dict[str, float] = {}
    for k in range(1, len(us_days)):
        prev, cur = us_days[k - 1], us_days[k]
        c0 = us_series[prev].get("close")
        c1 = us_series[cur].get("close")
        if not c0 or c0 <= 0 or not c1:
            continue
        kr = next_kr_day(kr_dates, cur)
        if kr is None:
            continue
        out[kr] = (c1 / c0 - 1) * 100      # 뒤에 오는 미국 날짜가 앞의 것을 덮어씀
    return out
