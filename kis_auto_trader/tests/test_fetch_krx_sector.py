"""fetch_krx_sector.py 검증 - 업종을 시점 기준으로 받는가.

(2026-09-22 신설) 이 파일에서 제일 크게 틀릴 수 있는 것은 **오늘 받은
업종을 과거에 갖다 붙이는 것**이다. 그건 생존편향과 같은 종류의
실수고, 이 저장소가 이미 한 번 겪은 실수다 (panel vs krx_panel).

그래서 넷을 본다.

  1) **date 가 스키마의 첫 열인가.** 시점을 안 적으면 언제 기준인지
     모르게 되고, 그러면 과거에 갖다 붙이는 것을 막을 수 없다.
  2) **(date, code) 로 중복을 막는가.** 같은 날 두 번 받아도 안 늘어야
     한다. 반대로 **다른 날 같은 종목은 늘어야 한다** - 업종이 바뀐
     것을 기록해야 하니까.
  3) **빈칸을 메우지 않는가.** 업종명이 없을 때 '기타' 로 채우면 가짜
     분류가 생긴다.
  4) **네트워크 없이도 돌아가는가.** pykrx 가 없으면 안내만 하고 1을
     반환해야지, 다른 수집을 막으면 안 된다.

실행:
  python tests/test_fetch_krx_sector.py
"""
import csv
import datetime as dt
import pathlib
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


import fetch_krx_sector as M  # noqa: E402

