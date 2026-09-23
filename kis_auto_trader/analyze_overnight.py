"""드리프트가 장중에 있나 오버나이트에 있나. (기준만 - 결과 미기입)

(2026-09-22 신설) 사용자: "10분, 20분 짧은 변동 동안 수수료 이상의 이득을
얻고 그걸 반복하는 거 (...) 그 목표에 집중해보자", "인터넷에 단기 투자를
하는 사람들의 (...) 우리가 놓치고 있는 지표나 사실을 알려줄 수도 있다"

공개 자료를 뒤져서 나온 것 중, **새 수집 없이 지금 잴 수 있는 것**이
하나 있다. 이 파일이 그것이다.

===========================================================================
0 - 이 파일은 결과를 보기 전에 쓴다 (사전 등록)
===========================================================================
아래 조건들은 숫자를 보기 전에 정했다. git log 가 순서를 증명한다.
결과를 보고 조건을 고치면 이 저장소의 모든 판정이 무의미해진다.

===========================================================================
1 - 밖에서 가져온 사실
===========================================================================
(a) 대만 개인 데이트레이더 전수 (1992~2006, Barber/Lee/Liu/Odean)
    수수료 차감 후 이익 약 5%. 활발한 상위권만 봐도 약 20%.
    평균 **하루 -23.9bp**. 생존 1년 44% / 2년 24% / 3년 15%.
    -> 저 -0.239%/일이 우리가 잰 왕복 수수료 0.21% 와 거의 같다.
       "예측을 못 해서" 가 아니라 **비용으로** 진다는 우리 계산과 맞다.

(b) 시초 30분 -> 마감 30분 (Gao/Han/Li/Zhou, JFE 2018)
    예측 R^2 1.6%. 변동성/거래량 큰 날에 강해진다.
    KOSPI 확인본도 있다 (JRFM 2022): 오버나이트 + 첫 30분이 마지막
    30분을 예측한다.
    -> 우리 10분봉으로 언젠가 잴 수 있다. **지금은 1일치라 못 잰다.**

(c) 마감 30분 반전, 개별종목 (Baltussen/Da/Soebhag)
    지수는 momentum 인데 개별종목은 reversal 이다. 방향이 반대다.
    -> 이것도 10분봉이 쌓여야 잰다.

(d) **오버나이트 vs 장중.** 여러 시장에서, 수십 년 누적수익이 거의 전부
    오버나이트(종가->다음 시가)에 있고 장중(시가->종가)은 0 근처이거나
    마이너스다. 한 ETF 예: 전체 +8%/년, 오버나이트 +12.9%, 장중 -4.3%.

(e) 돌파매매(ORB)는 비용을 못 넘는다. 사전등록 연구, 선물 16년, 225개
    조합, 중앙값 -0.01틱/거래. 살아남은 칸도 무작위 대조에서 탈락.
    -> 우리가 돌파매매를 새로 재볼 이유가 줄었다.

(f) 한국 실전 쪽에서 반복해 나오는 지표: 거래대금 상위 / 상승률 상위 /
    거래량 급증(평소 200~500%) / 시간대보정 RVOL 2.0배 / 09:00~09:30.
    -> 논문 뒷받침은 못 찾았다. **우리가 한 번도 안 잰 변수**이긴 하다.

===========================================================================
2 - 그래서 이 파일이 재는 것 (d 번. 지금 잴 수 있는 유일한 것)
===========================================================================
하루를 둘로 쪼갠다.

  오버나이트   전일 종가 -> 당일 시가   (장이 닫혀 있는 동안)
  장중         당일 시가 -> 당일 종가   (장이 열려 있는 동안)
  둘을 곱하면  전일 종가 -> 당일 종가   (= 우리가 늘 쓰던 일간수익률)

**단타는 장중에만 산다.** 10분봉도, 손절/익절도, 눌림목도 전부 장중이다.
그러니 장중에 드리프트가 없으면 단타는 흐름이 없는 물에서 낚시하면서
왕복마다 0.21% 를 내는 것이 된다.

이건 **새로 수집할 게 없다.** data/krx_panel_*.csv 에 1,813종목 x
1,402거래일의 open 과 close 가 이미 있다.

===========================================================================
3 - 이 파일이 답할 수 없는 것 (미리 밝힌다)
===========================================================================
- 시가/종가는 **동시호가로 결정된 단일가**다. 그 가격에 원하는 수량이
  체결된다는 보장이 없다. 특히 저유동 종목에서 그렇다.
  -> 그래서 유동성 상위(유니버스 200)에서만 잰다. 그래도 남는 위험이다.
- 실제 체결가와 단일가의 차이(슬리피지)는 **우리가 한 번도 못 쟀다.**
  호가 수집이 없기 때문이다. 이 파일은 그 차이를 0 으로 놓는다.
  0 이 아니므로 아래 결과는 전부 **상한**이다.
- 장중이 마이너스여도 "공매도로 먹으면 된다" 는 결론은 못 낸다.
  개인 공매도는 제약이 크고 이 저장소는 주문 자체가 없다.

===========================================================================
4 - 측정 넷
===========================================================================
측정 1. 유니버스 동일가중으로, 해마다
        오버나이트 연환산 % / 장중 연환산 % / 합계
        (합계가 analyze_follow_up 의 -7.0% 와 맞아야 한다. 검산이다.)

측정 2. 저변동 10종목(우리 전략의 실제 보유)에 같은 분해.
        전략이 버는 22.3% 가 어느 쪽에서 나오나.

측정 3. **실행 가능성.** "종가 사서 다음 시가 판다" 를 매일 하면
        하루에 왕복 0.21% 를 낸다. 오버나이트 일평균이 0.21% 를
        넘나. (넘으면 연 66% 라 거의 확실히 안 넘는다. 그래도 잰다 -
        안 재고 "안 될 것이다" 라고 쓰면 그건 측정이 아니다.)

측정 4. **체결 시점만 바꾸기.** 이게 실제로 쓸 수 있는 부분이다.
        저변동 120일 전략은 교체 횟수가 고정(연 2.05회)이라 수수료가
        안 늘어난다. 같은 횟수로 **언제 체결하느냐**만 바꾼다.

          (A) 시가 매수 / 시가 매도   <- 지금
          (B) 종가 매수 / 종가 매도
          (C) 종가 매수 / 시가 매도   <- 오버나이트를 한 번 더 먹는다
          (D) 시가 매수 / 종가 매도   <- 장중을 한 번 더 먹는다

        사람은 매번 정확히 종가/시가에 못 넣는다. 프로그램은 넣는다.
        전제.md 가 말한 "자동화만 되는 이득" 에 해당한다.

===========================================================================
5 - 받아들이는 조건 (결과 보기 전에 정한다)
===========================================================================
측정 1~2 (드리프트가 어디 있나) 는 **서술**이다. 통과/탈락이 없다.
다만 표본.md 규약대로 **독립 표본 수(달력 연도 5개)를 같이 적는다.**

측정 4 (체결 시점) 는 **전략 변경**이므로 넷을 다 넘어야 채택한다.

  조건 1  달력 연도 5개 중 **4개 이상**에서 새 방식이 (A) 보다 낫다.
  조건 2  반띵(전반 2021~2023 / 후반 2024~2026) **양쪽 다** 같은 방향.
  조건 3  무작위 대조 500회. 교체일을 무작위 날짜로 바꿔도 같은 격차가
          나오면 그건 시점의 정보가 아니라 그냥 드리프트다. p < 0.05.
  조건 4  가장 좋았던 해를 빼도 격차가 여전히 양수.

  그리고 **절대선**: 격차가 연 0.10%p 미만이면 채택하지 않는다.
  슬리피지를 못 쟀기 때문이다. 못 잰 비용보다 작은 이득은 이득이
  아니라 측정 오차다. (0.10%p 는 왕복 2.05회 x 편도 0.024% 어림이다.)

===========================================================================
6 - 결과
===========================================================================
6.1 측정 1 - 유니버스 200 동일가중 (수수료 전, 연환산)

  해        오버나이트      장중       합계    거래일
  2021        +56.3%    -39.1%     -4.8%     227
  2022         +9.9%    -45.5%    -40.1%     246
  2023        +53.2%    -31.0%     +5.7%     245
  2024        +30.5%    -40.7%    -22.5%     244
  2025        +81.2%    -17.9%    +48.9%     242
  2026       +178.8%    -54.1%    +28.5%     177
  평균        +60.9%    -39.1%     -1.8%

  일평균  오버나이트 +0.1936%,  장중 -0.2011%
  독립 표본 6개 (달력 연도. 표본.md 규약대로 같이 적는다)

**6년 6번 모두 오버나이트 양수 / 장중 음수다.** 방향이 한 번도 안
뒤집혔다. 밖에서 읽은 (d) 가 한국에서도 그대로 나온다.

  [검산] 사전 등록에 "합계가 analyze_follow_up 의 -7.0% 와 맞아야
  한다" 고 썼다. 산술평균을 연환산하면 -1.8% 로 안 맞는다. 실제로
  복리로 굴리면 **-7.8%** 이고 이건 맞는다. 차이 6.0%p 는 분산
  손실이다 (매일 +1%/-1% 를 오가면 산술평균은 0 인데 실제로는 줄어든다).
  -> 검산은 통과했다. 대신 **일평균을 연환산한 숫자를 '벌 수 있는 돈'
     으로 읽으면 안 된다.** 이 절의 +60.9% 가 그런 숫자다.

6.2 측정 2 - 저변동 10종목 (우리가 실제로 담는 것)

  해        오버나이트      장중       합계
  2021         +3.0%     -3.0%     -0.1%
  2022        -15.2%    +10.3%     -6.4%
  2023         +9.4%     +3.3%    +13.1%
  2024        +20.7%     -4.6%    +15.1%
  2025         +9.6%    +29.2%    +41.5%
  2026        +81.7%    -14.7%    +55.0%
  평균        +14.9%     +2.5%    +17.8%

  일평균  오버나이트 +0.0563%,  장중 +0.0102%

**저변동에서는 격차가 훨씬 작고, 장중도 양수다.** 유니버스에서는
100%p 격차인데 저변동에서는 12%p 다. 이 차이가 6.4 의 실마리다.

6.3 측정 3 - "매일 종가 사서 다음 시가 판다" 는 되나

  왕복 수수료              0.210% / 일
  유니버스 200 오버나이트   +0.1936% / 일  -> 수수료 후 -0.0164%  (연 -4%)
  저변동 10   오버나이트   +0.0563% / 일  -> 수수료 후 -0.1537%  (연 -31%)

**안 된다.** 유니버스 쪽은 아깝게 못 넘는다 - 필요한 0.210% 에
0.1936% 로 92% 까지 갔다. 하지만 못 넘은 것은 못 넘은 것이고, 여기에
슬리피지가 아직 안 들어갔다 (3절). 슬리피지는 반드시 음수다.

6.4 측정 5 (사후) - 이 격차가 진짜인가

  변동성 구간   오버나이트      장중    격차(일)    종목-일
  1 저변동      +23.1%     -8.8%   0.1219%    51,188
  2            +48.2%    -22.0%   0.2611%    51,182
  3            +72.4%    -35.0%   0.3964%    51,187
  4            +68.6%    -46.8%   0.4690%    51,182
  5 고변동      +64.9%    -59.1%   0.5666%    51,114

  고변동/저변동 격차 = **4.6배**, 그리고 1->5 가 한 번도 안 꺾이고
  단조 증가한다.

**이건 호가 튀기(bid-ask bounce)의 지문이다.** 종가는 매도호가 쪽에서,
시가는 매수호가 쪽에서 결정되는 쏠림이 있으면, 호가 폭이 넓은 종목일수록
가짜 오버나이트 수익이 크게 잡힌다. 변동성이 큰 종목이 곧 호가가 넓은
종목이다. 진짜 오버나이트 위험 프리미엄이라면 변동성과 이렇게 4.6배로
깔끔하게 붙어 있을 이유가 없다.

**이건 사후 검사라 이걸로 아무것도 채택하지 않는다.** 다만 6.3 이
이미 "안 된다" 이므로, 6.4 는 그 결론을 뒤집으려는 시도를 막는 쪽으로만
쓴다 - "0.1936% 가 0.210% 에 이렇게 가까우니 조금만 더 하면" 이라는
생각을 하면 안 된다는 뜻이다. 그 0.1936% 자체가 상당 부분 가짜다.

6.5 측정 4 - 체결 시점만 바꾸기 (실제로 쓸 수 있었던 부분)

  방식                   연수익   2021   2022   2023   2024   2025   2026
  A 시가매수/시가매도(지금) 12.6%   +0.3%  -9.9%  -1.9% +27.1% +27.4% +36.9%
  B 종가매수/종가매도      12.3%   -0.3%  -9.2%  -2.1% +22.4% +27.1% +40.2%
  C 종가매수/시가매도      12.1%   +1.0%  -9.5%  -2.4% +25.5% +28.2% +33.6%
  D 시가매수/종가매도      12.7%   -1.1%  -9.6%  -1.5% +23.9% +26.3% +43.7%

  방식   격차    이긴 해   전반     후반    최고해 빼고   대조 p    판정
  B    -0.33%p   2/6   -0.03%p -0.58%p   -1.01%p   0.687   탈락
  C    -0.48%p   3/6   +0.20%p -1.37%p   -0.86%p   0.786   탈락
  D    +0.15%p   3/6   -0.23%p +0.83%p   -1.00%p   0.397   탈락

**셋 다 탈락이다.** D 만 격차가 양수인데 조건 1(4/6 필요, 3/6),
조건 2(전반 음수/후반 양수), 조건 4(최고 해를 빼면 -1.00%p) 에서 진다.
대조 p 0.397 은 "무작위로 교체일을 옮겨도 이 정도 격차는 40% 확률로
나온다" 는 뜻이다.

**결론: 체결 시점은 바꾸지 않는다. 지금 방식(A)을 그대로 둔다.**

6.6 그래서 남는 한 줄

  하루를 쪼개면 드리프트는 **장이 닫혀 있는 동안**에 있고, 장이
  열려 있는 동안은 마이너스다. 단타는 마이너스인 쪽에서만 논다.
  그런데 닫혀 있는 쪽도 (a) 수수료를 못 넘고 (b) 상당 부분 가짜다.

===========================================================================
7 - 한계
===========================================================================
0) **슬리피지가 0 으로 들어가 있다.** 호가를 한 번도 수집한 적이 없어서
   실제 체결가와 단일가의 차이를 모른다. 위 숫자는 전부 상한이다.
   이게 이 파일에서 제일 큰 구멍이고, 호가 수집을 시작해야 메워진다.

1) **시가/종가는 동시호가 단일가다.** 그 가격에 원하는 수량이 체결된다는
   보장이 없다. 유동성 상위 200 에서만 쟀지만 그래도 남는 위험이다.

2) 독립 표본이 달력 연도 6개다 (측정 1) / 5개다 (측정 4 는 2021 이
   반 년뿐이라 사실상). 표본.md 의 문제가 여기도 그대로 있다.
   다만 측정 1 은 6/6 이 같은 방향이고 종목-일이 25만 건이라 방향
   자체는 연도 표본에만 기대고 있지 않다.

3) **측정 5 는 사후 검사다.** "호가 튀기다" 를 증명한 게 아니라
   "호가 튀기와 모양이 같다" 를 보인 것이다. 진짜로 가르려면 호가
   데이터가 있어야 한다. 그래서 7-0 과 같은 구멍이다.

4) 장중이 마이너스라고 "공매도하면 된다" 가 안 된다. 개인 공매도는
   제약이 크고, 이 저장소는 주문 함수 자체가 없다.

5) 밖에서 읽은 (b)(c) - 시초 30분/마감 30분 - 는 **아직 못 쟀다.**
   10분봉이 1일치뿐이다. 20거래일이 쌓이면 그때 잰다.

6) (f) 의 지표들(거래대금 상위, 거래량 급증, 시간대보정 RVOL)도
   아직 안 쟀다. 이건 10분봉 없이도 일봉으로 일부 잴 수 있다.

실행:
  python analyze_overnight.py
  python analyze_overnight.py --perms 500
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
FEE_ROUND_TRIP = 0.21        # 매수 0.015 + 매도 0.015 + 거래세 0.180
UNIVERSE_SIZE = 200
PICK_N = 10
PERIOD = 120
FACTOR = "low_vol"
VOL_DAYS = 60
# 조건들 (5절. 결과 보기 전에 정했다)
MIN_YEARS_WIN = 4            # 조건 1
N_YEARS = 5                  # 달력 연도 - 독립 표본 수 (표본.md)
P_CUTOFF = 0.05              # 조건 3
MIN_EDGE_PP = 0.10           # 절대선. 슬리피지를 못 쟀으므로 이 아래는 안 본다
# 측정 4 의 네 가지 체결 방식. (매수 시점, 매도 시점)
FILLS = (("A 시가매수/시가매도", "open", "open"),
         ("B 종가매수/종가매도", "close", "close"),
         ("C 종가매수/시가매도", "close", "open"),
         ("D 시가매수/종가매도", "open", "close"))


def split_day(s, j):
    """한 종목의 j 번째 기록을 오버나이트/장중으로 쪼갠다.

    (오버나이트%, 장중%) 를 돌려준다. j == 0 이면 전일 종가가 없으므로
    오버나이트는 None 이다. **0 으로 메우지 않는다** - 메우면 장이
    열리기 전 수익이 0 이었다고 거짓말하는 것이 된다.
    """
    intra = (s.close[j] / s.open[j] - 1) * 100
    if j == 0:
        return None, intra
    # 전일이 바로 어제가 아닐 수 있다 (거래정지 등). di 가 이어져야만 쓴다.
    if s.di[j] != s.di[j - 1] + 1:
        return None, intra
    over = (s.open[j] / s.close[j - 1] - 1) * 100
    return over, intra


def year_of(date):
    return date[:4]


def decompose(dates, panel, codes_at, label=""):
    """해마다 (오버나이트 일평균%, 장중 일평균%, 종목-일 수).

    codes_at(di) 가 그날 담는 종목을 돌려준다. 동일가중이다.
    그날 담은 종목이 없으면 그 날은 아예 안 센다 (0% 로도 안 센다).
    """
    by_year = {}
    for di, date in enumerate(dates):
        codes = codes_at(di)
        if not codes:
            continue
        overs, intras = [], []
        for code in codes:
            s = panel.get(code)
            if s is None:
                continue
            j = s.pos.get(di)
            if j is None:
                continue
            o, i = split_day(s, j)
            if o is None:
                continue          # 오버나이트를 모르는 날은 둘 다 버린다
            overs.append(o)
            intras.append(i)
        if not overs:
            continue
        y = by_year.setdefault(year_of(date), [[], []])
        y[0].append(st.mean(overs))
        y[1].append(st.mean(intras))
    out = {}
    for y, (ov, iv) in sorted(by_year.items()):
        out[y] = (st.mean(ov), st.mean(iv), len(ov))
    return out


def compound_universe(dates, panel, codes_at):
    """유니버스 동일가중을 **실제로 복리로** 굴린 연수익%.

    산술평균을 연환산한 값과 이게 다르다. 매일 +1%/-1% 를 오가면
    산술평균은 0 인데 실제로는 줄어든다 (분산 손실). 어느 쪽이 맞냐가
    아니라 서로 다른 것을 재는 것이고, '얼마 벌었나' 는 이쪽이다.
    """
    acc, n = 1.0, 0
    for di, _d in enumerate(dates):
        codes = codes_at(di)
        if not codes:
            continue
        rets = []
        for code in codes:
            s = panel.get(code)
            if s is None:
                continue
            j = s.pos.get(di)
            if j is None or j == 0 or s.di[j] != s.di[j - 1] + 1:
                continue
            rets.append(s.close[j] / s.close[j - 1] - 1)
        if not rets:
            continue
        acc *= (1 + st.mean(rets))
        n += 1
    if n == 0 or acc <= 0:
        return float("nan")
    return ((acc ** (TRADING_DAYS / n)) - 1) * 100


def annualize(daily_pct, days=TRADING_DAYS):
    """일평균 %를 연환산 %로. 복리로 센다."""
    return ((1 + daily_pct / 100) ** days - 1) * 100


def rebalance_days(dates, period=PERIOD, start=None):
    """교체하는 날의 di 목록. start 가 None 이면 첫 교체 가능일부터."""
    first = start if start is not None else S.LIQUIDITY_DAYS + VOL_DAYS + 1
    return list(range(first, len(dates), period))


_PICK_CACHE = {}


def pick_low_vol(panel, di, n=PICK_N, size=UNIVERSE_SIZE):
    """그날 저변동 n 종목. 미래를 안 본다 (universe_at 이 di-1 까지만 본다).

    무작위 대조 500회가 같은 di 를 계속 다시 뽑으므로 캐시한다. 캐시는
    결과를 바꾸지 않는다 - 같은 di 면 같은 답이다.
    """
    key = (di, n, size)
    if key in _PICK_CACHE:
        return _PICK_CACHE[key]
    uni = S.universe_at(panel, di, size=size)
    scored = []
    for c in uni:
        v = S.factor_score(panel, c, di, FACTOR, vol_days=VOL_DAYS)
        if v is not None:
            scored.append((v, c))
    scored.sort(reverse=True)          # low_vol 은 -표준편차라 큰 쪽이 저변동
    out = [c for _v, c in scored[:n]]
    _PICK_CACHE[key] = out
    return out


def vol_split(dates, panel, n_bucket=5):
    """**사후 검사.** 변동성 구간별로 오버나이트/장중 분해.

    이건 사전 등록에 없다. 그러니 이걸로는 아무것도 채택하지 않는다.
    오직 하나를 가른다 - 측정 1 의 큰 격차가 진짜 드리프트인가,
    아니면 호가 튀기(bid-ask bounce) 같은 미시구조 때문인가.

    미시구조라면 **변동성이 클수록 격차가 커야 한다.** 싼 주식, 넓은
    호가, 많이 흔들리는 주식에서 종가가 매도호가/매수호가 사이를
    튀는 폭이 크기 때문이다. 진짜 오버나이트 위험 프리미엄이라면
    변동성과 그렇게까지 깔끔하게 붙어 있을 이유가 없다.
    """
    buckets = [[[], []] for _ in range(n_bucket)]
    for di in range(S.LIQUIDITY_DAYS + VOL_DAYS + 1, len(dates)):
        uni = S.universe_at(panel, di, size=UNIVERSE_SIZE)
        scored = []
        for c in uni:
            v = S.factor_score(panel, c, di, FACTOR, vol_days=VOL_DAYS)
            if v is not None:
                scored.append((v, c))
        if len(scored) < n_bucket:
            continue
        scored.sort(reverse=True)      # 앞이 저변동, 뒤가 고변동
        size = len(scored) // n_bucket
        for b in range(n_bucket):
            part = scored[b * size:(b + 1) * size]
            for _v, c in part:
                s = panel.get(c)
                if s is None:
                    continue
                j = s.pos.get(di)
                if j is None:
                    continue
                o, i = split_day(s, j)
                if o is None:
                    continue
                buckets[b][0].append(o)
                buckets[b][1].append(i)
    return [(st.mean(ov) if ov else None, st.mean(iv) if iv else None,
             len(ov)) for ov, iv in buckets]


def leg_price(s, j, when):
    """체결 가격. when 은 'open' 또는 'close'."""
    return s.open[j] if when == "open" else s.close[j]


def run_fill(dates, panel, rounds, buy_at, sell_at, fee=FEE_ROUND_TRIP):
    """체결 시점을 바꿔가며 저변동 전략을 돌린다. (해별 수익%, 전체 곡선).

    rounds 는 [(매수 di, 매도 di, [종목])]. 종목 선정은 방식마다 같다 -
    **바꾸는 것은 오직 체결 시점 하나**다. 그래야 격차가 시점의 것이다.
    """
    by_year, curve = {}, [1.0]
    for buy_di, sell_di, codes in rounds:
        rets = []
        for code in codes:
            s = panel.get(code)
            if s is None:
                continue
            jb, js = s.pos.get(buy_di), s.pos.get(sell_di)
            if jb is None or js is None:
                continue
            pb, ps = leg_price(s, jb, buy_at), leg_price(s, js, sell_at)
            if pb <= 0 or ps <= 0:
                continue
            rets.append(ps / pb - 1)
        if not rets:
            continue
        r = st.mean(rets) - fee / 100      # 왕복 수수료를 회차마다 뗀다
        curve.append(curve[-1] * (1 + r))
        by_year.setdefault(year_of(dates[sell_di]), []).append(r)
    years = {}
    for y, rs in sorted(by_year.items()):
        acc = 1.0
        for r in rs:
            acc *= (1 + r)
        years[y] = (acc - 1) * 100
    return years, curve


def cagr(curve, n_days):
    if len(curve) < 2 or curve[-1] <= 0 or n_days <= 0:
        return None
    return ((curve[-1] ** (TRADING_DAYS / n_days)) - 1) * 100


def build_rounds(dates, panel, period=PERIOD, start=None):
    """교체 회차. 종목 선정은 한 번만 하고 네 방식이 공유한다."""
    days = rebalance_days(dates, period, start)
    rounds = []
    for k in range(len(days) - 1):
        buy_di, sell_di = days[k], days[k + 1]
        codes = pick_low_vol(panel, buy_di)
        if codes:
            rounds.append((buy_di, sell_di, codes))
    return rounds


def main(argv=None):
    ap = argparse.ArgumentParser(description="오버나이트 vs 장중 분해")
    ap.add_argument("--perms", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20260922)
    args = ap.parse_args(argv)
    random.seed(args.seed)

    dates, panel = S.load_panel()
    n_days = len(dates)

    # ---------------------------------------------------------- 측정 1
    print("\n=== 측정 1. 유니버스 200 동일가중, 해마다 ===")
    print("(오버나이트 = 전일종가->시가, 장중 = 시가->종가. 수수료 전)")
    uni_cache = {}

    def uni_at(di):
        if di < S.LIQUIDITY_DAYS + 1:
            return []
        if di not in uni_cache:
            uni_cache[di] = S.universe_at(panel, di, size=UNIVERSE_SIZE)
        return uni_cache[di]

    uni_year = decompose(dates, panel, uni_at)
    print(f"  {'해':<6}{'오버나이트':>12}{'장중':>12}{'합계':>12}"
          f"{'거래일':>8}")
    for y, (ov, iv, n) in uni_year.items():
        print(f"  {y:<6}{annualize(ov):>11.1f}%{annualize(iv):>11.1f}%"
              f"{annualize(ov + iv):>11.1f}%{n:>8}")
    ov_all = st.mean([v[0] for v in uni_year.values()])
    iv_all = st.mean([v[1] for v in uni_year.values()])
    print(f"  {'평균':<6}{annualize(ov_all):>11.1f}%{annualize(iv_all):>11.1f}%"
          f"{annualize(ov_all + iv_all):>11.1f}%")
    print(f"  일평균: 오버나이트 {ov_all:+.4f}%, 장중 {iv_all:+.4f}%")
    print(f"  독립 표본 {len(uni_year)}개 (달력 연도. 표본.md)")

    # 검산 - 사전 등록에 "합계가 -7.0% 와 맞아야 한다" 고 썼다.
    # 안 맞으면 안 맞는다고 적는다. 산술평균을 연환산한 값과 실제로
    # 복리로 굴린 값은 다르다 (분산 손실). 둘을 다 낸다.
    geo = compound_universe(dates, panel, uni_at)
    print(f"  [검산] 산술평균 연환산 {annualize(ov_all + iv_all):+.1f}% "
          f"vs 실제 복리 {geo:+.1f}% (차이 = 분산 손실)")

    # ---------------------------------------------------------- 측정 2
    print(f"\n=== 측정 2. 저변동 {PICK_N}종목 (교체 {PERIOD}일), 해마다 ===")
    rounds = build_rounds(dates, panel)
    hold = {}
    for buy_di, sell_di, codes in rounds:
        for di in range(buy_di, sell_di):
            hold[di] = codes
    lv_year = decompose(dates, panel, lambda di: hold.get(di, []))
    print(f"  {'해':<6}{'오버나이트':>12}{'장중':>12}{'합계':>12}"
          f"{'거래일':>8}")
    for y, (ov, iv, n) in lv_year.items():
        print(f"  {y:<6}{annualize(ov):>11.1f}%{annualize(iv):>11.1f}%"
              f"{annualize(ov + iv):>11.1f}%{n:>8}")
    lov = st.mean([v[0] for v in lv_year.values()])
    liv = st.mean([v[1] for v in lv_year.values()])
    print(f"  {'평균':<6}{annualize(lov):>11.1f}%{annualize(liv):>11.1f}%"
          f"{annualize(lov + liv):>11.1f}%")
    print(f"  일평균: 오버나이트 {lov:+.4f}%, 장중 {liv:+.4f}%")

    # ---------------------------------------------------------- 측정 3
    print("\n=== 측정 3. '매일 종가 사서 다음 시가 판다' 가 되나 ===")
    print(f"  왕복 수수료           {FEE_ROUND_TRIP:.3f}% / 일")
    for name, daily in (("유니버스 200", ov_all), (f"저변동 {PICK_N}", lov)):
        net = daily - FEE_ROUND_TRIP
        print(f"  {name:<14} 오버나이트 {daily:+.4f}% -> 수수료 후 "
              f"{net:+.4f}% / 일  ({annualize(net):+,.0f}%/년)")
    print(f"  수수료를 넘으려면 오버나이트가 일 {FEE_ROUND_TRIP:.3f}% 는"
          f" 돼야 한다 (= 연 {annualize(FEE_ROUND_TRIP):,.0f}%).")

    # ---------------------------------------------------------- 측정 4
    print(f"\n=== 측정 4. 체결 시점만 바꾼다 (교체 {len(rounds)}회, "
          f"종목 선정은 같다) ===")
    res = {}
    for label, buy_at, sell_at in FILLS:
        years, curve = run_fill(dates, panel, rounds, buy_at, sell_at)
        res[label] = (years, curve, cagr(curve, n_days))
    print(f"  {'방식':<22}{'연수익':>9}" +
          "".join(f"{y:>9}" for y in sorted(res[FILLS[0][0]][0])))
    for label, _b, _s in FILLS:
        years, _c, an = res[label]
        row = "".join(f"{years.get(y, float('nan')):>8.1f}%"
                      for y in sorted(years))
        print(f"  {label:<22}{an:>8.1f}%{row}")

    base_label = FILLS[0][0]
    base_years, _bc, base_an = res[base_label]
    print(f"\n  기준은 {base_label} (지금 쓰는 방식, 연 {base_an:.1f}%)")
    print(f"  {'방식':<22}{'격차':>9}{'이긴 해':>9}{'전반':>9}{'후반':>9}"
          f"{'최고해 빼고':>13}{'대조 p':>9}")
    for label, buy_at, sell_at in FILLS[1:]:
        years, curve, an = res[label]
        diffs = {y: years[y] - base_years[y]
                 for y in years if y in base_years}
        wins = sum(1 for d in diffs.values() if d > 0)
        ys = sorted(diffs)
        half = len(ys) // 2
        first = st.mean([diffs[y] for y in ys[:half]]) if half else 0.0
        second = st.mean([diffs[y] for y in ys[half:]])
        best = max(diffs, key=lambda y: diffs[y])
        drop = st.mean([diffs[y] for y in diffs if y != best])
        p = control_p(dates, panel, buy_at, sell_at, base_an,
                      an, args.perms)
        print(f"  {label:<22}{an - base_an:>8.2f}%p{wins:>7}/{len(diffs)}"
              f"{first:>8.2f}%p{second:>8.2f}%p{drop:>12.2f}%p{p:>9.3f}")
        verdict(label, an - base_an, wins, len(diffs), first, second,
                drop, p)

    # ------------------------------------------------- 측정 5 (사후)
    print("\n=== 측정 5 (사후 검사. 이걸로 아무것도 채택하지 않는다) ===")
    print("  측정 1 의 격차가 진짜 드리프트인가, 호가 튀기인가.")
    print("  미시구조라면 변동성이 클수록 격차가 커야 한다.")
    vs = vol_split(dates, panel)
    print(f"  {'변동성 구간':<14}{'오버나이트':>12}{'장중':>12}"
          f"{'격차(일)':>12}{'종목-일':>12}")
    names = ["1 저변동", "2", "3", "4", "5 고변동"]
    for nm, (ov, iv, n) in zip(names, vs):
        if ov is None:
            continue
        print(f"  {nm:<14}{annualize(ov):>11.1f}%{annualize(iv):>11.1f}%"
              f"{ov - iv:>11.4f}%{n:>12,}")
    gaps = [ov - iv for ov, iv, _n in vs if ov is not None]
    if len(gaps) >= 2:
        print(f"  고변동/저변동 격차 비율: {gaps[-1] / gaps[0]:.1f}배"
              if gaps[0] else "")
    return 0


def control_p(dates, panel, buy_at, sell_at, base_an, real_an, perms):
    """무작위 대조. 교체일을 무작위로 옮겨도 같은 격차가 나오나.

    시점의 정보가 아니라 그냥 드리프트라면, 아무 날에 갈아타도 같은
    격차가 나와야 한다. 나오면 p 가 커지고 조건 3 에서 탈락한다.
    """
    if perms <= 0:
        return float("nan")
    lo = S.LIQUIDITY_DAYS + VOL_DAYS + 1
    hi = len(dates) - PERIOD - 1
    if hi <= lo:
        return float("nan")
    hits, done = 0, 0
    for _ in range(perms):
        start = random.randint(lo, lo + PERIOD - 1)
        rs = build_rounds(dates, panel, PERIOD, start)
        if not rs:
            continue
        _yb, cb = run_fill(dates, panel, rs, "open", "open")
        _yn, cn = run_fill(dates, panel, rs, buy_at, sell_at)
        ab, an = cagr(cb, len(dates)), cagr(cn, len(dates))
        if ab is None or an is None:
            continue
        done += 1
        if (an - ab) >= (real_an - base_an):
            hits += 1
    return (hits + 1) / (done + 1) if done else float("nan")


def verdict(label, edge, wins, n, first, second, drop, p):
    """조건 넷 + 절대선. 결과를 보고 조건을 고치지 않는다."""
    c1 = wins >= MIN_YEARS_WIN
    c2 = (first > 0) == (second > 0) and first != 0 and second != 0
    c3 = p < P_CUTOFF
    c4 = drop > 0
    c0 = abs(edge) >= MIN_EDGE_PP
    marks = (f"조건1 {'O' if c1 else 'X'} 조건2 {'O' if c2 else 'X'} "
             f"조건3 {'O' if c3 else 'X'} 조건4 {'O' if c4 else 'X'} "
             f"절대선 {'O' if c0 else 'X'}")
    ok = c0 and c1 and c2 and c3 and c4
    print(f"      -> {marks} => {'채택' if ok else '탈락'}")
    return ok


if __name__ == "__main__":
    sys.exit(main())
