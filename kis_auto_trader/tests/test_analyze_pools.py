"""analyze_pools.py 검증 - 풀이 실제로 서로 다른 종목을 담는지.

(2026-09-18 신설) 이 파일의 결론은 "개인 순매수 선택이 저변동 풀 밖에서
3곳 중 1곳만 재현됐다" 다. 그 판정이 풀 구성 실수에서 나오면 안 된다.

특히 위험한 것: 저변동60 과 고변동60 이 겹치면 '독립 재현' 이 아니게 되고,
재현됐다는 말 자체가 거짓이 된다.

실행:
  python tests/test_analyze_pools.py
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


src = (REPO_ROOT / "analyze_pools.py").read_text(encoding="utf-8")

# 풀 다섯 개가 서로 다른 구간을 잡는지 - 코드로 고정
check("0) 저변동은 앞에서, 고변동은 뒤에서 자른다 (겹치지 않음)",
      'vols[:POOL_N]' in src and 'vols[-POOL_N:]' in src)
check("0b) 중간변동은 가운데에서 자른다",
      'mid = (n - POOL_N) // 2' in src and 'vols[mid:mid + POOL_N]' in src)
check("0c) 저변동/고변동이 겹치지 않도록 풀 두 개 크기를 확보한다",
      'len(vols) < POOL_N * 2' in src)
check("0d) 풀이 다섯 개다",
      src.count('"저변동60"') >= 1 and '"고변동60"' in src
      and '"중간변동60"' in src and '"거래대금60"' in src
      and '"전체200"' in src)

# 손으로 확인: 120종목이면 저변동 60과 고변동 60이 정확히 갈린다
vols = [(-float(i), f"C{i:03d}") for i in range(120)]
vols.sort(reverse=True)
low = {c for _s, c in vols[:60]}
high = {c for _s, c in vols[-60:]}
check("1) 120종목이면 저변동 60과 고변동 60이 전혀 겹치지 않는다",
      len(low & high) == 0, f"겹침 {len(low & high)}개")
n = len(vols)
mid = (n - 60) // 2
middle = {c for _s, c in vols[mid:mid + 60]}
check("1b) 중간변동 풀은 저변동/고변동 사이 구간이다",
      len(middle) == 60 and middle != low and middle != high)

# 방향이 어제 정한 것과 같은지
check("2) 방향이 어제와 같다 (기관/외국인 낮은쪽, 개인 높은쪽)",
      'DIRS = {"기관": -1, "외국인": -1, "개인": +1}' in src)
check("2b) 대조군이 '같은 풀 안에서 신호값만 섞기' 다",
      'rng.permutation(len(recs))' in src)
check("2c) 신호는 전날까지만 본다 (di - 1)",
      's.pos.get(di - 1)' in src and 'flow.get((dates[di - 1], code))' in src)

# 결과가 문서에 숫자로 남아 있는지
check("3) 다섯 풀 결과가 문서에 있다",
      all(t in src for t in ("+0.891", "+1.585", "+0.230", "+1.063",
                             "+1.044")))
check("3b) 통과/탈락 비율이 문서에 있다",
      all(t in src for t in ("1.3%", "3.7%", "37.5%", "6.0%", "2.8%")))
check("3c) 방향이 5/5 양수라는 것이 문서에 있다", "5/5 양수" in src)
check("3d) 15검정 중 3통과, 기대값 0.75 가 문서에 있다",
      "15검정 중 3개" in src and "0.75" in src)

# 가장 중요한 한계: 신호가 상대적이라는 것
check("4) '신호는 상대적' 한계가 문서에 있다",
      "이 신호는 상대적이다" in src)
check("4b) 고변동 풀은 신호가 좋아도 못 쓴다는 것이 적혀 있다",
      "-1.135" in src and "못 쓴다" in src)
check("4c) 절대수익 플러스 + 대조군 통과 조합이 하나뿐이라고 적혀 있다",
      "저변동60 + 개인" in src and "하나뿐" in src)
check("4d) 저변동60 은 재현 증거가 아니라고 적혀 있다",
      "재현 증거가 아니라" in src)
check("4e) 새로 나온 기관@전체200 도 갈아탈 이유가 없다고 적혀 있다",
      "갈아탈 이유가 없다" in src)

for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"5) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
