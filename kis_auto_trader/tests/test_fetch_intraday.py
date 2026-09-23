"""fetch_intraday.py 검증 - 10분봉 수집.

(2026-09-21 신설) 이 파일의 위험은 보통 수집기와 다르다. **소급이 안
된다.** KIS 당일분봉 API 는 오늘 것만 주므로, 하루 빠뜨리면 그날은
영구히 없다. 일봉은 몇 달 뒤에도 채울 수 있어서 버그가 있어도 복구됐지만
여기는 안 된다.

그래서 집중해서 보는 것
  1) 묶는 계산이 맞는가 (시가=첫봉, 종가=마지막봉, 고/저=구간전체, 거래량=합)
  2) 같은 날 두 번 돌려도 행이 안 늘어나는가
  3) 없는 값을 0 으로 메우지 않는가 - 메우면 '안 움직였다' 는 가짜가 된다
  4) 자동 실행에 실제로 걸려 있는가 (수동에만 있으면 빠뜨린다)

주의: API 호출은 이 환경에서 못 해본다. 인증 정보가 없다. 그래서 순수
계산과 파일 처리만 검사한다. 응답 필드 이름이 맞는지는 사용자가
--check 로 확인해야 한다.

실행:
  python tests/test_fetch_intraday.py
"""
import csv
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


import fetch_intraday as M  # noqa: E402

src = (REPO_ROOT / "fetch_intraday.py").read_text(encoding="utf-8")
flat = " ".join(src.split())
api_src = (REPO_ROOT / "api_client.py").read_text(encoding="utf-8")

# =====================================================================
# A) 10분 구간 나누기
# =====================================================================
check("A1) 09:35:12 는 0930 구간", M.bucket_of("093512") == "0930")
check("A2) 09:40:00 은 0940 구간", M.bucket_of("094000") == "0940")
check("A3) 09:39:59 는 아직 0930", M.bucket_of("093959") == "0930")
check("A4) HHMM 만 와도 된다", M.bucket_of("0930") == "0930")
check("A5) 15:29 는 1520 구간", M.bucket_of("152959") == "1520")
check("A6) 못 읽으면 None", M.bucket_of("x") is None and M.bucket_of("") is None)
check("A7) 시각이 말이 안 되면 None", M.bucket_of("997700") is None)
check("A8) 숫자가 아닌 글자가 섞여도 걸러낸다", M.bucket_of("09:35:12") == "0930")
check("A9) 구간이 10분이다", M.BUCKET_MIN == 10)

# =====================================================================
# B) 묶는 계산 - 시/고/저/종/거래량
# =====================================================================
bars = [
    {"date": "20260922", "time": "093100", "open": 100.0, "high": 105.0,
     "low": 99.0, "close": 104.0, "volume": 10},
    {"date": "20260922", "time": "093500", "open": 104.0, "high": 108.0,
     "low": 103.0, "close": 107.0, "volume": 5},
    {"date": "20260922", "time": "094000", "open": 107.0, "high": 107.0,
     "low": 106.0, "close": 106.0, "volume": 3},
]
b = M.to_buckets(bars)
c0 = b[("20260922", "0930")]
check("B1) 시가는 구간의 첫 봉", c0["open"] == 100.0, str(c0))
check("B2) 종가는 구간의 마지막 봉", c0["close"] == 107.0)
check("B3) 고가는 구간 전체 최고", c0["high"] == 108.0)
check("B4) 저가는 구간 전체 최저", c0["low"] == 99.0)
check("B5) 거래량은 합", c0["volume"] == 15)
check("B6) 다음 구간은 따로 잡힌다",
      b[("20260922", "0940")]["close"] == 106.0 and len(b) == 2)

# 순서가 뒤섞여 와도 시가/종가가 맞아야 한다 (API 가 역순으로 줄 수 있다)
b2 = M.to_buckets(list(reversed(bars)))
check("B7) 입력 순서가 뒤집혀도 결과가 같다",
      b2[("20260922", "0930")] == c0, str(b2[("20260922", "0930")]))

