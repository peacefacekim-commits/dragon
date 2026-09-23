"""10분봉 수집 - 장 마감 뒤에 그날 분봉을 받아 쌓는다.

(2026-09-21 신설) 사용자: "그럼 내일부터 10분 씩 거래를 기록하자."

===========================================================================
왜 이게 필요한가
===========================================================================
이 저장소의 패널은 일봉이다. 그래서 10분 매매를 채점할 방법이 없었다.
analyze_intraday.py 가 시/고/저/종으로 '되돌림을 잡으려면 최소 몇 %를
먹어야 하나' 같은 상한만 따져본 게 한계였다.

사용자의 원래 방식이 10분 단위 단기매매였고, 며칠 계속 손해가 나서
'어떤 조건을 붙이면 승률이 오르나' 를 묻고 있다. 그 질문은 분 단위
가격 없이는 답이 안 나온다. 그래서 지금부터 모은다.

===========================================================================
제일 중요한 제약 - 소급이 안 된다
===========================================================================
KIS 당일분봉 API 는 **오늘 것만** 준다. 과거 분봉을 나중에 받아올
방법이 없다.

  => 하루를 빠뜨리면 그날 데이터는 영구히 없다.
  => 매 거래일 장 마감 뒤에 반드시 돌려야 한다.
  => 그래서 daemon.py 의 마감 후 단계에 넣었다. PC 가 꺼져 있던 날은
     '매일 실행.bat' 로도 당일치는 받을 수 있지만, 지난 날은 못 받는다.

일봉(krx_panel)과 다른 점이 이것이다. 일봉은 몇 달 뒤에도 소급해서
채울 수 있어서 빠뜨려도 복구됐다. 분봉은 안 된다.

===========================================================================
어떻게 받는가
===========================================================================
한 번 호출에 기준시각 이전 1분봉 30건까지 온다. 그래서 09:30 부터
15:30 까지 30분 간격 13개 시각을 기준으로 불러서 하루(390분)를 덮는다.
받은 1분봉을 10분 단위로 묶어 저장한다.

  호출 수 = 종목수 x 13
  스로틀이 8회/초라서 200종목이면 약 5.5분, 30종목이면 약 50초.

10분으로 묶는 이유: 사용자가 말한 단위가 10분이고, 1분봉을 그대로
쌓으면 하루 390행 x 종목수가 되어 일봉 패널(226만행)보다 훨씬 빨리
커진다. 10분이면 하루 39행이다. 1분 원본이 필요해지면 그때 다시
논의한다 (소급이 안 되므로 지금 결정이 남는다는 점은 밝혀둔다).

===========================================================================
CSV 스키마 (새 파일이므로 여기서 정한다)
===========================================================================
  data/krx_min10_YYYY.csv
  date,time,code,open,high,low,close,volume

  time 은 그 10분 구간의 **시작** 시각 "HHMM" (예: 0930 = 09:30~09:39).
  이 저장소 규칙대로 컬럼을 새로 늘릴 때는 맨 뒤에 붙인다.

중복 방지: 이미 있는 (date, time, code) 는 다시 안 쓴다. 같은 날 두 번
돌려도 행이 안 늘어난다.

===========================================================================
검증 상태 - 아직 안 돌려봤다
===========================================================================
**이 파일은 실제 API 응답으로 확인하지 않았다.** 이 환경에는 KIS 인증
정보가 없어서 호출을 못 해봤다. 응답 필드 이름(stck_cntg_hour 등)이
실제와 다르면 빈 결과가 나올 수 있다.

그래서 --check 를 먼저 쓰도록 만들었다. 한 종목만 불러서 원본 응답을
그대로 보여준다. 그걸로 필드가 맞는지 확인한 뒤에 전체를 돌리면 된다.
확인되기 전까지 이 파일이 '작동한다' 고 말할 수 없다.

실행:
  python fetch_intraday.py --check          # 한 종목만, 응답 확인용
  python fetch_intraday.py --limit 30       # 30종목만 (약 50초)
  python fetch_intraday.py                  # 유니버스 전체 (약 5.5분)
"""
import argparse
import csv
import pathlib
import sys
from datetime import datetime

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

DATA_DIR = _ROOT / "data"
PREFIX = "krx_min10"
HEADER = ["date", "time", "code", "open", "high", "low", "close", "volume"]

