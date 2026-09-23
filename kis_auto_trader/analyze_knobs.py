"""손잡이 훑기 - 종목 수 / 교체 주기 / 변동성 측정 기간. 하나도 못 바꾼다.

(2026-09-19 신설) 사용자: "지금 거래 방법에서 이윤을 얻을 수 있는 방법을
찾아봐"

지금까지 잰 것들(손절/익절/타이밍/이벤트교체)은 전부 **신호를 어떻게 쓸까**
였다. 이 파일은 **신호를 어떻게 만들까** 와 **얼마나 나눠 담을까** 를 본다.
엣지가 나오는 유일한 차원이 선정이므로, 남은 손잡이도 거기 있다.

훑은 것
  종목 수      3, 5, 10, 15, 20, 30
  교체 주기    40, 60, 120 거래일
  vol_days     20, 40, 60, 90, 120, 250   (low_vol 을 며칠로 재는가)

채택 조건을 미리 정해두고 시작했다. 24가지를 훑으면 순전히 우연으로도
1~2개는 좋아 보이기 때문이다.
  1) 손잡이를 돌릴 때 성과가 매끄럽게 변해야 한다 (지그재그면 잡음)
  2) 반띵 양방향 통과
  3) 시작일 5개에서 일관 (중앙값만 좋고 최소값이 나쁘면 탈락)
셋 다 넘겨야 바꾼다.

===========================================================================
결과 0 - 기준점: 저변동을 고르는 것 자체가 얼마나 큰가 (--flip)
===========================================================================
손잡이를 논하기 전에 기준점이 필요하다. 같은 후보 풀에서 **순서만 뒤집어서**
고변동 10종목을 사면 어떻게 되는지 본다. 풀도 주기도 부분교체도 전부 같고
고르는 방향만 반대다. 그래서 차이가 전부 '선정' 에서 온다.

  (120일 주기, 부분교체, 시작일 5개 중앙값)
                  연수익    최대낙폭
    저변동 10     +22.0%    -15.9%
    고변동 10     -41.5%    -95.1%

  (2026-09-21 추가) 이 숫자는 원래 임시 스크립트로만 재고 모듈에 안
  넣어뒀다. 그랬더니 결론.py 가 출처 없는 숫자를 인용하게 됐고
  tests/test_결론.py 가 그걸 잡았다. 그래서 --flip 으로 재현할 수 있게
  옮겼다. 요약에 쓸 숫자는 돌릴 수 있는 자리에 있어야 한다.

아래 손잡이들이 만드는 차이는 전부 이것보다 훨씬 작다. 그게 이 파일의
결론이기도 하다.

===========================================================================
결과 1 - 종목 수 x 교체 주기: 10~15종목 바깥은 확실히 나쁘다
===========================================================================
시작일 5개의 중앙값.

  종목수  주기   연수익   최소   최대   낙폭    수익/낙폭
     3    40     10.6    6.3  26.2  -21.2     0.50
     3   120     16.7   14.7  22.4  -19.6     0.85
     5    40     17.7   13.2  23.6  -17.5     1.01
     5   120     18.2    9.3  28.3  -18.7     0.97
    10    40     19.4   15.2  22.9  -16.4     1.19
    10   120     22.0   16.7  26.6  -15.9     1.38   <- 지금 설정
    15    40     19.3   18.4  19.8  -18.5     1.04
    15   120     19.1   15.1  23.6  -18.2     1.05
    20   120     17.3   14.5  19.2  -19.6     0.88
    30    40     15.3   14.5  17.7  -22.4     0.68

집중(3~5종목)은 수익도 낮고 낙폭도 크다. 양쪽 다 나쁘다.
분산(20~30종목)도 낙폭이 오히려 커진다.
10종목이 골짜기가 아니라 봉우리다.

왜 집중이 안 먹히나: 저변동 엣지는 "1등 종목이 제일 좋다" 가 아니라
"저변동 무리가 고변동 무리를 이긴다" 다. 무리의 성질이지 순위의 성질이
아니다. 그래서 3종목으로 좁히면 엣지가 진해지는 게 아니라 개별 종목의
잡음만 커진다.

**다만 10/120 이 1등인 것을 그대로 믿으면 안 된다.** 최소값으로 보면
순위가 바뀐다.
    10종목 120일   중앙 22.0 / 최소 16.7 / 최대 26.6  (폭 9.9%p)
    15종목  40일   중앙 19.3 / 최소 18.4 / 최대 19.8  (폭 1.4%p)
중앙값 차이 2.7%p 는 시작일 잡음 9.9%p 보다 작다. 그러니 "10/120 이
15/40 보다 낫다" 고 말할 근거는 없다. 말할 수 있는 건 3~5종목과
20~30종목이 나쁘다는 것까지다.

===========================================================================
결과 2 - 20~30종목이 나쁜 건 돈이 모자라서가 아니다
===========================================================================
200만원에 30종목이면 슬롯당 6.7만원이라, 1주 단위 제약에 걸려서 못 사고
현금이 놀아서 나쁜 것일 수 있다. 그래서 교체 때마다 남는 현금을 쟀다.

  종목수    노는 현금 평균    연수익 중앙   낙폭 중앙
     5          0.6%          18.2      -18.7
    10          0.5%          22.0      -15.9
    15          0.4%          19.1      -18.2
    20          0.5%          17.3      -19.6
    30          0.4%          16.4      -21.6

노는 현금이 종목 수와 상관없이 0.4~0.6% 다. 남은 돈으로 싼 것부터 1주씩
더 사는 방식이 제 역할을 한다. 즉 **돈이 모자라서 나쁜 게 아니다.**
(주의: 이건 "현금이 안 논다" 까지만 말한다. 슬롯당 금액이 작아지면 1주
단위 때문에 종목별 비중이 들쭉날쭉해지는데, 그건 따로 안 쟀다.)

===========================================================================
결과 3 - vol_days: 지그재그다. 조건 1에서 바로 걸린다
===========================================================================
low_vol 을 며칠로 재는가. 신호 자체를 정의하는 값인데 한 번도 안 건드려
봤다. 처음 코드 쓸 때 60 으로 정해놓고 그대로였다.

  vol_days   연수익 중앙   최소   최대   낙폭 중앙   수익/낙폭
       20       20.9     18.2  21.8    -22.0      0.95
       40       18.8     17.2  27.0    -16.9      1.11
       60       22.0     16.7  26.6    -15.9      1.38
       90       17.4     15.5  22.6    -16.3      1.06
      120       19.8     12.5  23.9    -18.1      1.09
      250       19.0     14.1  28.5    -17.1      1.11

  20.9 -> 18.8 -> 22.0 -> 17.4 -> 19.8 -> 19.0

오르내린다. 짧게 잴수록 좋아진다거나 길게 잴수록 좋아진다는 방향이 없다.
조건 1(매끄러운 곡선)에서 걸리므로 2, 3 은 보지 않았다.

크기로 따져도 같은 결론이다. 중앙값의 폭은 17.4~22.0 = 4.6%p 인데,
설정 하나 안에서 시작일만 바꿨을 때의 폭이 최대 11.4%p(vol_days 120:
12.5~23.9) 다. **손잡이가 만든 차이가 시작일 운보다 작다.** 고를 수 없다.

=> vol_days 는 60 그대로 둔다. 20 이든 250 이든 구별이 안 되기 때문이지,
   60 이 좋다는 것을 확인해서가 아니다.

===========================================================================
읽는 법 - 이 파일의 진짜 결론
===========================================================================
1) 손잡이 24가지를 훑어서 바꿀 만한 것이 하나도 안 나왔다. 그리고
   그때마다 마침 지금 설정이 1등이었다. 이건 지금 설정이 훌륭해서가
   아니라, **손잡이들이 애초에 성과를 별로 안 움직이기 때문**이다.
   손잡이가 만드는 차이가 시작일 운에 묻힌다.

2) 그래서 지금 전략에 실제로 작동하는 부분은 둘뿐이다.
     저변동 선정   낙폭 -95% -> -16%, 수익 -41% -> +22%  (6년 내내)
     부분교체      수수료 3~5배 절감, 6/6 기간에서 전량교체를 이김
   나머지는 전부 "돌려도 안 움직이는 손잡이" 였다.

3) 그러니 파라미터를 더 훑는 건 이제 잡음을 줍는 일이다. 남은 방향은
   손잡이가 아니라 **새 신호**다. 지금 손에 있는 것 중 아직 안 쓴 것은
   배당수익률 / PER / PBR 이다 (1,813종목 중 30종목만 모여 있어서
   fetch_krx_extra.py --what fundamental 로 채워야 쓸 수 있다).
   그게 선정 차원이라는 점이 중요하다 - 엣지가 나온 유일한 차원이다.

4) 다중검정 누적: 이 저장소에서 지금까지 훑은 설정이 24가지(이 파일)
   + 타이밍 23가지 + 손절/익절 12가지 + 이벤트 버퍼 7가지 + 재활용
   4가지 = 70가지쯤 된다. 이 중 "좋아 보이는 것" 이 두세 개 나오는 건
   우연으로도 생긴다. 앞으로 뭘 재든 반띵과 시작일을 먼저 통과시킨다.

===========================================================================
결과 4 - 주기를 하루까지 좁히면 (--fast, 2026-09-21 추가)
===========================================================================
사용자: "매매 주기를 더 좁히면 어떻게 될까? 한번 하루, 일주일, 이주
삼주 이렇게 계산해봐"

위의 훑기는 40일부터였다. 그 아래를 안 봤으므로 새로 쟀다.

  (저변동 10종목, 부분교체, 시작일 5개 중앙값)
    주기         연수익%   최소   최대   낙폭%   연 주문일
    1일(매일)      25.1   22.4   26.7   -18.8    246.0
    5일(1주)      22.4   20.8   23.2   -18.3     49.2
    10일(2주)     20.9   16.7   25.4   -17.1     24.6
    15일(3주)     20.2   15.5   22.3   -17.2     16.4
    20일          20.2   16.1   24.7   -16.2     12.3
    120일         22.0   16.7   26.6   -15.9      2.1

매일 갈아타는 것이 25.1% 로 제일 높게 나온다. 최소값 22.4% 도 다른
어떤 주기의 중앙값보다 높다. **그럼에도 채택하지 않는다.** 이유가 셋
이고, 셋 다 따로 잰 것이다.

(1) 반띵에서 뒤집힌다
    전반부 / 후반부, 기준은 120일 (8.5 / 15.6)
      1일    5.4 / 37.9   뒤집힘   <- 전반부에서 기준에 진다
      5일    5.9 / 31.6   뒤집힘
      10일   6.4 / 35.9   뒤집힘
      15일  11.5 / 24.2   양쪽 이김
      20일   7.6 / 35.9   뒤집힘
    짧은 주기의 우위가 **후반부에만** 있다. 시기 하나에 기댄 결과다.
    (15일만 양쪽을 넘는데, 정작 5개 시작일 중앙값은 20.2% 로 120일의
    22.0% 에 진다. 두 잣대가 어긋나는 것 자체가 잡음의 표시다.)

(2) 슬리피지 0.08% 에서 우위가 사라진다
    백테스트는 수수료만 넣고 **호가 스프레드와 체결 밀림을 안 넣는다.**
    120일은 거래가 95건이라 상관없지만 1일은 1,250건이다.

      주기      슬립0%  0.05%  0.10%  0.20%  0.30%
      1일        25.1   23.1   19.4   15.1   14.6
      5일        22.4   22.0   20.5   17.5   15.4
      120일      22.0   22.0   22.0   21.5   21.2

    0.10% 만 물려도 1등이 120일로 바뀐다. 한국 시장 호가 단위상
    5만원짜리 주식의 한 틱이 50원(0.1%)이므로 반스프레드만 0.05%,
    거기에 체결 밀림이 더 붙는다. **1일의 우위는 측정하지 않은 비용
    안에 들어가 있다.** 반면 120일은 슬리피지 0.30% 에서도 21.2% 로
    거의 안 흔들린다.

(3) 낙폭이 나빠진다 (-15.9% -> -18.8%)
    사용자의 목적은 '큰 이득을 포기하더라도 큰 손해를 피한다' 다.
    방향이 반대다.

읽는 법: 주기를 좁히면 순위가 더 싱싱해지는 것은 사실이다(수수료를 0으로
놓으면 1일이 26.6%, 120일이 21.1%). 그런데 그 이득이 거래비용과 같은
크기라서, 비용을 정확히 모르는 한 어느 쪽이 이기는지 말할 수 없다.
그리고 우리는 비용을 정확히 모른다.

실행:
  python analyze_knobs.py            # 종목 수 x 주기
  python analyze_knobs.py --vol      # vol_days (오래 걸린다)
  python analyze_knobs.py --flip     # 기준점 (고변동과 견주기)
  python analyze_knobs.py --fast     # 하루~3주 주기 + 슬리피지 민감도
"""
import argparse
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import strategy as S  # noqa: E402

