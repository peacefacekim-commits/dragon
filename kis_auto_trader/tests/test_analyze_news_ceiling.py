"""analyze_news_ceiling.py 검증 - 천장 계산과 검증기간 계산이 맞는지.

(2026-09-18 신설) 사용자 질문 "뉴스 기사등 외적인 실물경제 정보까지
고려한다면" 에 답하는 파일이다. 뉴스 자체는 과거 기록이 없어 못 재므로,
'뉴스가 놓일 자리의 크기' 와 '검증에 걸리는 기간' 을 대신 잰다.

이 파일에서 틀리면 안 되는 것

  1) 검산: 적중률 h = drop/PICK (찍기) 이면 결과가 10종목 다 갖기와
     같아야 한다. 다르게 나오면 시뮬레이션이 편향된 것이다.
  2) 필요 표본 계산에 '뽑기 운' 분산이 들어가야 한다. 회차별 기대값만
     쓰면 분산이 사라져 '1회차면 된다' 는 엉터리가 나온다. 실제로
     처음 그렇게 틀렸다.
  3) 천장은 사후 판단이고 실현 불가능하다는 말이 있어야 한다.
  4) 바닥(잘못 골랐을 때)을 천장과 같이 내야 한다. 천장만 보면
     공짜 옵션처럼 보인다.
  5) 뉴스를 지금 쓰면 안 된다는 결론이 있어야 한다 (적중률 미확인).
  6) 미래 정보를 안 쓴다.

실행:
  python tests/test_analyze_news_ceiling.py
"""
import math
import pathlib
import statistics as st
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import analyze_news_ceiling as M  # noqa: E402

src = (REPO_ROOT / "analyze_news_ceiling.py").read_text(encoding="utf-8")

# =====================================================================
# A) 계산 자체를 가짜 데이터로 검산한다
# =====================================================================
# 흩어짐이 분명한 회차들. 각 회차 10종목.
FAKE = [
    ("d1", [-9.0, -7.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 11.0]),
    ("d2", [-12.0, -5.0, -2.0, -1.0, 0.5, 1.5, 2.5, 5.0, 7.0, 9.0]),
    ("d3", [-4.0, -3.0, -2.0, 0.0, 0.0, 1.0, 1.0, 2.0, 3.0, 8.0]),
    ("d4", [-20.0, -10.0, -3.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0]),
    ("d5", [-1.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 5.0]),
]

base = M.hold_all(FAKE)
manual = st.mean([st.mean(rs) - M.FEE for _d, rs in FAKE])
check("A1) 다 갖기 평균이 수수료를 뺀 단순평균과 같다",
      abs(base - manual) < 1e-9, f"{base:+.4f}")

top2, bot2 = M.ceiling_floor(FAKE, 2)
m_top = st.mean([st.mean(sorted(rs)[2:]) - M.FEE for _d, rs in FAKE])
m_bot = st.mean([st.mean(sorted(rs)[:-2]) - M.FEE for _d, rs in FAKE])
check("A2) 천장은 최악 2개를 뺀 값이다", abs(top2 - m_top) < 1e-9)
check("A3) 바닥은 최고 2개를 뺀 값이다", abs(bot2 - m_bot) < 1e-9)
check("A4) 천장 > 다갖기 > 바닥 순서다", top2 > base > bot2,
      f"{top2:+.3f} > {base:+.3f} > {bot2:+.3f}")

t1, b1 = M.ceiling_floor(FAKE, 1)
t3, b3 = M.ceiling_floor(FAKE, 3)
check("A5) 많이 뺄수록 천장이 높아진다", t1 < top2 < t3)
check("A6) 많이 뺄수록 바닥도 깊어진다", b1 > bot2 > b3)

# --- 핵심 검산: 찍기는 다 갖기와 같아야 한다
M.N_SIM = 3000
means_rand, within_rand = M.simulate(FAKE, 2, 2 / M.PICK)
eff_rand = st.mean(means_rand) - base
check("A7) 검산: 적중률 20%(찍기) 면 다 갖기와 같다",
      abs(eff_rand) < 0.06, f"차이 {eff_rand:+.4f}%p (0 이어야 함)")

means_perf, _w = M.simulate(FAKE, 2, 1.0)
check("A8) 적중률 100% 면 천장과 같다",
      abs(st.mean(means_perf) - top2) < 1e-9)

means_half, within_half = M.simulate(FAKE, 2, 0.5)
check("A9) 적중률이 오르면 수익도 오른다 (20% < 50% < 100%)",
      st.mean(means_rand) < st.mean(means_half) < st.mean(means_perf))

# --- 필요 표본 계산
dsd, need, yrs = M.needed_rounds(FAKE, means_half, within_half, base)
check("B1) 차이 표준편차에 뽑기 운이 포함된다 (0 이 아니다)",
      dsd > 0.1, f"{dsd:.3f}%p")
