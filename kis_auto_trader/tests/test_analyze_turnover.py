"""analyze_turnover.py 검증 - 부분교체가 공짜로 유리해지지 않게.

(2026-09-19 신설) 사용자: "이 방식대로 생각을 확장시켜 보자."

이 파일의 결론은 '부분교체가 낫다' 이고, 그건 **수수료 계산에 전적으로
의존한다**. 부분교체 쪽 수수료를 빼먹으면 결론이 공짜로 나온다.
그래서 검사의 중심은 수수료다.

지켜야 하는 것
  1) 부분교체도 팔고 사는 종목에는 반드시 수수료를 물어야 한다.
     안 바뀐 종목만 면제된다.
  2) 교체비율 계산이 '새로 들어온 종목 수 / 종목 수' 여야 한다.
  3) 부분교체가 전량교체보다 수수료를 적게 내야 한다 (같으면 버그).
  4) 종목이 하나도 안 바뀌면 부분교체는 수수료가 0 이어야 한다.
  5) 반기 양방향이 기간을 실제로 반으로 가르는지.
  6) 문서가 '주기는 못 가린다' 를 분명히 해야 한다 - 1위 숫자만 보면
     5일이 최고로 보이는데 반기 검증에서 뒤집혔다.

실행:
  python tests/test_analyze_turnover.py
"""
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


import analyze_turnover as M  # noqa: E402

src = (REPO_ROOT / "analyze_turnover.py").read_text(encoding="utf-8")


class FakeSeries:
    def __init__(self, closes, opens=None):
        self.close = list(closes)
        self.open = list(opens if opens is not None else closes)
        self.pos = {i: i for i in range(len(self.close))}


# =====================================================================
# A) 가격/수익
# =====================================================================
panel = {"A": FakeSeries([100.0] * 6, [100, 110, 120, 130, 140, 150])}
check("A1) 시가에 사서 시가에 판다",
      abs(M.trade_ret(panel, "A", 0, 1) - 10.0) < 1e-9)
check("A2) 없는 날은 None", M.trade_ret(panel, "A", 0, 99) is None)
check("A3) 종가도 읽을 수 있다",
      abs(M.price(panel, "A", 0, "close") - 100.0) < 1e-9)

# =====================================================================
# B) 낙폭 / 연환산
# =====================================================================
check("B1) 계속 오르면 낙폭 0", M.mdd([1, 1.1, 1.2]) == 0.0)
check("B2) 반토막이면 -50%", abs(M.mdd([1, 2, 1]) - (-50.0)) < 1e-9)
check("B3) 회복해도 최악을 기억", abs(M.mdd([1, 2, 1, 3]) - (-50.0)) < 1e-9)
cv = [M.CAPITAL] * M.DAYS_PER_YEAR + [M.CAPITAL * 2]
check("B4) 1년에 2배면 연환산이 100% 근처",
      90 < M.annualized(cv) < 110, f"{M.annualized(cv):.1f}%")
check("B5) 제자리면 연환산 0",
      abs(M.annualized([M.CAPITAL] * 500)) < 1e-9)

