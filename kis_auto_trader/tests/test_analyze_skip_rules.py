"""analyze_skip_rules.py 검증 - 대조군이 정말 판별을 하는지.

(2026-09-17 신설) 이 파일의 대조군은 "찾은 게 아니다" 를 말하는 데 쓰인다.
그래서 두 방향으로 다 확인해야 한다.

  가짜를 가짜라고 하는가?  (노이즈를 넣으면 '우연' 이라고 해야 한다)
  진짜를 진짜라고 하는가?  (진짜 신호를 심으면 찾아내야 한다)

두 번째가 빠지면 대조군이 그냥 항상 "아니다" 라고 말하는 고장난 자가
되고, 그걸로 내린 모든 결론이 무의미해진다. 실제로 위험한 쪽은 이것이다.

합성 데이터로 검증한다 - 정답을 알고 있어야 하기 때문이다.

실행:
  python tests/test_analyze_skip_rules.py
"""
import pathlib
import random
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import analyze_skip_rules as A  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# ------------------------------------------------------------- 기본 산수
check("0) 누적수익: +10% 두 번이면 +21%",
      abs(A.cumulative([10, 10]) - 21.0) < 1e-9, f"{A.cumulative([10, 10])}")
check("0b) 누적수익: +50% 뒤 -50% 면 -25%",
      abs(A.cumulative([50, -50]) + 25.0) < 1e-9, f"{A.cumulative([50, -50])}")
check("0c) 최대낙폭: +10% 뒤 -20% 면 -20%",
      abs(A.max_drawdown([10, -20]) + 20.0) < 1e-9,
      f"{A.max_drawdown([10, -20])}")
check("0d) 계속 오르면 최대낙폭 0",
      A.max_drawdown([1, 2, 3]) == 0.0, f"{A.max_drawdown([1, 2, 3])}")
check("0e) 쉼(0%)은 누적을 바꾸지 않는다",
      abs(A.cumulative([10, 0, 10]) - A.cumulative([10, 10])) < 1e-9)

# ================================================== 대조군 2: 노출 (양방향)
# 수익률 200개: 20개는 -10%, 나머지는 +1%.
rets = [-10.0 if i % 10 == 0 else 1.0 for i in range(200)]

# (가) 최악 회차를 정확히 집어내는 규칙 -> 대조군이 '지표가 일했다' 고 해야 한다
perfect = [r < 0 for r in rets]
res_p = A.judge_exposure(rets, perfect, n_trial=300)
check("1) 최악 회차를 정확히 집으면 무작위가 이기는 비율이 거의 0 (누적)",
      res_p["beat_cum"] < 0.02, f"{res_p['beat_cum']:.3f}")
check("1b) 같은 경우 최대낙폭에서도 무작위가 거의 못 이긴다",
      res_p["beat_mdd"] < 0.02, f"{res_p['beat_mdd']:.3f}")
check("1c) 쉰 개수가 규칙이 쉰 개수와 같다",
      res_p["n_skip"] == 20, str(res_p["n_skip"]))

# (나) 아무 관계 없이 무작위로 쉬는 규칙 -> '구별 안 된다' 고 해야 한다
random.seed(7)
noise = [False] * 200
for i in random.sample(range(200), 20):
    noise[i] = True
res_n = A.judge_exposure(rets, noise, n_trial=300)
check("2) 무작위로 쉬면 무작위 대조군과 구별되지 않는다 (누적)",
      0.05 < res_n["beat_cum"] < 0.95, f"{res_n['beat_cum']:.3f}")
# 노출을 줄이면 최대낙폭이 '그냥 줄어든다' 고 생각했는데 그렇게 단순하지
# 않았다. 오르는 회차를 빼면 회복이 사라져 낙폭이 더 깊어질 수도 있고,
# 이 합성 데이터에서는 거의 안 움직였다. 방향과 크기가 데이터에 따라
# 다르다는 것이 바로 '가정하지 말고 계산하라' 는 이유다.
# 그래서 확인할 것은 '무작위로 쉰 결과가 넓게 퍼진다' 는 것이다. 폭이
# 넓으면 규칙 하나의 숫자를 점 하나(전부 투자)와 비교할 수 없다.
cums_n, mdds_n = A.exposure_baseline(rets, 20, n_trial=300)
spread_cum = cums_n[int(len(cums_n) * 0.95)] - cums_n[int(len(cums_n) * 0.05)]
spread_mdd = mdds_n[int(len(mdds_n) * 0.95)] - mdds_n[int(len(mdds_n) * 0.05)]
check("2b) 무작위로 쉰 결과가 넓게 퍼진다 - 점 하나와 비교할 수 없다",
      spread_cum > 5.0 and spread_mdd > 2.0,
      f"누적 5~95% 폭 {spread_cum:.1f}%p, 최대낙폭 폭 {spread_mdd:.1f}%p")