diffs = [m - (st.mean(rs) - M.FEE) for m, (_d, rs) in zip(means_half, FAKE)]
only_between = st.pstdev(diffs)
check("B2) 뽑기 운을 빼먹으면 표준편차가 더 작아진다 - 그 함정을 피했다",
      dsd > only_between, f"제대로 {dsd:.3f} vs 빼먹으면 {only_between:.3f}")
check("B3) 필요 회차가 공식대로 나온다",
      need is not None
      and abs(need - M.Z2 * dsd ** 2
              / (st.mean(means_half) - base) ** 2) < 1e-6)
check("B4) 연 단위 환산이 회차/년 으로 나눈 값이다",
      yrs is not None and abs(yrs - need / M.ROUNDS_PER_YEAR) < 1e-9)
check("B5) 효과가 0 이면 필요 회차를 내지 않는다 (발산)",
      M.needed_rounds(FAKE, [st.mean(rs) - M.FEE for _d, rs in FAKE],
                      [0.0] * len(FAKE), base)[1] is None)
_d2, need_hi, _y2 = M.needed_rounds(FAKE, means_perf,
                                    [0.0] * len(FAKE), base)
check("B6) 효과가 클수록 필요 회차가 적다",
      need_hi is not None and need_hi < need,
      f"100%: {need_hi:.0f}회차 vs 50%: {need:.0f}회차")

# --- 짝지은 비교가 왜 유리한지 (이 파일의 논거)
paired = dsd
unpaired = st.pstdev([st.mean(rs) - M.FEE for _d, rs in FAKE])
check("B7) 짝지은 비교의 흩어짐이 회차 수익 자체의 흩어짐보다 작다",
      paired < unpaired, f"짝지음 {paired:.2f} vs 회차수익 {unpaired:.2f}")

# =====================================================================
# C) 문서가 한계를 숨기지 않는지
# =====================================================================
check("C1) 뉴스를 백테스트할 수 없다고 먼저 밝힌다",
      "백테스트가 불가능하다" in src)
check("C2) 왜 불가능한지 (최근 뉴스만 받아온다) 적어놨다",
      "최근" in src and "news.py" in src and "과거 기록을 저장한 파일이" in src)
check("C3) 이미 가진 실물경제 지표는 전에 훑었다는 것을 적어놨다",
      "analyze_best_rounds.py" in src and "9/25" in src)
check("C4) 천장이 사후 판단이고 실현 불가능하다고 밝힌다",
      "사후 판단" in src and "실현 불가능" in src)
check("C5) 바닥(틀렸을 때)을 천장과 같이 낸다",
      "바닥" in src and "공짜 옵션이 아니" in src)
check("C6) 여지가 있다는 것과 뉴스가 잡아낸다는 것을 구별한다",
      "증거는 전혀 아니다" in src)
check("C7) 적중률 확인 전에는 쓰지 말라는 결론이 있다",
      "확인되기 전에는 실제로" in src and "빼면 안 된다" in src)
check("C8) 목표 적중률과 걸리는 기간이 명시돼 있다",
      "40%" in src and "3.8" in src)
check("C9) 30% 면 이득이지만 확인이 불가능하다는 구별이 있다",
      "14.6" in src and "확인 못 한 채로" in src)
check("C10) 제목 원문도 저장해야 한다는 주의가 있다",
      "제목 원문도 같이 저장" in src)
check("C11) 실물 투자는 다 갖기로 하고 장부상으로만 채점하라고 적었다",
      "장부상" in src)
check("C12) 짝지은 비교라서 표본이 적게 든다는 이유를 적었다",
      "짝지은 비교" in src and "상쇄" in src)
check("C13) 기존 타이밍 가설의 13년과 비교해놨다",
      "167회차" in src and "13년" in src)
check("C14) 검산(h=찍기 -> 0)이 코드 출력에 설명돼 있다",
      "검산" in src)

# =====================================================================
# D) 미래 정보 / 안전
# =====================================================================
check("D1) 종목 선정은 진입 시점 정보로만 한다",
      "S.factor_score(panel, c, di, \"low_vol\")" in src
      and "S.universe_at(panel, di" in src)
check("D2) 수익은 진입 이후 구간만 쓴다",
      "S.trade_return(panel, c, di, di + HOLD)" in src)
check("D3) 회차가 겹치지 않는다", "di += HOLD" in src)
check("D4) 수수료를 뺀다", "- FEE" in src)
check("D5) 난수 씨앗이 고정돼 있다", "SEED = 20260918" in src)
check("D6) 리눅스 절대경로를 박아두지 않았다",
      '"/home/user/' not in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"D7) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
