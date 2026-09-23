"""analyze_short_term.py 검증 - 짧은 거래를 공평하게 재는지.

(2026-09-19 신설) 사용자: "짧게 거래해서 시세차익을 노리는 형태는?"

결론이 '안 된다' 쪽이므로, 짧은 쪽에 **불리하게** 계산하지 않았는지가
핵심이다. 불리하게 기울이면 결론이 공짜로 나온다.

지켜야 하는 것
  1) 수수료를 회차마다 정확히 한 번만 물려야 한다. 두 번 물리면
     짧은 쪽이 부당하게 나빠진다.
  2) 연환산이 보유기간에 맞아야 한다 (1일 보유면 246번 복리).
  3) '풀 대비' 로 재야 시장 등락이 상쇄된다. 총수익만 보면 그 시기가
     좋았는지 나빴는지가 섞인다.
  4) 대조군이 같은 회차 안에서 섞어야 한다. 회차를 가로질러 섞으면
     시장 등락이 대조군에 남아 비교가 틀어진다.
  5) 과거 수익 신호가 전날까지만 봐야 한다 (미래 정보 금지).
  6) 30가지를 훑었다는 것과 경계선 값을 믿지 말라는 경고가 있어야 한다.
  7) 호가 스프레드를 안 넣어서 짧은 쪽에 유리하게 기울어 있다는
     사실을 밝혀야 한다.

실행:
  python tests/test_analyze_short_term.py
"""
import math
import pathlib
import statistics as st
import sys

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import analyze_short_term as M  # noqa: E402

src = (REPO_ROOT / "analyze_short_term.py").read_text(encoding="utf-8")


class FakeSeries:
    def __init__(self, closes, opens=None):
        self.close = list(closes)
        self.open = list(opens if opens is not None else closes)
        self.pos = {i: i for i in range(len(self.close))}


# =====================================================================
# A) 수익 계산 - 시가 매수, 시가 매도
# =====================================================================
panel = {"A": FakeSeries([100.0] * 10, [100, 110, 120, 130, 140,
                                        150, 160, 170, 180, 190])}
check("A1) 시가에 사서 시가에 판다",
      abs(M.trade_ret(panel, "A", 0, 1) - 10.0) < 1e-9,
      f"{M.trade_ret(panel, 'A', 0, 1):.2f}%")
check("A2) 보유기간이 길면 그만큼 누적된다",
      abs(M.trade_ret(panel, "A", 0, 5) - 50.0) < 1e-9)
check("A3) 없는 날은 None", M.trade_ret(panel, "A", 0, 99) is None)
check("A4) 없는 종목은 None", M.trade_ret(panel, "Z", 0, 1) is None)

# 과거수익 신호가 전날까지만 보는지
panel2 = {"B": FakeSeries([100, 110, 121, 133.1, 146.41, 161.051])}
# di=3 이면 전날 j=2(121), w=2 면 j0=0(100) -> +21%
check("A5) 과거수익은 전날까지만 본다 (미래 정보 금지)",
      abs(M.past_ret(panel2, "B", 3, 2) - 21.0) < 1e-6,
      f"{M.past_ret(panel2, 'B', 3, 2):.2f}%")
check("A6) 과거수익 계산에 당일 종가를 안 쓴다",
      "s.pos.get(di - 1)" in src and "s.pos.get(di - 1 - w)" in src)
check("A7) 데이터가 모자라면 None", M.past_ret(panel2, "B", 1, 5) is None)

# =====================================================================
# B) 연환산 - 보유기간에 맞아야 한다
# =====================================================================
check("B1) 20일 보유 +1% 는 연 12.3회 복리다",
      abs(M.annualize(1.0, 20) - ((1.01 ** (246 / 20) - 1) * 100)) < 1e-9)
check("B2) 1일 보유는 246회 복리다",
      abs(M.annualize(0.1, 1) - ((1.001 ** 246 - 1) * 100)) < 1e-9)
check("B3) 회차 수익이 0 이면 연환산도 0", abs(M.annualize(0.0, 5)) < 1e-12)
check("B4) 회차가 마이너스면 연환산도 마이너스", M.annualize(-0.5, 1) < 0)
check("B5) 짧을수록 같은 회차수익이 크게 증폭된다",
      M.annualize(0.5, 1) > M.annualize(0.5, 20))
check("B6) 마이너스도 짧을수록 크게 증폭된다",
      M.annualize(-0.5, 1) < M.annualize(-0.5, 20))

# =====================================================================
# C) 손익분기 - 이 파일의 핵심 논리
# =====================================================================
check("C1) 손익분기 = 수수료 / 하루당엣지",
      abs(M.break_even_hold(0.093, 0.21) - 0.21 / 0.093) < 1e-9,
      f"{M.break_even_hold(0.093, 0.21):.2f}일")
check("C2) 실제 값으로 2.3일이 나온다",
      abs(M.break_even_hold(0.093) - 2.258) < 0.01,
      f"{M.break_even_hold(0.093):.2f}일")
check("C3) 수수료가 절반이면 손익분기도 절반",
      abs(M.break_even_hold(0.093, 0.105)
          - M.break_even_hold(0.093, 0.21) / 2) < 1e-9)
check("C4) 엣지가 크면 손익분기가 짧아진다",
      M.break_even_hold(0.2) < M.break_even_hold(0.05))
check("C5) 엣지가 0 이하면 무한 (아무리 길어도 본전 못 넘음)",
      M.break_even_hold(0.0) == float("inf")
      and M.break_even_hold(-0.1) == float("inf"))

# =====================================================================
# D) 수수료를 회차당 한 번만 무는지 - 짧은 쪽에 불리하게 안 했나
# =====================================================================
check("D1) 순수익 = 총수익 - 수수료 (한 번만)",
      "net = gross - FEE" in src)
