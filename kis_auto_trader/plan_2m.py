"""200만원 운영 계획 - 월 3만원 목표. 리밸런스 날과 주문 수량을 내준다.

(2026-09-18 신설) 사용자: "최소한의 투자로 이윤을 보고 손해는 최대한 피하는
방향. 거래 횟수는 알아서. 목표는 월 3만원 정도, 클로드 구독값 정도만 벌어도
됨. 투자 금액은 200만원까지."

===========================================================================
먼저 목표가 무엇을 요구하는지
===========================================================================
  월 30,000원 x 12 = 연 360,000원
  200만원 기준 = **연 18.0%**

이건 작은 목표가 아니다. 이 전략의 과거 5.5년 연환산 중앙값이
15.1~16.8% 였으므로, 목표가 실적보다 **약간 높다**. 그리고 그 5.5년에는
2025년 시장 +55% 가 들어 있다.

===========================================================================
백테스트가 무시했던 것 - 200만원의 실제 제약
===========================================================================
지금까지의 백테스트는 '10종목 동일가중' 을 소수점으로 계산했다. 실제로는
1주 단위로만 살 수 있고, 200만원/10종목 = 한 종목에 20만원이다.

  20260723 회차의 10종목 주가
    088980     10,030원 -> 19주      138930    17,630원 -> 11주
    024110     20,650원 ->  9주      030200    52,200원 ->  3주
    138040    114,100원 ->  1주      011200    20,300원 ->  9주
    316140     30,400원 ->  6주      005830   164,600원 ->  1주
    033780    175,200원 ->  1주      207940 1,399,000원 -> **0주**

  삼성바이오로직스(207940)는 한 주가 139만원이라 20만원으로 못 산다.
  그냥 슬롯대로 사면 **평균 26.3% 가 투자도 안 되고 놀았다**
  (회차 76% 에서 최소 한 종목을 못 샀다). 수익이 74% 로 깎인다.

  그래서 이 파일은 못 사는 종목을 건너뛰고 그 돈을 나머지에 돌린다
  (아래 allocate). 그러면 놀는 돈이 거의 없어진다.

===========================================================================
구성을 고른 근거 - '손해를 최대한 피하는' 기준
===========================================================================
1주 단위 배분으로 실제 돌린 결과 (시작일 12개 중앙값, 200만원)

  종목수 주기        연 거래  연수익(중앙)   월평균   최대낙폭  목표달성
   3   분기 1회      4.0   346,459원  28,872원  -19.7%   33%
   5   분기 1회      4.2   309,887원  25,824원  -19.6%   17%
   8   분기 1회      4.2   343,463원  28,622원  -17.3%   33%
  10   분기 1회      4.2   347,877원  28,990원  -16.6%   42%
  10   반년 1회      2.2   349,518원  29,127원  -18.3%   42%
  10   연  1회       1.1   330,464원  27,539원  -19.0%   42%

종목을 줄이면 나아질 것 같지만 아니다. 10종목이 낙폭도 제일 작고 수익도
제일 낫다. 20만원씩 쪼개도 살 수 있는 종목이 대부분이고, 10개로 나누는
것이 한 종목 사고에 덜 다치기 때문이다.

그리고 결정적인 것은 '최악의 1년' 이다 (1년 창 1,012개 전부)

  종목수 주기      손실확률   최악 1년      중앙값     목표 이상
  10   분기 1회     21%   -447,087원  509,380원   60%
  10   반년 1회     17%   -252,177원  339,813원   49%   <- 고름
  10   연  1회      20%   -301,631원  465,738원   59%
   5   분기 1회     25%   -336,972원  477,804원   61%

**반년 1회의 최악이 -252,177원, 분기 1회는 -447,087원이다.** 수익은
거의 같은데 최악이 절반이다. 손실 확률도 17% 로 가장 낮다. 사용자가
'손해는 최대한 피하는 방향' 이라고 했으므로 반년 1회를 고른다.

  => **10종목 / 120거래일(약 반년)마다 교체 / 연 2.2회 거래**

===========================================================================
그래서 얼마 벌 것 같은가 - 정직하게
===========================================================================
  연 349,518원 = **월 29,127원**  (중앙값)
  목표 월 30,000원에 **약간 못 미친다**

  1년 창 1,012개 중
    손실 17%        최악 -252,177원 (목표 8.4개월치를 잃는다)
    목표(36만원) 이상 49%
    중앙값 +339,813원

연도별로 보면 (10종목/분기 1회 기준. 반년 1회도 모양은 같다)
  2021  -425,818원  (월 -35,485원)  그해 낙폭 -25.1%
  2022   -60,967원  (월  -5,081원)  그해 낙폭  -9.9%
  2023  +189,230원  (월 +15,769원)
  2024  +445,649원  (월 +37,137원)
  2025  +971,197원  (월 +80,933원)   <- 시장이 +55% 였다
  2026  +611,097원  (월 +50,925원)

  **2021~2022 는 2년 연속 목표 미달이었고 2021년은 42만원을 잃었다.**
  구독료를 벌려고 시작했는데 첫 2년은 구독료를 못 벌고 원금이 줄어드는
  기간이 실제로 있었다.

  결론: '월 3만원 꾸준히' 는 안 된다. '여러 해 평균으로 월 3만원 근처,
  나쁜 해에는 20~40만원 손실' 이 맞는 기대다.

===========================================================================
'하루 5,000원 벌기' 는 되나 - 안 된다. 더 큰 목표다
===========================================================================
(2026-09-18 추가) 사용자: "하루에 5000원만 벌기 프로젝트 이런건 안되나?"

'5,000원' 이 작게 들리지만 200만원 기준으로는
  5,000원 x 246거래일 = 연 1,230,000원 = **연 61.5%**
월 3만원 목표(연 18%)의 **3.4배** 다. 더 작은 목표가 아니라 훨씬 큰
목표다. 달력일로 치면 연 91.2% 다.

그리고 '매일' 조금씩은 구조적으로 안 된다. 200만원으로 이 구성을 5.1년
돌렸을 때 일별 손익 (1,257일)

  오른 날 670일 (53.3%) / 내린 날 587일 (46.7%)
  하루 평균    +1,530원
  하루 표준편차 35,158원   <- 목표 5,000원의 7배
  제일 좋은 날 +271,112원
  제일 나쁜 날 -429,500원  <- 하루에 목표 86일치를 잃는다

  구간              일수    비율
  -5만원 이하         48   3.8%
  -5만 ~ -2만원      146  11.6%
  -2만 ~ -5천원      256  20.4%
  -5천 ~ 0원        136  10.8%
  0 ~ +5천원        154  12.3%
  +5천 ~ +2만원      289  23.0%
  +2만 ~ +5만원      166  13.2%
  +5만원 이상         62   4.9%

  하루 5,000원 이상 번 날 517일 = **41.1%**. 59% 의 날은 못 번다.
  5,000원을 연속으로 못 번 최장 기간 11거래일.

  흔들림(35,158원)이 목표(5,000원)의 7배다. 하루 단위로 5,000원을
  '떼어내는' 것은 불가능하다. 매일 통장에 5,000원이 꽂히는 그림은
  주식으로 만들 수 없다 - 그건 이자나 월급의 모양이다.

그래서 하루 목표는 '평균' 으로만 말이 된다. 200만원의 실제 하루 평균은
  단일 경로 1,137원 / 시작일 12개 중앙값 1,421원
즉 목표 5,000원의 23~28% 수준이다.

하루 평균 5,000원을 벌려면 자금이 얼마나 필요한가 (연 14.0~17.5% 가정)
  하루  1,000원 ->  141만 ~ 176만원
  하루  1,500원 ->  211만 ~ 264만원
  하루  2,000원 ->  282만 ~ 352만원
  하루  3,000원 ->  422만 ~ 528만원
  하루  5,000원 ->  704만 ~ 879만원
  하루 10,000원 -> 1,408만 ~ 1,759만원

  **200만원으로 낼 수 있는 하루 평균은 1,100~1,400원이다.**
  5,000원을 원하면 돈을 700~880만원으로 늘리는 것 말고 방법이 없다.
  수익률을 3.4배로 올리는 방법은 이 세션에서 찾지 못했다.

  아래 required_capital() 로 아무 목표나 넣어 확인할 수 있다.
    python plan_2m.py --daily 5000
    python plan_2m.py --month 30000

===========================================================================
'매달 3만원' 을 요구 조건으로 받으면 - 모델을 이렇게 짜야 한다
===========================================================================
(2026-09-19) 사용자: "한달에 3만원씩 이윤을 보고 싶은데 그러려면 어떻게
모델을 짜야하는지 알려줘. 내 요구 조건은 한달에 3만원 이득을 보는 거야."
(정정) "아니 1년에 36만원이 아니라 한달에 3만원"

연 36만원과 월 3만원은 전혀 다른 조건이다.
  연 36만원 - 좋은 달이 나쁜 달을 메워도 된다
  월 3만원  - 달마다 각각 +3만원 이상이어야 한다

--- 먼저: '매달 버는 것' 은 자금으로 못 푼다 ---
1개월(21거래일) 창 1,237개에서

  마이너스이거나 0인 달  508개 = **41.1%**
  플러스인 달           729개 = 58.9%

  월 수익률: 평균 +1.36% / 표준편차 5.73%
    하위10% -4.27%  하위30% -1.19%  중앙 +0.93%  하위70% +3.16%

자금별로 '그 달에 3만원 이상 번' 비율
  자금            달성률    중앙 월수익     최악의 달
  200만원         45.8%    18,698원    -357,544원
  500만원         53.1%    46,745원    -893,861원
  1,000만원       56.0%    93,490원  -1,787,722원
  5,000만원       58.4%   467,448원  -8,938,610원
  1억원           58.7%   934,896원 -17,877,221원

  **달성률의 천장이 58.9% 다.** 마이너스인 달은 자금을 아무리 늘려도
  +3만원이 안 된다 - 수익률이 음수면 금액도 음수이기 때문이다.
  1억을 넣어도 열 달 중 네 달은 못 번다. 겹치지 않는 달로 세면
  200만원에서 59개월 중 27개월(46%) 달성, 연속 미달 최장 5개월이었다.

  그러므로 '매달 +3만원을 버는 모델' 은 짤 수 없다. 이건 전략 문제가
  아니라 주가가 매달 오르지는 않는다는 사실이다.

--- 그런데 '매달 3만원을 꺼내 쓰는 것' 은 된다 ---
버는 것과 꺼내 쓰는 것은 다르다. 좋은 달에 쌓인 것을 나쁜 달에 꺼내면
통장에는 **매달 3만원이 들어온다.** 조건은 하나다.

  **인출률(연) < 기대 수익률(연)**

매달 3만원 = 연 36만원이므로
  200만원에서는 인출률 18.0%  -> 기대 14.0~17.5% 보다 높다 -> 원금이 마른다
  500만원에서는 인출률  7.2%  -> 넉넉히 낮다 -> 버틴다

실제로 5.1년(59개월) 돌려봤다. 매달 첫 거래일에 3만원 인출, 현금이
모자라면 비싼 종목부터 일부 매도해서 채운다.

  자금        인출 총액      남은 돈(중앙)        최소~최대         원금 유지
  200만원   1,665,000원     979,329원    409,392~1,469,599      0%
  300만원   1,665,000원   3,025,133원  2,213,015~3,696,506     50%
  400만원   1,665,000원   5,184,158원  3,983,250~6,165,700     88%
  500만원   1,665,000원   7,189,366원  5,664,970~8,629,000    100%
  700만원   1,665,000원  10,910,081원  9,419,009~14,172,686   100%

  200만원으로 매달 3만원을 꺼내면 5.1년간 166만원을 받지만 원금이
  200만원 -> 98만원으로 줄어든다 (8개 경로 전부 원금 손실, 최악 41만원).
  **원금을 까먹으면서 받는 것이지 이윤으로 받는 게 아니다.**

  400만원이면 88%, **500만원이면 8개 경로 전부 원금이 유지된다.**
  500만원이면 5.1년간 166만원을 꺼내고도 718만원이 남았다.

--- 그래서 답 ---
  요구 조건 '매달 3만원' 을 만족하는 모델은
    전략   지금 것 그대로 (저변동 10종목 / 120거래일마다 교체)
    자금   **500만원** (400만원이면 아슬아슬, 200만원이면 원금 잠식)
    인출   매달 첫 거래일에 3만원. 현금 부족하면 일부 매도해서 채움
    금지   매달 벌기를 기대하는 것. 41% 의 달은 마이너스다

  200만원만 쓰겠다면 인출액을 줄여야 한다. 안전 인출률을 연 7.2% 로
  잡으면 200만원에서는 **월 12,000원**이다.
  (아래 safe_withdrawal / capital_for_withdrawal 로 계산할 수 있다)

===========================================================================
왜 타이밍(좋은날/나쁜날)을 안 쓰는가
===========================================================================
이 세션에서 23가지 타이밍 가설을 검사했고 전부 실패했다. 마지막 두 개만
적어두면
  - 지표 14개가 전부 한 방향인 날의 승률 50.0% vs 전부 반대인 날 54.5%,
    차이 z=+0.20 (analyze_consensus.py)
  - '제일 중요한 지표 하나' 의 최고 |t|=1.48 인데 어긋난 데이터의
    중앙값이 1.78 이다 (analyze_cascade.py)
그래서 날짜만 정해놓고 판단 없이 돌린다. 이게 '사용자가 신경 안 쓰기' 에
도 더 맞는다.

===========================================================================
운영 규칙 (판단이 안 들어간다)
===========================================================================
  1) 기준일 ANCHOR 부터 120거래일마다 교체일이다
  2) 교체일에 저변동 10종목을 다시 뽑는다
  3) 기존 보유를 전량 매도하고, 아래 allocate 로 주문 수량을 정한다
  4) 손절/익절 없다. 중간에 아무것도 하지 않는다
  5) 교체일이 아니면 할 일이 없다

실행:
    python plan_2m.py              # 오늘 할 일
    python plan_2m.py --capital 2000000
    python plan_2m.py --force      # 교체일이 아니어도 주문표를 보여준다

주문은 내지 않는다. CSV 만 읽고 주문표를 화면에 찍는다.
"""
import argparse
import pathlib
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import strategy as S  # noqa: E402

