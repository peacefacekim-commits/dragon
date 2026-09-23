"""대책.py 검증 - 반사실 계산이 공평한가, 유망을 채택으로 안 올렸는가.

(2026-09-22 신설) 이 파일의 위험은 둘이다.

  1) **표본을 안 맞추고 비교하는 것.** 보유기간을 늘리면 일봉이 없는
     거래가 늘어난다. 88건 대 71건 대 43건을 비교하면 차이가 규칙
     때문인지 표본 때문인지 모른다.
  2) **유망을 채택으로 올리는 것.** '규칙 없이 당일 종가' 가 +0.647%
     로 나왔지만 t=1.36 이고 상위 3건을 빼면 +0.072% 다. 이걸 채택하면
     재무에서 2025년 한 해를 채택하는 것과 같은 실수가 된다.

실행:
  python tests/test_대책.py
"""
import pathlib
import statistics as st
import sys
from datetime import datetime

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import importlib  # noqa: E402

M = importlib.import_module("대책")

src = (REPO_ROOT / "대책.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes):
        self.close = list(closes)
        self.open = list(closes)
        self.pos = {i: i for i in range(len(closes))}


# =====================================================================
# A) 반사실 계산 - 실제 매수가를 그대로 쓰는가
# =====================================================================
panel = {"A": FakeSeries([100.0, 110.0, 120.0, 130.0])}
dpos = {"20260101": 0, "20260102": 1}
tr = {"code": "A", "buy": 100.0, "buy_t": datetime(2026, 1, 1, 9, 30)}
check("A1) 당일 종가 (n=0)",
      abs(M.hold_return(panel, dpos, tr, 0) - (0.0 - M.R.FEE_ROUND_TRIP)) < 1e-9,
      f"{M.hold_return(panel, dpos, tr, 0)}")
check("A2) 1거래일 뒤",
      abs(M.hold_return(panel, dpos, tr, 1) - (10.0 - M.R.FEE_ROUND_TRIP)) < 1e-9)
check("A3) 수수료를 뺀다", M.hold_return(panel, dpos, tr, 1) < 10.0)
check("A4) 범위를 넘으면 None", M.hold_return(panel, dpos, tr, 99) is None)
check("A5) 없는 종목이면 None",
      M.hold_return(panel, dpos, {**tr, "code": "Z"}, 0) is None)
check("A6) 매수일이 패널에 없으면 None",
      M.hold_return(panel, {}, tr, 0) is None)
check("A7) 매수가가 0 이면 None",
      M.hold_return(panel, dpos, {**tr, "buy": 0.0}, 0) is None)
check("A8) 매수가를 바꾸지 않는다고 적어뒀다",
      "실제 체결가를 그대로 쓴다" in flat)
check("A9) 왜 그런지 적었다", "질문이 달라진다" in flat)

# =====================================================================
# B) 표본을 맞추는가 - 이 파일의 핵심 1
# =====================================================================
long_panel = {"A": FakeSeries([100.0] * 30), "B": FakeSeries([100.0] * 3)}
d2 = {f"2026010{i}" if i < 10 else f"202601{i}": i for i in range(1, 30)}
d2 = {f"20260{i:03d}": i for i in range(1, 30)}
trs = [{"code": "A", "buy": 100.0, "buy_t": datetime(2026, 1, 1)},
       {"code": "B", "buy": 100.0, "buy_t": datetime(2026, 1, 1)}]
dp = {"20260101": 0}
got = M.matched(long_panel, dp, trs, holds=(0, 5, 10, 20))
check("B1) 20일까지 없는 거래는 뺀다",
      len(got) == 1 and got[0]["code"] == "A", str([t["code"] for t in got]))
check("B2) 짧은 보유만 요구하면 둘 다 남는다",
      len(M.matched(long_panel, dp, trs, holds=(0,))) == 2)
check("B3) 왜 맞추는지 적어뒀다",
      "규칙 때문인지 표본 때문인지 모른다" in flat)
check("B4) 88/71/43 을 그냥 비교하면 안 된다고 적었다",
      "88건 대 71건 대 43건" in flat)

# =====================================================================
# C) 통계 - 유망을 채택으로 안 올리는가 (핵심 2)
# =====================================================================
n, m, sd, se, t = M.tstat([1.0, 1.0, 1.0, 1.0])
check("C1) 흩어짐이 0 이면 t 가 0 (0으로 안 나눈다)", t == 0.0)
n, m, sd, se, t = M.tstat([2.0, 4.0, 6.0, 8.0])
check("C2) 평균이 맞다", abs(m - 5.0) < 1e-9)
check("C3) t 가 평균/표준오차다", abs(t - m / se) < 1e-9)
check("C4) 표본 1개면 0", M.tstat([3.0])[4] == 0.0)
check("C5) 빈 입력이어도 안 터진다", M.tstat([])[0] == 0)

check("C6) 큰 것 몇 개를 빼고 다시 본다",
      abs(M.drop_top([1.0, 1.0, 1.0, 100.0], 1) - 1.0) < 1e-9)
check("C7) 표본이 적으면 0", M.drop_top([1.0, 2.0], 3) == 0.0)

# 값이 전부 같으면 표준편차가 0 이라 t 도 0 이 된다. 흩어짐이 있어야
# 의미 있는 사례다.
_good = [2.0, 3.0, 4.0] * 20          # n=60, 평균 3.0, 흩어짐 있음
check("C8) t 를 넘고 상위를 빼도 양수면 채택",
      M.proven(_good) is True,
      f"t={M.tstat(_good)[4]:.1f}, 상위빼고 {M.drop_top(_good):.2f}")
check("C9) t 를 못 넘으면 탈락 (실제 43건이 이 경우)",
      M.proven([0.647] * 5 + [-3.0, 3.0]) is False)
check("C10) 몇 건이 전부를 만들면 탈락",
      M.proven([0.0] * 40 + [100.0, 100.0, 100.0]) is False)
check("C11) 평균이 음수면 탈락", M.proven([-3.0] * 50) is False)
check("C12) 왜 둘을 같이 요구하는지 적었다",
      "t 만 보면 소수의 큰 값이 만든 평균을" in flat)
check("C13) 기준 t 가 2 로 박혀 있다", M.NEED_T == 2.0)
check("C14) 빼볼 개수가 상수다", M.TOP_DROP == 3)

# =====================================================================
# D) 결과 숫자가 모듈 출력과 맞는가
# =====================================================================
for tok in ("-0.230", "+0.647", "-3.707", "-5.759", "-7.577",
            "62.8%", "55.8%", "20.9%", "1.36", "+0.072", "+2.28%",
            "3.114", "0.475"):
    check(f"D) 문서에 {tok} 가 있다", tok in src)
check("D1) 채택 안 한다고 명시한다", "채택' 으로 안 넘긴다" in flat)
check("D2) 상위 3건이 전부를 만들었다고 밝힌다",
      "3건이 거의 전부를 만들었다" in flat)
check("D3) 재무의 2025년과 같은 모양이라고 잇는다",
      "2025년 한 해가 전부였던" in flat)
check("D4) 95% 구간이 0 을 포함한다고 적었다", "0 을 포함한다" in flat)

# =====================================================================
# E) 이번에 새로 배운 것 - '길게 들어라' 가 종목과 짝이었다
# =====================================================================
check("E1) 내 예상이 정반대였다고 밝힌다", "정반대였다" in flat)
check("E2) 원인이 종목이라고 짚는다",
      "이유는 종목이다" in flat)
check("E3) 고변동을 길게 들면 -41.5% 로 간다고 잇는다", "-41.5%" in src)
check("E4) 보유와 종목을 따로 옮기면 안 된다고 정리한다",
      "종목과 짝지어진 조건이었다" in flat
      and "하나만 떼어 옮기면" in flat)
check("E5) 이번에 처음 확인한 것이라고 밝힌다", "처음 확인한 것이다" in flat)

# =====================================================================
# F) 대책이 셋으로 갈려 있는가
# =====================================================================
check("F1) 바로 바꾸는 것 / 검증할 것 / 못 하는 것을 갈랐다",
      "지금 바로 바꾸는 것" in flat and "검증하고 정하는 것" in flat
      and "못 하는 것" in flat)
check("F2) A 손절/익절 - 증거가 둘이라고 밝힌다",
      "실거래와 백테스트가 같은 방향" in flat)
check("F3) B 고변동을 길게 안 든다 - 시총 상관을 근거로 든다",
      "-0.722" in src)
check("F4) C 보유와 종목을 따로 정하지 않는다", "이번의 제일 큰 교훈" in flat)
check("F5) D 조합으로 새로 잰다고 적었다",
      "조합으로\n     새로 재야 한다" in src or "조합으로 새로 재야 한다" in flat)
check("F6) D 의 채점 기준이 이미 있다고 잇는다", "analyze_min10.py" in src)
check("F7) E 를 정정했다 - 선정 기준이 기록에 있다",
      "이건 틀렸다" in flat and "config.yaml:18" in src)
check("F8) E 거래를 더 안 해도 잴 수 있다고 바로잡았다",
      "거래를 더 하지 않고도 5.7년 일봉으로 같은 규칙을 돌릴 수 있다" in flat)
check("F8b) E 골든크로스가 아니었다고 밝힌다",
      "골든크로스가 아니었다" in flat and "dip 75건 / volatility 13건" in flat)
check("F8c) E 재현의 한계를 따로 적었다",
      "88건이 한 규칙이 아니다" in flat
      and "규칙 탓인가' 에는 답하지 못한다" in flat)
check("F8d) E 를 어디로 옮겼는지 적었다", "analyze_old_rules.py" in src)
check("F9) F 슬리피지 민감도가 240배라고 계산했다", "240배" in flat)
check("F10) F 앞으로 주문가도 기록하라고 적었다",
      "주문가와 체결가를 둘 다 기록" in flat)

# =====================================================================
# G) 기준선과 한계
# =====================================================================
check("G1) 같은 기간 지금 전략 값을 적었다", "+2.28%" in src)
check("G2) 그게 채점 기준선이라고 적었다", "기준선이다" in flat)
check("G3) 자본이 달라 직접 비교 못 한다고 밝힌다",
      "직접 비교할 수는" in flat)
check("G4) 43건이라 확정이 아니라고 밝힌다", "'확정' 이 아니다" in flat)
check("G5) 매수 시점은 안 바꿨다고 밝힌다", "매수 시점을\n   바꾸지 않았으므로" in src
      or "매수 시점을 바꾸지 않았으므로" in flat)
check("G6) 사후 계산이라 새 데이터로 다시 재라고 적었다",
      "사전 등록이 아니라 사후 계산" in flat
      and "새 데이터로 다시 재야" in flat)
check("G7) 같은 43건에서 재확인은 무의미하다고 적었다",
      "다시 확인하는 것은 의미가 없다" in flat)

# =====================================================================
# H) 안전
# =====================================================================
check("H1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"H2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
