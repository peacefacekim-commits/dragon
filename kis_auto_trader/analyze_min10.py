"""10분봉으로 무엇을 물을지 - 데이터가 생기기 전에 정해둔다.

(2026-09-21 신설) 사용자: "그럼 내일부터 장중 10분간 데이터들을 계속
수집하고 어떤 투자전략을 세울지 확인하자"

===========================================================================
지금이 사전 등록의 유일한 기회다
===========================================================================
이 파일을 쓰는 시점에 10분봉 데이터는 **한 줄도 없다.** 그러니 여기
적힌 기준은 결과를 보고 만든 것이 아니라는 게 확실하다. git log 로
순서를 확인할 수 있다.

이게 중요한 이유는 바로 오늘 겪었다. analyze_fundamentals 에서 PER/PBR
이 미리 정한 세 조건을 전부 통과했는데, 해마다 쪼개니 2025년 한 해가
전부였다. 조건 세 개가 서로 독립이 아니어서 못 걸렀다. 데이터가 쌓이면
**반드시 뭔가 보인다.** 우연이라도 보인다.

===========================================================================
0 - 다른 것보다 먼저 답할 것: 수수료를 넘을 수 있나
===========================================================================
규칙을 찾기 전에 판이 되는지부터 본다. analyze_short_term 이 일봉에서
했던 것과 같다 (거기서 손익분기가 2.3일로 나왔다).

일봉에서 역산한 값:
  하루 변동폭(고-저) 중앙값      5.80%   (최근 240일, 유니버스, 47,978건)
  10분 구간 변동폭 추정          0.93%   (하루 / sqrt(39))
  왕복 수수료                    0.21%   (매수 0.015 + 매도 0.015 + 거래세 0.18)
  => 10분 한 번에 구간 변동폭의 **23%** 를 먹어야 본전이다.

이건 추정이다. 10분봉이 쌓이면 실제로 재서 바꾼다. 그때 볼 표:

  보유시간    10분  60분  140분  종가까지
  평균 수익%    ?     ?     ?      ?
  수수료 뺀 뒤  ?     ?     ?      ?

(2026-09-22 수정) 원래 칸이 10/20/30/60분이었는데 실거래 중앙 보유가
**140.3분**이었다 (analyze_real_trades.py). 그 범위를 아예 못 덮고
있었으므로 10분 / 60분 / 140분 / 종가까지로 바꿨다. **데이터가 0행인
상태에서 고쳤다** - 결과를 보고 칸을 고른 것이 아니다.

**어느 칸도 양수가 아니면 조건을 아무리 붙여도 소용없다.** 그 경우
답은 '10분 매매는 이 수수료 구조에서 안 된다' 이고, 조건 찾기를
그만둔다. 이 판정을 먼저 하는 이유는, 판이 안 되는데 규칙을 찾으면
반드시 잡음을 줍게 되기 때문이다.

===========================================================================
1 - 시험할 것 다섯 가지. 늘리지 않는다
===========================================================================
방향도 미리 고정한다. 양방향을 보면 가짓수가 두 배가 된다.

  gap_fill    시가가 전일 종가보다 낮게 출발하면 그날 되돌린다
              (사용자의 원래 아이디어에 제일 가깝다)
  reversal    장 초반 30분에 많이 오른 종목은 그 뒤에 되돌린다
              (단기반전. 저변동/모멘텀 결과와 같은 방향이다)
  time_of_day 시간대에 따라 다르다 (09:00~10:00 vs 14:30~15:30 등)
  vol_spike   그 구간 거래량이 평소보다 크면 그 뒤가 다르다
  range_pos   그 구간 가격이 당일 고-저 범위의 아래쪽이면 그 뒤가 낫다

왜 이 다섯인가: 넷은 사용자가 실제로 쓰던 방식(단기 되돌림 매매)의
구성요소이고, time_of_day 는 '언제 거래를 쉴까' 를 묻는다. 이 저장소가
타이밍에서 23가지를 전부 놓쳤지만, 그건 전부 **날 단위** 타이밍이었다.
**하루 안의** 시간대는 한 번도 못 봤다 - 데이터가 없었기 때문이다.

===========================================================================
2 - 채택 조건 넷. 하나라도 걸리면 안 넣는다
===========================================================================
  1) **수수료를 뺀 뒤** 평균 순수익이 양수다.
     승률이 아니라 순수익으로 판정한다. 승률 60% 라도 이길 때 0.1%
     벌고 질 때 0.3% 잃으면 진다. 사용자가 며칠 연속 손해 본 것이
     바로 이 모양일 수 있다.
  2) 날짜 반띵 양방향에서 기준을 넘는다.
  3) 무작위 대조군을 넘는다 (같은 구간 수를 아무 때나 잡은 것).
  4) **날짜별 지속성** - 양수인 날이 과반을 넘고, 제일 좋은 날 하나를
     빼도 나머지 평균이 양수다.

4번이 핵심이다. 재무에서 2025년 한 해가 전부였던 것을 못 걸렀던 이유가
1~3번이 서로 독립이 아니어서였다. 분봉에서는 '한 날' 이 그 자리를
차지할 수 있다. 폭등한 하루가 전부를 만들면 4번에서 걸린다.

===========================================================================
3 - 얼마나 모아야 하나
===========================================================================
표본 크기는 금방 찬다 (일봉에서 역산):
  구간당 순엣지 0.05% 를 t=2 로 확인 -> 거래 1,380건
  구간당 순엣지 0.10% 를 t=2 로 확인 -> 거래   345건
  하루 수집량 = 150종목 x 39구간 = 5,850관측

그러니 **표본은 며칠이면 충분하다.** 진짜 제약은 '며칠에 걸쳐 같은
결과가 나오나' 다. 조건 4번이 그걸 본다.

  20거래일(약 1개월)  수집이 제대로 되는지 확인 + 0절 판정
  60거래일(약 3개월)  반띵과 날짜별 지속성이 뜻을 갖기 시작
  250거래일(약 1년)   시기를 나눠서 볼 수 있다

===========================================================================
4 - 미리 정해두는 처리 방식
===========================================================================
  체결 가정    그 구간 종가에 사고 판다. 시가에 사면 그 구간 안의
               정보를 쓰는 셈이라 선견이 된다.
  수수료       왕복 0.21% 를 모든 거래에 문다. 예외 없다.
  슬리피지     0 으로 둔다. 대신 결과에 '슬리피지 X% 면 뒤집힌다' 를
               같이 적는다 (analyze_knobs --fast 에서 쓴 방식).
  빠진 구간    그 종목 그 구간은 통째로 뺀다. 앞 값을 끌어오지 않는다.
  미래 정보    조건은 t 구간까지, 표적은 t+1 구간부터.
  시장 대비    그날 그 구간 전체의 동일가중 평균을 뺀다. 안 빼면
               '시장이 오른 구간' 을 맞힌 게 신호로 보인다.

===========================================================================
결과 - 아직 없음 (데이터가 없다)
===========================================================================
10분봉이 쌓이기 시작하면 여기에 채운다.

실행:
  python analyze_min10.py            # 데이터가 얼마나 모였나
  python analyze_min10.py --run      # 0절부터 (데이터가 충분해지면)
"""
import argparse
import csv
import glob
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