CAPITAL = 2_000_000
N_PICK = 10
REBAL_DAYS = 120          # 약 반년. 최악의 1년을 절반으로 줄인다
# alert.py 와 같은 기준일을 쓴다. 이걸 바꾸면 교체 주기가 어긋난다.
ANCHOR = "20260915"

TARGET_MONTH = 30_000
TARGET_YEAR = TARGET_MONTH * 12

DAYS_PER_YEAR = 246          # 거래일
# 과거 5.5년 실적의 범위. 낮은 쪽은 단일 경로, 높은 쪽은 시작일 12개 중앙값.
# 하나만 쓰면 낙관/비관 한쪽으로 기울므로 둘 다 들고 범위로 답한다.
ANN_LOW, ANN_HIGH = 0.1399, 0.1748
# 하루 손익의 실제 흔들림 (200만원 기준). 하루 목표를 판정할 때 쓴다.
DAILY_SD_AT_2M = 35_158

# 매수 수수료. 실제 매수 수수료는 0.015% 수준이고 매도 쪽에 세금이 붙는데,
# 여기서는 왕복의 절반을 매수에 물려 주식수를 보수적으로(조금 적게) 잡는다.
BUY_COST_PCT = S.FEE_ROUND_TRIP_PCT / 2


# 안전 인출률(연). 5.1년 시뮬에서 8개 경로 전부 원금이 유지된 수준이다
# (500만원에서 연 36만원 = 7.2%). 9.0%(400만원)는 88% 만 유지됐다.
SAFE_WITHDRAW_RATE = 0.072
# 월간 마이너스 비율. '매달 벌기' 의 천장을 정하는 값이다.
NEG_MONTH_PCT = 41.1


