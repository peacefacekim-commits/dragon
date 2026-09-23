"""10분봉을 구경한다. **판정하지 않는다.**

(2026-09-22 신설) 사용자: "지금 하루 데이터가 있을 거거든 이걸 마음껏
즐기자"

===========================================================================
0 - 이 파일은 analyze_ 가 아니라 explore_ 다
===========================================================================
이름을 다르게 지은 이유가 있다. 이 저장소의 analyze_* 파일은 모두
**사전 등록한 조건으로 채택/탈락을 판정**한다. 이 파일은 그걸 하지
않는다. 하면 안 된다.

1일치로 할 수 없는 것
  - 신호가 통하나. 하루는 시장 상황의 표본이 **1개**다. 종목이 163개
    있어도 그날의 시장은 하나다. analyze_reverse.py 에서 같은 실수를
    했었다 (하루 안에서 섞는 대조군은 시장 조건에 대해 검정력이 0).
  - 승률, 기대수익, 조건 조합. 전부 20~60거래일이 필요하다
    (analyze_min10.py 의 MIN_DAYS_FOR_VERDICT / MIN_DAYS_FOR_RULES).

1일치로 할 수 있는 것
  - **구조**를 본다. 시간대별 변동폭, 거래량 분포, 수수료가 변동폭의
    몇 %인가. 이건 하루만 있어도 모양이 보이고, 며칠 쌓이면 확인된다.
  - **추정값을 실측값으로 바꾼다.** analyze_min10.py 가 일봉에서 역산한
    값으로 문턱을 계산해뒀는데, 이제 실제로 잴 수 있다. 이게 이 파일의
    제일 쓸모 있는 일이다.

거래일 수를 항상 화면 맨 위에 찍고, 20일 미만이면 판정이 아니라고
크게 알린다.

===========================================================================
1 - 실측이 추정보다 나빴다 (2026-09-22, 1거래일)
===========================================================================
analyze_min10.py 는 일봉에서 이렇게 역산해뒀다.

  하루 변동폭(고-저) 중앙값   5.80%   (최근 240일, 유니버스)
  10분 구간 변동폭 **추정**   0.93%   (하루 / sqrt(39))
  => 수수료 0.21% 가 구간 변동폭의 23%

실제로 재보니

  10분 구간 변동폭 **실측**   0.646%  (중앙값, 6,294구간)
  => 수수료 0.21% 가 구간 변동폭의 **33%**

sqrt 로 나눈 추정이 30% 크게 잡혀 있었다. 이유는 하루 변동폭이 시간에
고르게 퍼져 있지 않기 때문이다 - 아래 2절에서 보인다. **문턱이 23% 가
아니라 33% 다.** 나쁜 쪽으로 틀렸다.

===========================================================================
2 - 하루 안에서 변동폭이 U자다 (이게 제일 또렷한 구조)
===========================================================================
  구간    변동폭중앙%   수수료/변동폭   거래량비중%
  0900      2.135          10%         11.9%
  0910      1.643          13%          8.1%
  0920      1.141          18%          5.9%
  0930      1.063          20%          4.7%
  1000      0.835          25%          3.0%
  1100      0.553          38%          2.2%
  1220      0.398          53%          1.0%   <- 제일 죽은 시간
  1300      0.571          37%          2.0%
  1400      0.867          24%          1.8%
  1500      0.609          34%          1.5%

읽는 법
  - **장 초반 30분이 하루의 전부다.** 0900~0920 세 구간이 거래량의
    25.9% 이고 변동폭이 1.1~2.1% 다.
  - **점심때는 수수료가 변동폭의 절반이다** (1220 에 53%). 그 시간에
    10분 매매를 하면 이기든 지든 수수료가 반을 먹는다.
  - 오후 2시경에 조금 살아난다 (0.867%).

**주의: 변동폭이 크다고 버는 게 아니다.** 변동폭은 '벌 여지' 이고 방향은
따로다. 게다가 장 초반은 호가 스프레드도 가장 넓어서 슬리피지가 크다
(그건 이 데이터로 못 잰다 - 호가가 아니라 체결가만 있다). 그래서 이
표는 "어디가 가능성이 있나" 이지 "어디서 번다" 가 아니다.

그래도 한쪽으로는 쓸 수 있다. **1220 처럼 수수료가 변동폭의 절반인
시간대는 안 하는 것이 낫다** - 이건 방향을 몰라도 말할 수 있다.
사용자의 아이디어 2("지표가 안 좋은 날엔 쉰다")를 하루 단위에서
시간 단위로 옮긴 것이고, 일봉에서는 11,830가지가 전부 대조군을 못
넘었지만 (analyze_skip_rules.py) 시간대는 아직 안 재봤다.

그리고 이게 1절의 33% 를 다시 읽게 만든다. **하루 전체로 잰 33% 는
계획에 쓸 숫자가 아니다** - 1220 에 거래할 사람은 없으니까. 시간대를
갈라서 재면

  하루 전체        6,294구간   변동폭 0.646%   수수료/변동폭 **33%**
  0900~0950         978구간   변동폭 1.248%   수수료/변동폭 **17%**
  1100~1350       2,934구간   변동폭 0.536%   수수료/변동폭 **39%**

장 초반 1시간만 쓰면 문턱이 17% 다. 추정값(23%)보다 **오히려 낫다.**
하루 전체(33%)보다는 확실히 낫다.

단, 여기에 반대 무게가 하나 있고 그게 하필 같은 자리다. **장 초반은
호가 스프레드가 가장 넓다.** 변동폭이 제일 큰 시간이 슬리피지도 제일
큰 시간이다. 이 데이터로는 못 잰다 (체결가만 있다). analyze_knobs
--fast 의 0.08% 교차점이 여기서 결판난다.

===========================================================================
3 - 시간대에 따라 '안 움직인 종목' 이 6% ~ 24% 다
===========================================================================
시가와 종가가 같은(한 틱도 안 움직인) 종목 비율

  0900   6%      1030  18%      1220  21%      1400   7%
  0920   9%      1120  24%      1300  12%      1450  21%

장 초반엔 거의 다 움직이고 점심때는 4분의 1이 멈춰 있다. 안 움직이는
종목을 사면 수수료만 낸다. 10분 매매에서 종목 선정의 첫 일은 '오를
종목 고르기' 가 아니라 **'움직이는 종목 고르기'** 일 수 있다.
20거래일이 모이면 잴 수 있다.

===========================================================================
4 - 15:20~15:30 은 10분봉이 없다 (동시호가)
===========================================================================
  1500   163종목   거래량 4,158,935
  1510   163종목   거래량 4,734,176
  1520     1종목   거래량 1          <- 사실상 없음
  1530    99종목   거래량 1,187,769  (64% 가 시가=종가)

한국 시장은 15:20~15:30 이 **단일가 동시호가**라서 연속 체결이 없다.
그래서 종목당 봉이 38~39개다 (40개가 아니다). 쓸 수 있는 연속 거래
구간은 **0900~1510 의 38구간**이고, 1530 은 종가 단일가 한 점이다.

수집은 15:30 까지 그대로 두는 것이 맞다 (종가가 필요하다). 다만 분석에서
'구간' 으로 셀 때는 38개로 봐야 한다.

===========================================================================
5 - 보유시간 미리보기 - 그리고 이걸 읽을 때의 함정
===========================================================================
  그날 시장 (첫 봉 시가 -> 마지막 봉 종가, 중앙값): **-1.40%**

  보유        표본     평균%    중앙%   수수료뺀%   시장대비%p
  10분      6,131   -0.053  -0.067    -0.263      +1.346
  60분      6,131   -0.222  -0.192    -0.432      +1.176
  140분     6,131   -0.484  -0.372    -0.694      +0.915
  종가까지    6,131   -0.810  -0.556    -1.020      +0.588

**두 칸 다 1거래일로는 못 읽는다.** 이유가 각각 다르다.

  평균/중앙   그날 시장이 -1.40% 였다. 음수인 게 당연하고 발견이 아니다.
  시장대비    전부 양수인데 이것도 엣지가 아니다. **그날 하락이 장 초반에
              몰려 있었기 때문**이다 (0900 구간 변동폭 2.135%, 수익 중앙
              -0.136%). 시장 기준을 '첫 봉 시가부터' 로 잡았으니, 0910
              이후에 들어간 모든 거래는 그 첫 하락을 피한 것으로 잡힌다.
              즉 이 +1.346%p 는 '늦게 들어가서 좋았다' 가 아니라 '기준을
              첫 봉부터 잡았다' 는 사실이다.

이 함정은 며칠 쌓이면 사라진다 (오르는 날과 내리는 날이 섞이면 기준의
편향이 상쇄된다). 그래서 20거래일을 기다린다.

읽을 수 있는 것 하나: **보유가 길어질수록 수수료를 뺀 값이 더 나빠진다**
(-0.263 -> -1.020). 이건 그날 시장이 내렸기 때문이므로 역시 발견이
아니다. 다만 오르는 날에 반대로 나오는지 보면 그때는 뜻이 생긴다.

===========================================================================
4 - 한계 (이 파일은 결론을 내지 않는다)
===========================================================================
1) 1거래일이다. 시장 상황 표본이 1개다. 여기 나온 U자 모양조차 그날의
   모양일 수 있다 (다만 U자는 세계 어느 시장에서나 알려진 구조라서
   뒤집힐 가능성은 낮다고 본다 - 그건 근거가 아니라 기대다).
1b) 그날은 **내린 날**이었다 (중앙 -1.40%, 오른 종목 26%). 방향이 걸린
   숫자는 전부 그 사실에 물들어 있다.
2) 호가/스프레드가 없다. 체결가만 있어서 슬리피지를 못 잰다. 0.08%
   교차점(analyze_knobs --fast)이 여전히 미해결이다.
3) 150종목 유니버스에서 163종목이 잡혔다 (universe.json 과 그날 후보가
   다르다). 유니버스 정의가 확정되면 다시 재야 한다.
4) 여기서 무엇도 채택하지 않는다. 채택은 analyze_min10.py 가 20/60
   거래일에 사전 등록한 조건으로만 한다.

실행:
  python explore_min10.py              # 전부
  python explore_min10.py --time       # 시간대별만
  python explore_min10.py --holds      # 보유시간별 미리보기
"""
import argparse
import collections
import csv
import glob
import pathlib
import statistics as st
import sys

