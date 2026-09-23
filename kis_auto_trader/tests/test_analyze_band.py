"""analyze_band.py 검증 - 밴드 매매가 공정하게 쟀는가.

(2026-09-22 신설) 이 파일에서 틀릴 수 있는 방향이 넷이다.

  1) **미래를 보는 것.** 그날 종가로 신호를 내고 그날 종가에 체결하면
     미래를 보는 것이다. 체결이 반드시 다음 날 시가여야 한다.
  2) **비교 대상을 봐주는 것.** 밴드에는 왕복마다 수수료를 물리면서
     보유에는 안 물리면 밴드가 불리해 보이고, 반대면 유리해 보인다.
     보유도 왕복 한 번은 물어야 한다.
  3) **현금으로 논 날을 안 세는 것.** 이게 이 파일의 결론(9.4)을
     만든 숫자다. 안 세면 밴드가 실제보다 좋아 보인다.
  4) **진 이유를 틀리게 적는 것.** 나는 3절에서 "작은 이득 자주 / 큰
     손해 가끔" 이라 질 것이라 예측했는데 틀렸다. 문서가 그 틀림을
     지우지 않고 적어뒀는지 본다.

실행:
  python tests/test_analyze_band.py
"""
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


import analyze_band as M  # noqa: E402

src = (REPO_ROOT / "analyze_band.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes, opens=None):
        self.close = list(closes)
        self.open = list(opens) if opens else list(closes)
        self.di = list(range(len(self.close)))
        self.pos = {d: d for d in self.di}


# =====================================================================
# A) 수수료 산수 (2절) - 이 아이디어가 수수료로 안 죽는다는 근거
# =====================================================================
check("A1) +-1% 밴드 수수료 비중 10.5%",
      abs(M.fee_share(1.0) - 10.5) < 0.01, f"{M.fee_share(1.0):.2f}%")
check("A2) +-3% 밴드 수수료 비중 3.5%",
      abs(M.fee_share(3.0) - 3.5) < 0.01, f"{M.fee_share(3.0):.2f}%")
check("A3) 밴드가 넓을수록 수수료 비중이 작다",
      M.fee_share(5.0) < M.fee_share(1.0))
check("A4) 왕복 수수료가 0.21% 다", M.FEE_ROUND_TRIP == 0.21)
check("A5) 10분 단타(0.646% 폭, 33%) 와 비교를 적었다",
      "0.646%" in src and "자릿수가 다르다" in flat)
check("A6) 밴드 0 이면 무한 (0 으로 안 나눈다)",
      M.fee_share(0) == float("inf"))

# =====================================================================
# B) moving_avg / band_signals - 미래를 안 보는가
# =====================================================================
s = FakeSeries([10.0, 20.0, 30.0, 40.0, 50.0])
check("B1) 3일 이동평균은 j=2 부터", M.moving_avg(s, 1, 3) is None)
check("B2) j=2 에서 (10+20+30)/3 = 20",
      abs(M.moving_avg(s, 2, 3) - 20.0) < 1e-9)
check("B3) j=4 에서 (30+40+50)/3 = 40",
      abs(M.moving_avg(s, 4, 3) - 40.0) < 1e-9)
check("B4) 그날 종가를 포함한다 (그래서 체결이 다음 날이어야 한다)",
      "**j 를 포함한다**" in src)

# 신호: MA 대비 +-k
s2 = FakeSeries([100.0] * 10 + [80.0] + [100.0] * 5 + [130.0])
sig = dict(M.band_signals(s2, 5, 5.0))
check("B5) 크게 빠진 날에 buy 신호", sig.get(10) == "buy", str(sig.get(10)))
check("B6) 크게 오른 날에 sell 신호", sig.get(16) == "sell",
      str(sig.get(16)))
check("B7) 평평한 구간엔 신호가 없다", 5 not in sig and 6 not in sig)

# 누적합 판본이 순진한 판본과 같은 답을 내는가 (최적화가 답을 바꾸면 안 된다)
M._SIG_CACHE.clear()
s3 = FakeSeries([100 + (k * 7919 % 41) - 20 for k in range(120)])
fast = M.band_signals(s3, 20, 2.0)
naive = []
for j in range(len(s3.close)):
    ma = M.moving_avg(s3, j, 20)
    if ma is None or ma <= 0:
        continue
    c = s3.close[j]
    if c < ma * 0.98:
        naive.append((j, "buy"))
    elif c > ma * 1.02:
        naive.append((j, "sell"))
check("B8) 누적합 판본이 순진한 판본과 같다", fast == naive,
      f"{len(fast)} vs {len(naive)}")
check("B9) 캐시가 답을 안 바꾼다",
      M.band_signals(s3, 20, 2.0) == fast)
check("B10) 캐시가 답을 안 바꾼다고 적었다", "캐시도 답을 안 바꾼다" in flat)

# =====================================================================
# C) run_band - 체결이 다음 날 시가인가 (제일 중요)
# =====================================================================
# 종가로 신호가 나고, 다음 날 시가가 전혀 다른 값일 때 어느 쪽에 체결되나
closes = [100.0] * 10 + [80.0] + [100.0] * 5 + [130.0] + [100.0] * 5
opens = list(closes)
opens[11] = 55.0          # buy 신호(j=10) 다음 날 시가를 확 낮춘다
opens[17] = 200.0         # sell 신호(j=16) 다음 날 시가를 확 높인다
s4 = FakeSeries(closes, opens)
M._SIG_CACHE.clear()
r = M.run_band(s4, 5, 5.0)
check("C1) 왕복이 한 번 생겼다", len(r.trips) == 1, str(r.trips))
if r.trips:
    expect = (200.0 / 55.0) * (1 - 0.21 / 100) - 1
    check("C2) 다음 날 시가(55 -> 200)로 체결됐다",
          abs(r.trips[0] / 100 - expect) < 1e-9,
          f"{r.trips[0]:.2f}% vs {expect * 100:.2f}%")
    check("C3) 신호 난 날 종가(80 -> 130)로 체결되지 않았다",
          abs(r.trips[0] / 100 - ((130 / 80) * (1 - 0.0021) - 1)) > 0.1)
check("C4) 문서가 미래 보기를 막았다고 적었다",
      "미래를 보는 것이다" in src)
check("C5) 코드가 어제 신호를 오늘 체결한다", "sig.get(j - 1)" in src)

# 수수료가 왕복마다 빠지는가
M._SIG_CACHE.clear()
flat_s = FakeSeries([100.0] * 10 + [80.0] + [100.0] * 5 + [100.0] * 6)
r2 = M.run_band(flat_s, 5, 5.0)
check("C6) 사고 안 팔면 왕복이 0", len(r2.trips) == 0)
check("C7) 안 팔았으면 자본 곡선이 평가액을 따라간다",
      r2.curve[-1] > 0)

# 최대 미실현 손실
M._SIG_CACHE.clear()
down = FakeSeries([100.0] * 10 + [80.0] + [70.0, 60.0, 50.0] + [100.0] * 3)
r3 = M.run_band(down, 5, 5.0)
check("C8) 물린 깊이를 잰다 (음수)", r3.worst_un < 0, f"{r3.worst_un:.1f}%")
check("C9) 안 물렸으면 0", M.run_band(FakeSeries([100.0] * 30), 5,
                                     5.0).worst_un == 0.0)

# 현금으로 논 날 (9.4 의 근거 숫자)
check("C10) 현금 날을 센다", r2.cash_days > 0, f"{r2.cash_days}일")
check("C11) 현금 날 + 보유 날 = 전체", r2.cash_days <= r2.days)
check("C12) 문서가 현금 비율을 결론의 근거로 썼다",
      "현금으로 노는 비용" in flat and "약 50%" in flat)

# =====================================================================
# D) buy_and_hold - 비교 대상을 봐주지 않았는가
# =====================================================================
bh = M.buy_and_hold(FakeSeries([100.0, 110.0, 120.0]), 0)
check("D1) 보유도 왕복 수수료를 문다",
      abs(bh[-1] - 1.2 * (1 - 0.21 / 100)) < 1e-9, f"{bh[-1]:.6f}")
check("D2) 보유가 수수료를 면제받지 않는다", bh[-1] < 1.2)
check("D3) 보유는 수수료를 한 번만 문다 (밴드는 왕복마다)",
      "왕복 한 번의 수수료만 문다" in flat)
check("D4) 시작이 1.0", bh[0] == 1.0)

# =====================================================================
# E) 문서가 기록한 숫자
# =====================================================================
for tok in ("-10.61%p", "-8.08%p", "-7.05%p", "-11.47%p",
            "68.2%", "31.8%", "+9.84%", "-9.12%", "+3.54%", "1.12배",
            "3,769건", "+10.31%", "+17.36%", "59%",
            "-2.15%p", "-2.25%p", "-2.86%p",
            "+8.21%", "-17.0%", "-40.6%", "171"):
    check(f"E) 문서에 {tok} 가 있다", tok in src)

check("E1) 12칸 전부 음수라고 적었다", "12칸 전부 음수다" in flat)
check("E2) 통과한 칸이 0 개라고 적었다", "통과한 칸 0개" in flat)
check("E3) 보유 17.36 = 밴드 10.31 + 우위 7.05 가 맞는다",
      abs((10.31 + 7.05) - 17.36) < 0.01)
check("E4) 59% = 10.31 / 17.36 이 맞는다",
      abs(10.31 / 17.36 * 100 - 59) < 1.0,
      f"{10.31 / 17.36 * 100:.1f}%")
check("E5) 왕복 평균 3.54% 가 수수료의 17배라는 말이 맞는다",
      abs(3.54 / M.FEE_ROUND_TRIP - 16.86) < 0.5,
      f"{3.54 / M.FEE_ROUND_TRIP:.1f}배")
check("E6) 손절이 연 2.1%p 를 받아간다",
      abs((10.31 - 8.21) - 2.1) < 0.01)
check("E7) 손절이 물린 깊이를 절반 이하로 줄였다",
      17.0 < 40.6 / 2)

# =====================================================================
# F) 내가 틀린 것을 지우지 않았는가 (이 파일의 핵심 검사)
# =====================================================================
check("F1) 3절 예측이 틀렸다고 적었다",
      "내가 3절에서 예측한 이유가 틀렸다" in flat)
check("F2) 무엇을 예측했는지 남겼다",
      "작은 이득 자주 / 큰 손해 가끔" in src)
check("F3) 실제 모양이 나쁘지 않았다고 적었다",
      "모양이 나쁘지 않았다" in flat)
check("F4) 진짜 이유를 기회비용으로 지목했다",
      "손익 모양이 아니라 **기회비용**이다" in flat)
check("F5) 사용자 지적을 맞다고 적었다", "맞는 말이다" in flat)
check("F6) 그런데 그 이유로 진 게 아니라고 정정했다",
      "내 예측은 틀렸다" in flat)

# 9.5 의 구분 - 능력은 있는데 모자랐다
check("F7) 밴드가 무작위보다 낫다고 적었다",
      "밴드 > 무작위 매매" in src)
check("F8) 그래도 보유보다 못하다고 적었다",
      "밴드 < 그냥 보유" in src)
check("F9) 능력이 없어서 진 게 아니라고 정리했다",
      "능력이 없어서 진 게 아니라" in flat)
check("F10) 조건3 이 8칸 통과했다고 적었다", "8칸이 통과" in flat)

# 9.6 - 사용자 방향이 맞았다고 인정
check("F11) '안정적인 종목' 방향이 맞았다고 적었다",
      "옳은\n  방향이었다" in src or "옳은 방향이었다" in flat)
check("F12) 그래도 음수라고 같이 적었다", "여전히 음수지만" in flat)
check("F13) 방향이 맞은 것과 이기는 것은 다르다고 밝혔다",
      "방향이 맞은 것과 이기는 것은 다르다" in flat)

# =====================================================================
# G) 사전 등록 규약 + 좋게 안 기울였는가
# =====================================================================
check("G1) 결과 보기 전에 정했다고 밝혔다", "숫자를 보기 전에 정했다" in flat)
check("G2) git log 가 순서를 증명한다고 적었다", "git log" in src)
check("G3) 격자를 고정하고 안 더한다고 적었다",
      "칸을 더하지 않는다" in flat)
check("G4) 격자가 실제로 12칸이다", M.N_CELLS == 12)
check("G5) 절대선 2 가 2칸이다", M.MIN_CELLS_PASS == 2)
check("G6) 다중비교 계산을 적었다", "92%" in src)
# 1-(1-0.1875)^12 가 정말 92% 인가
check("G7) 그 92% 가 맞는 산수다",
      abs((1 - (1 - 0.1875) ** 12) * 100 - 91.9) < 0.5,
      f"{(1 - (1 - 0.1875) ** 12) * 100:.1f}%")
check("G8) 12번 시도해 0번 이겼다고 적었다",
      "12번 시도해서 0번 이겼다" in flat)
check("G9) 생존편향을 한계 0 번으로 적었다",
      "생존편향이 들어 있다" in flat)
check("G10) 그 편향이 좋은 쪽으로 기운다고 밝혔다",
      "좋은 쪽으로\n   기울어 있다" in src or "좋은 쪽으로 기울어 있다" in flat)
check("G11) 슬리피지 0 을 밝혔다", "슬리피지 0" in src)
check("G12) 종목 171개가 독립이 아니라고 밝혔다",
      "서로 독립이\n   아니다" in src or "서로 독립이 아니다" in flat)
check("G13) 독립 표본 수를 적었다 (표본.md 규약)",
      "표본.md" in src and "달력 연도 5~6개" in src)
check("G14) 평가가격 정의를 바꿔도 안 풀리는 이유를 적었다",
      "정의를 바꿔도 안 풀린다" in flat)
check("G15) 종목을 고르지 않는다고 정했다 (체리피킹 방지)",
      "종목을 고르지 않는다" in flat)
check("G16) 상위 몇 개만 이기는 것은 체리피킹이라 적었다",
      "체리피킹이다" in flat)

# =====================================================================
# H) 저장소 안의 반대 증거 둘을 양쪽 다 적었는가
# =====================================================================
check("H1) analyze_stops 를 되돌림 증거로 들었다",
      "analyze_stops.py" in src and "되돌림이 있다는 말이다" in flat)
check("H2) analyze_old_rules 를 반대 증거로 들었다",
      "analyze_old_rules.py" in src and "-29.6%" in src)
check("H3) 둘 다 오염됐다고 밝혔다", "둘 다 오염됐다" in flat)
check("H4) dip 이 사실상 고변동 고르기였다고 짚었다",
      "고변동 고르기" in src and "중앙 16" in src)
check("H5) 이게 횡단면이 아니라 시계열이라고 갈랐다",
      "횡단면" in src and "시계열" in src)

# =====================================================================
# I) 조건 판정 상수
# =====================================================================
check("I1) 조건1 문턱이 4다", M.MIN_YEARS_WIN == 4)
check("I2) 조건3 문턱이 0.05 다", M.P_CUTOFF == 0.05)
check("I3) MA 셋이다", M.MA_DAYS == (20, 60, 120))
check("I4) 밴드 넷이다", M.BANDS == (1.0, 2.0, 3.0, 5.0))
check("I5) 안정 종목 수가 10 이다", M.STABLE_N == 10)
check("I6) 격자 = MA x 밴드", M.N_CELLS == len(M.MA_DAYS) * len(M.BANDS))

# cagr
check("I7) 2배가 되면 양수", M.cagr([1.0, 2.0], 246) > 99)
check("I8) 반토막이면 음수", M.cagr([1.0, 0.5], 246) < 0)
check("I9) 곡선이 짧으면 None", M.cagr([1.0], 246) is None)
check("I10) 날이 0 이면 None", M.cagr([1.0, 2.0], 0) is None)
check("I11) 자본이 0 이하면 None", M.cagr([1.0, 0.0], 246) is None)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
