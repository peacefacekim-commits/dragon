"""analyze_self_signal.py 검증 - 바스켓 자기 신호가 전날까지만 보는지.

(2026-09-17 신설) 이 파일이 내리는 결론은 "바스켓 자신의 움직임으로도
타이밍이 안 된다" 다. 그 결론이 신호 계산 실수에서 나오면 안 된다.

특히 위험한 것: 신호가 진입일 당일 값을 보면 미래 정보가 되고, 결과가
좋아지는 방향으로 틀린다.

실행:
  python tests/test_analyze_self_signal.py
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


src = (REPO_ROOT / "analyze_self_signal.py").read_text(encoding="utf-8")

# 신호가 전날(j = i - 1)까지만 보는지 - 코드로 고정한다
check("0) 신호가 전날 인덱스에서 시작한다 (j = i - 1)",
      "j = i - 1" in src and "# 전날" in src)
check("0b) 진입일 당일(i)을 신호에 쓰지 않는다",
      "basket_ret(codes, i," not in src and "s.pos.get(i)" not in src)

# 신호 여섯 개가 다 들어있는지
for k in ("self_ret5", "self_ret20", "self_ret60", "self_dd",
          "self_vol20", "self_disp"):
    check(f"1) 신호 {k} 가 정의되어 있다", f'"{k}"' in src)

# 결과가 문서에 숫자로 남아있는지 (재현 확인용)
check("2) 반기 부호 일치 1/6 이 문서에 있다", "부호 유지 1/6" in src)
check("2b) 여섯 개 전부 탈락이 문서에 있다",
      all(t in src for t in ("25.7%", "49.5%", "31.3%", "68.7%",
                             "19.2%", "20.4%")))
check("2c) 상관이 0 근처라는 것이 문서에 있다", "+0.000 ~ -0.116" in src)
check("2d) 정방향에서 걸러내는 것이 손해였다는 것이 문서에 있다",
      "-1.111" in src and "걸러내는 것 자체가 손해" in src)

# 왜 시계열은 안 되고 횡단면은 되는지가 문서에 있어야 한다
check("3) 시계열 표본 한계(62회차, 13년)가 문서에 있다",
      "62개" in src and "13년" in src)
check("3b) 횡단면이 되는 이유(3,720개, 시장 변동 상쇄)가 문서에 있다",
      "3,720" in src and "상쇄" in src)
check("3c) '절대 불가능'이 아니라 '이 데이터로는 확인 불가능'이라고 적혀 있다",
      "이 데이터로는 확인 불가능" in src)
check("3d) 하루 단위는 표본이 충분했다는 것이 적혀 있다",
      "1,257" in src and "+0.002" in src)

# 앞선 19번이 이미 '뽑은 종목'을 목표로 했다는 것을 명시
check("4) 앞선 테스트가 시장지수가 아니라 뽑은 종목을 목표로 했음을 적었다",
      "시장지수를 맞히려던 게 아니다" in src)
check("4b) 안 해본 구멍이 무엇이었는지 적었다",
      "바스켓 자신의 가격 움직임은 한 번도 안 썼다" in src)

for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"5) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
