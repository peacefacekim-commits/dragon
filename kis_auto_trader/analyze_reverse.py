"""거꾸로 추적 - 결과가 좋았던 순간의 지표를 역추적한다.

(2026-09-21 신설) 사용자: "투자 결과가 좋았을 때 (...) 가장 좋은 시나리오
부터 생각해서 그 때의 지표를 역추적하는 거야. (...) 코스피가 얼마나
오르는지 내리는지 상대적인 걸 생각해서 각 지표별 조건을 맞춰보자고
(...) 나는 원래는 10분 씩 짧게 소형주를 사고 팔면서 이윤을 보려고
했거든 근데 며칠 계속 손해를 보니까 추리를 하는 거야. 어떤 조건을
추가하면 약간이라도 승률이 높아질까"

===========================================================================
이 방식의 위험을 먼저 적는다
===========================================================================
'결과를 보고 조건을 찾는다' 는 순서다. 그대로 하면 **반드시 뭔가
발견된다.** 우연이라도 나온다. 65개 칸을 훑어서 제일 좋은 것을 고르면,
표적이 순전히 무작위여도 승률 55~60% 짜리 칸이 나온다.

그래서 세 가지를 붙였다.
  (1) 탐색은 **전반부만** 본다. 찾은 것을 후반부에서 딱 한 번 확인한다.
      후반부는 탐색에 쓰지 않는다.
  (2) **잡음 기준선** - 표적을 날짜 안에서 무작위로 섞고 같은 탐색을
      반복한다. 우연히 나오는 '제일 좋은 칸' 의 승률이 얼마인지 잰다.
      실제 탐색 결과가 이 분포 안에 있으면 발견이 아니다.
  (3) 표적을 **시장 대비 상대 수익률** 로 둔다. 절대 수익률로 재면
      '시장이 오른 날' 을 맞힌 것이 신호처럼 보인다.

===========================================================================
무엇을 재는가
===========================================================================
표적 (사용자가 말한 '결과')
  다음날 상대 수익률 = 그 종목 다음날 수익률 - 그날 후보 전체 평균
  승리 = 상대 수익률 > 0
  '코스피 대비' 를 후보 200종목 동일가중 평균으로 대신한다. 지수를
  따로 들여오면 구성종목이 패널과 달라서 비교가 흐려진다.

조건 (사용자가 말한 '지표')
  시장 지표 13개    각각 5분위. di-1 값으로 나눈다.
  지표의 전일 변화  13개 각각 5분위 (전날 - 그전날)
  종목 자신 전날    5분위
  = 27 x 5 = 135 칸

종목 무리
  시총 3분위 (대형 / 중형 / 소형). 사용자의 실제 대상이 소형주이므로
  따로 본다. 소형주에서만 되는 것과 전체에서 되는 것은 다른 이야기다.

===========================================================================
못 재는 것 - 먼저 밝힌다
===========================================================================
**10분 매매는 이 데이터로 못 잰다.** 패널이 일봉이라 하루 안의 사고
팔기를 재현할 수 없다. 여기서 재는 승률은 **하루 보유** 승률이다.
10분 매매의 승률과 같다고 볼 근거가 없다.

그리고 이미 잰 것이 있다 (analyze_short_term, analyze_intraday).
  하루 보유는 엣지가 +0.102% 로 살아 있는데도 연 -27.0% 다. 신호가
  없어서가 아니라 왕복 수수료 0.21% 를 못 넘어서다.
  장중 변동폭이 2.3~3.5% 이므로 수수료는 그 6~9% 다. 즉 10분 매매는
  '승률' 이 아니라 '한 번에 얼마를 남기나' 가 문제다. 승률 55% 로
  0.1% 씩 남겨도 수수료가 0.21% 면 진다.

그래서 이 파일이 승률 높은 조건을 찾아내도 **그것만으로 10분 매매가
되는 것은 아니다.** 필요한 것은 '승률 x 이익 - 패률 x 손실 > 수수료'
이고, 이 파일은 그 첫 항만 본다.

===========================================================================
결과 - 아직 없음
===========================================================================
아직 돌리지 않았다. 이 문단이 바뀌면 결과가 들어온 것이다.

실행:
  python analyze_reverse.py            # 요약만 (빠름)
  python analyze_reverse.py --run      # 전체 탐색 + 확인 + 잡음 (오래)
"""
import argparse
import csv
import glob
import pathlib
import random
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_consensus as C  # noqa: E402
import strategy as S  # noqa: E402

