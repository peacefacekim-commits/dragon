"""한 종목을 정해서 싸면 사고 비싸면 판다. (기준만 - 결과 미기입)

(2026-09-22 신설) 사용자: "안정적인 종목 하나를 정해서 계속 사고 파는 건
어떨까. 우리가 평가하는 가격 이하면 사고 이상이면 팔고 이런식으로 원금을
불려나가는 거야"

===========================================================================
0 - 이 파일은 결과를 보기 전에 쓴다 (사전 등록)
===========================================================================
아래 조건들은 숫자를 보기 전에 정했다. git log 가 순서를 증명한다.

===========================================================================
1 - 이게 지금까지 잰 것과 다른 점
===========================================================================
이 저장소가 5.7년간 잰 것은 전부 **횡단면**이었다 - "오늘 200종목 중
무엇을 고르나". 이건 **시계열**이다 - "한 종목이 시간에 따라 오르내리는
것을 타고 앉는다". 종목 정체가 고정이다.

가까운 것이 하나 있긴 하다. analyze_old_rules.py 의 dip 이 "많이 떨어진
것을 산다" 였고 연 -29.6% 로 졌다. 하지만 그건 **교체일마다 다른 종목**을
골랐고, 떨어진 종목을 고르는 바람에 사실상 고변동 고르기가 됐다
(변동성 백분위 중앙 16). 이 파일은 종목을 안 바꾼다. 다른 가설이다.

===========================================================================
2 - 먼저 수수료. 이 아이디어는 수수료로 죽지 않는다
===========================================================================
  밴드 폭   왕복 총수익   수수료(0.21%) 비중
  +-1%        2%           10.5%
  +-2%        4%            5.3%
  +-3%        6%            3.5%
  +-5%       10%            2.1%

10분 단타는 막대 폭 중앙값 0.646% 에 수수료가 33% 였다 (explore_min10).
+-3% 밴드면 3.5% 다. **자릿수가 다르다.** 단타를 죽인 이유가 여기엔
없다. 그러니 이건 진지하게 잴 가치가 있다.

===========================================================================
3 - 손익 모양이 나쁘다. 그런데 나쁜 모양이 곧 지는 건 아니다
===========================================================================
  오르면   밴드 위에서 팔고 끝난다      -> 이득이 잘린다
  내리면   밴드 아래에서 사고 계속 든다 -> 손해는 안 잘린다

**작은 이득을 자주, 큰 손해를 가끔.** 사실상 변동성 매도다.
저장소 전제("큰 이득을 포기하더라도 큰 손해를 피하고 작은 이득을
쌓아간다")에서 앞쪽만 맞고 뒤쪽이 반대다.

사용자: "큰이득을 포기하고 큰 손해를 보는 건 걍 바보짓이잖아?"

**맞는 말이다.** 위를 자르고 아래를 안 자르면 그냥 들고 있는 것보다
나쁜 모양이다. 이건 반박할 것이 없다.

단서가 하나 붙을 뿐이다. 나쁜 모양을 갚는 길이 하나 있는데, **작은
이득이 충분히 자주 나는 것**이다 (보험사가 그 모양으로 돈을 버는 이유가
그것이다). 그러니 이 파일이 재야 하는 것은 모양이 아니라 빈도다.
빈도가 모자라면 사용자 말대로 바보짓이 맞고, 그러면 탈락시킨다.

그리고 빈도 질문은 **가격이 되돌아오는가(평균회귀)** 와 같은 질문이다.
무작위 걷기라면 기대값은 0 에서 수수료를 뺀 것이다.

===========================================================================
3.1 - 저장소 안에 정반대 방향의 증거가 둘 있다. 둘 다 오염됐다
===========================================================================
**되돌아온다는 쪽** - analyze_stops.py

  저변동 10종목에 손절을 붙였더니 전부 손해였고, 타이트할수록 나빴다.
    손절 -5%  -5.4%p   손절 -10%  -3.1%p   손절 -20%  -1.2%p
  그 파일이 적은 이유: "저변동 종목이 -5% 빠진 것은 대개 잡음이고,
  팔면 (1) 되돌림을 놓치고 (2) 수수료를 낸다."

  -> **되돌림이 있다는 말이다.** 손절이 진 이유가 밴드가 이길 이유다.
     팔지 말라던 자리에서 밴드는 거꾸로 산다.

**안 되돌아온다는 쪽** - analyze_old_rules.py

  dip(많이 떨어진 것을 산다) 이 연 -29.6%, 낙폭 -85.0%, 시작일 0/5.

  -> 다만 그건 **교체일마다 다른 종목**을 골랐고, 그 바람에 사실상
     고변동 고르기가 됐다 (변동성 백분위 중앙 16, 10회 전부 33 미만).
     종목을 고정한 경우는 잰 적이 없다.

**둘 다 곧바로 이 질문에 답하지 못한다.** 그래서 잰다.

===========================================================================
3.2 - 큰 손해를 그냥 받을 것인가 (사용자 지적에 대한 처리)
===========================================================================
받지 않는 방법은 손절이다. 그런데 analyze_stops 가 이미 저변동에서
손절이 1.2~5.4%p 손해라고 쟀다. 그래서 손절을 **격자에 넣지 않는다** -
넣으면 칸이 24개가 되고 우연히 통과하는 칸이 늘어난다.

대신 **따로 한 줄로 재서 보고한다** (손절 -10%, 7절). 채택 판정에는
안 쓰고, "큰 손해를 그냥 받나" 라는 질문에 숫자로 답하는 용도다.
그리고 **최대 미실현 손실을 반드시 같이 낸다** - 이걸 안 적으면
이 전략을 실제보다 좋게 보이게 만드는 것이다.

===========================================================================
4 - 규칙 (숫자를 보기 전에 고정한다)
===========================================================================
'우리가 평가하는 가격' = **N일 이동평균**. 다른 정의는 안 쓴다.

  산다   종가 < MA(N) x (1 - k/100)   그리고 지금 현금이면
  판다   종가 > MA(N) x (1 + k/100)   그리고 지금 들고 있으면
  체결   신호 난 **다음 날 시가**. (그날 종가를 보고 그날 종가에
         사는 것은 미래를 보는 것이다. 이 저장소가 이미 겪은 실수다.)
  자리   전액. 나누지 않는다 (나누면 손잡이가 하나 더 늘고, 손잡이가
         늘수록 좋아 보이는 칸을 고를 여지가 커진다)

격자는 **이것뿐이다. 나중에 칸을 더하지 않는다.**
  N  in {20, 60, 120}
  k  in {1, 2, 3, 5}
  = 12칸

===========================================================================
5 - 무엇과 비교하나 (이게 제일 중요하다)
===========================================================================
"돈을 벌었나" 가 아니라 **"그냥 들고 있는 것보다 나은가"** 를 묻는다.
밴드가 연 +10% 를 내도 그 종목을 그냥 들고 있으면 +15% 였다면 진 것이다.

그리고 **종목을 고르지 않는다.** 유니버스 200 전부에 같은 규칙을 돌리고
분포를 낸다. 한 종목을 골라서 보여주면 그건 체리피킹이다 - 200개 중
제일 잘된 것은 아무 규칙으로도 잘 나온다.

'안정적인 종목' 이라는 사용자의 조건은 **사후에 고르지 않고** 사전
정보로만 건다: 직전 60일 변동성 하위 10 (= 우리 저변동 선정과 같은 규칙).
그 부분집합에서도 따로 낸다.

===========================================================================
6 - 받아들이는 조건 (결과 보기 전에 정한다)
===========================================================================
가장 좋아 보이는 칸 하나를 골라서 넷을 건다.

  조건 1  달력 연도 5개 중 **4개 이상**에서 밴드가 보유를 이긴다.
  조건 2  반띵(2021~2023 / 2024~2026) **양쪽 다** 같은 방향.
  조건 3  무작위 대조 500회. 같은 횟수만큼 **무작위 날짜에** 사고 팔아도
          같은 우위가 나오면 그건 밴드의 정보가 아니라 그냥 매매 빈도의
          효과다. p < 0.05.
  조건 4  가장 좋았던 해를 빼도 우위가 여전히 양수.

  **절대선 1**: 200종목의 **중앙값**에서 이겨야 한다. 상위 몇 개만
  이기는 것은 체리피킹이다.
  **절대선 2**: 격자가 12칸이므로 우연히 한 칸이 4/5 를 맞출 확률이
  높다. 12칸 중 아무 칸이나 조건1을 통과할 확률은 1-(1-0.1875)^12 = 92%
  다. 그래서 **12칸 중 2칸 이상이 넷을 다 통과해야** 채택한다.
  한 칸만 통과하면 격자 탐색의 부산물로 본다.

===========================================================================
7 - 같이 재서 적을 것 (조건은 아니지만 안 적으면 속이는 것)
===========================================================================
  - **최대 미실현 손실.** 내려갈 때 얼마나 물리나. 3.2 의 질문이다.
  - **손절 -10% 를 붙이면 어떻게 되나.** 격자 밖, 보고용 한 줄.
  - **이득 분포의 모양.** 3절의 "작은 이득 자주 / 큰 손해 가끔" 이
    실제로 그런지. 왕복당 이익 중앙값, 최악 왕복, 이긴 왕복 비율.
    이게 이 파일의 핵심 숫자다 - 빈도가 모양을 갚는지가 여기서 보인다.
  - **현금이 노는 비율.** 밴드 밖에서 기다리는 동안은 돈이 안 일한다.
  - **연간 왕복 횟수.** 이게 0 에 가까우면 그냥 보유와 같은 것이다.
  - **독립 표본 수** (표본.md 규약).

===========================================================================
8 - 이 파일이 답할 수 없는 것
===========================================================================
  - 슬리피지 0 으로 넣는다. 호가를 한 번도 수집한 적이 없다.
    analyze_overnight.py 와 같은 구멍이고, 결과는 상한이다.
  - 일봉이라 하루 안의 오르내림은 못 탄다. 10분봉이 쌓이면 따로 잰다.
  - 한 종목에 전액이므로 **분산이 0 이다.** 그 종목이 상장폐지되면
    끝이다. 유니버스 200 은 상폐가 드물지만 0 은 아니다.

===========================================================================
9 - 결과
===========================================================================
9.1 격자 12칸, 유니버스 171종목 (우위 = 밴드 연수익 - 같은 종목 보유 연수익)

  MA  밴드   중앙 우위  이긴 종목  연 왕복  현금 비율  최악 미실현
  20  +-1%  -10.61%p    26.3%     9.4     49.6%     -39.3%
  20  +-2%   -8.72%p    29.2%     6.9     49.5%     -39.6%
  20  +-3%   -8.08%p    25.7%     5.7     48.8%     -39.7%
  20  +-5%   -7.05%p    27.5%     4.1     49.4%     -40.6%
  60  +-1%   -8.43%p    28.1%     5.3     50.2%     -43.2%
  60  +-2%   -8.28%p    31.0%     4.0     50.4%     -42.6%
  60  +-3%   -8.70%p    32.2%     3.1     50.2%     -42.6%
  60  +-5%   -9.16%p    29.2%     2.3     50.9%     -42.7%
 120  +-1%  -10.97%p    29.2%     3.6     50.8%     -42.2%
 120  +-2%  -11.47%p    28.7%     2.7     51.0%     -41.6%
 120  +-3%  -10.87%p    28.1%     2.1     51.3%     -41.7%
 120  +-5%  -10.91%p    30.4%     1.5     52.5%     -41.0%

**12칸 전부 음수다.** 이긴 종목이 26~32% 뿐이다. 즉 어느 밴드를 잡아도
종목 셋 중 둘은 그냥 들고 있는 것이 나았다.

9.2 조건 판정 - 12칸 전부 탈락, 통과한 칸 0개 (절대선 2 는 2개 필요)

  모든 칸이 **절대선 1(중앙값에서 이긴다)** 에서 먼저 죽었다.
  조건 1 은 12칸 중 1칸만 통과(MA120 +-5%, 4/6), 조건 2 는 0칸.

9.3 **내가 3절에서 예측한 이유가 틀렸다**

나는 "작은 이득 자주 / 큰 손해 가끔" 이라 질 것이라고 썼다.
실제 왕복 3,769건의 모양은 이랬다 (MA20 +-5%).

  이긴 왕복  68.2%   중앙 +9.84%   평균 +10.92%   최고 +69.1%
  진 왕복    31.8%   중앙 -9.12%   평균 -12.26%   최악 -62.4%
  전체       중앙 +5.98%,  평균 +3.54%,  크기 비 1.12배

**모양이 나쁘지 않았다.** 이긴 왕복이 68% 이고, 이긴 크기와 진 크기가
거의 같다 (1.12배). 왕복당 평균이 +3.54% 로 수수료 0.21% 의 17배다.
내 예측은 틀렸다.

9.4 그러면 왜 졌나 - **현금으로 노는 비용이다**

  현금 비율이 어느 칸에서나 **약 50%** 다.

  MA20 +-5% 중앙값 종목에서
    밴드      연 +10.31%
    그냥 보유  연 +17.36%   (= 10.31 + 7.05)

  절반만 들고 있으면서 보유 수익의 59% 를 가져왔다. 거래 자체는
  괜찮았는데 (9.3), **자리를 비운 동안 주식이 올라버렸다.**

  이게 진짜 이유다. 손익 모양이 아니라 **기회비용**이다.

9.5 그런데 밴드는 무작위 매매보다는 낫다 (이 구분이 중요하다)

  조건 3(무작위 대조 500회) 은 12칸 중 **8칸이 통과**했다.
  MA20 계열은 p=0.002~0.026 이다.

  뜻: 같은 횟수만큼 무작위 날짜에 사고팔면 밴드보다 더 나쁘다.
  **밴드에는 진짜 타이밍 능력이 있다.** 다만

    밴드 > 무작위 매매      (능력이 있다)
    밴드 < 그냥 보유        (그 능력이 자리 비운 비용을 못 갚는다)

  능력이 없어서 진 게 아니라, 있는데도 모자라서 졌다.

9.6 '안정적인 종목' 이라는 조건은 **방향이 맞았다**

  직전 60일 변동성 하위 10 종목만 보면 (측정 3)

    MA20 +-3%   전체 -8.08%p  ->  안정 종목 **-2.15%p**
    MA20 +-5%   전체 -7.05%p  ->  안정 종목 **-2.25%p**
    MA60 +-1%   전체 -8.43%p  ->  안정 종목 **-2.86%p**

  손실이 3~4배 줄었다. 최악 미실현도 -40% 대에서 **-23% 대**로 줄었다.
  **여전히 음수지만, 사용자가 '안정적인 종목' 을 고른 것은 옳은
  방향이었다.** 다만 방향이 맞은 것과 이기는 것은 다르다.

9.7 손절 -10% (격자 밖, 보고용. 사용자 지적에 대한 답)

  MA20 +-5%, 171종목 중앙값
    손절 없음   연 +10.31%   최악 미실현 -40.6%
    손절 -10%   연  +8.21%   최악 미실현 **-17.0%**   손절 16회

  **여기서는 보호를 살 수 있다.** 연 2.1%p 를 내면 물리는 깊이가
  -40.6% 에서 -17.0% 로 절반 이하가 된다.

  이건 analyze_stops.py 와 다르다. 거기서는 손절 -5% 가 낙폭을 -17.9%
  에서 -17.5% 로 0.4%p 밖에 못 줄이면서 수익을 5.4%p 잃었다 ("보호를
  사는 게 아니라 그냥 손해다"). 여기서는 값을 내면 보호가 실제로 온다.
  차이는 전략이 다르기 때문이다 - 저기는 분산된 10종목, 여기는 한
  종목 전액이라 물리는 깊이 자체가 다르다.

  **그래도 전체 판정은 안 바뀐다.** 8.21% 는 보유 17.36% 에 더 멀다.

===========================================================================
10 - 한계
===========================================================================
0) **생존편향이 들어 있다.** '전 기간 자료가 있는 종목' 만 쟀다 (171개).
   밴드는 한 종목을 오래 드는 전략이라 기간이 끊기면 잴 수가 없어서
   뺐다. 중간에 상장폐지된 종목이 빠졌으므로 위 숫자는 **좋은 쪽으로
   기울어 있다.** 그런데도 12칸 전부 졌다.

1) 슬리피지 0 이다. 호가를 한 번도 수집한 적이 없다.
   analyze_overnight.py 와 같은 구멍이고, 결과는 상한이다.
   연 왕복이 1.5~9.4회라 10분 단타만큼 치명적이진 않다.

2) **격자가 12칸이라 우연히 통과하는 칸이 나올 수 있었다.** 그래서
   6절에서 "2칸 이상" 을 걸어뒀다. 실제로는 0칸이라 이 걱정은 쓸 일이
   없었다. 반대로 말하면 **이 결과는 다중비교 때문에 좋게 나온 것이
   아니다** - 12번 시도해서 0번 이겼다.

3) 독립 표본은 달력 연도 5~6개다 (표본.md). 종목 171개는 서로 독립이
   아니다 - 같은 시장을 같이 타기 때문에, 171개가 다 졌다고 해서
   독립 증거 171개가 아니다.

4) 평가가격을 이동평균으로만 정의했다. 다른 정의(PER/PBR 기준가,
   52주 범위 위치, 볼린저 밴드의 표준편차 기반)는 안 쟀다.
   **다만 9.4 가 맞다면 정의를 바꿔도 안 풀린다** - 문제가 "언제
   사고 파는가" 가 아니라 "절반을 현금으로 논다" 이기 때문이다.
   정의를 바꿔서 이기려면 현금 비율을 크게 낮춰야 하는데, 그러면
   밴드가 넓지 않다는 뜻이고 그건 그냥 보유에 가까워진다.

5) 일봉이라 하루 안의 오르내림은 못 탔다. 10분봉이 쌓이면 따로 잰다.
   다만 9.4 의 기회비용 구조는 시간 단위를 바꿔도 남는다.

실행:
  python analyze_band.py
  python analyze_band.py --perms 500
"""
import argparse
import pathlib
import random
import statistics as st
import sys

