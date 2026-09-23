"""fetch_krx_extra.py 검증 - 수급/재무/시가총액 수집.

(2026-09-15 신설) 이 컨테이너는 KRX 가 네트워크 정책으로 막혀 있어(403) 실제
호출로 확인할 수 없다. pykrx 와 같은 모양의 가짜 KRX로 로직만 검증한다.
실제 응답 형식이 다를 가능성은 남아 있고, PC에서 --limit 3 으로 먼저 확인해야 한다.

특히 확인하는 것:
  - pykrx 반환 컬럼(기관합계/외국인합계/PER/PBR/시가총액 ...)이 우리 컬럼으로
    제대로 옮겨지는가. 지난번에 컬럼 문제로 68번 헛돌았다.
  - 예상한 컬럼이 없을 때 조용히 넘어가지 않고 알리는가.
  - 이어받기가 되는가.

실행:
  python tests/test_krx_extra.py
"""
import pathlib
import shutil
import sys
import tempfile
import datetime as dt

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


class FakeDF:
    def __init__(self, index, rows, columns):
        self._index, self._rows, self.columns = list(index), list(rows), list(columns)

    def __len__(self):
        return len(self._rows)

    def iterrows(self):
        return zip(self._index, self._rows)


def make_df(cols, n=5):
    idx = [dt.datetime(2021, 1, 4) + dt.timedelta(days=i) for i in range(n)]
    rows = [{c: (i + 1) * 100 for c in cols} for i in range(n)]
    return FakeDF(idx, rows, cols)


class FakeStock:
    def __init__(self):
        self.calls = []

    def get_market_trading_value_by_date(self, s, e, t, **kw):
        self.calls.append(("flow", t))
        return make_df(["기관합계", "기타법인", "개인", "외국인합계", "전체"])

    def get_market_fundamental_by_date(self, s, e, t, **kw):
        self.calls.append(("fund", t))
        return make_df(["BPS", "PER", "PBR", "EPS", "DIV", "DPS"])

    def get_market_cap_by_date(self, s, e, t, **kw):
        self.calls.append(("cap", t))
        return make_df(["시가총액", "거래량", "거래대금", "상장주식수"])


import fetch_krx_extra as fke  # noqa: E402
import yearly_csv  # noqa: E402

tmp = pathlib.Path(tempfile.mkdtemp())
fke.DATA_DIR = tmp / "data"
fke.UNIVERSE_HISTORY_PATH = fke.DATA_DIR / "krx_universe_history.csv"
fke.SLEEP_SEC = 0
fke.RETRY_SLEEP_SEC = 0

CODES = ["000001", "000002", "000003"]
s = FakeStock()

# ---------------------------------------------------------------- 1) 수급
fke.collect(s, "flow", CODES, "20210101", "20210108", verbose=False)
rows = yearly_csv.load_rows(fke.DATA_DIR, "krx_flow")
check("1) 수급 3종목이 저장된다", len({c for _, c in rows}) == 3, str(sorted({c for _, c in rows})))
one = next(iter(rows.values()))
check("1b) 기관/개인/외국인 컬럼이 값으로 옮겨진다",
      one["inst"] and one["indiv"] and one["foreign"],
      f"inst={one['inst']} indiv={one['indiv']} foreign={one['foreign']}")
check("1c) 우리 컬럼 이름으로 저장된다 (pykrx 한글 컬럼 아님)",
      set(one) >= {"date", "code", "inst", "corp", "indiv", "foreign"}, str(sorted(one)))

# ---------------------------------------------------------------- 2) 재무/시총
fke.collect(s, "fundamental", CODES, "20210101", "20210108", verbose=False)
f1 = next(iter(yearly_csv.load_rows(fke.DATA_DIR, "krx_fund").values()))
check("2) PER/PBR/BPS 가 저장된다", f1["per"] and f1["pbr"] and f1["bps"],
      f"per={f1['per']} pbr={f1['pbr']}")

fke.collect(s, "cap", CODES, "20210101", "20210108", verbose=False)
c1 = next(iter(yearly_csv.load_rows(fke.DATA_DIR, "krx_cap").values()))
check("2b) 시가총액/상장주식수가 저장된다", c1["market_cap"] and c1["shares"],
      f"cap={c1['market_cap']} shares={c1['shares']}")

# ---------------------------------------------------------------- 3) 이어받기
before = len(s.calls)
fke.collect(s, "flow", CODES, "20210101", "20210108", verbose=False)
check("3) 이미 받은 종목은 다시 조회하지 않는다",
      len(s.calls) == before, f"추가 호출 {len(s.calls)-before}회")


# ---------------------------------------------------------------- 4) 컬럼이 다르면 알림
class WrongCols(FakeStock):
    def get_market_trading_value_by_date(self, st, e, t, **kw):
        return make_df(["엉뚱한컬럼", "전체"])


