"""analyze_knobs.py 검증 - 손잡이 훑기를 공평하게 재는지.

(2026-09-19 신설) 사용자: "지금 거래 방법에서 이윤을 얻을 수 있는 방법을
찾아봐"

이 파일의 결론이 "하나도 못 바꾼다" 이므로, 위험은 두 방향이다.
  - 너무 관대해서 잡음을 채택하는 것 (24가지를 훑으면 우연히 1등이 나온다)
  - 너무 엄격해서 진짜 손잡이를 놓치는 것

그래서 판정 함수 두 개를 따로 두고 양쪽을 다 검사한다.
  beats_noise()   손잡이가 만든 차이가 시작일 운의 두 배는 되는가
  capital_bound() 성과가 나쁜 걸 '돈이 모자라서' 라고 말할 수 있는가

실행:
  python tests/test_analyze_knobs.py
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


import analyze_knobs as M  # noqa: E402

src = (REPO_ROOT / "analyze_knobs.py").read_text(encoding="utf-8")


class FakeSeries:
    def __init__(self, opens, closes):
        self.open = list(opens)
        self.close = list(closes)
        self.pos = {i: i for i in range(len(closes))}


# =====================================================================
# A) 잡음을 채택하지 않는 판정
# =====================================================================
# 실제로 나온 값: 중앙값 폭 4.6%p, 시작일 폭 11.4%p -> 못 고른다
check("A1) 실제 vol_days 결과는 고를 수 없다고 판정한다",
      M.beats_noise([20.9, 18.8, 22.0, 17.4, 19.8, 19.0], 11.4) is False)
check("A2) 손잡이 폭이 시작일 폭의 두 배면 고를 수 있다",
      M.beats_noise([10.0, 30.0], 10.0) is True)
check("A3) 딱 두 배도 통과시킨다 (경계)",
      M.beats_noise([10.0, 30.0], 10.0) is True)
check("A4) 두 배에 못 미치면 탈락",
      M.beats_noise([10.0, 29.9], 10.0) is False)
check("A5) 값이 하나뿐이면 고를 수 없다", M.beats_noise([10.0], 1.0) is False)
check("A6) 기준이 analyze_event_rebal 과 같은 생각이라고 적었다",
      "pickable" in src and "두 배" in src)

# 지그재그 판정을 재사용하는지 (직접 새로 만들면 기준이 갈린다)
check("A7) 지그재그 판정을 analyze_event_rebal 것을 쓴다",
      "E.is_zigzag(" in src)
check("A8) 실제 vol_days 결과가 지그재그로 잡힌다",
      M.E.is_zigzag([20.9, 18.8, 22.0, 17.4, 19.8, 19.0]) is True)
check("A9) 단조 증가는 지그재그가 아니다",
      M.E.is_zigzag([10.0, 12.0, 15.0, 19.0]) is False)

# =====================================================================
# B) 돈이 모자란 것과 분산이 나쁜 것을 구별하는 판정
# =====================================================================
check("B1) 실제로 잰 노는 현금(0.4~0.6%)은 돈 문제가 아니라고 판정한다",
      all(M.capital_bound(v) is False for v in (0.4, 0.5, 0.6)))
check("B2) 현금이 많이 남으면 돈 문제를 의심한다",
      M.capital_bound(26.3) is True)
check("B3) 경계(5%)는 넘어야 의심한다",
      M.capital_bound(5.0) is False and M.capital_bound(5.1) is True)
check("B4) 이 구별을 왜 하는지 코드에 적어뒀다",
      "분산이 해로운 것" in src and "돈이 노는 것" in src)

# =====================================================================
# C) 시뮬레이터 - 노는 현금을 실제로 돌려주는지
# =====================================================================
N = 40
panel = {
    "A": FakeSeries([100.0] * N, [100.0] * N),
    "B": FakeSeries([200.0] * N, [200.0] * N),
    "C": FakeSeries([50.0] * N, [50.0] * N),
}
order = {di: ["A", "B", "C"] for di in range(N)}
curve, idle = M.run(list(range(N)), panel, order, 10, 0, 3, capital=300_000)
check("C1) 곡선 길이가 기간과 같다", len(curve) == N, f"{len(curve)}")
check("C2) 가격이 안 변하면 자본이 거의 그대로다 (수수료만큼만 준다)",
      299_000 < curve[-1] <= 300_000, f"{curve[-1]:,.0f}원")
check("C3) 노는 현금 비율을 돌려준다 (0~100 사이)",
      0.0 <= idle <= 100.0, f"{idle:.2f}%")
check("C4) 다 살 수 있으면 노는 현금이 거의 없다", idle < 5.0, f"{idle:.2f}%")

# 슬롯당 돈이 모자라면 현금이 남아야 한다 - 판정 함수가 구별할 재료가 되는지
poor = {"X": FakeSeries([90_000.0] * N, [90_000.0] * N)}
order_poor = {di: ["X"] for di in range(N)}
_c2, idle2 = M.run(list(range(N)), panel={**poor}, order=order_poor,
                   period=10, start=0, pick=1, capital=100_000)
check("C5) 비싼 주식 하나뿐이면 현금이 남는다 (구별할 재료가 생긴다)",
      idle2 > 5.0, f"{idle2:.1f}%")
check("C6) 그 경우 돈 문제라고 판정한다", M.capital_bound(idle2) is True)

# =====================================================================
# D) 지표 계산
# =====================================================================
check("D1) 최대낙폭은 고점 대비다",
      abs(M.mdd([100, 120, 60, 80]) - (-50.0)) < 1e-9)
check("D2) 우상향이면 낙폭 0", abs(M.mdd([100, 110, 120])) < 1e-9)
check("D3) 제자리면 연환산 0",
      abs(M.annualized([100.0] * 246, capital=100.0)) < 1e-6)
check("D4) 빈 곡선이어도 안 터진다", M.annualized([]) == 0.0)

# =====================================================================
# E) vol_days 를 실제로 바꿔 끼울 수 있는지
# =====================================================================
check("E1) ranks 가 vol_days 를 받는다",
      "vol_days=vol_days" in src)
check("E2) 기본값이 지금 쓰는 60 이다",
      M.ranks.__defaults__[0] == 60, str(M.ranks.__defaults__))
check("E3) 훑는 목록에 60 이 들어있다 (기준점이 있어야 비교가 된다)",
      60 in M.VOL_DAYS, str(M.VOL_DAYS))
check("E4) 짧은 쪽과 긴 쪽을 다 훑는다",
      min(M.VOL_DAYS) <= 20 and max(M.VOL_DAYS) >= 250, str(M.VOL_DAYS))
check("E5) 종목 수에 지금 값 10 이 들어있다", 10 in M.PICKS, str(M.PICKS))
check("E6) 교체 주기에 지금 값 120 이 들어있다", 120 in M.PERIODS,
      str(M.PERIODS))
check("E7) 종목 선정은 그 시점 정보로만 한다",
      "S.universe_at(panel, di" in src and 'factor_score(panel, c, di, "low_vol"' in src)

# =====================================================================
# F) 안전
# =====================================================================
check("F1) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"F2) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# G) 문서 - 결론을 부풀리거나 숨기지 않는지
# =====================================================================
check("G1) 채택 조건을 미리 정했다고 적었다",
      "미리 정해두고 시작했다" in src)
check("G2) 조건 세 개가 다 적혀 있다",
      "매끄럽게" in src and "반띵" in src and "시작일 5개" in src)
check("G3) 집중(3~5종목)이 나쁘다는 결과가 있다",
      "10.6" in src and "18.2" in src)
# 줄바꿈을 건너뛰고 봐야 한다 - 이 문장은 두 줄에 걸쳐 있다.
_flat = " ".join(src.split())
check("G4) 왜 집중이 안 먹히는지 설명한다",
      "무리의 성질이지 순위의 성질이 아니다" in _flat)
check("G4b) 좁히면 엣지가 아니라 잡음이 커진다고 적었다",
      "엣지가 진해지는 게 아니라 개별 종목의 잡음만 커진다" in _flat)
check("G5) 1등이 지금 설정인 것을 그대로 믿지 말라고 적었다",
      "그대로 믿으면 안 된다" in src)
check("G6) 최소값으로 보면 순위가 바뀐다는 것을 보인다",
      "15종목  40일" in src and "1.4%p" in src)
check("G7) 노는 현금을 재서 돈 문제가 아님을 밝힌다",
      "0.4~0.6%" in src and "돈이 모자라서 나쁜 게 아니다" in src)
check("G8) 안 잰 것(비중 쏠림)을 안 잰다고 밝힌다",
      "그건 따로 안 쟀다" in src)
check("G9) vol_days 가 지그재그라는 결과가 있다",
      "20.9 -> 18.8 -> 22.0" in src)
check("G10) 60 을 두는 이유가 '좋아서' 가 아니라고 못 박았다",
      "60 이 좋다는 것을 확인해서가 아니다" in src
      or "60 이 좋아서가 아니라" in src)
check("G11) 손잡이가 성과를 별로 안 움직인다는 것이 결론이라고 적었다",
      "돌려도 안 움직이는 손잡이" in src)
check("G12) 실제로 작동하는 둘(저변동 선정/부분교체)을 적었다",
      "저변동 선정" in src and "부분교체" in src and "-95%" in src)
check("G13) 다음은 손잡이가 아니라 새 신호라고 적었다",
      "새 신호" in src and "배당수익률" in src)
check("G14) 다중검정 누적을 세어서 적었다",
      "70가지" in src)

# =====================================================================
# H) 짧은 주기 (--fast) - 사용자: "매매 주기를 더 좁히면"
# =====================================================================
flat = " ".join(src.split())
check("H1) 하루 주기까지 잰다", 1 in M.FAST_PERIODS, str(M.FAST_PERIODS))
check("H2) 1주/2주/3주가 다 들어 있다",
      all(p in M.FAST_PERIODS for p in (5, 10, 15)))
check("H3) 비교 기준으로 120일도 같이 돌린다", 120 in M.FAST_PERIODS)
check("H4) 이름표가 사람 말로 나온다",
      M.label_of(1) == "1일(매일)" and M.label_of(5) == "5일(1주)")
check("H5) 이름표가 없는 주기는 숫자로", M.label_of(60) == "60일")
check("H6) 슬리피지 0부터 0.30%까지 잰다",
      M.SLIPPAGES[0] == 0.0 and max(M.SLIPPAGES) >= 0.0030,
      str(M.SLIPPAGES))
check("H7) 슬리피지를 수수료에 더해서 문다 (한쪽당)",
      "base_fee + slip" in src)
check("H8) 슬리피지를 재고 나서 원래 수수료로 되돌린다",
      "E.FEE_ONE_WAY = base_fee" in src)
check("H9) 왜 슬리피지를 변수로 두는지 적었다",
      "슬리피지를 안 넣는다" in flat)

check("H10) 하루 주기가 백테스트에서 제일 높다는 것을 숨기지 않았다",
      "25.1" in src and "제일 높게 나온다" in flat)
check("H11) 그래도 채택 안 한다고 밝힌다", "그럼에도 채택하지 않는다" in flat)
check("H12) 이유1 - 반띵 뒤집힘", "뒤집힘" in src and "후반부에만" in flat)
check("H13) 15일만 양쪽을 넘는 모순을 짚는다",
      "두 잣대가 어긋나는 것 자체가 잡음" in flat)
check("H14) 이유2 - 슬리피지에서 역전",
      "0.08%" in src and "1등이 120일로 바뀐다" in flat)
check("H15) 호가 단위로 슬리피지 크기를 근거 댄다",
      "한 틱이 50원" in flat and "반스프레드" in flat)
check("H16) 120일이 슬리피지에 둔감하다고 적었다", "거의 안 흔들린다" in flat)
check("H17) 이유3 - 낙폭이 나빠진다",
      "-15.9% -> -18.8%" in flat and "방향이 반대다" in flat)
check("H18) 짧은 주기가 순위를 싱싱하게 하는 것은 사실이라고 인정한다",
      "순위가 더 싱싱해지는 것은 사실" in flat)
check("H19) 비용을 모른다는 것이 결론이라고 적었다",
      "비용을 정확히 모른다" in flat)
check("H20) 거래 건수 차이를 적었다", "95건" in flat and "1,250건" in flat)
check("H21) --fast 실행법이 있다", "--fast" in src)
check("H22) 40일 아래를 안 봤었다고 밝힌다", "위의 훑기는 40일부터였다" in flat)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
