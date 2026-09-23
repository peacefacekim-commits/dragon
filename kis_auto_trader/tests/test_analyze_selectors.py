"""analyze_selectors.py 검증 - 사전 등록을 지켰는가.

(2026-09-21 신설) 이 파일의 채점 기준은 **결과보다 먼저 커밋됐다**
(52cad5b). 그러니 여기서 제일 중요한 검사는 '숫자가 맞나' 가 아니라
**결과를 보고 기준을 손댔나** 다.

바로 앞 파일(analyze_fundamentals)에서 1~3번 조건을 다 통과한 신호가
해마다 쪼개니 한 해짜리였다. 그래서 4번(연도별)이 추가됐다. 이 테스트는
그 네 개가 다 살아 있는지를 본다.

실행:
  python tests/test_analyze_selectors.py
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


import analyze_selectors as M  # noqa: E402

src = (REPO_ROOT / "analyze_selectors.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes, opens=None):
        self.close = list(closes)
        self.open = list(opens if opens is not None else closes)
        self.pos = {i: i for i in range(len(closes))}


# =====================================================================
# A) 무엇을 시험하는지 미리 고정했는가
# =====================================================================
check("A1) 다섯 가지다 (늘리면 다중검정이 커진다)", len(M.SIGNALS) == 5,
      str(M.SIGNALS))
check("A2) 시가총액이 들어 있다 (안 써본 데이터)", "size" in M.SIGNALS)
check("A3) 늘리지 않겠다고 적어뒀다", "늘리지 않는다" in flat)
check("A4) 방향을 미리 고정했다 (양방향을 안 본다)",
      "한 방향만 본다" in flat)
check("A5) 왜 그 방향인지 근거를 댔다",
      "큰 손해를 피한다" in flat)
check("A6) 저변동 결합만 본다고 못박았다", "alone 은 안 본다" in flat)
check("A7) 그 이유로 재무 결과를 든다", "여섯 중 여섯이 졌다" in flat)

# =====================================================================
# B) 14개 지표를 왜 못 쓰는지 갈랐는가 - 사용자 질문의 핵심
# =====================================================================
check("B1) 14개가 시장 전체 값이라 선정에 못 쓴다고 밝힌다",
      "하루에 한 줄, 시장 전체" in flat)
check("B2) 그래서 타이밍으로만 썼다고 잇는다",
      "타이밍으로만 썼고" in flat)
check("B3) 종목별 데이터 넷을 나열하고 무엇이 안 쓰였는지 짚는다",
      "krx_cap" in src and "한 번도 안 썼다" in flat)
check("B4) krx_cap 범위를 숫자로 댔다", "226만행" in src)

# =====================================================================
# C) 1단계 - 재포장 걸러내기
# =====================================================================
check("C1) 문턱이 0.70 으로 박혀 있다", M.REDUNDANT_CORR == 0.70)
check("C2) 문턱 이상이면 재포장", M.redundant(0.71) and M.redundant(-0.75))
check("C3) 문턱 미만이면 새 정보",
      not M.redundant(0.69) and not M.redundant(-0.5))
check("C4) 경계값은 재포장으로 친다", M.redundant(0.70))
check("C5) 부호와 무관하게 절댓값으로 본다", M.redundant(-0.80))
check("C6) 왜 문턱을 미리 박았는지 적어뒀다",
      "0.75 면 그래도 다르지" in flat)
check("C7) analyze_consensus 와 잇는다", "6.3개" in src)

# 순위상관이 실제로 맞나
a = {"x": 1.0, "y": 2.0, "z": 3.0}
check("C8) 같은 순서면 +1", abs(M.spearman(a, a) - 1.0) < 1e-9)
check("C9) 뒤집힌 순서면 -1",
      abs(M.spearman(a, {"x": 3.0, "y": 2.0, "z": 1.0}) - (-1.0)) < 1e-9)
check("C10) 표본이 너무 적으면 0", M.spearman({"x": 1.0}, {"x": 1.0}) == 0.0)

# =====================================================================
# D) 2단계 - 채택 조건이 넷이고 하나라도 빠지면 탈락
# =====================================================================
ok = dict(start_wins=5, first_beats=True, second_beats=True, perm_p=0.01,
          years_pos=4, years_total=5, rest_mean=2.0)
check("D1) 넷 다 넘으면 채택", M.accepted(**ok) is True)
check("D2) 시작일에서 걸리면 탈락",
      M.accepted(**{**ok, "start_wins": 3}) is False)
check("D3) 전반부에서 지면 탈락",
      M.accepted(**{**ok, "first_beats": False}) is False)
check("D4) 후반부에서 지면 탈락",
      M.accepted(**{**ok, "second_beats": False}) is False)
check("D5) 대조군을 못 넘으면 탈락",
      M.accepted(**{**ok, "perm_p": 0.2}) is False)
check("D6) 양수인 해가 과반이 아니면 탈락",
      M.accepted(**{**ok, "years_pos": 2}) is False)
check("D7) 최고 해를 빼서 음수면 탈락 (한 해짜리 거르기)",
      M.accepted(**{**ok, "rest_mean": -3.6}) is False)
check("D8) 연도 자료가 없으면 탈락", M.accepted(**{**ok, "years_total": 0}) is False)
check("D9) 조건 4 가 왜 생겼는지 적어뒀다",
      "한 해가 전부였다" in flat and "서로 독립이 아니었기" in flat)
check("D10) 저변동이 6/6 이었다고 견준다", "6/6 으로 통과했다" in flat)
check("D11) 아깝다고 조건을 고치지 않겠다고 적었다",
      "조건을 고치지 않는다" in flat)

# =====================================================================
# E) 점수 계산 - 방향과 미래 정보
# =====================================================================
# 톱니(100 + j%5)로 만들면 하락폭이 매번 똑같아서 하방변동성이 0 이 된다.
# 하락폭이 실제로 제각각이고, b 가 a 의 3배로 흔들리는 판을 만든다.
N = 300
_R = [0.012, -0.004, 0.006, -0.015, 0.009, -0.002, 0.011, -0.008, 0.003, -0.011]


def _walk(scale):
    px, out = 100.0, []
    for j in range(N):
        px *= 1 + _R[j % len(_R)] * scale
        out.append(px)
    return out


panel = {"a": FakeSeries(_walk(1.0)), "b": FakeSeries(_walk(3.0))}
cap = {}
for di in range(N):
    cap[(di, "a")] = {"cap": 1e11, "tvalue": 1e8, "shares": 1e6}
    cap[(di, "b")] = {"cap": 1e12, "tvalue": 1e8, "shares": 1e6}
check("E1) 시총이 작을수록 높은 점수",
      M.sel_score(panel, cap, "a", 100, "size")
      > M.sel_score(panel, cap, "b", 100, "size"))
check("E2) 회전율이 낮을수록 높은 점수",
      M.sel_score(panel, cap, "b", 100, "turnover")
      > M.sel_score(panel, cap, "a", 100, "turnover"))
check("E3) 시총이 0 이하면 제외",
      M.sel_score(panel, {(99, "a"): {"cap": 0.0, "tvalue": 1.0}},
                  "a", 100, "size") is None)
check("E4) 기록이 없으면 제외", M.sel_score(panel, {}, "a", 100, "size") is None)
check("E5) 덜 흔들리는 쪽이 하방변동성 점수가 높다",
      M.sel_score(panel, cap, "a", 200, "downside")
      > M.sel_score(panel, cap, "b", 200, "downside"))
check("E6) 낙폭이 작을수록 높은 점수 (0 에 가까울수록)",
      M.sel_score(panel, cap, "a", 200, "past_mdd")
      > M.sel_score(panel, cap, "b", 200, "past_mdd"))
check("E7) 우상향만 하면 과거 낙폭이 0",
      abs(M.sel_score({"c": FakeSeries([100.0 * (1.001 ** j)
                                        for j in range(N)])},
                      cap, "c", 200, "past_mdd")) < 1e-9)
check("E8) 자료가 모자라면 None (앞 값을 끌어오지 않는다)",
      M.sel_score(panel, cap, "a", 5, "downside") is None)
check("E9) di-1 까지만 본다", "s.pos.get(di - 1)" in src)
check("E10) 시총도 di-1 을 본다", 'cap.get((di - 1, code))' in src)
check("E11) 모르는 신호면 None", M.sel_score(panel, cap, "a", 100, "없음") is None)

# 베타
mkt = [0.01 if k % 2 else -0.01 for k in range(M.BETA_DAYS)]
check("E12) 시장 수익률이 없으면 베타를 못 낸다",
      M.sel_score(panel, cap, "a", 200, "beta", None) is None)
check("E13) 길이가 안 맞으면 None",
      M.sel_score(panel, cap, "a", 200, "beta", mkt[:5]) is None)
check("E14) 시장을 패널 안에서 만든다 (지수를 안 들여온다)",
      "지수를 따로 안 쓴다" in flat)

# =====================================================================
# F) 결과 - 다섯 다 탈락
# =====================================================================
check("F1) 1단계 상관값을 적었다",
      all(t in src for t in ("-0.722", "+0.788", "+0.834", "+0.537", "+0.530")))
check("F2) 셋이 재포장이었다고 밝힌다", "다섯 중 셋이 저변동의 다른 이름" in flat)
check("F3) size 의 음수 부호를 해석했다",
      "시가총액이" in flat and "작을수록 변동성이 크다" in flat)
check("F4) 소형주 = 고변동이라는 결론을 잇는다",
      "고변동을 고른다' 와 거의 같다" in flat and "-41.5%" in src)
check("F5) downside 가 걸린 뜻도 적었다", "같은 것을 재고 있었다" in flat)
check("F6) 2단계 성과를 적었다",
      "20.0" in src and "17.7" in src and "-19.2" in src and "-19.5" in src)
check("F7) 둘 다 조건 1 에서 탈락했다고 밝힌다",
      "조건 1(4/5)에서 탈락했다" in flat)
check("F8) 맞교환조차 없다고 짚는다", "맞교환조차 없다" in flat)
check("F9) 베타가 진 것이 뜻밖이라고 적고 해석한다",
      "조금 뜻밖이다" in flat and "작동하는 쪽은 후자다" in flat)
check("F10) 실제로 성과를 잰 것은 2개라고 밝힌다",
      "실제로 성과를 잰 것은 2개" in flat)
check("F11) 이제 선정 신호를 다 써봤다고 정리한다",
      "다 써봤다" in flat and "새 데이터를 구하는 것뿐이다" in flat)
check("F12) 2021~2026 한계를 밝힌다", "2021~2026" in src)
check("F13) 결과가 없다는 문단이 지워졌다", "결과 - 아직 없음" not in src)
check("F14) 기준을 먼저 커밋했다고 밝힌다",
      "결과가 나오기 전에" in flat and "git log" in flat)

# =====================================================================
# G) 조건이 다른 곳과 같은가
# =====================================================================
check("G1) 자본이 공용 상수", M.CAPITAL == 2_000_000)
check("G2) 주기/종목수가 채택안과 같다", M.PERIOD == 120 and M.PICK == 10)
check("G3) 시작일 5개", M.N_STARTS == 5)
check("G4) 대조군 500회", M.N_PERM == 500)
check("G5) 대조군은 재무 쪽 것을 그대로 쓴다 (같은 자)",
      "F.control_p(" in src)
check("G6) 기준선도 같은 run_calendar 를 쓴다", "E.run_calendar(" in src)
check("G7) 후보 풀이 같다", "S.universe_at(panel, di" in src)

# =====================================================================
# H) 안전
# =====================================================================
check("H1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"H2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
