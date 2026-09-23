"""analyze_recycle.py 검증 - 슬롯 재활용 익절을 공평하게 재는지.

(2026-09-19 신설) 사용자: "종목을 하나 정해서 정해진 익절률까지 계속
버티고 판매한 슬롯은 다시 정해놓은 종목을 사면서 계속 순환시키는 전략은?"

이 파일에서 제일 중요한 검사는 **선행 참조**다. 처음 쓴 코드는 익절한
그날 시가로 다시 샀는데, 익절은 장중 체결이고 시가는 그보다 앞선
가격이다. 오후에 받은 돈으로 오전 가격을 사는 것이라 그날 오른 종목이
공짜로 싸게 잡힌다. 그 한 줄이 연수익을 13.3% -> 25.4% 로 부풀렸고,
반띵 검증까지 통과시켰다. 그러니 그게 다시 들어오지 못하게 박아둔다.

지켜야 하는 것
  1) 판 날에는 다시 사지 않는다 (선행 참조 금지).
  2) 수수료를 매수/매도 각각 한 번씩만 문다.
  3) 익절 체결가가 갭에 유리하게 잡히지 않는다.
  4) 거래정지/데이터 공백을 0원으로 잡지 않는다 (가짜 낙폭).
  5) 낙폭이 줄었다는 것만으로 좋다고 하지 않는다 (포기한 수익과 견준다).
  6) 결론과 내 버그를 문서에 남긴다.

실행:
  python tests/test_analyze_recycle.py
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


import analyze_recycle as M  # noqa: E402

src = (REPO_ROOT / "analyze_recycle.py").read_text(encoding="utf-8")


class FakeSeries:
    def __init__(self, opens, closes):
        self.open = list(opens)
        self.close = list(closes)
        self.pos = {i: i for i in range(len(closes))}


def mk(n, op, cl):
    return FakeSeries([op] * n, [cl] * n)


# =====================================================================
# A) 선행 참조 - 이 파일의 핵심
# =====================================================================
check("A1) 판 슬롯이 다시 살 수 있는 날을 따로 관리한다",
      "free_from" in src)
check("A2) 익절한 날 다음날부터 살 수 있게 한다",
      "free_from[i] = di + 1" in src)
check("A3) 매수 단계에서 그 날짜를 실제로 본다",
      "di < free_from[i]" in src)
check("A4) 왜 막아야 하는지 코드에 적어뒀다",
      "오후에 받은 돈으로 오전 가격" in src)

# 실제로 같은 날 재매수가 일어나지 않는지 가짜 데이터로 확인한다.
N = 12
panel = {
    "A": mk(N, 100.0, 100.0),      # 첫날 사는 종목
    "B": mk(N, 50.0, 50.0),        # 빈 슬롯이 다음으로 살 종목
}
# A 는 di=2 에 장중 고가가 +10% 를 찍는다 -> 익절
hl = {}
for di in range(N):
    # 112 로 잡는다. 110 은 익절선(100*1.1 = 110.00000000000001) 과
    # 부동소수점 경계에 딱 걸려서, 검사가 코드가 아니라 반올림을 재게 된다.
    hl[(di, "A")] = (112.0, 100.0) if di == 2 else (100.0, 100.0)
    hl[(di, "B")] = (50.0, 50.0)

M.pool_at = lambda p, di, n=None: ["A", "B"]
r = M.run_recycle(list(range(N)), panel, hl, take=10, start=0,
                  capital=200_000, n_slot=1)
check("A5) 익절이 실제로 일어난다 (검사 전제)", r["takes"] == 1,
      f"{r['takes']}회")
# 슬롯 1개이므로, 같은 날 재매수를 허용하면 di=2 에 바로 B 를 산다.
# 막혀 있으면 di=3 에 산다.
# di=0 매수 -> di=2 익절. 같은 날 재매수를 허용하면 di=2 에 다시 사서
# 마지막 보유일이 (N-1)-2 = 9 가 되고, 막혀 있으면 di=3 이라 8 이 된다.
check("A6) 판 날에는 다시 사지 않는다 (같은 날 재매수 금지)",
      r["open"] and r["open"][0][1] == N - 1 - 3,
      f"마지막 매수 이후 보유일 {r['open'][0][1] if r['open'] else None} (막히면 8, 뚫리면 9)")

# =====================================================================
# B) 수수료
# =====================================================================
check("B1) 수수료는 편도 상수를 쓴다",
      abs(M.FEE_ONE_WAY - M.A.FEE_ONE_WAY) < 1e-12)
check("B2) 편도가 왕복의 절반이다",
      abs(M.FEE_ONE_WAY * 2 - M.A.S.FEE_ROUND_TRIP_PCT / 100) < 1e-12)
check("B3) 매도에 수수료를 뺀다", "(1 - FEE_ONE_WAY)" in src)
check("B4) 매수에 수수료를 더한다", "(1 + FEE_ONE_WAY)" in src)

# 익절 1회면 수수료가 매수1 + 매도1 이다. 그 이상이면 이중 차감이다.
one = M.run_recycle(list(range(N)), panel, hl, take=10, start=0,
                    capital=200_000, n_slot=1)
# di=0 매수, di=2 매도, di=3 재매수 -> 매수2 + 매도1
check("B5) 거래 횟수만큼만 수수료가 붙는다 (이중 차감 없음)",
      one["fees"] > 0 and one["fees"] < 200_000 * M.FEE_ONE_WAY * 4,
      f"{one['fees']:,.0f}원")

# =====================================================================
# C) 익절 체결가 - 유리하게 잡지 않는다
# =====================================================================
check("C1) 체결가 계산을 analyze_stops 의 것을 그대로 쓴다",
      "A.exit_price(" in src)
check("C2) 갭 상승이면 익절선이 아니라 시가에 팔린다",
      M.A.exit_price(100.0, 130.0, 135.0, 128.0, None, 10)[0] == 130.0)
check("C3) 장중에만 닿으면 익절선에 팔린다",
      abs(M.A.exit_price(100.0, 100.0, 115.0, 99.0, None, 10)[0] - 110.0) < 1e-9,
      f"{M.A.exit_price(100.0, 100.0, 115.0, 99.0, None, 10)[0]}")
check("C4) 안 닿으면 안 판다",
      M.A.exit_price(100.0, 100.0, 105.0, 99.0, None, 10) is None)
check("C5) 손절은 안 쓴다 (규칙상 없음)",
      "None, take)" in src and "stop_pct=" not in src)

# =====================================================================
# D) 거래정지 / 상장폐지 처리
# =====================================================================
check("D1) 공백을 0원으로 잡지 않고 마지막 값을 들고 간다",
      "last_px" in src and "가짜 낙폭" in src)

gap = {"A": FakeSeries([100.0] * 6, [100.0, 100.0, None, None, 100.0, 100.0])}
ghl = {(di, "A"): (100.0, 100.0) for di in (0, 1, 4, 5)}
M.pool_at = lambda p, di, n=None: ["A"]
g = M.run_recycle(list(range(6)), panel={"A": gap["A"]}, hl=ghl, take=50,
                  start=0, capital=200_000, n_slot=1)
check("D2) 공백 날에도 평가액이 0으로 꺼지지 않는다",
      min(g["curve"]) > 100_000, f"최저 평가액 {min(g['curve']):,.0f}원")
check("D3) 그래서 가짜 낙폭이 안 생긴다",
      M.mdd(g["curve"]) > -5.0, f"{M.mdd(g['curve']):.1f}%")

# =====================================================================
# E) 낙폭을 줄인 값어치를 따지는 판정
# =====================================================================
check("E1) 낙폭만 줄면 통과시키지 않는다 (수익을 더 많이 잃으면 탈락)",
      M.worth_it(22.0, -15.9, 14.9, -12.3) is False)
check("E2) 수익 손실이 작으면 통과시킨다",
      M.worth_it(22.0, -15.9, 21.0, -12.3) is True)
check("E3) 0 낙폭이 들어와도 안 터진다",
      M.worth_it(10.0, 0.0, 5.0, -1.0) is False)

check("E4) 끝에 남은 슬롯이 전부 마이너스인지 판정한다",
      M.losers_only([("A", 10, -5.0), ("B", 20, -1.0)]) is True)
check("E5) 하나라도 플러스면 아니다",
      M.losers_only([("A", 10, -5.0), ("B", 20, 1.0)]) is False)
check("E6) 빈 목록은 참이라고 하지 않는다", M.losers_only([]) is False)

# =====================================================================
# F) 지표 계산
# =====================================================================
check("F1) 최대낙폭은 고점 대비다",
      abs(M.mdd([100, 120, 60, 80]) - (-50.0)) < 1e-9,
      f"{M.mdd([100, 120, 60, 80]):.1f}%")
check("F2) 우상향이면 낙폭 0", abs(M.mdd([100, 110, 120])) < 1e-9)
check("F3) 연환산이 기간에 맞다",
      abs(M.annualized([100.0] * 246, capital=100.0)) < 1e-6)
check("F4) 두 배가 되면 연환산이 플러스다",
      M.annualized([100.0] * 245 + [200.0], capital=100.0) > 90)
check("F5) 빈 곡선이어도 안 터진다", M.annualized([]) == 0.0)

# =====================================================================
# G) 미래 정보 / 안전
# =====================================================================
check("G1) 종목 선정은 그 시점 정보로만 한다",
      "S.universe_at(panel, di" in src
      and 'S.factor_score(panel, c, di, "low_vol")' in src)
check("G2) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"G3) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# H) 문서 - 결론과 내 버그를 숨기지 않는지
# =====================================================================
check("H1) analyze_stops 의 익절과 무엇이 다른지 밝힌다",
      "현금으로 놀았다" in src and "바로 다시 산다" in src)
check("H2) 선행 참조 버그가 있었다고 적었다",
      "미래 정보" in src and "그 버그가 결과의 전부였다" in src)
check("H3) 고치기 전후 숫자를 나란히 적었다",
      "25.4%" in src and "13.3%" in src)
check("H4) 반띵 검증도 오염된 입력은 통과시킨다고 적었다",
      "입력이 오염돼 있으면 통과시킨다" in src)
check("H5) 시작일 5개 전부 졌다는 결과가 있다",
      "0/5" in src)
check("H6) 낙폭이 실제로 낮아진다는 것도 숨기지 않는다",
      "-12.3" in src and "일관되게" in src)
check("H7) 그런데 대가가 더 크다고 계산해서 보인다",
      "1.38" in src and "1.21" in src)
check("H8) 지는 기전(이긴 것만 팔고 진 것만 남는다)을 적었다",
      "10/10 마이너스" in src and "못 오른 것들의 모음" in src)
check("H9) 슬롯이 오래 묶인다는 위험을 적었다",
      "869" in src and "상장폐지" in src)
check("H10) 다음에 볼 곳(종목 수)을 적었다",
      "종목 수(분산)" in src and "아직 안 쟀다" in src)
check("H11) 결론이 '넣지 않는다' 로 제목에 있다",
      "넣지 않는다" in src.split("\n")[0])

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