DATA_DIR = _ROOT / "data"
PREFIX = "krx_min10"

FEE_ROUND_TRIP = 0.21          # 왕복 %
# (2026-09-22 수정, 데이터 0행 상태에서) 실거래 중앙 보유가 140.3분이었다
# (analyze_real_trades.py). 원래 칸이 10~60분이라 실제 범위를 아예 못 덮었다.
# 1=10분, 6=60분, 14=140분(실거래 중앙), 39=당일 종가까지.
HOLD_BUCKETS = (1, 6, 14, 39)
HOLD_LABELS = {1: "10분", 6: "60분", 14: "140분", 39: "종가까지"}
# 실거래가 실제로 얼마나 자주 돌았나 -> 목표 문턱의 재료
# 완결 88건 / 거래일 26일 = 하루 3.4 왕복 (analyze_real_trades.py)
TRIPS_PER_DAY = 3.4
# Pro 구독료를 200만원으로 채우는 데 필요한 연수익률 (analyze_goal.py)
TARGET_ANNUAL = 16.8
SIGNALS = ("gap_fill", "reversal", "time_of_day", "vol_spike", "range_pos")

# 채택 조건
MIN_DAYS_FOR_VERDICT = 20      # 0절 판정에 필요한 최소 거래일
MIN_DAYS_FOR_RULES = 60        # 규칙 시험에 필요한 최소 거래일
PERM_ALPHA = 0.05