CAPITAL = E.CAPITAL
DAYS_PER_YEAR = 246
BASE_DI = 250
N_STARTS, START_GAP = 5, 37
PICKS = (3, 5, 10, 15, 20, 30)
PERIODS = (40, 60, 120)
VOL_DAYS = (20, 40, 60, 90, 120, 250)
# 짧은 주기 (--fast). 사용자: "매매 주기를 더 좁히면 어떻게 될까?"
FAST_PERIODS = (1, 5, 10, 15, 20, 120)
FAST_LABELS = {1: "1일(매일)", 5: "5일(1주)", 10: "10일(2주)", 15: "15일(3주)"}
# 슬리피지 (호가 스프레드 + 체결 밀림). 한쪽당, 수수료에 더해서 문다.
SLIPPAGES = (0.0, 0.0005, 0.0010, 0.0020, 0.0030)


def label_of(period):
    return FAST_LABELS.get(period, f"{period}일")


def ranks(dates, panel, base, vol_days=60, usize=None, least=10):
    """날짜별 저변동 순위. vol_days 를 바꿔가며 부를 수 있게 열어뒀다."""
    usize = usize if usize is not None else S.UNIVERSE_SIZE
    order = {}
    for di in range(base, len(dates)):
        cand = S.universe_at(panel, di, usize, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := S.factor_score(panel, c, di, "low_vol",
                                      vol_days=vol_days)) is not None]
        if len(sc) >= least:
            sc.sort(reverse=True)
            order[di] = [c for _s, c in sc]
    return order