BASE_DI = 250
N_BUCKETS = 5
N_SIZE = 3
SIZE_NAMES = ("대형", "중형", "소형")
MIN_CELL = 300        # 이보다 적은 칸은 안 본다 (승률이 흔들린다)
N_NOISE = 50          # 잡음 기준선 반복 횟수
SEED = 20260921
KEYS = C.CSV_KEYS


def load_raw():
    raw = {}
    for path in sorted(glob.glob(str(_ROOT / "data" / "market_indicators_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                raw[r["date"]] = r
    return raw


def load_caps(dates):
    """{(di, code): 시가총액}. 시총 3분위를 나누는 데만 쓴다."""
    dpos = {d: i for i, d in enumerate(dates)}
    out = {}
    for path in sorted(glob.glob(str(_ROOT / "data" / "krx_cap_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                di = dpos.get(r["date"])
                if di is None:
                    continue
                try:
                    v = float(r["market_cap"])
                except (KeyError, TypeError, ValueError):
                    continue
                if v > 0:
                    out[(di, r["code"])] = v
    return out


def ind_at(raw, dates, di, key):
    if di < 0 or di >= len(dates):
        return None
    try:
        return float(raw[dates[di]][key])
    except (KeyError, TypeError, ValueError):
        return None


def day_return(panel, code, di):
    """di 일의 전일 대비 수익률%."""
    s = panel.get(code)
    if s is None:
        return None
    a, b = s.pos.get(di), s.pos.get(di - 1)
    if a is None or b is None or not s.close[b]:
        return None
    return (s.close[a] / s.close[b] - 1) * 100


def bucketize(values, n=N_BUCKETS):
    """값 목록 -> {값 순서 -> 분위}. 같은 값이 많으면 칸이 비뚤어진다.

    경계를 분위수로 잡는다. 미리 정한 절대 문턱을 쓰지 않는 이유는
    지표마다 단위가 달라서다.
    """
    srt = sorted(values)
    if len(srt) < n:
        return []
    return [srt[int(len(srt) * k / n)] for k in range(1, n)]


def which_bucket(v, edges):
    for i, e in enumerate(edges):
        if v < e:
            return i
    return len(edges)


def build_rows(dates, panel, raw, caps, base_di=BASE_DI):
    """관측 하나 = (di, 종목, 시총분위, 표적, {조건이름: 값}).

    표적은 **다음날** 상대 수익률이므로 미래다. 조건은 전부 di-1 까지만
    본다. 이 둘이 섞이지 않게 하는 것이 이 함수의 핵심이다.
    """
    rows = []
    n = len(dates)
    for di in range(base_di, n - 1):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        nxt = {}
        for c in cand:
            v = day_return(panel, c, di + 1)
            if v is not None:
                nxt[c] = v
        if len(nxt) < 20:
            continue
        mkt = st.mean(nxt.values())          # 시장 대신 후보 동일가중
        capd = {c: caps.get((di - 1, c)) for c in nxt}
        have = [c for c in nxt if capd[c]]
        if len(have) < 20:
            continue
        cedges = bucketize([capd[c] for c in have], N_SIZE)
        cond = {}
        for key in KEYS:
            a = ind_at(raw, dates, di - 1, key)
            b = ind_at(raw, dates, di - 2, key)
            if a is not None:
                cond[key] = a
            if a is not None and b is not None:
                cond[key + "_chg"] = a - b
        for c in have:
            own = day_return(panel, c, di - 1)
            if own is None:
                continue
            rows.append((di, c, which_bucket(capd[c], cedges),
                         nxt[c] - mkt, dict(cond, own_prev=own)))
    return rows


def cell_stats(rows, name, edges, bucket, size=None):
    """그 칸의 (승률%, 평균 상대수익%, 표본수). 확인용에서 쓴다."""
    hit = [r[3] for r in rows
           if (size is None or r[2] == size)
           and name in r[4] and which_bucket(r[4][name], edges) == bucket]
    if not hit:
        return (0.0, 0.0, 0)
    return (sum(1 for v in hit if v > 0) / len(hit) * 100,
            st.mean(hit), len(hit))


def cond_names(rows):
    names = set()
    for r in rows:
        names |= set(r[4])
    return sorted(names)


def build_index(rows, size=None):
    """(조건, 분위) -> 그 칸에 드는 관측 번호 목록. 한 번만 만든다.

    왜 미리 만드나: 잡음 기준선은 표적만 섞고 조건은 그대로다. 그러니
    칸 배정은 안 바뀐다. 50번 반복하면서 매번 다시 나누면 그만큼 낭비다.
    """
    idx = [i for i, r in enumerate(rows) if size is None or r[2] == size]
    cells, edge_of = {}, {}
    for name in cond_names(rows):
        vals = [rows[i][4][name] for i in idx if name in rows[i][4]]
        edges = bucketize(vals)
        if not edges:
            continue
        edge_of[name] = edges
        for i in idx:
            v = rows[i][4].get(name)
            if v is None:
                continue
            cells.setdefault((name, which_bucket(v, edges)), []).append(i)
    return cells, edge_of


def sweep_indexed(targets, cells, edge_of, min_cell=MIN_CELL):
    """미리 만든 칸으로 승률을 잰다. 제일 좋은 것부터."""
    out = []
    for (name, b), idxs in cells.items():
        if len(idxs) < min_cell:
            continue
        vals = [targets[i] for i in idxs]
        wr = sum(1 for v in vals if v > 0) / len(vals) * 100
        out.append((wr, st.mean(vals), len(vals), name, b, edge_of[name]))
    out.sort(reverse=True)
    return out


def sweep(rows, size=None, min_cell=MIN_CELL):
    """모든 (조건, 분위) 칸의 승률. 제일 좋은 것부터 정렬해서 돌려준다."""
    cells, edge_of = build_index(rows, size)
    return sweep_indexed([r[3] for r in rows], cells, edge_of, min_cell)


def day_groups(rows):
    """{날짜: 관측 번호들}. 날짜 안에서만 섞기 위해서다."""
    byday = {}
    for i, r in enumerate(rows):
        byday.setdefault(r[0], []).append(i)
    return byday


def shuffled_targets(rows, byday, rng):
    """표적을 **같은 날 안에서** 섞은 목록.

    날짜를 넘겨서 섞으면 시장 전체의 오른 날/내린 날 구조가 깨져서
    잡음 기준선이 너무 쉬워진다. 날짜 안에서 섞으면 '그날 어느 종목이
    이겼나' 만 무작위가 된다 - 우리가 묻는 것과 정확히 같은 질문이다.
    """
    out = [r[3] for r in rows]
    for idxs in byday.values():
        tg = [out[i] for i in idxs]
        rng.shuffle(tg)
        for i, v in zip(idxs, tg):
            out[i] = v
    return out


def noise_ceiling(rows, size=None, n_noise=N_NOISE, seed=SEED,
                  cells=None, edge_of=None):
    """표적을 섞고 같은 탐색을 반복했을 때 '제일 좋은 칸' 승률의 분포.

    이게 이 파일의 핵심 장치다. 실제 탐색의 1등이 이 분포 안에 있으면
    발견이 아니다. 칸 배정은 안 바뀌므로 미리 만든 것을 재사용한다.
    """
    if cells is None:
        cells, edge_of = build_index(rows, size)
    rng = random.Random(seed)
    byday = day_groups(rows)
    tops = []
    for _ in range(n_noise):
        tg = shuffled_targets(rows, byday, rng)
        s = sweep_indexed(tg, cells, edge_of)
        tops.append(s[0][0] if s else 0.0)
    return sorted(tops)


def main():
    ap = argparse.ArgumentParser(description="결과에서 지표를 역추적한다")
    ap.add_argument("--run", action="store_true", help="전체 탐색 (오래 걸린다)")
    ap.add_argument("--noise", type=int, default=N_NOISE)
    args = ap.parse_args()

    dates, panel = S.load_panel()
    raw, caps = load_raw(), load_caps(dates)
    print("관측 만드는 중...", flush=True)
    rows = build_rows(dates, panel, raw, caps)
    half = (BASE_DI + len(dates)) // 2
    explore = [r for r in rows if r[0] < half]
    confirm = [r for r in rows if r[0] >= half]
    print(f"\n관측 {len(rows):,}개 "
          f"(탐색용 {len(explore):,} / 확인용 {len(confirm):,})")
    print(f"조건 {len(cond_names(rows))}개 x {N_BUCKETS}분위")
    base = sum(1 for r in rows if r[3] > 0) / len(rows) * 100
    print(f"아무 조건 없는 승률: {base:.2f}% (상대 수익률이므로 50% 근처가 정상)")
    if not args.run:
        print("\n--run 을 붙이면 전체 탐색 + 확인 + 잡음 기준선을 돌립니다.")
        return 0

    for size, sname in [(None, "전체")] + list(enumerate(SIZE_NAMES)):
        print(f"\n{'=' * 70}")
        print(f"{sname} 종목")
        print(f"{'=' * 70}")
        cells, edge_of = build_index(explore, size)
        ex = sweep_indexed([r[3] for r in explore], cells, edge_of)
        if not ex:
            print("  칸이 표본 기준을 못 넘었다.")
            continue
        eb = (sum(1 for r in explore if (size is None or r[2] == size) and r[3] > 0)
              / max(1, sum(1 for r in explore if size is None or r[2] == size)) * 100)
        print(f"\n[탐색 전반부] 기준 승률 {eb:.2f}%. 상위 8칸:")
        print(f"  {'조건':<22}{'분위':>5}{'승률%':>8}{'평균%':>9}{'표본':>9}")
        for wr, mean, n, name, b, _e in ex[:8]:
            print(f"  {name:<22}{b + 1:>5}{wr:>8.2f}{mean:>+9.3f}{n:>9,}")

        print(f"\n[잡음 기준선] 표적을 섞고 같은 탐색을 {args.noise}번")
        nz = noise_ceiling(explore, size, args.noise,
                           cells=cells, edge_of=edge_of)
        print(f"  우연히 나오는 1등 승률: 최소 {nz[0]:.2f}% / "
              f"중앙 {st.median(nz):.2f}% / 최대 {nz[-1]:.2f}%")
        top = ex[0][0]
        beat = sum(1 for v in nz if v >= top)
        print(f"  실제 1등 {top:.2f}% -> 잡음 {args.noise}개 중 "
              f"{beat}개가 이보다 높거나 같다")
        if beat > args.noise * 0.05:
            print("  => 잡음 분포 안이다. 발견이 아니다.")
        else:
            print("  => 잡음을 넘었다. 확인용에서 다시 본다.")

        print(f"\n[확인 후반부] 탐색 상위 5칸을 그대로 적용")
        print(f"  {'조건':<22}{'분위':>5}{'전반 승률':>10}{'후반 승률':>10}"
              f"{'후반 평균%':>11}{'후반 표본':>10}")
        cb = (sum(1 for r in confirm if (size is None or r[2] == size) and r[3] > 0)
              / max(1, sum(1 for r in confirm if size is None or r[2] == size)) * 100)
        kept = 0
        for wr, _m, _n, name, b, edges in ex[:5]:
            cwr, cmean, cn = cell_stats(confirm, name, edges, b, size)
            if cn >= MIN_CELL and cwr > cb:
                kept += 1
            print(f"  {name:<22}{b + 1:>5}{wr:>10.2f}{cwr:>10.2f}"
                  f"{cmean:>+11.3f}{cn:>10,}")
        print(f"  후반부 기준 승률 {cb:.2f}%. 5칸 중 {kept}칸이 넘었다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
