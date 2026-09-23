"""두 전략 정면 비교 - 흔들리는 걸 사고팔기 vs 안 흔들리는 걸 드물게.

(2026-09-21 신설) 사용자: "그 두가지 상반되는 전략이 있는데 그걸 비교
해줄래? 하나는 변동이 큰 주식들을 사고 팔면서 이득을 노리기 / 다른 하는
안정적으로 우상향하는 주식을 적당히 사고 팔면서 이득을 노리기"

흩어진 숫자를 모으는 게 아니라 **완전히 같은 조건에서 나란히** 돌린다.
같은 후보 풀, 같은 자본 200만원, 같은 수수료, 같은 1주 단위 제약,
같은 시작일 5개. 다른 것은 선정 기준과 교체 주기뿐이다.

'안정적으로 우상향' 을 저변동과 따로 넣은 이유
  저변동은 '안 흔들린다' 이고 추세는 '올라간다' 다. 같은 종목일 수도
  아닐 수도 있다. 사용자의 표현에 더 가까운 것은 사실 추세 쪽이라,
  섞지 않고 셋으로 나눠서 쟀다.

===========================================================================
결과 (시작일 5개 중앙값)
===========================================================================
  선정          주기   연수익%  최대낙폭%  최악1년%  회복최장  수수료/자본%  거래수
  고변동        20일   -53.7    -97.2    -77.0    1071일      1.6      497
  고변동       120일   -41.5    -95.1    -66.7    1071일      0.7      150
  저변동        20일   +20.2    -16.2     -8.2     378일      5.1      324
  저변동       120일   +22.0    -15.9    -12.7     379일      1.5       95
  우상향(추세)   20일   -31.5    -86.3    -72.8     849일      3.2      636
  우상향(추세)  120일   -30.9    -88.3    -58.3     839일      1.1      154

===========================================================================
1 - 변동이 큰 주식 매매는 압도적으로 진다
===========================================================================
고변동 20일은 연 -53.7%, 최대낙폭 -97.2% 다. 200만원이 6만원이 된다.
최악의 1년에 -77.0% 를 맞는다.

그리고 **자주 거래할수록 더 나빠진다** (120일 -41.5% -> 20일 -53.7%).
수수료 탓이 아니다. 수수료는 자본의 1.6% 뿐이다. 흔들리는 종목은 거래
기회를 줄수록 손해가 커진다.

===========================================================================
2 - '안정적으로 우상향' 을 고르면 고변동 쪽에 붙는다 (새로 나온 것)
===========================================================================
우상향(추세) 선정은 연 -30.9%, 최대낙폭 -88.3% 다. 저변동이 아니라
고변동 쪽에 가깝다.

읽는 방법: '지금까지 올라온 것' 을 고르면 이미 많이 오른 종목을 사게
되고, 그건 대개 변동이 큰 종목이다. analyze_pools.py 에서 모멘텀이
생존편향을 걷으니 -4.76%p 였던 것과 같은 방향이다.

**'안정적' 과 '우상향' 이 실제로는 다른 종목을 가리킨다.** 둘 중
작동하는 것은 '안정적' 쪽이다. 직관적으로는 우상향이 더 그럴듯한데
숫자는 반대다.

===========================================================================
3 - 선정이 주기보다 35배 중요하다
===========================================================================
  바꾼 것                        수익 변화
  선정 (고변동 -> 저변동, 120일)  -41.5% -> +22.0%   63.5%p
  주기 (20일 -> 120일, 저변동)    +20.2% -> +22.0%    1.8%p

손잡이(주기)가 만드는 차이가 선정이 만드는 차이의 1/35 다.
analyze_knobs.py 의 '손잡이는 안 움직인다' 와 같은 결론이 다른 각도에서
다시 나온다.

다만 주기를 짧게 하면 수수료는 확실히 는다 (저변동 1.5% -> 5.1%, 3.4배).
얻는 것 없이 비용만 는다.

===========================================================================
3b - 선정은 켜짐/꺼짐이 아니라 단계적이다 (--slice, 2026-09-21 추가)
===========================================================================
사용자: "이 전략의 핵심은 종목선정이라고 보거든"

위의 뒤집기는 **양 끝** 만 본다 (저변동 10 vs 고변동 10). 중간을 안
보면 '저변동을 고르면 켜지고 아니면 꺼지는' 스위치인지, 순위를 따라
조금씩 나빠지는 것인지 모른다. 그래서 10칸씩 잘라서 각각 샀다.

  (120일, 10종목, 조건 전부 동일, 시작일 5개)
    순위 구간     연수익%   최소    최대   최대낙폭%
    1~10위        22.0    16.7    26.6    -15.9
    11~20위       11.0     7.2    17.1    -27.1
    21~30위       15.7     3.4    28.9    -32.9
    31~40위       16.4     8.8    32.0    -38.3
    51~60위       19.0    13.1    25.5    -39.7
    101~110위      9.1    -1.4    31.1    -56.3

**최대낙폭이 순위를 따라 한 방향으로 나빠진다** (-15.9 -> -27.1 ->
-32.9 -> -38.3 -> -39.7 -> -56.3). 여섯 칸 전부 단조롭다. 이건 저변동
점수가 진짜 신호라는 뜻이다. 우연이라면 이렇게 줄을 서지 않는다.

연수익은 들쭉날쭉하다 (11.0 / 15.7 / 16.4 / 19.0 / 9.1). 즉 저변동
점수가 잘 맞히는 것은 **얼마나 벌지가 아니라 얼마나 깨질지** 다.
analyze_why.py 의 '낮은 베타 + 비대칭' 과 같은 이야기가 다른 각도에서
나온다.

실무적으로 중요한 것: 1~10위와 11~20위의 차이가 22.0% 대 11.0% 다.
**한 칸만 밀려도 절반이 날아간다.** 선정을 대충 해도 되는 게 아니다.

===========================================================================
4 - 맞교환이 없다
===========================================================================
보통은 '수익을 더 얻으려면 위험을 더 진다' 인데 여기서는 그 맞교환조차
없다. 저변동이 수익도 높고 낙폭도 작고 회복도 빠르다.

                 고변동 20일    저변동 120일
  연수익           -53.7%        +22.0%
  최대낙폭         -97.2%        -15.9%
  최악 1년         -77.0%        -12.7%
  회복 최장     1,071일(4.4년)   379일(1.5년)

===========================================================================
읽는 법
===========================================================================
1) 이건 가설 탐색이 아니라 **기술(description)** 이다. 여섯 칸을 훑어서
   제일 좋은 것을 고른 게 아니라, 사용자가 지목한 두 갈래를 같은 자로
   재서 보인 것이다. 그래서 다중검정이 늘지 않는다.
2) 최악1년과 회복최장을 넣은 이유: 연수익만 보면 '그 6년을 버틸 수
   있느냐' 가 안 보인다. 연 20% 여도 중간에 1년 -30% 를 지나가야 한다면
   실제로는 못 버틴다.
3) 우상향이 지는 것은 이 저장소에 없던 새 측정이다. 사용자의 표현에
   가장 가까운 후보였으므로 따로 남겨둔다.
4) 2021~2026 한국 시장의 결과다. 다른 시기 다른 시장에서 같다는 보장은
   없다. 특히 강한 상승장에서는 순위가 달라질 수 있다 (analyze_why.py
   의 손익분기 1.318 참고).

실행:
  python analyze_styles.py            # 세 가지 선정 x 두 주기
  python analyze_styles.py --slice    # 저변동 순위 구간별
"""
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import strategy as S  # noqa: E402