src = (REPO_ROOT / "fetch_krx_sector.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeDF:
    """pykrx 가 돌려주는 DataFrame 흉내. iterrows 만 쓴다."""

    def __init__(self, rows):
        self._rows = rows          # [(code, {컬럼: 값})]

    def __len__(self):
        return len(self._rows)

    def iterrows(self):
        return iter(self._rows)


class FakeStock:
    """get_market_sector_classifications 만 있는 가짜."""

    def __init__(self, table, fail=()):
        self.table = table         # {(date, market): FakeDF}
        self.fail = set(fail)      # {(date, market)} -> 예외
        self.calls = []

    def get_market_sector_classifications(self, date, market):
        self.calls.append((date, market))
        if (date, market) in self.fail:
            raise RuntimeError("로그인이 필요합니다")
        return self.table.get((date, market))


# =====================================================================
# A) 스키마 - date 가 먼저이고, 컬럼은 끝에만 붙인다
# =====================================================================
check("A1) 컬럼이 5개다", len(M.FIELDS) == 5, str(M.FIELDS))
check("A2) 첫 열이 date 다", M.FIELDS[0] == "date")
check("A3) code 가 둘째다", M.FIELDS[1] == "code")
check("A4) sector 가 있다", "sector" in M.FIELDS)
check("A5) market 이 있다", "market" in M.FIELDS)
check("A6) 파일 접두어가 krx_sector 다", M.PREFIX == "krx_sector")
check("A7) 컬럼은 끝에만 붙인다는 규약을 적었다", "맨 끝에" in flat)
check("A8) (date, code) 가 열쇠라고 적었다", "(date, code) 가 열쇠다" in flat)

# =====================================================================
# B) 왜 날짜별로 받나 - 설계 이유가 문서에 있는가
# =====================================================================
check("B1) 오늘 업종을 과거에 붙이면 안 된다고 적었다",
      "과거에 그대로 갖다 붙이면 안 된다" in flat)
check("B2) 생존편향과 같은 실수라고 짚었다", "생존편향" in src)
check("B3) 상장폐지 종목이 지금 조회하면 안 나온다고 적었다",
      "상장폐지된" in flat and "안 나온다" in src)
check("B4) pykrx 가 날짜를 받는다는 근거를 적었다",
      "get_market_sector_classifications(date, market)" in src)

# =====================================================================
# C) 표준 업종만 받는다 - 테마를 안 섞는가
# =====================================================================
check("C1) 테마는 안 받는다고 명시했다", "테마는 안 받는다" in flat)
check("C2) 무엇이 테마인지 예를 들었다",
      "2차전지" in src and "AI" in src)
check("C3) 표준은 사실이고 테마는 해석이라고 갈랐다",
      "표준 업종은 사실이고 테마는 해석이라" in flat)
check("C4) 테마가 필요하면 파일을 나눈다고 정했다",
      "따로** 얹는다" in flat or "파일을 나눠서" in flat)
check("C5) 답할 수 없는 것을 적었다", "답할 수 없다" in src)
check("C6) 업종이 수익을 예측하나는 여기서 안 답한다고 했다",
      "재료만" in flat)

# =====================================================================
# D) quarter_dates - 분기 중순, 오늘을 안 넘는다
# =====================================================================
ds = M.quarter_dates(2021, dt.date(2021, 12, 31))
check("D1) 2021년 한 해면 4개", len(ds) == 4, str(ds))
check("D2) 전부 15일이다", all(d.endswith("15") for d in ds))
check("D3) 3/6/9/12월이다",
      [d[4:6] for d in ds] == ["03", "06", "09", "12"], str(ds))

ds = M.quarter_dates(2021, dt.date(2021, 4, 1))
check("D4) 4월 1일이면 3월 것만", ds == ["20210315"], str(ds))

ds = M.quarter_dates(2021, dt.date(2021, 3, 14))
check("D5) 분기 중순 전이면 하나도 없다", ds == [], str(ds))

ds = M.quarter_dates(2021, dt.date(2021, 3, 15))
check("D6) 딱 그날이면 포함한다 (경계)", ds == ["20210315"], str(ds))

ds = M.quarter_dates(2021, dt.date(2026, 9, 22))
check("D7) 2021~2026-09 면 23개",
      len(ds) == 23, f"{len(ds)}개")
check("D8) 오름차순이다", ds == sorted(ds))
check("D9) 중복이 없다", len(ds) == len(set(ds)))
check("D10) 미래는 안 만든다", all(d <= "20260922" for d in ds))
check("D11) 첫 해가 상수와 같다", M.FIRST_YEAR == 2021)

# =====================================================================
# E) to_rows - 컬럼 이름이 달라도 읽고, 없으면 빈칸으로 둔다
# =====================================================================
rows = M.to_rows(FakeDF([("005930", {"종목명": "삼성전자", "업종명": "전기전자"})]),
                 "20240315", "KOSPI")
check("E1) 한 행이 나온다", len(rows) == 1)
check("E2) 열 순서가 FIELDS 와 같다",
      rows[0] == ["20240315", "005930", "삼성전자", "KOSPI", "전기전자"],
      str(rows[0]))

rows = M.to_rows(FakeDF([("005930", {"name": "SEC", "sector": "Electronics"})]),
                 "20240315", "KOSPI")
check("E3) 영문 컬럼 이름도 읽는다",
      rows[0][2] == "SEC" and rows[0][4] == "Electronics", str(rows[0]))

rows = M.to_rows(FakeDF([("005930", {"업종": "화학"})]),
                 "20240315", "KOSPI")
check("E4) '업종' 이라는 이름도 읽는다", rows[0][4] == "화학")

rows = M.to_rows(FakeDF([("005930", {})]), "20240315", "KOSPI")
check("E5) 업종이 없으면 빈칸이다 (메우지 않는다)", rows[0][4] == "")
check("E6) 이름이 없어도 빈칸이다", rows[0][2] == "")
check("E7) '기타' 로 채우지 않는다", rows[0][4] != "기타")
check("E8) 코드는 남는다 (빈칸이어도 행을 버리지 않는다)",
      rows[0][1] == "005930")

rows = M.to_rows(FakeDF([]), "20240315", "KOSPI")
check("E9) 빈 DF 면 빈 목록", rows == [])

rows = M.to_rows(FakeDF([(5930, {"종목명": "삼성전자"})]), "20240315", "KOSPI")
check("E10) 코드가 숫자로 와도 문자로 바꾼다", rows[0][1] == "5930",
      repr(rows[0][1]))

# =====================================================================
# F) append_rows - 중복은 안 늘고, 다른 날은 는다
#    (실제 data/ 를 건드리지 않게 DATA_DIR 를 임시로 바꾼다)
# =====================================================================
real_dir, real_sleep = M.DATA_DIR, M.SLEEP_SEC
tmp = tempfile.TemporaryDirectory()
M.DATA_DIR = pathlib.Path(tmp.name)
try:
    a = ["20240315", "005930", "삼성전자", "KOSPI", "전기전자"]
    b = ["20240315", "000660", "SK하이닉스", "KOSPI", "전기전자"]
    n = M.append_rows([a, b])
    check("F1) 두 행이 새로 들어갔다", n == 2, f"{n}행")

    path = M.DATA_DIR / "krx_sector_2024.csv"
    check("F2) 해별 파일이 생겼다", path.exists())
    with open(path, encoding="utf-8-sig", newline="") as fh:
        got = list(csv.DictReader(fh))
    check("F3) 헤더가 FIELDS 와 같다",
          list(got[0].keys()) == M.FIELDS, str(list(got[0].keys())))
    check("F4) 2행이다", len(got) == 2)

    n = M.append_rows([a, b])
    check("F5) 같은 것을 또 넣어도 0행", n == 0, f"{n}행")

    # 같은 종목, 다른 날 -> 들어가야 한다 (업종이 바뀐 것을 기록해야 하니까)
    c = ["20240617", "005930", "삼성전자", "KOSPI", "서비스업"]
    n = M.append_rows([c])
    check("F6) 같은 종목이라도 날짜가 다르면 들어간다", n == 1, f"{n}행")
    with open(path, encoding="utf-8-sig", newline="") as fh:
        got = list(csv.DictReader(fh))
    check("F7) 3행이 됐다", len(got) == 3)
    check("F8) 업종이 바뀐 것이 둘 다 남았다",
          {r["sector"] for r in got if r["code"] == "005930"}
          == {"전기전자", "서비스업"})

    # 다른 해 -> 다른 파일
    d = ["20250317", "005930", "삼성전자", "KOSPI", "전기전자"]
    M.append_rows([d])
    check("F9) 해가 다르면 파일이 갈린다",
          (M.DATA_DIR / "krx_sector_2025.csv").exists())
    check("F10) 2024 파일은 안 늘었다", len(got) == 3)

    check("F11) 빈 입력이면 0", M.append_rows([]) == 0)

    # existing_dates 가 두 파일을 다 읽나
    have = M.existing_dates()
    check("F12) 받은 날짜를 다 찾는다",
          have == {"20240315", "20240617", "20250317"}, str(sorted(have)))

    # =================================================================
    # G) fetch_one - 실패한 시장이 다른 시장을 막지 않는다
    # =================================================================
    table = {
        ("20240315", "KOSPI"): FakeDF([("005930", {"종목명": "삼성전자",
                                                   "업종명": "전기전자"})]),
        ("20240315", "KOSDAQ"): FakeDF([("035720", {"종목명": "카카오",
                                                    "업종명": "서비스업"})]),
    }
    st = FakeStock(table)
    M.SLEEP_SEC = 0               # 테스트에서는 안 쉰다
    rows, failed = M.fetch_one(st, "20240315")
    check("G1) 두 시장을 다 부른다", len(st.calls) == 2, str(st.calls))
    check("G2) 두 행이 나온다", len(rows) == 2, f"{len(rows)}행")
    check("G3) 실패 0", failed == 0)
    check("G4) 시장 이름이 행에 들어간다",
          {r[3] for r in rows} == {"KOSPI", "KOSDAQ"})

    st = FakeStock(table, fail=[("20240315", "KOSPI")])
    rows, failed = M.fetch_one(st, "20240315")
    check("G5) 한 시장이 실패해도 다른 시장은 받는다",
          len(rows) == 1 and rows[0][3] == "KOSDAQ", str(rows))
    check("G6) 실패 수를 센다", failed == 1)

    st = FakeStock({})
    rows, failed = M.fetch_one(st, "20240315")
    check("G7) 둘 다 None 이면 빈 목록이고 실패는 0 (빈 응답 != 오류)",
          rows == [] and failed == 0)
finally:
    M.DATA_DIR, M.SLEEP_SEC = real_dir, real_sleep
    tmp.cleanup()

# =====================================================================
# H) 실행 방식 - 매일 안 돌리고, 없으면 조용히 끝난다
# =====================================================================
check("H1) 매일 실행.bat 에 안 넣는다고 적었다",
      "매일 실행.bat 에 **안 넣는다.**" in src or "안 넣는다" in flat)
check("H2) 분기마다 한 번이면 된다고 적었다", "분기마다 한 번" in flat)
check("H3) 분기 달이 3/6/9/12 다", M.QUARTER_MONTHS == (3, 6, 9, 12))
check("H4) 분기 날이 15일이다", M.QUARTER_DAY == 15)
check("H5) 호출 사이에 쉬는 시간이 있다", M.SLEEP_SEC > 0,
      f"{M.SLEEP_SEC}초")
check("H6) KRX 로그인이 필요하다고 안내했다",
      "KRX_ID" in src and "KRX_PW" in src)
check("H7) 로그인이 없으면 다른 수집을 막지 않는다고 적었다",
      "다른 수집을 막지 않는다" in flat)

bat = REPO_ROOT / "매일 실행.bat"
if bat.exists():
    check("H8) 실제로 매일 실행.bat 에 없다",
          "fetch_krx_sector" not in bat.read_text(encoding="utf-8",
                                                  errors="replace"))

# 매일 실행.bat 에는 없지만 backup 대상에는 들어가야 한다
bk = (REPO_ROOT / "backup.py").read_text(encoding="utf-8")
check("H9) backup.py 가 krx_sector 를 챙긴다", "krx_sector" in bk)

# =====================================================================
# I) main - pykrx 가 없어도 안 터진다
# =====================================================================
saved = sys.modules.get("pykrx")
sys.modules["pykrx"] = None       # import 하면 실패하게 만든다
try:
    rc = M.main([])
    check("I1) pykrx 가 없으면 1을 돌려준다 (예외로 안 터진다)", rc == 1,
          f"rc={rc}")
finally:
    if saved is None:
        sys.modules.pop("pykrx", None)
    else:
        sys.modules["pykrx"] = saved

check("I2) --backfill 옵션이 있다", "--backfill" in src)
check("I3) --date 옵션이 있다", "--date" in src)
check("I4) 이미 받은 날짜는 건너뛴다", "이미 받은 것" in src)
check("I5) 0행이면 안내하고 1을 돌려준다",
      "저장된 행이 0입니다" in src)
check("I6) 무엇이 들어왔는지 보여준다 (10분봉 사고 교훈)",
      "지금까지 모인 업종" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
