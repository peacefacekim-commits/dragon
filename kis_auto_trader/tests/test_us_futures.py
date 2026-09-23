"""fetch_us_futures.py 검증 - 특히 시간대와 '미확정 봉 배제'.

(2026-09-16 신설) 이 파일의 핵심 위험은 둘이다.

  1) 시간대를 잘못 바꾸면 한국 날짜가 어긋나서 전부 무의미해진다.
  2) 한국 종가(15:30) 이후에 마감되는 봉을 쓰면 미래 정보가 섞인다.
     한국시간 15:00~16:00 봉은 16시에 끝나므로, 한국 종가 시점에는 아직
     확정되지 않은 값이다. 그걸 쓰면 "종가 전에 알 수 있다"는 전제가 깨진다.

가짜 객체가 아니라 진짜 tz-aware pandas DataFrame 으로 검증한다 - 시간대
변환이 핵심이라 흉내로는 의미가 없다.

실행:
  python tests/test_us_futures.py
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
    import pandas as pd
except ImportError:
    print("pandas 가 없어 건너뜁니다 (이 스크립트는 PC 에서만 씁니다).")
    sys.exit(0)

import fetch_us_futures as fuf  # noqa: E402
import yearly_csv  # noqa: E402

# ---------------------------------------------------------------- 1) 시간대 변환
# 미국 동부시간 기준 봉을 만들고, 한국시간으로 바뀌는지 본다.
# 2026-09-15 20:00 ET = 2026-09-16 09:00 KST (여름, ET=UTC-4, KST=UTC+9 -> +13시간)
idx_et = pd.to_datetime(["2026-09-15 20:00", "2026-09-15 23:00",
                         "2026-09-16 01:00", "2026-09-16 02:00"]).tz_localize("America/New_York")
df = pd.DataFrame({"Close": [100.0, 101.0, 102.0, 103.0]}, index=idx_et)
kst = fuf._to_kst(df)
hours = [t.hour for t in kst.index]
check("1) 미국 동부시간이 한국시간으로 바뀐다", hours == [9, 12, 14, 15], str(hours))
check("1b) 한국 날짜로도 맞다",
      [t.strftime("%Y%m%d") for t in kst.index] == ["20260916"] * 4,
      str([t.strftime("%Y%m%d") for t in kst.index]))

# 시간대 정보가 없으면 UTC 로 가정
naive = pd.DataFrame({"Close": [1.0]}, index=pd.to_datetime(["2026-09-16 00:00"]))
k2 = fuf._to_kst(naive)
check("1c) 시간대 정보가 없으면 UTC 로 가정해 +9시간", k2.index[0].hour == 9,
      str(k2.index[0]))

# ---------------------------------------------------------------- 2) 미확정 봉 배제
tmp = pathlib.Path(tempfile.mkdtemp()) / "data"
fuf.DATA_DIR = tmp
saved = fuf.TICKERS
fuf.TICKERS = {"ES=F": "S&P500 선물"}


class FakeYF:
    @staticmethod
    def download(t, **kw):
        return df       # 한국시간 09,12,14,15시 봉


sys.modules["yfinance"] = FakeYF
r = fuf.collect("20260901", "20260917", verbose=False)
rows = yearly_csv.load_rows(tmp, "us_futures", key_fields=("date", "ticker"))
check("2) 저장된다", r["ok"] == 1 and len(rows) == 1, str(r))

row = rows[("20260916", "ES=F")]
check("2b) 한국 15시 봉(16시 마감)은 제외된다 - 종가 시점에 미확정",
      row["bars"] == "3", f"bars={row['bars']} (09,12,14시만 = 3개여야 함)")
check("2c) kr_close 는 14시 봉 값(102.0), 15시 봉(103.0)이 아니다",
      row["kr_close"] == "102.0", f"kr_close={row['kr_close']}")
check("2d) kr_open 은 09시 봉 값", row["kr_open"] == "100.0", f"kr_open={row['kr_open']}")
check("2e) 장중 변화율이 09->14시로 계산된다 (102/100-1 = +2%)",
      row["kr_session_chg"] == "2.0", f"chg={row['kr_session_chg']}")

# ---------------------------------------------------------------- 3) 이어받기
before = len(rows)
r2 = fuf.collect("20260901", "20260917", verbose=False)
check("3) 이미 받은 티커는 건너뛴다", r2["fetched"] == 0, str(r2))

fuf.TICKERS = saved
shutil.rmtree(tmp.parent, ignore_errors=True)

# ---------------------------------------------------------------- 4) 컬럼 규칙
check("4) date 가 맨 앞, 컬럼 순서 고정", fuf.FIELDS[0] == "date")
check("4b) 컷오프가 한국 종가(15:30)보다 앞", fuf.KR_CUTOFF_HOUR <= 14,
      f"KR_CUTOFF_HOUR={fuf.KR_CUTOFF_HOUR}")

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