# 30분 간격 기준시각. 각 호출이 그 시각 이전 30분을 돌려주므로 이 13개로
# 09:00~15:30 을 덮는다. 장 마감(15:30) 뒤에 도는 것을 전제한다.
ANCHORS = ("093000", "100000", "103000", "110000", "113000", "120000",
           "123000", "130000", "133000", "140000", "143000", "150000",
           "153000")
BUCKET_MIN = 10
# 장 마감 시각. 이 전에 돌리면 그날 데이터가 아직 없거나 반쪽이다.
CLOSE_HHMM = (15, 30)
# (2026-09-22) 이만큼 종목을 받을 때마다 파일에 쓴다. 전에는 루프가 다
# 끝난 뒤 한 번만 써서, 5분짜리 루프 중간에 정전이나 절전으로 죽으면
# 받은 것이 통째로 날아갔다. 20종목이면 파일 쓰기가 8번으로 늘지만
# (163/20) 그건 무의미한 비용이고, 죽어도 직전 20종목까지는 남는다.
FLUSH_EVERY = 20


def bucket_of(hhmmss):
    """"HHMMSS" 또는 "HHMM" -> 10분 구간 시작 "HHMM". 못 읽으면 None."""
    s = "".join(ch for ch in str(hhmmss) if ch.isdigit())
    if len(s) < 4:
        return None
    try:
        hh, mm = int(s[:2]), int(s[2:4])
    except ValueError:
        return None
    if not (0 <= hh < 24 and 0 <= mm < 60):
        return None
    return f"{hh:02d}{(mm // BUCKET_MIN) * BUCKET_MIN:02d}"


def to_buckets(bars):
    """1분봉 목록 -> {(date, 10분구간): {open,high,low,close,volume}}.

    시가는 구간의 첫 봉, 종가는 마지막 봉, 고/저는 구간 전체, 거래량은
    합이다. 값이 없는 봉은 그 항목만 건너뛴다 (0 으로 메우지 않는다).
    """
    out = {}
    for b in sorted(bars, key=lambda x: (x.get("date") or "", x.get("time") or "")):
        d, t = b.get("date"), bucket_of(b.get("time"))
        if not d or not t:
            continue
        cell = out.setdefault((d, t), {"open": None, "high": None,
                                       "low": None, "close": None,
                                       "volume": 0})
        if cell["open"] is None and b.get("open") is not None:
            cell["open"] = b["open"]
        if b.get("close") is not None:
            cell["close"] = b["close"]
        if b.get("high") is not None:
            cell["high"] = (b["high"] if cell["high"] is None
                            else max(cell["high"], b["high"]))
        if b.get("low") is not None:
            cell["low"] = (b["low"] if cell["low"] is None
                           else min(cell["low"], b["low"]))
        if b.get("volume"):
            cell["volume"] += b["volume"]
    return out


def existing_keys(year):
    """이미 저장된 (date, time, code). 중복을 안 쓰기 위해서다."""
    path = DATA_DIR / f"{PREFIX}_{year}.csv"
    have = set()
    if not path.exists():
        return have
    with open(path, encoding="utf-8-sig", newline="") as fh:
        r = csv.reader(fh)
        header = next(r, None)
        if not header:
            return have
        try:
            di, ti, ci = (header.index("date"), header.index("time"),
                          header.index("code"))
        except ValueError:
            return have
        for row in r:
            if len(row) > max(di, ti, ci):
                have.add((row[di], row[ti], row[ci]))
    return have


