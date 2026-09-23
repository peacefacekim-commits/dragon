"""analyze_intraday.py 검증 - 장중 되돌림을 공평하게 재는지.

(2026-09-21 신설) 결론이 '안 된다' 쪽이므로, 규칙에 불리하게 계산하지
않았는지가 핵심이다. 불리하게 기울이면 결론이 공짜로 나온다.

지켜야 하는 것
  1) 미래 정보 금지. 저가가 선을 찍었을 때만 산다. 고가는 매수에 안 쓴다.
  2) 수수료를 왕복 한 번만 문다.
  3) 대조군(조건 없이 시가매수-종가매도)이 있어야 한다. 없으면 '빠질 때
     산다' 가 일을 했는지 그냥 하루 들고 있어서 난 결과인지 모른다.
  4) 대조군을 이기는 것과 실제로 쓸 수 있는 것을 구별한다.
  5) 국면은 '그날 올랐나' 가 아니라 60일 수익률이어야 한다.
  6) 유리한 가정(스프레드 없음)을 쓴 사실을 밝혀야 한다.

실행:
  python tests/test_analyze_intraday.py
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


import analyze_intraday as M  # noqa: E402

src = (REPO_ROOT / "analyze_intraday.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, opens, closes):
        self.open = list(opens)
        self.close = list(closes)
        self.pos = {i: i for i in range(len(closes))}


# =====================================================================
# A) 매수 조건 - 저가가 선을 찍었을 때만
# =====================================================================
panel = {"A": FakeSeries([100.0] * 5, [102.0, 98.0, 100.0, 100.0, 100.0])}
# di=0: 시가 100, 종가 102. 저가 98 -> -1%, -2% 선을 찍음. -3% 는 안 찍음.
hl = {(0, "A"): (103.0, 98.0), (1, "A"): (101.0, 99.5)}

r1 = M.dip_trade(panel, hl, "A", 0, 1)
check("A1) 저가가 -1% 선을 찍었으면 산다",
      r1 is not None and abs(r1 - ((102.0 / 99.0 - 1) * 100 - M.FEE)) < 1e-9,
      f"{r1}")
check("A2) -2% 선도 찍었으므로 산다", M.dip_trade(panel, hl, "A", 0, 2) is not None)
check("A3) -3% 선은 안 찍었으므로 안 산다",
      M.dip_trade(panel, hl, "A", 0, 3) is None)
check("A4) 저가가 얕으면 안 산다 (di=1, 저가 99.5 는 -1% 선 99 위)",
      M.dip_trade(panel, hl, "A", 1, 1) is None)
check("A5) 고저 자료가 없으면 안 산다",
      M.dip_trade(panel, hl, "A", 2, 1) is None)
check("A6) 매수가는 선 가격이다 (저가가 아니라)",
      "line = op * (1 - dip_pct / 100)" in src and "cl / line" in src)
check("A7) 고가는 매수 판정에 안 쓴다 (v[1] 만 본다)",
      "if v[1] > line" in src and "v[0]" not in src.split("def dip_trade")[1].split("def ")[0])

# 이익이 나는 날과 손해 나는 날 둘 다 잡히는지
panel2 = {"B": FakeSeries([100.0], [95.0])}
hl2 = {(0, "B"): (100.0, 94.0)}
loss = M.dip_trade(panel2, hl2, "B", 0, 1)
check("A8) 빠진 뒤 더 빠지면 손해로 잡힌다", loss is not None and loss < 0,
      f"{loss:.3f}%")

# =====================================================================
# B) 수수료
# =====================================================================
check("B1) 왕복 수수료 상수를 그대로 쓴다",
      abs(M.FEE - M.S.FEE_ROUND_TRIP_PCT) < 1e-12)
check("B2) 매수-종가 한 번에 왕복 한 번만 뺀다",
      src.count("- FEE") == 2, f"{src.count('- FEE')}곳 (dip_trade, open_to_close)")
check("B3) 총수익으로 되돌릴 수 있다 (신호 크기를 보려고)",
      abs(M.gross(-0.074) - (-0.074 + M.FEE)) < 1e-12)
check("B4) 총수익이 순수익보다 항상 크다", M.gross(0.0) > 0.0)

# 가격이 그대로면 수수료만큼만 손해여야 한다
flat_p = {"C": FakeSeries([100.0], [99.0])}
flat_hl = {(0, "C"): (100.0, 99.0)}
z = M.dip_trade(flat_p, flat_hl, "C", 0, 1)
check("B5) -1% 에 사서 -1% 에 팔면 딱 수수료만큼 손해",
      z is not None and abs(z + M.FEE) < 1e-9, f"{z:.4f}")

# =====================================================================
# C) 대조군 - 없으면 규칙이 일했는지 모른다
# =====================================================================
check("C1) 대조군 함수가 있다", callable(M.open_to_close))
c = M.open_to_close(panel, "A", 0)
check("C2) 대조군은 시가매수-종가매도다",
      abs(c - ((102.0 / 100.0 - 1) * 100 - M.FEE)) < 1e-9, f"{c}")
check("C3) 대조군에도 같은 수수료를 문다 (한쪽만 깎으면 비교가 틀어진다)",
      "- FEE" in src.split("def open_to_close")[1].split("def ")[0])
check("C4) 왜 대조군이 필요한지 적어뒀다",
      "그냥 하루 들고 있어서 난 결과인지 구별할 수 없다" in flat)
check("C5) 결과표에 대조군 줄이 있다", '"대조군"' in src)

# =====================================================================
# D) 이기는 것과 쓸 수 있는 것을 구별
# =====================================================================
check("D1) 대조군을 이겼는지 판정한다",
      M.beats_control(-0.074, -0.215) is True)
check("D2) 대조군보다 나빠도 이겼다고 안 한다",
      M.beats_control(-0.300, -0.215) is False)
check("D3) 대조군을 이겨도 마이너스면 못 쓴다 (실제로 겪은 칸)",
      M.beats_control(-0.074, -0.215) is True and M.usable(-0.074) is False)
check("D4) 양수라야 쓸 수 있다", M.usable(0.001) is True)
check("D5) 0 은 못 쓴다", M.usable(0.0) is False)

# =====================================================================
# E) 국면 - 하루 부호가 아니라 60일
# =====================================================================
check("E1) 국면 기간이 60일이다", M.REGIME_BACK == 60)
n = 80
down = {f"d{i}": FakeSeries([100.0] * n, [100.0 - j * 0.5 for j in range(n)])
        for i in range(3)}
up = {f"u{i}": FakeSeries([100.0] * n, [100.0 + j * 0.5 for j in range(n)])
      for i in range(3)}
check("E2) 내려온 구간을 하락으로 본다",
      M.regime_at(down, list(down), 70) == "하락")
check("E3) 올라온 구간을 상승으로 본다",
      M.regime_at(up, list(up), 70) == "상승")
check("E4) 자료가 없으면 None", M.regime_at({}, [], 70) is None)
check("E5) 하루 부호로 가르지 않는다고 적어뒀다",
      "그날 올랐나 내렸나가 아니라" in flat)

# =====================================================================
# F) 문서 - 결론과 한계를 숨기지 않는가
# =====================================================================
check("F1) 10~20분 봉이 없다고 밝힌다", "10~20분 봉이 없다" in src)
check("F2) 이 계산이 10분 거래의 상한이라고 설명한다",
      "10분 거래 아이디어의 **상한**" in src or "10분 거래 아이디어의 상한" in flat)
check("F3) 왜 상한인지 이유를 적었다",
      "되돌림을 덜 먹고 수수료는 똑같이 낸다" in flat)
check("F4) 되돌림이 진짜 있다고 인정한다 (불리한 쪽으로 안 기울임)",
      "되돌림은 진짜 있다" in flat and "0.159%p" in src)
check("F5) 그런데 거의 전부 마이너스라고 밝힌다", "거의 전부 마이너스다" in flat)
check("F6) 총수익 규모를 적었다 (신호는 있고 수수료를 못 넘는다)",
      "+0.13 ~ +0.19%" in src)
check("F7) 1일 보유와 같은 구조라고 잇는다",
      "1일 보유 때와 똑같은 구조" in flat or "1일 보유 때와 같은 구조" in flat)
check("F8) 사용자 전제(하락장)와 반대 결과라고 밝힌다",
      "사용자의 전제와 반대다" in flat)
check("F9) 하락국면이 더 나쁘다는 숫자를 적었다",
      "-0.444" in src and "+0.086" in src)
check("F10) 양수 칸이 상승국면이고 표본이 적다고 밝힌다",
      "50일뿐이고" in flat and "상승국면" in src)
check("F10b) 그래서 채택하지 않는다고 못 박았다", "채택하지 않는다" in flat)
check("F11) 스프레드를 안 넣어 규칙에 유리하다고 밝힌다",
      "규칙에 유리하게" in flat and "스프레드" in src)
check("F12) 변동폭의 6~9%만 잡으면 되므로 '원천봉쇄' 는 틀린 설명이라고 밝힌다",
      "6~9%" in src and "틀린 설명이다" in flat)
check("F13) 일중 변동폭이 국면에 따라 안 변한다는 것도 적었다",
      "2.39" in src and "2.25" in src and "거의 안 변한다" in flat)
check("F13b) 변동폭 계산도 모듈 안에 있다 (재현 가능)",
      callable(M.day_range) and callable(M.capture_needed))
check("F13c) 숫자를 두 번 틀린 경위를 남겼다",
      "519/632 에서 393/758" in flat and "40종목, 모듈 60종목" in flat)
check("F13d) 모든 숫자가 재현된다고 밝힌다",
      "python analyze_intraday.py 로 재현된다" in flat)
check("F14) 다중검정 누적을 세어서 적었다", "16칸" in src and "90가지" in src)

# 변동폭 -> 필요 포착률 계산
check("F15) 변동폭 2.39% 면 8.8% 를 잡아야 한다",
      abs(M.capture_needed(2.39) - 8.79) < 0.05, f"{M.capture_needed(2.39):.2f}")
check("F16) 변동폭이 크면 덜 잡아도 된다",
      M.capture_needed(5.0) < M.capture_needed(2.0))
check("F17) 변동폭 0 이면 무한 (못 넘는다)",
      M.capture_needed(0) == float("inf"))
check("F18) 이 값이 작다고 되는 게 아니라고 적어뒀다",
      "되면 되겠네' 가 아니다" in flat)

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