CAPITAL = E.CAPITAL
BASE_DI = 250
PICK = 10
DAYS_PER_YEAR = 246
N_STARTS, START_GAP = 5, 37
PERIODS = (20, 120)
STYLES = ("고변동", "저변동", "우상향(추세)")


def ranks_by(dates, panel, factor, base=BASE_DI):
    """그 팩터 점수가 높은 순서. factor_score 는 미래 정보를 안 쓴다."""
    out = {}
    for di in range(base, len(dates)):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := S.factor_score(panel, c, di, factor)) is not None]
        if len(sc) >= PICK:
            sc.sort(reverse=True)
            out[di] = [c for _s, c in sc]
    return out


def flip(order):
    """순서를 뒤집는다. 저변동 순위를 뒤집으면 고변동이 된다.

    풀도 주기도 그대로이므로 차이가 전부 '어느 쪽을 고르나' 에서 온다.
    """
    return {di: lst[::-1] for di, lst in order.items()}


def _starts():
    """시작일. 한 군데서만 만든다 - 전략마다 다른 날에서 재면 비교가 깨진다."""
    return [BASE_DI + k * START_GAP for k in range(N_STARTS)]


def sliced(order, lo, hi):
    """순위 lo~hi 구간만 산다.

    뒤집기(flip)는 양 끝(저변동 10 vs 고변동 10)만 본다. 이건 **중간**
    을 본다. 선정 신호가 켜짐/꺼짐인지, 아니면 순위를 따라 단계적으로
    나빠지는지가 여기서 갈린다.
    """
    return {di: lst[lo:hi] for di, lst in order.items() if len(lst) >= hi}