check("D2) 연환산에 수수료를 또 안 뺀다 (이중 차감 금지)",
      "annualize(net, hold)" in src
      and "annualize(net - FEE" not in src)
check("D3) 본전 기준이 회당 수수료 한 번이라고 밝힌다",
      "회당 총수익 > 0.21%" in src or "회당 총수익이 이걸 넘어야" in src)
check("D4) 수수료는 왕복 상수를 그대로 쓴다",
      abs(M.FEE - M.S.FEE_ROUND_TRIP_PCT) < 1e-12)

# =====================================================================
# E) 대조군이 회차 안에서 섞는지 - 가로질러 섞으면 틀어진다
# =====================================================================
check("E1) 대조군은 회차 안에서 섞는다 (회차 루프 안의 permutation)",
      "idx = rng.permutation(len(rs))" in src)
check("E2) 실제도 대조군도 '풀 평균 대비' 로 잰다",
      "rs[order[:PICK]].mean() - rs.mean()" in src
      and "rs[idx[:PICK]].mean() - rs.mean()" in src)
check("E3) 대조군을 여러 번 돌린다", M.N_PERM >= 500, f"{M.N_PERM}번")
check("E4) 씨앗이 고정돼 있다", "SEED = 20260919" in src)

# 가짜 데이터로 대조군이 제 기능을 하는지
rng = np.random.default_rng(5)
for trial, (has_edge, want) in enumerate(((False, "높아야"), (True, "낮아야"))):
    reals, beats = [], []
    for rep in range(3):
        r2 = np.random.default_rng(100 + trial * 10 + rep)
        real_ex, perm_ex = [], [[] for _ in range(200)]
        for _round in range(120):
            xs = r2.normal(size=40)
            rs = r2.normal(size=40) + (xs * 0.5 if has_edge else 0.0)
            order = np.argsort(-xs)
            real_ex.append(rs[order[:10]].mean() - rs.mean())
            for p in range(200):
                idx = r2.permutation(40)
                perm_ex[p].append(rs[idx[:10]].mean() - rs.mean())
        rm = st.mean(real_ex)
        pm = [st.mean(p) for p in perm_ex]
        beats.append(sum(1 for v in pm if v >= rm) / len(pm))
    beats.sort()
    if has_edge:
        check("E5) 진짜 엣지가 있으면 대조군을 통과한다 (검정력)",
              beats[1] < 0.05, f"통과율 중앙값 {beats[1]:.3f}")
    else:
        check("E6) 엣지가 없으면 대조군을 못 넘는다 (거짓 통과 안 함)",
              beats[1] > 0.05, f"통과율 중앙값 {beats[1]:.3f}")

# =====================================================================
# F) 미래 정보 / 안전
# =====================================================================
check("F1) 종목 선정은 그 시점 정보로만 한다",
      "S.universe_at(panel, di" in src
      and 'S.factor_score(panel, code, di, "low_vol")' in src)
check("F2) 회차가 겹치지 않는다", "di += hold" in src)
check("F3) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"F4) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# G) 문서가 결론을 과장하거나 숨기지 않는지
# =====================================================================
check("G1) 짧은 쪽이 표본이 많다는 장점을 인정한다",
      "표본이 많" in src and "1,257" in src)
check("G2) 보유기간별 표가 있다 (1일 -27.0%, 20일 +13.8%)",
      "-27.0%" in src and "+13.8%" in src)
check("G3) 하루당 엣지가 거의 일정하다는 핵심 발견이 있다",
      "0.093%" in src and "거의 일정" in src)
check("G4) 손익분기 2.3일이 기록돼 있다", "2.3일" in src)
check("G5) 신호가 없어서가 아니라 수수료 때문이라고 구별한다",
      "신호가 없어서가 아니라" in src)
check("G6) 1일에도 신호가 살아있다는 것을 밝힌다",
      "1일에도 살아 있다" in src or "짧은 쪽에서 죽는 게 아니다" in src)
check("G7) 단기 반전이 안 된다는 결과가 있다",
      "5일 반전" in src and "-20.5%" in src)
check("G8) 모멘텀이 크게 마이너스라는 결과가 있다",
      "모멘텀" in src and "-75.2%" in src)
check("G9) 30가지를 훑었다는 다중검정 경고가 있다",
      "30가지" in src and "1.5개" in src)
check("G10) 경계선 값을 믿지 말라고 적었다",
      "경계선" in src and "믿지 말" in src)
# (2026-09-19 수정) 원래 이 검사는 '수수료가 절반이어도' 라는 문장을
# 요구했다. 그런데 0.21% 의 86% 가 세금이라 절반으로 만들 수가 없다.
# 그 문장을 정정했으므로 검사도 정정 내용을 확인하도록 바꿨다.
check("G11) 수수료를 깎아도 안 된다는 것을 실제 구성으로 밝힌다",
      "86% 가 세금이다" in src and "0.180%" in src)
check("G11b) '절반' 가정이 틀렸다고 스스로 정정했다",
      "현실에서 불가능한 가정이었다" in src)
check("G11c) 실제 손익분기 변화(2.3->1.9일)를 적었다",
      "2.3일 -> 1.9일" in src)
check("G12) 호가 스프레드를 안 넣어 짧은 쪽에 유리하게 기울었다고 밝힌다",
      "스프레드" in src and "유리하게" in src and "더" in src)
check("G13) 대조군 통과율이 기록돼 있다",
      "0.3%" in src and "0.6%" in src and "2.1%" in src)
check("G14) 짧게 vs 길게가 취향이 아니라 계산 문제라고 정리한다",
      "취향 문제가 아니라" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
