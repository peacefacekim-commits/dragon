"""analyze_event_rebal.py 검증 - 이벤트 방식을 공평하게 재는지.

(2026-09-19 신설) 사용자: "교체할 종목이 나오면 그때 날을 정해서 팔거나?"

이 파일의 결론은 '수익으로는 날짜 방식과 구별 안 된다' 다. 그런데
비교를 한쪽에 유리하게 하면 결론이 바뀌므로 거기를 검사한다.

지켜야 하는 것
  1) 두 방식이 같은 조건에서 시작해야 한다 (같은 자본, 같은 시작일,
     같은 순위 계산, 같은 부분교체 방식).
  2) 이벤트 방식도 수수료를 낸다. 날짜 방식만 물리면 불공평하다.
  3) 버퍼가 넓으면 거래가 줄어야 한다 (단조). 아니면 구현 버그다.
  4) 지그재그 판정이 실제로 지그재그를 잡아내야 한다 - 이게 이 파일의
     결론 근거다.
  5) '버퍼를 고를 수 있나' 판정이 너무 관대하면 안 된다. 처음 쓴
     스크립트가 7.1 vs 6.0 을 '볼 만하다' 고 찍어서 고쳤다.
  6) 사용자 제안(이익>수수료면 팔기)의 결과와 sunk cost 설명이 있어야
     한다.

실행:
  python tests/test_analyze_event_rebal.py
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


import analyze_event_rebal as M  # noqa: E402

src = (REPO_ROOT / "analyze_event_rebal.py").read_text(encoding="utf-8")
st_src = (REPO_ROOT / "analyze_short_term.py").read_text(encoding="utf-8")


class FakeSeries:
    def __init__(self, closes, opens=None):
        self.close = list(closes)
        self.open = list(opens if opens is not None else closes)
        self.pos = {i: i for i in range(len(self.close))}


# =====================================================================
# A) 지그재그 판정 - 결론의 근거다
# =====================================================================
REAL = [21.3, 17.0, 20.6, 15.8, 16.1, 21.3, 22.9]
check("A1) 실제 버퍼별 값을 지그재그로 판정한다", M.is_zigzag(REAL))
check("A2) 단조 증가는 지그재그가 아니다", not M.is_zigzag([1, 2, 3, 4, 5]))
check("A3) 단조 감소도 지그재그가 아니다", not M.is_zigzag([5, 4, 3, 2, 1]))
check("A4) 값이 두 개뿐이면 판정하지 않는다", not M.is_zigzag([1, 2]))
check("A5) 전부 같으면 지그재그가 아니다", not M.is_zigzag([3, 3, 3, 3]))
check("A6) 한 번만 꺾여도 지그재그다", M.is_zigzag([1, 5, 2]))

# =====================================================================
# B) '버퍼를 고를 수 있나' 판정 - 처음 너무 관대했다
# =====================================================================
check("B1) 7.1 vs 6.0 은 못 고른다고 판정한다 (처음엔 True 였다)",
      not M.pickable(7.1, 6.0))
check("B2) 두 배를 넘으면 고를 수 있다고 한다", M.pickable(12.1, 6.0))
check("B3) 정확히 두 배는 경계로 통과", M.pickable(12.0, 6.0))
check("B4) 흔들림이 더 크면 당연히 못 고른다", not M.pickable(3.0, 6.0))
check("B5) 최소 두 배 기준이라고 주석에 적어놨다",
      "최소\n    두 배는" in src or "두 배는 돼야" in src)

# =====================================================================
# C) 낙폭 / 연환산
# =====================================================================
check("C1) 계속 오르면 낙폭 0", M.mdd([1, 1.1, 1.2]) == 0.0)
check("C2) 반토막이면 -50%", abs(M.mdd([1, 2, 1]) - (-50.0)) < 1e-9)
cv = [M.CAPITAL] * M.DAYS_PER_YEAR + [M.CAPITAL * 2]
check("C3) 1년에 2배면 연환산 100% 근처", 90 < M.annualized(cv) < 110)

# =====================================================================
# D) 두 방식이 같은 조건인지 + 수수료를 둘 다 내는지
# =====================================================================
_real = (M.S.universe_at, M.S.factor_score)
try:
    codes = [f"{i:06d}" for i in range(40)]
    n = 300
    fdates = [f"d{i:04d}" for i in range(n)]
    fpanel = {c: FakeSeries([100.0] * n) for c in codes}   # 값이 안 움직임
    M.S.universe_at = lambda p, di, size, mp: list(codes)

    # 순위가 천천히 돌아간다 -> 종목이 밀려난다
    M.S.factor_score = lambda p, c, di, kind: float((int(c) + di // 10) % 40)
    order, rank = M.daily_ranks(fdates, fpanel, 0)
    check("D1) 순위를 매일 계산한다", len(rank) > n * 0.9, f"{len(rank)}일")
    check("D2) 순위가 1부터 시작한다",
          min(rank[0].values()) == 1 and max(rank[0].values()) == len(codes))
    check("D3) order 와 rank 가 일치한다",
          all(rank[0][c] == i + 1 for i, c in enumerate(order[0])))

    # 버퍼가 넓으면 거래가 줄어야 한다 (단조)
    trades = []
    for buf in (10, 15, 20, 30, 40):
        _cv, _f, nt = M.run_event(fdates, fpanel, order, rank, buf, 0)
        trades.append(nt)
    check("D4) 버퍼가 넓으면 거래가 줄어든다 (단조 감소)",
          all(a >= b for a, b in zip(trades, trades[1:])),
          " -> ".join(str(t) for t in trades))
    check("D5) 좁은 버퍼는 거래가 많다", trades[0] > trades[-1] * 2,
          f"버퍼10 {trades[0]}회 vs 버퍼40 {trades[-1]}회")

    # 이벤트 방식도 수수료를 낸다 (값이 안 움직이는 세계에서 자산이 줄어야)
    cv_e, fee_e, nt_e = M.run_event(fdates, fpanel, order, rank, 15, 0)
    check("D6) 이벤트 방식이 수수료를 낸다", fee_e > 0, f"{fee_e:,.0f}원")
    check("D7) 값이 안 움직이면 자산이 수수료만큼 줄어든다",
          cv_e[-1] < M.CAPITAL, f"{cv_e[-1]:,.0f}원")

    cv_c, fee_c, nt_c = M.run_calendar(fdates, fpanel, order, 40, 0)
    check("D8) 날짜 방식도 수수료를 낸다", fee_c > 0, f"{fee_c:,.0f}원")
    check("D9) 거래가 많은 쪽이 수수료를 더 낸다",
          (fee_e > fee_c) == (nt_e > nt_c),
          f"이벤트 {nt_e}회/{fee_e:,.0f}원 vs 날짜 {nt_c}회/{fee_c:,.0f}원")

    # 둘 다 같은 자본에서 시작하고 같은 길이의 곡선을 낸다
    check("D10) 두 방식의 곡선 길이가 같다 (같은 기간)",
          len(cv_e) == len(cv_c), f"{len(cv_e)} vs {len(cv_c)}")
    check("D11) 두 방식이 같은 순위 계산을 공유한다",
          "run_event(dates, panel, order, rank" in src
          and "run_calendar(dates, panel, order" in src)
    check("D12) 날짜 방식도 부분교체다 (공평한 비교)",
          "keep = {c: q for c, q in hold.items() if c in new}" in src)

    # upto 로 기간을 자를 수 있어야 한다 (반기 검증용)
    cv_half, _f, _t = M.run_event(fdates, fpanel, order, rank, 15, 0, upto=150)
    check("D13) upto 로 기간을 자른다", len(cv_half) == 150)

    # 유니버스에서 빠진 종목도 교체 대상이다
    check("D14) 유니버스에서 빠진 종목은 순위를 크게 봐서 교체한다",
          "rk.get(c, 10 ** 9) > buffer_rank" in src)
finally:
    M.S.universe_at, M.S.factor_score = _real

# =====================================================================
# E) 안전
# =====================================================================
check("E1) 종목 선정은 그 시점 정보로만 한다",
      'S.factor_score(panel, c, di, "low_vol")' in src
      and "S.universe_at(panel, di" in src)
check("E2) 리눅스 절대경로를 박아두지 않았다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"E3) 주문/통신 코드가 없다 ({banned})", banned not in src)

# =====================================================================
# F) 문서 - 오해를 바로잡고 결론을 과장하지 않는지
# =====================================================================
check("F1) 사용자 오해(조짐으로 날짜 정하기)를 먼저 바로잡는다",
      "내 결론은 **반대**였다" in src)
check("F2) 이 아이디어가 타이밍과 다른 차원이라고 인정한다",
      "종목 선택 차원" in src and "엣지를 가진 유일한 곳" in src)
check("F3) 버퍼별 지그재그 수치가 있다",
      "21.3 -> 17.0 -> 20.6" in src)
check("F4) 거래 횟수를 맞춘 비교가 양방향으로 있다",
      "같은 조건에서 날짜가 +3.2%p" in src and "여기선 이벤트가 이긴다" in src)
check("F5) 시작일 흔들림 6.0 vs 버퍼 차이 7.1 이 기록돼 있다",
      "6.0%p" in src and "7.1%p" in src)
check("F6) 처음 판정이 관대했다고 스스로 적었다",
      "너무 관대한 판정이었다" in src)
check("F7) 반기 양방향 1위가 다르다는 것을 밝힌다",
      "1위가 완전히 다르다" in src)
check("F8) 이벤트가 낫다고 말할 수 없다고 결론한다",
      "이벤트 방식이 낫다고 말할 수 없다" in src)
check("F9) 레짐 베팅이라는 해석이 있다",
      "레짐 베팅" in src and "강세" in src and "약세" in src)
check("F10) 실무 권고가 수익이 아니라 운영 근거라고 밝힌다",
      "이유는 수익이 아니라 운영이다" in src)
check("F11) 언제 주문할지 미리 아는 것이 목표에 맞다고 설명한다",
      "언제\n     할지 미리 아는 쪽" in src or "미리 아는 쪽" in src)
check("F12) 굳이 쓸 거면 버퍼를 넓게 잡으라고 한다",
      "버퍼를 넓게(30~50위)" in src)
check("F13) 그 권고가 검증된 게 아니라고 밝힌다",
      "검증된 권고가 아니라" in src)
check("F14) 스프레드 미반영이 이벤트 방식에 관대하다고 밝힌다",
      "이벤트 방식에 이미 관대하다" in src)

# 결과 4 - 사용자 제안
check("F15) 수수료 구성(세금 86%)을 밝힌다",
      "86% 가 세금이다" in src)
check("F16) 수수료를 깎아도 안 된다고 밝힌다",
      "수수료를 깎아서" in src)
check("F17) sunk cost 문제를 설명한다",
      "이미 정해진 과거" in src and "회복되지" in src)
check("F18) 제안 규칙이 -4.9%p 라는 결과가 있다", "-4.9%p" in src)
check("F19) 반대 규칙이 덜 나쁘다는 것도 밝힌다",
      "-1.4%p" in src and "방향까지 거꾸로다" in src)
check("F20) 0.21% 문턱이 아무것도 안 걸렀다는 것을 짚는다",
      "아무것도 안 걸렀다" in src)
check("F21) 사용자 직관 자체는 맞고 버퍼가 그 구현이라고 정리한다",
      "직관 자체는 맞다" in src
      and "구현한 것이 위의 **버퍼**다" in src)

# analyze_short_term.py 의 정정
check("F22) analyze_short_term.py 의 '수수료 절반' 주장을 정정했다",
      "현실에서 불가능한 가정이었다" in st_src
      and "86% 가 세금이다" in st_src)
check("F23) 정정본에 실제 손익분기 변화(2.3->1.9일)가 있다",
      "2.3일 -> 1.9일" in st_src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