def safe_withdrawal(capital: float) -> float:
    """이 자금에서 매달 안전하게 꺼내 쓸 수 있는 금액.

    안전 인출률은 '5.1년 동안 원금이 안 줄어든' 수준에서 잡았다.
    수익을 다 꺼내면 나쁜 해에 원금이 깎이므로 수익률보다 낮게 잡는다.
    """
    return capital * SAFE_WITHDRAW_RATE / 12


def capital_for_withdrawal(monthly: float) -> float:
    """매달 이만큼 꺼내 쓰려면 자금이 얼마나 필요한가."""
    if monthly <= 0:
        return 0.0
    return monthly * 12 / SAFE_WITHDRAW_RATE


def withdrawal_report(capital: float, monthly: float) -> str:
    """'매달 X원' 요구 조건에 대한 답. 버는 것과 꺼내 쓰는 것을 구별한다."""
    need = capital_for_withdrawal(monthly)
    can = safe_withdrawal(capital)
    rate = monthly * 12 / capital * 100 if capital > 0 else 0.0
    out = []
    out.append(f"요구 조건: 매달 {monthly:,.0f}원")
    out.append("")
    out.append("[1] '매달 그만큼 버는' 모델은 짤 수 없다")
    out.append(f"    과거 1개월 창의 {NEG_MONTH_PCT:.1f}% 가 마이너스였다.")
    out.append("    마이너스인 달은 자금을 늘려도 +가 안 된다 (수익률이")
    out.append("    음수면 금액도 음수다). 1억을 넣어도 달성률 천장이")
    out.append(f"    {100-NEG_MONTH_PCT:.1f}% 다.")
    out.append("")
    out.append("[2] '매달 그만큼 꺼내 쓰는' 모델은 된다")
    out.append(f"    연 인출률 = {monthly*12:,.0f}원 / {capital:,.0f}원 "
               f"= {rate:.1f}%")
    out.append(f"    안전 인출률은 연 {SAFE_WITHDRAW_RATE*100:.1f}% 다 "
               f"(5.1년 시뮬에서 원금이 유지된 수준).")
    if rate > SAFE_WITHDRAW_RATE * 100:
        out.append(f"    -> {rate:.1f}% 는 너무 높다. 원금을 까먹으면서 "
                   f"받게 된다.")
        out.append(f"       필요 자금 {need:,.0f}원 (지금 {capital:,.0f}원)")
        out.append(f"       또는 지금 자금으로는 월 {can:,.0f}원까지가 "
                   f"안전하다.")
    else:
        out.append(f"    -> {rate:.1f}% 는 안전 범위 안이다. "
                   f"{capital:,.0f}원이면 월 {can:,.0f}원까지 가능하다.")
    out.append("")
    out.append("    인출 방법: 매달 첫 거래일에 그만큼 뺀다. 현금이")
    out.append("    모자라면 비싼 종목부터 일부 매도해 채운다. 좋은 달에")
    out.append("    쌓인 것을 나쁜 달에 꺼내는 구조라 통장에는 매달")
    out.append("    같은 금액이 들어온다.")
    return "\n".join(out)