_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

DATA_DIR = _ROOT / "data"
PREFIX = "krx_min10"
FEE_ROUND_TRIP = 0.21
# analyze_min10.py 가 일봉에서 역산해둔 추정값. 이 파일이 실측으로 바꾼다.
EST_BAR_RANGE_PCT = 0.93
MIN_DAYS_FOR_VERDICT = 20
# 보유 구간 (10분봉 개수). analyze_min10.HOLD_BUCKETS 와 같게 둔다.
HOLD_BUCKETS = (1, 6, 14, 39)
HOLD_LABELS = {1: "10분", 6: "60분", 14: "140분", 39: "종가까지"}


def load(path_glob=None):
    """10분봉을 [(date, time, code, o, h, l, c, v)] 로. 빈 봉은 버린다."""
    out = []
    pat = path_glob or str(DATA_DIR / f"{PREFIX}_*.csv")
    for path in sorted(glob.glob(pat)):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in fh and csv.DictReader(fh):
                try:
                    o, h, l, c = (float(r["open"]), float(r["high"]),
                                  float(r["low"]), float(r["close"]))
                    v = int(float(r["volume"]))
                except (KeyError, TypeError, ValueError):
                    continue
                if not o:
                    continue
                if v == 0 and len({o, h, l, c}) == 1:
                    continue                    # 거래 없는 빈 봉
                out.append((r["date"], r["time"], r["code"], o, h, l, c, v))
    return out