_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

import strategy as S  # noqa: E402

TRADING_DAYS = 246.0
FEE_ROUND_TRIP = 0.21
UNIVERSE_SIZE = 200
VOL_DAYS = 60
STABLE_N = 10                # '안정적인 종목' = 직전 60일 변동성 하위 10
# 격자. 4절에서 고정했다. 칸을 더하지 않는다.
MA_DAYS = (20, 60, 120)
BANDS = (1.0, 2.0, 3.0, 5.0)
# 조건 (6절)
MIN_YEARS_WIN = 4
P_CUTOFF = 0.05
MIN_CELLS_PASS = 2           # 절대선 2. 12칸 중 2칸 이상
N_CELLS = len(MA_DAYS) * len(BANDS)


def fee_share(band_pct, fee=FEE_ROUND_TRIP):
    """밴드 한 왕복에서 수수료가 차지하는 몫 %."""
    gross = 2 * band_pct
    return fee / gross * 100 if gross else float("inf")


def moving_avg(s, j, n):
    """j 번째 기록 시점의 N일 이동평균. 모자라면 None.

    **j 를 포함한다** (그날 종가까지 쓴다). 그래서 체결은 다음 날
    시가여야 한다 - 안 그러면 미래를 보는 것이 된다.
    """
    if j < n - 1:
        return None
    return st.mean(s.close[j - n + 1:j + 1])


