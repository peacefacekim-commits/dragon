"""저변동으로 고른 종목을 골든/데드크로스로 사고팔아 본다. (기준만 - 결과 미기입)

(2026-09-22 신설) 사용자: "저변동 종목에 데드크로스 골드크로스로 종목을
구입하고 파는 전략은?"

===========================================================================
0 - 이건 어제 잰 것과 다른 질문이다
===========================================================================
analyze_old_rules.py 에서 골든크로스를 쟀지만 그건 **선정**에 쓴 것이고
(그래서 reversal 과 -0.750 으로 재포장 판정), 여기서는 **선정은 저변동으로
두고 사고파는 시점**에만 쓴다. 같은 지표라도 쓰는 자리가 다르면 다른
질문이다. 어제 결과를 여기로 옮기면 안 된다.

===========================================================================
1 - 기준선이 무엇인가 (이게 이 파일의 핵심)
===========================================================================
무작위가 기준선이 아니다. **검증된 저변동 전략 자체**가 기준선이다.

  저변동 10종목 / 120일 부분교체 = 연 +22.3% (analyze_old_rules.py 에서
  같은 코드로 다시 확인한 값)

타이밍 규칙은 이걸 넘어야 의미가 있다. 이건 무작위를 넘는 것보다 훨씬
높은 문턱이고, 그래야 맞다 - 이미 있는 것보다 나은지를 묻는 것이니까.

미리 적어두는 예상: analyze_original.py 에서 익절/손절이 12/12 로 졌고,
analyze_stops.py 에서 11가지 손절 문턱이 전부 졌다. 데드크로스도 '파는
규칙' 이므로 같은 쪽에 붙을 것 같다. **그런데 다른 점이 하나 있다** -
익절/손절은 가격 문턱이고 데드크로스는 추세 전환이다. 문턱을 못 넘는
것과 방향이 바뀌는 것은 다를 수 있다. 그래서 잰다.

===========================================================================
2 - 무엇을 잰다. 다섯 가지
===========================================================================
선정(저변동)과 종목수(10)는 고정. 주기는 20일/120일 둘만 본다.

  없음               교체일에만 사고팔기. 기준선이다.
  데드크로스 매도      들고 있는 종목의 5일선이 20일선 아래로 가면 판다.
                     판 돈은 다음 교체일까지 현금이다.
  데드크로스 매도+재투자  팔고 바로 순위 다음 종목(골든 상태인 것)을 산다.
                     analyze_takeprofit.py 에서 '노는 돈' 이 결과를
                     크게 바꿨으므로 둘 다 잰다.
  골든크로스만 매수     교체일에 저변동 순위대로 훑되 골든 상태인 것만
                     담는다. 아닌 것은 건너뛰고 순위를 더 내려간다.
  둘 다               골든만 매수 + 데드크로스 매도 + 재투자

덧붙여 **지수** 골든/데드크로스도 둘 잰다 (표 2). 전제.md 의 '사람은
계속 못 보지만 AI 는 본다' 에 해당하는 것이라 같이 본다. 다만 이 지수는
KOSPI 가 아니다 - 5.7년치 지수 종가가 저장소에 없어서 패널로 만든
동일가중 대용이다. 그렇게 읽어야 한다.

  지수 데드크로스면 전부 현금   골든으로 돌아오면 다시 담는다
  지수 데드크로스면 새로 안 산다  들고 있는 건 그대로 둔다

늘리지 않는다. 이동평균은 5/20 하나만 쓴다 (README 에 적혀 있던 값).
문턱을 훑으면 12칸이 60칸이 되고, 그러면 하나는 우연히 이긴다.

===========================================================================
3 - 채택 조건 넷
===========================================================================
  1) 시작일 5개 중 4개 이상에서 **'없음' 을 이긴다** (무작위가 아니다)
  2) 반띵 양방향 모두에서 '없음' 을 이긴다
  3) **같은 횟수로 무작위 날에 파는 것**을 넘는다 (500회, p < 0.05)
     이 대조군이 이 파일에서 제일 중요하다. 파는 횟수만 같게 해놓고
     파는 날을 무작위로 고른다. 데드크로스가 정보를 담고 있다면 무작위
     날짜보다 나아야 하고, 아니라면 '그냥 그만큼 팔았을 때' 와 같다.
     대조군은 **파는 신호만** 바꾼다. 들어가는 쪽(골든만 매수)과 재투자는
     그대로 둔다. 둘 다 바꾸면 무엇이 차이를 만들었는지 알 수 없다.
  4) 연도별 지속성 - 양수인 해가 과반이고 최고 해를 빼도 양수다

하나라도 걸리면 넣지 않는다. 결과를 보고 조건을 고치지 않는다.

미리 정해두는 처리
  미래 정보      이동평균은 di-1 종가까지로 계산하고 매매는 di 시가다.
  같은 날 사고팔기  교체일에 산 종목은 그날 데드크로스 검사에서 뺀다.
                 안 그러면 같은 시가에 사고팔아 수수료만 버린다.
  값이 없는 날    그 종목은 그 검사에서 제외. 앞 값을 끌어오지 않는다.
  슬리피지       백테스트에 스프레드가 없다. 늘어난 왕복 수로 '한쪽당
                 몇 %면 차이가 사라지나' 를 같이 적는다.

===========================================================================
결과 - 10칸 전부 탈락. 조건 1 에서 끝났다
===========================================================================
표 1: 종목별 5/20 교차 (저변동 10종목 고정, 시작일 5개 중앙값)

  주기  규칙                     연수익%   낙폭%  규칙매도  수수료%  기준선대비
  20일  없음                      20.3   -16.2      0     5.1  (기준선)
  20일  데드크로스 매도              0.1   -18.3    402    10.3   -20.1%p
  20일  데드크로스 매도+재투자        -8.2   -49.4    867    20.7   -28.5%p
  20일  골든크로스만 매수             5.8   -34.0      0     9.0   -14.4%p
  20일  둘 다                     -5.0   -40.5    699    16.5   -25.3%p

 120일  없음                      22.3   -15.9      0     1.5  (기준선)
 120일  데드크로스 매도              0.7   -11.0     80     2.0   -21.6%p
 120일  데드크로스 매도+재투자        -3.1   -43.8    774    15.3   -25.4%p
 120일  골든크로스만 매수            14.3   -19.7      0     1.5    -7.9%p
 120일  둘 다                     -3.1   -42.0    740    14.5   -25.4%p

표 2: 지수(동일가중 대용) 5/20 교차, 120일 주기
  지수가 골든인 날 765일 / 데드인 날 617일 (45% 가 데드)

  지수 데드면 전부 현금             10.3   -15.9                 -12.0%p
  지수 데드면 새로 안 산다           16.9   -18.4                  -5.3%p

조건 1 (시작일 5개 중 '없음' 을 이긴 횟수)
  전부 0/5. 하나만 예외로 120일 골든크로스만 매수가 2/5 인데 이것도 탈락.
  그래서 조건 2/3/4 는 돌리지 않았다. 새로 만든 무작위 매도 대조군도
  쓸 일이 없었다 - 넘어온 것이 없으니까. 조건을 고치지 않는다.

기준선 대조: 20일 20.3% / 120일 22.3% 는 analyze_styles.py 의 20.2% /
22.0% 와 맞는다. 다른 코드로 같은 값이 나온 것이니 배관은 맞다.

===========================================================================
1 - 파는 쪽: 낙폭이 준 것은 위험관리가 아니라 투자를 덜 한 것
===========================================================================
120일 데드크로스 매도가 이 파일에서 **낙폭이 나아진 유일한 칸**이다
(-15.9% -> -11.0%). 그런데 수익은 22.3% -> 0.7% 다. 낙폭 4.9%p 를 사는
값이 수익 21.6%p 다.

analyze_original.py 에서 손절이 똑같은 모양이었다 (-16.2 -> -13.4 인데
20.2 -> 8.0). 현금으로 도망가 있으면 덜 깨지는 것은 당연하고, 그건
위험관리가 아니라 투자를 덜 한 것이다. 규칙이 가격 문턱(손절)에서
추세 전환(데드크로스)으로 바뀌어도 결과가 같다. 미리 적어둔 "다를 수도
있다" 는 기대는 틀렸다.

===========================================================================
2 - 뒤집힌 것: 여기서는 '노는 돈' 을 없애면 더 나빠졌다
===========================================================================
analyze_takeprofit.py 에서는 판 돈을 바로 재투자하니 18.4% -> 22.8% 로
좋아졌다. 그래서 '노는 돈' 이 손해의 큰 몫이라고 적었다. 여기서는
**정반대**다.

  120일  데드크로스 매도        +0.7   (판 돈을 현금으로 둠, 매도 80건)
  120일  데드크로스 매도+재투자  -3.1   (바로 재투자, 매도 774건)

낙폭은 -11.0% 에서 -43.8% 로 네 배가 된다. 수수료가 자본의 2.0% 에서
15.3% 로 는다.

왜 뒤집혔나: 재투자 대상이 다르다. 익절 때는 같은 저변동 순위 안에서
다음 종목을 샀다. 여기서는 '데드크로스가 아닌 종목' 을 사야 하므로
골든 상태인 종목으로 가고, 그건 어제 잰 대로 모멘텀 쪽이다. 게다가
새로 산 종목도 곧 데드크로스가 되어 또 팔린다 - 매도가 80건에서 774건,
거의 10배다.

교훈: **'노는 돈을 없애라' 는 보편 규칙이 아니다.** 재투자 대상이
나쁘면 노는 것이 낫다. 앞 파일의 결론을 그대로 옮겨 쓰면 틀린다.

===========================================================================
3 - 사는 쪽: 규칙 매도가 0 건인데도 진다 (그래서 원인이 선정이다)
===========================================================================
'골든크로스만 매수' 는 파는 규칙이 아예 없다. 그런데 120일에서 -7.9%p,
20일에서 -14.4%p 다. 낙폭도 나빠진다 (-15.9 -> -19.7, -16.2 -> -34.0).
파는 쪽 탓이 아니니 **고르는 쪽이 망가진 것**이다. --why 로 쟀다.

  교체일    필터없음   골든만   순위깊이  후보중골든%
   중앙값       98      92       28        61

읽는 법: 필터가 없으면 저변동 상위 10종목을 담고, 그건 유니버스에서
변동성 백분위 98 (가장 안 흔들리는 쪽) 이다. 골든 필터를 켜면 10종목을
채우려고 저변동 순위를 **28번째까지** 내려가야 하고, 그 결과 백분위가
92 로 내려간다. **-6 만큼 덜 안정적인 쪽으로 밀린다.**

최악의 회차는 후보 중 골든이 27% 뿐이어서 57번째까지 내려갔다. 그날은
'저변동 상위 10종목' 이 아니라 '저변동 상위 57종목 중 오르는 것 10개' 를
산 것이다. 그건 다른 전략이다.

이건 어제 analyze_old_rules.py 에서 본 것과 같은 힘이다. 골든 상태는
20일 모멘텀과 +0.750 이므로, 골든으로 거르면 포트폴리오가 모멘텀 쪽으로
끌려간다. 선정에 쓰든 필터로 쓰든 같은 방향으로 끌고 간다.

수수료도 는다: 20일에서 5.1% -> 9.0% 다. 규칙 매도가 0 건인데 늘어난
이유는 골든 집합 자체가 교체일마다 많이 바뀌어서 교체 회전이 커지기
때문이다.

===========================================================================
4 - 지수 교차: 낙폭조차 못 줄였다
===========================================================================
전제.md 의 '사람은 계속 못 보지만 AI 는 본다' 에 해당하는 칸이라 기대가
있었다. 결과는 둘 다 진다 (-12.0%p, -5.3%p).

제일 말해주는 숫자는 낙폭이다. '전부 현금' 의 낙폭이 **-15.9% 로
기준선과 같다.** 45% 의 날을 현금으로 앉아 있었는데도 최악의 하락을
피하지 못했다. 즉 이 저변동 포트폴리오가 깨지는 시기와 지수가 데드
크로스인 시기가 겹치지 않는다. 수익만 깎고 안전은 못 산 것이다.

한계: 이 지수는 KOSPI 가 아니다. 패널 전체 동일가중 대용이라 소형주
쪽으로 기운다. KOSPI 종가로 다시 하면 숫자가 달라질 수 있다. 다만
'45% 를 현금으로 있었는데 낙폭이 같다' 는 방향이 뒤집힐 만한 종류의
차이는 아니다.

===========================================================================
읽는 법 / 한계
===========================================================================
1) 다중검정: 12칸을 봤다 (표 1 열 칸, 표 2 두 칸). 채택은 0 개다.
   12칸을 보면 우연히 이기는 칸이 나오기 쉬운데, 그런 칸이 하나도
   없었다는 것이 결과를 더 분명하게 만든다.
2) 이동평균은 5/20 하나만 썼다. 10/30, 20/60 을 훑지 않았다 - 그러면
   12칸이 60칸이 된다. 여기서 문턱을 훑을 이유는 5/20 이 조금이라도
   가능성을 보였을 때인데, -7.9%p 부터 -28.5%p 다.
3) 일봉이다. 장중 교차는 여기서 못 잰다.
4) 2021~2026 한국 시장, 저변동 선정, 10종목 기준이다.
5) 슬리피지는 계산하지 않았다. 수수료 전에 이미 졌으므로 볼 필요가
   없다. (기준선을 넘은 칸이 있었다면 늘어난 왕복 수로 뒤집히는
   슬리피지를 같이 적게 해뒀다 - slip_flip 함수.)

===========================================================================
남는 것
===========================================================================
검증된 것은 여전히 '저변동으로 골라서 안 건드린다' 하나다. 이번에
붙여본 다섯 가지 중 낙폭이라도 사준 것은 하나(120일 데드크로스 매도)
뿐이고 그 값이 수익 21.6%p 였다.

실행:
  python analyze_ma_timing.py          # 표 1 (종목별 교차)
  python analyze_ma_timing.py --index  # 표 2 (지수 교차)까지
  python analyze_ma_timing.py --why    # 골든 필터가 무엇을 포기하게 하나
  python analyze_ma_timing.py --full   # 이긴 것이 있으면 조건 2~4 까지
"""
import argparse
import pathlib
import random
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import analyze_fundamentals as F  # noqa: E402
import strategy as S  # noqa: E402

