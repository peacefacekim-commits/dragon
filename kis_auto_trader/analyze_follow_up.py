"""시장이 오를 때 따라가는 것을 목표로 바꿔서 잰다. (기준만 - 결과 미기입)

(2026-09-22 신설) 사용자: "그치 시장이 오를때 따라가는 걸 목표로 해보자"

===========================================================================
0 - 이건 지금까지와 목표가 다르다
===========================================================================
지금까지는 전부 "저변동을 이기는 것" 을 찾았고 전부 졌다 (dip -29.6%,
골든/데드 10칸, 익절/손절 12/12, 재무 4칸...). 이번은 **이기려는 게
아니다.** 시장이 줄 때 받겠다는 것이다.

이 목표가 왜 새로운가: 저변동은 **설계상 상승을 포기하는 전략**이다.
monitor.py 의 기준값이 상승 포착률 0.37 / 하락 포착률 0.23 이고, 상승
포착률이 0.50 을 넘으면 오히려 **경보**를 울린다 ("저변동 성질이
흐려졌다"). 즉 지금 전략은 사용자의 새 목표와 반대 방향으로 설계돼
있다. 그래서 다시 재야 한다.

그리고 analyze_winning_period.py 가 이 목표의 출발점을 이미 만들어줬다.
07-30~08-12 에 시장 중앙 종목이 +16.59% 인데 실거래는 +1.49% 였고,
비중을 맞춘 따라간 비율이 0.29 였다. 그걸 올리자는 것이다.

===========================================================================
1 - 안 되는 길을 먼저 지운다 (이미 잰 것)
===========================================================================
"시장을 따라가려면 대형주를 사면 되지 않나" - 안 된다.
analyze_selectors.py 에서 size(시가총액 작은 순)가 저변동과 **-0.722**
였다. 부호를 뒤집으면 **대형주는 저변동과 +0.722** 다. 거의 같은 것을
고른다. 대형주로 가는 것은 이미 있는 자리로 가는 것이다.

"오르는 것을 사면 되지 않나" - 안 된다. 추세 -30.9%, 모멘텀 탈락,
골든크로스 필터 -7.9%p, dip -29.6%. 전부 졌다.

그래서 남는 길은 둘뿐이다.
  (1) **분산을 늘린다.** 종목을 늘리면 포트폴리오가 시장에 수렴한다.
      이건 선정을 바꾸는 게 아니라 선정의 '농도' 를 낮추는 것이다.
  (2) **그냥 시장을 산다.** 유니버스 전체 동일가중. 상승 포착률은
      정의상 1.0 이다.

===========================================================================
2 - 무엇을 잰다. 여섯 칸
===========================================================================
전부 같은 조건이다. 200만원, 같은 수수료, 1주 단위 제약, 120일 부분교체,
같은 시작일 5개. 다른 것은 **종목 수 하나뿐**이다.

  저변동 10종목    지금 검증된 것. 기준선이다.
  저변동 30종목
  저변동 50종목
  저변동 100종목   유니버스 200종목의 절반
  유니버스 200종목  '그냥 시장' (factor "all", 동일가중)

여기서 제일 중요한 칸은 **유니버스 200종목**이다. 이게 저변동 10종목을
이기면 5.7년 저변동 우위는 착각이었고 그냥 시장을 사면 된다는 뜻이다.
지면 저변동이 상승을 포기한 값을 받고 있었다는 뜻이다. 어느 쪽이든
이번 결과의 중심이다.

시총가중은 안 넣는다. buy_greedy 가 동일가중 배분기라서 시총가중은
배분기를 새로 써야 하고, 그건 이번 질문에 필요하지 않다 (대형주가
저변동과 +0.722 이므로 시총가중도 그쪽으로 기운다).

재는 것
  연수익% / 최대낙폭% / 최악 1년%
  **상승 포착률 / 하락 포착률** (이번의 목표 지표)
  수수료/자본%
  **실제 채워진 종목 수** - 200만원에 100종목이면 1종목당 2만원이고,
    최저가 5,000원 제약 때문에 다 안 채워질 수 있다. 안 채워지면
    '100종목을 산 것' 이 아니므로 반드시 같이 적는다.

===========================================================================
3 - 포착률을 어떻게 재나
===========================================================================
시장 = 유니버스 전체 동일가중 **지수** 다. 수수료도 1주 제약도 없는
맨 지수다 (포트폴리오가 아니다). 그래야 기준이 전략 쪽 사정에 안
흔들린다.

  상승 포착률 = (시장이 오른 날들의 전략 평균 일수익) / (같은 날들의
                시장 평균 일수익)
  하락 포착률 = (시장이 내린 날들의 전략 평균 일수익) / (같은 날들의
                시장 평균 일수익)

둘 다 1.0 이면 시장과 똑같이 움직인 것이다. 좋은 모양은 **상승은 1 에
가깝고 하락은 0 에 가까운 것**이다.

monitor.py 와 뜻이 반대다. 거기서는 상승 포착률이 높으면 경보인데
(저변동 성질이 흐려진 신호), 여기서는 목표다. 같은 숫자를 다른 뜻으로
쓰는 것이므로 monitor.py 의 문턱을 가져다 쓰지 않는다.

===========================================================================
4 - 채택 조건 넷. 목표가 바뀌었으니 조건도 바뀐다
===========================================================================
이번엔 "저변동을 이겨라" 가 아니다. "따라가되 대가가 너무 크지 않아야
한다" 다. 그래서 허용치를 **결과를 보기 전에** 숫자로 박는다.

  1) (목표)   상승 포착률이 저변동 10종목보다 높다
  2) (안 지기) 연수익 중앙값이 저변동 10종목보다 **3.0%p 이상 낮지 않다**
  3) (안 깨지기) 최대낙폭이 저변동 10종목보다 **5.0%p 이상 나쁘지 않다**
  4) (지속)   연도별로 양수인 해가 과반이고 최고 해를 빼도 양수다

허용치를 왜 3.0%p / 5.0%p 로 잡았나 (결과를 보고 고르지 않으려고 근거를
먼저 적는다)
  3.0%p  이 저장소가 잰 '손잡이' 효과 중 제일 큰 것이 주기 20일->120일
         의 1.8%p 였다 (analyze_styles). 3.0%p 는 그보다 크게 잡은
         값이므로, 이걸 넘어 깎이면 손잡이 수준이 아니라 전략이 바뀐
         것이다.
  5.0%p  저변동의 최대낙폭이 -15.9% 다. 5.0%p 는 그 3분의 1 가까이다.
         이것보다 더 깨지면 '큰 손해를 피한다' 는 전제가 무너진다.

하나라도 걸리면 채택하지 않는다. 결과를 보고 허용치를 늘리지 않는다.

미리 정해두는 처리
  미래 정보     저변동 점수는 di-1 종가까지, 매매는 di 시가.
  값이 없는 날   그 종목은 그 회차에서 제외. 앞 값을 끌어오지 않는다.
  1주 제약      못 채운 종목 수를 세서 같이 출력한다.

===========================================================================
결과 - 목표는 달성 가능하다. 그런데 대가가 1:1 이다. 채택 0개
===========================================================================
먼저 이 표의 어느 숫자보다 중요한 것

  **유니버스 동일가중 지수 (수수료 없는 맨 지수) = 연 -7.0%**

5.7년 동안 시장 자체가 손실이었다. 저변동 10종목이 +22.3% 니까 차이가
**29.3%p** 다. 저변동 우위는 착각이 아니었다. 그리고 이게 이번 목표의
전제를 흔든다 - **따라갈 시장이 내려가는 시장이었다.**

표 (120일 부분교체, 시작일 5개 중앙값)

  칸                연수익%   낙폭%  최악1년%  상승포착  하락포착  상승/하락  수수료%  채운종목
  저변동 10종목        22.3  -15.9   -12.7    0.39    0.25     1.55     1.5      9
  저변동 30종목        16.5  -21.6   -14.5    0.51    0.40     1.27     1.1     22
  저변동 50종목        26.9  -23.6   -12.9    0.62    0.47     1.32     1.2     32
  저변동 100종목       18.2  -31.8   -15.9    0.82    0.68     1.21     1.0     51
  유니버스 200종목       2.1  -53.5   -28.6    1.14    1.09     1.05     0.6     78

===========================================================================
1 - 목표는 달성 가능하다 (상승 포착률이 단조롭게 오른다)
===========================================================================
  0.39 -> 0.51 -> 0.62 -> 0.82 -> 1.14

종목을 늘리면 시장을 따라간다. 이건 확실하다. 사용자가 세운 목표는
'할 수 있나' 의 문제가 아니었다.

===========================================================================
2 - 그런데 대가가 거의 1:1 이다 (이게 답이다)
===========================================================================
하락 포착률이 같이 오른다.

  0.25 -> 0.40 -> 0.47 -> 0.68 -> 1.09

둘을 나눈 **비대칭 비율**로 보면 무슨 일이 벌어지는지 한눈에 보인다.

  10종목 1.55 -> 30종목 1.27 -> 50종목 1.32 -> 100종목 1.21 -> 200종목 1.05

**비대칭이 제일 큰 곳이 10종목이고, 시장으로 갈수록 1.05 로 수렴한다.**
1.05 는 '시장을 그냥 산 것' 이다.

읽는 법: 상승 포착률만 보면 분산이 목표를 이뤄준다. 그런데 그 상승은
**시장에 가까워져서** 얻은 것이고, 시장에 가까워지면 하락도 같이 온다.
'오를 때 받고 내릴 때 덜 맞는' 성질은 저변동을 **소수로 집중**한 데서
나오고 있었다. 분산은 그 성질을 사는 게 아니라 파는 것이다.

===========================================================================
3 - 연수익 차이는 잡음이다 (50종목에 속으면 안 된다)
===========================================================================
표만 보면 저변동 50종목이 연 26.9% 로 10종목(22.3%)을 +4.6%p 이긴다.
조건 1 과 2 도 통과한다. 그런데 시작일 5개를 펼쳐보면

  칸                시작일별 연수익%                       최대-최소
  저변동 10종목      16.9  17.7  22.3  24.8  26.7        9.8
  저변동 30종목      13.4  14.6  16.5  19.0  21.7        8.2
  저변동 50종목      12.5  19.7  26.9  27.3  33.6       21.1
  저변동 100종목     13.4  18.0  18.2  19.6  21.5        8.1
  유니버스 200종목   -7.0  -6.0   2.1   6.3   8.9       15.8

50종목의 우위 +4.6%p 보다 **자기 흩어짐 21.1%p 가 네 배 넘게 크다.**
그리고 50종목의 구간(12.5~33.6)이 10종목의 구간(16.9~26.7)을 완전히
덮는다. 시작일을 언제로 잡느냐가 칸 사이 차이보다 크게 작용한다.

연수익 자체도 지그재그다 (22.3 -> 16.5 -> 26.9 -> 18.2 -> 2.1). 진짜
효과라면 단조로울 텐데 아니다. **반면 낙폭과 포착률은 다섯 칸 모두
단조롭다.** 그래서 이 표에서 믿을 것은 낙폭/포착률이고, 연수익 차이는
아니다. 50종목의 +4.6%p 는 잡음으로 본다.

이게 채택 조건 2(연수익 허용치)를 통과한 칸이 왜 채택이 아닌지의
이유이기도 하다. 조건 3(낙폭)에서 -7.6%p 로 걸렸고, 조건 2 를 통과한
것도 실력이 아니었다.

===========================================================================
4 - '유니버스 200종목' 칸은 시장이 아니다 (이 칸은 조심해서 읽어야 한다)
===========================================================================
채운 종목이 **78개**다. 200만원을 200종목에 나누면 1종목당 1만원이고,
최저가 5,000원 제약 때문에 다 못 채운다. 게다가 buy_greedy 는 남은 돈을
**싼 종목부터** 채우므로 못 채운 칸은 싼 종목 쪽으로 기운다.

그래서 이 칸의 상승 포착률 1.14 가 1 을 넘고 낙폭이 -53.5% 까지 간다.
지수 자체보다 더 흔들리는 것을 산 것이다. **깨끗한 시장 숫자는 맨 지수
쪽(-7.0%)이고, 이 칸의 연 2.1% 는 '싼 종목으로 기운 78종목' 이다.**

다른 칸도 목표를 다 못 채운다 (30->22, 50->32, 100->51). 같은 방향의
편향이 조금씩 섞여 있다는 뜻이다. 표를 '종목 수' 로 읽지 말고 '분산의
정도' 로 읽어야 한다.

===========================================================================
5 - 채택 0개
===========================================================================
  칸               연수익차   낙폭차   상승포착차  조건1/2/3
  저변동 30종목       -5.8    -5.7    +0.12    O/X/X
  저변동 50종목       +4.6    -7.6    +0.23    O/O/X
  저변동 100종목      -4.1   -15.8    +0.43    O/X/X
  유니버스 200종목   -20.2   -37.6    +0.75    O/X/X

네 칸 모두 조건 1(목표)은 통과했고 전부 조건 3(낙폭 -5.0%p)에서
걸렸다. 조건 4 는 돌리지 않았다. 허용치를 늘리지 않는다.

===========================================================================
6 - 그래서 목표를 어떻게 고쳐야 하나
===========================================================================
"시장이 오를 때 따라간다" 를 **종목 수로** 이루려 하면 값이 하락이다.
그리고 그 값을 치를 이유가 이 5.7년에는 없었다 - 시장이 연 -7.0% 였다.

사용자가 실제로 원하는 것은 '상승 포착률' 이 아니라 **비대칭 비율**로
보인다. "큰 이득을 포기하더라도 큰 손해를 피하고 작은 이득을 쌓는다" 는
전제와 같은 말이다. 그 지표에서는 **지금 쓰는 저변동 10종목이 이미
다섯 칸 중 제일 좋다 (1.55)**.

그러면 남는 길은 '분산을 늘린다' 가 아니고, **상승과 하락을 갈라주는
무언가**다. 그건 이 저장소에서 계속 실패한 자리다 (지수 데드크로스는
낙폭조차 못 줄였고, 손절/익절은 12/12 졌다). 아직 안 해본 것은 장중
데이터뿐이고, 그게 analyze_min10.py 의 판정이다.

덧붙임: analyze_winning_period.py 에서 실거래의 상승 따라간 비율이
0.29 였다. 저변동 10종목의 0.39 보다도 낮다. **사용자의 새 목표 지표로
재도 실거래가 지금 전략보다 나빴다.** 목표를 바꾸어도 결론이 같은
쪽으로 간다.

===========================================================================
한계
===========================================================================
1) 다섯 칸을 봤다. 종목 수 하나만 움직이는 단조로운 손잡이라서 '여러
   가지를 훑어 하나 고른 것' 과는 다르지만, 다섯 칸이라는 사실은 남는다.
2) 1주 단위 제약 때문에 어느 칸도 목표 종목수를 다 못 채웠다 (4절).
   자본이 크면 표가 달라질 수 있다. 200만원 기준의 결과다.
3) 시총가중을 안 넣었다. buy_greedy 가 동일가중 배분기라서 배분기를
   새로 써야 한다. 대형주가 저변동과 +0.722 이므로 시총가중도 저변동
   쪽으로 기울 것으로 보지만, 그건 추정이고 잰 것이 아니다.
4) 2021~2026 한국 시장이다. 시장이 연 -7.0% 인 구간이었다. 오르는
   5.7년이었다면 '따라가기' 의 값이 달랐을 것이다 - 이 결론은 시기에
   묶여 있다.
5) 포착률은 일수익률 평균 기준이다. 중앙값으로 재면 값이 달라진다.

실행:
  python analyze_follow_up.py          # 표
  python analyze_follow_up.py --full    # 조건 4(연도별)까지
"""
import argparse
import pathlib
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
PERIOD = 120
DAYS_PER_YEAR = 246
N_STARTS, START_GAP = 5, 37

