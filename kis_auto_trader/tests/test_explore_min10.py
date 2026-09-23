"""explore_min10.py 검증 - 구경을 판정으로 둔갑시키지 않는가.

(2026-09-22 신설) 이 파일의 위험은 하나로 모인다. **1거래일치를 보고
뭔가 찾았다고 말하는 것.** 이 저장소가 계속 조심해온 것의 극단이다.

지키는 것
  1) 거래일 수를 항상 찍고, 20일 미만이면 판정이 아니라고 알리는가.
  2) 여기서 채택하지 않는다고 명시하는가.
  3) 시장이 움직인 만큼을 빼고 보는가. 내린 날에 다 음수인 것은
     발견이 아니다.
  4) '시장대비' 가 양수로 나온 것을 엣지로 읽지 않는가. 기준을 첫 봉
     시가로 잡았으니 하락이 장 초반에 몰린 날엔 자동으로 양수가 된다.
  5) 동시호가(15:20~15:30)를 연속 거래 구간으로 세지 않는가.

실행:
  python tests/test_explore_min10.py
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


import explore_min10 as M  # noqa: E402

src = (REPO_ROOT / "explore_min10.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


def bar(d="20260922", t="0900", c="A", o=100.0, h=101.0, l=99.0, cl=100.5,
        v=1000):
    return (d, t, c, o, h, l, cl, v)


# =====================================================================
# A) 구경과 판정을 갈랐는가 (핵심 1, 2)
# =====================================================================
check("A1) 파일 이름이 explore_ 다", "explore_min10" in src)
check("A2) 왜 이름을 다르게 지었는지 적었다",
      "analyze_ 가 아니라 explore_ 다" in flat)
check("A3) 판정하지 않는다고 제목에 박았다", "**판정하지 않는다.**" in src)
check("A4) 1일치로 할 수 없는 것을 적었다", "1일치로 할 수 없는 것" in flat)
check("A5) 시장 표본이 1개라고 짚었다",
      "하루는 시장 상황의 표본이 **1개**다" in src)
check("A6) analyze_reverse 의 같은 실수와 잇는다",
      "analyze_reverse.py" in src and "검정력이 0" in flat)
check("A7) 채택은 analyze_min10 만 한다고 적었다",
      "채택은 analyze_min10.py 가 20/60" in flat)
check("A8) 필요 거래일이 상수다", M.MIN_DAYS_FOR_VERDICT == 20)
check("A9) 거래일 수를 센다", M.n_days([bar(), bar(d="20260923")]) == 2)
check("A10) 20일 미만이면 부족하다고 판정",
      M.enough([bar()]) is False)
check("A11) 20일이면 충분",
      M.enough([bar(d=f"2026{i:04d}") for i in range(1, 21)]) is True)
check("A12) 화면에 부족 경고를 찍는다",
      "거래일뿐입니다. 판정에" in src and "아무것도 채택하지 않습니다" in src)

# =====================================================================
# B) 빈 봉을 걸러내는가
# =====================================================================
check("B1) 변동폭 계산", abs(M.bar_range([bar()])[0] - 2.0) < 1e-9,
      f"{M.bar_range([bar()])[0]}")
check("B2) 시가가 0 이면 건너뛴다", M.bar_range([bar(o=0.0)]) == [])
check("B3) 수수료 비중 계산",
      abs(M.fee_share_of_range(0.646) - 32.51) < 0.05,
      f"{M.fee_share_of_range(0.646):.2f}%")
check("B4) 변동폭이 0 이면 None (0 으로 안 나눈다)",
      M.fee_share_of_range(0.0) is None)
check("B5) 변동폭이 크면 비중이 작다",
      M.fee_share_of_range(2.0) < M.fee_share_of_range(0.5))

# =====================================================================
# C) 시간대별
# =====================================================================
rows = [bar(t="0900", c="A", o=100.0, h=104.0, l=100.0, cl=100.0),
        bar(t="0900", c="B", o=100.0, h=102.0, l=100.0, cl=101.0),
        bar(t="1220", c="A", o=100.0, h=100.2, l=100.0, cl=100.0)]
got = M.by_time(rows)
check("C1) 구간별로 묶는다", len(got) == 2, str([g[0] for g in got]))
check("C2) 변동폭 중앙값", abs(got[0][2] - 3.0) < 1e-9, f"{got[0][2]}")
check("C3) 안 움직인 비율을 센다 (A 는 시가=종가)",
      abs(got[0][4] - 50.0) < 1e-9, f"{got[0][4]}%")
check("C4) 거래량을 더한다", got[0][5] == 2000)
check("C5) U자 모양을 결과에 적었다", "변동폭이 U자다" in flat)
check("C6) 장 초반이 전부라고 짚었다", "장 초반 30분이 하루의 전부다" in flat)
check("C7) 점심에 수수료가 절반이라고 적었다", "1220" in src and "53%" in src)
check("C8) 변동폭이 크다고 버는 게 아니라고 못박았다",
      "변동폭이 크다고 버는 게 아니다" in flat)
check("C9) 스프레드를 못 잰다고 밝혔다",
      "체결가만 있어서 슬리피지를 못 잰다" in flat
      or "호가가 아니라 체결가만 있다" in flat)
check("C10) 한쪽으로는 쓸 수 있다고 정리했다",
      "수수료가 변동폭의 절반인" in flat and "방향을 몰라도 말할 수 있다" in flat)
check("C11) analyze_skip_rules 와 잇는다",
      "analyze_skip_rules.py" in src and "11,830" in src)

# =====================================================================
# D) 시장이 움직인 만큼을 빼는가 (핵심 3)
# =====================================================================
two = [bar(t="0900", c="A", o=100.0, cl=100.0),
       bar(t="0910", c="A", o=100.0, h=100.0, l=90.0, cl=90.0)]
mv = M.day_move(two)
check("D1) 날짜별 시장 움직임을 낸다 (첫 시가 -> 마지막 종가)",
      abs(mv["20260922"] - (-10.0)) < 1e-9, str(mv))
check("D2) 여러 날이면 각각", len(M.day_move(two + [bar(d="20260923")])) == 2)
check("D3) 시가가 0 인 종목은 뺀다", M.day_move([bar(o=0.0)]) == {})
check("D4) 왜 필요한지 적었다",
      "모든 보유가 음수인 것은 발견이 아니라 그날 시장이다" in flat)
check("D5) 그날이 내린 날이었다고 밝혔다", "-1.40%" in src)
check("D6) 오른 종목 비율까지 적었다", "오른 종목 26%" in src)
check("D7) 방향이 걸린 숫자는 물들었다고 못박았다",
      "전부 그 사실에 물들어 있다" in flat)

# =====================================================================
# E) '시장대비' 를 엣지로 읽지 않는가 (핵심 4 - 이 파일의 제일 중요한 것)
# =====================================================================
check("E1) 시장대비도 못 읽는다고 밝혔다",
      "**두 칸 다 1거래일로는 못 읽는다.**" in src)
check("E2) 왜 양수가 나오는지 설명했다",
      "그날 하락이 장 초반에\n              몰려 있었기 때문" in src
      or "그날 하락이 장 초반에 몰려 있었기 때문" in flat)
check("E3) 기준을 첫 봉으로 잡은 탓이라고 짚었다",
      "기준을\n              첫 봉부터 잡았다' 는 사실이다" in src
      or "기준을 첫 봉부터 잡았다' 는 사실이다" in flat)
check("E4) 엣지가 아니라고 못박았다", "엣지가 아니다" in flat)
check("E5) 며칠 쌓이면 사라지는 함정이라고 적었다",
      "며칠 쌓이면 사라진다" in flat)
check("E6) 화면 출력에도 그 경고가 있다",
      "늦게 들어간 거래가 자동으로 좋아 보인다" in src)
check("E7) 보유가 길수록 나빠진 것도 발견이 아니라고 밝혔다",
      "역시 발견이\n아니다" in src or "역시 발견이 아니다" in flat)

# =====================================================================
# F) 보유시간 미리보기 산수
# =====================================================================
seq = [bar(t=f"{9 + i // 6:02d}{(i % 6) * 10:02d}", c="A",
           o=100.0 + i, h=101.0 + i, l=99.0 + i, cl=100.5 + i)
       for i in range(10)]
pv = M.hold_preview(seq, buckets=(1, 39))
check("F1) 구간마다 한 줄", len(pv) == 2)
check("F2) 1구간 보유에 표본이 있다", pv[0][1] > 0, f"{pv[0][1]}")
check("F3) k 가 봉보다 커도 표본이 생긴다 (마지막 봉에 판다)",
      pv[1][1] > 0, f"종가까지 표본 {pv[1][1]}")
check("F4) 왜 그렇게 하는지 적었다",
      "그날 마지막 봉**에 판다" in src or "그날 마지막 봉에 판다" in flat)
check("F5) 안 그러면 표본 0 이 된다고 적었다", "표본 0 이 된다" in flat)
check("F6) 수수료를 뺀 칸이 평균보다 낮다", pv[0][4] < pv[0][2])
check("F7) 수수료만큼 정확히 낮다",
      abs((pv[0][2] - pv[0][4]) - M.FEE_ROUND_TRIP) < 1e-9)
check("F8) 표본이 없으면 None (안 터진다)",
      M.hold_preview([bar()], buckets=(1,))[0][2] is None)
check("F9) 보유 구간이 analyze_min10 과 같다",
      M.HOLD_BUCKETS == (1, 6, 14, 39))
import analyze_min10 as A  # noqa: E402
check("F10) 실제로 같은 값인지 대조한다",
      M.HOLD_BUCKETS == A.HOLD_BUCKETS, f"{M.HOLD_BUCKETS} vs {A.HOLD_BUCKETS}")

# =====================================================================
# G) 동시호가를 연속 구간으로 세지 않는가 (핵심 5)
# =====================================================================
check("G1) 15:20~15:30 이 동시호가라고 적었다",
      "단일가 동시호가" in flat)
check("G2) 그래서 봉이 38~39개라고 밝혔다", "38~39개다" in flat)
check("G3) 쓸 수 있는 구간이 38개라고 정리했다",
      "0900~1510 의 38구간" in src)
check("G4) 1520 이 사실상 없다고 숫자로 보였다",
      "1520" in src and "거래량 1" in src)
check("G5) 수집은 15:30 까지 두는 게 맞다고 적었다",
      "수집은 15:30 까지 그대로 두는 것이 맞다" in flat)

# =====================================================================
# H) 실측이 추정보다 나빴다 - 이 파일의 제일 쓸모 있는 결과
# =====================================================================
check("H1) 추정값을 상수로 갖고 있다", M.EST_BAR_RANGE_PCT == 0.93)
check("H2) 실측이 0.646% 라고 적었다", "0.646%" in src)
check("H3) 문턱이 23% -> 33% 라고 적었다",
      "23%" in src and "33%" in src)
check("H4) 왜 sqrt 어림이 틀렸는지 설명했다",
      "하루 변동폭이 시간에\n고르게 퍼져 있지 않기 때문이다" in src
      or "하루 변동폭이 시간에 고르게 퍼져 있지 않기 때문이다" in flat)
check("H5) 나쁜 쪽으로 틀렸다고 밝혔다", "나쁜 쪽으로 틀렸다" in flat)
check("H6) analyze_min10 이 실측을 쓰게 됐다",
      abs(A.fee_hurdle() - 32.5) < 0.1, f"{A.fee_hurdle():.2f}%")
check("H7) analyze_min10 에 실측 거래일 수가 박혀 있다", A.MEASURED_DAYS == 1)

# =====================================================================
# I) 안전 / 실제 파일로 돌려도 되는가
# =====================================================================
check("I1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"I2) 주문/통신 코드가 없다 ({banned})", banned not in src)
check("I3) 파일이 없어도 안 터진다", M.load("/없는/경로_*.csv") == [])
real = M.load()
if real:
    check("I4) 실제 10분봉을 읽는다", len(real) > 1000, f"{len(real):,}구간")
    check("I5) 빈 봉이 걸러져 있다",
          all(not (v == 0 and len({o, h, l, c}) == 1)
              for _d, _t, _cd, o, h, l, c, v in real))
    rng = M.bar_range(real)
    check("I6) 실측 중앙이 0.646% 대", abs(st.median(rng) - 0.646) < 0.02,
          f"{st.median(rng):.3f}%")
else:
    check("I4) 10분봉이 없으면 빈 목록", real == [])
check("I7) main 이 0 을 돌려준다", M.main([]) == 0)
check("I8) --time 도 돈다", M.main(["--time"]) == 0)
check("I9) --holds 도 돈다", M.main(["--holds"]) == 0)

# =====================================================================
# J) 33% 를 계획 숫자로 쓰지 않는가 (시간대를 갈라야 한다)
# =====================================================================
check("J1) 하루 전체 33% 가 계획용이 아니라고 밝혔다",
      "계획에 쓸 숫자가 아니다" in flat)
check("J2) 시간대를 갈라 재서 적었다",
      "0900~0950" in src and "17%" in src and "1100~1350" in src)
check("J3) 장 초반만 쓰면 추정보다 낫다고 적었다",
      "추정값(23%)보다 **오히려 낫다.**" in src)
check("J4) 반대 무게(스프레드)를 같이 적었다",
      "장 초반은 호가 스프레드가 가장 넓다" in flat)
check("J5) 하필 같은 자리라고 짚었다",
      "변동폭이 제일 큰 시간이 슬리피지도 제일 큰 시간이다" in flat)
check("J6) 0.08% 교차점이 여기서 결판난다고 적었다",
      "0.08% 교차점이 여기서 결판난다" in flat)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