CAPITAL = E.CAPITAL
FEE_ONE_WAY = E.FEE_ONE_WAY
BASE_DI = 250
PICK = 10
PERIODS = (20, 120)
N_STARTS, START_GAP = 5, 37
MA_SHORT, MA_LONG = 5, 20
N_PERM = 500
SEED = 20260922
MIN_START_WINS = 4
PERM_ALPHA = 0.05

# (이름, 골든만 매수, 데드크로스 매도, 팔고 재투자)
RULES = (("없음", False, False, False),
         ("데드크로스 매도", False, True, False),
         ("데드크로스 매도+재투자", False, True, True),
         ("골든크로스만 매수", True, False, False),
         ("둘 다", True, True, True))
INDEX_RULES = (("지수 데드면 전부 현금", "cash"),
               ("지수 데드면 새로 안 산다", "nobuy"))


# ---------------------------------------------------------------- 교차 상태
def ma_states(panel, short=MA_SHORT, long=MA_LONG):
    """종목별로 '5일선이 20일선 위인가' 를 미리 계산한다.

    매일 모든 보유 종목에 대해 물어보므로 그때그때 평균을 내면 너무
    느리다. 누적합으로 한 번에 만들어두고 O(1) 로 조회한다.
    값이 모자라는 앞부분은 None 이다 (모른다는 뜻. False 가 아니다).
    """
    out = {}
    for code, s in panel.items():
        cs = s.close
        n = len(cs)
        pre = [0.0] * (n + 1)
        for i, v in enumerate(cs):
            pre[i + 1] = pre[i] + (v or 0.0)
        arr = [None] * n
        for j in range(long - 1, n):
            ms = (pre[j + 1] - pre[j + 1 - short]) / short
            ml = (pre[j + 1] - pre[j + 1 - long]) / long
            arr[j] = (ms > ml) if ml else None
        out[code] = arr
    return out


