"""analyze_cascade.py 검증 - '중요한 지표 하나로 걸러내기' 를 공평하게 재는지.

(2026-09-18 신설) 사용자: "가장 중요한 지표 하나만 탐지하고 그게 통과되면
나머지들을 보면 돼지"

이 파일이 지켜야 하는 것

  1) 고르는 비용을 물어야 한다. 지표 14개 중 제일 센 것을 골랐으면
     대조군에서도 14개 중 제일 센 것을 골라야 한다. 대조군이 지표
     하나만 보면 비교가 유리하게 기울어 거짓 통과가 난다. 여기가
     이 파일의 핵심이다.
  2) 2단계가 더하는 값을 1단계 대비로 내야 한다. 전체 대비로만 내면
     2단계가 1단계 덕을 보는 것과 제 몫을 구별할 수 없다.
  3) 반기 양방향에서 '부호 유지' 와 '양쪽 다 손해' 를 구별해야 한다.
     둘 다 마이너스인데 부호가 같다고 좋게 읽으면 거꾸로 결론이 난다.
  4) 퍼센타일은 과거 창에서만 재야 한다 (미래 정보 없음).
  5) 앞에서 쓴 약한 논거(감시 비용)를 취소한 기록이 있어야 한다.

실행:
  python tests/test_analyze_cascade.py
"""
import math
import pathlib
import statistics as st
import sys

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import analyze_cascade as M  # noqa: E402

src = (REPO_ROOT / "analyze_cascade.py").read_text(encoding="utf-8")
rare_src = (REPO_ROOT / "analyze_rare_trading.py").read_text(encoding="utf-8")

rng = np.random.default_rng(11)

# =====================================================================
# A) 상관/t
# =====================================================================
x = np.arange(300, dtype=float)
r, t = M.corr_t(x, 2.0 * x + rng.normal(size=300))
check("A1) 분명한 관계면 상관이 1 에 가깝다", r > 0.99, f"{r:.4f}")
check("A2) 그때 t 가 크다", t > 15, f"t={t:.0f}")
_r0, t0 = M.corr_t(x, rng.normal(size=300))
check("A3) 관계가 없으면 t 가 작다", abs(t0) < 2.5, f"t={t0:+.2f}")
check("A4) 값이 전부 같으면 0 을 돌려준다", M.corr_t(np.ones(50), x[:50]) == (0.0, 0.0))
check("A5) 1일 앞은 겹치지 않아 겹침 보정을 안 한다고 적어놨다",
      "겹치지 않으므로 겹침 보정이 필요 없다" in src)

# =====================================================================
# B) best_of_n - 고르는 비용을 제대로 무는지 (핵심)
# =====================================================================
ys = rng.normal(size=400)
one = np.array([ys + rng.normal(size=400) * 0.01]).T      # 거의 완벽한 열 1개
check("B1) 관계 있는 열이 있으면 최고 |t| 가 크다",
      M.best_of_n(one, ys) > 15, f"{M.best_of_n(one, ys):.1f}")
many = rng.normal(size=(400, 14))
check("B2) 잡음 열 14개면 최고 |t| 가 작다",
      M.best_of_n(many, ys) < 5, f"{M.best_of_n(many, ys):.2f}")
# 열이 많아지면 최고 |t| 가 커진다 - 이게 '고르는 비용' 이다
best1, best14 = [], []
for s in range(60):
    r2 = np.random.default_rng(900 + s)
    yy = r2.normal(size=400)
    best1.append(M.best_of_n(r2.normal(size=(400, 1)), yy))
    best14.append(M.best_of_n(r2.normal(size=(400, 14)), yy))
check("B3) 열이 14개면 1개보다 최고 |t| 가 커진다 (고르는 비용이 있다)",
      st.median(best14) > st.median(best1) + 0.5,
      f"1개 {st.median(best1):.2f} vs 14개 {st.median(best14):.2f}")
check("B4) 대조군이 실제와 똑같이 14개에서 고른다",
      "best_of_n(np.roll(mat, sh, axis=0), ys)" in src)
check("B5) 대조군을 여러 번 돌린다", M.N_SHIFT >= 200, f"{M.N_SHIFT}번")
check("B6) 씨앗이 고정돼 있다", "SEED = 20260918" in src)

# 잡음에서 거짓 통과하지 않는지 (5회 중앙값)
beats = []
for s in range(5):
    r3 = np.random.default_rng(300 + s)
    yy = r3.normal(size=600)
    mm = r3.normal(size=(600, 14))
    real = M.best_of_n(mm, yy)
    vals = [M.best_of_n(np.roll(mm, int(r3.integers(20, 580)), axis=0), yy)
            for _ in range(100)]
    beats.append(sum(1 for v in vals if v >= real) / len(vals))
beats.sort()
check("B7) 잡음에서는 대조군 통과율이 낮지 않다 (거짓 통과 안 함)",
      beats[2] > 0.05, f"중앙값 {beats[2]:.3f} (전부: "
      + ", ".join(f"{b:.2f}" for b in beats) + ")")
# 진짜 관계가 있으면 통과해야 한다 (검정력)
r4 = np.random.default_rng(777)
yy4 = r4.normal(size=600)
mm4 = r4.normal(size=(600, 14))
mm4[:, 3] = yy4 * 0.25 + r4.normal(size=600)      # 한 열에 진짜 관계
real4 = M.best_of_n(mm4, yy4)
vals4 = [M.best_of_n(np.roll(mm4, int(r4.integers(20, 580)), axis=0), yy4)
         for _ in range(200)]
beat4 = sum(1 for v in vals4 if v >= real4) / len(vals4)
check("B8) 진짜 관계가 한 열에 있으면 대조군을 통과한다 (검정력 있음)",
      beat4 < 0.05, f"통과율 {beat4:.3f}")

