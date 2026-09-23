"""analyze_min10.py 검증 - 데이터가 없을 때 박아둔 기준을 지키는가.

(2026-09-21 신설) 이 테스트가 특별한 이유: 검사 대상 모듈이 쓰일 때
10분봉 데이터가 **한 줄도 없었다.** 그러니 기준이 결과를 보고 만들어진
게 아니라는 것이 확실하다.

이 파일의 임무는 하나다. 나중에 데이터가 쌓이고 "아깝다" 는 숫자가
나왔을 때, **기준이 조용히 느슨해지는 것을 막는 것.** 오늘 겪은 일이
그것이다 - analyze_fundamentals 에서 세 조건을 다 통과한 신호가 해마다
쪼개니 한 해짜리였다.

실행:
  python tests/test_analyze_min10.py
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


import analyze_min10 as M  # noqa: E402

src = (REPO_ROOT / "analyze_min10.py").read_text(encoding="utf-8")
flat = " ".join(src.split())

# =====================================================================
# A) 시험 가짓수와 방향이 고정돼 있는가
# =====================================================================
check("A1) 다섯 가지다", len(M.SIGNALS) == 5, str(M.SIGNALS))
check("A2) 사용자의 원래 방식(되돌림)이 들어 있다", "gap_fill" in M.SIGNALS)
check("A3) 하루 안의 시간대를 본다 (날 단위 타이밍은 이미 다 졌다)",
      "time_of_day" in M.SIGNALS)
check("A4) 늘리지 않겠다고 적었다", "늘리지 않는다" in flat)
check("A5) 방향도 미리 고정했다고 적었다", "방향도 미리 고정" in flat)
check("A6) 양방향을 안 보는 이유를 댔다", "가짓수가 두 배" in flat)
check("A7) 왜 이 다섯인지 근거를 댔다", "왜 이 다섯인가" in flat)
check("A8) 날 단위 타이밍과 다르다는 것을 짚었다",
      "전부 **날 단위** 타이밍이었다" in src or "날 단위" in flat)

# =====================================================================
# B) 수수료 문턱 - 규칙보다 먼저 보는 것
# =====================================================================
check("B1) 왕복 수수료가 0.21%", M.FEE_ROUND_TRIP == 0.21)
check("B2) 구간 변동폭 대비 문턱을 계산한다",
      abs(M.fee_hurdle(0.93, 0.21) - 22.58) < 0.1, f"{M.fee_hurdle(0.93, 0.21):.2f}")
check("B3) 변동폭이 크면 문턱이 낮아진다",
      M.fee_hurdle(2.0) < M.fee_hurdle(0.5))
check("B4) 변동폭이 0이면 무한대 (0으로 안 나눈다)",
      M.fee_hurdle(0.0) == float("inf"))
check("B5) 순수익은 수수료를 뺀 값이다",
      abs(M.net_edge(0.30) - 0.09) < 1e-9, f"{M.net_edge(0.30)}")
check("B6) 총수익이 수수료보다 작으면 순수익이 음수",
      M.net_edge(0.10) < 0)
check("B7) 0절을 먼저 하는 이유를 적었다",
      "판이 안 되는데 규칙을 찾으면" in flat)
check("B8) 어느 칸도 양수가 아니면 그만둔다고 적었다",
      "조건 찾기를" in flat and "그만둔다" in flat)
check("B9) analyze_short_term 과 같은 논리라고 잇는다",
      "손익분기가 2.3일" in flat)

# =====================================================================
# C) 필요한 표본 계산
# =====================================================================
check("C1) 엣지가 작을수록 더 많이 필요하다",
      M.trades_needed(0.05) > M.trades_needed(0.10) > M.trades_needed(0.21))
check("C2) 0.10% 면 약 346건", abs(M.trades_needed(0.10) - 346) < 5,
      f"{M.trades_needed(0.10):.0f}")
check("C3) 엣지가 0 이하면 무한대", M.trades_needed(0.0) == float("inf")
      and M.trades_needed(-0.1) == float("inf"))
check("C4) 표본은 금방 찬다고 밝혔다", "표본은 며칠이면 충분" in flat)
check("C5) 진짜 제약이 무엇인지 적었다",
      "며칠에 걸쳐 같은 결과가 나오나" in flat)

# =====================================================================
# D) 채택 조건 넷 - 하나라도 빠지면 탈락
# =====================================================================
ok = dict(mean_gross_pct=0.40, first_beats=True, second_beats=True,
          perm_p=0.01, days_pos=40, days_total=60, rest_mean=0.1)
check("D1) 넷 다 넘으면 채택", M.accepted(**ok) is True)
check("D2) 수수료를 못 넘으면 탈락 (승률과 무관)",
      M.accepted(**{**ok, "mean_gross_pct": 0.15}) is False)
check("D3) 딱 수수료만큼이면 탈락 (0 은 양수가 아니다)",
      M.accepted(**{**ok, "mean_gross_pct": 0.21}) is False)
check("D4) 전반부에서 지면 탈락",
      M.accepted(**{**ok, "first_beats": False}) is False)
check("D5) 후반부에서 지면 탈락",
      M.accepted(**{**ok, "second_beats": False}) is False)
check("D6) 대조군을 못 넘으면 탈락",
      M.accepted(**{**ok, "perm_p": 0.2}) is False)
check("D7) 양수인 날이 과반이 아니면 탈락",
      M.accepted(**{**ok, "days_pos": 30}) is False)
check("D8) 최고 날을 빼서 음수면 탈락 (하루가 전부인 경우)",
      M.accepted(**{**ok, "rest_mean": -0.05}) is False)
check("D9) 날짜 자료가 없으면 탈락",
      M.accepted(**{**ok, "days_total": 0}) is False)
check("D10) 승률이 아니라 순수익으로 판정한다고 적었다",
      "승률이 아니라 순수익으로 판정한다" in flat)
check("D11) 승률 60%여도 질 수 있다는 예를 들었다",
      "승률 60%" in flat)
check("D12) 사용자의 연속 손해가 그 모양일 수 있다고 짚었다",
      "며칠 연속 손해 본 것이" in flat)

# 날짜별 지속성
pos, tot, rest = M.day_persistence([0.1, 0.1, -0.05, 0.2])
check("D13) 양수인 날을 센다", pos == 3 and tot == 4, f"{pos}/{tot}")
check("D14) 최고 날을 뺀 평균을 낸다", abs(rest - 0.05) < 1e-9, f"{rest}")
check("D15) 하루가 전부면 나머지가 0 근처로 떨어진다",
      M.day_persistence([0.0, 0.0, 5.0])[2] == 0.0)
check("D16) 날이 하나뿐이면 판정 불가", M.day_persistence([0.3]) == (0, 1, 0.0))
check("D17) 빈 입력이어도 안 터진다", M.day_persistence([]) == (0, 0, 0.0))
check("D18) 조건 4가 왜 핵심인지 적었다",
      "한 날' 이 그 자리를 차지할 수 있다" in flat
      or "'한 날'" in flat or "한 날" in flat)
check("D19) 재무에서 못 걸렀던 이유를 근거로 든다",
      "서로 독립이 아니어서" in flat)

# =====================================================================
# E) 슬리피지를 따로 적는가
# =====================================================================
check("E1) 순수익이 0이 되는 슬리피지를 낸다",
      abs(M.slippage_flip(0.41) - 0.10) < 1e-9, f"{M.slippage_flip(0.41)}")
check("E2) 이미 지고 있으면 0", M.slippage_flip(0.10) == 0.0)
check("E3) 슬리피지를 0으로 두되 여유를 같이 적는다고 밝혔다",
      "슬리피지" in flat and "0 으로 둔다" in flat)
check("E4) analyze_knobs 와 같은 방식이라고 잇는다", "--fast" in src)

# =====================================================================
# F) 미래 정보와 처리 방식을 미리 정했는가
# =====================================================================
check("F1) 그 구간 종가에 체결한다고 정했다", "구간 종가에 사고 판다" in flat)
check("F2) 시가 체결이 왜 선견인지 적었다", "선견이 된다" in flat)
check("F3) 조건은 t 까지, 표적은 t+1 부터",
      "조건은 t 구간까지, 표적은 t+1 구간부터" in flat)
check("F4) 빠진 구간은 앞 값을 안 끌어온다", "앞 값을 끌어오지 않는다" in flat)
check("F5) 시장 대비로 본다", "동일가중 평균을 뺀다" in flat)
check("F6) 왜 시장을 빼는지 적었다", "시장이 오른 구간" in flat)
check("F7) 수수료를 모든 거래에 문다", "예외 없다" in flat)

# =====================================================================
# G) 사전 등록임을 밝히는가 - 이 파일의 존재 이유
# =====================================================================
check("G1) 데이터가 한 줄도 없을 때 썼다고 밝힌다",
      "한 줄도 없다" in flat)
check("G2) git log 로 순서를 확인할 수 있다고 적었다", "git log" in flat)
check("G3) 오늘 겪은 실패를 근거로 든다",
      "2025년 한 해가" in flat)
check("G4) 데이터가 쌓이면 반드시 뭔가 보인다고 경고한다",
      "반드시 뭔가 보인다" in flat)
check("G5) 결과 문단이 아직 비어 있다", "결과 - 아직 없음" in src)
check("G6) 필요한 거래일 기준이 박혀 있다",
      M.MIN_DAYS_FOR_VERDICT == 20 and M.MIN_DAYS_FOR_RULES == 60)
check("G7) 대조군 기준이 박혀 있다", M.PERM_ALPHA == 0.05)
check("G8) 데이터가 모자라면 돌려도 뜻이 없다고 막는다",
      "돌려도 뜻이 없습니다" in src)

# =====================================================================
# H) 데이터 읽기 (아직 파일이 없어도 안 터져야 한다)
# =====================================================================
check("H1) 파일이 없어도 빈 목록", isinstance(M.load_min10(), list))
cov = M.coverage([])
check("H2) 빈 입력이면 0일", cov["days"] == 0 and cov["rows"] == 0)
fake = [("20260922", "0930", "005930", 1.0, 2.0, 0.5, 1.5, 10),
        ("20260922", "0940", "005930", 1.5, 1.6, 1.4, 1.5, 5),
        ("20260923", "0930", "000660", 2.0, 2.1, 1.9, 2.0, 7)]
cov2 = M.coverage(fake)
check("H3) 거래일 수를 센다", cov2["days"] == 2, str(cov2))
check("H4) 종목 수를 센다", cov2["codes"] == 2)
check("H5) 첫날/마지막날을 잡는다",
      cov2["first"] == "20260922" and cov2["last"] == "20260923")
check("H6) 하루 평균 구간 수를 낸다", cov2["per_day"] > 0)

# =====================================================================
# I) 안전
# =====================================================================
check("I1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"I2) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# Z) 보유시간 칸과 목표 문턱 (2026-09-22 추가)
# =====================================================================
# 원래 칸이 10/20/30/60분이었는데 실거래 중앙 보유가 140.3분이었다.
# 데이터가 0행인 상태에서 고쳤다는 것을 기록에 남겨둔다.
check("Z1) 보유시간 칸이 실제 범위를 덮는다",
      M.HOLD_BUCKETS == (1, 6, 14, 39), str(M.HOLD_BUCKETS))
check("Z2) 칸 이름이 붙어 있다",
      M.HOLD_LABELS[14] == "140분" and M.HOLD_LABELS[39] == "종가까지")
check("Z3) 실거래 중앙 보유를 근거로 들었다", "140.3" in src)
check("Z4) 데이터 0행에서 고쳤다고 밝혔다",
      "데이터가 0행인 상태에서 고쳤다" in flat)
check("Z5) 결과를 보고 고른 게 아니라고 못박았다",
      "결과를 보고 칸을 고른 것이 아니다" in flat)
check("Z6) 실거래 빈도가 상수다", M.TRIPS_PER_DAY == 3.4)
check("Z7) 목표 연수익률이 상수다", M.TARGET_ANNUAL == 16.8)
check("Z8) 목표 문턱이 0.229%", abs(M.target_gross_per_trip() - 0.229) < 0.002,
      f"{M.target_gross_per_trip():.3f}%")
check("Z9) 목표 문턱이 본전(수수료)보다 높다",
      M.target_gross_per_trip() > M.FEE_ROUND_TRIP)
check("Z10) 본전과 목표가 다른 문턱이라고 적었다",
      "본전만 넘으면" in flat and "목표를 넘어야" in flat)
check("Z11) 빈도가 바뀌면 문턱도 바뀐다고 적었다",
      "실제 빈도로 다시 계산해야 한다" in flat)
check("Z12) 왕복이 0 이면 무한 (0 으로 안 나눈다)",
      M.target_gross_per_trip(trips_per_day=0) == float("inf"))
check("Z13) 자주 거래하면 문턱이 수수료에 가까워진다",
      M.target_gross_per_trip(trips_per_day=100)
      < M.target_gross_per_trip(trips_per_day=1))

# =====================================================================
# Y) 추정값을 실측값으로 바꿨는가 (2026-09-22, explore_min10.py)
# =====================================================================
check("Y1) 실측값이 상수로 있다", M.MEASURED_BAR_RANGE_PCT == 0.646)
check("Y2) 몇 거래일로 쟀는지 같이 박아뒀다", M.MEASURED_DAYS == 1)
check("Y3) 기본값이 실측이다 (추정이 아니다)",
      abs(M.fee_hurdle() - M.fee_hurdle(M.MEASURED_BAR_RANGE_PCT)) < 1e-9)
check("Y4) 실측 문턱이 32.5%", abs(M.fee_hurdle() - 32.5) < 0.1,
      f"{M.fee_hurdle():.2f}%")
check("Y5) 추정 문턱보다 나쁘다 (추정이 크게 잡혀 있었다)",
      M.fee_hurdle() > M.fee_hurdle(M.EST_BAR_RANGE_PCT),
      f"실측 {M.fee_hurdle():.1f}% > 추정 {M.fee_hurdle(M.EST_BAR_RANGE_PCT):.1f}%")
check("Y6) 추정값도 남겨뒀다 (비교용)", M.EST_BAR_RANGE_PCT == 0.93)
check("Y7) 왜 sqrt 어림이 안 맞는지 적었다",
      "시간에 고르게 안 퍼져 있어서" in flat)
check("Y8) 나쁜 쪽으로 틀렸다고 밝혔다", "나쁜 쪽으로 틀렸" in flat)
check("Y9) 1거래일은 표본이 얇다고 적었다", "1거래일은 표본이 얇다" in flat)
check("Y10) 쌓이면 갱신해야 한다고 적었다", "다시 갱신해야 한다" in flat)
check("Y11) explore_min10 이 출처라고 적었다", "explore_min10.py" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