def run(dates, panel, order, period, start, pick, upto=None, capital=CAPITAL):
    """부분교체. (곡선, 교체 때 남은 현금 비율 평균%)

    남는 현금을 같이 돌려주는 이유: 종목 수를 늘렸을 때 성과가 나빠지면
    '분산이 해로운 것' 과 '1주 단위 때문에 못 사서 돈이 노는 것' 을
    구별해야 하는데, 그걸 구별하는 값이다.
    """
    n = upto if upto is not None else len(dates)
    cash, hold, idle = float(capital), {}, []
    curve, di = [], start
    while di < n:
        if (di - start) % period == 0 and di in order:
            new = order[di][:pick]
            keep = {c: q for c, q in hold.items() if c in new}
            for c in [c for c in hold if c not in new]:
                v = E.price(panel, c, di)
                if v:
                    cash += hold[c] * v * (1 - E.FEE_ONE_WAY)
            add = [c for c in new if c not in hold]
            got, cash, _f = (E.buy_greedy(panel, cash, add, di) if add
                             else ({}, cash, 0.0))
            hold = {**keep, **got}
            tot = cash + sum(q * (E.price(panel, c, di, "close") or 0)
                             for c, q in hold.items())
            if tot:
                idle.append(cash / tot * 100)
        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, (st.mean(idle) if idle else 0.0)


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