# (이름, 종목수, 선정). 종목 수 하나만 움직인다.
BOXES = (("저변동 10종목", 10, "low_vol"),
         ("저변동 30종목", 30, "low_vol"),
         ("저변동 50종목", 50, "low_vol"),
         ("저변동 100종목", 100, "low_vol"),
         ("유니버스 200종목", 200, "all"))
BASE_BOX = "저변동 10종목"

# 채택 허용치. 결과를 보기 전에 박는다 (근거는 위 4절).
MAX_RETURN_GIVEUP = 3.0      # %p
MAX_MDD_GIVEUP = 5.0         # %p


def ranks_for(dates, panel, factor, base=BASE_DI):
    """날짜별 선정 순위. factor "all" 은 유니버스 전체(동일가중)다."""
    order = {}
    di, n = base, len(dates)
    while di < n:
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        if factor == "all":
            order[di] = list(cand)          # 순서가 뜻이 없다. 전부 산다.
        else:
            sc = [(x, c) for c in cand
                  if (x := S.factor_score(panel, c, di, factor)) is not None]
            if len(sc) >= 10:
                sc.sort(reverse=True)
                order[di] = [c for _s, c in sc]
        di += 1
    return order


def run(dates, panel, order, start, pick, period=PERIOD, upto=None,
        capital=CAPITAL):
    """부분교체. (곡선, 수수료, 회차별 채워진 종목수)."""
    n = upto if upto is not None else len(dates)
    cash, hold = float(capital), {}
    curve, fees, filled = [], 0.0, []
    di = start
    while di < n:
        if (di - start) % period == 0 and di in order:
            new = order[di][:pick]
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
            hold = {**keep, **got}
            filled.append(len(hold))
        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, fees, filled