def above(states, panel, code, di):
    """di 시점에 쓸 수 있는 정보로 본 상태. di-1 종가까지만 쓴다.

    None 은 '모른다' 다 (기록이 모자라거나 그 종목이 없다). 모르는 것을
    False 로 취급하면 안 된다 - 그러면 신규 상장 종목을 전부 팔게 된다.
    """
    s = panel.get(code)
    if s is None:
        return None
    j = s.pos.get(di - 1)
    if j is None:
        return None
    arr = states.get(code)
    if not arr or j >= len(arr):
        return None
    return arr[j]


# ---------------------------------------------------------------- 지수 대용
def market_index(dates, panel):
    """유니버스 동일가중 지수 대용. **KOSPI 가 아니다.**

    5.7년치 지수 종가가 저장소에 없다 (market_history.csv 는 최근 것뿐).
    그래서 패널 종목 전체의 하루 수익률을 동일가중 평균해서 쌓았다.
    지수보다 소형주 쪽으로 기운 대용물이므로 그렇게 읽어야 한다.
    """
    level = [100.0]
    for di in range(1, len(dates)):
        rets = []
        for s in panel.values():
            a, b = s.pos.get(di - 1), s.pos.get(di)
            if a is None or b is None:
                continue
            p0, p1 = s.close[a], s.close[b]
            if p0:
                rets.append(p1 / p0 - 1)
        level.append(level[-1] * (1 + (st.mean(rets) if rets else 0.0)))
    return level


