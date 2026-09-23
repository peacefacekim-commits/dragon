"""미국 날짜를 한국 거래일에 붙이는 로직 검증.

(2026-09-15 신설) 이게 틀리면 미래 정보를 쓰게 되어 백테스트가 통째로
거짓이 된다. 그래서 따로 떼어내서 검증한다.

특히 확인하는 것:
  - 미국 T 정보가 한국 T 에 붙지 않는가 (한국이 먼저 끝나므로 미래 정보 누수)
  - 한국 휴장일을 건너뛰고 다음 거래일에 붙는가
  - 연휴로 미국 날짜 여러 개가 한 한국 거래일에 몰리면 최신 것을 쓰는가

실행:
  python tests/test_us_align.py
"""
import pathlib
import shutil
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import us_align  # noqa: E402
import yearly_csv  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# 한국 거래일: 9/10(목), 9/11(금), 9/14(월) ... 9/12~13 주말, 9/15 는 휴장 가정
KR = ["20260908", "20260909", "20260910", "20260911", "20260914", "20260916"]

# ---------------------------------------------------------------- 1) 기본
check("1) 미국 9/10 정보는 한국 9/11 에 붙는다 (한국 9/10 아님)",
      us_align.next_kr_day(KR, "20260910") == "20260911",
      us_align.next_kr_day(KR, "20260910"))
check("1b) 미국 T 가 한국 T 에 붙으면 미래 정보 누수 - 그렇게 되지 않는다",
      us_align.next_kr_day(KR, "20260909") != "20260909")

# ---------------------------------------------------------------- 2) 주말
check("2) 미국 금요일(9/11) 정보는 한국 월요일(9/14)에 붙는다",
      us_align.next_kr_day(KR, "20260911") == "20260914",
      us_align.next_kr_day(KR, "20260911"))

# ---------------------------------------------------------------- 3) 한국 휴장
check("3) 한국이 9/15 휴장이면 9/16 으로 밀린다",
      us_align.next_kr_day(KR, "20260914") == "20260916",
      us_align.next_kr_day(KR, "20260914"))

# ---------------------------------------------------------------- 4) 범위 밖
check("4) 붙일 한국 거래일이 없으면 None", us_align.next_kr_day(KR, "20261231") is None)

# ---------------------------------------------------------------- 5) 등락률 계산 + 매핑
us = {
    "20260909": {"close": 100.0},
    "20260910": {"close": 110.0},   # +10%
    "20260911": {"close": 99.0},    # -10%
    "20260914": {"close": 99.0},    # 0%
}
sig = us_align.us_signal_for(KR, us)
check("5) 미국 9/10 의 +10% 가 한국 9/11 에 붙는다",
      abs(sig.get("20260911", 0) - 10.0) < 1e-9, str(sig))
check("5b) 미국 9/11 의 -10% 가 한국 9/14 에 붙는다",
      abs(sig.get("20260914", 0) + 10.0) < 1e-9, str(sig))
check("5c) 한국 9/10 에는 아무것도 안 붙는다 (아직 미국 9/10 이 안 끝났으므로)",
      "20260910" not in sig or sig["20260910"] != 10.0, str(sig.get("20260910")))

# ---------------------------------------------------------------- 6) 연휴로 몰릴 때
KR2 = ["20260910", "20260918"]      # 한국이 9/11~9/17 내내 휴장
us2 = {"20260910": {"close": 100.0}, "20260911": {"close": 105.0},
       "20260914": {"close": 110.0}, "20260917": {"close": 121.0}}
sig2 = us_align.us_signal_for(KR2, us2)
check("6) 미국 날짜 여러 개가 한 한국 거래일에 몰리면 가장 최근 것을 쓴다",
      abs(sig2.get("20260918", 0) - 10.0) < 1e-9,
      f"9/17 의 +10% 여야 함. 실제 {sig2.get('20260918')}")

# ---------------------------------------------------------------- 7) 파일 읽기
tmp = pathlib.Path(tempfile.mkdtemp()) / "data"
yearly_csv.append(tmp, "us_market",
                  ["date", "ticker", "open", "high", "low", "close", "volume"],
                  [{"date": "20260910", "ticker": "^GSPC", "open": 1, "high": 2,
                    "low": 1, "close": 110, "volume": 0},
                   {"date": "20260910", "ticker": "KRW=X", "open": 1, "high": 2,
                    "low": 1, "close": 1300, "volume": 0}],
                  key_fields=("date", "ticker"))
loaded = us_align.load_us(tmp)
check("7) 티커별로 나눠서 읽는다",
      set(loaded) == {"^GSPC", "KRW=X"}, str(sorted(loaded)))
check("7b) 같은 날짜에 티커가 여러 개여도 안 섞인다",
      loaded["^GSPC"]["20260910"]["close"] == 110
      and loaded["KRW=X"]["20260910"]["close"] == 1300)
shutil.rmtree(tmp.parent, ignore_errors=True)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