def bar_range(rows):
    """구간 변동폭 (고-저)/시가 % 목록."""
    return [(h - l) / o * 100 for _d, _t, _c, o, h, l, _cl, _v in rows if o]


def fee_share_of_range(range_pct, fee=FEE_ROUND_TRIP):
    """수수료가 구간 변동폭의 몇 %인가. 변동폭이 0 이면 None."""
    if not range_pct:
        return None
    return fee / range_pct * 100


def by_time(rows):
    """구간별 (종목수, 변동폭중앙, 수익중앙, 안움직인비율%, 거래량)."""
    g = collections.defaultdict(lambda: {"rng": [], "ret": [], "flat": 0,
                                         "vol": 0})
    for _d, t, _c, o, h, l, cl, v in rows:
        a = g[t]
        a["rng"].append((h - l) / o * 100)
        a["ret"].append((cl / o - 1) * 100)
        a["flat"] += 1 if cl == o else 0
        a["vol"] += v
    out = []
    for t in sorted(g):
        a = g[t]
        n = len(a["rng"])
        out.append((t, n, st.median(a["rng"]), st.median(a["ret"]),
                    a["flat"] / n * 100 if n else 0.0, a["vol"]))
    return out


def day_move(rows):
    """날짜별 시장 움직임. 첫 봉 시가 -> 마지막 봉 종가의 중앙값%.

    보유시간 표를 읽으려면 이게 먼저 있어야 한다. 시장이 -1.3% 인 날에
    모든 보유가 음수인 것은 발견이 아니라 그날 시장이다.
    """
    per = collections.defaultdict(dict)
    for d, t, c, o, _h, _l, cl, _v in rows:
        per[(d, c)][t] = (o, cl)
    by_day = collections.defaultdict(list)
    for (d, _c), tm in per.items():
        if not tm:
            continue
        ts = sorted(tm)
        o = tm[ts[0]][0]
        cl = tm[ts[-1]][1]
        if o:
            by_day[d].append((cl / o - 1) * 100)
    return {d: st.median(v) for d, v in by_day.items() if v}


