"""analyze_stops.py 검증 - 손절/익절 체결을 유리하게 잡지 않았나.

(2026-09-19 신설) 사용자: "언제 팔아야할지 장중 몇번 신호를 잡아야하는지"

이 파일의 결론은 '손절도 익절도 넣지 마라' 다. 그런데 체결을 손절/익절에
유리하게 잡으면 결론이 거꾸로 나올 수 있으므로, 거기를 집중 검사한다.

지켜야 하는 것
  1) 갭이 나면 손절선이 아니라 시가에 체결돼야 한다. 선 가격으로
     잡아주면 손절이 실제보다 좋아 보인다. (현실은 갭 체결이다)
  2) 손절선은 저가로, 익절선은 고가로 판정해야 한다. 반대로 하면
     아무것도 안 걸린다.
  3) 손절이 익절보다 먼저 판정돼야 한다 (같은 날 둘 다 닿으면 보수적).
  4) 손절/익절도 수수료를 낸다.
  5) 검증(반기 양방향) 없이 결론을 내지 않는다 - 12가지를 훑었다.
  6) 장중 신호는 분봉이 없어 검증 불가라는 사실을 밝혀야 한다.

실행:
  python tests/test_analyze_stops.py
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


import analyze_stops as M  # noqa: E402

src = (REPO_ROOT / "analyze_stops.py").read_text(encoding="utf-8")

B = 10_000.0          # 매수가 1만원

# =====================================================================
# A) 체결가 - 여기가 결론을 뒤집을 수 있는 자리다
# =====================================================================
# 손절 -10% => 9,000원. 저가가 8,900 이면 9,000 에 체결
r = M.exit_price(B, op=9_800, high=9_900, low=8_900, stop_pct=-10, take_pct=None)
check("A1) 저가가 손절선을 뚫으면 손절선에 체결",
      r == (9_000.0, "손절"), f"{r}")

# 시가가 이미 8,500 으로 갭하락 => 9,000 아니라 8,500 에 체결 (불리하게)
r = M.exit_price(B, op=8_500, high=8_700, low=8_400, stop_pct=-10, take_pct=None)
check("A2) 갭하락이면 손절선이 아니라 시가에 체결 (유리하게 안 잡음)",
      r == (8_500.0, "손절"), f"{r}")
check("A2b) 그래서 손절이 과대평가되지 않는다",
      r[0] < 9_000.0, f"체결 {r[0]:,.0f} < 손절선 9,000")

# 저가가 손절선에 안 닿으면 아무것도 안 걸림
r = M.exit_price(B, op=9_800, high=9_900, low=9_100, stop_pct=-10, take_pct=None)
check("A3) 손절선에 안 닿으면 안 팔린다", r is None, f"{r}")

# 익절 +20% => 12,000. 고가가 12,500 이면 12,000 에 체결
r = M.exit_price(B, op=10_500, high=12_500, low=10_400, stop_pct=None, take_pct=20)
check("A4) 고가가 익절선을 넘으면 익절선에 체결",
      r == (12_000.0, "익절"), f"{r}")

# 시가가 이미 13,000 으로 갭상승 => 13,000 에 체결 (이건 유리한 쪽)
r = M.exit_price(B, op=13_000, high=13_200, low=12_800, stop_pct=None, take_pct=20)
check("A5) 갭상승이면 시가에 체결", r == (13_000.0, "익절"), f"{r}")

# 같은 날 손절/익절 둘 다 닿으면 손절이 먼저 (보수적)
r = M.exit_price(B, op=10_000, high=12_500, low=8_500,
                 stop_pct=-10, take_pct=20)
check("A6) 둘 다 닿으면 손절이 먼저 판정된다 (보수적)",
      r is not None and r[1] == "손절", f"{r}")
check("A6b) 코드에서 손절을 먼저 본다",
      src.index("if stop_pct is not None:") < src.index("if take_pct is not None:"))

# 손절/익절 둘 다 None 이면 아무것도 안 걸림
check("A7) 규칙이 없으면 안 팔린다",
      M.exit_price(B, 9_000, 9_100, 8_000, None, None) is None)

# 손절선 정확히 닿는 경계
r = M.exit_price(B, op=9_500, high=9_600, low=9_000.0, stop_pct=-10,
                 take_pct=None)
check("A8) 저가가 손절선과 정확히 같으면 체결된다",
      r == (9_000.0, "손절"), f"{r}")

# =====================================================================
# B) 손익분기 / 수수료 계산
# =====================================================================
check("B1) 거래 한 번이 벌어야 하는 배수 = 수수료 / 하루당엣지",
      abs(M.break_even_trades() - M.FEE_ROUND / M.EDGE_PER_DAY) < 1e-12)
check("B2) 그 값이 2.3배 근처다",
      abs(M.break_even_trades() - 2.258) < 0.01,
      f"{M.break_even_trades():.2f}배")
check("B3) 하루 1번 확인 발동 20% 면 연 10.3%",
      abs(M.extra_fee_per_year(1, 0.20) - 10.332) < 0.01,
      f"{M.extra_fee_per_year(1, 0.20):.2f}%")
check("B4) 확인 횟수가 3배면 수수료도 3배",
      abs(M.extra_fee_per_year(3, 0.2) - 3 * M.extra_fee_per_year(1, 0.2)) < 1e-9)
check("B5) 발동률 0 이면 수수료 0", M.extra_fee_per_year(10, 0.0) == 0.0)
check("B6) 하루 3번 20% 발동이 연 31% 라 기대수익의 두 배다",
      M.extra_fee_per_year(3, 0.2) > 30, f"{M.extra_fee_per_year(3, 0.2):.1f}%")

# =====================================================================
# C) 낙폭 / 연환산
# =====================================================================
check("C1) 계속 오르면 낙폭 0", M.mdd([1, 1.1, 1.2]) == 0.0)
check("C2) 반토막이면 -50%", abs(M.mdd([1, 2, 1]) - (-50.0)) < 1e-9)
cv = [M.CAPITAL] * M.DAYS_PER_YEAR + [M.CAPITAL * 2]
check("C3) 1년에 2배면 연환산 100% 근처", 90 < M.annualized(cv) < 110)

# =====================================================================
# D) 실제 돌려보기 - 손절이 수수료를 내는지
# =====================================================================
class FakeSeries:
    def __init__(self, closes, opens=None):
        self.close = list(closes)
        self.open = list(opens if opens is not None else closes)
        self.pos = {i: i for i in range(len(self.close))}


_real = (M.S.universe_at, M.S.factor_score)
try:
    codes = [f"{i:06d}" for i in range(20)]
    n = 200
    fdates = [f"d{i:04d}" for i in range(n)]
    # 값이 안 움직이는 세계 -> 수수료만 남는다
    fpanel = {c: FakeSeries([100.0] * n) for c in codes}
    M.S.universe_at = lambda p, di, size, mp: list(codes)
    M.S.factor_score = lambda p, c, di, kind: float(int(c))

    # 손절이 안 걸리는 고가/저가 (가격이 안 움직임)
    hl_flat = {(di, c): (100.0, 100.0) for di in range(n) for c in codes}
    cv0, fee0, ns0, nt0 = M.run(fdates, fpanel, hl_flat, None, None, 0)
    check("D1) 규칙 없으면 손절/익절 횟수 0",
          ns0 == 0 and nt0 == 0, f"손절 {ns0}, 익절 {nt0}")

    # 저가를 손절선 아래로 만들어 손절이 걸리게 한다
    hl_drop = {(di, c): (100.0, 80.0) for di in range(n) for c in codes}
    cv1, fee1, ns1, nt1 = M.run(fdates, fpanel, hl_drop, -10, None, 0)
    check("D2) 저가가 손절선을 뚫으면 손절이 걸린다", ns1 > 0, f"{ns1}회")
    check("D3) 손절이 걸리면 수수료가 더 나간다", fee1 > fee0,
          f"{fee1:,.0f}원 vs {fee0:,.0f}원")
    check("D4) 손절 있는 쪽 자산이 더 적다 (값이 안 움직이는 세계)",
          cv1[-1] < cv0[-1], f"{cv1[-1]:,.0f} vs {cv0[-1]:,.0f}")
    check("D5) 익절 횟수는 0 이다 (익절 규칙을 안 줬다)", nt1 == 0)

    # 고가를 익절선 위로 만들어 익절이 걸리게 한다
    hl_up = {(di, c): (130.0, 100.0) for di in range(n) for c in codes}
    _cv2, _f2, ns2, nt2 = M.run(fdates, fpanel, hl_up, None, 20, 0)
    check("D6) 고가가 익절선을 넘으면 익절이 걸린다", nt2 > 0, f"{nt2}회")
    check("D7) 그때 손절 횟수는 0", ns2 == 0)

    # upto 로 기간을 자를 수 있어야 한다 (반기 양방향에 쓴다)
    cv_half, _f, _s, _t = M.run(fdates, fpanel, hl_flat, None, None, 0,
                                upto=100)
    check("D8) upto 로 기간을 자른다 (반기 검증용)",
          len(cv_half) == 100, f"{len(cv_half)}일")
    check("D9) 자른 쪽이 전체보다 짧다", len(cv_half) < len(cv0))
finally:
    M.S.universe_at, M.S.factor_score = _real

# =====================================================================
# E) 미래 정보 / 안전
# =====================================================================
check("E1) 종목 선정은 그 시점 정보로만 한다",
      'S.factor_score(panel, c, di, "low_vol")' in src
      and "S.universe_at(panel, di" in src)
check("E2) 부분교체를 쓴다 (겹치는 종목 유지)",
      "keep = {c: q for c, q in hold.items() if c in new}" in src)
check("E3) 매수가를 기록해 손절 기준으로 쓴다", "basis.setdefault" in src)
check("E4) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"E5) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# F) 문서 - 검증 없이 결론 내지 않았나
# =====================================================================
check("F1) 손절이 전부 손해라는 표가 있다",
      "-5.4%p" in src and "-1.2%p" in src)
check("F2) 타이트할수록 나쁘다는 것을 짚는다", "타이트할수록 더 나쁘다" in src)
check("F3) 낙폭도 안 줄었다는 것을 밝힌다",
      "보호를 사는 게 아니라" in src)
check("F4) 익절 +20% 가 전체 기간에선 좋아 보였다고 먼저 밝힌다",
      "+2.0%p" in src)
check("F5) 그 기전이 그럴듯하다는 것도 적었다 (편들기 금지)",
      "그럴듯한 기전도 있다" in src)
check("F6) 그런데 반기 검증에서 뒤집혔다는 결과가 있다",
      "뒤집힌다" in src and "+0.7%p" in src and "-0.8%p" in src)
check("F7) 익절 다섯 수준 전부 실패했다고 밝힌다",
      "다섯 수준 전부" in src)
check("F8) 채택했으면 실수였다고 적었다", "실수였다" in src)
check("F9) 손절이 나쁘다는 것은 검증을 통과했다고 구별한다",
      "일관되게 나쁘다" in src)
check("F10) 최종 결론이 '둘 다 넣지 않는다' 다",
      "손절도 익절도 넣지 않는다" in src)
check("F11) 장중은 분봉이 없어 검증 불가라고 밝힌다",
      "분봉이 없다" in src and "검증이 불가능하다" in src)
check("F12) 신호를 보는 것은 공짜지만 행동이 비용이라고 구별한다",
      "보고 행동할 때" in src)
check("F13) 장중 확인 횟수 = 0번 이라는 결론이 있다",
      "장중 확인 횟수 = 0번" in src)
check("F14) 23가지 타이밍 실패를 근거로 든다",
      "23가지" in src and "z=+0.20" in src and "1.48" in src)
check("F15) 스프레드 미반영이 손절/익절에 관대하다는 것을 밝힌다",
      "스프레드" in src and "관대한" in src)
check("F16) 절대 수준을 기대치로 쓰지 말라는 경고가 있다",
      "절대 수준을 기대치로 쓰면 안 된다" in src)
check("F17) 갭이면 시가 체결이라고 문서에 밝힌다",
      "갭하락했으면 시가에 팔린 것" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