# 일봉에서 역산한 추정값. 10분봉이 쌓이면 실제 값으로 바꾼다.
EST_DAY_RANGE_PCT = 5.80
EST_BAR_RANGE_PCT = 0.93
# (2026-09-22, 1거래일) explore_min10.py 로 실제로 쟀다. 추정이 30% 크게
# 잡혀 있었다 - 하루 변동폭이 시간에 고르게 안 퍼져 있어서 sqrt 로 나누는
# 어림이 안 맞는다. 문턱이 나쁜 쪽으로 틀렸으므로 실측을 기본으로 쓴다.
#   추정 0.93% -> 수수료가 변동폭의 23%
#   실측 0.646% -> 수수료가 변동폭의 33%
# 거래일이 쌓이면 이 값을 다시 갱신해야 한다 (1거래일은 표본이 얇다).
MEASURED_BAR_RANGE_PCT = 0.646
MEASURED_DAYS = 1


def target_gross_per_trip(target_annual=TARGET_ANNUAL,
                          trips_per_day=TRIPS_PER_DAY,
                          fee=FEE_ROUND_TRIP, days_per_year=246):
    """구독료 목표를 채우려면 왕복당 수수료 전 몇 % 를 벌어야 하나.

    본전(수수료 0.21%)과 목표(Pro 16.8%)는 다른 문턱이다. 본전만 넘으면
    '안 잃는다' 이고, 목표를 넘어야 '구독료가 나온다'. 둘을 같이 찍는다.

    실거래 빈도(하루 3.4 왕복)를 그대로 쓴다. 빈도를 바꾸면 문턱도
    바뀌므로 판정할 때 실제 빈도로 다시 계산해야 한다.
    """
    trips = trips_per_day * days_per_year
    if trips <= 0:
        return float("inf")
    net = (1 + target_annual / 100) ** (1 / trips) - 1
    return net * 100 + fee