def index_states(level, short=MA_SHORT, long=MA_LONG):
    """지수의 골든 상태. arr[di] 는 'di-1 까지 본 상태' 다."""
    n = len(level)
    pre = [0.0] * (n + 1)
    for i, v in enumerate(level):
        pre[i + 1] = pre[i] + v
    arr = [None] * n
    for di in range(long, n):
        j = di - 1                        # di-1 종가까지
        ms = (pre[j + 1] - pre[j + 1 - short]) / short
        ml = (pre[j + 1] - pre[j + 1 - long]) / long
        arr[di] = ms > ml if ml else None
    return arr


# ---------------------------------------------------------------- 돌리기
def _sell_all(panel, cash, hold, di):
    fees = 0.0
    for c, q in list(hold.items()):
        v = E.price(panel, c, di)
        if v:
            cash += q * v * (1 - FEE_ONE_WAY)
            fees += q * v * FEE_ONE_WAY
    return cash, {}, fees


def _entry_list(order, states, panel, di, pick, golden_only):
    """그 날 담을 종목. 골든만 매수면 순위를 더 내려가서 채운다."""
    ranked = order.get(di)
    if not ranked:
        return None
    if not golden_only:
        return ranked[:pick]
    out = []
    for c in ranked:
        if above(states, panel, c, di) is True:
            out.append(c)
            if len(out) == pick:
                break
    return out or None


