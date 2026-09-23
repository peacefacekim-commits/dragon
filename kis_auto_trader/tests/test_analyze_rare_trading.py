"""analyze_rare_trading.py 검증 - '드물게 거래' 계산이 유리하게 기울지 않게.

(2026-09-18 신설) 사용자 목표 "신경 안 쓰고 연 한두 번 거래하고 조금씩
벌기" 가 가능한지 재는 파일이다. 결론이 '가능하다' 쪽이므로 검사가 더
엄해야 한다 - 안 되는 것을 된다고 말하는 쪽이 위험하다.

이 파일에서 틀리면 안 되는 것

  1) 수수료를 빼먹으면 드물게 거래하는 쪽이 공짜로 유리해진다.
     갈아탈 때마다 반드시 빠져야 하고, 겹치는 종목을 봐주지 않아야 한다
     (봐주면 유리해진다 - 보수적으로 전량 교체로 계산한다).
  2) 최대낙폭은 일별 곡선에서 재야 한다. 거래만 보면 0 이 나온다
     (앞에 analyze_extremes.py 에서 실제로 그렇게 틀렸다).
  3) 시작일을 하나만 쓰면 그 시기 운이 섞인다. 흩어진 시작일 여러 개로
     재고 중앙값과 범위를 같이 내야 한다 (analyze_lowvol.py 에서
     이렇게 틀렸다 - 시작일 20개가 모두 같은 두 달 안에 있었다).
  4) '조금씩 꾸준히' 를 확인해야 한다. 평균만 내면 손실 연도가 숨는다.
  5) 미래 정보를 안 쓴다.
  6) 같은 5.5년을 다르게 자른 것이라는 경고가 있어야 한다.

실행:
  python tests/test_analyze_rare_trading.py
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


import analyze_rare_trading as M  # noqa: E402

src = (REPO_ROOT / "analyze_rare_trading.py").read_text(encoding="utf-8")

# =====================================================================
# A) 최대낙폭 계산
# =====================================================================
check("A1) 계속 오르면 낙폭이 0 이다", M.mdd([1.0, 1.1, 1.2, 1.5]) == 0.0)
check("A2) 반토막이면 -50% 다",
      abs(M.mdd([1.0, 2.0, 1.0]) - (-50.0)) < 1e-9,
      f"{M.mdd([1.0, 2.0, 1.0]):.1f}%")
check("A3) 회복해도 최악을 기억한다",
      abs(M.mdd([1.0, 2.0, 1.0, 3.0]) - (-50.0)) < 1e-9)
check("A4) 낙폭은 평가손실을 포함한다 (곡선 전체를 본다)",
      "def mdd(curve)" in src and "평가손실을 포함한다" in src)
check("A5) 거래만 보면 0 이 나온다는 경고가 있다",
      "거래만 보면 0 이 나온다" in src)

# =====================================================================
# B) 1년 이동창
# =====================================================================
win = M.rolling_windows(list(range(1, 500)), span=246)
check("B1) 이동창 개수가 맞다 (길이 - 창)", len(win) == 499 - 246)
flat = M.rolling_windows([2.0] * 400, span=246)
check("B2) 곡선이 평평하면 창 수익이 0 이다",
      all(abs(w) < 1e-9 for w in flat))
doub = M.rolling_windows([1.0] * 246 + [2.0] * 246, span=246)
check("B3) 두 배가 되면 +100% 창이 나온다",
      abs(max(doub) - 100.0) < 1e-9, f"{max(doub):.1f}%")

# =====================================================================
# C) 수수료 - 드물게 거래하는 쪽이 공짜로 유리해지지 않아야 한다
# =====================================================================
check("C1) 갈아탈 때 수수료를 뺀다", "eq *= (1 - FEE / 100)" in src)
check("C2) 첫 매수 때는 교체가 아니므로 빼지 않는다",
      "if cur:\n                        eq *= (1 - FEE / 100)" in src)
check("C3) 종목이 그대로면 갈아타지 않는다 (수수료도 안 뺀다)",
      "if new != cur:" in src)
check("C4) 겹치는 종목을 봐주지 않고 전량 교체로 계산한다 (보수적)",
      "보수적으로 전량 교체" in src)
check("C5) 거래 횟수를 세서 총수수료를 낸다",
      "trades += 1" in src and "*FEE" in src.replace(" ", ""))

# 가짜 전략으로 수수료가 실제로 빠지는지 확인한다
class FakeSeries:
    def __init__(self, closes):
        self.close = closes
        self.pos = {i: i for i in range(len(closes))}


def fake_panel(codes, closes):
    return {c: FakeSeries(list(closes)) for c in codes}


_real = (M.S.universe_at, M.S.factor_score, M.S.UNIVERSE_SIZE, M.S.MIN_PRICE)
try:
    n = 60
    dates = [f"2021{i:04d}" for i in range(n)]
    # 값이 전혀 안 움직이는 종목들 -> 수익은 0, 수수료만 남는다
    codes = [f"{i:06d}" for i in range(20)]
    panel = fake_panel(codes, [100.0] * n)
    M.S.universe_at = lambda p, di, size, mp: list(codes)
    # 회차마다 뽑히는 10종목이 바뀌도록 순위를 돌린다.
    # (모든 종목에 같은 값을 더하면 순위가 안 바뀌어 갈아타지 않는다 -
    #  처음 그렇게 써서 이 검사가 헛돌았다)
    M.S.factor_score = lambda p, c, di, kind: float((int(c) + di // 10) % 20)
    curve, trades = M.run(dates, panel, 0, 10)
    check("C6) 값이 안 움직이면 자산은 수수료만큼만 줄어든다",
          curve[-1] < 1.0, f"자산 {curve[-1]:.5f}, 거래 {trades}회")
    expected = (1 - M.FEE / 100) ** (trades - 1)
    check("C7) 줄어든 만큼이 (거래횟수-1) 번의 수수료와 같다",
          abs(curve[-1] - expected) < 1e-9,
          f"실제 {curve[-1]:.6f} vs 기대 {expected:.6f}")

    # 종목이 절대 안 바뀌면 거래는 한 번, 수수료는 0
    M.S.factor_score = lambda p, c, di, kind: float(int(c))
    curve2, trades2 = M.run(dates, panel, 0, 10)
    check("C8) 뽑히는 종목이 안 바뀌면 거래가 한 번뿐이다",
          trades2 == 1, f"{trades2}회")
    check("C9) 그때는 수수료가 안 빠진다 (자산 그대로)",
          abs(curve2[-1] - 1.0) < 1e-12, f"{curve2[-1]:.8f}")

    # 주기를 짧게 하면 거래가 늘고 수수료가 더 빠져야 한다
    M.S.factor_score = lambda p, c, di, kind: float((int(c) + di // 5) % 20)
    c_short, t_short = M.run(dates, panel, 0, 5)
    M.S.factor_score = lambda p, c, di, kind: float((int(c) + di // 20) % 20)
    c_long, t_long = M.run(dates, panel, 0, 20)
    check("C10) 주기가 짧으면 거래가 더 많다",
          t_short > t_long, f"5일 {t_short}회 vs 20일 {t_long}회")
    check("C11) 거래가 많으면 수수료로 더 잃는다 (수익이 0인 세계에서)",
          c_short[-1] < c_long[-1],
          f"{c_short[-1]:.5f} vs {c_long[-1]:.5f}")
finally:
    M.S.universe_at, M.S.factor_score = _real[0], _real[1]
    M.S.UNIVERSE_SIZE, M.S.MIN_PRICE = _real[2], _real[3]

# =====================================================================
# D) 시작일을 흩어놓았나 - 앞에 이걸로 틀렸다
# =====================================================================
check("D1) 시작일이 여러 개다", M.N_STARTS >= 10, f"{M.N_STARTS}개")
check("D2) 시작일이 서로 벌어져 있다", M.START_GAP >= 20, f"{M.START_GAP}거래일")
span = M.N_STARTS * M.START_GAP
check("D3) 시작일이 1년 넘게 퍼져 있다 (한 시기에 몰리지 않는다)",
      span > M.DAYS_PER_YEAR, f"{span}거래일 = {span/246:.1f}년")
check("D4) 시작일 하나로 재면 안 된다는 이유를 적어놨다",
      "시작일 하나로 재면" in src and "analyze_lowvol.py" in src)
check("D5) 중앙값과 최소~최대를 같이 낸다",
      "st.median(tot)" in src and "min(tot)" in src and "max(tot)" in src)

# =====================================================================
# E) 미래 정보 / 안전
# =====================================================================
check("E1) 종목 선정은 그 시점 정보로만 한다",
      'S.factor_score(panel, c, di, "low_vol")' in src
      and "S.universe_at(panel, di" in src)
check("E2) 일별 수익은 전날 종가 대비로 잰다", "s.pos.get(di - 1)" in src)
check("E3) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"E4) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# F) 문서가 결론을 과장하지 않는지 - 여기가 제일 중요하다
# =====================================================================
check("F1) 목표를 세 조각으로 나눈다",
      "(1) 사용자가 신경을 안 쓴다" in src
      and "(2) 연 한두 번만 거래한다" in src
      and "(3) 이윤을 조금씩 낸다" in src)
check("F2) '드물게 거래' 와 '타이밍 맞추기' 를 구별한다",
      "거래를 드물게 한다" in src and "언제 거래할지 맞춘다" in src)
check("F3) 드물게 거래하는 데 조짐이 필요 없다고 밝힌다",
      "조짐을 읽을 필요가 없다" in src)
check("F4) 연 1.1회 +114.0% 와 월 12.4회 +110.3% 가 기록돼 있다",
      "+114.0%" in src and "+110.3%" in src and "12.4" in src)
check("F5) 수수료가 13.3% -> 1.2% 로 빠지는 것을 밝힌다",
      "13.3%" in src and "1.2%" in src)
check("F6) 드물게 거래하는 대가(들쭉날쭉함)를 밝힌다",
      "들쭉날쭉함" in src and "+51~+161" in src)
check("F7) '조금씩' 이 아니라고 분명히 말한다",
      "'조금씩' 이 아니다" in src)
check("F8) 2021~2022 2년 연속 손실을 남겼다",
      "-10.4%" in src and "-10.3%" in src and "2년 연속 손실" in src)
check("F9) 1년 창 손실 비율을 낸다 (연 1회 19%, 월 1회 28%)",
      "19%" in src and "28%" in src)
check("F10) 드물게 하면 최악이 더 깊다는 것을 밝힌다",
      "-19.1%" in src and "한 번 지면 더 크게 진다" in src)
check("F11) 2025~2026 이 시장 몫이라는 경고가 있다",
      "+55.1%" in src and "시장이 올라간 몫" in src)
check("F12) 같은 5.5년을 다르게 자른 것이라는 경고가 있다",
      "같은 5.5년을 다르게 자른 것" in src
      and "한 시기를 여섯 번 본 것" in src)
check("F13) 연 1회와 월 1회를 이 데이터로 못 가른다고 밝힌다",
      "못 가른다" in src)
check("F14) 손실 연도는 전략을 바꿔서 없앨 수 없다고 밝힌다",
      "주식을 들고 있는" in src and "대가다" in src)
# (2026-09-18 수정) 원래 이 검사는 '매일 지표를 봐야 한다' 는 줄을 요구했다.
# 사용자가 그건 반론이 못 된다고 지적해서 그 줄을 뺐고, 검사도 바꿨다.
# 이제는 그 논거를 취소한 기록이 있는지를 본다.
check("F15) 감시 비용 논거를 취소한 기록이 있다",
      "정정" in src and "반론이 못 된다" in src
      and "감시 비용은 이 아이디어의 문제가 아니다" in src)
check("F15b) 취소한 논거 대신 남는 문제를 적어놨다",
      "연 2일뿐" in src and "거의 안 하게" in src)
check("F15c) 실제 검사는 따로 했다고 가리킨다",
      "analyze_cascade.py" in src)
check("F16) 조짐 효과에 증거가 없다는 것을 다시 밝힌다",
      "증거 없음" in src and "z=+0.20" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
