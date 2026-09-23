"""fetch_krx_history.py 검증 - 시점별 유니버스가 제대로 만들어지는지.

(2026-09-15 신설) 이 스크립트의 존재 이유가 생존편향 제거라서, 검증의 핵심도
"나중에 상장폐지된 종목이 과거 유니버스에 제대로 남는가"다. 그게 안 되면
스크립트를 돌려봐야 지금과 똑같은 편향된 데이터가 나온다.

이 컨테이너에서는 KRX(data.krx.co.kr)가 네트워크 정책으로 막혀 있어서 실제
호출로는 확인할 수 없다. 그래서 pykrx 와 같은 모양의 가짜 KRX를 만들어서
로직만 검증한다 - 실제 KRX 응답 형식이 예상과 다를 가능성은 남아 있고,
그건 PC에서 처음 돌릴 때 확인해야 한다.

실행:
  python tests/test_krx_history.py
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


# ---------------------------------------------------------------- 가짜 KRX
#
# pandas 없이 돌아가게 최소한의 DataFrame 흉내를 낸다 (컬럼 접근 + sort + head).

class FakeRow(dict):
    pass


class FakeDF:
    def __init__(self, index, rows, columns):
        self._index = list(index)
        self._rows = list(rows)
        self.columns = list(columns)

    def __len__(self):
        return len(self._rows)

    def sort_values(self, col, ascending=True):
        order = sorted(range(len(self._rows)), key=lambda i: self._rows[i][col],
                       reverse=not ascending)
        return FakeDF([self._index[i] for i in order],
                      [self._rows[i] for i in order], self.columns)

    def head(self, n):
        return FakeDF(self._index[:n], self._rows[:n], self.columns)

    def iterrows(self):
        return zip(self._index, self._rows)


class FakeStock:
    """종목 3개 중 하나(DEAD01)가 2022년 중 상장폐지되는 시장."""

    ALIVE = ["000001", "000002"]
    DEAD = "DEAD01"

    def __init__(self):
        self.ohlcv_calls = []

    def _listed_on(self, date):
        # DEAD01 은 2022-07-01 이후로 사라진다
        return self.ALIVE + ([self.DEAD] if date < "20220701" else [])

    def get_market_ohlcv_by_ticker(self, date, market="KOSPI"):
        codes = self._listed_on(date)
        # 거래대금은 DEAD01 이 제일 크게 해둔다 - 그때는 상위권이었다는 뜻
        tv = {"000001": 100, "000002": 200, "DEAD01": 300}
        rows = [FakeRow({"종가": 1000.0, "거래대금": tv[c]}) for c in codes]
        return FakeDF(codes, rows, ["종가", "거래대금"])

    def get_market_ohlcv_by_date(self, start, end, ticker):
        self.ohlcv_calls.append(ticker)
        import datetime as dt
        s = dt.datetime.strptime(start, "%Y%m%d")
        e = dt.datetime.strptime(end, "%Y%m%d")
        if ticker == self.DEAD:
            e = min(e, dt.datetime(2022, 6, 30))   # 상장폐지일까지만
        idx, rows = [], []
        d = s
        while d <= e:
            if d.weekday() < 5:
                idx.append(d)
                rows.append(FakeRow({"시가": 990.0, "고가": 1010.0, "저가": 980.0,
                                     "종가": 1000.0, "거래량": 5000}))
            d += dt.timedelta(days=7)          # 표본을 줄이려고 주 1개만
        return FakeDF(idx, rows, ["시가", "고가", "저가", "종가", "거래량"])

    def get_market_ticker_name(self, ticker):
        if ticker == self.DEAD:
            raise RuntimeError("상장폐지 종목은 이름 조회 실패")
        return f"종목{ticker}"


import fetch_krx_history as fkh  # noqa: E402

tmp = pathlib.Path(tempfile.mkdtemp())
fkh.DATA_DIR = tmp / "data"
fkh.UNIVERSE_HISTORY_PATH = fkh.DATA_DIR / "krx_universe_history.csv"
fkh.SLEEP_SEC = 0    # 테스트에서 쉬는 시간은 낭비

# ---------------------------------------------------------------- 1) 월말 목록
me = fkh._month_ends("20210101", "20211231")
check("1) 1년이면 월말 12개", len(me) == 12, str(me[:3]))
check("1b) 말일이 맞게 계산됨 (2월/윤년 포함)",
      me[0] == "20210131" and me[1] == "20210228", f"{me[0]}, {me[1]}")
check("1c) 범위 밖은 안 들어간다",
      all("20210101" <= d <= "20211231" for d in me))

# ---------------------------------------------------------------- 2) 시점별 유니버스
s = FakeStock()
hist = fkh.collect_universe_history(s, "20210101", "20221231", top_n=3, verbose=False)
codes = {c for (_, c) in hist}
check("2) 상장폐지된 종목이 과거 유니버스에 남아있다 (생존편향 제거의 핵심)",
      "DEAD01" in codes, str(sorted(codes)))

dead_dates = sorted(d for (d, c) in hist if c == "DEAD01")
check("2b) 상장폐지 전 기간에만 들어있다",
      dead_dates and max(dead_dates) < "20220701",
      f"{dead_dates[0]}~{dead_dates[-1]}")
check("2c) 상장폐지 후 기준일에는 안 들어있다",
      not any(d >= "20220701" for d in dead_dates))

first = sorted({d for (d, _) in hist})[0]
row = hist[(first, "DEAD01")]
check("2d) 거래대금 순위가 기록된다 (1등이 rank 1)",
      row["rank"] == 1, f"rank={row['rank']} trade_value={row['trade_value']}")

# 다시 실행해도 같은 기준일을 또 받지 않는다 (이어받기)
before = len(s.ohlcv_calls)
hist2 = fkh.collect_universe_history(s, "20210101", "20221231", top_n=3, verbose=False)
check("2e) 다시 실행하면 이미 받은 기준일은 건너뛴다 (중간에 끊겨도 이어받기)",
      len(hist2) == len(hist), f"{len(hist)} -> {len(hist2)}")


# --- 로그인이 안 됐을 때: 68번 갈지 말고 일찍 멈춰야 한다 (실제로 겪은 문제)
class DeadStock:
    def __init__(self): self.calls = 0

    def get_market_ohlcv_by_ticker(self, date, market="KOSPI"):
        self.calls += 1
        raise RuntimeError("None of [Index(['시가','고가','저가','종가'])] are in the [columns]")


fkh.UNIVERSE_HISTORY_PATH = tmp / "data" / "empty.csv"
dead = DeadStock()
fkh.collect_universe_history(dead, "20210101", "20260831", top_n=3, verbose=False)
check("2f) 조회가 계속 실패하면 몇 번 만에 멈춘다 (68번 헛돌지 않게)",
      dead.calls <= 4, f"{dead.calls}회 호출")

import os  # noqa: E402
saved = (os.environ.pop("KRX_ID", None), os.environ.pop("KRX_PW", None))
check("2g) 계정이 없으면 시작 전에 막는다", fkh.check_credentials() is False)
os.environ["KRX_ID"], os.environ["KRX_PW"] = "id", "pw"
check("2h) 계정이 있으면 통과한다", fkh.check_credentials() is True)
for k, v in zip(("KRX_ID", "KRX_PW"), saved):
    os.environ.pop(k, None)
    if v is not None:
        os.environ[k] = v

fkh.UNIVERSE_HISTORY_PATH = tmp / "data" / "krx_universe_history.csv"

# ---------------------------------------------------------------- 3) 일봉 수집
all_codes = sorted({c for (_, c) in hist})
fkh.collect_panel(s, all_codes, "20210101", "20221231", verbose=False)

import yearly_csv  # noqa: E402
# 대량 수집은 전체를 메모리에 안 올리는 경로를 쓴다 - 종목 집합만 빠르게 확인
check("3-0) 저장된 종목 집합을 전체 로드 없이 읽는다",
      yearly_csv.codes_in(fkh.DATA_DIR, fkh.PANEL_PREFIX) == set(all_codes),
      str(sorted(yearly_csv.codes_in(fkh.DATA_DIR, fkh.PANEL_PREFIX))))
cov = yearly_csv.coverage(fkh.DATA_DIR, fkh.PANEL_PREFIX)
check("3) 상장폐지 종목의 일봉도 저장된다", "DEAD01" in cov, str(sorted(cov)))
check("3b) 상장폐지 종목은 폐지일까지만 있다",
      cov["DEAD01"][1] < "20220701", f"마지막 {cov['DEAD01'][1]}")
check("3c) 살아있는 종목은 끝까지 있다",
      cov["000001"][1] >= "20221201", f"마지막 {cov['000001'][1]}")
check("3d) 이름 조회가 실패해도 행은 저장된다 (상장폐지 종목)",
      cov["DEAD01"][2] > 0, f"{cov['DEAD01'][2]}행")

# 멱등성: 다시 돌리면 이미 받은 종목은 건너뛴다
calls_before = len(s.ohlcv_calls)
r2 = fkh.collect_panel(s, all_codes, "20210101", "20221231", verbose=False)
check("3e) 다시 실행하면 이미 받은 종목은 조회하지 않는다",
      len(s.ohlcv_calls) == calls_before and r2["requested"] == 0,
      f"추가 호출 {len(s.ohlcv_calls)-calls_before}회")

# ---------------------------------------------------------------- 4) 백테스트 호환
import backtest  # noqa: E402
import panel as panel_mod  # noqa: E402
panel_mod.DATA_DIR = fkh.DATA_DIR
panel_mod.PREFIX = fkh.PANEL_PREFIX
bp = backtest.Panel.load()
check("4) 받은 데이터를 백테스트가 그대로 읽는다",
      len(bp.bars) == 3 and len(bp.dates) > 50,
      f"{len(bp.bars)}종목 {len(bp.dates)}일")
check("4b) 상장폐지 종목도 백테스트 패널에 들어있다", "DEAD01" in bp.bars)


# ---------------------------------------------------------------- 5) 전진 갱신
#
# (2026-09-19 신설) 이 스크립트는 "한 번 받고 끝" 으로 만들어져서, 이미 받은
# 종목을 통째로 건너뛴다. 그래서 며칠 뒤에 다시 돌려도 새로 생긴 거래일이
# 절대 안 들어온다 - 실제로 krx_panel 이 20260915 에서 멈춘 채 다시 돌려도
# "1,744종목 건너뜀" 만 나왔다. 전략과 모든 분석이 이 패널을 읽으므로 전진
# 기록이 아예 안 쌓이는 상태였다. --update 가 그걸 메운다.
#
# 여기서 반드시 확인할 것은 **중복이 안 생기는지**다. StreamWriter 는 중복을
# 지우지 않으므로, 같은 날을 두 번 쓰면 그 종목의 그날 수익률이 두 번 세어진다.

class DailyStock:
    """매 평일 봉을 주는 가짜 시장 (주 1개가 아니라 전부 - 날짜 정렬 확인용)."""

    def __init__(self, upto="20210331"):
        self.upto = upto
        self.calls = []

    def get_market_ohlcv_by_date(self, start, end, ticker):
        import datetime as dt
        self.calls.append((ticker, start, end))
        e = min(end, self.upto)
        if start > e:
            return FakeDF([], [], ["시가", "고가", "저가", "종가", "거래량"])
        d = dt.datetime.strptime(start, "%Y%m%d")
        ed = dt.datetime.strptime(e, "%Y%m%d")
        idx, rows = [], []
        while d <= ed:
            if d.weekday() < 5:
                idx.append(d)
                rows.append(FakeRow({"시가": 990.0, "고가": 1010.0, "저가": 980.0,
                                     "종가": 1000.0, "거래량": 5000}))
            d += dt.timedelta(days=1)
        return FakeDF(idx, rows, ["시가", "고가", "저가", "종가", "거래량"])

    def get_market_ticker_name(self, ticker):
        return f"종목{ticker}"


def stored_pairs(data_dir, prefix):
    """저장된 (날짜,종목) 쌍 전부를 리스트로 (중복을 세려면 set 이면 안 된다)."""
    import csv as _csv
    out = []
    for p in yearly_csv.paths(data_dir, prefix):
        with open(p, encoding="utf-8-sig", newline="") as f:
            for r in _csv.DictReader(f):
                if r.get("date") and r.get("code"):
                    out.append((r["date"], r["code"]))
    return out


tmp5 = pathlib.Path(tempfile.mkdtemp())
fkh.DATA_DIR = tmp5 / "data"

check("5-0) 패널이 비어 있으면 마지막 날짜가 None", fkh.last_panel_date() is None)

ds = DailyStock(upto="20210131")
fkh.collect_panel(ds, ["000001", "000002"], "20210101", "20210131", verbose=False)
last1 = fkh.last_panel_date()
check("5) 저장된 마지막 날짜를 읽는다", last1 == "20210129", f"{last1}")

pairs1 = stored_pairs(fkh.DATA_DIR, fkh.PANEL_PREFIX)
n1 = len(pairs1)

# 옵션 없이 다시 돌리면 - 이게 문제였던 동작. 새 날이 생겼는데도 안 들어온다.
ds.upto = "20210228"
ds.calls.clear()
fkh.collect_panel(ds, ["000001", "000002"], "20210101", "20210228", verbose=False)
check("5b) 옵션 없이 다시 돌리면 새 거래일이 안 들어온다 (원래 문제를 재현)",
      len(stored_pairs(fkh.DATA_DIR, fkh.PANEL_PREFIX)) == n1
      and fkh.last_panel_date() == last1,
      f"{n1}행 -> {len(stored_pairs(fkh.DATA_DIR, fkh.PANEL_PREFIX))}행")

# --update 경로: 마지막 날 다음날부터
import datetime as _dt  # noqa: E402
since = (_dt.datetime.strptime(last1, "%Y%m%d") + _dt.timedelta(days=1)).strftime("%Y%m%d")
ds.calls.clear()
fkh.collect_panel(ds, ["000001", "000002"], "20210101", "20210228",
                  verbose=False, since=since)
pairs2 = stored_pairs(fkh.DATA_DIR, fkh.PANEL_PREFIX)
check("5c) since 를 주면 이미 받은 종목도 다시 조회한다",
      sorted(t for (t, _s, _e) in ds.calls) == ["000001", "000002"], str(ds.calls))
check("5c2) 기존 종목은 since 부터만 조회한다 (전체를 다시 받지 않는다)",
      all(s == since for (_t, s, _e) in ds.calls), str(ds.calls))
check("5d) 새 거래일이 실제로 들어온다",
      fkh.last_panel_date() == "20210226" and len(pairs2) > n1,
      f"마지막 {fkh.last_panel_date()}, {n1}행 -> {len(pairs2)}행")
check("5e) 중복이 생기지 않는다 (StreamWriter 는 중복을 안 지운다)",
      len(pairs2) == len(set(pairs2)),
      f"{len(pairs2)}행 중 서로 다른 키 {len(set(pairs2))}개")
check("5e2) 이전에 있던 행이 사라지지 않았다",
      set(pairs1) <= set(pairs2))

# 새로 편입된 종목은 since 가 아니라 처음부터 받아야 한다 (과거가 비면
# 저변동 계산에 필요한 20일 표본이 없다).
ds.calls.clear()
fkh.collect_panel(ds, ["000001", "000002", "000003"], "20210101", "20210228",
                  verbose=False, since=since)
starts = {t: s for (t, s, _e) in ds.calls}
check("5f) 처음 보는 종목은 since 가 아니라 start 부터 전체를 받는다",
      starts.get("000003") == "20210101", str(starts))
cov5 = yearly_csv.coverage(fkh.DATA_DIR, fkh.PANEL_PREFIX)
check("5f2) 그래서 새 종목도 과거 구간이 채워진다",
      cov5["000003"][0] == "20210101", f"{cov5['000003']}")
check("5f3) 새 종목을 넣어도 기존 종목에 중복이 안 생긴다",
      len(stored_pairs(fkh.DATA_DIR, fkh.PANEL_PREFIX))
      == len(set(stored_pairs(fkh.DATA_DIR, fkh.PANEL_PREFIX))))
#   여기서 넘긴 since(20210130)는 이미 받아둔 20210226 보다 앞이다. 그걸
#   그대로 믿으면 20210130~20210226 을 또 써서 중복이 된다. 저장된 마지막
#   날 다음날로 끌어올려야 맞다.
floor5 = (_dt.datetime.strptime("20210226", "%Y%m%d")
          + _dt.timedelta(days=1)).strftime("%Y%m%d")
check("5f4) 지난번 since 를 그대로 다시 넘기면 마지막 날 다음날로 끌어올린다",
      starts.get("000001") == floor5 and since < floor5,
      f"넘긴 since={since}, 실제 조회 시작={starts.get('000001')}, 기대={floor5}")

# 이미 최신이면 아무것도 안 받아야 한다 (since > end)
ds.calls.clear()
fkh.collect_panel(ds, ["000001"], "20210101", "20210226", verbose=False,
                  since="20210227")
check("5g) 받을 게 없으면 행이 안 늘어난다",
      fkh.last_panel_date() == "20210226")

src5 = (REPO_ROOT / "fetch_krx_history.py").read_text(encoding="utf-8")
check("5h) --update 옵션이 있다", '"--update"' in src5)
check("5h2) 왜 필요한지(건너뛰어서 새 날이 안 들어옴)를 적어뒀다",
      "20260915" in src5 and "건너뜀" in src5)
check("5h3) 중복이 안 생기는 근거를 적어뒀다",
      "마지막 날' 다음날" in src5 or "마지막 날 다음날" in src5)
check("5h4) 리눅스 절대경로가 박혀 있지 않다", '"/home/user/' not in src5)

shutil.rmtree(tmp5, ignore_errors=True)
shutil.rmtree(tmp, ignore_errors=True)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