def run(dates, panel, order, states, start, period, rule, pick=PICK,
        upto=None, index_arr=None, index_mode=None, rng=None,
        rand_sell_p=0.0):
    """부분교체 + 교차 규칙. (곡선, 규칙매도수, 수수료)

    rule = (골든만매수, 데드매도, 재투자)
    index_mode = None / "cash" / "nobuy"
    rand_sell_p > 0 이면 데드크로스 대신 **무작위로** 그 확률로 판다
    (조건 3 의 대조군. 파는 횟수를 맞추려고 확률을 조절한다).
    """
    golden_only, dead_exit, reinvest = rule
    n = upto if upto is not None else len(dates)
    cash, hold, opened = float(CAPITAL), {}, {}
    curve, di, nsell, fees = [], start, 0, 0.0
    frozen = False                        # 지수 데드크로스 상태인가

    while di < n:
        back_in = False
        if index_arr is not None and index_mode:
            st_ok = index_arr[di] if di < len(index_arr) else None
            was = frozen
            frozen = (st_ok is False)
            if frozen and index_mode == "cash" and hold:
                cash, hold, f = _sell_all(panel, cash, hold, di)
                fees += f
                nsell += 1
            # 골든으로 돌아오면 교체일을 기다리지 않고 바로 다시 담는다.
            # 안 그러면 120일 주기에서는 몇 달을 현금으로 앉아 있게 되고,
            # 그건 '지수 교차를 본 것' 이 아니라 '투자를 안 한 것' 이다.
            if was and not frozen and index_mode == "cash" and not hold:
                back_in = True

        rebal = (di - start) % period == 0 or back_in
        if rebal and not frozen:
            new = _entry_list(order, states, panel, di, pick, golden_only)
            if new:
                keep = {c: q for c, q in hold.items() if c in new}
                for c in [c for c in hold if c not in new]:
                    v = E.price(panel, c, di)
                    if v:
                        cash += hold[c] * v * (1 - FEE_ONE_WAY)
                        fees += hold[c] * v * FEE_ONE_WAY
                add = [c for c in new if c not in hold]
                got, cash, f = (E.buy_greedy(panel, cash, add, di) if add
                                else ({}, cash, 0.0))
                fees += f
                for c in got:
                    opened[c] = di
                hold = {**keep, **got}

        if (dead_exit or rand_sell_p) and not frozen:
            for c in list(hold):
                if opened.get(c) == di:   # 같은 시가에 사고팔지 않는다
                    continue
                if rand_sell_p:
                    go = rng.random() < rand_sell_p
                else:
                    go = above(states, panel, c, di) is False
                if not go:
                    continue
                v = E.price(panel, c, di)
                if not v:
                    continue
                cash += hold[c] * v * (1 - FEE_ONE_WAY)
                fees += hold[c] * v * FEE_ONE_WAY
                del hold[c]
                nsell += 1
            if reinvest and len(hold) < pick:
                ranked = order.get(di) or []
                add = [c for c in ranked if c not in hold
                       and above(states, panel, c, di) is True][:pick - len(hold)]
                if add:
                    got, cash, f = E.buy_greedy(panel, cash, add, di)
                    fees += f
                    for c in got:
                        opened[c] = di
                    hold.update(got)

        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, nsell, fees


# ---------------------------------------------------------------- 조건 3
def control_rule(rule):
    """대조군의 규칙. **파는 신호만** 무작위로 갈아치운다.

    들어가는 쪽(골든만 매수)과 재투자는 그대로 둔다. 그래야 "데드크로스가
    파는 날을 고를 줄 아나" 만 물어보는 게 된다. 둘 다 바꾸면 무엇이
    차이를 만들었는지 알 수 없다.
    """
    golden_only, _dead, reinvest = rule
    return (golden_only, False, reinvest)