# =====================================================================
# C) 1단계 / 2단계 / 초과분
# =====================================================================
K = M.KEYS
FAKE = []
for i in range(400):
    pct = {k: float(rng.random()) for k in K}
    FAKE.append((f"d{i:04d}", pct, float(rng.normal())))

s1 = M.stage1(FAKE, K[0])
check("C1) 1단계는 문턱을 넘은 날만 남긴다",
      all(r[1][K[0]] >= M.GATE_Q for r in s1) and len(s1) < len(FAKE),
      f"{len(s1)}/{len(FAKE)}일")
check("C2) 1단계 문턱이 상위 30% 다", abs(M.GATE_Q - 0.70) < 1e-9)
s2 = M.stage2(FAKE, K[0])
check("C3) 2단계는 1단계의 부분집합이다",
      set(id(r) for r in s2) <= set(id(r) for r in s1),
      f"2단계 {len(s2)}일 <= 1단계 {len(s1)}일")
check("C4) 2단계는 나머지 지표 과반 동의를 요구한다",
      all(sum(1 for o in K if o != K[0] and r[1][o] >= M.CONFIRM_Q)
          > (len(K) - 1) / 2 for r in s2))
check("C5) 2단계에서 1단계 지표 자신은 세지 않는다 (자기 확인 금지)",
      "others = [o for o in KEYS if o != key]" in src)

check("C6) 초과분은 전체 평균 대비다", M.excess(FAKE, FAKE) == 0.0
      or abs(M.excess(FAKE, FAKE)) < 1e-12)
hi = [r for r in FAKE if r[2] > 0.5]
check("C7) 좋은 날만 고르면 초과분이 양수다", M.excess(hi, FAKE) > 0,
      f"{M.excess(hi, FAKE):+.4f}")
check("C8) 표본이 너무 작으면 계산하지 않는다",
      M.excess(FAKE[:3], FAKE) is None)
check("C9) 2단계가 더한 값을 1단계 대비로 낸다 (전체 대비가 아니다)",
      "d = e2 - e1" in src)

# =====================================================================
# D) 반기 양방향 판정 - '양쪽 다 손해' 를 구별하는지
# =====================================================================
check("D1) 부호가 같아도 둘 다 마이너스면 '양쪽 다 손해' 로 적는다",
      'verdict = "양쪽 다 손해"' in src and 'verdict = "양쪽 다 이득"' in src)
check("D2) 부호가 같다는 말에 속지 말라는 주석이 있다",
      "부호가 같아도 둘 다 마이너스면 좋은 소식이 아니다" in src)
check("D3) 1번 지표를 한쪽에서만 골라 다른 쪽에서 쓴다",
      "rank_indicators(fit)" in src and "fn(test, k)" in src)
check("D4) 양방향으로 다 한다",
      '("전반부에서 고름", A, B)' in src and '("후반부에서 고름", B, A)' in src)
check("D5) 1번 지표가 바뀌는지 확인해서 알려준다",
      "picks[0] != picks[1]" in src and "고정된 서열이 없다" in src)

# =====================================================================
# E) 미래 정보 / 안전
# =====================================================================
check("E1) 퍼센타일을 과거 창에서만 잰다",
      "for m in range(n - LOOK, n)" in src)
check("E2) 다음날 수익을 쓴다 (당일이 아니다)", "basket[bd[i + 1]]" in src)
check("E3) 종목 선정/바스켓은 검증된 모듈을 재사용한다",
      "AC.basket_daily" in src and "AC.load_indicators" in src)
check("E4) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"E5) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# F) 문서: 취소한 논거와 결과
# =====================================================================
check("F1) 앞에서 쓴 감시 비용 논거를 취소한다고 밝힌다",
      "취소한다" in src and "반론이 못 된다" in src)
check("F2) analyze_rare_trading.py 의 비교표에서 그 줄이 빠졌다",
      "매일 확인할 게 없다" not in rare_src
      and "1년 내내 대기해야 함" not in rare_src)
check("F3) 뺀 이유를 rare_trading 문서에 남겼다",
      "정정" in rare_src and "감시 비용은 이 아이디어의 문제가 아니다"
      in rare_src)
check("F4) 이게 '몇 개가 일치하나' 와 다른 구조라고 밝힌다",
      "analyze_consensus.py" in src and "서열" in src)
check("F5) |t|>2 인 지표가 하나도 없다는 결과가 있다",
      "+1.48" in src and "kr_ret5" in src)
check("F6) 실제 최고가 잡음 중앙값보다 낮다는 것이 기록돼 있다",
      "1.78" in src and "72.8%" in src)
check("F7) 그 해석(여러 개 중 하나는 있겠지가 성립 안 함)을 적었다",
      "성립하지 않는다" in src)
check("F8) 2단계가 6/6 음수라는 것과 부호검정 1.6% 가 있다",
      "6/6" in src and "1.6%" in src)
check("F9) 2단계가 깎이는 이유가 구조적(독립 아님)이라고 밝힌다",
      "6.3" in src and "독립이 아니다" in src)
check("F10) 1번 지표가 시기마다 바뀐 것을 기록했다",
      "us_vix_chg" in src and "mkt_value" in src and "바뀐다" in src)
check("F11) 방향만은 사용자 직관과 맞다고 인정한다",
      "나쁜 날에 사라" in src or "나쁜 날에 산다" in src)
check("F12) '틀렸다' 와 '확인이 안 된다' 를 구별한다",
      "'틀렸다' 가 아니라" in src and "확인이 안 된다" in src)
check("F13) 20일 앞은 여전히 알 수 없다고 밝힌다",
      "알 수 없다" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
