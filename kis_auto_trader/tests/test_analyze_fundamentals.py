"""analyze_fundamentals.py 검증 - 재무 신호를 공평하게 재는 틀인지.

(2026-09-19 신설) 이 테스트는 **결과가 나오기 전에** 쓴다. 데이터가 아직
29종목뿐이라 돌릴 수 없고, 그래서 지금이 기준을 못 박아두기 가장 좋은
때다. 결과를 본 뒤에 기준을 만들면 어떤 잡음이든 통과시킬 수 있다.

특히 지키는 것
  1) 채택 조건 세 개가 함수로 박혀 있고, 하나라도 빠지면 탈락한다.
     (느슨하게 고치려면 이 테스트가 걸리게 한다)
  2) 시험 개수가 여섯으로 고정돼 있다. 늘리면 다중검정이 다시 커진다.
  3) 미래 정보를 안 본다 (di-1 까지).
  4) 적자/자본잠식/결측 처리가 미리 정한 대로다.
  5) 값이 없는 날 앞의 값을 끌어다 쓰지 않는다.

실행:
  python tests/test_analyze_fundamentals.py
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


import analyze_fundamentals as M  # noqa: E402

src = (REPO_ROOT / "analyze_fundamentals.py").read_text(encoding="utf-8")
flat = " ".join(src.split())

# =====================================================================
# A) 시험 개수를 미리 고정했는가
# =====================================================================
check("A1) 신호가 셋이다 (배당/PER/PBR)",
      tuple(M.SIGNALS) == ("div", "per", "pbr"), str(M.SIGNALS))
check("A2) 방식이 둘이다 (단독 / 저변동과 결합)",
      tuple(M.MODES) == ("alone", "with_lowvol"), str(M.MODES))
check("A3) 그래서 여섯 가지다 (늘리면 다중검정이 다시 커진다)",
      len(M.SIGNALS) * len(M.MODES) == 6)
check("A4) 늘리지 않겠다고 적어뒀다", "늘리지 않는다" in src)
check("A5) 데이터를 보기 전에 썼다고 밝힌다",
      "데이터가 도착하기 전에" in flat)

# =====================================================================
# B) 채택 조건 - 셋 다 넘어야 한다
# =====================================================================
ok_all = dict(start_wins=5, n_starts=5, first_beats=True,
              second_beats=True, perm_p=0.01)
check("B1) 셋 다 넘으면 채택", M.accepted(**ok_all) is True)
check("B2) 시작일 조건에 걸리면 탈락",
      M.accepted(**{**ok_all, "start_wins": 3}) is False)
check("B3) 전반부에서 지면 탈락",
      M.accepted(**{**ok_all, "first_beats": False}) is False)
check("B4) 후반부에서 지면 탈락",
      M.accepted(**{**ok_all, "second_beats": False}) is False)
check("B5) 대조군을 못 넘으면 탈락",
      M.accepted(**{**ok_all, "perm_p": 0.20}) is False)
check("B6) 경계도 정확하다 (4/5 는 통과, 3/5 는 탈락)",
      M.accepted(**{**ok_all, "start_wins": 4}) is True
      and M.accepted(**{**ok_all, "start_wins": 3}) is False)
check("B7) 대조군 경계 (0.05 는 탈락, 0.049 는 통과)",
      M.accepted(**{**ok_all, "perm_p": 0.05}) is False
      and M.accepted(**{**ok_all, "perm_p": 0.049}) is True)
check("B8) 조건을 왜 함수로 박았는지 적어뒀다",
      "느슨하게 만드는 것을 막기 위해서다" in flat)
check("B9) 아깝다고 조건을 고치지 않겠다고 적어뒀다",
      "조건을 고치지 않는다" in flat)

# =====================================================================
# C) 점수 계산 - 방향과 제외 규칙
# =====================================================================
fund = {
    (0, "A"): {"per": 10.0, "pbr": 0.5, "div": 4.0},
    (0, "B"): {"per": -5.0, "pbr": 1.2, "div": 0.0},    # 적자
    (0, "C"): {"per": 20.0, "pbr": -0.3, "div": 2.0},   # 자본잠식
    (0, "D"): {"per": None, "pbr": None, "div": None},  # 값 없음
}
check("C1) 배당은 높을수록 높은 점수",
      M.fund_score(fund, "A", 1, "div") > M.fund_score(fund, "C", 1, "div"))
check("C2) 배당 0 도 점수로 친다 (무배당인 것도 정보다)",
      M.fund_score(fund, "B", 1, "div") == 0.0)
check("C3) PER 은 낮을수록 높은 점수",
      M.fund_score(fund, "A", 1, "per") > M.fund_score(fund, "C", 1, "per"),
      f"A={M.fund_score(fund,'A',1,'per')} C={M.fund_score(fund,'C',1,'per')}")
check("C4) 적자(PER<=0)는 제외한다",
      M.fund_score(fund, "B", 1, "per") is None)
check("C5) PBR 은 낮을수록 높은 점수",
      M.fund_score(fund, "A", 1, "pbr") > M.fund_score(fund, "B", 1, "pbr"))
check("C6) 자본잠식(PBR<=0)은 제외한다",
      M.fund_score(fund, "C", 1, "pbr") is None)
check("C7) 값이 없으면 None", M.fund_score(fund, "D", 1, "per") is None)
check("C8) 기록 자체가 없으면 None",
      M.fund_score(fund, "ZZ", 1, "per") is None)

# 미래 정보 - di-1 을 봐야 한다
check("C9) di-1 의 값을 본다 (당일 값을 안 쓴다)",
      M.fund_score(fund, "A", 1, "div") == 4.0
      and M.fund_score(fund, "A", 0, "div") is None)
check("C10) 코드에도 di - 1 로 찾는다", "fund.get((di - 1, code))" in src)

# 앞의 값을 끌어다 쓰지 않는다
check("C11) 값이 없는 날은 앞 값을 끌어오지 않는다 (없는 정보를 만들지 않음)",
      M.fund_score(fund, "A", 5, "div") is None,
      "di=5 면 di-1=4 에 기록이 없으므로 None 이어야 한다")
check("C12) 그 방침을 적어뒀다", "앞의 값을 끌어다" in flat)

# =====================================================================
# D) 순위 결합
# =====================================================================
rm = M.rank_map([(3.0, "A"), (1.0, "B"), (2.0, "C")])
check("D1) 점수가 높을수록 1등(0)", rm["A"] == 0 and rm["C"] == 1 and rm["B"] == 2,
      str(rm))
check("D2) 결합은 등수 평균이다 (단위가 다른 값을 직접 더하지 않는다)",
      "(fr[c] + vr[c]) / 2" in src)
check("D3) 왜 등수로 맞추는지 적어뒀다", "값의 단위가 다르므로" in flat)

# =====================================================================
# E) 지표 계산
# =====================================================================
check("E1) 최대낙폭은 고점 대비다",
      abs(M.mdd([100, 120, 60, 80]) - (-50.0)) < 1e-9)
check("E2) 우상향이면 낙폭 0", abs(M.mdd([100, 110, 120])) < 1e-9)
check("E3) 제자리면 연환산 0",
      abs(M.annualized([100.0] * 246, capital=100.0)) < 1e-6)
check("E4) 빈 곡선이어도 안 터진다", M.annualized([]) == 0.0)

# =====================================================================
# F) 데이터가 모자라면 돌리지 않는다
# =====================================================================
check("F1) 종목이 적으면 막는 선이 있다", "cov[\"codes\"] < 500" in src)
check("F2) 그 경우 수집하라고 안내한다", "KRX 데이터 수집.bat" in src)
cov = M.coverage({(1, "A"): {}, (2, "A"): {}, (1, "B"): {}},
                 ["20210104", "20210105", "20210106"])
check("F3) 커버리지를 종목/날짜로 센다",
      cov["codes"] == 2 and cov["days"] == 2, str(cov))
check("F4) 비어 있어도 안 터진다",
      M.coverage({}, ["20210104"])["codes"] == 0)

# =====================================================================
# G) 안전 / 미래 정보
# =====================================================================
check("G1) 종목 선정은 그 시점 정보로만 한다",
      "S.universe_at(panel, di" in src)
check("G2) 저변동 점수도 같은 규칙을 쓴다",
      'S.factor_score(panel, c, di, "low_vol")' in src)
check("G3) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"G4) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# H) 문서
# =====================================================================
check("H1) 왜 이것만 남았는지 적었다",
      "선정 차원에서 아직 안 써본 재료가 재무지표뿐" in flat)
check("H2) 가격에서 유도할 수 없는 정보라는 점을 짚었다",
      "가격에서 유도할 수 없는 정보" in flat)
check("H3) 결과를 채웠다 (데이터 도착 후)",
      "1,780종목" in src and "결과 - 아직 없음" not in src)
check("H4) 내 선행참조 버그가 반띵을 통과했던 것을 근거로 든다",
      "선행참조 버그가 만든 결과가 반띵 검증까지 통과했다" in flat)
check("H5) 적자/자본잠식을 빼는 것도 선택이라고 밝힌다",
      "빼는 것 자체가 선택이므로 밝혀둔다" in flat)


# =====================================================================
# I) 결과가 들어온 뒤에 붙인 검사 (2026-09-21)
#     통과한 결과일수록 더 깐깐하게 본다. 여기서 보는 것은 '숫자가
#     맞나' 가 아니라 **통과를 만들려고 규칙을 손댔나** 다.
# =====================================================================
check("I1) 채택 조건이 그대로다 (결과를 보고 느슨하게 안 바꿨다)",
      M.MIN_START_WINS == 4 and M.PERM_ALPHA == 0.05 and M.N_PERM == 500)
check("I2) 시험한 가짓수가 그대로 6개다",
      len(M.SIGNALS) * len(M.MODES) == 6)
check("I3) accepted 가 셋을 모두 요구한다",
      M.accepted(4, 5, True, True, 0.001) is True
      and M.accepted(3, 5, True, True, 0.001) is False
      and M.accepted(5, 5, False, True, 0.001) is False
      and M.accepted(5, 5, True, False, 0.001) is False
      and M.accepted(5, 5, True, True, 0.20) is False)

check("I4) 결과표에 여섯 줄이 다 있다",
      all(t in src for t in ("16.6", "19.0", "15.2", "26.4", "18.1", "29.7")))
check("I5) 단독으로는 전부 진다는 것을 밝힌다", "여섯 중 여섯이 진다" in flat)
check("I6) 재무가 저변동을 대체하지 않는다고 정리한다",
      "대체하지 않고 보완한다" in flat)
check("I7) 반띵 결과를 적었다",
      "31.3 / 16.9" in src and "33.6 / 16.9" in src)
check("I8) 대조군 p 값을 적었다", "p = 0.0020" in src)
check("I9) 사전 등록 기준을 처음 통과했다고 밝힌다",
      "통과한 것은 이번이 처음이다" in flat)

check("I10) 생존편향을 다시 확인했다",
      "생존편향이 다시 들어왔나" in flat and "1,615" in src and "165" in src)
check("I11) 폐지 종목 비율을 숫자로 댔다", "(98%)" in src and "(96%)" in src)
check("I12) 필터인지 순위인지 갈랐다",
      "버는 것이 '순위' 인가 '필터' 인가" in flat)
check("I13) 필터만 쓰면 진다는 대조 결과를 적었다",
      "17.1" in src and "19.5" in src and "필터만 쓰면 오히려 진다" in flat)
check("I14) 미래 정보를 안 쓴다고 다시 밝힌다", "di-1 까지만 읽는다" in flat)

check("I15) 낙폭이 나빠진다는 것을 숨기지 않았다",
      "-18.9%" in src and "-20.0%" in src and "맞교환이다" in flat)
check("I16) 사전 등록에 낙폭이 빠졌다고 스스로 밝힌다",
      "내 사전 등록의 구멍" in flat)
check("I17) 뒤늦게 조건을 추가하지 않겠다고 밝힌다",
      "조건을 추가해 탈락시키면" in flat and "규칙을 스스로 어기는" in flat)
# (2026-09-21 고침) 처음에는 "맞교환이니 사용자가 정할 일" 로 적었다.
# 그 뒤 연도별을 재보니 +7.4%p 자체가 2025년 한 해였다. 그래서 '켤지
# 말지' 가 아니라 '안 켠다' 가 됐다. 근거는 J 절이 본다.
check("I18) 판정은 남기되 켜지는 않는다고 밝힌다",
      "판정은 '통과' 로 둔다" in flat and "다만 켜지 않는다" in flat)
check("I19) 저변동 때와 달리 공짜가 아니라고 잇는다",
      "수익도 낙폭도 둘 다 좋았다" in flat)
check("I20) 이득이 후반부에 크다는 것을 밝힌다", "후반부에 크다" in flat)
check("I21) 저장소 전체 다중검정도 밝힌다", "80가지 넘게" in flat)
check("I22) 아직 strategy.py 에 안 넣었다고 밝힌다",
      "아직 strategy.py 에 넣지 않았다" in flat)

# 반띵/대조군이 문구만 있고 코드가 없던 상태였다. 실제로 도는지 본다.
check("I23) 무작위 대조군 함수가 있다", hasattr(M, "run_random"))
check("I24) p 값 함수가 있다", hasattr(M, "control_p"))
check("I25) 반띵 함수가 있다", hasattr(M, "split_half"))
check("I26) p 가 0 이 되지 않는다 (+1 보정)",
      "(hits + 1) / (n_perm + 1)" in src)
check("I27) 대조군이 같은 후보 풀을 쓴다",
      "S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)" in src)
check("I28) 대조군 씨앗이 고정이다 (돌릴 때마다 바뀌면 p 를 못 믿는다)",
      "random.Random(seed)" in src and M.SEED == 20260919)


# =====================================================================
# J) 연도별 지속성 (2026-09-21) - 세 조건이 독립이 아니었다
#     사용자가 "수익 7.4%에 낙폭 3%면 감안할 만하다" 고 했고, 그 계산은
#     맞았다. 틀린 것은 +7.4%p 라는 전제였다. 해마다 쪼개니 2025년
#     하나가 전부였다. 이 절은 그 교훈이 지워지지 않게 한다.
# =====================================================================
check("J1) 연도별 함수가 있다", hasattr(M, "by_year"))
check("J2) 최고 해를 빼는 함수가 있다", hasattr(M, "one_year_story"))
pos, rest = M.one_year_story([1.7, -8.4, 8.3, 41.3, -15.8])
check("J3) 양수인 해를 센다", pos == 3, str(pos))
check("J4) 최고 해를 빼면 나머지 평균이 음수가 된다",
      abs(rest - (-3.55)) < 0.01, f"{rest:.2f}")
check("J5) 한 해짜리면 최고 해를 뺀 나머지가 확 떨어진다",
      M.one_year_story([0.0, 0.0, 100.0])[1] == 0.0)
check("J6) 해가 하나뿐이면 안 터진다", M.one_year_story([5.0]) == (0, 0.0))

check("J7) 연도표를 문서에 적었다",
      "+41.3" in src and "-15.8" in src and "+8.3" in src)
check("J8) pbr 이 2025년 한 해짜리라고 못박는다",
      "2025년 한 해가 전부다" in flat)
check("J9) 최고 해를 빼면 기준보다 나쁘다고 적었다",
      "-3.6%p" in src and "-2.0%p" in src)
check("J10) 저변동 6/6 과 나란히 놓았다",
      "6/6 해 양수였다" in flat and "+7.908" in src)
check("J11) 성격이 다르다고 정리한다",
      "저변동은 매년 벌고" in flat)

check("J12) 세 조건이 독립이 아니었다고 스스로 밝힌다",
      "서로 독립이 아니어서다" in flat)
check("J13) 왜 독립이 아닌지 셋을 다 설명한다",
      "다섯 개가 전부 2025년을 통과한다" in flat
      and "후반부가 2025년을 통째로 품는다" in flat
      and "전 구간을 한 덩어리로 본다" in flat)
check("J14) 같은 실수를 전에도 지적했었다고 잇는다",
      "거울상" in flat and "여기서 똑같이 했다" in flat)
check("J15) 앞으로 연도별을 조건에 넣겠다고 적었다",
      "연도별 지속성" in flat and "채택 조건에 넣는다" in flat)

check("J16) 골대 옮기기와 기존 기준 적용을 구별한다",
      "골대 옮기기다. 안 한다" in flat
      and "골대 옮기기가 아니다" in flat)
check("J17) 안 켜는 진짜 이유를 명확히 한다",
      "+7.4%p 가 애초에 없어서" in flat and "한 해짜리다" in flat)
check("J18) 판정은 통과로 남겨둔다 (사후 변경 안 함)",
      "판정은 '통과' 로 둔다" in flat)
check("J19) 밸류업 가능성을 제기하되 증명은 아니라고 밝힌다",
      "밸류업" in src and "증명한 것은 아니다" in flat)
check("J20) 정책이면 되풀이 근거가 없다고 적었다",
      "되풀이된다고 볼 근거가 없다" in flat)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
