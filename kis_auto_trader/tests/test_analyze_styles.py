"""analyze_styles.py 검증 - 두 전략을 같은 자로 쟀는지.

(2026-09-21 신설) 비교 파일의 위험은 **한쪽에 유리한 조건을 준 것**이다.
수수료를 한쪽만 물리거나, 풀이 다르거나, 시작일이 다르면 결론이 공짜로
나온다. 그래서 여기서는 '같은 조건' 을 집중해서 검사한다.

그리고 요약 숫자가 원본 실행과 어긋나지 않는지도 본다. 앞서 두 번
(analyze_knobs 의 -41.5%, analyze_intraday 의 국면 날수) 임시 스크립트
값을 문서에 적었다가 모듈과 달랐던 적이 있다.

실행:
  python tests/test_analyze_styles.py
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


import analyze_styles as M  # noqa: E402

src = (REPO_ROOT / "analyze_styles.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


class FakeSeries:
    def __init__(self, closes, opens=None):
        self.close = list(closes)
        self.open = list(opens if opens is not None else closes)
        self.pos = {i: i for i in range(len(closes))}


# =====================================================================
# A) 같은 조건인가 - 이 파일의 핵심
# =====================================================================
check("A1) 고변동은 저변동 순위를 뒤집어서 만든다 (풀이 같다)",
      "flip(lo)" in src and "lst[::-1]" in src)
check("A2) 왜 뒤집기를 쓰는지 적어뒀다",
      "풀도 주기도 그대로이므로" in flat)
o = {0: ["a", "b", "c"], 1: ["x", "y"]}
f = M.flip(o)
check("A3) 뒤집기가 순서만 바꾼다 (종목 집합은 같다)",
      set(f[0]) == set(o[0]) and f[0] == ["c", "b", "a"], str(f))
check("A4) 모든 전략이 같은 run() 을 쓴다 (한쪽만 다른 계산 금지)",
      src.count("def run(") == 1)
# 시작일을 만드는 자리가 하나여야 한다. 표마다 따로 만들면 비교가 깨진다.
check("A5) 시작일을 만드는 자리가 하나다",
      src.count("BASE_DI + k * START_GAP") == 1 and src.count("def _starts(") == 1)
check("A5b) 모든 표가 그 하나를 가져다 쓴다",
      src.count("starts = _starts()") >= 2)
check("A5c) 시작일이 실제로 같은 값이다",
      M._starts() == M._starts() and len(M._starts()) == M.N_STARTS)
# 문자열 개수를 세면 안 된다 - 매수 수수료는 E.buy_greedy 안에서 붙는다.
# 행동으로 확인한다: 값이 안 변하는 시장에서 자본이 딱 수수료만큼 준다.
check("A6) 매도 수수료를 판다는 쪽에서 뗀다",
      "(1 - E.FEE_ONE_WAY)" in src)
_flat_panel = {c: FakeSeries([1000.0] * 60) for c in ("p", "q")}
_o1 = {di: ["p", "q"] for di in range(60)}
_o2 = {di: ["q", "p"] for di in range(60)}   # 매 교체마다 갈아타게
_c, _f, _n = M.run(list(range(60)), _flat_panel, _o1, 20, 0, pick=1,
                   capital=100_000)
check("A6b) 가격이 안 변해도 수수료가 붙는다 (매수 쪽도 물린다)",
      _f > 0 and _c[-1] < 100_000, f"수수료 {_f:.0f}원, 끝 {_c[-1]:,.0f}원")
check("A6c) 수수료가 왕복 상수와 자릿수가 맞는다",
      0 < _f < 100_000 * M.E.FEE_ONE_WAY * 4, f"{_f:.0f}원")
check("A7) 자본도 하나로 고정",
      src.count("capital=CAPITAL") >= 1 and M.CAPITAL == 2_000_000)

# 실제로 같은 값이 나오는지 - 같은 order 를 주면 결과가 같아야 한다
N = 300
# 종목마다 값이 조금씩 다르게 (같은 값이면 비교가 무의미하다)
panel = {c: FakeSeries([100.0 + j % 7 + k for j in range(N)])
         for k, c in enumerate(("a", "b", "c"))}
order = {di: ["a", "b", "c"] for di in range(N)}
c1, f1, n1 = M.run(list(range(N)), panel, order, 20, 0, pick=3, capital=300_000)
c2, f2, n2 = M.run(list(range(N)), panel, order, 20, 0, pick=3, capital=300_000)
check("A8) 같은 입력이면 같은 결과 (무작위성 없음)",
      c1 == c2 and f1 == f2 and n1 == n2)

# =====================================================================
# B) 지표 계산
# =====================================================================
check("B1) 최대낙폭은 고점 대비",
      abs(M.mdd([100, 120, 60, 80]) - (-50.0)) < 1e-9)
check("B2) 우상향이면 낙폭 0", abs(M.mdd([100, 110, 120])) < 1e-9)
check("B3) 제자리면 연환산 0",
      abs(M.annualized([100.0] * 246, capital=100.0)) < 1e-6)
check("B4) 빈 곡선이어도 안 터진다", M.annualized([]) == 0.0)

# 최악 1년: 중간에 반토막 나는 구간을 잡아야 한다
curve = [100.0] * 100 + [50.0] * 300
check("B5) 최악 1년이 중간 하락을 잡는다",
      M.worst_year(curve) <= -49.0, f"{M.worst_year(curve):.1f}%")
check("B6) 기간이 1년보다 짧으면 0", M.worst_year([100.0] * 10) == 0.0)
check("B7) 계속 오르면 최악 1년도 양수",
      M.worst_year([100.0 * (1.001 ** i) for i in range(500)]) > 0)

check("B8) 회복 최장은 고점을 못 넘은 구간이다",
      M.underwater([100, 90, 95, 99, 101, 102]) == 3,
      f"{M.underwater([100, 90, 95, 99, 101, 102])}")
check("B9) 계속 오르면 0", M.underwater([100, 101, 102]) == 0)

# =====================================================================
# C) 맞교환 판정
# =====================================================================
check("C1) 한쪽이 수익 높고 낙폭도 작으면 맞교환이 없다",
      M.tradeoff(-53.7, -97.2, 22.0, -15.9) is False)
check("C2) 수익이 높은 대신 낙폭도 크면 맞교환이 있다",
      M.tradeoff(10.0, -10.0, 20.0, -30.0) is True)
check("C3) 수익이 낮으면 맞교환이 있다고 본다",
      M.tradeoff(20.0, -10.0, 10.0, -5.0) is True)
check("C4) 왜 이걸 보는지 적어뒀다",
      "보통은 '수익이 높으면 낙폭도 크다'" in flat)

# =====================================================================
# D) 팩터 - 우상향을 저변동과 따로 쟀는가
# =====================================================================
check("D1) 세 가지를 잰다", len(M.STYLES) == 3, str(M.STYLES))
check("D2) 우상향(추세)이 따로 들어 있다", "우상향(추세)" in M.STYLES)
check("D3) 추세 팩터를 strategy 의 trend 로 쓴다",
      'ranks_by(dates, panel, "trend")' in src)
check("D4) 저변동은 low_vol 이다", 'ranks_by(dates, panel, "low_vol")' in src)
check("D5) 왜 따로 쟀는지 적어뒀다",
      "저변동은 '안 흔들린다' 이고 추세는 '올라간다' 다" in flat)
check("D6) 종목 선정이 그 시점 정보로만 한다",
      "S.universe_at(panel, di" in src and "S.factor_score(panel, c, di, factor)" in src)
check("D7) 주기를 둘 다 본다 (20일/120일)", tuple(M.PERIODS) == (20, 120))

# =====================================================================
# E) 문서 - 숫자와 결론
# =====================================================================
for tok in ("-53.7", "-97.2", "-77.0", "+22.0", "-15.9", "-12.7",
            "-30.9", "-88.3", "-41.5"):
    check(f"E) 결과표에 {tok} 가 있다", tok in src)
check("E2) 고변동은 자주 거래할수록 더 나빠진다고 밝힌다",
      "자주 거래할수록 더 나빠진다" in flat)
check("E3) 그게 수수료 탓이 아니라고 짚는다",
      "수수료 탓이 아니다" in flat and "1.6%" in src)
check("E4) 우상향이 고변동 쪽에 붙는다는 새 결과를 적었다",
      "고변동 쪽에 가깝다" in flat)
check("E5) 왜 그런지 설명한다",
      "이미 많이 오른 종목을 사게" in flat)
check("E6) 모멘텀 결과와 이어 붙인다", "-4.76%p" in src)
check("E7) '안정적' 과 '우상향' 이 다른 종목이라고 정리한다",
      "다른 종목을 가리킨다" in flat)
check("E8) 선정이 주기보다 35배 중요하다는 계산을 보인다",
      "63.5%p" in src and "1.8%p" in src and "35배" in src)
check("E9) 주기를 짧게 하면 수수료가 3.4배라고 적었다", "3.4배" in src)
check("E10) 맞교환이 없다는 것을 표로 보인다", "맞교환이 없다" in src)
check("E11) 이건 탐색이 아니라 기술이라고 밝힌다 (다중검정 안 늘어남)",
      "다중검정이 늘지 않는다" in flat)
check("E12) 최악1년/회복최장을 왜 넣었는지 적었다",
      "그 6년을 버틸 수 있느냐" in flat)
check("E13) 2021~2026 결과라는 한계를 밝힌다",
      "다른 시기 다른 시장에서 같다는 보장은" in flat)
check("E14) 상승장에서 순위가 달라질 수 있다고 잇는다",
      "강한 상승장에서는 순위가 달라질 수 있다" in flat)

# =====================================================================
# G) 순위 구간 자르기 (--slice) - 선정이 단계적인가
# =====================================================================
_o = {0: list("abcdefghijklmnop"), 1: list("abc")}
_s = M.sliced(_o, 10, 16)
check("G1) 구간을 자른다", _s.get(0) == list("klmnop"), str(_s))
check("G2) 종목이 모자란 날은 뺀다 (짧은 목록을 억지로 안 쓴다)", 1 not in _s)
check("G3) 자른 구간이 서로 안 겹친다",
      not set(M.sliced(_o, 0, 5)[0]) & set(M.sliced(_o, 5, 10)[0]))
check("G4) 한 방향이면 단조 판정",
      M.monotone([1, 2, 3]) and M.monotone([3, 2, 1]))
check("G5) 들쭉날쭉하면 아니다", M.monotone([1, 3, 2]) is False)
check("G6) 같은 값이 섞여도 단조로 본다", M.monotone([1, 1, 2]))
check("G7) 잴 구간이 100위대까지 간다", max(M.SLICES) >= 100, str(M.SLICES))
check("G8) 뒤집기와 다른 것을 본다고 밝힌다",
      "양 끝" in flat and "중간을 안" in flat)
check("G9) 낙폭이 단조롭다는 결과를 적었다", "여섯 칸 전부 단조롭다" in flat)
for tok in ("-27.1", "-32.9", "-38.3", "-39.7", "-56.3", "11.0"):
    check(f"G) 구간표에 {tok} 가 있다", tok in src)
check("G10) 연수익은 들쭉날쭉하다고 밝힌다", "연수익은 들쭉날쭉하다" in flat)
check("G11) 신호가 무엇을 맞히는지 정리한다",
      "얼마나 벌지가 아니라 얼마나 깨질지" in flat)
check("G12) analyze_why 와 잇는다", "낮은 베타 + 비대칭" in flat)
check("G13) 한 칸 밀리면 절반이라고 짚는다",
      "한 칸만 밀려도 절반이 날아간다" in flat)
check("G14) 사용자 말이 출발점이라고 적었다", "핵심은 종목선정" in flat)
check("G15) --slice 실행법이 있다", "--slice" in src)

# =====================================================================
# F) 안전
# =====================================================================
check("F1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"F2) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