_SIG_CACHE = {}


def band_signals(s, n, k):
    """[(j, 'buy'|'sell')]. 신호가 난 기록 위치와 방향.

    신호는 그날 종가로 판정하고, 체결은 run_band 가 다음 날 시가로 한다.
    이동평균은 누적합으로 O(1) 에 뽑는다 (무작위 대조가 같은 것을 500번
    다시 부른다). 캐시도 답을 안 바꾼다 - 같은 (종목, n, k) 면 같은 답이다.
    """
    key = (id(s), n, k)
    if key in _SIG_CACHE:
        return _SIG_CACHE[key]
    cs, acc = [0.0], 0.0
    for c in s.close:
        acc += c
        cs.append(acc)
    out = []
    for j in range(n - 1, len(s.close)):
        ma = (cs[j + 1] - cs[j + 1 - n]) / n
        if ma <= 0:
            continue
        c = s.close[j]
        if c < ma * (1 - k / 100):
            out.append((j, "buy"))
        elif c > ma * (1 + k / 100):
            out.append((j, "sell"))
    _SIG_CACHE[key] = out
    return out


class Result:
    """한 종목 한 칸의 결과. 모양을 보려면 왕복 하나하나가 필요하다."""

    def __init__(self):
        self.curve = [1.0]
        self.trips = []        # 왕복마다 수수료 뺀 이익%
        self.worst_un = 0.0    # 최대 미실현 손실%
        self.cash_days = 0
        self.days = 0
        self.stops = 0         # 손절로 나간 횟수 (stop 을 줄 때만)

    def annual(self):
        return cagr(self.curve, self.days)