def append_rows(year, rows):
    """새 행만 덧붙인다. 파일이 없으면 헤더부터 쓴다."""
    if not rows:
        return 0
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{PREFIX}_{year}.csv"
    new = not path.exists()
    with open(path, "a", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(HEADER)
        for r in rows:
            w.writerow(r)
    return len(rows)


def collect_code(api, cfg, code, anchors=ANCHORS):
    """한 종목의 하루치 1분봉을 모아서 돌려준다. 실패한 시각은 건너뛴다."""
    bars, failed = [], 0
    for a in anchors:
        try:
            bars.extend(api.get_minute_prices(cfg, code, a))
        except Exception:
            failed += 1
    return bars, failed


def is_placeholder(cell):
    """거래가 없던 구간인가. 저장하면 안 된다.

    (2026-09-22 추가) 실제로 당했다. 08:36 에 돌렸더니 장이 안 열렸는데도
    API 가 **오늘 날짜로** 전일 종가를 채운 빈 봉 6,000행을 줬다. 거래량
    0, 시=고=저=종 이 40구간 전부였다.

    이게 그냥 쓸모없는 게 아니라 위험하다. 날짜가 오늘로 찍히므로,
    장 마감 뒤에 다시 돌리면 (date,time,code) 가 이미 있다고 중복 처리
    되어 **진짜 데이터가 영구히 안 들어간다.** 그래서 아예 저장을 막는다.

    판정: 거래량이 0 이고 네 값이 다 같으면 거래가 없던 것이다. 둘 중
    하나만으로는 안 된다 - 한 번만 체결된 구간은 네 값이 같지만 거래량이
    있고, 그건 진짜 데이터다.
    """
    if cell.get("volume"):
        return False
    vals = [cell.get(k) for k in ("open", "high", "low", "close")]
    if any(v is None for v in vals):
        return True          # 값이 없으면 쓸 것도 없다
    return len(set(vals)) == 1


def drop_placeholders(year, dry_run=False):
    """이미 저장된 빈 봉을 걷어낸다. (지운 행, 남은 행)

    08:36 사고로 들어간 6,000행을 치우기 위해 만들었다. 앞으로는
    is_placeholder 가 막으므로 이 함수가 할 일이 없어야 정상이다.
    """
    path = DATA_DIR / f"{PREFIX}_{year}.csv"
    if not path.exists():
        return (0, 0)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        r = csv.reader(fh)
        header = next(r, None)
        rows = [row for row in r if row]
    if not header:
        return (0, 0)
    idx = {k: header.index(k) for k in HEADER if k in header}

    def cell_of(row):
        def num(k):
            try:
                v = row[idx[k]]
                return float(v) if v not in (None, "") else None
            except (KeyError, IndexError, TypeError, ValueError):
                return None
        return {k: num(k) for k in ("open", "high", "low", "close", "volume")}

    keep = [row for row in rows if not is_placeholder(cell_of(row))]
    dropped = len(rows) - len(keep)
    if dropped and not dry_run:
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(keep)
    return (dropped, len(keep))


def main(argv=None):
    ap = argparse.ArgumentParser(description="10분봉 수집 (당일만 받을 수 있다)")
    ap.add_argument("--check", action="store_true",
                    help="한 종목만 불러 원본 응답을 보여준다 (필드 확인용)")
    ap.add_argument("--code", default="005930", help="--check 에 쓸 종목코드")
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N종목만")
    ap.add_argument("--clean", action="store_true",
                    help="이미 저장된 빈 봉(거래량 0 + 시=고=저=종)을 걷어낸다")
    args = ap.parse_args(argv)

    if args.clean:
        import glob as _g
        total_drop = 0
        for path in sorted(_g.glob(str(DATA_DIR / f"{PREFIX}_*.csv"))):
            y = pathlib.Path(path).stem.rsplit("_", 1)[-1]
            dropped, left = drop_placeholders(y)
            total_drop += dropped
            print(f"  {y}: 빈 봉 {dropped:,}행 삭제, {left:,}행 남음")
        print(f"합계 {total_drop:,}행 걷어냈습니다.")
        return 0

    import api_client as api  # noqa: E402
    from common import load_config  # noqa: E402
    cfg = load_config()

    if args.check:
        print(f"[확인] {args.code} / 기준시각 {ANCHORS[0]}")
        bars = api.get_minute_prices(cfg, args.code, ANCHORS[0])
        print(f"  받은 1분봉 {len(bars)}건")
        for b in bars[:5]:
            print("   ", b)
        if not bars:
            print("  [!] 0건입니다. 응답 필드 이름이 다를 수 있습니다.")
            print("      장 시작 전/휴장일에도 0건이 나옵니다.")
            return 1
        buckets = to_buckets(bars)
        print(f"  10분으로 묶으면 {len(buckets)}구간")
        for k in sorted(buckets)[:3]:
            print("   ", k, buckets[k])
        return 0

    import universe as U  # noqa: E402
    codes = U.codes()
    if args.limit:
        codes = codes[:args.limit]
    if not codes:
        print("[!] 유니버스가 비어 있습니다. collect_daily.py 를 먼저 돌리세요.")
        return 1

    today = datetime.now().strftime("%Y%m%d")
    year = today[:4]
    have = existing_keys(year)
    now = datetime.now()
    print(f"=== 10분봉 수집 {now:%Y-%m-%d %H:%M:%S} ===")
    print(f"{len(codes)}종목 x {len(ANCHORS)}회 호출. "
          f"기존 {len(have):,}행. 소급이 안 되므로 매일 돌려야 합니다.")
    # (2026-09-22) 08:36 에 돌렸다가 빈 봉 6,000행을 받았다. 장이 끝나기
    # 전에는 그날 데이터가 아직 없거나 반쪽이다.
    if (now.hour, now.minute) < CLOSE_HHMM:
        print(f"[!] 아직 장이 안 끝났습니다 ({now:%H:%M}, 마감 "
              f"{CLOSE_HHMM[0]:02d}:{CLOSE_HHMM[1]:02d}).")
        print("    지금 받는 것은 오늘의 일부이거나 거래 없는 빈 봉입니다.")
        print("    빈 봉은 저장하지 않습니다. 마감 뒤에 한 번 더 돌리세요.")

    rows, n_ok, n_fail, n_empty = [], 0, 0, 0
    total, bydate = 0, {}

    def flush():
        """모아둔 행을 파일에 쓰고 버퍼를 비운다. (쓴 행 수)

        (2026-09-22) 전에는 163종목 루프가 다 끝난 뒤에 한 번만 썼다.
        그 사이에 정전이나 절전으로 죽으면 5분간 받은 것이 통째로
        날아갔다. 사용자: "한 두번 정도는 날려도 상관없는데 계속
        날려먹는 건 좀". 그래서 FLUSH_EVERY 종목마다 쓴다.

        다시 돌릴 때 이어받는 것은 existing_keys 가 이미 해준다 -
        (날짜,시각,종목)이 파일에 있으면 건너뛰므로, 중간에 죽어도
        다음 회차가 빠진 것만 채운다.
        """
        nonlocal rows, total
        if not rows:
            return 0
        wrote = 0
        # 해가 바뀌는 날을 대비해 날짜별로 나눠 쓴다.
        for y in sorted({r[0][:4] for r in rows if r[0]}):
            wrote += append_rows(y, [r for r in rows if r[0].startswith(y)])
        for r in rows:
            bydate.setdefault(r[0], set()).add((r[1], r[2]))
        total += wrote
        rows = []
        return wrote

    for i, code in enumerate(codes, 1):
        bars, failed = collect_code(api, cfg, code)
        n_fail += failed
        added = 0
        for (d, t), c in sorted(to_buckets(bars).items()):
            if (d, t, code) in have:
                continue
            if is_placeholder(c):
                n_empty += 1
                continue
            have.add((d, t, code))
            rows.append([d, t, code, c["open"], c["high"], c["low"],
                         c["close"], c["volume"]])
            added += 1
        if added:
            n_ok += 1
        if i % FLUSH_EVERY == 0 or i == len(codes):
            n_new = len(rows)
            flush()
            print(f"  {i}/{len(codes)} 종목, 새 행 {n_new:,} 저장 "
                  f"(누적 {total:,})", flush=True)

    flush()
    print(f"\n{n_ok}종목에서 {total:,}행 저장. "
          f"거래 없어 버린 구간 {n_empty:,}개, 실패한 호출 {n_fail}회.")
    # 어느 날짜가 들어갔는지 꼭 보여준다. 08:36 사고 때 화면에는 '새 행
    # 800' 만 나와서 그게 빈 봉인지 알 수가 없었다.
    for d in sorted(bydate):
        ts = sorted({t for t, _c in bydate[d]})
        cs = {c for _t, c in bydate[d]}
        print(f"  {d}: {len(bydate[d]):,}행 / {len(cs)}종목 / "
              f"{len(ts)}구간 {ts[0]}~{ts[-1]}")
    if total == 0:
        print("[!] 저장된 행이 0입니다.")
        if n_empty:
            print("    전부 거래 없는 빈 봉이었습니다. 장 마감 뒤에 돌리세요.")
        else:
            print("    --check 로 응답을 먼저 확인하세요.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
