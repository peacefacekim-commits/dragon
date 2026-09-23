"""analyze_original.py 검증 - 사용자 방식을 진짜로 재현했는가.

(2026-09-21 신설) 이 파일의 위험은 **사용자 방식을 일부러 약하게
만들어놓고 지는 것을 보이는 것** 이다. 그러면 결론이 공짜로 나온다.
그래서 여기서는 재현이 정확한지를 집중 검사한다.

특히 앞서 임시 스크립트에서 한 번 틀렸다. 주기를 1일로 두니 교체가
매일 일어나서 익절/손절이 발동할 틈이 아예 없었고, 매도 0건으로 '규칙
있음' 과 '없음' 이 같은 숫자가 나왔다. 규칙을 안 잰 것을 '차이 없음'
으로 읽을 뻔했다. D 절이 그 재발을 막는다.

실행:
  python tests/test_analyze_original.py
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


import analyze_original as M  # noqa: E402

src = (REPO_ROOT / "analyze_original.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes, opens=None):
        self.close = list(closes)
        self.open = list(opens if opens is not None else closes)
        self.pos = {i: i for i in range(len(closes))}


N = 400
dates = list(range(N))
rising = {"a": FakeSeries([100.0 * (1.01 ** i) for i in range(N)])}
rising.update({c: FakeSeries([100.0] * N) for c in ("b", "c", "d", "e", "f")})
order = {di: ["a", "b", "c", "d", "e", "f"] for di in range(N)}
falling = {c: FakeSeries([100.0 * (0.99 ** i) for i in range(N)])
           for c in ("a", "b")}
forder = {di: ["a", "b"] for di in range(N)}

# =====================================================================
# A) 사용자 방식의 세 조각이 다 들어 있는가
# =====================================================================
check("A1) 5종목을 잰다", 5 in M.PICKS, str(M.PICKS))
check("A2) 10종목과 견준다", 10 in M.PICKS)
check("A3) 짧은 주기를 쓴다", max(M.PERIODS) <= 20, str(M.PERIODS))
check("A4) '없음' 기준선이 있다", any(t == "없음" for t, _a, _b in M.RULES))
check("A5) 익절과 손절을 같이 건다",
      any(a is not None and b is not None for _t, a, b in M.RULES))
check("A6) 문턱을 여러 개 본다", len(M.RULES) >= 4)
check("A7) 세 조각이 붙어 있었다고 밝힌다",
      "세 가지가 붙어 있었다" in flat)
check("A8) 지금까지 따로만 쟀다고 밝힌다", "따로따로만 쟀다" in flat)

# =====================================================================
# B) 익절/손절이 실제로 동작하는가
# =====================================================================
_c, n_tp = M.run(dates, rising, order, 0, 20, 6, tp=5, sl=None)
check("B1) 오르면 익절이 걸린다", n_tp > 0, f"{n_tp}건")
_c, n_sl = M.run(dates, falling, forder, 0, 20, 2, tp=None, sl=5)
check("B2) 내리면 손절이 걸린다", n_sl > 0, f"{n_sl}건")
_c, n_none = M.run(dates, rising, order, 0, 20, 6)
check("B3) 규칙이 없으면 중간 매도가 0건", n_none == 0)
_c, n_far = M.run(dates, rising, order, 0, 20, 6, tp=100000, sl=100000)
check("B4) 닿을 수 없는 문턱이면 발동 안 한다", n_far == 0)
# 문턱이 느슨해질수록 매도가 줄어야 한다. 하루 1% 오르는 종목이라
# 20일 주기 안에서 +5%/+15% 는 닿고 +30% 는 못 닿는다.
_counts = [M.run(dates, rising, order, 0, 20, 6, tp=t)[1] for t in (5, 15, 30)]
check("B5) 문턱이 느슨할수록 덜 판다",
      _counts[0] >= _counts[1] >= _counts[2] and _counts[0] > _counts[2],
      f"+5%:{_counts[0]} +15%:{_counts[1]} +30%:{_counts[2]}")

# =====================================================================
# C) 조건이 같은가 (한쪽에 유리하게 주지 않았는가)
# =====================================================================
check("C1) 모든 칸이 같은 run() 을 쓴다", src.count("def run(") == 1)
check("C2) 시작일을 만드는 자리가 하나다", src.count("def _starts(") == 1)
check("C3) 자본이 공용 상수", M.CAPITAL == 2_000_000)
check("C4) 수수료가 공용 상수", M.FEE_ONE_WAY == M.E.FEE_ONE_WAY)
check("C5) 매도 수수료를 판다는 쪽에서 뗀다", "(1 - FEE_ONE_WAY)" in src)
_flat = {c: FakeSeries([1000.0] * N) for c in ("a", "b")}
_curve, _ = M.run(dates, _flat, {di: ["a", "b"] for di in range(N)}, 0, 20, 2)
check("C6) 값이 안 변해도 수수료가 붙는다", _curve[-1] < M.CAPITAL,
      f"{_curve[-1]:,.0f}원")
c1, s1 = M.run(dates, rising, order, 0, 20, 6, tp=10, sl=5)
c2, s2 = M.run(dates, rising, order, 0, 20, 6, tp=10, sl=5)
check("C7) 같은 입력이면 같은 결과 (무작위성 없음)", c1 == c2 and s1 == s2)
check("C8) 종목 선정이 그 시점 정보로만 한다", "K.ranks(dates, panel" in src)
check("C9) 선정을 저변동으로 고정했다고 밝힌다",
      "선정을 저변동으로 고정" in flat or "저변동 선정 고정" in src)

# =====================================================================
# D) 지난번 실수 재발 방지 - 규칙이 발동할 틈이 있는가
# =====================================================================
check("D1) 익절/손절을 교체일과 무관하게 본다 (elif 가 아니다)",
      "if tp is not None or sl is not None:" in src
      and "elif tp is not None" not in src)
check("D2) 왜 그렇게 했는지 적어뒀다",
      "규칙이 발동할 틈이 없어지는데" in flat)
# 주기 1일이어도 규칙이 발동해야 한다 (예전엔 0건이었다)
_c, n_daily = M.run(dates, rising, order, 0, 1, 6, tp=5, sl=5)
check("D3) 주기가 1일이어도 규칙이 발동한다", n_daily > 0, f"{n_daily}건")

# =====================================================================
# E) 판정 함수
# =====================================================================
fake = {(10, 20, "없음"): (20.0, -16.0, 0),
        (10, 20, "익절+5 손절-5"): (8.0, -13.0, 340),
        (10, 20, "익절+10 손절-5"): (12.0, -14.0, 247),
        (10, 20, "익절+10 손절-10"): (17.0, -15.0, 161)}
check("E1) 전부 지면 3/3", M.rules_lost(fake) == (3, 3),
      str(M.rules_lost(fake)))
fake2 = dict(fake)
fake2[(10, 20, "익절+10 손절-10")] = (25.0, -15.0, 161)
check("E2) 하나가 이기면 2/3", M.rules_lost(fake2) == (2, 3),
      str(M.rules_lost(fake2)))
check("E3) 왜 '전부 지는지' 가 중요한지 적어뒀다",
      "문턱을 잘 고르면 된다" in flat)

# =====================================================================
# F) 문서 - 결론
# =====================================================================
for tok in ("14.1", "22.4", "16.5", "20.2", "8.0", "17.7", "-18.9", "-16.2"):
    check(f"F) 결과표에 {tok} 가 있다", tok in src)
check("F1) 12/12 전부 졌다고 밝힌다", "12번 중 12번" in flat)
check("F2) 파는 횟수에 비례해 나빠진다고 짚는다",
      "파는 횟수에 비례해서 나빠진다" in flat)
check("F3) 문턱 고르기 문제가 아니라고 못박는다",
      "파는 행위 자체가 손해" in flat)
check("F4) 손절이 낙폭도 못 줄였다고 밝힌다",
      "-18.3% -> -18.5%" in flat)
check("F5) 낙폭이 준 것은 투자를 덜 한 대가라고 짚는다",
      "투자를 덜 한 것" in flat)
check("F6) 5종목이 10종목에 진다고 밝힌다", "5종목은 10종목에 전부 진다" in flat)
check("F7) 5종목이 낙폭도 나쁘다고 밝힌다", "맞교환이 아니라" in flat)
check("F8) 답이 '절반만' 이라고 정리한다", "절반만" in flat)
check("F9) 맞는 부분을 인정한다",
      "선정이 지배적이라는 진단은 옳다" in flat)
check("F10) 자주 거래하는 것 자체는 괜찮다고 인정한다",
      "자주 거래하는 것 자체는 치명적이지 않다" in flat)
check("F11) 무엇을 바꿨어야 하는지 한 줄로 정리한다",
      "파는 규칙을 빼고, 종목 수를 늘려야" in flat)
check("F12) 장중 10분 매매는 못 잰다고 밝힌다",
      "장중 10분 매매는 여기서 못 잰다" in flat and "일봉" in flat)
check("F13) 장중은 따로 쟀다고 잇는다", "analyze_intraday.py" in src)
check("F14) 익절/손절을 더 훑을 이유가 없다고 밝힌다",
      "analyze_stops.py" in src and "전부 졌다" in flat)
check("F15) 2021~2026 한계를 밝힌다", "2021~2026" in src)
check("F16) 다중검정 칸수를 적었다", "16칸" in flat)
check("F17) 채택한 게 없다고 밝힌다", "채택한 것은 없다" in flat)
check("F18) 사용자 질문을 그대로 적어뒀다", "투자종목만 잘 고른다면" in flat)

# =====================================================================
# G) 안전
# =====================================================================
check("G1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"G2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
