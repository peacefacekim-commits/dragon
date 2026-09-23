"""analyze_bottoms.py 검증 - 순환논리를 순환논리라고 밝히는지.

(2026-09-18 신설) 이 파일은 "바닥의 특징 19/21 일치" 라는 이 프로젝트 최고
수치를 냈다가, 정밀도 검사로 그게 순환논리였음을 밝힌다.

지켜야 하는 것
  1) 바닥/천장 정의가 앞뒤 W 일 중 최저/최고여야 한다. 그게 순환논리의
     출처이고, 정의가 흐려지면 왜 순환인지 설명이 안 된다.
  2) 지표는 전날까지만 봐야 한다 (바닥 자체는 사후 정의여도 지표는 아니다).
  3) 정밀도를 기본 확률과 같이 내야 한다. 6.92% 만 보면 좋아 보인다.
  4) 돈으로 재는 검사를 반기 양방향으로 해야 한다. 12/12 부호 뒤집힘이
     이 파일의 결론이다.
  5) 순환논리라는 말과 그 이유가 문서에 있어야 한다.

실행:
  python tests/test_analyze_bottoms.py
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


src = (REPO_ROOT / "analyze_bottoms.py").read_text(encoding="utf-8")

# --- 정의
check("0) 바닥은 앞뒤 W일 중 종가 최저다",
      "s.close[n] == min(win)" in src and "win = s.close[n - W:n + W + 1]" in src)
check("0b) 천장은 앞뒤 W일 중 종가 최고다", "s.close[n] == max(win)" in src)
check("0c) 바닥에서 사고 다음 천장에서 판다",
      'if pos is None and kind == "L"' in src)

# --- 미래 정보 차단 (지표 쪽)
check("1) 지표는 전날 종가에서 읽는다", "j = s.pos.get(di_ - 1)" in src)
check("1b) 시장 지표도 전날에서 읽는다", "d_prev = dates[di_ - 1]" in src)
check("1c) 수급도 전날 것을 쓴다", "flow.get((d_prev, code))" in src)

# --- 정밀도
check("2) 정밀도를 기본 확률과 같이 낸다",
      "base_rate" in src and "prec/base_rate" in src)
check("2b) 기본 확률의 이론값(1/(2W+1))도 보여준다",
      "1/(2*W+1)*100" in src)
check("2c) 최고 정밀도 6.92% 와 3.73배가 문서에 있다",
      "6.92%" in src and "3.73x" in src)
check("2d) 6.92% 가 열세 번 틀린다는 해석이 적혀 있다",
      "열세 번 틀리고 한 번 맞는다" in src)

# --- 돈으로 재는 검사
check("3) 반기 양방향으로 돈을 잰다",
      "실전 검사" in src and 'r["date"] < mid' in src)
check("3b) 12개 조건 전부 부호가 뒤집혔다는 결론이 있다",
      "0/12 일치" in src)
check("3c) 전반부/후반부 기준선을 같이 낸다",
      "전반부 기준선 -0.041% / 후반부 기준선 +2.018%" in src)
check("3d) 이유(하락장/상승장)가 적혀 있다",
      "하락장에서 통하고 상승장에서 손해" in src)
check("3e) 어느 장세인지 아는 것이 20번 실패한 문제라고 연결했다",
      "20번 실패한 그 문제" in src)

# --- 순환논리 명시
check("4) 순환논리라는 말이 있다", "순환논리" in src)
check("4b) 왜 순환인지 설명이 있다",
      "정의상 당연하다" in src and "정의를 다시 말한 것" in src)
check("4c) 19/21 일치가 최고 수치였다는 것도 남겼다",
      "19/21" in src and "최고 수치" in src)

# --- 천장(상금) 결과
check("5) 완벽한 타이밍의 가치가 문서에 있다",
      "+1102.3%" in src and "+4540.3%" in src and "10~45배" in src)
check("5b) 사놓기와의 비교가 같이 있다", "+107.3%" in src and "+201.6%" in src)

for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"6) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