def required_capital(annual_target: float) -> tuple:
    """연 목표 금액을 벌려면 자금이 얼마나 필요한가. (낮은쪽, 높은쪽)

    과거 실적 범위 두 개로 계산해 범위로 돌려준다. 하나만 쓰면 낙관 또는
    비관 한쪽으로 기운다. 어느 쪽도 보장이 아니다 - 1년 창의 17% 는
    손실이었다.
    """
    if annual_target <= 0:
        return 0.0, 0.0
    return annual_target / ANN_HIGH, annual_target / ANN_LOW


def target_report(capital: float, daily: float = None,
                  month: float = None) -> str:
    """목표를 넣으면 그게 무엇을 요구하는지 계산해서 알려준다."""
    if daily:
        year = daily * DAYS_PER_YEAR
        label = f"하루 {daily:,.0f}원"
        per_day = daily
    elif month:
        year = month * 12
        label = f"월 {month:,.0f}원"
        per_day = year / DAYS_PER_YEAR
    else:
        return ""

    lo, hi = required_capital(year)
    out = []
    out.append(f"목표 {label} = 연 {year:,.0f}원 "
               f"(거래일 {DAYS_PER_YEAR}일 기준)")
    out.append(f"  투자금 {capital:,.0f}원 기준 = 연 {year/capital*100:.1f}%")
    out.append("")
    out.append(f"  과거 실적은 연 {ANN_LOW*100:.1f}~{ANN_HIGH*100:.1f}% 였다.")
    out.append(f"  그 수익률로 이 목표를 내려면 자금이 "
               f"{lo:,.0f} ~ {hi:,.0f}원 필요하다.")
    if capital < lo:
        out.append(f"  -> 지금 {capital:,.0f}원으로는 부족하다. "
                   f"최소 {lo:,.0f}원은 있어야 한다.")
        out.append(f"     {capital:,.0f}원으로 기대할 하루 평균은 "
                   f"{capital*ANN_LOW/DAYS_PER_YEAR:,.0f}~"
                   f"{capital*ANN_HIGH/DAYS_PER_YEAR:,.0f}원이다.")
    else:
        out.append(f"  -> {capital:,.0f}원이면 과거 실적 범위 안에 든다.")

    # 하루 단위 목표는 흔들림과 같이 봐야 한다
    if daily:
        sd = DAILY_SD_AT_2M * capital / 2_000_000
        out.append("")
        out.append(f"  다만 하루 손익의 흔들림이 약 {sd:,.0f}원이다 "
                   f"(목표의 {sd/per_day:.0f}배).")
        out.append("  흔들림이 목표보다 크면 '매일 그만큼' 을 떼어낼 수 없다.")
        out.append("  실제로 200만원에서 하루 5,000원 이상 번 날은 41.1%")
        out.append("  뿐이었고, 연속으로 못 번 기간이 최장 11거래일이었다.")
        out.append("  그래서 하루 목표는 '평균' 으로만 말이 된다.")
    return "\n".join(out)