def market_index(dates, panel, order, base=BASE_DI):
    """유니버스 동일가중 지수. 수수료도 1주 제약도 없는 맨 지수다.

    포트폴리오로 만들지 않는 이유: 기준이 전략 쪽 사정(수수료, 1주 단위,
    현금 잔돔)에 흔들리면 포착률이 그 사정을 재는 숫자가 되어버린다.
    """
    lvl = {base: 100.0}
    for di in range(base + 1, len(dates)):
        codes = order.get(di - 1) or order.get(di) or []
        rets = []
        for c in codes:
            s = panel.get(c)
            if s is None:
                continue
            a, b = s.pos.get(di - 1), s.pos.get(di)
            if a is None or b is None:
                continue
            p0 = s.close[a]
            if p0:
                rets.append(s.close[b] / p0 - 1)
        lvl[di] = lvl[di - 1] * (1 + (st.mean(rets) if rets else 0.0))
    return lvl


def daily_rets(curve):
    """곡선 -> 일수익률 목록 (첫날은 없다)."""
    out = []
    for i in range(1, len(curve)):
        p = curve[i - 1]
        out.append(curve[i] / p - 1 if p else 0.0)
    return out


def capture(strat_curve, mkt_lvl, start):
    """(상승 포착률, 하락 포착률, 오른날 수, 내린날 수).

    시장이 오른 날과 내린 날을 나눠서, 각 묶음의 평균 일수익률을 비교한다.
    상승은 1 에 가까울수록 좋고 하락은 0 에 가까울수록 좋다.
    """
    up_s, up_m, dn_s, dn_m = [], [], [], []
    for i in range(1, len(strat_curve)):
        di = start + i
        a, b = mkt_lvl.get(di - 1), mkt_lvl.get(di)
        if a is None or b is None or not a:
            continue
        mr = b / a - 1
        p = strat_curve[i - 1]
        if not p:
            continue
        sr = strat_curve[i] / p - 1
        if mr > 0:
            up_s.append(sr)
            up_m.append(mr)
        elif mr < 0:
            dn_s.append(sr)
            dn_m.append(mr)
    uc = (st.mean(up_s) / st.mean(up_m)
          if up_m and st.mean(up_m) else None)
    dc = (st.mean(dn_s) / st.mean(dn_m)
          if dn_m and st.mean(dn_m) else None)
    return uc, dc, len(up_m), len(dn_m)