def match_sell_prob(dates, panel, order, states, start, period, rule, target,
                    pick=PICK, lo=0.0, hi=0.2, rounds=18):
    """무작위 매도 확률을 조절해서 매도 횟수를 target 에 맞춘다.

    횟수를 안 맞추면 대조군이 '덜 팔았다' 가 되어 비교가 안 된다.
    """
    ctrl = control_rule(rule)
    for _ in range(rounds):
        mid = (lo + hi) / 2
        rng = random.Random(SEED)
        _c, ns, _f = run(dates, panel, order, states, start, period,
                         ctrl, pick, rng=rng, rand_sell_p=mid)
        if ns < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def random_exit_p(dates, panel, order, states, starts, period, rule, observed,
                  target, pick=PICK, n_perm=N_PERM, seed=SEED):
    """같은 횟수로 무작위 날에 팔았을 때 관측값 이상이 나온 비율 -> p."""
    ctrl = control_rule(rule)
    probs = {s: match_sell_prob(dates, panel, order, states, s, period,
                                rule, target, pick) for s in starts}
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_perm):
        med = st.median(
            F.annualized(run(dates, panel, order, states, s, period,
                             ctrl, pick, rng=rng, rand_sell_p=probs[s])[0])
            for s in starts)
        if med >= observed:
            hits += 1
    return (hits + 1) / (n_perm + 1), probs


def golden_cost(dates, panel, order, states, base=BASE_DI, period=120,
                pick=PICK):
    """골든 필터가 '무엇을 포기하게 하나' 를 잰다.

    '골든크로스만 매수' 는 규칙 매도가 0 건인데도 진다. 그러면 원인은
    파는 쪽이 아니라 **고르는 쪽**이다. 필터를 켜면 저변동 순위를 더
    내려가야 10종목이 차므로, 덜 안정적인 종목을 담게 된다.

    교체일마다 (필터 없는 10종목의 변동성 백분위, 필터 켠 10종목의
    백분위, 순위를 몇 번째까지 내려갔나, 후보 중 골든 비율) 을 모은다.
    백분위는 0 = 가장 흔들림, 100 = 가장 안 흔들림.
    """
    rows = []
    for di in range(base, len(dates), period):
        ranked = order.get(di)
        if not ranked:
            continue
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        vol = {c: x for c in cand
               if (x := S.factor_score(panel, c, di, "low_vol")) is not None}
        if len(vol) < 20:
            continue
        asc = sorted(vol, key=vol.get)          # 변동 큰 것부터
        rank = {c: i / (len(asc) - 1) * 100 for i, c in enumerate(asc)}
        plain = ranked[:pick]
        gold, depth = [], 0
        for i, c in enumerate(ranked):
            if above(states, panel, c, di) is True:
                gold.append(c)
                if len(gold) == pick:
                    depth = i + 1
                    break
        if len(gold) < pick:
            continue
        share = sum(1 for c in ranked
                    if above(states, panel, c, di) is True) / len(ranked) * 100
        rows.append((st.mean([rank[c] for c in plain if c in rank]),
                     st.mean([rank[c] for c in gold if c in rank]),
                     depth, share))
    return rows


def slip_flip(gap_pct_per_year, extra_sells_per_year):
    """늘어난 매도 때문에 차이가 사라지는 한쪽당 슬리피지(%).

    매도 한 건이 늘면 매수도 한 건 늘어 왕복 하나가 는다. 왕복당
    스프레드를 2 x slip 으로 보면 slip = 차이 / (2 x 늘어난 왕복) 이다.
    어림값이다 (복리와 비중을 무시한다).
    """
    if extra_sells_per_year <= 0:
        return float("inf")
    return gap_pct_per_year / (2 * extra_sells_per_year)


def accepted(start_wins, first_beats, second_beats, perm_p,
             years_pos, years_total, rest_mean):
    """채택 조건 넷. 전제.md 의 규약과 같다."""
    return (start_wins >= MIN_START_WINS
            and first_beats and second_beats
            and perm_p < PERM_ALPHA
            and years_total > 0
            and years_pos * 2 > years_total
            and rest_mean > 0)


def _starts():
    return [BASE_DI + k * START_GAP for k in range(N_STARTS)]