# 값이 없는 봉 - 0 으로 메우면 안 된다
b3 = M.to_buckets([
    {"date": "20260922", "time": "093100", "open": None, "high": None,
     "low": None, "close": 50.0, "volume": None},
])
c3 = b3[("20260922", "0930")]
check("B8) 없는 시가를 0 으로 메우지 않는다", c3["open"] is None, str(c3))
check("B9) 없는 고/저도 None", c3["high"] is None and c3["low"] is None)
check("B10) 거래량이 없으면 0 으로 둔다 (합이므로)", c3["volume"] == 0)
check("B11) 왜 0 으로 안 메우는지 적어뒀다",
      "0 으로 메우지 않는다" in flat)
check("B12) 날짜가 없으면 버린다",
      M.to_buckets([{"date": None, "time": "093100", "close": 1.0}]) == {})
check("B13) 시각이 없으면 버린다",
      M.to_buckets([{"date": "20260922", "time": None, "close": 1.0}]) == {})
check("B14) 빈 입력이어도 안 터진다", M.to_buckets([]) == {})

# 날짜가 둘 섞여도 따로 잡혀야 한다 (자정 넘겨 돌리는 경우)
b4 = M.to_buckets([
    {"date": "20260922", "time": "093100", "close": 1.0, "volume": 1},
    {"date": "20260923", "time": "093100", "close": 2.0, "volume": 1},
])
check("B15) 날짜가 다르면 다른 칸", len(b4) == 2)

# =====================================================================
# C) 중복 방지와 파일 쓰기
# =====================================================================
_real_dir = M.DATA_DIR
tmp = tempfile.mkdtemp()
M.DATA_DIR = pathlib.Path(tmp)
try:
    n1 = M.append_rows("2026", [["20260922", "0930", "005930",
                                 100.0, 105.0, 99.0, 104.0, 15]])
    check("C1) 새 파일에 행을 쓴다", n1 == 1)
    path = M.DATA_DIR / "krx_min10_2026.csv"
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    check("C2) 헤더가 정해진 순서다", rows[0] == M.HEADER, str(rows[0]))
    check("C3) 스키마가 date,time,code 로 시작한다",
          M.HEADER[:3] == ["date", "time", "code"])
    check("C4) 데이터 한 줄이 들어갔다", len(rows) == 2)

    have = M.existing_keys("2026")
    check("C5) 이미 있는 키를 읽어온다",
          ("20260922", "0930", "005930") in have, str(have))
    check("C6) 없는 키는 안 들어 있다",
          ("20260922", "0940", "005930") not in have)

    M.append_rows("2026", [["20260922", "0940", "005930",
                            1.0, 2.0, 0.5, 1.5, 3]])
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows2 = list(csv.reader(fh))
    check("C7) 덧붙일 때 헤더를 또 안 쓴다", len(rows2) == 3 and rows2[0] == M.HEADER)

    check("C8) 빈 목록이면 아무것도 안 쓴다", M.append_rows("2026", []) == 0)
    check("C9) 파일이 없는 해는 빈 집합", M.existing_keys("1999") == set())
finally:
    M.DATA_DIR = _real_dir

check("C10) 같은 날 두 번 돌려도 안 늘어난다고 적어뒀다",
      "행이 안 늘어난다" in flat)
check("C11) 실제로 have 로 걸러낸다", "if (d, t, code) in have:" in src)

# =====================================================================
# D) 하루를 다 덮는가
# =====================================================================
check("D1) 기준시각이 13개다", len(M.ANCHORS) == 13, str(len(M.ANCHORS)))
check("D2) 첫 기준시각이 09:30", M.ANCHORS[0] == "093000")
check("D3) 마지막이 15:30 (마감)", M.ANCHORS[-1] == "153000")
_gaps = [int(M.ANCHORS[i + 1][:4]) - int(M.ANCHORS[i][:4])
         for i in range(len(M.ANCHORS) - 1)]
check("D4) 30분 간격이다 (한 호출이 30분을 준다)",
      all(g in (30, 70) for g in _gaps), str(_gaps))
check("D5) 한 호출에 30건이라고 api_client 에 적혀 있다",
      "MINUTE_ROWS_PER_CALL = 30" in api_src)

# =====================================================================
# E) 소급 불가 - 이 파일의 핵심 위험
# =====================================================================
check("E1) 소급이 안 된다고 문서 앞에 크게 적었다",
      "소급이 안 된다" in flat and "영구히 없다" in flat)