def monotone(vals):
    """값이 한 방향으로만 가는가. 단계적 신호인지 판정하는 데 쓴다."""
    return (all(a >= b for a, b in zip(vals, vals[1:]))
            or all(a <= b for a, b in zip(vals, vals[1:])))


def run(dates, panel, order, period, start, pick=PICK, capital=CAPITAL):
    """부분교체. (곡선, 수수료, 거래수)"""
    n = len(dates)
    cash, hold, fees, ntr = float(capital), {}, 0.0, 0
    curve, di = [], start
    while di < n:
        if (di - start) % period == 0 and di in order:
            new = order[di][:pick]
            keep = {c: q for c, q in hold.items() if c in new}
            for c in [c for c in hold if c not in new]:
                v = E.price(panel, c, di)
                if v:
                    cash += hold[c] * v * (1 - E.FEE_ONE_WAY)
                    fees += hold[c] * v * E.FEE_ONE_WAY
                    ntr += 1
            add = [c for c in new if c not in hold]
            got, cash, f = (E.buy_greedy(panel, cash, add, di) if add
                            else ({}, cash, 0.0))
            fees += f
            ntr += len(got)
            hold = {**keep, **got}
        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, fees, ntr


def mdd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def annualized(curve, capital=CAPITAL):
    if not curve:
        return 0.0
    return ((curve[-1] / capital) ** (DAYS_PER_YEAR / len(curve)) - 1) * 100


def worst_year(curve, window=DAYS_PER_YEAR):
    """1년을 들고 있었을 때 최악의 결과%.

    연수익만 보면 '그 기간을 버틸 수 있느냐' 가 안 보인다. 연 20% 여도
    중간에 1년 -30% 를 지나가야 하면 실제로는 못 버틴다.
    """
    if len(curve) <= window:
        return 0.0
    return min((curve[i + window] / curve[i] - 1) * 100
               for i in range(len(curve) - window))


def underwater(curve):
    """전 고점을 못 넘은 최장 구간(거래일)."""
    peak, worst, run_len = curve[0], 0, 0
    for v in curve:
        if v >= peak:
            peak, run_len = v, 0
        else:
            run_len += 1
            worst = max(worst, run_len)
    return worst


def tradeoff(a_ret, a_dd, b_ret, b_dd):
    """수익-위험 맞교환이 있나.

    보통은 '수익이 높으면 낙폭도 크다' 다. 한쪽이 수익도 높고 낙폭도
    작으면 맞교환이 없는 것이고, 그건 고를 이유가 분명하다는 뜻이다.
    """
    return not (b_ret > a_ret and abs(b_dd) < abs(a_dd))


SLICES = (0, 10, 20, 30, 50, 100)