def beats_noise(medians, worst_start_spread):
    """손잡이가 만든 차이가 시작일 운보다 큰가.

    작으면 그 손잡이로는 고를 수 없다. analyze_event_rebal.pickable() 과
    같은 생각이고, 거기서 '두 배는 돼야 한다' 고 정한 기준을 그대로 쓴다.
    """
    if len(medians) < 2:
        return False
    return (max(medians) - min(medians)) >= worst_start_spread * 2


def capital_bound(idle_pct, limit=5.0):
    """돈이 모자라서 성과가 나빴다고 말할 수 있나.

    교체 때 남는 현금이 이 선보다 많으면 '1주 단위에 걸려서 못 샀다'
    쪽을 의심해야 한다. 적으면 그 핑계를 댈 수 없다.
    """
    return idle_pct > limit


def report_fast(dates, panel, order, starts):
    """짧은 주기 + 슬리피지 민감도 + 반띵.

    주기를 좁히면 순위가 더 싱싱해지는 대신 거래가 는다. 어느 쪽이
    이기는지는 **거래 한 번에 얼마를 잃느냐** 에 달렸고, 백테스트는
    수수료만 넣고 슬리피지를 안 넣는다. 그래서 슬리피지를 변수로 둔다.
    """
    base_fee = E.FEE_ONE_WAY
    half = BASE_DI + (len(dates) - BASE_DI) // 2

    print("\n=== 짧은 주기 (시작일 5개 중앙값) ===")
    print(f"{'주기':<12}{'연수익%':>9}{'최소':>8}{'최대':>8}{'낙폭%':>9}"
          f"{'연 주문일':>10}")
    years = (len(dates) - BASE_DI) / DAYS_PER_YEAR
    box = {}
    for p in FAST_PERIODS:
        curves = [run(dates, panel, order, p, s, 10)[0] for s in starts]
        rs = [annualized(c) for c in curves]
        ds = [mdd(c) for c in curves]
        box[p] = (st.median(rs), min(rs), max(rs), st.median(ds))
        print(f"{label_of(p):<12}{st.median(rs):>9.1f}{min(rs):>8.1f}"
              f"{max(rs):>8.1f}{st.median(ds):>9.1f}"
              f"{(len(dates)-BASE_DI)/p/years:>10.1f}", flush=True)

    print("\n=== 슬리피지를 한쪽당 더 물리면 ===")
    print(f"{'주기':<12}" + "".join(f"{s*100:>9.2f}%" for s in SLIPPAGES))
    grid = {}
    for p in FAST_PERIODS:
        row = []
        for slip in SLIPPAGES:
            E.FEE_ONE_WAY = base_fee + slip
            row.append(st.median(annualized(run(dates, panel, order, p, s, 10)[0])
                                 for s in starts))
        grid[p] = row
        print(f"{label_of(p):<12}" + "".join(f"{v:>10.1f}" for v in row),
              flush=True)
    E.FEE_ONE_WAY = base_fee
    for i, slip in enumerate(SLIPPAGES):
        best = max(grid, key=lambda p: grid[p][i])
        print(f"  슬리피지 {slip*100:.2f}% -> 1등 {label_of(best)}"
              f" ({grid[best][i]:.1f}%)")

    print("\n=== 반띵 (전반부 / 후반부), 기준은 120일 ===")
    b1 = annualized(run(dates, panel, order, 120, BASE_DI, 10, upto=half)[0])
    b2 = annualized(run(dates, panel, order, 120, half, 10)[0])
    print(f"{'120일 (기준)':<14}{b1:>9.1f}{b2:>9.1f}")
    for p in [x for x in FAST_PERIODS if x != 120]:
        x = annualized(run(dates, panel, order, p, BASE_DI, 10, upto=half)[0])
        y = annualized(run(dates, panel, order, p, half, 10)[0])
        v = ("양쪽 이김" if x > b1 and y > b2 else
             "뒤집힘" if (x > b1) != (y > b2) else "양쪽 짐")
        print(f"{label_of(p):<14}{x:>9.1f}{y:>9.1f}   {v}", flush=True)
    return box, grid