# (다) 가장 좋은 회차를 쉬는 규칙 -> 무작위가 거의 항상 이겨야 한다
worst_rule = [r > 0 for r in rets]
res_w = A.judge_exposure(rets, worst_rule[:20] + [False] * 180, n_trial=300)
check("2c) 좋은 회차를 쉬면 무작위가 거의 항상 이긴다",
      res_w["beat_cum"] > 0.9, f"{res_w['beat_cum']:.3f}")

# ============================================ 대조군 1: 밀어놓기 (양방향)
KEYS = [f"k{i}" for i in range(6)]
HOLD = 5
N = 400
DATES = [f"D{i:04d}" for i in range(N)]

# (가) 진짜 신호를 심는다: k0 과 k1 이 둘 다 낮은 날은 수익이 나쁘다.
#     나쁜 날을 '무작위' 로 고른다 - 주기적으로 두면(예: 7일마다) 7의
#     배수만큼 밀었을 때 짝이 다시 맞아버려서 대조군이 무력해진다. 실제
#     시장 지표는 그런 주기를 갖지 않으므로 무작위가 맞는 모사다.
random.seed(11)
bad_idx = set(random.sample(range(N), N // 7))
bad = {d: (i in bad_idx) for i, d in enumerate(DATES)}
day_real, rounds_real = {}, []
for i, d in enumerate(DATES):
    day_real[d] = {"k0": (-1.0 if bad[d] else 1.0),
                   "k1": (-1.0 if bad[d] else 1.0)}
    for k in KEYS[2:]:
        day_real[d][k] = random.gauss(0, 1)
    rounds_real.append((d, -6.0 if bad[d] else 1.0))

g_real = A.and_gate_search(rounds_real, day_real, KEYS, HOLD, max_k=2,
                           n_shift=100)
check("3) 진짜 신호를 심으면 탐색이 찾아낸다 (우연 비율이 낮다)",
      g_real.get("beat") is not None and g_real["beat"] < 0.05,
      f"beat={g_real.get('beat')}")
check("3b) 찾아낸 조합에 심어둔 지표 k0 이 들어 있다",
      "k0" in (g_real.get("combo") or ()), str(g_real.get("combo")))
check("3c) 심은 신호라면 최악 회차도 실제로 개선된다",
      g_real["worst_keep"] > g_real["base_worst"],
      f"{g_real['base_worst']:.2f} -> {g_real['worst_keep']:.2f}")

# (나) 지표와 수익률이 아무 상관 없게 만든다 -> '우연' 이라고 해야 한다
random.seed(13)
day_noise, rounds_noise = {}, []
for d in DATES:
    day_noise[d] = {k: random.gauss(0, 1) for k in KEYS}
    rounds_noise.append((d, random.gauss(0, 3)))
g_noise = A.and_gate_search(rounds_noise, day_noise, KEYS, HOLD, max_k=3,
                            n_shift=100)
check("4) 관계가 없으면 우연 비율이 충분히 높다 (찾은 게 아니라고 말한다)",
      g_noise.get("beat") is not None and g_noise["beat"] > 0.05,
      f"beat={g_noise['beat']:.3f}")
check("4b) 관계가 없어도 '최고 조합' 은 나온다 - 그래서 대조군이 필요하다",
      g_noise.get("gain", 0) > 0, f"gain={g_noise.get('gain')}")
check("4c) 훑은 가짓수와 남은 가짓수를 같이 보고한다",
      g_noise["tried"] > g_noise["kept"] > 0,
      f"{g_noise['tried']} -> {g_noise['kept']}")
check("4d) 독립 표본 수를 (회차/보유일) 로 보고한다",
      g_noise["n_independent"] == g_noise["n_test"] // HOLD,
      f"{g_noise['n_independent']} vs {g_noise['n_test']}//{HOLD}")

# ===================================== side="good": 좋은 날에만 투자하는 쪽
# AND 의 여집합은 OR 이므로, side="bad" 로 훑어도 'AND 로 정의된 투자
# 집합' 은 한 번도 보지 않는다. 다른 공간이라는 것부터 확인한다.
check("4e) 모르는 side 는 조용히 넘어가지 않고 예외", True)
try:
    A.and_gate_search(rounds_noise, day_noise, KEYS, HOLD, max_k=2,
                      n_shift=5, side="없는쪽")
    results[-1] = False
    print("[FAIL] 4e) 모르는 side 는 조용히 넘어가지 않고 예외 - 예외 없음")
except ValueError:
    pass

# 좋은 신호를 심는다: k0, k1 이 둘 다 높은 날에만 수익이 크다.
random.seed(23)
great_idx = set(random.sample(range(N), N // 8))
day_g, rounds_g = {}, []
for i, d in enumerate(DATES):
    great = i in great_idx
    day_g[d] = {"k0": (2.0 if great else -0.5),
                "k1": (2.0 if great else -0.5)}
    for k in KEYS[2:]:
        day_g[d][k] = random.gauss(0, 1)
    rounds_g.append((d, 8.0 if great else 0.2))

g_good = A.and_gate_search(rounds_g, day_g, KEYS, HOLD, max_k=2,
                           n_shift=100, side="good")
check("5) 좋은 날 신호를 심으면 side='good' 탐색이 찾아낸다",
      g_good.get("beat") is not None and g_good["beat"] < 0.05,
      f"beat={g_good.get('beat')}")
check("5b) 심어둔 지표가 조합에 들어 있다",
      "k0" in (g_good.get("combo") or ()), str(g_good.get("combo")))
check("5c) side 를 결과에 남긴다", g_good.get("side") == "good")
check("5d) 투자 집합의 평균이 나머지보다 높다",
      g_good["mean_invest"] > g_good["mean_other"],
      f"{g_good['mean_invest']:.2f} vs {g_good['mean_other']:.2f}")

# 위에 심은 신호는 '좋은 날' 이 이항(있다/없다)이라서, 그 여집합도 AND 로
# 표현된다 - 그래서 bad 쪽 탐색이 같은 답에 도달한다 (실제로 gain 이
# 6.825 로 똑같이 나온다). 두 탐색이 서로 다른 공간이라는 것은 그런 특수한
# 구조가 없는 데이터에서 확인해야 한다.
g_bad_same = A.and_gate_search(rounds_g, day_g, KEYS, HOLD, max_k=2,
                               n_shift=20, side="bad")
check("5e) 좋은 날이 이항 구조면 두 탐색이 같은 답에 도달한다 "
      "(여집합도 AND 로 표현되는 특수한 경우)",
      abs(g_good["gain"] - g_bad_same["gain"]) < 1e-6,
      f"good {g_good['gain']:.6f} vs bad {g_bad_same['gain']:.6f}")

# ---------------------------------------------- 대조군의 '보정' 이 맞는지
# beat 은 p 값이다. 관계가 없어도 20번 중 1번은 0.05 미만이 나온다. 그래서
# 노이즈 한 판으로 판정하면 이 테스트 자체가 20번에 한 번 실패한다.
# 여러 판을 돌려 '중간값이 0.05 를 넘는지' 로 봐야 보정을 확인할 수 있다.
beats_noise = []
for s in range(5):
    random.seed(100 + s)
    dv, rr = {}, []
    for i in range(N):
        d = f"G{s}_{i:04d}"
        dv[d] = {k: random.gauss(0, 1) for k in KEYS}
        rr.append((d, random.gauss(0, 3)))
    gg = A.and_gate_search(rr, dv, KEYS, HOLD, max_k=2, n_shift=60,
                           side="good")
    beats_noise.append(gg["beat"])
beats_noise.sort()
check("6) 관계가 없으면 good 쪽 beat 이 고루 퍼진다 (중간값이 0.05 초과)",
      beats_noise[2] > 0.05, f"5판 beat = {beats_noise}")

g_good_noise = A.and_gate_search(rounds_noise, day_noise, KEYS, HOLD,
                                 max_k=3, n_shift=100, side="good")
check("6b) 관계가 없어도 좋아 보이는 '최고' 가 나온다 - 적게 고르면 더 크게 나온다",
      g_good_noise["gain"] > g_noise["gain"],
      f"good {g_good_noise['gain']:.3f} vs bad {g_noise['gain']:.3f}")
# 특수 구조가 없는 데이터에서는 두 탐색이 서로 다른 집합을 고른다.
# 이것이 'AND 의 여집합은 OR 이라 다른 공간' 의 실제 증거다.
check("6b2) 특수 구조가 없으면 두 탐색이 서로 다른 집합을 고른다",
      g_good_noise["n_invest"] < g_noise["n_invest"]
      and g_good_noise["gain"] != g_noise["gain"],
      f"good {g_good_noise['n_invest']}회 투자 vs "
      f"bad {g_noise['n_invest']}회 투자")

# 붙어 있는 날을 하나의 거래로 세는지 (적게 고를 때 가장 중요한 보정)
check("6c) 고른 날이 붙어 있으면 덩어리 수가 고른 날 수보다 적다",
      g_good_noise["n_blocks"] <= g_good_noise["n_invest"],
      f"{g_good_noise['n_blocks']}덩어리 / {g_good_noise['n_invest']}회")
# 표준오차는 '고른 날 수' 가 아니라 '떨어진 덩어리 수' 로 나눠야 한다.
# 붙어 있는 날은 같은 거래라서 새 정보가 아니기 때문이다.
_se = g_good_noise.get("se_invest")
_sd = g_good_noise.get("std_invest")
_nb = g_good_noise["n_blocks"]
check("6d) 표준오차를 덩어리 수로 나눈다 (고른 날 수로 나누면 과소평가)",
      _se is not None and _sd is not None
      and abs(_se - _sd / _nb ** 0.5) < 1e-9,
      f"se={_se} vs 표준편차 {_sd}/sqrt({_nb})")
check("6d2) 덩어리가 고른 날보다 적으면 표준오차가 더 크게 나온다",
      _nb == g_good_noise["n_invest"]
      or _se > _sd / g_good_noise["n_invest"] ** 0.5,
      f"{_nb}덩어리 / {g_good_noise['n_invest']}회")
check("6e) 임계값별 생존 개수를 보고한다 (빡빡한 쪽이 확인 불가였는지 알려면)",
      set(g_good_noise["by_pct"]) == set(A.PCTS)
      and all(v["tried"] > 0 for v in g_good_noise["by_pct"].values()),
      str({int(p * 100): v["kept"] for p, v in
           sorted(g_good_noise["by_pct"].items())}))

# 나쁜 방향을 전반부에서만 정하는지 - 후반부만 바꿔도 기준이 안 바뀌어야 한다
tr = rounds_noise[:len(rounds_noise) // 2]
bd1, cuts1 = A._fit_bad_side(tr, day_noise, KEYS)
bd2, cuts2 = A._fit_bad_side(tr, day_noise, KEYS)
check("5) 나쁜 방향/임계값이 같은 학습 구간에서 같게 나온다 (재현성)",
      bd1 == bd2 and cuts1 == cuts2)
tr_flip = [(d, -r) for d, r in tr]
bd3, _ = A._fit_bad_side(tr_flip, day_noise, KEYS)
check("5b) 학습 구간 수익 부호를 뒤집으면 나쁜 방향도 뒤집힌다 "
      "(5번이 헛돌지 않음)",
      all(bd3[k] == -bd1[k] for k in KEYS))

# --------------------------------------------------------- 자기상관
seq = []
for i in range(300):
    seq.append((f"E{i:04d}", 1.0 if i % 2 else -1.0))
ac = A.autocorr(seq, 1)
check("6) 완전히 번갈아 나오면 자기상관이 -1 에 가깝다",
      ac["corr"] < -0.9, f"{ac['corr']:+.3f}")
check("6b) 표준오차를 같이 보고한다 (0과 구별되는지 판단하려면 필요)",
      ac.get("se") is not None and abs(ac["se"] - (1 / 300 ** 0.5)) < 1e-9,
      f"{ac.get('se')}")
random.seed(17)
rseq = [(f"F{i:04d}", random.gauss(0, 1)) for i in range(500)]
ac2 = A.autocorr(rseq, 1)
check("6c) 무작위면 자기상관이 0 근처 (표준오차 2배 안)",
      abs(ac2["corr"]) < 2 * ac2["se"], f"{ac2['corr']:+.3f}")
check("6d) 겹치지 않는 회차만 센다 (보유일마다 하나)",
      A.autocorr(rseq, 5)["n"] == 100, str(A.autocorr(rseq, 5)["n"]))

# ------------------------------------------------------- 주의문과 관찰 전용
src = (REPO_ROOT / "analyze_skip_rules.py").read_text(encoding="utf-8")
check("7) 주의문에 탐색 가짓수의 함정이 적혀 있다", "11,830" in A.CAUTION)
check("7b) 주의문에 노출 감소 함정이 적혀 있다",
      "노출이 줄면" in A.CAUTION and "분포와 비교" in A.CAUTION)
check("7c) 주의문에 최악 회차를 보라는 말이 있다", "최악 회차" in A.CAUTION)
check("7d) 실행 결과가 문서에 숫자로 남아 있다",
      all(s in src for s in ("+0.387", "48.0", "-13.97", "+0.002")))
check("7e) 좋은 날 탐색 결과도 문서에 숫자로 남아 있다",
      all(s in src for s in ("+6.364", "+5.670", "35.0", "2.81")))
check("7f) 주의문에 적게 고르는 규칙의 함정이 적혀 있다",
      "떨어진 덩어리" in A.CAUTION and "표준오차" in A.CAUTION)
check("7g) 주의문에 '빡빡한 임계값은 확인 불가' 가 적혀 있다",
      "확인이 불가능한" in A.CAUTION)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"8) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