# =====================================================================
# C) 교체비율 - 이 파일의 핵심 측정
# =====================================================================
_real = (M.S.universe_at, M.S.factor_score)
try:
    codes = [f"{i:06d}" for i in range(30)]
    fpanel = {c: FakeSeries([100.0] * 400) for c in codes}
    M.S.universe_at = lambda p, di, size, mp: list(codes)
    fdates = [f"d{i:04d}" for i in range(400)]

    # 아무것도 안 바뀌는 경우
    M.S.factor_score = lambda p, c, di, kind: float(int(c))
    avg, frac, cnt = M.turnover(fdates, fpanel, 20)
    check("C1) 종목이 안 바뀌면 교체비율 0",
          avg == 0.0 and frac == 0.0 and cnt > 5,
          f"평균 {avg}개, 비율 {frac}, 회차 {cnt}")

    # 매 회차 전부 바뀌는 경우 (순위를 10칸씩 돌린다)
    M.S.factor_score = lambda p, c, di, kind: float(
        (int(c) + (di // 20) * 10) % 30)
    avg2, frac2, _c2 = M.turnover(fdates, fpanel, 20)
    check("C2) 전부 바뀌면 교체비율 1.0",
          abs(frac2 - 1.0) < 1e-9, f"평균 {avg2}개, 비율 {frac2}")
    check("C3) 교체비율 = 새 종목 수 / 종목 수",
          "len(set(p) - set(prev))" in src and "avg / PICK" in src)

    # ------------------------------------------------------------------
    # D) 수수료 - 부분교체가 공짜로 유리해지지 않는지
    # ------------------------------------------------------------------
    # 값이 안 움직이는 세계: 수수료만 남는다
    M.S.factor_score = lambda p, c, di, kind: float(int(c))   # 안 바뀜
    cv_f, fee_f = M.run(fdates, fpanel, 20, "full", 0)
    cv_p, fee_p = M.run(fdates, fpanel, 20, "partial", 0)
    check("D1) 종목이 안 바뀌면 부분교체는 첫 매수 수수료만 낸다",
          fee_p > 0 and fee_p < fee_f / 3,
          f"부분 {fee_p:,.0f}원 vs 전량 {fee_f:,.0f}원")
    check("D2) 그때 부분교체 자산이 전량교체보다 많다",
          cv_p[-1] > cv_f[-1],
          f"{cv_p[-1]:,.0f} vs {cv_f[-1]:,.0f}")

    # 전부 바뀌는 세계: 둘이 같아야 한다 (부분교체가 면제받을 게 없다)
    M.S.factor_score = lambda p, c, di, kind: float(
        (int(c) + (di // 20) * 10) % 30)
    cv_f2, fee_f2 = M.run(fdates, fpanel, 20, "full", 0)
    cv_p2, fee_p2 = M.run(fdates, fpanel, 20, "partial", 0)
    check("D3) 전부 바뀌면 부분교체도 수수료를 똑같이 낸다 (면제 없음)",
          abs(fee_p2 - fee_f2) / max(fee_f2, 1) < 0.05,
          f"부분 {fee_p2:,.0f}원 vs 전량 {fee_f2:,.0f}원")
    check("D4) 그때 자산도 거의 같다",
          abs(cv_p2[-1] - cv_f2[-1]) / M.CAPITAL < 0.02,
          f"{cv_p2[-1]:,.0f} vs {cv_f2[-1]:,.0f}")

    # 절반만 바뀌는 세계: 부분교체 수수료가 전량의 절반 근처
    M.S.factor_score = lambda p, c, di, kind: float(
        (int(c) + (di // 20) * 5) % 30)
    _cv3, fee_f3 = M.run(fdates, fpanel, 20, "full", 0)
    _cv4, fee_p3 = M.run(fdates, fpanel, 20, "partial", 0)
    check("D5) 절반 바뀌면 부분교체 수수료가 전량보다 확실히 적다",
          fee_p3 < fee_f3 * 0.8,
          f"부분 {fee_p3:,.0f}원 vs 전량 {fee_f3:,.0f}원 "
          f"({fee_p3/fee_f3*100:.0f}%)")

    # 예산 초과 금지
    M.S.factor_score = lambda p, c, di, kind: float(int(c))
    for mode in ("full", "partial"):
        cvx, _fx = M.run(fdates, fpanel, 20, mode, 0)
        check(f"D6) [{mode}] 자산이 음수가 되지 않는다",
              all(v >= 0 for v in cvx))
    check("D7) 부분교체는 빠진 종목만 판다",
          "for c in [c for c in hold if c not in new]" in src)
    check("D8) 부분교체는 새로 들어온 종목만 산다",
          "add = [c for c in new if c not in hold]" in src)
    check("D9) 남은 종목은 그대로 들고 간다",
          "keep = {c: q for c, q in hold.items() if c in new}" in src)

    # ------------------------------------------------------------------
    # E) 반기 양방향
    # ------------------------------------------------------------------
    rows = M.split_half(fdates, fpanel, cands=[(20, "partial"), (20, "full")])
    check("E1) 반기 양방향이 두 구간 값을 돌려준다",
          len(rows) == 2 and all(len(r) == 4 for r in rows),
          f"{rows}")
    check("E2) 기간을 실제로 반으로 가른다", "mid = base + (n - base) // 2" in src)
    check("E3) 각 구간에서 시작일을 여러 개 쓴다",
          "for s0 in [lo + k * 17 for k in range(5)]" in src)
finally:
    M.S.universe_at, M.S.factor_score = _real

# =====================================================================
# F) 미래 정보 / 안전
# =====================================================================
check("F1) 종목 선정은 그 시점 정보로만 한다",
      'S.factor_score(panel, c, di, "low_vol")' in src
      and "S.universe_at(panel, di" in src)
check("F2) 수수료는 편도 = 왕복/2 다",
      abs(M.FEE_ONE_WAY - M.S.FEE_ROUND_TRIP_PCT / 2 / 100) < 1e-15)
check("F3) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"F4) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# G) 문서 - 확실한 것과 아닌 것을 갈랐는지
# =====================================================================
check("G1) 틀의 식이 적혀 있다", "하루당엣지(H) x H" in src and "교체비율" in src)
check("G2) 앞에서 교체비율을 1.0 으로 뒀던 게 틀렸다고 밝힌다",
      "전량 교체)으로" in src and "그게 틀렸다" in src)
check("G3) 엣지가 40일에서 포화된다는 결과가 있다",
      "+2.690%" in src and "포화" in src)
check("G4) 하루당 엣지가 서서히 닳는다고 정정한다",
      "서서히 닳는다" in src and "0.0298%" in src)
check("G5) 20일에도 3.3종목만 바뀐다는 핵심 수치가 있다",
      "3.3종목" in src)
check("G6) 수수료를 3배 과다 계상했다고 인정한다",
      "3배 과다 계상" in src)
check("G7) 실제 시뮬로 6/6 주기에서 이긴 것을 밝힌다",
      "여섯 주기 전부에서" in src)
check("G8) 비중조정이 전량교체와 같아진다는 발견이 있다",
      "정확히 같은 값" in src and "비중을 맞추려면" in src)
check("G9) 반기 양방향 1위가 다르다는 것을 밝힌다",
      "1위가 완전히 다르다" in src)
check("G10) 부분교체는 양쪽 반에서 이겼다고 밝힌다",
      "양쪽 반 모두에서 이긴다" in src)
check("G11) 주기는 못 가린다고 분명히 말한다",
      "주기는 이 데이터로 못 가린다" in src)
check("G12) 전반부/후반부가 10배 차이라는 경고가 있다",
      "10배 차이" in src and "+55%" in src)
check("G13) 부분교체가 과최적화가 아닌 이유를 설명한다",
      "낭비를 없앤 것" in src and "과최적화가 아니다" in src)
check("G14) 앞 파일의 '길수록 유리' 를 좁힌다고 밝힌다",
      "analyze_short_term.py" in src and "좁혀야 한다" in src)
check("G15) 1~2일은 여전히 안 된다고 남긴다",
      "1일~2일은 여전히 안 된다" in src)
check("G16) 스프레드 미반영 경고가 있다", "스프레드" in src)
check("G17) 실무 결론이 주기 20~60일 + 부분교체다",
      "20~60일 중 아무거나" in src and "부분교체" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