def run_band(s, n, k, fee=FEE_ROUND_TRIP, stop=None):
    """밴드 매매를 돌린다. stop 이 주어지면 그 손실%에서 손절한다.

    체결은 **신호 다음 날 시가**다. 그날 종가를 보고 그날 종가에 사는
    것은 미래를 보는 것이다.

    손절도 같은 규칙이다 - 종가가 손절선 아래로 마감하면 **다음 날
    시가**에 판다. analyze_stops.py 는 장중 저가를 썼지만 여기서는
    못 쓴다. strategy.load_panel() 이 open/close 만 보관하고 low 를
    안 들고 있기 때문이다. 유리/불리 어느 쪽인지 단정할 수 없으므로
    (갭하락이면 손절가보다 나쁘고, 장중에만 찍고 회복하면 더 좋다)
    그냥 다른 규칙이라고 적어둔다.
    """
    sig = {j: side for j, side in band_signals(s, n, k)}
    r = Result()
    cap, pos_price, stop_armed = 1.0, None, False
    start = min(sig) if sig else len(s.close)
    for j in range(start, len(s.close)):
        side = sig.get(j - 1)          # 어제 신호 -> 오늘 시가 체결
        if pos_price is not None and stop_armed:
            g = s.open[j] / pos_price * (1 - fee / 100)
            cap *= g
            r.trips.append((g - 1) * 100)
            pos_price, stop_armed = None, False
            r.stops += 1
        elif side == "buy" and pos_price is None:
            pos_price = s.open[j]
        elif side == "sell" and pos_price is not None:
            g = s.open[j] / pos_price * (1 - fee / 100)
            cap *= g
            r.trips.append((g - 1) * 100)
            pos_price = None
        if (pos_price is not None and stop is not None
                and s.close[j] <= pos_price * (1 + stop / 100)):
            stop_armed = True          # 오늘 종가가 뚫렸다 -> 내일 시가에 판다
        if pos_price is None:
            r.cash_days += 1
            r.curve.append(cap)
        else:
            r.worst_un = min(r.worst_un, (s.close[j] / pos_price - 1) * 100)
            r.curve.append(cap * s.close[j] / pos_price)
    r.days = max(len(s.close) - start, 0)
    return r


