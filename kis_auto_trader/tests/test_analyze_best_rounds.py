"""analyze_best_rounds.py 검증 - '공통점' 이 착각이 되지 않게 막는다.

(2026-09-18 신설) 이 파일은 "잘된 회차의 공통점" 을 찾는다. 그건 착각이
가장 잘 생기는 작업이다 - 54회차에서 상위 10개를 골라 지표 25개를 보면
공통점은 반드시 나온다.

그래서 이 파일이 지켜야 하는 것
  1) 지표는 전부 '전날까지' 값이어야 한다. 진입일 당일을 쓰면 미래 정보다.
  2) 상위/하위 차이를 '무작위 10회차 평균의 흔들림' 으로 나눠야 한다.
     그냥 차이만 보면 지표마다 단위가 달라 비교가 안 된다.
  3) 판정은 상위/하위 비교가 아니라 전반부/후반부 부호 일치여야 한다.
  4) 부호 일치 개수를 우연 기대값과 같이 내야 한다.
  5) 쓸 수 없는 데이터(배당/PER/PBR)를 왜 뺐는지 남겨야 한다.

실행:
  python tests/test_analyze_best_rounds.py
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


src = (REPO_ROOT / "analyze_best_rounds.py").read_text(encoding="utf-8")

# --- 미래 정보 차단
check("0) 지표는 전날(md[i-1])에서 읽는다", "p = md[i - 1]" in src)
check("0b) 지수 수준도 전날 값을 쓴다", "lv = idx[p]" in src)
check("0c) 수급도 전날 값을 쓴다", 'out[f"{label}전날"] = g(p, key)' in src)
check("0d) 미국 거래량도 전날 이전만 본다",
      "cands = [k for k in us_dates if k <= p]" in src)

# --- 잡음 자
check("1) 무작위 10회차 평균의 흔들림을 잡음 자로 쓴다",
      "noise[k] = st.pstdev(ms)" in src
      and "(noise[k] * math.sqrt(2))" in src)
check("1b) 잡음배수 2 가 기준이라고 적혀 있다", "잡음배수 2" in src)
check("1c) 지표가 많으면 몇 개는 우연히 넘는다고 적혀 있다",
      "우연히 넘는다" in src)

# --- 판정 방식
check("2) 판정이 전반부/후반부 부호 일치다",
      "전반부 상위의 특징을 후반부 상위도" in src
      and "(da > 0) == (db > 0)" in src)
check("2b) 부호 일치 개수를 우연 기대값과 같이 낸다",
      "우연이면 {len(KEYS)/2:.1f}개" in src)
check("2c) 9/25 가 우연보다 낮다는 결론이 적혀 있다",
      "9/25" in src and "우연(12.5)보다 **낮다**" in src)

# --- 규칙 검정
check("3) AND 규칙을 양방향으로 검정한다",
      'for label, A, B in (("정방향"' in src and "역방향" in src)
check("3b) 대조군이 '같은 개수만큼 무작위 회차' 다",
      "rng.choice(len(base), size=len(got), replace=False)" in src)
check("3c) 발동 3회차 결과가 양방향으로 문서에 있다",
      "+11.771%" in src and "+0.053%" in src)
check("3d) 적게 발동하는 규칙이 크게 나오는 이유가 적혀 있다",
      "표본이 작다는 신호" in src)
check("3e) 양방향에서 살아남는 것이 기관 단독뿐이라고 적혀 있다",
      "기관 단독 하나" in src)

# --- 결과와 한계
check("4) 양쪽 같은 방향 9개가 문서에 있다",
      all(t in src for t in ("외국인5일누적", "-21.09", "-28.51", "+0.35")))
check("4b) 지수 수준이 뒤집혔다는 것이 문서에 있다",
      "전반부는 지수가 낮을 때, 후반부는 높을 때" in src)
check("4c) 거래량 변화가 뒤집혔다는 것이 문서에 있다",
      "시장 거래대금   -0.08 /  +0.15" in src)
check("4d) 개인전날이 프로파일과 반기에서 다르다는 것이 적혀 있다",
      "상위/하위 표에서는 +2.10 이었는데 뒤집힘" in src)
check("4e) 미국 4개가 사실상 하나라고 적혀 있다",
      "사실상 하나" in src)
check("5) 지수가 유니버스 대용이라는 한계가 적혀 있다",
      "유니버스 200종목 동일가중 누적지수 대용" in src
      and "코스닥 단독은 낼 수 없다" in src)
check("5b) 배당/PER/PBR 를 왜 뺐는지 적혀 있다",
      "1,813종목 중 30개만" in src and "fetch_krx_extra.py" in src)
check("5c) 미국 선물을 왜 뺐는지 적혀 있다", "2024-09 부터라" in src)

for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"6) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
