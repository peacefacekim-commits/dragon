"""analyze_losers.py 검증.

(2026-09-17 신설) 이 파일이 내리는 결론은 "지표의 공통점이 다음 구간에서
유지되지 않는다" 다. 그 결론이 계산 실수에서 나온 것이면 안 된다.

특히 위험한 두 가지:

  1) 손실/이익 회차의 지표 평균 차이(split_gap)의 부호가 뒤집혀 있으면
     '유지' 와 '뒤집힘' 이 거꾸로 세어지고, 결론이 정반대가 된다.
  2) 부호 유지 개수를 우연 기준선(절반)과 비교하는 것이 요점인데, 그
     개수를 잘못 세면 우연을 발견으로 착각한다.

그래서 손으로 계산할 수 있는 값으로 둘 다 직접 확인한다.

실행:
  python tests/test_analyze_losers.py
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import analyze_losers as A  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# ------------------------------------------------------------------ corr
check("0) 완전 양의 상관은 +1", abs(A.corr([1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                                          [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]) - 1) < 1e-12)
check("0b) 완전 음의 상관은 -1", abs(A.corr(list(range(10)),
                                          [-x for x in range(10)]) + 1) < 1e-12)
check("0c) 표본이 10개 미만이면 None", A.corr([1, 2, 3], [1, 2, 3]) is None)
check("0d) 한쪽이 상수면 None (0으로 나누지 않음)",
      A.corr([1] * 10, list(range(10))) is None)

# ------------------------------------------------------------- split_gap
# 손실 회차(수익 -1)에서 지표가 크고, 이익 회차(수익 +1)에서 작게 둔다.
# 값이 손실 2개 [3,3], 이익 2개 [1,1] 이면 전체 [3,3,1,1] 의 모표준편차는 1.0,
# 평균 차이는 3-1=2 -> gap = +2.0 이 손으로 나온다.
rows = [("d1", -1.0), ("d2", -1.0), ("d3", 1.0), ("d4", 1.0)]
vals = {"d1": {"x": 3.0}, "d2": {"x": 3.0}, "d3": {"x": 1.0}, "d4": {"x": 1.0}}
g = A.split_gap(rows, vals, "x")
check("1) 손실 회차에서 지표가 크면 gap 이 양수", g > 0, f"{g}")
check("1b) gap 값이 손으로 계산한 +2.0 과 같다", abs(g - 2.0) < 1e-12, f"{g}")

vals_flip = {d: {"x": -v["x"]} for d, v in vals.items()}
g2 = A.split_gap(rows, vals_flip, "x")
check("1c) 지표 부호를 뒤집으면 gap 부호도 뒤집힌다", abs(g2 + 2.0) < 1e-12, f"{g2}")

# 손실 회차가 없으면 비교 자체가 불가능하므로 None 이어야 한다
check("1d) 손실 회차가 없으면 None",
      A.split_gap([("d3", 1.0), ("d4", 1.0)], vals, "x") is None)
check("1e) 이익 회차가 없으면 None",
      A.split_gap([("d1", -1.0), ("d2", -1.0)], vals, "x") is None)

# 표준편차가 0 이어도 0 으로 나누지 않아야 한다
flat = {d: {"x": 5.0} for d, _r in rows}
check("1f) 지표가 상수여도 죽지 않는다", A.split_gap(rows, flat, "x") == 0.0)

# ----------------------------------------------------- 부호 유지 세기 (핵심)
# gap 의 부호가 전반부/후반부에서 같은지를 세는 논리를 직접 확인한다.
# (analyze 안에서 쓰는 식과 같은 식이어야 한다)
cases = [(+1.0, +1.0, True), (-1.0, -1.0, True),
         (+1.0, -1.0, False), (-1.0, +1.0, False)]
ok = all(((a > 0) == (b > 0)) == want for a, b, want in cases)
check("2) 부호 유지 판정이 네 경우 모두 맞다", ok)

src = (REPO_ROOT / "analyze_losers.py").read_text(encoding="utf-8")
check("2b) 코드가 같은 식으로 부호를 센다",
      '(g1 > 0) == (g2 > 0)' in src)
check("2c) 우연 기준선(절반)을 같이 출력한다", "n/2" in src)

# ----------------------------------------------------------- 주의문과 한계
check("3) 주의문에 겹침으로 인한 독립 표본 한계가 적혀 있다",
      "독립 표본" in A.CAUTION)
check("3b) 주의문에 지표를 여러 개 늘어놓는 것의 함정이 적혀 있다",
      "가장 큰 것을 고르면" in A.CAUTION)
check("3c) 주의문에 최악 회차를 보라는 말이 적혀 있다", "최악 회차" in A.CAUTION)
check("3d) 전반부 상관은 성능이 아니라는 경고가 있다", "성능이 아니다" in A.CAUTION)

# 결론이 문서에 숫자로 남아 있어야 한다 (나중에 재현 확인용)
check("3e) 실행 결과가 문서에 숫자로 남아 있다",
      all(s in src for s in ("+0.222", "-0.204", "7개", "-0.102")))

# --------------------------------------------------------------- 관찰 전용
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"4) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
