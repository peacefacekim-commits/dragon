"""갈아타는 순간을 들여다본다 - 파는 종목과 사는 종목은 어떻게 다른가.

(2026-09-21 신설) 사용자: "지금 상황에서 지표를 쌓는게 무슨 의미겠어
있는 거나 잘 써야지 거꾸로 안정적인 종목을 팔게 되는 때와 사게 되는
때의 지표를 분석해서 공통점을 찾아줘 전날에 비해서 얼마나 변했나 또
그전날에 비해서 어땠냐 이정도로만"

지금까지 지표는 전부 "내일 오를까" (타이밍) 로만 썼고 전부 탈락했다.
이건 반대 방향이다. **우리가 이미 내리는 결정의 순간이 어떤 모습인지**
를 본다. 새 신호를 찾는 게 아니라 있는 것을 설명하는 것이다.

이벤트 정의: 저변동 상위 10에 어제 없던 종목이 오늘 들어오면 '진입',
어제 있던 종목이 오늘 빠지면 '이탈'. 2021~2026 에서 각각 738건이다.

===========================================================================
0 - 먼저 나온 구조적 사실: 시장 지표로는 절대 구별할 수 없다
===========================================================================
처음에 시장 지표 13개를 진입일과 이탈일로 나눠봤더니 **차이가 정확히
0.000** 이었다. 버그가 아니다.

상위 10은 자리 수가 고정이다. 하나가 들어오면 반드시 하나가 나간다.
**같은 날이다.** 그런데 시장 지표는 하루에 한 줄뿐이라 두 사건에 같은
값이 붙는다. 그러니 "살 때의 지표" 와 "팔 때의 지표" 는 정의상 같은
값이고, 아무리 지표를 늘려도 이건 안 바뀐다.

그래서 답할 수 있는 형태로 두 가지를 본다.
  [1] 종목 자신의 움직임 - 진입 종목과 이탈 종목은 다를 수 있다
  [2] 교체가 일어나는 날 vs 조용한 날 - 시장 지표가 여기서는 다를 수 있다

===========================================================================
1 - 파는 종목은 '어제 크게 움직인 종목' 이다
===========================================================================
                     전날%    그 전날%   전날 절대값%   전날 변동폭
  들어오는 종목      +0.007    +0.019      1.32         1.84
  빠지는 종목        +0.615    +0.050      2.60         3.79
  그대로 있는 종목    +0.052    +0.050      1.19         1.67

**이탈 종목의 전날 변동폭이 3.79 로, 그대로 있는 종목(1.67)의 2.3배다.**
절대값으로 봐도 2.60% 대 1.19% 로 두 배가 넘는다.

그런데 '그 전날' 은 +0.050 으로 그대로 있는 종목과 똑같다. 즉 **하루짜리
튐** 이다. 며칠에 걸쳐 나빠지는 게 아니라 하루 크게 움직이고 그 다음날
순위에서 밀린다.

방향도 한쪽이다. 이탈 종목의 전날 평균이 **+0.615%** 로 양수다.
**우리는 어제 오른 종목을 판다.** 떨어져서 파는 게 아니다.

들어오는 종목은 특별한 게 없다 (+0.007%, 변동폭 1.84). 그대로 있는
종목과 거의 같다. 즉 **교체는 '좋은 것을 발견해서' 가 아니라 '있던 것이
시끄러워져서' 일어난다.** 사는 쪽이 아니라 파는 쪽이 사건이다.

읽는 법: 이건 기계적으로 당연한 면이 있다. 저변동 순위는 60일 변동성
으로 매기므로, 하루 크게 움직이면 변동성이 올라가 순위가 밀린다.
그래도 두 가지는 미리 알기 어려웠다.
  (1) 며칠이 아니라 **하루** 로 갈린다는 것
  (2) 그 하루가 평균적으로 **오른** 날이라는 것

===========================================================================
2 - 교체가 일어나는 날은 특별한 날이 아니다
===========================================================================
시장 지표 13개를 '교체 있는 날(580일)' 과 '조용한 날(490일)' 로 나눴다.
차이를 그 지표의 표준편차로 나눠 적었다 (단위가 제각각이라서다).

  지표             교체 있는 날   조용한 날   차이(표준편차)  그전날 차이
  kr_ret5            -0.006      0.347       -0.096       -0.073
  kr_vol20            1.411      1.331       +0.092       +0.089
  us_dow              0.064      0.007       +0.061       -0.124
  flow_inst           0.819     -0.722       +0.047       +0.039
  kr_breadth5        44.105     44.551       -0.047       -0.025
  flow_foreign       -3.762     -2.161       -0.046       -0.126
  us_vix_chg          0.057      0.354       -0.038       +0.056
  fx_krw              0.030      0.006       +0.038       +0.037
  us_sp500            0.061      0.020       +0.038       -0.107
  us_sox              0.117      0.069       +0.019       -0.115
  us_nasdaq           0.056      0.034       +0.015       -0.091
  flow_indiv          0.959      1.081       -0.003       +0.075
  us_vix_level       19.140     19.141       -0.000       +0.025

**제일 큰 차이가 0.096 표준편차다.** 사실상 차이가 없다. 그리고 부호가
전날과 그전날에서 뒤집히는 것이 많다 (us_sp500 +0.038 -> -0.107,
us_dow +0.061 -> -0.124). 일관된 방향이 아니라 잡음이다.

뜻: **교체를 일으키는 것은 시장이 아니라 종목 자신이다.** 이건 이
저장소가 타이밍에서 23가지 가설, 지표 14개, 합의/계단식을 전부 실패한
것과 같은 이야기다. 시장 지표는 우리 결정을 설명하지 못한다.

굳이 방향을 읽자면 kr_vol20(국내 변동성)이 교체일에 높고 kr_ret5(시장
5일 수익률)가 낮다. 시장이 흔들리면 교체가 조금 더 생긴다는 뜻인데,
0.09 표준편차는 쓸 수 있는 크기가 아니다.

===========================================================================
그래서 뭘 할 수 있나 - 아직 아무것도 아니다
===========================================================================
1절은 **설명** 이지 **신호** 가 아니다. "어제 오른 종목을 판다" 는 사실을
알았다고 해서 그걸 바꾸면 좋아진다는 뜻이 아니다. 실제로 이 저장소는
이미 관련된 것들을 재봤고 전부 졌다.
  이벤트 교체 (순위 밀리면 그날 판다)      지그재그, 반띵 뒤집힘  [analyze_event_rebal]
  익절 (오르면 판다)                      12/12 짐              [analyze_original]
  하루 보유                               엣지는 있으나 수수료   [analyze_short_term]

다만 이 관찰은 **다음에 뭘 물어야 하는지** 를 좁힌다. "어제 크게 오른
탓에 밀려난 종목이 그 뒤에 어떻게 되나" 는 아직 이 형태로 안 재봤다.
재려면 사전 등록부터 해야 한다 (analyze_selectors.py 참고).

한계
  1) 738건은 겹친다. 같은 종목이 여러 번 드나든다.
  2) 2021~2026 한국 시장, 저변동 10종목 기준이다.
  3) 이건 기술(description)이다. 가설을 훑은 게 아니므로 다중검정이
     늘지 않는다. 대신 여기서 나온 것을 신호로 쓰려면 새로 등록해야 한다.

실행:
  python analyze_switch.py
"""
import csv
import glob
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_consensus as C  # noqa: E402
import analyze_event_rebal as E  # noqa: E402
import strategy as S  # noqa: E402

