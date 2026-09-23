"""analyze_lowvol.py 검증 - 갈아타기 비교와 지표 훑기의 계산이 맞는지.

(2026-09-18 신설) 이 파일에서 틀리면 "갈아타는 게 낫다/아니다" 가 뒤집힌다.

특히 위험한 곳
  1) 수수료를 리밸런스마다 한 번씩 물려야 한다. 안 물리면 자주 갈아타는
     쪽이 공짜로 유리해진다.
  2) 낙폭은 일별 평가금액으로 재야 한다. 구간 끝값만 이으면 보유 중
     평가손실이 안 보인다.
  3) 데이터가 끊긴 종목은 마지막 종가에서 얼어붙어야 한다. 조용히 빼면
     생존편향이 되살아난다 - '한 번 사고 끝까지' 가 이 위험이 가장 크다.
  4) 시작일 하나로 비교하면 운이 섞인다. 여러 시작일을 짝지어 봐야 한다.

실행:
  python tests/test_analyze_lowvol.py
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


src = (REPO_ROOT / "analyze_lowvol.py").read_text(encoding="utf-8")

# --- 수수료
check("0) 리밸런스 구간마다 수수료를 한 번 물린다",
      "base = equity * (1 - FEE / 100)" in src)
check("0b) 수수료 총액을 교체 횟수 x 수수료로 보고한다",
      "st.mean(nrs)*FEE" in src)

# --- 낙폭
check("1) 낙폭을 일별 평가금액 곡선에서 잰다",
      "def mdd(curve)" in src and "curve.extend(" in src)
check("1b) 구간 중간 날짜의 평가금액을 곡선에 다 넣는다 (끝값만 잇지 않음)",
      "for v in seg[:-1]" in src)

# --- 끊김 처리
check("2) 데이터가 끊긴 종목은 마지막 종가에서 얼어붙는다",
      "last[c] = s.close[j]" in src and "last[c] / entry[c]" in src)
check("2b) 끊김 수를 따로 세서 보고한다", 'cuts += cut' in src)
check("2c) '한 번 사고 끝까지' 가 끊김 위험이 가장 크다는 것이 적혀 있다",
      "이 위험이 가장 큰 방식" in src or "낙폭 관리" in src)

# --- 시작일 여러 개
check("3) 시작일을 여러 개로 돌린다", "N_STARTS = 20" in src
      and "starts = [START0 + k for k in range(N_STARTS)]" in src)
check("3b) 같은 시작일끼리 짝지어 비교한다",
      "base_by_start" in src and "시작일이 같으므로 운이 상쇄" in src)
check("3c) 전에 보고한 +22.0%p 가 시작일 하나였다고 정정했다",
      "+22.0%p 는 운 좋은 시작일 하나" in src)

# --- 결과가 문서에 남아 있는지
check("4) 갈아타기 주기 결과가 문서에 있다",
      all(t in src for t in ("94.7%", "105.9%", "87.0%", "13.2%", "2.3%")))
check("4b) 짝지은 비교 결과가 문서에 있다",
      "+12.5%p" in src and "14/20" in src and "12/20" in src)
check("4c) 120일이 제일 낫다는 결론이 적혀 있다",
      "120일(6개월)마다가 제일 낫다" in src)
check("4d) 한 번 사고 끝까지의 낙폭 악화 이유가 적혀 있다",
      "-31.5%" in src and "안 흔들리는 종목' 이 아니게" in src)

# --- 지표 훑기
check("5) 지표 14개를 본다고 적었고 보정 필요를 적었다",
      "지표 14개" in src and "곱해서 읽어야" in src)
check("5b) 통과한 두 지표 결과가 문서에 있다",
      all(t in src for t in ("hi52", "+2.084", "1.7%", "12개월모멘텀",
                             "+1.953", "2.3%")))
check("5c) 그 둘이 사실상 같은 것이라고 적었다",
      "사실상\n     같은 것이다" in src or "사실상 같은 것이다" in src)
check("5d) 효과가 후반부에 몰려 있다고 적었다",
      "후반부에 몰려 있다" in src and "20배 차이" in src)
check("5e) 어제 통과한 개인수급이 표본을 줄이니 탈락했다고 적었다",
      "6.9% 로 탈락" in src and "62 -> 55" in src)
check("5f) 전체 200종목 모멘텀과의 대비가 적혀 있다",
      "-3.657" in src and "다른 물건이다" in src)
check("5g) 지표가 전날까지만 본다", "s.pos.get(di - 1)" in src)
check("5h) 대조군이 '풀 안에서 그 지표값만 섞기' 다",
      "rng.permutation(len(recs))" in src)

for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"6) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