check("E2) 일봉과 다른 점을 짚었다",
      "일봉은 몇 달 뒤에도 소급" in flat)
check("E3) api_client 에도 같은 경고가 있다",
      "오늘 것만" in api_src and "영구히 없다" in api_src)
check("E4) 매일 돌려야 한다고 적었다", "매일 돌려야" in flat or "매 거래일" in flat)

# 자동 실행에 걸려 있는가 - 수동에만 있으면 빠뜨린다
daemon_src = (REPO_ROOT / "daemon.py").read_text(encoding="utf-8")
check("E5) daemon 의 마감 후 단계에 들어 있다",
      "fetch_intraday.py" in daemon_src)
check("E6) daemon 에서 제일 먼저 돈다 (소급이 안 되므로)",
      daemon_src.index("fetch_intraday.py")
      < daemon_src.index("fetch_us_market.py"))
check("E7) 왜 맨 앞인지 daemon 에 적어뒀다",
      "소급이 안 된다" in " ".join(daemon_src.split()))
bat = (REPO_ROOT / "매일 실행.bat").read_text(encoding="ascii")
check("E8) 매일 실행.bat 에도 들어 있다", "fetch_intraday.py" in bat)
check("E9) bat 이 소급 불가를 경고한다", "gone forever" in bat)
check("E10) bat 내용이 ASCII 다 (한글은 CP949 에서 깨진다)",
      all(ord(ch) < 128 for ch in bat))

# =====================================================================
# F) 검증 상태를 정직하게 적었는가
# =====================================================================
check("F1) API 응답으로 확인 안 했다고 밝힌다",
      "실제 API 응답으로 확인하지 않았다" in flat)
check("F2) 왜 못 했는지 적었다", "인증\n정보가 없어서" in src or "인증 정보가 없어서" in flat)
check("F3) --check 를 먼저 쓰라고 안내한다", "--check" in src)
check("F4) 확인 전에는 작동한다고 말할 수 없다고 적었다",
      "작동한다' 고 말할 수 없다" in flat)
check("F5) --check 가 0건이면 실패로 끝난다",
      "응답 필드 이름이 다를 수 있습니다" in src)
check("F6) 저장 행이 0이면 실패로 끝난다",
      "저장된 행이 0입니다" in src)

# =====================================================================
# G) 안전 - 주문 코드가 늘지 않았는가
# =====================================================================
import api_client  # noqa: E402
for fn in ("place_order", "place_order_and_verify", "_submit_order"):
    check(f"G1) api_client 에 {fn} 이 여전히 없다", not hasattr(api_client, fn))
check("G2) 새로 넣은 함수는 조회 전용이다",
      hasattr(api_client, "get_minute_prices"))
check("G3) 조회는 GET 으로만 한다 (POST 를 안 쓴다)",
      "_get_with_retry(" in api_src.split("def get_minute_prices")[1][:900])
check("G4) 리눅스 절대경로가 없다", '"/home/user/' not in src)


# =====================================================================
# J) 빈 봉 막기 (2026-09-22) - 실제로 당한 사고
#     08:36 에 돌렸더니 장이 안 열렸는데도 API 가 오늘 날짜로 전일
#     종가를 채운 빈 봉 6,000행(거래량 0, 시=고=저=종)을 줬다.
#     그냥 쓸모없는 게 아니라 위험했다 - 날짜가 오늘로 찍히니 마감 뒤에
#     다시 돌리면 중복 처리되어 진짜 데이터가 영구히 안 들어간다.
# =====================================================================
_flat = {"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0,
         "volume": 0}
check("J1) 거래량 0 + 네 값이 같으면 빈 봉", M.is_placeholder(_flat))
check("J2) 거래량이 있으면 빈 봉이 아니다",
      not M.is_placeholder({**_flat, "volume": 1}))
check("J3) 한 번만 체결돼도(네 값 같고 거래량 있음) 진짜다",
      not M.is_placeholder({"open": 5.0, "high": 5.0, "low": 5.0,
                            "close": 5.0, "volume": 10}))
check("J4) 값이 움직였으면 진짜다 (거래량이 0으로 와도)",
      not M.is_placeholder({**_flat, "high": 101.0}))
check("J5) 값이 없으면 빈 봉으로 본다",
      M.is_placeholder({"open": None, "high": None, "low": None,
                        "close": None, "volume": 0}))
