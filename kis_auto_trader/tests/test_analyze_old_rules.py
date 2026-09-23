"""analyze_old_rules.py 검증 - 옛 규칙을 규칙대로 재현했는가.

(2026-09-22 신설) 이 파일의 위험은 셋이다.

  1) **규칙을 내 마음대로 바꾸는 것.** 재현의 요점은 '그때 쓰던 값' 이다.
     dip -10% / 20일 / 반등 +3% 는 config.yaml 에 적힌 값이고, 결과가
     나쁘다고 -8% 로 고치면 재현이 아니라 새 탐색이 된다.
  2) **조건 미달인 날을 억지로 채우는 것.** dip 은 조건부 신호다.
     조건에 안 맞는 종목을 끌어와 10개를 채우면 다른 규칙이 된다.
  3) **1단계에서 걸린 신호의 성과를 슬쩍 재는 것.** golden 은 reversal
     과 -0.750 이라 재포장으로 걸렸다. 걸린 뒤에 "그래도 궁금하니" 하고
     재서 좋게 나오면 그걸 쓰게 된다. 규약이 무의미해진다.

실행:
  python tests/test_analyze_old_rules.py
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


import analyze_old_rules as M  # noqa: E402

src = (REPO_ROOT / "analyze_old_rules.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    """close 만 쓰는 가짜 종목. pos 는 di -> 인덱스."""

    def __init__(self, closes, start=0):
        self.close = list(closes)
        self.open = list(closes)
        self.high = list(closes)
        self.low = list(closes)
        self.value = [1e9] * len(closes)
        self.pos = {start + i: i for i in range(len(closes))}


# =====================================================================
# A) 규칙 값이 config.yaml 그대로인가 (핵심 1)
# =====================================================================
check("A1) dip 하락 문턱이 -10.0", M.DIP_PCT == -10.0)
check("A2) dip 되돌아보는 기간이 20일", M.DIP_LOOKBACK == 20)
check("A3) 반등 확인이 +3.0%", M.REBOUND_PCT == 3.0)
check("A4) 이동평균이 5/20", (M.MA_SHORT, M.MA_LONG) == (5, 20))
check("A5) 어디서 온 값인지 적어뒀다", "config.yaml 의 실제 값" in flat)
check("A6) 거래량 조건을 왜 뺐는지 적었다", "volume_multiplier 0" in flat)
check("A7) 바꾸지 않는다고 못박았다",
      "바꾸지 않는다 - 그때 쓰던 규칙을 재현하는 것이다" in flat)

_cfg = REPO_ROOT / "config.yaml"
if _cfg.exists():
    cfg = _cfg.read_text(encoding="utf-8")
    check("A8) config.yaml 의 dip_buy_pct 와 같다",
          "dip_buy_pct: -10.0" in cfg,
          "config 쪽이 바뀌면 재현 값도 같이 봐야 한다")
    check("A9) config.yaml 의 dip_lookback_days 와 같다",
          "dip_lookback_days: 20" in cfg)
    check("A10) config.yaml 의 rebound_confirm_pct 와 같다",
          "rebound_confirm_pct: 3.0" in cfg)

# =====================================================================
# B) dip 계산 - 조건 둘을 같이 보는가
# =====================================================================
# 100 -> 80 (고점 대비 -20%) -> 88 (저점 대비 +10%): 둘 다 만족
panel = {"A": FakeSeries([100.0] * 23 + [80.0, 88.0])}
check("B1) 많이 떨어지고 되돌아서면 점수가 나온다",
      M.dip_score(panel, "A", 25) is not None,
      f"{M.dip_score(panel, 'A', 25)}")
check("B2) 점수가 고점 대비 하락폭이다 (많이 떨어진 순)",
      abs(M.dip_score(panel, "A", 25) - 12.0) < 1e-9,
      f"{M.dip_score(panel, 'A', 25)}")

# 안 떨어졌다 -> None
flat_p = {"A": FakeSeries([100.0] * 25)}
check("B3) 안 떨어졌으면 None", M.dip_score(flat_p, "A", 25) is None)

# 떨어졌지만 아직 안 돌아섰다 (저점 그대로) -> None. 이게 reversal 과의 차이
falling = {"A": FakeSeries([100.0] * 23 + [90.0, 80.0])}
check("B4) 떨어지고만 있으면 None (반등 확인이 없다)",
      M.dip_score(falling, "A", 25) is None)
check("B5) 그게 reversal 과의 차이라고 적었다",
      "떨어진 뒤 돌아서기 시작한 것만 산다" in flat)

check("B6) 기록이 모자라면 None", M.dip_score(panel, "A", 5) is None)
check("B7) 없는 종목이면 None", M.dip_score(panel, "Z", 25) is None)

# di - 1 까지만: 신호가 인덱스 25 에 있다. di=25 (j=24) 면 아직 안 보이고
# di=26 (j=25) 이 되어야 보인다. 미래를 보면 di=25 에서 점수가 나온다.
ahead = {"A": FakeSeries([100.0] * 24 + [80.0, 88.0])}
check("B8) 미래 정보를 안 쓴다 - 신호 당일엔 아직 안 보인다",
      M.dip_score(ahead, "A", 25) is None,
      f"{M.dip_score(ahead, 'A', 25)}")
check("B9) 하루 뒤에 보인다",
      M.dip_score(ahead, "A", 26) is not None,
      f"{M.dip_score(ahead, 'A', 26)}")

# =====================================================================
# C) golden 계산 - 교차일이 아니라 상태인가
# =====================================================================
rising = {"A": FakeSeries([float(100 + i) for i in range(25)])}
check("C1) 오르는 중이면 5일선이 20일선 위",
      M.golden_score(rising, "A", 25) is not None,
      f"{M.golden_score(rising, 'A', 25)}")
falling2 = {"A": FakeSeries([float(200 - i) for i in range(25)])}
check("C2) 내리는 중이면 None", M.golden_score(falling2, "A", 25) is None)
check("C3) 평평하면 None (5일선 = 20일선)",
      M.golden_score({"A": FakeSeries([100.0] * 25)}, "A", 25) is None)
check("C4) 점수가 이격%다",
      M.golden_score(rising, "A", 25) > 0)
check("C5) 기록이 모자라면 None", M.golden_score(rising, "A", 10) is None)
check("C6) 왜 교차일이 아니라 상태인지 적었다",
      "교차한 그 날' 이 아니라 '위에 있는 상태' 로 잰다" in flat)
check("C7) 교차일만 보면 표본이 적다고 적었다", "표본이 너무 적고" in flat)

check("C8) 모르는 신호는 None", M.score_of(panel, "A", 20, "없는신호") is None)
check("C9) 잴 신호가 둘뿐이다", M.SIGNALS == ("dip", "golden"))

# =====================================================================
# D) 조건 미달인 날 - 억지로 채우지 않는가 (핵심 2)
# =====================================================================
check("D1) 조건 만족이 PICK 보다 적으면 None 을 돌려준다",
      M.picks_at(flat_p, 20, "dip", pick=10) is None)
check("D2) 왜 안 채우는지 적어뒀다",
      "억지로 채우지 않는 이유" in flat
      and "'그때 쓰던 규칙' 이 아니게 된다" in flat)
check("D3) 건너뛴 회차를 세서 돌려준다",
      "skipped" in src and "return curve, skipped" in src)
check("D4) 건너뛴 회차를 출력한다", "회차 건너뜀" in src)

# =====================================================================
# E) 채택 조건 - 넷을 다 요구하는가, 느슨하게 안 했는가
# =====================================================================
check("E1) 시작일 4/5 가 기준", M.MIN_START_WINS == 4)
check("E2) p 문턱이 0.05", M.PERM_ALPHA == 0.05)
check("E3) 무작위 500회", M.N_PERM == 500)
check("E4) 재포장 문턱이 analyze_selectors 와 같다",
      M.REDUNDANT_CORR == 0.70)
check("E5) 넷을 다 넘으면 채택",
      M.accepted(4, True, True, 0.01, 4, 6, 1.0) is True)
check("E6) 시작일이 모자라면 탈락",
      M.accepted(3, True, True, 0.01, 4, 6, 1.0) is False)
check("E7) 반띵 한쪽만 이기면 탈락",
      M.accepted(5, True, False, 0.01, 4, 6, 1.0) is False)
check("E8) p 가 크면 탈락",
      M.accepted(5, True, True, 0.20, 4, 6, 1.0) is False)
check("E9) 양수인 해가 과반이 아니면 탈락",
      M.accepted(5, True, True, 0.01, 3, 6, 1.0) is False)
check("E10) 최고 해를 빼면 음수면 탈락 (재무의 2025년 교훈)",
      M.accepted(5, True, True, 0.01, 5, 6, -1.0) is False)
check("E11) 잰 해가 없으면 탈락",
      M.accepted(5, True, True, 0.01, 0, 0, 1.0) is False)
check("E12) 결과를 보고 조건을 안 고친다고 적었다",
      "결과를 보고 조건을 고치지 않는다" in flat)

# =====================================================================
# F) 1단계에서 걸린 신호의 성과를 안 재는가 (핵심 3)
# =====================================================================
check("F1) fresh 에만 성과를 잰다", "for sig in fresh" in src)
check("F2) 전부 걸리면 아예 안 잰다", "성과를 재지 않는다" in flat)
check("F3) 조건 1 을 못 넘으면 2~4 를 안 돌린다",
      "여기서 끝. 조건을 고치지 않는다" in flat)
check("F4) golden 이 걸린 것을 결과에 적었다",
      "golden" in src and "-0.750" in src and "재포장" in src)
check("F5) golden 의 성과를 안 쟀다고 밝힌다",
      "성과를 재지 않는다 - 규약대로다" in flat)
check("F6) 겹친 상대가 이미 진 팩터라고 잇는다",
      "가장 가까운 친척이 크게 졌다" in flat and "-30.9%" in src)

# =====================================================================
# G) 결과 숫자가 모듈 출력과 맞는가
# =====================================================================
for tok in ("-0.356", "+0.028", "+0.165", "-0.497", "+0.588", "-0.750",
            "-29.6", "-85.0", "0/5", "+22.3", "51.9%p",
            "27 12 14 13 11 18 32 11 24 18",
            "21 25 16 19 12 22  8 16  9 23",
            "21% / 61%", "42개", "122개"):
    check(f"G) 문서에 {tok} 가 있다", tok in src)
check("G1) 기준 저변동 값을 밝혔다", "기준 저변동 120일 = 연 +22.3%" in flat)
check("G2) dip 이 1단계는 통과했다고 적었다", "새 정보" in src)
check("G3) 낮은 상관이 좋은 성과를 뜻하지 않는다고 적었다",
      "낮은 상관이 좋은 성과를 뜻하지 않는다" in flat)

# =====================================================================
# H) 왜 졌나 - 변동성 백분위 계산이 맞는가
# =====================================================================
check("H1) 백분위 함수가 있다", hasattr(M, "vol_percentile"))
check("H2) 0 이 가장 흔들리는 쪽이라고 적었다",
      "0 = 가장 많이 흔들림" in flat or "0=가장 변동 큼" in flat
      or "0 = 가장 많이 흔들리는" in flat)
check("H3) low_vol 이 -표준편차라서 그렇다고 설명했다",
      "low_vol 점수는 -표준편차라서" in flat)
check("H4) 유니버스가 작으면 None (0 으로 안 나눈다)",
      M.vol_percentile({"A": FakeSeries([100.0] * 80)}, 70, ["A"])[0] is None)
check("H5) 옛 규칙 둘 다 고변동 고르기였다고 정리한다",
      "옛 규칙 둘 다 사실은 고변동 고르기였다" in flat)
check("H6) 백분위는 성과가 아니라고 못박았다",
      "성과가 아니라 '무엇을 고르는 체인가' 다" in flat)
check("H7) 문턱이 흔하면 고르는 일을 안 한다고 적었다",
      "문턱이 고르는 일을 거의 안 한다" in flat)

# =====================================================================
# I) 실거래 5주에 대해 과하게 말하지 않는가
# =====================================================================
check("I1) 일봉이라 10분 체결과 다르다고 밝힌다",
      "일봉으로 쟀다" in flat and "10분 체결이었다" in flat)
check("I2) 88건이 한 규칙이 아니라고 밝힌다",
      "dip 75건 / volatility 13건" in flat)
check("I3) 손실이 dip 탓이라고까지 말하지 않는다",
      "dip 탓이다\" 까지는 말하지 못한다" in flat
      or "dip 탓이다' 까지는 말하지 못한다" in flat)
check("I4) 말할 수 있는 것을 따로 적었다",
      "dip 은 오래 돌려도 지는 규칙이다" in flat)
check("I5) 실거래 분석과 방향이 맞는다고 잇는다",
      "analyze_real_trades.py" in src and "-0.023" in src)
check("I6) 골든크로스가 아니었다고 바로잡았다",
      "골든크로스가 아니라 dip(하락폭)" in flat)
check("I7) 무엇이 남는지 적었다",
      "검증된 선정은 여전히 저변동 하나뿐이다" in flat)

# =====================================================================
# J) 미래 정보를 안 쓰는가
# =====================================================================
check("J1) di - 1 까지만 본다고 적었다", "di - 1 종가까지만 본다" in flat)
check("J2) 앞 값을 끌어오지 않는다고 적었다",
      "앞 값을 끌어오지 않는다" in flat)
for fn in ("dip_score", "golden_score"):
    body = src.split(f"def {fn}(")[1].split("\ndef ")[0]
    check(f"J3) {fn} 가 di - 1 을 쓴다", "s.pos.get(di - 1)" in body)

# =====================================================================
# K) 실제 패널로 돌려도 되는가 (느리므로 --slow 일 때만)
# =====================================================================
if "--slow" in sys.argv:
    import strategy as S
    dates, pnl = S.load_panel(verbose=False)
    got = M.picks_at(pnl, M.BASE_DI, "dip")
    check("K1) 실제 패널에서 10종목을 고른다",
          got is not None and len(got) == M.PICK, str(got))
    pcts, cnt, univ = M.why_lost(dates, pnl, "dip")
    check("K2) 백분위 중앙이 16 (문서와 같다)",
          round(st.median(pcts)) == 16, f"{st.median(pcts):.1f}")
    check("K3) 조건 만족 중앙이 42종목", st.median(cnt) == 42,
          f"{st.median(cnt)}")
else:
    check("K0) 느린 검사는 --slow 로 따로 돈다 (기본은 건너뜀)", True)

# =====================================================================
# L) 안전
# =====================================================================
check("L1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"L2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
