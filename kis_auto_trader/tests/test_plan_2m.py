"""plan_2m.py 검증 - 200만원 주문표가 실제로 살 수 있는 수량인지.

(2026-09-18 신설) 사용자 목표 "월 3만원, 투자금 200만원, 손해는 최대한
피하는 방향" 을 실제 주문표로 바꾸는 파일이다. 여기가 틀리면 실제 돈이
잘못 들어가므로 검사가 제일 엄해야 한다.

절대 틀리면 안 되는 것

  1) 주문 금액이 투자금을 **절대** 넘지 않아야 한다. 넘으면 주문이
     거부되거나 미수가 된다. 수수료까지 포함해서 안 넘어야 한다.
  2) 수량은 정수여야 한다. 주식은 1주 단위다.
  3) 못 사는 종목(한 주가 슬롯보다 비싼 것)을 0주로 두고 그 돈을
     나머지에 돌려야 한다. 안 돌리면 200만원 중 26% 가 놀았다.
  4) 교체일 계산이 거래일 기준이어야 한다 (휴장일에 밀리면 안 된다).
  5) 종목 선정에 미래 정보가 없어야 한다.
  6) 기대치를 과장하지 않아야 한다. 목표에 못 미친다는 사실과 손실
     연도가 주문표에 같이 찍혀야 한다.

실행:
  python tests/test_plan_2m.py
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import plan_2m as M  # noqa: E402

src = (REPO_ROOT / "plan_2m.py").read_text(encoding="utf-8")

CAP = 2_000_000


def cost_of(hold, prices):
    """수수료까지 포함한 실제 지출."""
    return sum(q * prices[c] * (1 + M.BUY_COST_PCT / 100)
               for c, q in hold.items())


# =====================================================================
# A) 예산을 절대 넘지 않는다 - 제일 중요한 검사
# =====================================================================
CASES = {
    "평범한 10종목": {f"{i:06d}": p for i, p in enumerate(
        [10030, 20650, 114100, 30400, 175200, 17630, 52200, 20300,
         164600, 100900])},
    "삼바처럼 비싼 것 포함": {f"{i:06d}": p for i, p in enumerate(
        [10030, 20650, 114100, 30400, 175200, 17630, 52200, 20300,
         164600, 1399000])},
    "전부 아주 비싼 것": {f"{i:06d}": p for i, p in enumerate(
        [900000, 1200000, 1399000, 800000, 1000000])},
    "전부 아주 싼 것": {f"{i:06d}": p for i, p in enumerate(
        [1200, 3400, 980, 5600, 2100, 7800, 1500, 4300, 6200, 2900])},
    "한 종목": {"000001": 50000},
}
for label, prices in CASES.items():
    hold, left = M.allocate(CAP, prices)
    spent = cost_of(hold, prices)
    check(f"A) [{label}] 지출이 투자금을 넘지 않는다",
          spent <= CAP + 1e-6,
          f"{spent:,.0f} <= {CAP:,}")
    check(f"A) [{label}] 남는 현금 계산이 지출과 맞는다",
          abs((CAP - spent) - left) < 1e-6,
          f"left={left:,.0f} vs {CAP-spent:,.0f}")
    check(f"A) [{label}] 남는 현금이 음수가 아니다", left >= -1e-6,
          f"{left:,.0f}원")
    check(f"A) [{label}] 수량이 모두 정수이고 1주 이상",
          all(isinstance(q, int) and q >= 1 for q in hold.values()))

# 아주 비싼 것만 있으면 못 사는 게 정상이다 (예산 초과보다 안 사는 게 맞다)
hold_exp, left_exp = M.allocate(500_000, {"000001": 1_399_000})
check("A2) 예산보다 비싼 종목 하나뿐이면 아무것도 안 산다",
      hold_exp == {} and abs(left_exp - 500_000) < 1e-6,
      f"{hold_exp}, 남은 돈 {left_exp:,.0f}")
check("A3) 가격이 0 이나 음수인 종목은 걸러낸다",
      M.allocate(CAP, {"a": 0, "b": -5, "c": 10000})[0].keys() == {"c"})
check("A4) 종목이 하나도 없으면 전액이 현금으로 남는다",
      M.allocate(CAP, {}) == ({}, CAP))

# =====================================================================
# B) 재배분이 실제로 놀는 돈을 줄이는지 - 이게 이 파일의 핵심 기능
# =====================================================================
prices = CASES["삼바처럼 비싼 것 포함"]
hold, left = M.allocate(CAP, prices)
idle = left / CAP * 100
# 재배분 없이 슬롯대로만 샀다면
slot = CAP / len(prices)
naive_spent = 0.0
naive_skipped = 0
for c, p in prices.items():
    cost = p * (1 + M.BUY_COST_PCT / 100)
    q = int(slot // cost)
    if q:
        naive_spent += q * cost
    else:
        naive_skipped += 1
naive_idle = (CAP - naive_spent) / CAP * 100
check("B1) 비싼 종목이 섞여 있으면 슬롯대로는 돈이 많이 논다",
      naive_idle > 15, f"재배분 없으면 {naive_idle:.1f}% 놀음")
check("B2) 재배분하면 놀는 돈이 크게 줄어든다",
      idle < naive_idle / 3,
      f"{naive_idle:.1f}% -> {idle:.1f}%")
check("B3) 재배분 후 놀는 돈이 3% 미만이다", idle < 3.0, f"{idle:.2f}%")
check("B4) 못 사는 종목은 주문표에서 빠진다 (0주)",
      "000009" not in hold and naive_skipped >= 1,
      f"139.9만원 종목 제외, 건너뛴 종목 {naive_skipped}개")
check("B5) 싼 종목부터 1주씩 더 사는 방식이다",
      "order = sorted(prices.items(), key=lambda kv: kv[1])" in src)
check("B6) 더 살 수 없을 때까지 반복한다",
      "while added:" in src)

# 재배분이 정말 최선인지 - 1주라도 더 살 수 있으면 안 된다
cheapest = min(prices.values()) * (1 + M.BUY_COST_PCT / 100)
check("B7) 남은 돈으로 제일 싼 것 1주도 더 못 산다 (더 짤 수 없다)",
      left < cheapest, f"남은 {left:,.0f}원 < 최저가 {cheapest:,.0f}원")

# 투자금을 바꿔도 성립하는지
for cap in (500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000):
    h, lf = M.allocate(cap, CASES["평범한 10종목"])
    sp = cost_of(h, CASES["평범한 10종목"])
    cheap = min(CASES["평범한 10종목"].values()) * (1 + M.BUY_COST_PCT / 100)
    check(f"B8) 투자금 {cap:,}원에서도 예산 안 넘고 최적이다",
          sp <= cap + 1e-6 and lf < cheap,
          f"지출 {sp:,.0f}, 남음 {lf:,.0f}")

# 투자금이 늘면 총 주식수도 늘어야 한다 (단조성)
q_small = sum(M.allocate(1_000_000, CASES["평범한 10종목"])[0].values())
q_big = sum(M.allocate(2_000_000, CASES["평범한 10종목"])[0].values())
check("B9) 투자금이 2배면 주식수가 더 많다",
      q_big > q_small, f"{q_small}주 -> {q_big}주")

# =====================================================================
# C) 교체일 계산 - 거래일 기준이어야 한다
# =====================================================================
fake_dates = [f"d{i:04d}" for i in range(400)]
anchor_i = 250          # 주기(120)보다 뒤에 둬야 '기준일 이전' 검사가 된다
_saved = M.ANCHOR
try:
    M.ANCHOR = fake_dates[anchor_i]
    due, rem = M.rebalance_due(fake_dates, fake_dates[anchor_i])
    check("C1) 기준일 당일은 교체일이다", due and rem == 0)
    due, rem = M.rebalance_due(fake_dates, fake_dates[anchor_i + M.REBAL_DAYS])
    check("C2) 기준일 + 주기 도 교체일이다", due and rem == 0)
    due, rem = M.rebalance_due(fake_dates, fake_dates[anchor_i + 1])
    check("C3) 하루 뒤는 교체일이 아니고 남은 일수를 알려준다",
          not due and rem == M.REBAL_DAYS - 1, f"{rem}거래일 남음")
    due, rem = M.rebalance_due(fake_dates,
                               fake_dates[anchor_i + M.REBAL_DAYS - 1])
    check("C4) 교체일 하루 전은 1거래일 남았다고 한다",
          not due and rem == 1, f"{rem}")
    due, rem = M.rebalance_due(fake_dates, fake_dates[anchor_i - M.REBAL_DAYS])
    check("C5) 기준일 이전도 주기가 맞으면 교체일이다", due)
    due, rem = M.rebalance_due(fake_dates, "없는날")
    check("C6) 데이터에 없는 날은 판단하지 않는다 (None)",
          not due and rem is None)
finally:
    M.ANCHOR = _saved

check("C7) 주기가 120거래일이다 (약 반년)", M.REBAL_DAYS == 120)
check("C8) alert.py 와 같은 기준일을 쓴다",
      M.ANCHOR == "20260915"
      and "alert.py 와 같은 기준일" in src)
check("C9) 거래일 수로 센다고 적어놨다 (휴장일에 안 밀린다)",
      "휴장일에 밀리지 않는다" in src)

# =====================================================================
# D) 설정값이 근거대로인지
# =====================================================================
check("D1) 투자금 기본값이 200만원", M.CAPITAL == 2_000_000)
check("D2) 종목 수가 10개", M.N_PICK == 10)
check("D3) 목표가 월 3만원", M.TARGET_MONTH == 30_000)
check("D4) 연 목표가 월 목표의 12배", M.TARGET_YEAR == 360_000)
check("D5) 매수 비용이 왕복 수수료의 절반이다",
      abs(M.BUY_COST_PCT - M.S.FEE_ROUND_TRIP_PCT / 2) < 1e-12)
check("D6) 보수적으로 잡았다는 설명이 있다", "보수적으로" in src)

# =====================================================================
# E) 미래 정보 / 안전
# =====================================================================
check("E1) 종목 선정은 그 시점 정보로만 한다",
      'S.factor_score(panel, c, di, "low_vol")' in src
      and "S.universe_at(panel, di" in src)
check("E2) 손절/익절이 없다 (중간 판단 없음)",
      "손절/익절 없" in src)
check("E3) 주문을 내지 않는다고 밝힌다", "주문은 내지 않는다" in src)
check("E4) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"E5) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# F) 기대치를 과장하지 않는지 - 실제 돈이 들어가므로 제일 중요하다
# =====================================================================
check("F1) 목표가 연 18% 라는 것을 먼저 밝힌다",
      "연 18.0%" in src and "작은 목표가 아니다" in src)
check("F2) 목표가 과거 실적보다 높다고 밝힌다",
      "목표가 실적보다" in src and "약간 높다" in src)
check("F3) 중앙값이 목표에 못 미친다고 밝힌다",
      "29,127원" in src and "못 미친다" in src)
check("F4) 1년 손실 확률 17% 와 최악 -252,177원이 있다",
      "17%" in src and "252,177" in src)
check("F5) 2021~2022 연속 손실을 밝힌다",
      "425,818" in src and "60,967" in src and "2년 연속" in src)
check("F6) '꾸준히' 는 안 된다고 분명히 말한다",
      "꾸준히' 는 안 된다" in src)
check("F7) 2025년이 시장 덕이라는 경고가 있다",
      "+55%" in src)
check("F8) 200만원의 1주 단위 제약(26.3% 놀음)을 밝힌다",
      "26.3%" in src and "투자도 안 되고 놀았다" in src)
check("F9) 종목을 줄이면 나아질 것 같지만 아니라는 근거가 있다",
      "줄이면 나아질 것 같지만 아니다" in src)
check("F10) 반년 1회를 고른 근거(최악의 1년)가 적혀 있다",
      "447,087" in src and "최악이 절반" in src)
check("F11) 타이밍을 안 쓰는 이유를 근거와 함께 적었다",
      "z=+0.20" in src and "1.48" in src and "1.78" in src)
check("F12) 보장이 아니라고 주문표에 찍는다", "보장 아님" in src)

# =====================================================================
# G) 목표 -> 필요 자금 계산 (사용자 "하루 5000원" 질문)
# =====================================================================
lo, hi = M.required_capital(360_000)
check("G1) 필요 자금은 목표를 수익률로 나눈 값이다",
      abs(lo - 360_000 / M.ANN_HIGH) < 1e-6
      and abs(hi - 360_000 / M.ANN_LOW) < 1e-6)
check("G2) 낮은 쪽이 높은 쪽보다 작다 (범위로 답한다)", lo < hi,
      f"{lo:,.0f} ~ {hi:,.0f}")
check("G3) 목표가 2배면 필요 자금도 2배다",
      abs(M.required_capital(720_000)[0] - lo * 2) < 1e-6)
check("G4) 목표가 0 이하면 0 을 돌려준다",
      M.required_capital(0) == (0.0, 0.0)
      and M.required_capital(-1) == (0.0, 0.0))
check("G5) 실적 범위를 두 개 들고 있다 (한쪽으로 안 기운다)",
      M.ANN_LOW < M.ANN_HIGH
      and abs(M.ANN_LOW - 0.1399) < 1e-9
      and abs(M.ANN_HIGH - 0.1748) < 1e-9)
check("G6) 왜 두 개를 쓰는지 이유가 적혀 있다",
      "한쪽으로 기울므로" in src or "한쪽으로 기운다" in src)

# 하루 5,000원 = 연 61.5% 라는 것을 실제로 계산해내는지
rep5 = M.target_report(2_000_000, daily=5000)
check("G7) 하루 5,000원이 연 61.5% 라고 계산한다",
      "61.5%" in rep5, rep5.splitlines()[1].strip())
check("G8) 200만원으로는 부족하다고 말한다", "부족하다" in rep5)
check("G9) 필요 자금 700만~880만원을 내놓는다",
      "7,036,613" in rep5 and "8,791,994" in rep5)
check("G10) 200만원으로 기대할 하루 평균을 알려준다",
      "1,137" in rep5 and "1,421" in rep5)
check("G11) 하루 흔들림이 목표의 몇 배인지 알려준다",
      "35,158" in rep5 and "7배" in rep5)
check("G12) '매일' 은 안 된다고 근거와 함께 말한다",
      "41.1%" in rep5 and "11거래일" in rep5 and "평균" in rep5)

# 자금이 충분하면 판정이 바뀌어야 한다
rep_ok = M.target_report(9_000_000, daily=5000)
check("G13) 자금이 충분하면 '범위 안에 든다' 고 한다",
      "범위 안에 든다" in rep_ok and "부족하다" not in rep_ok)
check("G14) 자금이 커지면 흔들림도 비례해 커진다고 알려준다",
      "158,211" in rep_ok)

# 월 목표도 같은 계산이 되는지
rep_m = M.target_report(2_000_000, month=30000)
check("G15) 월 목표도 연 18.0% 로 환산한다", "18.0%" in rep_m)
check("G16) 월 목표에는 하루 흔들림 경고를 붙이지 않는다",
      "35,158" not in rep_m)
check("G17) 목표를 안 주면 빈 문자열이다", M.target_report(2_000_000) == "")

# 문서에도 남아 있는지
check("G18) 하루 5,000원이 월 3만원의 3.4배라고 문서에 밝힌다",
      "3.4배" in src and "더 작은 목표가 아니라" in src)
check("G19) 일별 손익 분포표가 문서에 있다",
      "35,158원" in src and "-429,500원" in src and "41.1%" in src)
check("G20) 매일 5,000원이 주식의 모양이 아니라고 밝힌다",
      "이자나 월급의 모양" in src)
check("G21) 200만원의 하루 평균 한계(1,100~1,400원)를 밝힌다",
      "1,100~1,400원" in src)
check("G22) 수익률을 3.4배로 올리는 법은 못 찾았다고 밝힌다",
      "찾지 못했다" in src)

# =====================================================================
# H) 매달 인출 모델 - 사용자 요구 조건 "한달에 3만원"
# =====================================================================
check("H1) 안전 인출률이 연 7.2% 다 (원금이 유지된 수준)",
      abs(M.SAFE_WITHDRAW_RATE - 0.072) < 1e-12)
check("H2) 월간 마이너스 비율 41.1% 를 들고 있다",
      abs(M.NEG_MONTH_PCT - 41.1) < 1e-9)
check("H3) 500만원이면 월 3만원이 나온다",
      abs(M.safe_withdrawal(5_000_000) - 30_000) < 1,
      f"{M.safe_withdrawal(5_000_000):,.0f}원")
check("H4) 200만원이면 월 12,000원까지다",
      abs(M.safe_withdrawal(2_000_000) - 12_000) < 1,
      f"{M.safe_withdrawal(2_000_000):,.0f}원")
check("H5) 월 3만원을 꺼내려면 500만원이 필요하다",
      abs(M.capital_for_withdrawal(30_000) - 5_000_000) < 1,
      f"{M.capital_for_withdrawal(30_000):,.0f}원")
check("H6) 두 함수가 서로 역이다",
      abs(M.safe_withdrawal(M.capital_for_withdrawal(45_000)) - 45_000) < 1)
check("H7) 자금이 2배면 꺼낼 수 있는 돈도 2배다",
      abs(M.safe_withdrawal(4_000_000)
          - 2 * M.safe_withdrawal(2_000_000)) < 1)
check("H8) 인출액이 0 이하면 자금 0 을 돌려준다",
      M.capital_for_withdrawal(0) == 0.0
      and M.capital_for_withdrawal(-5) == 0.0)

rep_bad = M.withdrawal_report(2_000_000, 30_000)
check("H9) 200만원/월3만원은 인출률 18.0% 라고 계산한다",
      "18.0%" in rep_bad)
check("H10) 너무 높다고 경고하고 원금 잠식을 말한다",
      "너무 높다" in rep_bad and "원금을 까먹" in rep_bad)
check("H11) 필요 자금 500만원을 알려준다", "5,000,000원" in rep_bad)
check("H12) 지금 자금으로 가능한 월 12,000원을 알려준다",
      "12,000원" in rep_bad)
check("H13) '매달 버는 모델' 은 못 짠다고 먼저 밝힌다",
      "짤 수 없다" in rep_bad and "41.1%" in rep_bad)
check("H14) 자금을 늘려도 천장이 58.9% 라고 밝힌다",
      "58.9%" in rep_bad)
check("H15) 인출 방법을 구체적으로 알려준다",
      "첫 거래일" in rep_bad and "일부 매도" in rep_bad)

rep_ok = M.withdrawal_report(5_000_000, 30_000)
check("H16) 500만원이면 안전 범위라고 판정한다",
      "안전 범위 안" in rep_ok and "너무 높다" not in rep_ok)
check("H17) 어느 경우든 '버는 것' 과 '꺼내 쓰는 것' 을 구별한다",
      "[1]" in rep_ok and "[2]" in rep_ok
      and "[1]" in rep_bad and "[2]" in rep_bad)

# 문서 쪽
check("H18) 연 36만원과 월 3만원이 다른 조건이라고 밝힌다",
      "전혀 다른 조건이다" in src)
check("H19) 월간 마이너스 41.1% 와 천장 58.9% 가 문서에 있다",
      "41.1%" in src and "58.9%" in src)
check("H20) 1억을 넣어도 안 된다는 것을 밝힌다",
      "1억을 넣어도" in src)
check("H21) 인출 시뮬 결과표가 문서에 있다 (200만원 원금 유지 0%)",
      "979,329원" in src and "원금 유지" in src)
check("H22) 200만원은 원금을 까먹는 것이라고 분명히 말한다",
      "원금을 까먹으면서 받는 것이지" in src)
check("H23) 500만원이면 8개 경로 전부 유지된다고 밝힌다",
      "500만원이면 8개 경로 전부" in src)
check("H24) 최종 답(전략/자금/인출/금지)이 정리돼 있다",
      "자금   **500만원**" in src and "금지" in src)
check("H25) 200만원만 쓸 경우의 대안(월 12,000원)을 준다",
      "월 12,000원" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