def asymmetry(up_cap, dn_cap):
    """상승 포착 / 하락 포착. 이게 1.0 이면 시장과 같은 모양이다.

    포착률 둘을 따로 보면 '상승이 올랐다' 만 보이고 대가가 안 보인다.
    이 비율이 **비대칭의 크기**다. 1.0 은 시장을 그냥 산 것과 같고,
    클수록 '오를 때 더 받고 내릴 때 덜 맞는' 모양이다.
    """
    if up_cap is None or dn_cap is None or not dn_cap:
        return None
    return up_cap / dn_cap


def worst_year(curve, days=DAYS_PER_YEAR):
    """가장 나빴던 1년 구간 수익률%. 구간이 짧으면 전체로 본다."""
    if len(curve) <= days:
        return (curve[-1] / curve[0] - 1) * 100 if curve and curve[0] else 0.0
    worst = None
    for i in range(len(curve) - days):
        a = curve[i]
        if not a:
            continue
        r = (curve[i + days] / a - 1) * 100
        worst = r if worst is None else min(worst, r)
    return worst if worst is not None else 0.0


def _starts():
    return [BASE_DI + k * START_GAP for k in range(N_STARTS)]


def accepted(up_cap, base_up_cap, ret, base_ret, mdd, base_mdd,
             years_pos, years_total, rest_mean):
    """채택 조건 넷. 허용치는 결과를 보기 전에 박은 값이다."""
    if up_cap is None or base_up_cap is None:
        return False
    return (up_cap > base_up_cap
            and ret >= base_ret - MAX_RETURN_GIVEUP
            and mdd >= base_mdd - MAX_MDD_GIVEUP
            and years_total > 0
            and years_pos * 2 > years_total
            and rest_mean > 0)