# 지금 무엇을 들고 있는지 기록해두는 파일. 부분교체를 하려면 필요하다.
# (2026-09-19 추가) analyze_turnover.py 에서 부분교체가 전량교체를 6/6
# 주기에서 이기는 것이 확인됐다 (반기 양방향 모두 승). 겹치는 종목을
# 안 팔면 수수료가 3~5배 줄기 때문이다. 그러려면 프로그램이 현재 보유를
# 알아야 하므로 교체할 때마다 여기 적는다.
HOLDINGS_PATH = _ROOT / "data" / "plan_holdings.csv"
HOLDINGS_FIELDS = ("date", "code", "qty")


def load_holdings() -> tuple:
    """마지막으로 기록한 보유. ({종목: 수량}, 기록날짜) 없으면 ({}, None)."""
    if not HOLDINGS_PATH.exists():
        return {}, None
    import csv
    rows = []
    with open(HOLDINGS_PATH, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                rows.append((r["date"], r["code"], int(r["qty"])))
            except (TypeError, ValueError, KeyError):
                continue
    if not rows:
        return {}, None
    last = max(d for d, _c, _q in rows)
    return {c: q for d, c, q in rows if d == last and q > 0}, last


def save_holdings(date: str, hold: dict) -> None:
    """교체 후 보유를 덧붙여 기록한다. 과거 기록은 지우지 않는다."""
    import csv
    HOLDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    new = not HOLDINGS_PATH.exists()
    with open(HOLDINGS_PATH, "a", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(HOLDINGS_FIELDS)
        for c, q in sorted(hold.items()):
            w.writerow([date, c, int(q)])


def plan_changes(current: dict, picks: list) -> tuple:
    """부분교체 계획. (팔 것, 살 것, 그대로 둘 것)

    겹치는 종목은 건드리지 않는다 - 이게 수수료를 3~5배 줄이는 부분이다.
    """
    sell = {c: q for c, q in current.items() if c not in picks}
    keep = {c: q for c, q in current.items() if c in picks}
    buy = [c for c in picks if c not in current]
    return sell, buy, keep


def rebalance_due(dates: list, today: str) -> tuple:
    """오늘이 교체일인가, 아니면 며칠 남았나.

    ANCHOR 로부터 거래일 수를 세므로 휴장일에 밀리지 않는다.
    """
    if today not in dates or ANCHOR not in dates:
        return False, None
    gap = dates.index(today) - dates.index(ANCHOR)
    if gap % REBAL_DAYS == 0:
        return True, 0
    return False, (-gap) % REBAL_DAYS


def current_picks(dates: list, panel: dict, di: int = None) -> list:
    """그 시점의 저변동 10종목. di 를 안 주면 마지막 날 기준."""
    if di is None:
        di = len(dates) - 1
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    sc = [(x, c) for c in cand
          if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
    if len(sc) < N_PICK:
        return []
    sc.sort(reverse=True)
    return [c for _s, c in sc[:N_PICK]]


def allocate(capital: float, prices: dict) -> tuple:
    """1주 단위 주문 수량. 못 사는 종목은 건너뛰고 남은 돈을 싼 것에 돌린다.

    이 재배분이 핵심이다. 슬롯대로만 사면 200만원 중 평균 26.3% 가
    투자되지 않고 놀았다 (한 주가 슬롯보다 비싼 종목이 있어서).

    반환: ({종목: 주식수}, 남는 현금)
    """
    prices = {c: p for c, p in prices.items() if p and p > 0}
    if not prices:
        return {}, capital
    slot = capital / len(prices)
    hold, spent = {}, 0.0
    for c, p in prices.items():
        cost = p * (1 + BUY_COST_PCT / 100)
        q = int(slot // cost)
        if q > 0:
            hold[c] = q
            spent += q * cost
    left = capital - spent
    # 싼 종목부터 1주씩 더. 더 못 살 때까지.
    order = sorted(prices.items(), key=lambda kv: kv[1])
    added = True
    while added:
        added = False
        for c, p in order:
            cost = p * (1 + BUY_COST_PCT / 100)
            if left >= cost:
                hold[c] = hold.get(c, 0) + 1
                left -= cost
                added = True
    return hold, left


def last_price(panel: dict, code: str, di: int) -> float:
    s = panel.get(code)
    if s is None:
        return 0.0
    j = s.pos.get(di)
    if j is None:
        return 0.0
    return float(s.close[j] or 0.0)


def _names() -> dict:
    """종목코드 -> 종목명. 패널 파일의 마지막 연도만 읽으면 충분하다.

    (alert.py 의 _load_names 와 같은 방식. 패널에 name 컬럼이 있다.)
    """
    import csv
    import glob
    out = {}
    paths = sorted(glob.glob(str(_ROOT / "data" / f"{S.PANEL_PREFIX}_*.csv")))
    for path in paths[-1:]:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("code") and r.get("name"):
                    out[r["code"]] = r["name"]
    return out


def order_sheet(capital: float, force: bool) -> str:
    dates, panel = S.load_panel()
    today = dates[-1]
    due, remain = rebalance_due(dates, today)
    names = _names()
    lines = []
    lines.append(f"기준 데이터 마지막 날: {today}")
    lines.append(f"투자금 {capital:,.0f}원 / 목표 월 {TARGET_MONTH:,}원 "
                 f"(연 {TARGET_YEAR:,}원 = {TARGET_YEAR/capital*100:.1f}%)")
    lines.append(f"교체 주기 {REBAL_DAYS}거래일 (약 반년, 연 2회쯤) / "
                 f"종목 {N_PICK}개 / 기준일 {ANCHOR}")
    lines.append("")

    if due:
        lines.append(">>> 오늘은 교체일이다. 아래대로 갈아탄다.")
    elif force:
        lines.append(f">>> 교체일이 아니다 (다음 교체일까지 {remain}거래일). "
                     f"--force 라서 주문표만 보여준다.")
    else:
        if remain is None:
            lines.append("!! 기준일이나 오늘 날짜가 데이터에 없다. "
                         "collect_daily.py 를 먼저 돌려라.")
        else:
            lines.append(f"오늘은 할 일이 없다. 다음 교체일까지 "
                         f"{remain}거래일 남았다.")
            lines.append("(주문표를 미리 보려면 --force)")
        return "\n".join(lines)

    picks = current_picks(dates, panel)
    if not picks:
        lines.append("!! 종목을 뽑을 수 없다 (데이터 부족).")
        return "\n".join(lines)

    di = len(dates) - 1
    prices = {c: last_price(panel, c, di) for c in picks}
    current, rec_date = load_holdings()

    if not current:
        # 첫 매수. 전액으로 10종목을 산다.
        hold, left = allocate(capital, prices)
        lines.append("")
        lines.append("  [첫 매수] 기록된 보유가 없다. 전액으로 산다.")
        lines.append(f"  {'종목':<8} {'이름':<14} {'주가':>11} {'수량':>6} "
                     f"{'금액':>12} {'비중':>7}")
        total = 0.0
        for c in picks:
            pr = prices.get(c, 0.0)
            q = hold.get(c, 0)
            amt = q * pr
            total += amt
            mark = "" if q else "   <- 한 주가 비싸서 건너뜀"
            lines.append(f"  {c:<8} {names.get(c, '?'):<14} {pr:>10,.0f}원 "
                         f"{q:>5}주 {amt:>11,.0f}원 "
                         f"{(amt/capital*100):>6.1f}%{mark}")
        lines.append("")
        lines.append(f"  매수 합계 {total:,.0f}원 "
                     f"({total/capital*100:.1f}%) / "
                     f"남는 현금 {left:,.0f}원")
        skipped = [c for c in picks if not hold.get(c)]
        if skipped:
            lines.append(f"  건너뛴 종목 {len(skipped)}개: "
                         f"{', '.join(skipped)} (한 주가 슬롯보다 비싸다)")
    else:
        # 부분교체. 겹치는 종목은 건드리지 않는다 - 수수료가 3~5배 줄어든다.
        sell, buy, keep = plan_changes(current, picks)
        lines.append(f"  (마지막 기록 {rec_date} 기준 보유 "
                     f"{len(current)}종목)")
        lines.append("")
        lines.append(f"  [그대로 둘 것] {len(keep)}종목 - 팔지 마라. "
                     f"여기서 수수료가 절약된다.")
        for c in sorted(keep):
            lines.append(f"    {c:<8} {names.get(c, '?'):<14} "
                         f"{keep[c]:>5}주 유지")
        lines.append("")
        if sell:
            lines.append(f"  [팔 것] {len(sell)}종목")
            for c in sorted(sell):
                pr = last_price(panel, c, di)
                lines.append(f"    {c:<8} {names.get(c, '?'):<14} "
                             f"{sell[c]:>5}주 전량 매도  "
                             f"(약 {sell[c]*pr:,.0f}원)")
        else:
            lines.append("  [팔 것] 없다. 10종목이 그대로다 - 오늘 할 일 없음.")
        lines.append("")
        if buy:
            # 매도 대금 + 남은 현금으로 새 종목을 산다
            proceeds = sum(sell[c] * last_price(panel, c, di) for c in sell)
            cash_for_buy = proceeds * (1 - BUY_COST_PCT / 100)
            bp = {c: prices[c] for c in buy if prices.get(c)}
            got, left2 = allocate(cash_for_buy, bp)
            lines.append(f"  [살 것] {len(buy)}종목 "
                         f"(매도 대금 약 {cash_for_buy:,.0f}원으로)")
            for c in sorted(buy):
                pr = prices.get(c, 0.0)
                q = got.get(c, 0)
                mark = "" if q else "   <- 한 주가 비싸서 건너뜀"
                lines.append(f"    {c:<8} {names.get(c, '?'):<14} "
                             f"{pr:>10,.0f}원 {q:>5}주 "
                             f"{q*pr:>11,.0f}원{mark}")
            lines.append(f"    남는 현금 약 {left2:,.0f}원")
        else:
            lines.append("  [살 것] 없다.")
        lines.append("")
        lines.append("  ** 겹치는 종목을 팔았다 다시 사지 마라. **")
        lines.append("  그게 전량교체이고, 과거 5.1년에서 연 1~9%p 손해였다")
        lines.append("  (analyze_turnover.py: 6/6 주기에서 부분교체가 이김).")

    lines.append("")
    lines.append("  손절/익절 없음. 다음 교체일까지 아무것도 하지 않는다.")
    lines.append("  (손절은 과거 5.1년에서 -1.2~-5.6%p 였다. 타이트할수록")
    lines.append("   더 나빴다 - analyze_stops.py 참고)")
    lines.append("")
    lines.append("  교체를 실행했으면 기록해라:")
    lines.append(f"    python plan_2m.py --record <종목:수량> ...")
    lines.append("")
    lines.append("  기대치 (과거 5.5년 기준, 보장 아님)")
    lines.append(f"    중앙값 연 349,518원 = 월 29,127원 "
                 f"(목표에 조금 못 미친다)")
    lines.append(f"    1년 창 17% 는 손실. 최악 -252,177원")
    lines.append(f"    2021년 -425,818원, 2022년 -60,967원 "
                 f"(2년 연속 목표 미달)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="200만원 운영 계획")
    ap.add_argument("--capital", type=float, default=CAPITAL,
                    help=f"투자금 (기본 {CAPITAL:,})")
    ap.add_argument("--force", action="store_true",
                    help="교체일이 아니어도 주문표를 보여준다")
    ap.add_argument("--daily", type=float, default=None,
                    help="하루 목표 금액. 필요 자금을 계산해준다")
    ap.add_argument("--month", type=float, default=None,
                    help="월 목표 금액. 필요 자금을 계산해준다")
    ap.add_argument("--withdraw", type=float, default=None,
                    help="매달 꺼내 쓸 금액. 이 자금으로 되는지 알려준다")
    ap.add_argument("--record", nargs="*", default=None,
                    metavar="종목:수량",
                    help="교체 실행 후 보유를 기록한다 (예: 033780:1 030200:4)")
    ap.add_argument("--holdings", action="store_true",
                    help="기록된 보유를 보여준다")
    a = ap.parse_args()
    if a.holdings:
        cur, when = load_holdings()
        if not cur:
            print("기록된 보유가 없다. 교체 후 --record 로 적어라.")
        else:
            nm = _names()
            print(f"마지막 기록: {when}  ({len(cur)}종목)")
            for c, q in sorted(cur.items()):
                print(f"  {c:<8} {nm.get(c, '?'):<14} {q:>5}주")
        return 0
    if a.record is not None:
        if not a.record:
            print("기록할 보유를 주어라. 예: --record 033780:1 030200:4")
            return 1
        hold = {}
        for item in a.record:
            try:
                code, qty = item.split(":")
                q = int(qty)
            except ValueError:
                print(f"형식이 틀렸다: {item!r} (종목:수량 이어야 한다)")
                return 1
            if q <= 0:
                print(f"수량이 0 이하다: {item!r}")
                return 1
            hold[code.strip()] = q
        dates, _panel = S.load_panel()
        save_holdings(dates[-1], hold)
        print(f"{dates[-1]} 기준 보유 {len(hold)}종목을 기록했다 "
              f"-> {HOLDINGS_PATH.name}")
        for c, q in sorted(hold.items()):
            print(f"  {c:<8} {q:>5}주")
        return 0
    if a.withdraw:
        print(withdrawal_report(a.capital, a.withdraw))
        return 0
    if a.daily or a.month:
        print(target_report(a.capital, a.daily, a.month))
        return 0
    print(order_sheet(a.capital, a.force))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
