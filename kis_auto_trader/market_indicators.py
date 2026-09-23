"""매일 '장 시작 전에 알 수 있는' 시장 지표를 기록한다.

(2026-09-16 신설) 왜 이 파일이 필요한가:

사용자 방침: "좋은 날에 꼭 플러스일 것까지는 바라지 않는다. 일단 나쁜 날만
피하고, 데이터를 쌓아가면서 점점 걸러내자."

그러려면 **필터가 맞았는지 나중에 채점할 수 있어야** 한다. 그 채점표가 이
파일이다. 매일 지표를 기록해두면, 몇 달 뒤에 "그때 이 지표가 나쁘다고 했던
날들이 실제로 나빴나"를 앞검증(out-of-sample)으로 확인할 수 있다.

이게 백테스트와 다른 점:

  백테스트  과거 데이터에 기준을 맞춘다 -> 노이즈를 외울 수 있다
  이 기록    기준을 먼저 정하고 앞으로 채점한다 -> 외울 수가 없다

실제로 2026-09-16 에 지표 11개를 합쳐 앞 절반으로 학습시켜봤더니, 학습
구간에서는 예측-실제 상관 +0.231 이 나왔지만 시험 구간에서는 +0.142 로
떨어지고 평균 수익이 마이너스가 됐다. 과거에 맞추는 방식의 한계다.

기록하는 지표 (전부 그날 한국장이 열리기 전에 확정되는 값):

  전날 미국    S&P500 / 나스닥 / 다우 / 필라델피아반도체 등락률, VIX 수준과 변화
  전날 환율    달러/원 등락률
  한국 최근    20일 변동성, 5일 상승종목 비율, 5일 수익률
  전날 수급    시장 전체 외국인/기관/개인 순매수 비중

그리고 '결과'(그날 실제 시장 등락)도 같이 기록한다. 채점하려면 둘이 다
있어야 하기 때문이다. 단 결과는 그날 장이 끝난 뒤에 채워진다.

사용:
  python market_indicators.py --backfill   # 과거 5년치를 한 번에 채운다
  python market_indicators.py              # 오늘 하루치 (daemon 이 매일 부름)
"""
import argparse
import statistics
import sys
from datetime import datetime

import yearly_csv
from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
PREFIX = "market_indicators"

# 컬럼은 항상 맨 끝에 추가한다 (yearly_csv 문서 참고).
FIELDS = [
    "date",
    # --- 장 시작 전에 알 수 있는 값 (예측에 쓸 수 있음) ---
    "us_sp500", "us_nasdaq", "us_dow", "us_sox", "us_vix_chg", "us_vix_level",
    "fx_krw",
    "kr_vol20", "kr_breadth5", "kr_ret5",
    "flow_foreign", "flow_inst", "flow_indiv",
    # --- 결과 (장 끝난 뒤 채워짐. 채점용이며 예측에 쓰면 미래 정보 누수) ---
    "result_c2c", "result_o2c", "result_breadth",
    # (2026-09-18 추가) 금리. 컬럼은 맨 끝에 붙인다 - 중간에 끼우면 기존
    # CSV 행이 어긋난다(예전에 virtual_trades.csv 16행이 그렇게 깨졌다).
    # 맨 끝이라도 result_ 로 시작하지 않으므로 PREDICTOR_FIELDS 에 자동으로
    # 들어간다. 과거분은 fetch_us_market.py --backfill 후 --backfill 필요.
    "us_tnx_level", "us_tnx_chg",
]

# 예측에 써도 되는 컬럼과, 절대 쓰면 안 되는 컬럼을 코드로 구분해둔다.
# 사람이 헷갈려서 result_* 를 입력으로 넣는 사고를 막기 위한 것.
PREDICTOR_FIELDS = [f for f in FIELDS if f != "date" and not f.startswith("result_")]
OUTCOME_FIELDS = [f for f in FIELDS if f.startswith("result_")]


def load() -> dict:
    """{date: row}"""
    return {d: r for (d, _), r in _load_keyed().items()}


def _load_keyed() -> dict:
    return yearly_csv.load_rows(DATA_DIR, PREFIX, key_fields=("date", "date"))


def save(rows: list) -> int:
    return yearly_csv.append(DATA_DIR, PREFIX, FIELDS, rows, key_fields=("date",))


