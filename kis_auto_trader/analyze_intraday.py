"""장중 되돌림 - 빠질 때 사서 종가에 판다. 실재하지만 수수료를 못 넘는다.

(2026-09-21 신설) 사용자: "아예 투자전략을 하락장에 변동성을 이용해보는건
어떨까 10분이나 20분 단위로 거래를 하려고 하는데" ->
"그럼 해당 주식의 장중 최고가 최저가로 계산해볼래"

10~20분 봉이 없다. 지금 가진 건 일봉(시/고/저/종)뿐이다. 그런데 고가와
저가가 있으면 **일중 되돌림을 일봉만으로 잴 수 있다.**

  규칙: 시가 대비 -X% 선을 저가가 찍었다면 그 순간 샀다고 본다.
        그리고 그날 종가에 판다.

저가가 그 선을 찍었다는 것은 장중 어느 시점엔 그 가격이었다는 뜻이므로
실제로 살 수 있었다. 미래 정보가 아니다.

===========================================================================
왜 이 계산이 10분 거래까지 같이 답하는가
===========================================================================
이 규칙은 '빠진 시점에 사서 **종가까지 들고 간다**'. 10분 거래는 그보다
훨씬 일찍 판다. 되돌림을 덜 먹고 수수료는 똑같이 낸다.

즉 이 계산은 10분 거래 아이디어의 **상한**이다. 여기서 안 되면 10분에서는
더 안 된다. 분봉을 몇 달 모으기 전에 지금 답할 수 있는 이유가 이것이다.

===========================================================================
움직임은 충분하다 - 막는 건 수수료가 아니다
===========================================================================
국면은 풀 60종목의 60일 수익률 부호로 가른다 (하락 393일 / 상승 758일).

  일중 변동폭 (고가-저가)/시가 평균, 그리고 수수료를 넘으려면
                    하락국면                 상승국면
  저변동10    2.39% -> 8.8% 잡아야     2.25% -> 9.3% 잡아야
  풀          3.45% -> 6.1% 잡아야     3.30% -> 6.4% 잡아야

변동폭의 6~9% 만 가져오면 수수료를 넘는다. 그러니 '수수료 때문에 원천
봉쇄' 는 틀린 설명이다. 움직임 자체는 충분하다.

문제는 **그 움직임 중 양(+)의 방향을 얼마나 가져오느냐**다. 아무렇게나
사고팔면 평균 0 이고 수수료만 나간다. 아래가 그걸 쟀다.

그리고 일중 변동폭은 국면에 따라 거의 안 변한다 (2.39 vs 2.25, 3.45 vs
3.30). '하락장에 변동성이 커진다' 는 통념이 이 자료에서는 안 보인다.

===========================================================================
결과 - 대조군은 이기는데, 수수료를 못 넘는다
===========================================================================
왕복 수수료 0.21% 차감 후 회당 평균 순수익%.

  --- 저변동 10종목 ---
  규칙                   하락국면          상승국면      총수익(하락)
  대조군(시가->종가)    -0.209 (393일)   -0.138 (758일)    +0.001
  -1% 빠지면 매수       -0.050 (368일)   -0.051 (728일)    +0.160
  -2% 빠지면 매수       -0.063 (244일)   -0.093 (448일)    +0.147
  -3% 빠지면 매수       -0.018 (126일)   -0.078 (221일)    +0.192
  -5% 빠지면 매수       -0.444  (31일)   +0.086  (50일)    -0.234

  --- 풀 60종목 ---
  대조군(시가->종가)    -0.330 (393일)   -0.209 (758일)    -0.120
  -1% 빠지면 매수       -0.198 (393일)   -0.145 (758일)    +0.012
  -2% 빠지면 매수       -0.079 (391일)   -0.079 (758일)    +0.131
  -3% 빠지면 매수       -0.023 (383일)   -0.140 (735일)    +0.187
  -5% 빠지면 매수       -0.054 (265일)   -0.011 (519일)    +0.156

읽는 순서가 중요하다.

(1) **되돌림은 진짜 있다.** 저변동 하락국면에서 그냥 시가에 사면 -0.209
    인데 -1% 빠진 뒤에 사면 -0.050 이다. 0.159%p 좋아진다. -3% 면
    -0.018 까지 온다. '빠질 때 산다' 는 조건이 일을 한다.

(2) **그런데 거의 전부 마이너스다.** 총수익(수수료 빼기 전)으로 돌려보면
    +0.13 ~ +0.19% 다. 왕복 수수료 0.21% 가 거기서 먹는다. 1일 보유
    때와 똑같은 구조다 (엣지 +0.102% < 0.21%).

(3) **하락국면에서 오히려 더 나쁘다.** 사용자의 전제와 반대다.
      저변동 -5%   하락 -0.444 (총수익 -0.234)  vs  상승 +0.086
    빠진 뒤에 더 빠지는 일이 하락국면에 더 자주 일어난다는 뜻이다.
    '하락장에 변동성을 이용한다' 가 걸리는 지점이 여기다.

(4) 양수 칸이 하나 있다 - 저변동10 / 상승국면 / -5% 에서 +0.086%.
    그런데 50일뿐이고, **상승국면**이라 애초 아이디어와 반대 방향이며,
    호가 스프레드를 안 넣은 값이다. -5% 선에 정확히 체결된다고 가정했다.
    스프레드를 넣으면 마이너스로 내려간다. 채택하지 않는다.

===========================================================================
숫자를 두 번 틀렸다 - 경위를 남긴다
===========================================================================
처음에 임시 스크립트로 재고 그 값을 문서에 적었다. 모듈로 옮겨 돌리니
국면별 날수가 519/632 에서 393/758 로 바뀌었다. 원인은 국면 판정에 쓴
종목 수였다 (스크래치 40종목, 모듈 60종목). 그것만으로 126일이 다르게
분류됐다.

일중 변동폭도 마찬가지였다. 5.73/5.64 는 '그날 올랐나 내렸나' 로 가른
값이라 이 파일의 국면 기준과 다른 분류였다. 그래서 그 계산도 모듈 안에
넣어 같은 기준으로 다시 쟀다 (2.39/2.25, 3.45/3.30).

전날 analyze_knobs 의 -41.5% 때와 같은 실수다. 이 표의 모든 숫자는
python analyze_intraday.py 로 재현된다.

===========================================================================
읽는 법
===========================================================================
1) 되돌림 신호는 있다. 없어서 지는 게 아니라 수수료를 못 넘어서 진다.
   analyze_short_term.py 의 결론과 정확히 같은 모양이다.
2) 10분 거래는 이것보다 나쁘다. 되돌림을 덜 먹고 수수료는 같기 때문이다.
   그래서 분봉을 모으기 전에 여기서 답이 난다.
3) 이 표는 규칙에 유리하게 기울어 있다 (스프레드 없음, 선에 정확히 체결).
   그런데도 거의 전부 마이너스다.
4) 다중검정: 이 파일에서 16칸을 봤다. 저장소 누적은 이제 90가지쯤 된다.
   양수 한 칸은 그 안에서 나올 만한 수다.

실행:
  python analyze_intraday.py
"""
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import analyze_knobs as K  # noqa: E402
import analyze_stops as A  # noqa: E402
import strategy as S  # noqa: E402