def load_min10():
    """krx_min10_*.csv 를 [(date, time, code, o, h, l, c, v)] 로."""
    rows = []
    for path in sorted(glob.glob(str(DATA_DIR / f"{PREFIX}_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                def num(k):
                    try:
                        return float(r[k]) if r.get(k) not in (None, "") else None
                    except (TypeError, ValueError):
                        return None
                rows.append((r.get("date"), r.get("time"), r.get("code"),
                             num("open"), num("high"), num("low"),
                             num("close"), num("volume")))
    return rows


def coverage(rows):
    """며칠 / 몇 종목 / 하루 평균 몇 구간 모였나."""
    days = sorted({r[0] for r in rows if r[0]})
    codes = {r[2] for r in rows if r[2]}
    per_day = {}
    for r in rows:
        if r[0]:
            per_day.setdefault(r[0], set()).add((r[1], r[2]))
    return {
        "days": len(days),
        "codes": len(codes),
        "rows": len(rows),
        "first": days[0] if days else None,
        "last": days[-1] if days else None,
        "per_day": (st.median(len(v) for v in per_day.values())
                    if per_day else 0),
    }


def fee_hurdle(bar_range=None, fee=FEE_ROUND_TRIP):
    """수수료가 구간 변동폭의 몇 %인가 = 넘어야 하는 문턱.

    bar_range 를 안 주면 **실측값**을 쓴다 (MEASURED_BAR_RANGE_PCT).
    실측이 없던 동안은 일봉에서 역산한 추정값(0.93%)을 썼는데,
    explore_min10.py 로 재보니 0.646% 였다. 추정이 30% 크게 잡혀
    있었으므로 문턱이 23% 가 아니라 33% 다.
    """
    r = bar_range if bar_range is not None else MEASURED_BAR_RANGE_PCT
    if not r:
        return float("inf")
    return fee / r * 100


def trades_needed(edge_pct, bar_sd_pct=EST_BAR_RANGE_PCT, t=2.0):
    """그 크기의 순엣지를 t 값 t 로 확인하는 데 필요한 거래 수."""
    if edge_pct <= 0:
        return float("inf")
    return (t * bar_sd_pct / edge_pct) ** 2


def net_edge(mean_gross_pct, fee=FEE_ROUND_TRIP):
    """수수료를 뺀 순수익. 채택 조건 1번이 보는 값.

    승률이 아니라 이것으로 판정한다. 승률 60% 여도 이길 때 조금 벌고
    질 때 크게 잃으면 진다.
    """
    return mean_gross_pct - fee


def slippage_flip(mean_gross_pct, fee=FEE_ROUND_TRIP):
    """슬리피지가 한쪽당 얼마면 순수익이 0이 되나.

    백테스트는 호가 스프레드를 안 넣는다. 그 여유가 얼마인지 같이
    적어야 결과를 읽을 수 있다 (analyze_knobs --fast 와 같은 방식).
    """
    left = mean_gross_pct - fee
    return left / 2 if left > 0 else 0.0


def day_persistence(daily_edges):
    """날짜별 순엣지 -> (양수인 날, 전체, 최고 날을 뺀 평균).

    채택 조건 4번. 폭등한 하루가 전부를 만든 경우를 잡는다.
    """
    vals = list(daily_edges)
    if len(vals) < 2:
        return (0, len(vals), 0.0)
    rest = list(vals)
    rest.remove(max(vals))
    return (sum(1 for v in vals if v > 0), len(vals), st.mean(rest))


def accepted(mean_gross_pct, first_beats, second_beats, perm_p,
             days_pos, days_total, rest_mean):
    """채택 조건 네 개를 전부 넘겼나. 결과를 보고 고치지 않는다."""
    return (net_edge(mean_gross_pct) > 0
            and first_beats and second_beats
            and perm_p < PERM_ALPHA
            and days_total > 0
            and days_pos * 2 > days_total
            and rest_mean > 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description="10분봉 전략 - 기준은 미리 정해뒀다")
    ap.add_argument("--run", action="store_true",
                    help="0절부터 실제로 돌린다 (데이터가 충분해지면)")
    args = ap.parse_args(argv)

    rows = load_min10()
    cov = coverage(rows)
    print(f"\n[10분봉 데이터]")
    if not rows:
        print("  아직 한 줄도 없습니다.")
        print("  내일 장 마감 뒤 'python fetch_intraday.py --check' 로")
        print("  응답을 먼저 확인한 다음 '매일 실행.bat' 을 돌리세요.")
    else:
        print(f"  {cov['days']}거래일 / {cov['codes']:,}종목 / {cov['rows']:,}행")
        print(f"  {cov['first']} ~ {cov['last']}, 하루 평균 {cov['per_day']:,.0f}구간")

    print(f"\n[수수료 문턱] (일봉에서 역산한 추정값)")
    print(f"  하루 변동폭 중앙값      {EST_DAY_RANGE_PCT:.2f}%")
    print(f"  10분 구간 변동폭 추정   {EST_BAR_RANGE_PCT:.2f}%")
    print(f"  왕복 수수료             {FEE_ROUND_TRIP:.2f}%")
    print(f"  => 구간 변동폭의 {fee_hurdle():.0f}% 를 먹어야 본전")

    print(f"\n[필요한 표본]")
    for e in (0.05, 0.10, 0.21):
        print(f"  구간당 순엣지 {e:.2f}% 확인 -> 거래 {trades_needed(e):,.0f}건")

    need = MIN_DAYS_FOR_VERDICT - cov["days"]
    print(f"\n[진행]")
    print(f"  0절 판정(수수료를 넘나)까지 {max(0, need)}거래일 남음 "
          f"(기준 {MIN_DAYS_FOR_VERDICT}일)")
    print(f"  규칙 시험까지 {max(0, MIN_DAYS_FOR_RULES - cov['days'])}거래일 남음 "
          f"(기준 {MIN_DAYS_FOR_RULES}일)")

    if not args.run:
        print(f"\n시험할 것 {len(SIGNALS)}가지 (늘리지 않는다): {', '.join(SIGNALS)}")
        print("채택 조건 4개. --run 은 데이터가 충분해지면 씁니다.")
        return 0

    if cov["days"] < MIN_DAYS_FOR_VERDICT:
        print(f"\n[!] {MIN_DAYS_FOR_VERDICT}거래일이 안 됐습니다. 돌려도 뜻이 없습니다.")
        return 1
    print("\n[!] 0절 계산은 데이터가 모인 뒤에 채웁니다 (아직 미구현).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