def main():
    ap = argparse.ArgumentParser(description="손잡이 훑기")
    ap.add_argument("--fast", action="store_true",
                    help="주기를 하루까지 좁혀본다 (+ 슬리피지 민감도)")
    ap.add_argument("--vol", action="store_true",
                    help="vol_days 도 훑는다 (순위를 여섯 번 다시 계산하므로 오래 걸린다)")
    ap.add_argument("--flip", action="store_true",
                    help="저변동 대신 고변동을 골랐을 때와 견준다 (기준점)")
    args = ap.parse_args()

    dates, panel = S.load_panel()
    starts = [BASE_DI + k * START_GAP for k in range(N_STARTS)]
    print("일별 순위 계산 중...")
    order = ranks(dates, panel, BASE_DI)

    if args.fast:
        report_fast(dates, panel, order, starts)
        print("\n짧은 주기는 백테스트에서 이기지만 반띵에서 뒤집히고"
              " (전반부에서 진다)\n슬리피지 0.08% 에서 우위가 사라진다."
              " 낙폭도 나빠진다. 채택 안 한다.")
        return 0

    if args.flip:
        # 같은 후보 풀에서 순서만 뒤집으면 고변동 10종목이 된다. 풀도
        # 주기도 부분교체도 같으므로 차이가 전부 '선정' 에서 온다.
        flipped = {di: lst[::-1] for di, lst in order.items()}
        print("\n=== 기준점: 고르는 방향만 뒤집으면 (시작일 5개 중앙값) ===")
        print(f"{'':16}{'연수익%':>9}{'최대낙폭%':>11}")
        for label, od in (("저변동 10", order), ("고변동 10", flipped)):
            rs, ds = [], []
            for s in starts:
                c, _i = run(dates, panel, od, 120, s, 10)
                rs.append(annualized(c))
                ds.append(mdd(c))
            print(f"{label:<16}{st.median(rs):>9.1f}{st.median(ds):>11.1f}")
        print("\n아래 손잡이들이 만드는 차이는 전부 이것보다 훨씬 작다.")
        return 0

    print("\n=== 종목 수 x 교체 주기 (시작일 5개 중앙값) ===")
    print(f"{'종목수':>6}{'주기':>6}{'연수익':>9}{'최소':>8}{'최대':>8}"
          f"{'낙폭':>9}{'수익/낙폭':>10}")
    for pick in PICKS:
        for period in PERIODS:
            rs, ds = [], []
            for s in starts:
                c, _i = run(dates, panel, order, period, s, pick)
                rs.append(annualized(c))
                ds.append(mdd(c))
            m, d = st.median(rs), st.median(ds)
            print(f"{pick:>6}{period:>6}{m:>9.1f}{min(rs):>8.1f}{max(rs):>8.1f}"
                  f"{d:>9.1f}{m / abs(d):>10.2f}")

    print("\n=== 종목 수를 늘리면 돈이 노는가 ===")
    print(f"{'종목수':>6}{'노는 현금%':>12}{'판정':>28}")
    for pick in (5, 10, 15, 20, 30):
        ids = [run(dates, panel, order, 120, s, pick)[1] for s in starts]
        avg = st.mean(ids)
        verdict = ("돈이 모자란 쪽을 의심" if capital_bound(avg)
                   else "돈 문제 아님 (분산 자체의 결과)")
        print(f"{pick:>6}{avg:>12.1f}{verdict:>28}")

    if not args.vol:
        print("\n--vol 을 붙이면 vol_days 도 훑는다.")
        return 0

    print("\n=== vol_days (low_vol 을 며칠로 재는가, 지금 60) ===")
    print(f"{'vol_days':>9}{'연수익':>9}{'최소':>8}{'최대':>8}{'낙폭':>9}")
    meds, spreads = [], []
    for vd in VOL_DAYS:
        od = ranks(dates, panel, BASE_DI, vol_days=vd)
        rs, ds = [], []
        for s in starts:
            c, _i = run(dates, panel, od, 120, s, 10)
            rs.append(annualized(c))
            ds.append(mdd(c))
        meds.append(st.median(rs))
        spreads.append(max(rs) - min(rs))
        print(f"{vd:>9}{st.median(rs):>9.1f}{min(rs):>8.1f}{max(rs):>8.1f}"
              f"{st.median(ds):>9.1f}")

    zig = E.is_zigzag(meds)
    print(f"\n지그재그인가: {'예 - 방향이 없다 (잡음)' if zig else '아니오 - 방향이 있다'}")
    print(f"손잡이가 만든 폭 {max(meds) - min(meds):.1f}%p vs "
          f"시작일이 만든 폭(최대) {max(spreads):.1f}%p")
    print(f"고를 수 있나: {'예' if beats_noise(meds, max(spreads)) else '아니오'}")
    print("\n=> vol_days 는 60 그대로 둔다. 60 이 좋아서가 아니라 구별이 안 돼서다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