import io  # noqa: E402
import contextlib  # noqa: E402
fke.DATA_DIR = tmp / "data2"
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    fke.collect(WrongCols(), "flow", ["999999"], "20210101", "20210108", verbose=True)
out = buf.getvalue()
check("4) 예상한 컬럼이 없으면 조용히 넘어가지 않고 알린다",
      "예상한 컬럼이 없습니다" in out and "엉뚱한컬럼" in out, out.strip()[:90])
w = next(iter(yearly_csv.load_rows(fke.DATA_DIR, "krx_flow").values()))
check("4b) 없는 값은 빈칸으로 남는다 (임의로 채우지 않음)",
      w["inst"] == "" and w["foreign"] == "", f"inst={w['inst']!r}")


# ---------------------------------------------------------------- 5) 연속 실패 시 중단
class Dead:
    def __init__(self): self.n = 0

    def get_market_trading_value_by_date(self, *a, **kw):
        self.n += 1
        raise RuntimeError("로그인 안 됨")


fke.DATA_DIR = tmp / "data3"
d = Dead()
with contextlib.redirect_stdout(io.StringIO()):
    fke.collect(d, "flow", [f"{i:06d}" for i in range(1813)], "20210101", "20210108", verbose=False)
# 종목마다 한 번 재시도하므로 호출 수는 실패 종목 수의 두 배다.
check("5) 처음부터 전부 실패하면 1,813개를 다 돌지 않고 멈춘다",
      d.n <= fke.ABORT_STREAK_COLD * 2 + 2, f"{d.n}회 호출")


# --- (2026-09-19 추가) 실패가 두 종류인데 하나로 묶여 있었다.
#
#     설정이 틀린 경우와 일시적 오류를 같은 기준(연속 5회)으로 끊고,
#     둘 다 "계정 문제" 안내를 찍었다. 실제로 재무 수집이 29종목에서
#     멈춰 있었는데 계정은 멀쩡했다 - 같은 계정으로 수급 1,707종목을
#     받았다. 25분짜리 수집이 일시적 오류 5번에 통째로 날아가면 안 된다.

class FlakyAfterSome:
    """앞쪽 몇 종목은 성공하고, 그 뒤로 계속 실패한다."""

    def __init__(self, good=8):
        self.good, self.n = good, 0

    def get_market_trading_value_by_date(self, st, e, t, **kw):
        self.n += 1
        if self.n <= self.good:
            return make_df(["기관합계", "기타법인", "개인", "외국인합계"])
        raise RuntimeError("일시적인 오류")


fke.DATA_DIR = tmp / "data3b"
fl = FlakyAfterSome(good=8)
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    fke.collect(fl, "flow", [f"{i:06d}" for i in range(400)],
                "20210101", "20210108", verbose=False)
warm_out = buf2.getvalue()
check("5b) 이미 받은 게 있으면 5회에서 멈추지 않는다 (일시적 오류)",
      fl.n > fke.ABORT_STREAK_COLD * 2 + 8,
      f"{fl.n}회 호출 (COLD 기준이면 {fke.ABORT_STREAK_COLD*2+8}회에서 멈췄을 것)")
check("5c) 그래도 끝없이 돌지는 않는다 (WARM 기준에서 멈춘다)",
      fl.n < 400, f"{fl.n}회 호출")
check("5d) 그 경우 계정 문제라고 안내하지 않는다",
      "계정 문제는 아닙니다" in warm_out and "회원가입" not in warm_out,
      warm_out.strip()[-120:])
check("5e) 다시 실행하면 이어받는다고 안내한다",
      "이어서 받습니다" in warm_out)
check("5f) 한 종목도 못 받았을 때만 계정 안내를 한다",
      fke.ABORT_STREAK_COLD < fke.ABORT_STREAK_WARM,
      f"COLD {fke.ABORT_STREAK_COLD} < WARM {fke.ABORT_STREAK_WARM}")


# --- 일시적 오류 한 번은 재시도해서 종목을 잃지 않아야 한다
class FailsOnce:
    def __init__(self):
        self.seen, self.n = {}, 0

    def get_market_trading_value_by_date(self, st, e, t, **kw):
        self.n += 1
        self.seen[t] = self.seen.get(t, 0) + 1
        if self.seen[t] == 1:
            raise RuntimeError("한 번만 삐끗")
        return make_df(["기관합계", "기타법인", "개인", "외국인합계"])


fke.DATA_DIR = tmp / "data3c"
fo = FailsOnce()
with contextlib.redirect_stdout(io.StringIO()):
    fke.collect(fo, "flow", ["000001", "000002"], "20210101", "20210108",
                verbose=False)
got = {c for _d, c in yearly_csv.load_rows(fke.DATA_DIR, "krx_flow")}
check("5g) 한 번 삐끗한 종목도 재시도해서 받아낸다", got == {"000001", "000002"},
      str(sorted(got)))