def report_slices(dates, panel, order):
    """순위 구간별. '선정이 핵심' 이 맞다면 여기서 기울기가 보여야 한다."""
    starts = _starts()
    print(f"\n저변동 순위를 10칸씩 잘라서 ({PERIODS[-1]}일, {PICK}종목, 조건 동일)")
    print(f"{'순위 구간':<14}{'연수익%':>9}{'최소':>8}{'최대':>8}{'최대낙폭%':>11}")
    rows = []
    for lo in SLICES:
        od = sliced(order, lo, lo + PICK)
        if not od:
            continue
        curves = [run(dates, panel, od, PERIODS[-1], s)[0] for s in starts]
        rs = [annualized(c) for c in curves]
        ds = [mdd(c) for c in curves]
        rows.append((lo, st.median(rs), min(rs), max(rs), st.median(ds)))
        print(f"{f'{lo+1}~{lo+PICK}위':<14}{st.median(rs):>9.1f}{min(rs):>8.1f}"
              f"{max(rs):>8.1f}{st.median(ds):>11.1f}", flush=True)
    dds = [r[4] for r in rows]
    print(f"\n낙폭이 순위를 따라 한 방향인가: "
          f"{'그렇다 (단계적 신호)' if monotone(dds) else '아니다'}")
    print(f"  1~{PICK}위 {dds[0]:.1f}%  ->  "
          f"{rows[-1][0]+1}~{rows[-1][0]+PICK}위 {dds[-1]:.1f}%")
    print(f"연수익이 한 방향인가: "
          f"{'그렇다' if monotone([r[1] for r in rows]) else '아니다 (들쭉날쭉)'}")
    return rows


def main():
    dates, panel = S.load_panel()
    print("순위 계산 중...")
    lo = ranks_by(dates, panel, "low_vol")
    if "--slice" in sys.argv[1:]:
        report_slices(dates, panel, lo)
        return 0
    orders = {"저변동": lo, "고변동": flip(lo),
              "우상향(추세)": ranks_by(dates, panel, "trend")}
    starts = _starts()

    print(f"\n{CAPITAL:,}원 / {PICK}종목 / 부분교체 / 시작일 {N_STARTS}개 중앙값")
    print(f"{'선정':<14}{'주기':>6}{'연수익%':>9}{'최대낙폭%':>10}{'최악1년%':>9}"
          f"{'회복최장':>9}{'수수료/자본%':>12}{'거래수':>7}")
    box = {}
    for who in STYLES:
        for period in PERIODS:
            rows = []
            for s in starts:
                c, f, n = run(dates, panel, orders[who], period, s)
                rows.append((annualized(c), mdd(c), worst_year(c),
                             underwater(c), f / CAPITAL * 100, n))
            med = [st.median(r[i] for r in rows) for i in range(6)]
            box[(who, period)] = med
            print(f"{who:<14}{period:>5}일{med[0]:>9.1f}{med[1]:>10.1f}"
                  f"{med[2]:>9.1f}{med[3]:>9.0f}{med[4]:>12.1f}{med[5]:>7.0f}")

    hi, low = box[("고변동", 120)], box[("저변동", 120)]
    fast, slow = box[("저변동", 20)], box[("저변동", 120)]
    print(f"\n선정을 바꾸면 {hi[0]:.1f}% -> {low[0]:.1f}% "
          f"({low[0] - hi[0]:.1f}%p)")
    print(f"주기를 바꾸면 {fast[0]:.1f}% -> {slow[0]:.1f}% "
          f"({slow[0] - fast[0]:.1f}%p)")
    if abs(slow[0] - fast[0]) > 0:
        print(f"=> 선정이 주기보다 {abs(low[0]-hi[0])/abs(slow[0]-fast[0]):.0f}배 중요하다")

    a, b = box[("고변동", 20)], box[("저변동", 120)]
    print(f"\n수익-위험 맞교환이 있나: "
          f"{'있다' if tradeoff(a[0], a[1], b[0], b[1]) else '없다 (저변동이 양쪽 다 낫다)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