def buy_and_hold(s, start_j, fee=FEE_ROUND_TRIP):
    """같은 기간 그냥 들고 있기. 왕복 한 번의 수수료만 문다."""
    if start_j >= len(s.close):
        return [1.0]
    base = s.open[start_j]
    if base <= 0:
        return [1.0]
    return [1.0] + [s.close[j] / base * (1 - fee / 100)
                    for j in range(start_j, len(s.close))]


def cagr(curve, days):
    if len(curve) < 2 or curve[-1] <= 0 or days <= 0:
        return None
    return ((curve[-1] ** (TRADING_DAYS / days)) - 1) * 100


def stable_universe(dates, panel, size=UNIVERSE_SIZE):
    """잴 종목. 마지막 날 기준 거래대금 상위이고, 전 기간 자료가 있는 것.

    **전 기간 자료를 요구하는 것 자체가 생존편향**이다 (중간에 상폐된
    종목이 빠진다). 밴드 매매는 한 종목을 오래 들고 있는 전략이라
    기간이 끊기면 잴 수가 없다. 그래서 편향을 없애지 못하고 **적어만
    둔다** - 아래 결과는 살아남은 종목만 본 것이고, 그만큼 좋은 쪽으로
    기울어 있다.
    """
    di = len(dates) - 1
    uni = S.universe_at(panel, di, size=size)
    need = len(dates) * 0.9
    return [c for c in uni if len(panel[c].close) >= need]


