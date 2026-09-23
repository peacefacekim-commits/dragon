"""analyze_windows.py 검증 - '무조건 이득' 착각을 만드는 계산을 막는다.

(2026-09-18 신설) 사용자가 "이 방식대로면 무조건 다 이득인데" 라고 의심했고
맞았다. 앞 테스트는 시작일 20개가 전부 같은 기간(2021년 7~8월)이라 같은
5년을 20번 센 것이었다.

이 파일이 지키는 것
  1) 시작일이 전 기간에 흩뿌려져야 한다. 한 군데 모이면 표본이 1개다.
  2) 보유 기간이 고정돼야 한다. 전부 끝까지 달리면 시작일만 다른 같은 창이다.
  3) 손실로 끝난 창의 개수를 세야 한다. 중간값만 보면 착각한다.
  4) 겹치는 창을 독립 표본으로 세면 안 된다 (3년 창 26개 = 사실상 2개).

실행:
  python tests/test_analyze_windows.py
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


src = (REPO_ROOT / "analyze_windows.py").read_text(encoding="utf-8")
lv = (REPO_ROOT / "analyze_lowvol.py").read_text(encoding="utf-8")

# --- 설계
check("0) 보유 기간을 고정한다 (끝까지 달리지 않는다)",
      "for label, W in ((\"1년\", 250), (\"2년\", 500), (\"3년\", 750))" in src
      and "i0 + W <= N - 1" in src)
check("0b) 시작일을 20거래일마다 전 기간에 흩뿌린다", "i0 += 20" in src)
check("0c) 손실로 끝난 창의 개수를 센다",
      "neg = sum(1 for x in rs if x < 0)" in src)
check("0d) 같은 창에서 시장도 같이 잰다 (전략만 보면 장세와 구별 안 됨)",
      "def market(" in src and "ms[len(ms)//2]" in src)
check("0e) 최악 창이 언제였는지 출력한다",
      "worst = min(outs, key=lambda x: x[1])" in src)
check("0f) 연도별로도 낸다 (특정 해에 몰렸는지 보려고)",
      'for y in ("2021", "2022", "2023", "2024", "2025", "2026")' in src)
check("0g) 끊긴 종목은 마지막 종가로 얼린다",
      "s.close[-1]" in src and "end / s.open[a]" in src)
check("0h) 구간마다 수수료를 한 번 물린다", "(1 - FEE / 100)" in src)

# --- 결과가 문서에 남아 있는지
check("1) 1년 창 손실 개수가 문서에 있다", "16/51 (31%)" in src)
check("1b) 최악 창 수치가 문서에 있다", "-17.5%" in src and "2021-07-26" in src)
check("1c) 연도별 표가 문서에 있다",
      all(t in src for t in ("- 9.2%", "- 7.7%", "+57.1%", "+55.1%")))
check("1d) 2025년이 시장 덕이라는 것이 적혀 있다",
      "전략의 공로가 아니라 시장이 좋았던" in src)
check("1e) 2022년 폭락에서 덜 잃은 것이 본질이라고 적혀 있다",
      "-42.5%" in src and "덜 잃는 것이다" in src)
check("1f) 평범하게 오른 해에는 시장보다 나빴다고 적혀 있다",
      "덜 빠지는 대가로 덜 오른다" in src)
check("1g) 3년 창 0개 손실을 '안전' 으로 읽지 말라고 적혀 있다",
      "독립 표본 2개" in src)

# --- 앞 파일의 결함을 그 파일에도 적었는지 (틀린 결과를 방치하지 않는다)
check("2) analyze_lowvol.py 에 결함이 명시돼 있다",
      "!! 아래 표에도 결함이 있다" in lv)
check("2b) 같은 기간을 20번 센 것이라고 적혀 있다",
      "같은 5년\n   기간 하나를 20번 센 것이다" in lv
      or "같은 5년 기간 하나를 20번 센 것이다" in lv)
check("2c) 어디를 봐야 하는지 가리킨다", "analyze_windows.py" in lv)
check("2d) 그래도 주기 비교 자체는 쓸모 있다고 구분해 적었다",
      "주기만 바꾼 비교라" in lv)

for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"3) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
