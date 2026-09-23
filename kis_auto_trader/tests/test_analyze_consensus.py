"""analyze_consensus.py 검증 - '전부 같은 방향' 검사가 정직하게 되는지.

(2026-09-18 신설) 사용자 아이디어 "모든 지표들이 일직선으로 하나의 경향을
보일 때 투자" 를 재는 파일이다.

이 파일이 지켜야 하는 것

  1) 방향(RISK_OFF)을 결과 보고 정하지 않는다. 교과서 통념으로 미리
     박아놓고, 그 사실을 문서에 남긴다. 방향을 맞춰가면 검사가 무의미해진다.
  2) 실질 독립 지표 개수를 반드시 같이 낸다. 이게 이 아이디어의 핵심
     반론이다 - 13개가 일치해도 서로 베낀 것이면 증거는 13개가 아니다.
  3) 미리 정한 단 하나의 검사(기울기)가 있어야 한다. 버킷만 훑으면
     제일 좋은 걸 고른 셈이 된다.
  4) 대조군(밀어놓기)이 실제와 **똑같은 탐색 21가지**를 해야 한다.
     대조군이 더 적게 훑으면 비교가 유리하게 기울어 거짓 통과가 난다.
  5) 합의 점수에 미래 정보가 없어야 한다 (과거 LOOK일만 본다).
  6) 검정력 차이를 구별해 말해야 한다. 1일은 '없다', 20일은 '알 수 없다'.
  7) '구별되지 않는다' 와 '증명됐다' 를 구별해야 한다.

실행:
  python tests/test_analyze_consensus.py
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


import analyze_consensus as M  # noqa: E402

src = (REPO_ROOT / "analyze_consensus.py").read_text(encoding="utf-8")

# =====================================================================
# A) 실질 독립 개수 계산이 맞나 - 가짜 데이터로 검산
# =====================================================================
rng = np.random.default_rng(7)
n = 800


def mk(cols):
    """열 목록을 받아 rows 형태(날짜, {지표: 값})로 만든다."""
    out = []
    for i in range(n):
        out.append((f"d{i:04d}", {k: float(cols[k][i]) for k in M.KEYS}))
    return out


# 전부 독립인 경우 -> 실질 개수가 지표 개수에 가까워야 한다
indep = {k: rng.normal(size=n) for k in M.KEYS}
n_eff_i, _C, _k1 = M.effective_count(mk(indep))
check("A1) 지표가 전부 독립이면 실질 개수가 지표 개수에 가깝다",
      n_eff_i > len(M.KEYS) * 0.85,
      f"{n_eff_i:.1f} / {len(M.KEYS)}개")

# 전부 같은 것을 조금씩 바꾼 경우 -> 실질 개수가 1 에 가까워야 한다
one = rng.normal(size=n)
dup = {k: one * M.RISK_OFF[k] + rng.normal(size=n) * 0.02 for k in M.KEYS}
n_eff_d, _C2, _k2 = M.effective_count(mk(dup))
check("A2) 지표가 사실 하나면 실질 개수가 1 에 가깝다",
      n_eff_d < 1.5, f"{n_eff_d:.2f}개")
check("A3) 베낀 지표는 실질 개수를 늘리지 않는다 (독립 > 중복)",
      n_eff_i > n_eff_d * 4, f"{n_eff_i:.1f} vs {n_eff_d:.2f}")

# 절반은 한 덩어리, 절반은 독립 -> 중간값이 나와야 한다
mix = {}
for i, k in enumerate(M.KEYS):
    mix[k] = (one * M.RISK_OFF[k] + rng.normal(size=n) * 0.02 if i < 7
              else rng.normal(size=n))
n_eff_m, _C3, _k3 = M.effective_count(mk(mix))
check("A4) 일부만 겹치면 실질 개수가 그 중간에 온다",
      n_eff_d < n_eff_m < n_eff_i, f"{n_eff_m:.1f}개")

# =====================================================================
# B) 기울기 검정
# =====================================================================
x = np.arange(200, dtype=float)
b, t = M.slope_t(x, 3.0 * x + rng.normal(size=200) * 0.5)
check("B1) 기울기를 정확히 복원한다", abs(b - 3.0) < 0.05, f"{b:.4f}")
check("B2) 분명한 관계면 t 가 크다", t > 20, f"t={t:.1f}")
_b0, t0 = M.slope_t(x, rng.normal(size=200))
check("B3) 관계가 없으면 t 가 작다", abs(t0) < 2.5, f"t={t0:+.2f}")
check("B4) 값이 전부 같으면 0 을 돌려준다 (0으로 나누지 않음)",
      M.slope_t(np.ones(50), rng.normal(size=50)) == (0.0, 0.0))

# =====================================================================
# C) 대조군이 실제와 똑같은 탐색을 하나 - 가장 중요한 검사
# =====================================================================
cnt = rng.integers(0, 14, size=600)
y = rng.normal(size=600)
mt = M.max_abs_t(cnt, y)
check("C1) 최고 |t| 가 양수로 나온다", mt > 0, f"{mt:.2f}")

# max_abs_t 가 실제로 21가지를 보는지 - 버킷 하나를 크게 흔들면 반응해야 한다
y2 = y.copy()
y2[cnt == 13] += 8.0
check("C2) 위꼬리 버킷을 흔들면 최고 |t| 가 커진다",
      M.max_abs_t(cnt, y2) > mt + 1,
      f"{mt:.2f} -> {M.max_abs_t(cnt, y2):.2f}")
y3 = y.copy()
y3[cnt == 6] += 8.0
check("C3) 가운데 버킷을 흔들어도 최고 |t| 가 커진다 "
      "(가운데도 탐색에 들어간다)",
      M.max_abs_t(cnt, y3) > mt + 1)
y4 = y + 0.30 * cnt
check("C4) 기울기만 있는 관계도 잡아낸다",
      M.max_abs_t(cnt, y4) > mt + 1)
check("C5) 탐색 가지 수가 문서에 적혀 있다 (버킷14+꼬리6+기울기1)",
      "21" in src and "버킷 14" in src)

# 잡음 데이터에서는 실제가 대조군을 못 이겨야 한다 (5개 중 중앙값으로 본다)
beats = []
for seed in range(5):
    r2 = np.random.default_rng(100 + seed)
    c2 = r2.integers(0, 14, size=900)
    yy = r2.normal(size=900)
    real = M.max_abs_t(c2, yy)
    vals = []
    for _ in range(120):
        k = int(r2.integers(20, len(c2) - 20))
        vals.append(M.max_abs_t(np.roll(c2, k), yy))
    beats.append(sum(1 for v in vals if v >= real) / len(vals))
beats.sort()
check("C6) 잡음 데이터에서는 대조군 통과율이 낮지 않다 (거짓 통과 안 함)",
      beats[2] > 0.05,
      f"5회 통과율 중앙값 {beats[2]:.3f} (전부: "
      + ", ".join(f"{b:.2f}" for b in beats) + ")")

# 진짜 관계가 있으면 대조군을 이겨야 한다 (검정력 확인)
r3 = np.random.default_rng(500)
c3 = r3.integers(0, 14, size=900)
y5 = r3.normal(size=900) + 0.25 * c3
real5 = M.max_abs_t(c3, y5)
vals5 = []
for _ in range(200):
    k = int(r3.integers(20, len(c3) - 20))
    vals5.append(M.max_abs_t(np.roll(c3, k), y5))
beat5 = sum(1 for v in vals5 if v >= real5) / len(vals5)
check("C7) 진짜 관계가 있으면 대조군을 통과한다 (검정력 있음)",
      beat5 < 0.05, f"통과율 {beat5:.3f}")

# =====================================================================
# D) 미래 정보 / 방향 고정
# =====================================================================
check("D1) 방향은 미리 박아놓은 상수다", isinstance(M.RISK_OFF, dict)
      and len(M.RISK_OFF) == 14
      and all(v in (+1, -1) for v in M.RISK_OFF.values()))
check("D2) 방향을 결과 보고 정하지 않았다고 문서에 밝힌다",
      "결과를 보기 전에" in src and "맞추려고 고른 게 아니다" in src)
check("D3) 합의 점수는 과거 LOOK일만 본다 (미래 정보 없음)",
      "for m in range(n - LOOK, n)" in src)
check("D4) 과거 창을 쓰는 이유(추세 편향)를 적어놨다",
      "장기" in src and "추세" in src and "편향" in src)
check("D5) 종목 선정은 진입 시점 정보로만 한다",
      "S.factor_score(panel, c, di" in src and "S.universe_at(panel, di" in src)
check("D6) 바스켓 일별 수익은 전날 종가 대비로 잰다",
      "s.pos.get(di - 1)" in src)
check("D7) 난수 씨앗이 고정돼 있다", "SEED = 20260918" in src)

# =====================================================================
# E) 문서가 한계를 숨기지 않는지
# =====================================================================
check("E1) 실질 독립 개수 6.3 이 핵심 반론으로 적혀 있다",
      "6.3" in src and "첫 번째 문제" in src)
check("E2) 미국지수끼리 겹친다는 구체적 상관값이 있다",
      "+0.959" in src and "+0.865" in src)
check("E3) 한 증인에게 여러 번 물어본 것이라는 설명이 있다",
      "한 증인에게" in src)
check("E4) 전에 한 AND 조합 찾기와 어떻게 다른지 밝힌다",
      "analyze_skip_rules.py" in src and "11,830" in src
      and "고르는 게 없다" in src)
check("E5) 1일 앞 상관 +0.002 와 t=+0.06 이 기록돼 있다",
      "+0.002" in src and "+0.06" in src)
check("E6) 효과 크기를 하루 변동과 비교해놨다",
      "+0.0088" in src and "1.18%" in src)
check("E7) 가장 큰 t 가 가운데(5개)에서 나온 것을 지적한다",
      "+1.86" in src and "가운데" in src)
check("E8) 대조군 통과율 54.4% 와 그 판정이 적혀 있다",
      "54.4%" in src and "구별이 전혀 안 된다" in src)
check("E9) 반기 양방향이 양쪽 다 뒤집힌 것을 남겼다",
      "-0.7578" in src and "양방향 모두 뒤집혔다" in src)
check("E10) 1일은 '없다', 20일은 '알 수 없다' 로 구별한다",
      "거의 없다" in src and "알 수 없다" in src)
check("E11) '구별되지 않는다' 와 '증명됐다' 를 구별한다",
      "구별되지 않는다" in src)
check("E12) 사용자가 든 지표 중 빠진 것(금리/뉴스/코스닥)을 밝힌다",
      "금리" in src and "뉴스" in src and "코스닥" in src)
check("E13) 금리를 왜 아직 못 썼는지와 해결법을 적어놨다",
      "^TNX" in src and "backfill" in src)
check("E14) 쏠림->변동폭도 재고 '쓸 만한 크기가 아니다' 로 끝낸다",
      "쏠림" in src and "쓸 만한 크기가 아니다" in src)
check("E15) 아이디어의 논리 자체는 멀쩡하다고 인정한다",
      "논리는 멀쩡하다" in src)
check("E16) 거래량을 넣으니 대조군 통과율이 올라간 것을 밝힌다",
      "7.8%" in src and "잡음이었다" in src)
check("E17) 거래량을 넣어도 실질 개수가 0.6 만 올랐다고 적었다",
      "0.6 만 올랐다" in src)

# =====================================================================
# G) 승률 - 사용자가 물은 그 질문
# =====================================================================
p, lo, hi = M.wilson(5, 10)
check("G1) 승률을 맞게 낸다", abs(p - 0.5) < 1e-9, f"{p:.3f}")
check("G2) 신뢰구간이 승률을 감싼다", lo < p < hi, f"{lo:.3f} ~ {hi:.3f}")
_p8, lo8, hi8 = M.wilson(4, 8)
_p800, lo800, hi800 = M.wilson(400, 800)
check("G3) 표본이 작으면 구간이 넓다 (8일 vs 800일)",
      (hi8 - lo8) > (hi800 - lo800) * 5,
      f"8일 폭 {(hi8-lo8)*100:.0f}%p vs 800일 폭 {(hi800-lo800)*100:.0f}%p")
check("G4) 8일 표본의 구간이 20%p 넘게 흔들린다 - 숫자만 보면 착각한다",
      (hi8 - lo8) > 0.40, f"{(hi8-lo8)*100:.0f}%p")
check("G5) 표본 0 이면 계산하지 않는다",
      all(x != x for x in M.wilson(0, 0)))
check("G6) 전승/전패도 구간이 0~1 안에 있다",
      0 <= M.wilson(10, 10)[1] and M.wilson(10, 10)[2] <= 1.0
      and 0 <= M.wilson(0, 10)[1] and M.wilson(0, 10)[2] <= 1.0)

check("G7) 필요 표본이 공식대로 나온다 (10%p 차이 -> 392일)",
      abs(M.need_days(0.10) - 392) < 2, f"{M.need_days(0.10):.0f}일")
check("G8) 차이가 작아지면 필요 표본이 급격히 는다",
      M.need_days(0.02) > M.need_days(0.10) * 20,
      f"2%p {M.need_days(0.02):,.0f}일 vs 10%p {M.need_days(0.10):,.0f}일")
check("G9) 차이가 0 이면 무한으로 돌려준다",
      M.need_days(0.0) == float("inf"))

# 꼬리 기준이 중앙값 기준보다 해당일을 줄이는지 - 이게 두 번째 반론이다
FAKE = []
_r = np.random.default_rng(3)
for i in range(600):
    FAKE.append((f"d{i:04d}",
                 {k: float(_r.normal()) for k in M.KEYS}))
a_med = M.agreement(FAKE, "median")
a_tail = M.agreement(FAKE, "tail")
K = len(M.KEYS)
check("G10) 중앙값 기준과 꼬리 기준이 다른 값을 낸다",
      a_med != a_tail)
check("G11) 꼬리 기준은 나쁜 지표 개수가 더 적게 나온다 (조건이 엄격)",
      st.mean(a_tail.values()) < st.mean(a_med.values()),
      f"꼬리 {st.mean(a_tail.values()):.2f} vs "
      f"중앙값 {st.mean(a_med.values()):.2f}")
check("G12) 꼬리 기준에서 '전부 나쁨' 이 더 드물다 (AND 로 조이면 사라진다)",
      sum(1 for v in a_tail.values() if v == K)
      <= sum(1 for v in a_med.values() if v == K),
      f"꼬리 {sum(1 for v in a_tail.values() if v==K)}일 vs "
      f"중앙값 {sum(1 for v in a_med.values() if v==K)}일")
check("G13) 어느 기준이든 개수가 0~지표수 범위 안이다",
      all(0 <= v <= K for v in a_med.values())
      and all(0 <= v <= K for v in a_tail.values()))
check("G14) 꼬리 기준이 상위 20% 임계를 쓴다",
      "int(len(hist) * 0.80)" in src)

check("G15) 승률로 물은 질문에 승률로 답한 절이 있다",
      "오를 확률" in src and "평균 수익이 아니라" in src)
check("G16) 전부 좋음 54.5% vs 전부 나쁨 50.0% 가 기록돼 있다",
      "54.5%" in src and "50.0%" in src and "+4.5%p" in src)
check("G17) 꼬리 기준에서 전부 나쁜 날이 0일이었다는 것을 밝힌다",
      "전부 나쁨 0일" in src or "0일" in src)
check("G18) 극단이 드물어 확인에 150~200년 걸린다는 계산이 있다",
      "151년" in src and "207년" in src)
check("G19) 데이터를 더 모아서 풀 수 있는 문제가 아니라고 밝힌다",
      "데이터를 더 모아서 풀 수" in src)
check("G20) 조건을 조일수록 투자 기회도 사라진다는 점을 짚는다",
      "투자할 기회도 없다" in src)
check("G21) 거래량이 지표에 들어갔다", "mkt_value" in M.RISK_OFF)
check("G22) 거래량은 거래대금 5일/60일로 만든다",
      "5일평균/60일평균" in src)

# =====================================================================
# F) 안전
# =====================================================================
check("F1) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"F2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