def panel_name(panel, code):
    return code


def low_vol_codes(dates, panel, codes, n):
    """직전 60일 변동성 하위 n. 마지막 날 기준 - 사후 정보가 아니라
    '오늘 고른다면' 이라는 뜻이다."""
    di = len(dates) - 1
    scored = []
    for c in codes:
        v = S.factor_score(panel, c, di, "low_vol", vol_days=VOL_DAYS)
        if v is not None:
            scored.append((v, c))
    scored.sort(reverse=True)
    return [c for _v, c in scored[:n]]


def subset(rows, codes, keep):
    """rows 는 codes 순서와 같지 않다 (건너뛴 종목이 있다). 다시 잰다."""
    return [(e, r) for (e, r), c in zip(rows, codes) if c in keep]


def year_edges(s, n, k, dates, fee=FEE_ROUND_TRIP):
    """해마다 (밴드 수익%, 보유 수익%). 조건 1/2/4 에 쓴다."""
    sig = {j: side for j, side in band_signals(s, n, k)}
    if not sig:
        return {}
    out, cap, pos = {}, 1.0, None
    start = min(sig)
    for j in range(start, len(s.close)):
        y = dates[s.di[j]][:4]
        e = out.setdefault(y, [1.0, 1.0, None, None])
        side = sig.get(j - 1)
        if side == "buy" and pos is None:
            pos = s.open[j]
        elif side == "sell" and pos is not None:
            cap *= s.open[j] / pos * (1 - fee / 100)
            pos = None
        val = cap if pos is None else cap * s.close[j] / pos
        if e[2] is None:
            e[2], e[3] = val, s.close[j]
        e[0], e[1] = val, s.close[j]
    res = {}
    for y, (v1, p1, v0, p0) in out.items():
        if v0 and p0:
            res[y] = ((v1 / v0 - 1) * 100, (p1 / p0 - 1) * 100)
    return res


def judge(dates, panel, codes, n, k, rows, perms):
    """조건 넷 + 절대선 1. 결과를 보고 조건을 고치지 않는다."""
    edges = [e for e, _r in rows]
    med = st.median(edges)
    c_abs = med > 0                       # 절대선 1: 중앙값에서 이긴다

    per_year = {}
    for code in codes:
        for y, (bv, hv) in year_edges(panel[code], n, k, dates).items():
            per_year.setdefault(y, []).append(bv - hv)
    ys = sorted(y for y in per_year if len(per_year[y]) >= 10)
    yr_med = {y: st.median(per_year[y]) for y in ys}
    wins = sum(1 for y in ys if yr_med[y] > 0)
    c1 = wins >= MIN_YEARS_WIN
    half = len(ys) // 2
    first = st.median([yr_med[y] for y in ys[:half]]) if half else 0.0
    second = st.median([yr_med[y] for y in ys[half:]]) if ys[half:] else 0.0
    c2 = (first > 0) and (second > 0) or (first < 0) and (second < 0)
    c2 = c2 and first > 0
    best_y = max(yr_med, key=lambda y: yr_med[y]) if yr_med else None
    drop = st.median([yr_med[y] for y in ys if y != best_y]) if len(ys) > 1 \
        else 0.0
    c4 = drop > 0
    p = control_p(panel, codes, n, k, med, perms)
    c3 = p < P_CUTOFF
    ok = c_abs and c1 and c2 and c3 and c4
    detail = (f"중앙 {med:+6.2f}%p  "
              f"조건1 {'O' if c1 else 'X'}({wins}/{len(ys)}) "
              f"조건2 {'O' if c2 else 'X'} "
              f"조건3 {'O' if c3 else 'X'}(p={p:.3f}) "
              f"조건4 {'O' if c4 else 'X'}({drop:+.2f}) "
              f"절대선 {'O' if c_abs else 'X'} => "
              f"{'통과' if ok else '탈락'}")
    return ok, detail