def hold_preview(rows, buckets=HOLD_BUCKETS):
    """보유 구간별 수익률 미리보기. (구간, 표본, 평균%, 중앙%, 수수료뺀%, 시장대비%p).

    **판정이 아니다.** 하루치면 시장 상황 표본이 1개다. 20거래일이
    모이면 analyze_min10.py 가 사전 등록한 조건으로 판정한다.

    같은 종목/같은 날 안에서 i 번째 봉 시가에 사서 i+k 번째 봉 종가에
    판다. k 가 남은 봉보다 크면 **그날 마지막 봉**에 판다 (그게
    '종가까지' 다). 그렇게 안 하면 종가까지 칸이 표본 0 이 된다 -
    하루에 38~39봉뿐이라서.

    시장대비는 그날 시장 중앙값을 뺀 값이다. 하락장에서 음수가 나오는
    것과 시장보다 못한 것은 다르다.
    """
    per = collections.defaultdict(dict)
    for d, t, c, o, _h, _l, cl, _v in rows:
        per[(d, c)][t] = (o, cl)
    moves = day_move(rows)
    out = []
    for k in buckets:
        got, rel = [], []
        for (d, _c), tm in per.items():
            ts = sorted(tm)
            n = len(ts)
            for i in range(n - 1):
                j = min(i + k, n - 1)
                if j <= i:
                    continue
                o = tm[ts[i]][0]
                cl = tm[ts[j]][1]
                if not o:
                    continue
                r = (cl / o - 1) * 100
                got.append(r)
                rel.append(r - moves.get(d, 0.0))
        if not got:
            out.append((k, 0, None, None, None, None))
            continue
        m = st.mean(got)
        out.append((k, len(got), m, st.median(got),
                    m - FEE_ROUND_TRIP, st.mean(rel)))
    return out


def n_days(rows):
    return len({d for d, *_ in rows})


def enough(rows, need=MIN_DAYS_FOR_VERDICT):
    return n_days(rows) >= need