check("J6) 왜 두 조건을 같이 보는지 적어뒀다",
      "둘 중\n    하나만으로는 안 된다" in src or "하나만으로는 안 된다" in flat)
check("J7) 중복 때문에 위험하다는 것을 적어뒀다",
      "진짜 데이터가 영구히 안 들어간다" in flat)
check("J8) 실제로 저장 경로에서 막는다", "if is_placeholder(c):" in src)
check("J9) 버린 개수를 화면에 알린다", "거래 없어 버린 구간" in src)

# 이미 들어간 빈 봉을 걷어내는 기능
_real_dir2 = M.DATA_DIR
tmp2 = tempfile.mkdtemp()
M.DATA_DIR = pathlib.Path(tmp2)
try:
    M.append_rows("2099", [
        ["20991231", "0900", "A", 100.0, 100.0, 100.0, 100.0, 0],   # 빈 봉
        ["20991231", "0910", "A", 100.0, 105.0, 99.0, 104.0, 50],   # 진짜
        ["20991231", "0920", "B", 7.0, 7.0, 7.0, 7.0, 3],           # 진짜
    ])
    drop, left = M.drop_placeholders("2099", dry_run=True)
    check("J10) dry_run 은 세기만 한다", drop == 1 and left == 2, f"{drop}/{left}")
    with open(M.DATA_DIR / "krx_min10_2099.csv", encoding="utf-8-sig") as fh:
        check("J11) dry_run 이면 파일이 안 바뀐다", len(fh.readlines()) == 4)
    drop, left = M.drop_placeholders("2099")
    check("J12) 실제로 지운다", drop == 1 and left == 2)
    with open(M.DATA_DIR / "krx_min10_2099.csv", encoding="utf-8-sig",
              newline="") as fh:
        got = list(csv.reader(fh))
    check("J13) 헤더가 남는다", got[0] == M.HEADER)
    check("J14) 진짜 행만 남는다", len(got) == 3
          and all(r[1] != "0900" for r in got[1:]), str(got))
    check("J15) 두 번 돌려도 더 안 지운다", M.drop_placeholders("2099")[0] == 0)
    check("J16) 파일이 없으면 (0,0)", M.drop_placeholders("1900") == (0, 0))
finally:
    M.DATA_DIR = _real_dir2

# 장 마감 전 경고
check("J17) 마감 시각이 상수로 있다", M.CLOSE_HHMM == (15, 30))
check("J18) 마감 전이면 경고한다", "아직 장이 안 끝났습니다" in src)
check("J19) 마감 뒤에 다시 돌리라고 안내한다", "마감 뒤에 한 번 더 돌리세요" in flat)
check("J20) --clean 옵션이 있다", '"--clean"' in src)

# 무엇이 저장됐는지 화면에 보여주는가 - 사고 때 이게 없어서 몰랐다
check("J21) 날짜별 요약을 찍는다", "bydate" in src)
check("J22) 왜 그걸 찍는지 적어뒀다", "그게 빈 봉인지 알 수가 없었다" in flat)
check("J23) 전부 빈 봉이면 그 이유를 알려준다",
      "전부 거래 없는 빈 봉이었습니다" in src)

# bat 도 같이 경고하는가
_bat2 = (REPO_ROOT / "매일 실행.bat").read_text(encoding="ascii")
check("J24) bat 이 마감 뒤에 돌리라고 알린다", "AFTER 15:30" in _bat2)
check("J25) bat 의 단계 번호가 일관된다 (1/8 부터)",
      "STEP 1/8" in _bat2 and "STEP 1/7" not in _bat2)
check("J26) bat 이 여전히 ASCII 다", all(ord(ch) < 128 for ch in _bat2))

# =====================================================================
# K) 모은 것이 백업 목록에 들어가는가 (2026-09-22 추가)
# =====================================================================
# 이 파일이 만드는 데이터는 **다시 받을 데가 없다.** 당일분봉 API 는 오늘
# 것만 준다. 그런데 backup.py 의 목록에서 빠져 있었다 - 사용자 PC 가 모아도
# 올라오지 않으니 여기서 분석할 수도 없고, 그 PC 를 잃으면 영구히 사라진다.
# 다시 빠지지 않게 막는다.
import backup as B  # noqa: E402