def by_year(dates, panel, order, states, period, rule, base=BASE_DI,
            min_days=100):
    """해마다 '없음' 과의 차이. 조건 4 의 재료."""
    years = {}
    for i, d in enumerate(dates):
        years.setdefault(d[:4], []).append(i)
    out = []
    for y in sorted(years):
        idx = years[y]
        lo, hi = max(idx[0], base), idx[-1] + 1
        if hi - lo < min_days:
            continue
        ref = F.annualized(run(dates, panel, order, states, lo, period,
                               (False, False, False), upto=hi)[0])
        sig = F.annualized(run(dates, panel, order, states, lo, period,
                               rule, upto=hi)[0])
        out.append((y, ref, sig, sig - ref))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="저변동 선정 위에 골든/데드크로스 타이밍을 올려본다")
    ap.add_argument("--index", action="store_true", help="지수 교차까지")
    ap.add_argument("--full", action="store_true",
                    help="이긴 것이 있으면 조건 2~4 까지")
    ap.add_argument("--why", action="store_true",
                    help="골든 필터가 무엇을 포기하게 하나")
    args = ap.parse_args(argv)

    dates, panel = S.load_panel()
    print("저변동 순위 계산 중...", flush=True)
    order, _r = E.daily_ranks(dates, panel, BASE_DI)
    print("이동평균 상태 계산 중...", flush=True)
    states = ma_states(panel)
    starts = _starts()
    years_span = (len(dates) - BASE_DI) / 246

    if args.why:
        rows = golden_cost(dates, panel, order, states)
        print("\n=== 골든 필터를 켜면 무엇이 달라지나 (120일 교체일마다) ===")
        print("  변동성 백분위 0 = 가장 흔들림, 100 = 가장 안 흔들림")
        print(f"  {'필터없음':>10}{'골든만':>10}{'순위깊이':>10}{'후보중골든%':>12}")
        for a, b, d, sh in rows:
            print(f"  {a:>10.0f}{b:>10.0f}{d:>10}{sh:>12.0f}")
        if rows:
            print(f"  {'-' * 44}")
            print(f"  {st.median(r[0] for r in rows):>10.0f}"
                  f"{st.median(r[1] for r in rows):>10.0f}"
                  f"{st.median(r[2] for r in rows):>10.0f}"
                  f"{st.median(r[3] for r in rows):>12.0f}  <- 중앙값")
            drop = st.median(r[1] for r in rows) - st.median(r[0] for r in rows)
            print(f"\n  백분위가 {drop:+.0f} 만큼 움직인다"
                  f" ({'덜 안정적인 쪽' if drop < 0 else '더 안정적인 쪽'}으로)")
        return 0

    print(f"\n=== 표 1: 종목별 5/20 교차 (저변동 10종목 고정, "
          f"시작일 {N_STARTS}개 중앙값) ===")
    print(f"{'주기':>5}  {'규칙':<22}{'연수익%':>9}{'낙폭%':>9}"
          f"{'규칙매도':>9}{'수수료%':>8}  기준선대비")
    box = {}
    for period in PERIODS:
        for tag, *rule in RULES:
            rs, ds, ns, fs = [], [], [], []
            for s in starts:
                c, nse, fee = run(dates, panel, order, states, s, period,
                                  tuple(rule))
                rs.append(F.annualized(c))
                ds.append(F.mdd(c))
                ns.append(nse)
                fs.append(fee / CAPITAL * 100)
            box[(period, tag)] = (st.median(rs), st.median(ds),
                                  st.median(ns), st.median(fs), rs)
            base = box[(period, "없음")][0]
            gap = st.median(rs) - base
            print(f"{period:>4}일  {tag:<22}{st.median(rs):>9.1f}"
                  f"{st.median(ds):>9.1f}{st.median(ns):>9.0f}"
                  f"{st.median(fs):>8.1f}"
                  f"{'  (기준선)' if tag == '없음' else f'  {gap:+.1f}%p'}",
                  flush=True)
        print()

    if args.index:
        print("지수 대용 계산 중...", flush=True)
        level = market_index(dates, panel)
        iarr = index_states(level)
        on = sum(1 for x in iarr if x is True)
        off = sum(1 for x in iarr if x is False)
        print(f"\n=== 표 2: 지수(동일가중 대용) 5/20 교차, 120일 주기 ===")
        print(f"  지수가 골든인 날 {on}일 / 데드인 날 {off}일"
              f" ({off / (on + off) * 100:.0f}% 가 데드)")
        print(f"  {'규칙':<24}{'연수익%':>9}{'낙폭%':>9}  기준선대비")
        base = box[(120, "없음")][0]
        for tag, mode in INDEX_RULES:
            rs, ds = [], []
            for s in starts:
                c, _n, _f = run(dates, panel, order, states, s, 120,
                                (False, False, False), index_arr=iarr,
                                index_mode=mode)
                rs.append(F.annualized(c))
                ds.append(F.mdd(c))
            box[(120, tag)] = (st.median(rs), st.median(ds), 0, 0.0, rs)
            print(f"  {tag:<24}{st.median(rs):>9.1f}{st.median(ds):>9.1f}"
                  f"  {st.median(rs) - base:+.1f}%p", flush=True)

    # 조건 1
    print(f"\n=== 조건 1: 시작일 5개 중 몇 개에서 '없음' 을 이기나 ===")
    passed = []
    for (period, tag), v in sorted(box.items()):
        if tag == "없음":
            continue
        ref = box[(period, "없음")][4]
        wins = sum(1 for a, b in zip(v[4], ref) if a > b)
        mark = "통과" if wins >= MIN_START_WINS else "탈락"
        if wins >= MIN_START_WINS:
            passed.append((period, tag))
        print(f"  {period:>4}일  {tag:<24}{wins}/{N_STARTS}  {mark}")

    if not passed:
        print(f"\n조건 1 을 넘은 것이 없다. 여기서 끝이고 조건을 고치지 않는다.")
        print("슬리피지는 따로 볼 필요가 없다 - 수수료 전에 이미 졌다.")
        return 0
    if not args.full:
        print(f"\n조건 2~4 로 보낼 것: {passed}")
        print("--full 을 붙이면 끝까지 잽니다.")
        return 0

    half = BASE_DI + (len(dates) - BASE_DI) // 2
    print(f"\n=== 조건 2: 반띵 (규칙 / 없음) ===")
    halves = {}
    for period, tag in passed:
        rule = next(tuple(r) for t, *r in RULES if t == tag)
        row = []
        for s, upto in ((BASE_DI, half), (half, None)):
            a = F.annualized(run(dates, panel, order, states, s, period,
                                 rule, upto=upto)[0])
            b = F.annualized(run(dates, panel, order, states, s, period,
                                 (False, False, False), upto=upto)[0])
            row.append((a, b))
        halves[(period, tag)] = row
        (s1, r1), (s2, r2) = row
        v = ("양쪽 이김" if s1 > r1 and s2 > r2 else
             "뒤집힘" if (s1 > r1) != (s2 > r2) else "양쪽 짐")
        print(f"  {period:>4}일  {tag:<24}전반 {s1:>6.1f}/{r1:<6.1f}"
              f"후반 {s2:>6.1f}/{r2:<6.1f}  {v}", flush=True)

    print(f"\n=== 조건 3: 같은 횟수로 무작위 날에 팔기 {N_PERM}회 ===")
    ps = {}
    for period, tag in passed:
        obs, target = box[(period, tag)][0], box[(period, tag)][2]
        if not target:
            ps[(period, tag)] = 1.0
            print(f"  {period:>4}일  {tag:<24}규칙 매도가 0 건이라 "
                  f"이 대조군이 성립하지 않는다 -> 탈락 처리")
            continue
        rule = next(tuple(r) for t, *r in RULES if t == tag)
        p, probs = random_exit_p(dates, panel, order, states, starts,
                                 period, rule, obs, target)
        ps[(period, tag)] = p
        print(f"  {period:>4}일  {tag:<24}관측 {obs:>6.1f}  "
              f"매도 {target:.0f}건 맞춤(확률 중앙 "
              f"{st.median(probs.values()):.4f})  p = {p:.4f}", flush=True)

    print(f"\n=== 조건 4: 연도별 ('없음' 대비 %p) ===")
    years = {}
    for period, tag in passed:
        rule = next(tuple(r) for t, *r in RULES if t == tag)
        rows = by_year(dates, panel, order, states, period, rule)
        years[(period, tag)] = rows
        diffs = [d for _y, _r, _s, d in rows]
        pos, rest = F.one_year_story(diffs)
        print(f"  {period:>4}일  {tag:<24}"
              + " ".join(f"{y}:{d:+.1f}" for y, _r, _s, d in rows))
        print(f"  {'':>4}   {'':<24}양수 {pos}/{len(diffs)}, "
              f"최고 해 빼면 {rest:+.1f}%p", flush=True)

    print(f"\n{'주기':>5}  {'규칙':<24}{'조건1':>7}{'조건2':>7}{'조건3':>7}"
          f"{'조건4':>7}  판정   슬리피지")
    for period, tag in passed:
        v = box[(period, tag)]
        ref = box[(period, "없음")]
        wins = sum(1 for a, b in zip(v[4], ref[4]) if a > b)
        (s1, r1), (s2, r2) = halves[(period, tag)]
        diffs = [d for _y, _r, _s, d in years[(period, tag)]]
        pos, rest = F.one_year_story(diffs)
        ok = accepted(wins, s1 > r1, s2 > r2, ps[(period, tag)],
                      pos, len(diffs), rest)
        flip = slip_flip(v[0] - ref[0], (v[2] - ref[2]) / years_span)
        print(f"{period:>4}일  {tag:<24}{f'{wins}/{N_STARTS}':>7}"
              f"{'통과' if s1 > r1 and s2 > r2 else '탈락':>7}"
              f"{'통과' if ps[(period, tag)] < PERM_ALPHA else '탈락':>7}"
              f"{'통과' if pos * 2 > len(diffs) and rest > 0 else '탈락':>7}"
              f"  {'채택' if ok else '탈락'}   "
              + (f"{flip:.3f}% 에서 뒤집힘" if flip != float("inf")
                 else "매도 증가 없음"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