# ---------------------------------------------------------------- 6) 유니버스 읽기
fke.DATA_DIR = tmp / "data4"
fke.DATA_DIR.mkdir(parents=True)
fke.UNIVERSE_HISTORY_PATH = fke.DATA_DIR / "krx_universe_history.csv"
fke.UNIVERSE_HISTORY_PATH.write_text(
    "date,code,name,trade_value,rank\n20210131,000001,가,100,1\n"
    "20210131,000002,나,90,2\n20210228,000001,가,80,1\n", encoding="utf-8-sig")
check("6) 유니버스 파일에서 종목 목록을 중복 없이 읽는다",
      fke.universe_codes() == ["000001", "000002"], str(fke.universe_codes()))


# ---------------------------------------------------------------- 7) main 의 성패 판정
#
# (2026-09-19 추가) 실제로 겪은 문제. 형식 확인(--limit 3)이 유니버스 앞에서
# 3종목을 잘랐는데 그게 이미 받아둔 종목이라 "0종목 받습니다" 로 끝났고,
# main 이 그걸 "한 종목도 못 받았습니다" 로 돌려줘서 .bat 가 멈췄다.
# 로그인도 수집도 멀쩡한데 실패로 보고한 것이다.
#
#   받을 게 없어서 0   <- 성공 (할 일이 없었을 뿐)
#   전부 실패해서 0    <- 실패
# 이 둘을 갈라야 한다.

src_extra = (REPO_ROOT / "fetch_krx_extra.py").read_text(encoding="utf-8")
check("7) 요청 수를 따로 세어서 성패를 가른다", "total_req" in src_extra)
check("7b) 받을 게 없으면 성공으로 끝난다 (0 을 돌려준다)",
      "if total_req == 0:" in src_extra
      and src_extra.split("if total_req == 0:")[1].split("return")[1].lstrip().startswith("0"))
check("7c) 요청이 있었는데 못 받았을 때만 실패다",
      "요청한 종목을 한 개도 못 받았습니다" in src_extra)
check("7d) 왜 갈랐는지 적어뒀다",
      "받을 게 없어서 0" in src_extra and "전부 실패해서 0" in src_extra)

# --limit 이 '아직 안 받은' 종목에서 골라야 형식 확인이 뜻을 가진다
check("7e) --limit 은 아직 안 받은 종목 중에서 고른다",
      "fresh = [c for c in codes if c not in have]" in src_extra)
check("7f) 그 이유를 적어뒀다",
      "확인하려던 것" in src_extra and "하나도 확인하지 못한다" in src_extra)
check("7g) 안 받은 종목이 아예 없으면 확인할 게 없다고 알린다",
      "안 받은 종목이 없습니다" in src_extra)


# ---------------------------------------------------------------- 8) 걸리는 시간 안내
#
# (2026-09-20 추가) 원래 문서와 화면 안내가 "5,439회 호출, 70분" 이었는데
# SLEEP_SEC 만 곱한 값이라 실제의 1/50 이었다. 사용자가 25분인 줄 알고
# 돌렸다가 밤새 돌았다. 시간을 정하는 건 호출 횟수가 아니라 받아오는
# 양이다 - 종목당 5.7년치(약 1,340행)를 받으므로 20초쯤 걸린다.

check("8) 실측 단가가 상수로 박혀 있다", hasattr(fke, "SEC_PER_CODE"))
# 이 테스트가 위에서 fke.SLEEP_SEC 를 0 으로 덮어썼으므로, 그 값과
# 비교하면 "20.2 > 0" 이라는 뜻 없는 검사가 된다. 실제 기본값을 읽어온다.
import fetch_krx_history as _fkh  # noqa: E402
check("8b) 그 값이 쉬는 시간보다 훨씬 크다 (응답 시간이 지배한다)",
      fke.SEC_PER_CODE > _fkh.SLEEP_SEC * 10,
      f"{fke.SEC_PER_CODE}초 vs 실제 SLEEP_SEC {_fkh.SLEEP_SEC}초")
check("8c) 1,813종목 한 종류가 몇 시간 단위로 계산된다",
      1813 * fke.SEC_PER_CODE / 3600 > 5,
      f"{1813 * fke.SEC_PER_CODE / 3600:.1f}시간")
check("8d) 예상 시간을 SLEEP_SEC 로 계산하지 않는다",
      "SLEEP_SEC / 60" not in src_extra)
check("8e) 왜 틀렸었는지 적어뒀다",
      "호출 횟수가 아니라 받아오는 양이 시간을 정한다" in " ".join(src_extra.split()))
check("8f) 70분이라는 옛 값이 남아 있지 않다", "70분 안팎" not in src_extra)

# .bat 안내도 같이 고쳤는지 (사용자가 실제로 보는 것은 이쪽이다)
bat = (REPO_ROOT / "KRX 데이터 수집.bat").read_text(encoding="utf-8")
check("8g) bat 안내도 25분이라고 하지 않는다", "about 25 minutes" not in bat)
check("8h) bat 이 몇 시간 걸린다고 알린다", "10 HOURS" in bat or "10 hours" in bat)

shutil.rmtree(tmp, ignore_errors=True)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