def main(argv=None):
    ap = argparse.ArgumentParser(description="10분봉을 구경한다 (판정 안 함)")
    ap.add_argument("--time", action="store_true", help="시간대별만")
    ap.add_argument("--holds", action="store_true", help="보유시간별만")
    args = ap.parse_args(argv)

    rows = load()
    if not rows:
        print("10분봉이 없습니다. 매일 실행.bat 을 15:30 이후에 돌리세요.")
        return 0

    nd = n_days(rows)
    print(f"\n{'=' * 62}")
    print(f"10분봉 {len(rows):,}구간 / {nd}거래일 / "
          f"{len({c for _d, _t, c, *_ in rows})}종목")
    if not enough(rows):
        print(f"[!] {nd}거래일뿐입니다. 판정에 {MIN_DAYS_FOR_VERDICT}거래일이"
              f" 필요합니다 ({MIN_DAYS_FOR_VERDICT - nd}일 더).")
        print(f"[!] 아래는 **구경**입니다. 여기서 아무것도 채택하지 않습니다.")
    print(f"{'=' * 62}")

    show_all = not (args.time or args.holds)

    if show_all:
        rng = bar_range(rows)
        med = st.median(rng)
        rs = sorted(rng)
        print(f"\n=== 10분 구간 변동폭 (고-저)/시가 ===")
        print(f"  중앙 {med:.3f}%   평균 {st.mean(rng):.3f}%")
        print(f"  25% {rs[len(rs) // 4]:.3f}   "
              f"75% {rs[3 * len(rs) // 4]:.3f}   최대 {rs[-1]:.3f}")
        print(f"\n  추정({EST_BAR_RANGE_PCT:.2f}%) vs 실측({med:.3f}%)")
        print(f"  수수료 {FEE_ROUND_TRIP}% 가 변동폭의 "
              f"{fee_share_of_range(EST_BAR_RANGE_PCT):.0f}% (추정) -> "
              f"**{fee_share_of_range(med):.0f}%** (실측)")
        if med < EST_BAR_RANGE_PCT:
            print(f"  -> 추정이 크게 잡혀 있었다. 문턱이 나쁜 쪽으로 틀렸다.")

    if show_all or args.time:
        print(f"\n=== 시간대별 (하루 안의 모양) ===")
        print(f"  {'구간':<7}{'변동폭중앙%':>12}{'수수료/변동폭':>14}"
              f"{'안움직임%':>11}{'거래량비중%':>12}")
        rows_t = by_time(rows)
        tot = sum(v for *_x, v in rows_t) or 1
        for t, _n, rmed, _retmed, flat, vol in rows_t:
            sh = fee_share_of_range(rmed)
            print(f"  {t:<7}{rmed:>12.3f}"
                  + (f"{sh:>13.0f}%" if sh is not None else f"{'-':>14}")
                  + f"{flat:>10.0f}%{vol / tot * 100:>11.1f}%")
        best = max(rows_t, key=lambda r: r[2])
        worst = min((r for r in rows_t if r[2] > 0), key=lambda r: r[2])
        print(f"\n  가장 큰 구간 {best[0]} ({best[2]:.3f}%, 수수료 "
              f"{fee_share_of_range(best[2]):.0f}%)")
        print(f"  가장 죽은 구간 {worst[0]} ({worst[2]:.3f}%, 수수료 "
              f"{fee_share_of_range(worst[2]):.0f}%)")
        print("  변동폭이 크다고 버는 게 아니다 - 방향은 따로고,"
              " 장 초반은 스프레드도 넓다.")
        print("  다만 '수수료가 변동폭의 절반인 시간대는 안 한다' 는"
              " 방향을 몰라도 말할 수 있다.")

    if show_all or args.holds:
        moves = day_move(rows)
        print(f"\n=== 그날 시장 (첫 봉 시가 -> 마지막 봉 종가, 중앙값) ===")
        for d in sorted(moves):
            print(f"  {d}: {moves[d]:+.2f}%")
        print(f"\n=== 보유시간별 미리보기 ({nd}거래일, 판정 아님) ===")
        print(f"  {'보유':<10}{'표본':>9}{'평균%':>9}{'중앙%':>9}"
              f"{'수수료뺀%':>11}{'시장대비%p':>12}")
        for k, n, m, md, net, rel in hold_preview(rows):
            if m is None:
                print(f"  {HOLD_LABELS.get(k, str(k)):<10}{n:>9}"
                      f"{'표본없음':>33}")
                continue
            print(f"  {HOLD_LABELS.get(k, str(k)):<10}{n:>9,}{m:>9.3f}"
                  f"{md:>9.3f}{net:>11.3f}{rel:>12.3f}")
        print(f"  (i 번째 시가 매수 -> i+k 번째 종가 매도. k 가 남은 봉보다"
              f" 크면 그날 마지막 봉에 판다.)")
        print(f"  **두 칸 다 {nd}거래일로는 못 읽는다.**")
        print(f"   평균/중앙  그날 시장이 움직인 만큼 그대로 물든다.")
        print(f"   시장대비   기준을 '첫 봉 시가' 로 잡았으므로, 하락이"
              f" 장 초반에 몰린 날엔")
        print(f"              늦게 들어간 거래가 자동으로 좋아 보인다."
              f" 엣지가 아니다.")
        print(f"   판정은 analyze_min10.py 가"
              f" {MIN_DAYS_FOR_VERDICT}거래일에 한다.")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