FEE = S.FEE_ROUND_TRIP_PCT
BASE_DI = 250
DIPS = (1, 2, 3, 5)
REGIME_BACK = 60          # 국면 판정 기간 (거래일)
POOL_N = 60               # '풀' 로 볼 종목 수
PICK = 10
MIN_POOL = 40


def regime_at(panel, codes, di, back=REGIME_BACK):
    """풀 평균 back일 수익률의 부호. 음수면 '하락' 국면.

    그날 올랐나 내렸나가 아니라 **국면**이다. 둘은 다르다 - 처음에는
    하루 부호로 갈랐는데 그건 사용자가 말한 하락장이 아니었다.
    """
    rs = []
    for c in codes[:POOL_N]:
        a = E.price(panel, c, di - back, "close")
        b = E.price(panel, c, di, "close")
        if a and b:
            rs.append(b / a - 1)
    if not rs:
        return None
    return "하락" if st.mean(rs) < 0 else "상승"


def dip_trade(panel, hl, code, di, dip_pct):
    """시가 대비 -dip_pct% 를 저가가 찍었으면 거기서 사서 종가에 판다.

    수수료를 뺀 순수익%. 안 걸리면 None.

    저가가 그 선을 찍었다는 것은 장중에 그 가격이 있었다는 뜻이므로
    미래 정보가 아니다. 다만 그 선에 **정확히** 체결된다고 보는 것은
    규칙에 유리한 가정이다 (호가 스프레드를 안 넣었다).
    """
    op = E.price(panel, code, di, "open")
    cl = E.price(panel, code, di, "close")
    v = hl.get((di, code))
    if not (op and cl and v):
        return None
    line = op * (1 - dip_pct / 100)
    if v[1] > line:
        return None
    return (cl / line - 1) * 100 - FEE


def open_to_close(panel, code, di):
    """대조군: 조건 없이 시가에 사서 종가에 판다.

    이게 없으면 '빠질 때 산다' 가 일을 한 것인지, 그냥 하루 들고 있어서
    난 결과인지 구별할 수 없다.
    """
    op = E.price(panel, code, di, "open")
    cl = E.price(panel, code, di, "close")
    if not (op and cl):
        return None
    return (cl / op - 1) * 100 - FEE


def gross(net, fee=FEE):
    """수수료를 도로 더해서 총수익으로. 신호 자체의 크기를 보려는 것."""
    return net + fee