def control_p(panel, codes, n, k, real_med, perms):
    """무작위 대조. 같은 횟수만큼 **무작위 날짜에** 사고 판다.

    밴드가 이긴다면 그게 '싸게 사서 비싸게 판' 덕인지, 아니면 그냥
    '자주 사고 파는' 덕인지를 가른다. 후자라면 무작위로 해도 같은
    우위가 나오고 p 가 커진다.
    """
    if perms <= 0:
        return float("nan")
    # 밴드 쪽 횟수/기간/보유수익은 섞어도 안 변한다. 한 번만 구한다.
    fixed = []
    for code in codes[:40]:               # 500회 x 200종목은 너무 느리다
        s = panel[code]
        r = run_band(s, n, k)
        if r.days < TRADING_DAYS or not r.trips:
            continue
        bh = cagr(buy_and_hold(s, len(s.close) - r.days), r.days)
        if bh is None:
            continue
        fixed.append((s, len(r.trips), r.days, bh))
    if not fixed:
        return float("nan")
    hits, done = 0, 0
    for _ in range(perms):
        meds = []
        for s, n_trips, days, bh in fixed:
            a = shuffled_annual(s, n_trips, days)
            if a is not None:
                meds.append(a - bh)
        if not meds:
            continue
        done += 1
        if st.median(meds) >= real_med:
            hits += 1
    return (hits + 1) / (done + 1) if done else float("nan")


def shuffled_annual(s, n_trips, days, fee=FEE_ROUND_TRIP):
    """무작위 날짜에 n_trips 번 사고 판다. 밴드와 횟수만 같다."""
    start = len(s.close) - days
    if n_trips <= 0 or start < 0 or days < 2:
        return None
    picks = sorted(random.sample(range(start, len(s.close)),
                                 min(2 * n_trips, days)))
    cap, pos = 1.0, None
    for j in picks:
        if pos is None:
            pos = s.open[j]
        else:
            cap *= s.open[j] / pos * (1 - fee / 100)
            pos = None
    if pos is not None:
        cap *= s.close[-1] / pos * (1 - fee / 100)
    if cap <= 0:
        return None
    return ((cap ** (TRADING_DAYS / days)) - 1) * 100


