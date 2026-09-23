"""market_indicators.py 검증 - 특히 미래 정보가 섞이지 않는지.

(2026-09-16 신설) 이 파일의 목적은 "나쁜 날을 피하는 필터"를 나중에 채점할
재료를 만드는 것이다. 그런데 예측용 컬럼에 그날 결과가 섞이면 채점 자체가
거짓이 된다. 그래서 그 분리를 코드로 확인한다.

실행:
  python tests/test_market_indicators.py
"""
import pathlib
import shutil
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import market_indicators as mi  # noqa: E402
import yearly_csv  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# ---------------------------------------------------------------- 1) 컬럼 분리
check("1) 예측용 컬럼에 result_ 가 하나도 없다 (미래 정보 차단)",
      all(not f.startswith("result_") for f in mi.PREDICTOR_FIELDS),
      str([f for f in mi.PREDICTOR_FIELDS if f.startswith("result_")]))
check("1b) 결과 컬럼은 전부 result_ 로 시작한다",
      all(f.startswith("result_") for f in mi.OUTCOME_FIELDS), str(mi.OUTCOME_FIELDS))
check("1c) 예측용 + 결과 + date = 전체 컬럼 (빠진 것 없음)",
      len(mi.PREDICTOR_FIELDS) + len(mi.OUTCOME_FIELDS) + 1 == len(mi.FIELDS),
      f"{len(mi.PREDICTOR_FIELDS)}+{len(mi.OUTCOME_FIELDS)}+1 vs {len(mi.FIELDS)}")
check("1d) date 가 맨 앞", mi.FIELDS[0] == "date")

# ---------------------------------------------------------------- 2) 저장/읽기
tmp = pathlib.Path(tempfile.mkdtemp()) / "data"
mi.DATA_DIR = tmp
rows = [
    {f: "" for f in mi.FIELDS} | {"date": "20260101", "us_sp500": 1.5, "result_c2c": -0.5},
    {f: "" for f in mi.FIELDS} | {"date": "20260102", "us_sp500": -2.0, "result_c2c": 1.2},
]
added = mi.save(rows)
check("2) 저장된다", added == 2, str(added))
loaded = mi.load()
check("2b) 날짜로 읽힌다", set(loaded) == {"20260101", "20260102"}, str(sorted(loaded)))
check("2c) 값이 보존된다", loaded["20260101"]["us_sp500"] == "1.5",
      loaded["20260101"]["us_sp500"])

# 같은 날짜를 다시 넣으면 덮어쓰고 행이 안 늘어난다 (매일 전체를 다시 계산해도 안전)
again = mi.save([{f: "" for f in mi.FIELDS} | {"date": "20260101", "us_sp500": 9.9}])
check("2d) 같은 날짜는 덮어쓰고 행이 안 늘어난다 (매일 전체 재계산해도 안전)",
      again == 0 and mi.load()["20260101"]["us_sp500"] == "9.9",
      f"added={again} val={mi.load()['20260101']['us_sp500']}")

# ---------------------------------------------------------------- 3) 헤더 순서
check("3) 파일 헤더가 지금 컬럼 순서와 일치 (밀려 읽히는 사고 방지)",
      yearly_csv.check_header(tmp, mi.PREFIX, mi.FIELDS) == [])

# ---------------------------------------------------------------- 4) 요약
check("4) 기록이 없으면 안내 문구", "없음" in (lambda: (
    setattr(mi, "DATA_DIR", tmp / "empty"), mi.summary())[1])())
mi.DATA_DIR = tmp
s = mi.summary()
check("4b) 기록이 있으면 일수와 기간을 보여준다", "2거래일" in s, s.replace("\n", " / "))

shutil.rmtree(tmp.parent, ignore_errors=True)

# ---------------------------------------------------------------- 5) 백업 대상
import backup  # noqa: E402
src = (REPO_ROOT / "backup.py").read_text(encoding="utf-8")
check("5) 백업 대상에 지표 파일이 포함돼 있다", "market_indicators_*.csv" in src)
for pre in ("krx_panel", "krx_flow", "us_market"):
    check(f"5b) 백업 대상에 {pre} 포함", pre in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