def by_year(dates, panel, order, pick, base_order, base=BASE_DI,
            min_days=100):
    """해마다 기준선과의 차이(%p). 조건 4 의 재료."""
    years = {}
    for i, d in enumerate(dates):
        years.setdefault(d[:4], []).append(i)
    out = []
    for y in sorted(years):
        idx = years[y]
        lo, hi = max(idx[0], base), idx[-1] + 1
        if hi - lo < min_days:
            continue
        ref = F.annualized(run(dates, panel, base_order, lo, 10, upto=hi)[0])
        sig = F.annualized(run(dates, panel, order, lo, pick, upto=hi)[0])
        out.append((y, ref, sig, sig - ref))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="시장이 오를 때 따라가는 것을 목표로 잰다")
    ap.add_argument("--full", action="store_true", help="조건 4(연도별)까지")
    args = ap.parse_args(argv)

    dates, panel = S.load_panel()
    starts = _starts()
    print("선정 순위 계산 중...", flush=True)
    orders = {}
    for fac in {f for _n, _p, f in BOXES}:
        orders[fac] = ranks_for(dates, panel, fac)
    print("시장 지수 계산 중...", flush=True)
    mkt = market_index(dates, panel, orders["low_vol"])
    mkt_ann = ((mkt[max(mkt)] / 100.0)
               ** (DAYS_PER_YEAR / (len(mkt) - 1)) - 1) * 100
    print(f"  유니버스 동일가중 지수 (수수료 없음): 연 {mkt_ann:+.1f}%")

    print(f"\n=== 종목 수만 늘리면 시장을 얼마나 따라가나 "
          f"(120일, 시작일 {N_STARTS}개 중앙값) ===")
    print(f"  {'칸':<16}{'연수익%':>8}{'낙폭%':>8}{'최악1년%':>9}"
          f"{'상승포착':>9}{'하락포착':>9}{'상승/하락':>10}"
          f"{'수수료%':>8}{'채운종목':>9}")
    box = {}
    for name, pick, fac in BOXES:
        order = orders[fac]
        rs, ds, ws, ucs, dcs, fs, fl = [], [], [], [], [], [], []
        for s in starts:
            c, fee, filled = run(dates, panel, order, s, pick)
            rs.append(F.annualized(c))
            ds.append(F.mdd(c))
            ws.append(worst_year(c))
            uc, dc, _nu, _nd = capture(c, mkt, s)
            if uc is not None:
                ucs.append(uc)
            if dc is not None:
                dcs.append(dc)
            fs.append(fee / CAPITAL * 100)
            fl += filled
        box[name] = {
            "ret": st.median(rs), "mdd": st.median(ds),
            "worst": st.median(ws),
            "up": st.median(ucs) if ucs else None,
            "dn": st.median(dcs) if dcs else None,
            "fee": st.median(fs), "filled": st.median(fl) if fl else 0,
            "pick": pick, "fac": fac, "rs": rs, "ds": ds,
        }
        b = box[name]
        up_txt = f"{b['up']:.2f}" if b["up"] is not None else "-"
        dn_txt = f"{b['dn']:.2f}" if b["dn"] is not None else "-"
        b["ratio"] = asymmetry(b["up"], b["dn"])
        ra_txt = f"{b['ratio']:.2f}" if b["ratio"] is not None else "-"
        print(f"  {name:<16}{b['ret']:>8.1f}{b['mdd']:>8.1f}"
              f"{b['worst']:>9.1f}{up_txt:>9}{dn_txt:>9}{ra_txt:>10}"
              f"{b['fee']:>8.1f}{b['filled']:>9.0f}", flush=True)

    print(f"\n=== 시작일 5개가 얼마나 흩어지나 (중앙값만 보면 안 된다) ===")
    print(f"  {'칸':<16}{'시작일별 연수익%':<44}{'최대-최소':>10}")
    for name, _pick, _fac in BOXES:
        rs = sorted(box[name]["rs"])
        print(f"  {name:<16}"
              + " ".join(f"{r:>7.1f}" for r in rs)
              + f"{rs[-1] - rs[0]:>11.1f}")
    print("  흩어짐이 칸 사이 차이만큼 크면, 그 차이는 잡음일 수 있다.")

    print(f"\n=== 1주 제약으로 실제로 몇 종목이 채워졌나 ===")
    for name, pick, _fac in BOXES:
        got = box[name]["filled"]
        print(f"  {name:<16}목표 {pick:>3}종목 -> 실제 {got:>3.0f}종목"
              + ("  <- 목표의 절반도 안 찬다. '그 종목수를 산 것' 이 아니다."
                 if got < pick * 0.5 else ""))
    print(f"  200만원을 {BOXES[-1][1]}종목에 나누면 1종목당 "
          f"{CAPITAL // BOXES[-1][1]:,}원이다. buy_greedy 는 남은 돈을 "
          "싼 종목부터 채우므로\n  못 채운 칸은 **싼 종목 쪽으로 기운다**. "
          "그래서 아래 포착률도 그만큼 올라가 있다.")

    ref = box[BASE_BOX]
    print(f"\n=== 기준선({BASE_BOX}) 대비 ===")
    print(f"  {'칸':<16}{'연수익':>9}{'낙폭':>9}{'상승포착':>10}  조건1/2/3")
    for name, _pick, _fac in BOXES:
        if name == BASE_BOX:
            continue
        b = box[name]
        c1 = b["up"] is not None and ref["up"] is not None and b["up"] > ref["up"]
        c2 = b["ret"] >= ref["ret"] - MAX_RETURN_GIVEUP
        c3 = b["mdd"] >= ref["mdd"] - MAX_MDD_GIVEUP
        print(f"  {name:<16}{b['ret'] - ref['ret']:>+9.1f}"
              f"{b['mdd'] - ref['mdd']:>+9.1f}"
              f"{(b['up'] - ref['up']) if b['up'] and ref['up'] else 0:>+10.2f}"
              f"  {'O' if c1 else 'X'}/{'O' if c2 else 'X'}/{'O' if c3 else 'X'}")
    print(f"\n  허용치: 연수익 -{MAX_RETURN_GIVEUP}%p 까지, "
          f"낙폭 -{MAX_MDD_GIVEUP}%p 까지 (결과 보기 전에 박은 값)")

    live = [n for n, _p, _f in BOXES if n != BASE_BOX
            and box[n]["up"] is not None and ref["up"] is not None
            and box[n]["up"] > ref["up"]
            and box[n]["ret"] >= ref["ret"] - MAX_RETURN_GIVEUP
            and box[n]["mdd"] >= ref["mdd"] - MAX_MDD_GIVEUP]
    if not live:
        print("\n조건 1~3 을 동시에 넘은 칸이 없다. 조건 4 는 돌리지 않는다."
              "\n허용치를 늘리지 않는다.")
        return 0
    print(f"\n조건 4 로 보낼 칸: {live}")
    if not args.full:
        print("--full 을 붙이면 연도별까지 잽니다.")
        return 0

    print(f"\n=== 조건 4: 연도별 (기준선 대비 %p) ===")
    for name in live:
        b = box[name]
        rows = by_year(dates, panel, orders[b["fac"]], b["pick"],
                       orders["low_vol"])
        diffs = [d for _y, _r, _s, d in rows]
        pos, rest = F.one_year_story(diffs)
        print(f"  {name:<16}"
              + " ".join(f"{y}:{d:+.1f}" for y, _r, _s, d in rows))
        ok = accepted(b["up"], ref["up"], b["ret"], ref["ret"],
                      b["mdd"], ref["mdd"], pos, len(diffs), rest)
        print(f"  {'':<16}양수 {pos}/{len(diffs)}, 최고 해 빼면 "
              f"{rest:+.1f}%p  -> {'채택' if ok else '탈락'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