def compute_all(verbose: bool = True) -> list:
    """패널 + 미국 데이터 + 수급으로 전 기간 지표를 계산한다.

    전부 '그날 이전' 정보만 쓴다 - result_* 만 그날 값이다.
    """
    import collections
    import pathlib

    import backtest
    import panel as panel_mod
    import us_align
    panel_mod.PREFIX = "krx_panel"
    p = backtest.Panel.load()
    dates = p.dates
    if verbose:
        print(f"패널 {len(p.bars):,}종목 {len(dates):,}거래일")

    kr = {}
    for d in dates:
        oc, cc = [], []
        for c, bars in p.bars.items():
            j = p.pos_at(c, d)
            if j < 1 or bars[j].date != d:
                continue
            b, pb = bars[j], bars[j - 1]
            if not b.open or b.open <= 0 or pb.close <= 0 or b.close <= 0:
                continue
            oc.append(b.close / b.open - 1)
            cc.append(b.close / pb.close - 1)
        if len(oc) >= 100:
            kr[d] = {"o2c": statistics.mean(oc), "c2c": statistics.mean(cc),
                     "breadth": sum(1 for r in cc if r > 0) / len(cc)}

    us = us_align.load_us(pathlib.Path(DATA_DIR))
    usig = {t: us_align.us_signal_for(dates, s) for t, s in us.items()}
    vix_close = {d: v.get("close") for d, v in us.get("^VIX", {}).items()}
    vix_days = sorted(x for x in vix_close if vix_close[x])
    vix_prior = {}
    import bisect
    for d in dates:
        i = bisect.bisect_left(vix_days, d) - 1
        if i >= 0:
            vix_prior[d] = vix_close[vix_days[i]]

    # 금리도 VIX 와 같은 방식으로 '전날까지 확정된 수준' 을 쓴다.
    # ^TNX 는 수익률x10 으로 나오므로 10 으로 나눠 %로 맞춘다.
    tnx_close = {d: v.get("close") for d, v in us.get("^TNX", {}).items()}
    tnx_days = sorted(x for x in tnx_close if tnx_close[x])
    tnx_prior = {}
    for d in dates:
        i = bisect.bisect_left(tnx_days, d) - 1
        if i >= 0:
            tnx_prior[d] = tnx_close[tnx_days[i]] / 10.0

    mflow = collections.defaultdict(lambda: {"f": 0.0, "n": 0.0, "i": 0.0})
    try:
        for (d, _c), r in yearly_csv.load_rows(pathlib.Path(DATA_DIR), "krx_flow").items():
            try:
                mflow[d]["f"] += float(r["foreign"] or 0)
                mflow[d]["n"] += float(r["inst"] or 0)
                mflow[d]["i"] += float(r["indiv"] or 0)
            except ValueError:
                continue
    except Exception as e:
        if verbose:
            print(f"  [!] 수급 데이터를 못 읽었습니다 (해당 컬럼은 비워둡니다): {e}")

    kd = sorted(kr)
    out = []
    for n, d in enumerate(kd):
        if n < 21:
            continue
        prev = kd[n - 1]
        hist = [kr[kd[m]]["c2c"] for m in range(n - 20, n)]
        ff = mflow.get(prev)
        tot = (abs(ff["f"]) + abs(ff["n"]) + abs(ff["i"])) if ff else 0

        def pct(x):
            return round(x / tot * 100, 4) if tot > 0 else ""

        def g(t):
            v = usig.get(t, {}).get(d)
            return round(v, 4) if v is not None else ""

        out.append({
            "date": d,
            "us_sp500": g("^GSPC"), "us_nasdaq": g("^IXIC"),
            "us_dow": g("^DJI"), "us_sox": g("^SOX"),
            "us_vix_chg": g("^VIX"),
            "us_vix_level": round(vix_prior[d], 2) if d in vix_prior else "",
            "fx_krw": g("KRW=X"),
            "kr_vol20": round(statistics.pstdev(hist) * 100, 4),
            "kr_breadth5": round(statistics.mean(kr[kd[m]]["breadth"] for m in range(n - 5, n)) * 100, 2),
            "kr_ret5": round(sum(kr[kd[m]]["c2c"] for m in range(n - 5, n)) * 100, 4),
            "flow_foreign": pct(ff["f"]) if ff else "",
            "flow_inst": pct(ff["n"]) if ff else "",
            "flow_indiv": pct(ff["i"]) if ff else "",
            "result_c2c": round(kr[d]["c2c"] * 100, 4),
            "result_o2c": round(kr[d]["o2c"] * 100, 4),
            "result_breadth": round(kr[d]["breadth"] * 100, 2),
            # 금리: 전날까지 확정된 수준(%)과 그 전날 대비 변화(%p).
            # ^TNX 를 아직 안 받았으면 빈칸으로 남는다.
            "us_tnx_level": (round(tnx_prior[d], 3)
                             if d in tnx_prior else ""),
            "us_tnx_chg": g("^TNX"),
        })
    return out


def summary() -> str:
    rows = load()
    if not rows:
        return "지표 기록 없음 - python market_indicators.py --backfill 을 실행하세요."
    ds = sorted(rows)
    filled = sum(1 for d in ds if rows[d].get("result_c2c") not in ("", None))
    return (f"지표 기록: {len(ds):,}거래일 ({ds[0]}~{ds[-1]}), 결과까지 채워진 날 {filled:,}일\n"
            f"예측용 컬럼 {len(PREDICTOR_FIELDS)}개 / 결과 컬럼 {len(OUTCOME_FIELDS)}개")


def main():
    ap = argparse.ArgumentParser(description="장 시작 전 시장 지표 기록")
    ap.add_argument("--backfill", action="store_true",
                    help="패널·미국·수급 데이터로 과거 전체를 계산해 채운다")
    args = ap.parse_args()

    if args.backfill:
        rows = compute_all()
        added = save(rows)
        print(f"\n[지표] {len(rows):,}일 계산, 새 행 {added:,}개 저장")
        print(summary())
        return 0

    print(summary())
    print("\n(과거를 채우려면 --backfill)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
