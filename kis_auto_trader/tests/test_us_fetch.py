"""fetch_us_market.py 의 yfinance 응답 파싱 검증.

(2026-09-16 신설) 사용자 PC 에서 실제로 이 에러가 났다:

    ValueError: The truth value of a Series is ambiguous.

원인은 yfinance 가 티커 하나만 받아도 컬럼을 (필드, 티커) 2단 MultiIndex 로
돌려주는 것이었다. 그 상태에서 r["Volume"] 은 스칼라가 아니라 Series 라,
비교문에 쓰면 죽는다. 나는 컬럼이 평평할 거라고 가정하고 코드를 썼다.

가짜 객체가 아니라 진짜 pandas MultiIndex DataFrame 으로 검증한다 -
그게 실제로 죽었던 모양이므로, 흉내로는 같은 버그를 못 잡는다.

실행:
  python tests/test_us_fetch.py
"""
import pathlib
import shutil
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("pandas/numpy 가 없어 건너뜁니다 (fetch_us_market 는 PC 에서만 씁니다).")
    sys.exit(0)

import fetch_us_market as f  # noqa: E402
import yearly_csv  # noqa: E402

idx = pd.to_datetime(["2026-09-10", "2026-09-11"])
# yfinance 가 실제로 돌려주는 모양
mi = pd.DataFrame(
    [[100.0, 101.0, 99.0, 100.5, 1000],
     [101.0, 102.0, 100.0, 101.5, np.nan]],   # VIX/환율은 거래량이 NaN 으로 온다
    index=idx,
    columns=pd.MultiIndex.from_product(
        [["Open", "High", "Low", "Close", "Volume"], ["^GSPC"]]))

check("0) 재현: 컬럼이 2단 MultiIndex (원래 죽던 상황)", mi.columns.nlevels == 2)

flat = f._flatten(mi)
check("1) MultiIndex 를 평평하게 만든다",
      list(flat.columns) == ["Open", "High", "Low", "Close", "Volume"],
      str(list(flat.columns)))

r0, r1 = flat.iloc[0], flat.iloc[1]
check("2) 숫자를 스칼라로 꺼낸다 (Series 아님)", f._num(r0, "Close") == 100.5)
check("3) NaN 은 None 으로", f._num(r1, "Volume") is None)
check("4) 없는 컬럼은 None", f._num(r0, "없는컬럼") is None)

si = pd.DataFrame([[100.0, 100.5, 1000]], index=idx[:1],
                  columns=["Open", "Close", "Volume"])
check("5) MultiIndex 가 아닌 응답도 그대로 처리", list(f._flatten(si).columns) ==
      ["Open", "Close", "Volume"])

tmp = pathlib.Path(tempfile.mkdtemp()) / "data"
f.DATA_DIR = tmp
saved_tickers = f.TICKERS


class FakeYF:
    @staticmethod
    def download(t, **kw):
        return mi


sys.modules["yfinance"] = FakeYF
f.TICKERS = {"^GSPC": "S&P500"}
res = f.collect("20260901", "20260916", verbose=False)
rows = yearly_csv.load_rows(tmp, "us_market", key_fields=("date", "ticker"))
check("6) 끝까지 돌아서 저장된다", res["ok"] == 1 and len(rows) == 2, str(res))
check("6b) 거래량이 NaN 인 행도 버리지 않고 0 으로 저장",
      rows[("20260911", "^GSPC")]["volume"] == "0",
      f"volume={rows[('20260911', '^GSPC')]['volume']!r}")
f.TICKERS = saved_tickers
shutil.rmtree(tmp.parent, ignore_errors=True)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
