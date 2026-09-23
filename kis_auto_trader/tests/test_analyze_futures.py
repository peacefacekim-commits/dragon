"""analyze_futures.py 검증 - 특히 '매매할 수 없는 날' 배제.

(2026-09-16 신설) 이 파일이 존재하는 이유가 그 자체로 결과다.

선물 신호를 처음 돌렸을 때 다음날 갭 상관이 +0.184/+0.213 이고 전·후반부
부호도 같았다. 열두 번 시도 중 처음으로 분할 검증을 통과했다. 그런데 표본에
한국 공휴일이 섞여 있었다. 선물은 한국 휴일에도 거래되지만 그 날은 한국
종가가 없어서 주문을 낼 수 없다. 게다가 휴일 동안 선물에 미국장 여러 날치가
쌓여서 다음 거래일 갭에 한꺼번에 반영된다. 관계는 진짜지만 매매는 불가능하다.

거래일만 남기면 +0.184 -> +0.019 로 사실상 사라졌다.

그래서 이 테스트는 "휴일이 정말 빠지는가" 를 코드로 고정한다. 분할 검증은
과최적화는 잡지만 표본 자체가 틀린 것은 잡지 못하므로, 이건 테스트로 막아야
한다.

실행:
  python tests/test_analyze_futures.py
"""
import pathlib
import shutil
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import analyze_futures as af  # noqa: E402
import yearly_csv  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# ---------------------------------------------------------------- 준비
# 한국 거래일: 0102, 0105, 0106 (0103, 0104 는 휴일)
# 종목 40개를 만들어 MIN_STOCKS_PER_DAY(30) 을 넘긴다.
tmp = pathlib.Path(tempfile.mkdtemp()) / "data"
af.DATA_DIR = tmp

KR_DAYS = ["20260102", "20260105", "20260106"]
CLOSES = {"20260102": 100.0, "20260105": 110.0, "20260106": 121.0}   # 매일 +10%
OPENS = {"20260102": 100.0, "20260105": 105.0, "20260106": 115.5}    # 갭 +5%

panel = []
for d in KR_DAYS:
    for i in range(40):
        panel.append({"date": d, "code": f"{i:06d}", "name": f"종목{i}",
                      "open": OPENS[d], "high": CLOSES[d], "low": OPENS[d],
                      "close": CLOSES[d], "volume": 1000})
yearly_csv.append(tmp, "krx_panel",
                  ["date", "code", "name", "open", "high", "low", "close", "volume"],
                  panel, key_fields=("date", "code"))

# 선물: 한국 거래일 2일 + 한국 휴일 2일
fut = [
    {"date": "20260102", "ticker": "ES=F", "kr_open": 100, "kr_mid": "",
     "kr_close": 101, "kr_session_chg": 1.0, "bars": 6},
    {"date": "20260103", "ticker": "ES=F", "kr_open": 100, "kr_mid": "",
     "kr_close": 102, "kr_session_chg": 2.0, "bars": 6},   # 한국 휴일
    {"date": "20260104", "ticker": "ES=F", "kr_open": 100, "kr_mid": "",
     "kr_close": 103, "kr_session_chg": 3.0, "bars": 6},   # 한국 휴일
    {"date": "20260105", "ticker": "ES=F", "kr_open": 100, "kr_mid": "",
     "kr_close": 99, "kr_session_chg": -1.0, "bars": 6},
]
yearly_csv.append(tmp, "us_futures", af_fields := [
    "date", "ticker", "kr_open", "kr_mid", "kr_close", "kr_session_chg", "bars"],
    fut, key_fields=("date", "ticker"))

# ---------------------------------------------------------------- 1) 시장 계산
kr, byday = af.load_market()
check("1) 첫날은 전일이 없어 빠진다", set(kr) == {"20260105", "20260106"},
      str(sorted(kr)))
gap, o2c, c2c = kr["20260105"]
check("1b) 갭이 전일 종가 기준 (105/100-1 = +5%)", abs(gap - 5.0) < 1e-6, f"{gap}")
check("1c) 시가대비 (110/105-1 = +4.762%)", abs(o2c - 4.7619) < 1e-3, f"{o2c}")
check("1d) 종가대비 (110/100-1 = +10%)", abs(c2c - 10.0) < 1e-6, f"{c2c}")

# ---------------------------------------------------------------- 2) 휴일 배제
out = af.analyze(tradeable_only=True, verbose=False)
check("2) 신호일이 한국 거래일인 것만 남는다 (4일 -> 2일)",
      out["ES=F"]["n"] == 2, str(out["ES=F"]["n"]))
check("2b) 버린 휴일 수를 보고한다", out["ES=F"]["holiday_days"] == 2,
      str(out["ES=F"]["holiday_days"]))

out_all = af.analyze(tradeable_only=False, verbose=False)
check("2c) --include-holidays 면 휴일도 들어간다 (4일)",
      out_all["ES=F"]["n"] == 4, str(out_all["ES=F"]["n"]))
check("2d) 기본값은 휴일 배제 - 둘의 표본이 다르다",
      out["ES=F"]["n"] < out_all["ES=F"]["n"])

# ---------------------------------------------------------------- 3) 수수료
r = af.hold_return(byday, KR_DAYS, "20260102", 1)
check("3) 보유 수익에서 수수료가 빠진다 (+10% - 0.21% = +9.79%)",
      abs(r - (10.0 - af.FEE_ROUND_TRIP_PCT)) < 1e-6, f"{r}")
r2 = af.hold_return(byday, KR_DAYS, "20260102", 2)
check("3b) 2거래일 보유도 수수료는 한 번만 (121/100-1 - 0.21 = +20.79%)",
      abs(r2 - (21.0 - af.FEE_ROUND_TRIP_PCT)) < 1e-6, f"{r2}")
check("3c) 기간을 벗어나면 None", af.hold_return(byday, KR_DAYS, "20260106", 1) is None)
check("3d) 왕복 수수료가 0.21%", abs(af.FEE_ROUND_TRIP_PCT - 0.21) < 1e-9)

# ---------------------------------------------------------------- 4) 잔차
# 완전히 겹치는 값(y = 2x)이면 잔차가 0 이 되어 상관이 None (표준편차 0)
xs = [1.0, 2.0, 3.0, 4.0]
res = af.residual(xs, [2.0, 4.0, 6.0, 8.0])
check("4) 통제변수와 완전히 겹치면 잔차가 0 (새 정보 없음)",
      all(abs(v) < 1e-9 for v in res), str(res))
res2 = af.residual(xs, [1.0, 1.0, 1.0, 1.0])
check("4b) 통제변수가 상수면 원래 값의 편차가 그대로 남는다",
      abs(res2[0] - (1.0 - 2.5)) < 1e-9, str(res2))

# ---------------------------------------------------------------- 5) 주의문
check("5) 표본 한계(473일)가 주의문에 적혀 있다", "473" in af.CAUTION)
check("5b) 휴일 함정이 주의문에 적혀 있다", "주문을 낼 수 없는" in af.CAUTION)

# ---------------------------------------------------------------- 6) 관찰 전용
src = (REPO_ROOT / "analyze_futures.py").read_text(encoding="utf-8")
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"6) 주문/통신 코드가 없다 ({banned})", banned not in src)

shutil.rmtree(tmp.parent, ignore_errors=True)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
