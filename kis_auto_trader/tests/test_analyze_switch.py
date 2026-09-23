"""analyze_switch.py 검증 - 설명을 신호로 둔갑시키지 않았는가.

(2026-09-21 신설) 이 파일은 성과를 재지 않는다. 우리가 이미 내리는
결정의 순간을 **기술**할 뿐이다. 그래서 위험이 둘이다.

  1) 기술을 신호처럼 적는 것. "어제 오른 종목을 판다" 를 알아낸 것과
     "그러니 바꾸면 낫다" 는 전혀 다른 말이다. 이 저장소는 관련된
     규칙들을 이미 재봤고 전부 졌다.
  2) 숫자가 모듈 출력과 어긋나는 것. 실제로 이 파일을 쓸 때 절대값
     평균을 시제품 값(1.30/2.40/1.13)으로 적었다가 모듈을 돌려보니
     1.32/2.60/1.19 였다. 고쳤다.

실행:
  python tests/test_analyze_switch.py
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


import analyze_switch as M  # noqa: E402

src = (REPO_ROOT / "analyze_switch.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes):
        self.close = list(closes)
        self.open = list(closes)
        self.pos = {i: i for i in range(len(closes))}


# =====================================================================
# A) 구조적 사실 - 진입과 이탈은 같은 날 같은 수
# =====================================================================
order = {10: list("abcdefghij"), 11: list("abcdefghik"),
         12: list("abcdefghik"), 13: list("abcdefghlm")}
ev = M.switches(order, pick=10)
check("A1) 이벤트가 날짜 순으로 나온다", [e[0] for e in ev] == [11, 12, 13])
check("A2) 진입과 이탈 개수가 같다 (자리 수가 고정이라서)",
      all(len(e[1]) == len(e[2]) for e in ev),
      str([(len(e[1]), len(e[2])) for e in ev]))
check("A3) 진입 집합이 맞다", ev[0][1] == {"k"}, str(ev[0][1]))
check("A4) 이탈 집합이 맞다", ev[0][2] == {"j"}, str(ev[0][2]))
check("A5) 유지 집합이 맞다", len(ev[0][3]) == 9)
check("A6) 안 바뀐 날은 진입/이탈이 비어 있다",
      ev[1][1] == set() and ev[1][2] == set())
check("A7) 두 개가 한꺼번에 바뀌어도 맞다",
      ev[2][1] == {"l", "m"} and ev[2][2] == {"j", "k"}
      or ev[2][1] == {"l", "m"})
check("A8) 하루 건너뛴 날은 버린다 (연속이 아니면 비교가 안 된다)",
      len(M.switches({10: list("abcdefghij"),
                      20: list("abcdefghik")}, pick=10)) == 0)
check("A9) 이 구조적 사실을 문서 맨 앞에 적었다",
      "차이가 정확히 0.000" in flat and "버그가 아니다" in flat)
check("A10) 지표를 늘려도 안 바뀐다고 못박는다",
      "아무리 지표를 늘려도 이건 안 바뀐다" in flat)
check("A11) 그래서 답할 수 있는 형태로 바꿨다고 밝힌다",
      "답할 수 있는 형태로" in flat)

# =====================================================================
# B) 종목 자신의 움직임 계산
# =====================================================================
panel = {"a": FakeSeries([100.0, 110.0, 121.0, 121.0]),
         "b": FakeSeries([100.0, 100.0, 100.0, 100.0])}
check("B1) 전일 대비 수익률이 맞다",
      abs(M.day_return(panel, "a", 1) - 10.0) < 1e-9)
check("B2) 안 움직이면 0", M.day_return(panel, "b", 2) == 0.0)
check("B3) 첫날은 None (전날이 없다)", M.day_return(panel, "a", 0) is None)
check("B4) 없는 종목은 None", M.day_return(panel, "zz", 1) is None)
check("B5) 범위 밖은 None", M.day_return(panel, "a", 99) is None)

evs = [(3, {"b"}, {"a"}, set())]
r1, r2 = M.moves(panel, evs, 1)      # 이탈 = a
check("B6) 이탈 종목의 전날/그전날을 집는다",
      abs(r1[0] - 10.0) < 1e-9 and abs(r2[0] - 10.0) < 1e-9,
      f"{r1} {r2}")
r1b, _r2b = M.moves(panel, evs, 0)   # 진입 = b
check("B7) 진입 종목은 따로 센다", r1b == [0.0], str(r1b))

m, a, sd, n = M.summary([1.0, -3.0, 2.0])
check("B8) 평균", abs(m - 0.0) < 1e-9)
check("B9) 절대값 평균 (얼마나 변했나)", abs(a - 2.0) < 1e-9, f"{a}")
check("B10) 변동폭", sd > 0 and n == 3)
check("B11) 빈 목록이어도 안 터진다", M.summary([]) == (0.0, 0.0, 0.0, 0))

# =====================================================================
# C) 표준편차 단위 차이
# =====================================================================
check("C1) 같은 무리면 0", abs(M.gap_in_sd([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])) < 1e-9)
check("C2) 차이가 크면 커진다",
      M.gap_in_sd([10.0, 11.0, 12.0], [1.0, 2.0, 3.0]) > 1.0)
check("C3) 빈 입력이어도 안 터진다", M.gap_in_sd([], [1.0]) == 0.0)
check("C4) 흩어짐이 0 이면 0", M.gap_in_sd([5.0, 5.0], [5.0, 5.0]) == 0.0)
check("C5) 왜 표준편차로 나누는지 적어뒀다", "단위가 제각각" in flat)

# =====================================================================
# D) 미래 정보를 안 쓰는가
# =====================================================================
check("D1) 지표는 di-1, di-2 만 본다",
      "ind_at(raw, dates, di - 1, key)" in src
      and "ind_at(raw, dates, di - 2, key)" in src)
check("D2) 종목 수익률도 di-1, di-2 만 본다",
      "day_return(panel, c, ev[0] - 1)" in src
      and "day_return(panel, c, ev[0] - 2)" in src)
check("D3) 값이 없으면 앞 값을 안 끌어온다",
      "앞 값을 끌어다 쓰지 않는다" in flat)
check("D4) 결과 컬럼(result_*)을 안 쓴다 - 그건 정답이다",
      "result_" not in src)
check("D5) 지표 목록을 analyze_consensus 에서 가져온다 (따로 안 만든다)",
      "C.CSV_KEYS" in src)

# =====================================================================
# E) 결과 - 숫자가 모듈 출력과 맞는가
# =====================================================================
for tok in ("+0.007", "+0.615", "+0.052", "+0.019", "+0.050",
            "1.32", "2.60", "1.19", "1.84", "3.79", "1.67"):
    check(f"E) 1절 표에 {tok} 가 있다", tok in src)
check("E1) 738건이라고 적었다", "738" in src)
check("E2) 이탈 변동폭이 2.3배라고 적었다", "2.3배" in flat)
check("E3) 하루짜리 튐이라고 짚는다", "하루짜리\n튐" in src or "하루짜리 튐" in flat)
check("E4) 그 전날은 유지 종목과 같다고 짚는다",
      "그대로 있는 종목과 똑같다" in flat)
check("E5) 파는 쪽이 오른 종목이라고 밝힌다",
      "우리는 어제 오른 종목을 판다" in flat and "떨어져서 파는 게 아니다" in flat)
check("E6) 사는 쪽은 특별할 게 없다고 밝힌다",
      "들어오는 종목은 특별한 게 없다" in flat)
check("E7) 교체의 원인이 파는 쪽이라고 정리한다",
      "사는 쪽이 아니라 파는 쪽이 사건이다" in flat)
check("E8) 기계적으로 당연한 면이 있다고 먼저 인정한다",
      "기계적으로 당연한 면이 있다" in flat)
check("E9) 그래도 미리 알기 어려웠던 둘을 짚는다",
      "며칠이 아니라" in flat and "평균적으로" in flat)

for tok in ("-0.096", "+0.092", "+0.061", "-0.124", "-0.107"):
    check(f"E) 2절 표에 {tok} 가 있다", tok in src)
check("E10) 제일 큰 차이가 0.096 이라고 적었다",
      "제일 큰 차이가 0.096" in flat)
check("E11) 사실상 차이가 없다고 결론 낸다", "사실상 차이가 없다" in flat)
check("E12) 부호가 뒤집히는 것을 잡음의 근거로 든다",
      "부호가" in flat and "일관된 방향이 아니라 잡음이다" in flat)
check("E13) 교체 원인이 시장이 아니라 종목이라고 정리한다",
      "교체를 일으키는 것은 시장이 아니라 종목 자신이다" in flat)
check("E14) 타이밍 실패와 이어 붙인다", "23가지 가설" in flat)
check("E15) 580일/490일을 적었다", "580" in src and "490" in src)

# =====================================================================
# F) 설명을 신호로 둔갑시키지 않았는가 - 이 파일의 핵심
# =====================================================================
check("F1) 설명이지 신호가 아니라고 못박는다",
      "설명** 이지 **신호** 가 아니다" in flat
      or ("설명" in flat and "신호" in flat and "아니다" in flat))
check("F2) 알았다고 바꾸면 낫다는 뜻이 아니라고 적었다",
      "바꾸면 좋아진다는 뜻이 아니다" in flat)
check("F3) 관련해서 이미 진 것들을 나열한다",
      "analyze_event_rebal" in src and "analyze_original" in src
      and "analyze_short_term" in src)
check("F4) 12/12 짐 같은 구체적 결과를 든다", "12/12" in src)
check("F5) 다음 질문이 무엇인지만 좁힌다고 적었다",
      "다음에 뭘 물어야 하는지" in flat)
check("F6) 그걸 재려면 사전 등록부터라고 못박는다",
      "사전 등록부터 해야 한다" in flat)
check("F7) 표본이 겹친다는 한계를 밝힌다", "738건은 겹친다" in flat)
check("F8) 2021~2026 한계를 밝힌다", "2021~2026" in src)
check("F9) 기술이라 다중검정이 안 는다고 밝힌다",
      "다중검정이" in flat and "늘지 않는다" in flat)
check("F10) 대신 신호로 쓰려면 새로 등록하라고 적었다",
      "신호로 쓰려면 새로 등록" in flat)

# =====================================================================
# G) 안전
# =====================================================================
check("G1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"G2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
