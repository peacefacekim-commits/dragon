"""analyze_why.py 검증 - 분해가 맞는지, 그리고 결론을 넘겨짚지 않는지.

(2026-09-21 신설) 이 파일은 새 규칙을 채택하지 않는다. 이미 채택한 규칙을
쪼개보는 것이다. 그래서 위험이 다른 데 있다.

  - 분해가 틀리면 '왜 통하나' 의 답이 통째로 틀린다.
  - 손익분기 1.318 을 방아쇠처럼 쓰면 안 된다. 눈금일 뿐이다.
  - '시장에 뒤처진다' 와 '손해를 본다' 를 섞어 쓰면 안 된다.

실행:
  python tests/test_analyze_why.py
"""
import collections
import pathlib
import statistics as st
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import analyze_why as M  # noqa: E402

src = (REPO_ROOT / "analyze_why.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes):
        self.close = list(closes)
        self.open = list(closes)
        self.pos = {i: i for i in range(len(closes))}


# =====================================================================
# A) 손익분기 계산
# =====================================================================
check("A1) 실측값으로 1.318 이 나온다",
      abs(M.breakeven_ratio() - 1.318) < 0.002, f"{M.breakeven_ratio():.3f}")
check("A2) 공식이 내린날이득/오른날끌림 이다",
      abs(M.breakeven_ratio(2.0, 5.0) - 2.5) < 1e-9)
check("A3) 끌림이 0 이면 무한 (아무리 올라도 안 뒤처짐)",
      M.breakeven_ratio(0.0, 1.0) == float("inf"))
check("A4) 끌림이 커지면 손익분기가 낮아진다 (더 빨리 상쇄)",
      M.breakeven_ratio(2.0, 1.0) < M.breakeven_ratio(1.0, 1.0))

# 손익분기 비율에서 엣지가 정확히 0 이어야 한다 - 두 함수가 맞물리는지
be = M.breakeven_ratio()
check("A5) 손익분기 비율에서 총 엣지가 0 이다",
      abs(M.edge_left(be * 1000, 1000)) < 1e-6,
      f"{M.edge_left(be*1000, 1000):.6f}")
check("A6) 실제 구성(592/558)에서는 엣지가 양수다",
      M.edge_left(592, 558) > 0, f"{M.edge_left(592, 558):+.0f}%p")
check("A7) 실제 총 엣지가 +115%p 안팎이다 (문서와 맞음)",
      110 < M.edge_left(592, 558) < 122, f"{M.edge_left(592, 558):+.1f}%p")
check("A8) 오른 날만 있으면 엣지가 마이너스다",
      M.edge_left(1000, 0) < 0)
check("A9) 내린 날만 있으면 엣지가 플러스다",
      M.edge_left(0, 1000) > 0)

# =====================================================================
# B) 날 가르기와 기여도 분해
# =====================================================================
# 가짜 시장: A,B 는 안 흔들리고(저변동) Y,Z 는 크게 흔들린다(고변동).
N = 8
panel = {
    "A": FakeSeries([100, 101, 100, 101, 100, 101, 100, 101]),
    "B": FakeSeries([100, 101, 100, 101, 100, 101, 100, 101]),
    "Y": FakeSeries([100, 110, 90, 110, 90, 110, 90, 110]),
    "Z": FakeSeries([100, 110, 90, 110, 90, 110, 90, 110]),
}
order = {di: ["A", "B", "Y", "Z"] for di in range(N)}
M_MINPOOL = M.MIN_POOL
M.MIN_POOL, M.PICK = 2, 2
try:
    d = M.daily_split(list(range(N)), panel, order, base=0)
    nu, nd = len(d["up"]["pool"]), len(d["down"]["pool"])
    check("B1) 오른 날과 내린 날을 둘 다 잡는다", nu > 0 and nd > 0,
          f"오른 {nu} 내린 {nd}")
    check("B2) 오른 날에는 저변동이 풀보다 덜 오른다",
          st.mean(d["up"]["lo"]) < st.mean(d["up"]["pool"]),
          f"{st.mean(d['up']['lo']):.2f} < {st.mean(d['up']['pool']):.2f}")
    check("B3) 내린 날에는 저변동이 풀보다 덜 내린다",
          st.mean(d["down"]["lo"]) > st.mean(d["down"]["pool"]),
          f"{st.mean(d['down']['lo']):.2f} > {st.mean(d['down']['pool']):.2f}")
    check("B4) 고변동은 반대로 움직인다 (오른날 더 오르고 내린날 더 내린다)",
          st.mean(d["up"]["hi"]) > st.mean(d["up"]["pool"])
          and st.mean(d["down"]["hi"]) < st.mean(d["down"]["pool"]))
    check("B5) 기여도는 뽑힌 종목에만 쌓인다 (안 뽑힌 종목은 없다)",
          set(d["contrib"]) <= {"A", "B"}, str(dict(d["contrib"])))
    check("B6) 등장 횟수를 따로 센다",
          d["appear"]["A"] == nu + nd, f"{d['appear']['A']} vs {nu+nd}")
finally:
    M.MIN_POOL, M.PICK = M_MINPOOL, 10

# 풀이 너무 작으면 그 날을 버려야 한다 (표본이 적으면 평균이 튄다)
thin = {di: ["A"] for di in range(N)}
d2 = M.daily_split(list(range(N)), {"A": panel["A"]}, thin, base=0)
check("B7) 풀이 너무 작은 날은 버린다",
      len(d2["up"]["pool"]) == 0 and len(d2["down"]["pool"]) == 0)

# =====================================================================
# C) 몇 종목에 의존하나
# =====================================================================
c = collections.Counter({"a": 50.0, "b": 30.0, "c": 20.0})
check("C1) 상위 1개를 빼면 나머지 비율이 나온다",
      abs(M.drop_top(c, 1) - 0.5) < 1e-9, f"{M.drop_top(c, 1):.3f}")
check("C2) 상위 2개를 빼면 20% 남는다",
      abs(M.drop_top(c, 2) - 0.2) < 1e-9)
check("C3) 0개를 빼면 전부 남는다", abs(M.drop_top(c, 0) - 1.0) < 1e-9)
check("C4) 빈 입력이어도 안 터진다", M.drop_top(collections.Counter(), 1) == 0.0)
check("C5) 마이너스 기여 종목이 섞여도 계산된다",
      M.drop_top(collections.Counter({"a": 10.0, "b": -5.0}), 1) < 0)

# =====================================================================
# D) 교체일 종목 세기
# =====================================================================
order2 = {di: [f"c{i}" for i in range(20)] for di in range(500)}
got, rounds = M.picks_over_time(list(range(500)), None, order2, base=0, period=120)
check("D1) 회차 수가 주기와 맞는다", rounds == 5, f"{rounds}회")
check("D2) 회차마다 PICK 개씩 센다",
      sum(got.values()) == rounds * M.PICK, f"{sum(got.values())}")

# =====================================================================
# E) 문서 - 결론을 넘겨짚지 않는가
# =====================================================================
check("E1) 왜 이 파일을 쓰는지 밝힌다 (이유를 안 물어봤다)",
      "통하는 이유가 뭔가" in flat)
check("E2) 다중검정이 안 늘어난다고 밝힌다",
      "다중검정이 늘지 않는다" in flat)
check("E3) 실제 뽑히는 종목을 적었다",
      "KT&G" in src and "9/10" in src)
check("E4) 금융 단독 베팅이 아니라고 근거를 들어 말한다",
      "금융 단독 베팅' 은 아니다" in flat or "금융 단독 베팅" in src)
check("E5) 그래도 쏠림이 있다는 것은 인정한다",
      "몇 종목을 계속 들고 있는 전략" in flat)
check("E6) 따라가는 비율/맞는 비율을 숫자로 적었다",
      "37%" in src and "23%" in src)
check("E7) 엣지가 두 큰 값의 차이라고 밝힌다",
      "서로 상쇄되는 두 큰 값의 차이" in flat)
check("E8) 검산(22.0%)을 적었다", "연 22.0%" in src)
check("E9) 풀 자체는 마이너스였다는 것도 적었다", "-2.6%" in src)
check("E10) 손익분기 32% 를 적었다", "32% 이상" in src)
check("E11) '뒤처진다' 와 '손해본다' 를 구별한다",
      "손해를 보는 게 아니라" in flat and "둘은 다르다" in flat)
check("E12) 1.318 을 방아쇠가 아니라 눈금이라고 못 박았다",
      "경보의 눈금이지 방아쇠가 아니다" in flat)
check("E13) 상승장에서 뒤처지는 것은 고장이 아니라고 적었다",
      "정상 작동" in src)
check("E14) 진짜 의심해야 할 때를 적었다",
      "23% 비율이 무너질 때" in flat)
check("E15) 종목 의존도를 숫자로 적었다",
      "88% 남음" in src and "53% 남음" in src)
check("E16) 안 잰 것(신호 vs 실제 포트폴리오)을 밝힌다",
      "같다는 뜻은 아니다" in flat)

# =====================================================================
# F) 안전
# =====================================================================
check("F1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"F2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