def beats_control(rule_net, control_net):
    """규칙이 대조군보다 나은가. 이것만으로는 채택 못 한다."""
    return rule_net > control_net


def usable(net):
    """실제로 쓸 수 있나. 대조군을 이겨도 마이너스면 못 쓴다."""
    return net > 0


def day_range(panel, hl, code, di):
    """그날 (고가-저가)/시가 %. 일중에 쓸 수 있는 움직임의 총량이다."""
    op = E.price(panel, code, di, "open")
    v = hl.get((di, code))
    if not (op and v):
        return None
    return (v[0] - v[1]) / op * 100


def capture_needed(rng, fee=FEE):
    """변동폭의 몇 %를 잡아야 수수료를 넘나.

    이 값이 작다고 '되면 되겠네' 가 아니다. 움직임이 충분하다는 뜻일
    뿐이고, 그중 양(+)의 방향을 가져올 수 있는지는 따로 재야 한다.
    """
    return fee / rng * 100 if rng else float("inf")


def run(dates, panel, hl, base=BASE_DI):
    """{(대상, 국면, 규칙): [일별 평균 순수익]}, 국면별 날수, 국면별 변동폭."""
    order = K.ranks(dates, panel, base)
    out, nday, rng = {}, {}, {}
    for di in range(base, len(dates)):
        if di not in order:
            continue
        lst = order[di]
        reg = regime_at(panel, lst, di)
        if reg is None:
            continue
        nday[reg] = nday.get(reg, 0) + 1
        for who, codes in (("저변동10", lst[:PICK]), ("풀", lst[:POOL_N])):
            rr = [x for c in codes
                  if (x := day_range(panel, hl, c, di)) is not None]
            if rr:
                rng.setdefault((who, reg), []).append(st.mean(rr))
            ctl = [x for c in codes if (x := open_to_close(panel, c, di)) is not None]
            if ctl:
                out.setdefault((who, reg, "대조군"), []).append(st.mean(ctl))
            for dip in DIPS:
                tr = [x for c in codes
                      if (x := dip_trade(panel, hl, c, di, dip)) is not None]
                if tr:
                    out.setdefault((who, reg, f"-{dip}%"), []).append(st.mean(tr))
    return out, nday, rng


def main():
    dates, panel = S.load_panel()
    hl = A.load_high_low(dates)
    print("일별 순위 계산 중...")
    out, nday, rng = run(dates, panel, hl)

    print(f"\n국면별 날수: {nday}")
    print("\n일중 변동폭 (고가-저가)/시가 평균%, 그리고 수수료를 넘으려면")
    print(f"{'':10}{'하락국면':>22}{'상승국면':>22}")
    for who in ("저변동10", "풀"):
        cells = []
        for reg in ("하락", "상승"):
            v = rng.get((who, reg), [])
            m = st.mean(v) if v else None
            cells.append(f"{m:.2f}% -> {capture_needed(m):.1f}% 잡아야" if v else "-")
        print(f"{who:<10}{cells[0]:>22}{cells[1]:>22}")

    print(f"왕복 수수료 {FEE}% 차감 후 회당 평균 순수익% "
          f"(호가 스프레드는 안 넣음 - 규칙에 유리하게 기울어 있다)\n")
    for who in ("저변동10", "풀"):
        print(f"--- {who} ---")
        print(f"{'규칙':<16}{'하락국면':>18}{'상승국면':>18}{'총수익(하락)':>14}")
        for rule in ["대조군"] + [f"-{d}%" for d in DIPS]:
            cells, g = [], None
            for reg in ("하락", "상승"):
                r = out.get((who, reg, rule), [])
                m = st.mean(r) if r else None
                cells.append(f"{m:+.3f} ({len(r)}일)" if r else "-")
                if reg == "하락" and r:
                    g = gross(m)
            label = rule if rule == "대조군" else f"{rule} 빠지면 매수"
            print(f"{label:<16}{cells[0]:>18}{cells[1]:>18}"
                  f"{(f'{g:+.3f}' if g is not None else '-'):>14}")
        print()

    # 판정
    print("판정")
    any_usable = False
    for (who, reg, rule), r in sorted(out.items()):
        if rule == "대조군" or not r:
            continue
        m = st.mean(r)
        c = out.get((who, reg, "대조군"), [])
        if c and beats_control(m, st.mean(c)) and usable(m):
            any_usable = True
            print(f"  [!] {who}/{reg}/{rule}: 대조군을 이기고 양수 ({m:+.3f}%)")
    if not any_usable:
        print("  대조군을 이기면서 양수인 칸이 없다. 넣지 않는다.")
        print("  되돌림 신호는 있다 - 총수익이 +0.10~0.25% 다. 다만 왕복")
        print(f"  수수료 {FEE}% 를 못 넘는다. 1일 보유 때와 같은 구조다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