def main(argv=None):
    ap = argparse.ArgumentParser(description="밴드 매매")
    ap.add_argument("--perms", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260922)
    args = ap.parse_args(argv)
    random.seed(args.seed)

    print("=== 수수료 (2절) ===")
    for k in BANDS:
        print(f"  +-{k:.0f}%  왕복 {2 * k:.0f}%  수수료 비중 "
              f"{fee_share(k):.1f}%")
    dates, panel = S.load_panel()
    codes = stable_universe(dates, panel)
    print(f"\n유니버스 {len(codes)}종목 (마지막 날 거래대금 상위, "
          f"전 기간 자료가 있는 것만)")

    # --------------------------------------------------- 격자 12칸
    print(f"\n=== 측정 1. 격자 {N_CELLS}칸, 종목 {len(codes)}개의 분포 ===")
    print("  (밴드 연수익% - 같은 종목 보유 연수익%. 양수면 밴드가 이긴 것)")
    print(f"  {'MA':>4}{'밴드':>6}{'중앙 우위':>11}{'이긴 종목':>11}"
          f"{'연 왕복':>9}{'현금 비율':>11}{'최악 미실현':>12}")
    cells = {}
    for n in MA_DAYS:
        for k in BANDS:
            rows = []
            for code in codes:
                s = panel[code]
                r = run_band(s, n, k)
                if r.days < TRADING_DAYS or not r.trips:
                    continue
                bh = buy_and_hold(s, len(s.close) - r.days)
                a, b = r.annual(), cagr(bh, r.days)
                if a is None or b is None:
                    continue
                rows.append((a - b, r))
            if not rows:
                continue
            edges = [e for e, _r in rows]
            cells[(n, k)] = rows
            med = st.median(edges)
            win = sum(1 for e in edges if e > 0) / len(edges) * 100
            trips = st.median([len(r.trips) / (r.days / TRADING_DAYS)
                               for _e, r in rows])
            cash = st.median([r.cash_days / r.days * 100 for _e, r in rows])
            wun = st.median([r.worst_un for _e, r in rows])
            print(f"  {n:>4}{k:>5.0f}%{med:>10.2f}%p{win:>10.1f}%"
                  f"{trips:>9.1f}{cash:>10.1f}%{wun:>11.1f}%")

    # --------------------------------------------------- 모양
    best = max(cells, key=lambda c: st.median([e for e, _r in cells[c]]))
    print(f"\n=== 측정 2. 이득 분포의 모양 (제일 나은 칸 MA{best[0]} "
          f"+-{best[1]:.0f}%) ===")
    print("  3절의 '작은 이득 자주 / 큰 손해 가끔' 이 실제로 그런가")
    allt = [t for _e, r in cells[best] for t in r.trips]
    wins = [t for t in allt if t > 0]
    loss = [t for t in allt if t <= 0]
    print(f"  왕복 {len(allt):,}건")
    print(f"    이긴 왕복  {len(wins) / len(allt) * 100:5.1f}%  "
          f"중앙 {st.median(wins):+.2f}%  최고 {max(wins):+.1f}%")
    print(f"    진 왕복    {len(loss) / len(allt) * 100:5.1f}%  "
          f"중앙 {st.median(loss):+.2f}%  최악 {min(loss):+.1f}%")
    print(f"    전체 중앙 {st.median(allt):+.2f}%, 평균 "
          f"{st.mean(allt):+.2f}%")
    print(f"  -> 이긴 왕복 평균 {st.mean(wins):+.2f}% vs "
          f"진 왕복 평균 {st.mean(loss):+.2f}%  "
          f"(크기 비 {abs(st.mean(loss) / st.mean(wins)):.2f}배)")

    # --------------------------------------------------- 안정적인 종목
    print(f"\n=== 측정 3. '안정적인 종목' 만 (직전 60일 변동성 하위 "
          f"{STABLE_N}) ===")
    stable = low_vol_codes(dates, panel, codes, STABLE_N)
    print(f"  {', '.join(panel_name(panel, c) for c in stable)}")
    print(f"  {'MA':>4}{'밴드':>6}{'중앙 우위':>11}{'이긴 종목':>11}"
          f"{'연 왕복':>9}{'최악 미실현':>12}")
    for n in MA_DAYS:
        for k in BANDS:
            rows = [(e, r) for (e, r), c in zip(cells.get((n, k), []),
                                                codes) if c in stable] \
                if (n, k) in cells else []
            rows = subset(cells.get((n, k), []), codes, stable)
            if not rows:
                continue
            edges = [e for e, _r in rows]
            print(f"  {n:>4}{k:>5.0f}%{st.median(edges):>10.2f}%p"
                  f"{sum(1 for e in edges if e > 0) / len(edges) * 100:>10.1f}%"
                  f"{st.median([len(r.trips) / (r.days / TRADING_DAYS) for _e, r in rows]):>9.1f}"
                  f"{st.median([r.worst_un for _e, r in rows]):>11.1f}%")

    # --------------------------------------------------- 손절
    print(f"\n=== 측정 4. 손절 -10% 를 붙이면 (격자 밖, 보고용) ===")
    n, k = best
    rows = []
    for code in codes:
        s = panel[code]
        r0, r1 = run_band(s, n, k), run_band(s, n, k, stop=-10.0)
        if r0.days < TRADING_DAYS or not r0.trips or not r1.trips:
            continue
        a0, a1 = r0.annual(), r1.annual()
        if a0 is None or a1 is None:
            continue
        rows.append((a0, a1, r0, r1))
    if rows:
        print(f"  MA{n} +-{k:.0f}% 에서, 종목 {len(rows)}개 중앙값")
        print(f"    손절 없음  연 {st.median([a for a, _b, _c, _d in rows]):+.2f}%"
              f"  최악 미실현 "
              f"{st.median([c.worst_un for _a, _b, c, _d in rows]):.1f}%")
        print(f"    손절 -10%  연 {st.median([b for _a, b, _c, _d in rows]):+.2f}%"
              f"  최악 미실현 "
              f"{st.median([d.worst_un for _a, _b, _c, d in rows]):.1f}%"
              f"  손절 {st.median([d.stops for _a, _b, _c, d in rows]):.0f}회")

    # --------------------------------------------------- 조건 판정
    print(f"\n=== 측정 5. 조건 판정 (6절) ===")
    passed = []
    for (n, k), rows in sorted(cells.items()):
        ok, detail = judge(dates, panel, codes, n, k, rows, args.perms)
        print(f"  MA{n:>4} +-{k:.0f}%  {detail}")
        if ok:
            passed.append((n, k))
    print(f"\n  넷을 다 통과한 칸 {len(passed)}개 "
          f"(절대선 2 는 {MIN_CELLS_PASS}개 이상)")
    print(f"  => {'채택' if len(passed) >= MIN_CELLS_PASS else '탈락'}")
    print(f"\n  독립 표본: 달력 연도 5~6개 (표본.md). 종목 {len(codes)}개는"
          f" 서로 독립이 아니다 - 같은 시장을 같이 타기 때문이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