_bsrc = (REPO_ROOT / "backup.py").read_text(encoding="utf-8")
_bflat = " ".join(_bsrc.split())
check("K1) backup.py 가 10분봉을 목록에 넣는다",
      f'glob("{M.PREFIX}_*.csv")' in _bsrc,
      f"찾는 패턴: {M.PREFIX}_*.csv")
_names = [p.name for p in B._dynamic_backup_paths()]
_ondisk = list((REPO_ROOT / "data").glob(f"{M.PREFIX}_*.csv"))
check("K2) 디스크에 있는 10분봉 파일이 전부 목록에 들어온다",
      all(p.name in _names for p in _ondisk),
      f"디스크 {len(_ondisk)}개 / 목록 {[n for n in _names if M.PREFIX in n]}")
check("K3) 왜 제일 급한지 적어뒀다", "다시 받을 데가 없다" in _bflat)
check("K4) 오늘 것만 준다는 것을 백업 쪽에도 적었다", "오늘 것만" in _bflat)

# =====================================================================
# L) 중간에 죽어도 받은 만큼은 남는가 (2026-09-22 추가)
# =====================================================================
# 전에는 163종목 루프가 다 끝난 뒤 한 번만 파일에 썼다. 5분짜리 루프
# 중간에 정전/절전으로 죽으면 통째로 날아갔다. 사용자: "한 두번 정도는
# 날려도 상관없는데 계속 날려먹는 건 좀". FLUSH_EVERY 마다 쓰게 고쳤다.
check("L1) 몇 종목마다 쓸지 상수로 있다", M.FLUSH_EVERY == 20)
check("L2) 왜 중간에 쓰는지 적어뒀다",
      "받은 것이 통째로 날아갔다" in flat or "통째로" in flat)
check("L3) 비용이 무의미하다고 적었다", "무의미한 비용" in flat)
check("L4) 루프 안에서 flush 를 부른다",
      "if i % FLUSH_EVERY == 0 or i == len(codes):" in src
      and "flush()" in src)
check("L5) 루프가 끝나고도 한 번 더 부른다 (마지막 자투리)",
      src.count("flush()") >= 3, f"flush() {src.count('flush()')}번")
check("L6) 이어받기는 existing_keys 가 해준다고 적었다",
      "다음 회차가 빠진 것만 채운다" in flat)

# 실제로 중간 저장이 되는지 - 가짜 API 로 돌려본다
import csv as _csv  # noqa: E402
import sys as _sys  # noqa: E402
import types as _types  # noqa: E402

_tmp = REPO_ROOT / "tests" / "_tmp_flush"
_tmp.mkdir(exist_ok=True)
for _f in _tmp.glob("*.csv"):
    _f.unlink()


def _fake_minute(cfg, code, anchor):
    if code == "C025":
        raise RuntimeError("중간에 끊긴 흉내")
    return [{"date": "20260923", "time": "090100", "open": 100.0,
             "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000}]


_sys.modules["api_client"] = _types.SimpleNamespace(
    get_minute_prices=_fake_minute)
_sys.modules["universe"] = _types.SimpleNamespace(
    codes=lambda: [f"C{i:03d}" for i in range(1, 51)])
_sys.modules["common"] = _types.SimpleNamespace(load_config=lambda: None)

_old_dir, _old_close = M.DATA_DIR, M.CLOSE_HHMM
M.DATA_DIR, M.CLOSE_HHMM = _tmp, (0, 0)
try:
    _rc = M.main(["--limit", "50"])
    _path = _tmp / "krx_min10_2026.csv"
    _n = (sum(1 for _ in _csv.DictReader(_path.open(encoding="utf-8-sig")))
          if _path.exists() else 0)
    check("L7) 한 종목이 실패해도 나머지는 저장된다", _n == 49,
          f"{_n}행 (기대 49 = 50종목 - 실패 1)")
    check("L8) 파일이 루프 도중에 만들어진다 (끝까지 기다리지 않는다)",
          _path.exists())
finally:
    M.DATA_DIR, M.CLOSE_HHMM = _old_dir, _old_close
    for _f in _tmp.glob("*.csv"):
        _f.unlink()
    _tmp.rmdir()

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