BASE_DI = 250
PICK = 10
KEYS = C.CSV_KEYS


def load_raw():
    """market_indicators_*.csv 를 {날짜: 행} 으로."""
    raw = {}
    for path in sorted(glob.glob(str(_ROOT / "data" / "market_indicators_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                raw[r["date"]] = r
    return raw


def ind_at(raw, dates, di, key):
    """di 일의 지표 값. 없으면 None. 앞 값을 끌어다 쓰지 않는다."""
    if di < 0 or di >= len(dates):
        return None
    try:
        return float(raw[dates[di]][key])
    except (KeyError, TypeError, ValueError):
        return None


def day_return(panel, code, di):
    """di 일의 전일 대비 수익률%. 빠진 날이 있으면 None."""
    s = panel.get(code)
    if s is None:
        return None
    a, b = s.pos.get(di), s.pos.get(di - 1)
    if a is None or b is None or not s.close[b]:
        return None
    return (s.close[a] / s.close[b] - 1) * 100


def switches(order, pick=PICK):
    """(di, 진입집합, 이탈집합, 유지집합). 하루 건너뛴 날은 버린다.

    상위 pick 은 자리 수가 고정이라 진입과 이탈이 같은 날 같은 수만큼
    일어난다. 이 함수가 그 사실을 그대로 드러낸다.
    """
    out = []
    dis = sorted(order)
    for k in range(1, len(dis)):
        di, pv = dis[k], dis[k - 1]
        if di != pv + 1:
            continue
        now, before = set(order[di][:pick]), set(order[pv][:pick])
        out.append((di, now - before, before - now, now & before))
    return out


def moves(panel, events, which):
    """그 무리의 전날/그전날 수익률 목록. which: 0=진입 1=이탈 2=유지."""
    r1, r2 = [], []
    for ev in events:
        for c in ev[1 + which]:
            v1 = day_return(panel, c, ev[0] - 1)
            v2 = day_return(panel, c, ev[0] - 2)
            if v1 is not None:
                r1.append(v1)
            if v2 is not None:
                r2.append(v2)
    return r1, r2


def summary(vals):
    """(평균, 절대값 평균, 표준편차, 개수)."""
    if not vals:
        return (0.0, 0.0, 0.0, 0)
    return (st.mean(vals), st.mean(abs(v) for v in vals),
            st.pstdev(vals), len(vals))


def gap_in_sd(a, b):
    """두 무리 평균 차이를 공통 표준편차로 나눈 값.

    지표마다 단위가 달라서 그냥 빼면 비교가 안 된다.
    """
    if not a or not b:
        return 0.0
    sd = st.pstdev(list(a) + list(b))
    return (st.mean(a) - st.mean(b)) / sd if sd else 0.0


def main():
    dates, panel = S.load_panel()
    print("순위 계산 중...", flush=True)
    order, _rank = E.daily_ranks(dates, panel, BASE_DI)
    raw = load_raw()
    events = switches(order)

    print(f"\n[0] 진입과 이탈은 같은 날 같은 수만큼 일어난다")
    n_in = sum(len(e[1]) for e in events)
    n_out = sum(len(e[2]) for e in events)
    print(f"  진입 {n_in:,}건 / 이탈 {n_out:,}건 "
          f"-> {'같다' if n_in == n_out else '다르다'}")
    print("  그래서 하루에 한 줄뿐인 시장 지표로는 둘을 구별할 수 없다.")

    print(f"\n[1] 그 종목 자신의 움직임")
    print(f"{'':<20}{'전날%':>10}{'그 전날%':>10}"
          f"{'전날 절대값%':>13}{'전날 변동폭':>12}{'표본':>9}")
    got = {}
    for idx, name in ((0, "들어오는 종목"), (1, "빠지는 종목"),
                      (2, "그대로 있는 종목")):
        r1, r2 = moves(panel, events, idx)
        got[name] = (r1, r2)
        m1, a1, s1, n1 = summary(r1)
        m2, _a2, _s2, _n2 = summary(r2)
        print(f"{name:<20}{m1:>+10.3f}{m2:>+10.3f}{a1:>13.2f}"
              f"{s1:>12.2f}{n1:>9,}", flush=True)
    ex_sd = summary(got["빠지는 종목"][0])[2]
    stay_sd = summary(got["그대로 있는 종목"][0])[2]
    if stay_sd:
        print(f"\n  이탈 종목의 전날 변동폭이 유지 종목의 "
              f"{ex_sd / stay_sd:.1f}배")

    print(f"\n[2] 교체가 일어나는 날 vs 조용한 날 (시장 지표)")
    turn, quiet = [], []
    for di, ent, _ex, _stay in events:
        row = {}
        for key in KEYS:
            a, b = ind_at(raw, dates, di - 1, key), ind_at(raw, dates, di - 2, key)
            if a is None or b is None:
                row = None
                break
            row[key] = (a, b)
        if row:
            (turn if ent else quiet).append(row)
    print(f"{'지표':<15}{'교체 있는 날':>13}{'조용한 날':>11}"
          f"{'차이(표준편차)':>15}{'그전날 차이':>13}")
    rows = []
    for key in KEYS:
        a = [r[key][0] for r in turn]
        b = [r[key][0] for r in quiet]
        if len(a) < 30 or len(b) < 30:
            continue
        g1 = gap_in_sd(a, b)
        g2 = gap_in_sd([r[key][1] for r in turn], [r[key][1] for r in quiet])
        rows.append((abs(g1), key, st.mean(a), st.mean(b), g1, g2))
    for _k, key, ma, mb, g1, g2 in sorted(rows, reverse=True):
        print(f"{key:<15}{ma:>13.3f}{mb:>11.3f}{g1:>+15.3f}{g2:>+13.3f}")
    if rows:
        big = max(rows)[0]
        print(f"\n  제일 큰 차이가 {big:.3f} 표준편차다. "
              f"{'사실상 차이가 없다.' if big < 0.2 else ''}")
    print(f"  교체 있는 날 {len(turn)}일 / 조용한 날 {len(quiet)}일")
    print("\n교체를 일으키는 것은 시장이 아니라 종목 자신이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
