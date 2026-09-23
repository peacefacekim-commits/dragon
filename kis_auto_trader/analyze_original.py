"""사용자의 원래 방식을 좋은 선정 위에 올려본다.

(2026-09-21 신설) 사용자: "그럼 기존 투자 방식이 그렇게 잘못된 게
아니라는 걸까. 투자종목만 잘 고른다면"

앞선 측정들이 '선정이 지배적' 이라고 계속 말했고, --fast 에서 '자주
거래하는 것 자체는 치명적이지 않다' 가 나왔다. 그러면 자연히 나오는
물음이다. 그런데 사용자의 원래 방식은 **세 가지가 붙어 있었다.**

    (1) 5종목                      (2) 짧은 주기
    (3) 익절률/손절률 정해놓고 팔기

지금까지 이 셋을 따로따로만 쟀다. 여기서는 **선정을 저변동으로 고정
해놓고** 나머지 셋을 같이 켜본다. 즉 "종목만 잘 골랐다면 원래 방식이
통했을까" 를 그대로 재현한 것이다.

===========================================================================
결과 (저변동 선정 고정, 시작일 5개 중앙값)
===========================================================================
  종목  주기   파는 규칙            연수익%   낙폭%   매도
    5   5일   없음                  14.1   -18.9      0
    5   5일   익절+5 손절-5          11.5   -20.7    248
    5   5일   익절+10 손절-5         13.9   -21.1    140
    5   5일   익절+10 손절-10        13.8   -21.8     77
    5  20일   없음                  16.5   -18.3      0
    5  20일   익절+5 손절-5           8.2   -16.1    167
    5  20일   익절+10 손절-5         12.4   -14.3    115
    5  20일   익절+10 손절-10        14.7   -17.3     69
   10   5일   없음                  22.4   -18.3      0
   10   5일   익절+5 손절-5          12.6   -18.5    578
   10   5일   익절+10 손절-5         16.9   -18.2    357
   10   5일   익절+10 손절-10        18.1   -18.9    191
   10  20일   없음                  20.2   -16.2      0
   10  20일   익절+5 손절-5           8.0   -13.4    340
   10  20일   익절+10 손절-5         12.1   -14.0    247
   10  20일   익절+10 손절-10        17.7   -15.9    161

===========================================================================
1 - 익절/손절은 8가지 경우 전부에서 진다
===========================================================================
종목 수와 주기의 네 조합마다 '없음' 과 세 가지 규칙을 견줬다. **12번
중 12번 모두 '없음' 이 이긴다.** 예외가 없다.

  10종목 20일: 20.2 -> 8.0 / 12.1 / 17.7
  10종목  5일: 22.4 -> 12.6 / 16.9 / 18.1

그리고 규칙이 느슨할수록(팔 일이 적을수록) 덜 진다. 17.7 < 20.2 이고
매도 161건, 8.0 은 매도 340건이다. **파는 횟수에 비례해서 나빠진다.**
이건 '어느 문턱이 좋은가' 의 문제가 아니라 '파는 행위 자체가 손해'
라는 뜻이다. analyze_stops.py 와 analyze_takeprofit.py 가 따로 얻은
결론이 선정을 고쳐도 그대로 남는다.

중요한 점: 낙폭도 안 좋아진다. 손절의 명분은 '큰 손해를 막는다' 인데
10종목 5일에서는 -18.3% -> -18.5% 로 오히려 나빠졌다. 낙폭이 준 칸
(20일 -16.2 -> -13.4)은 수익이 20.2 -> 8.0 으로 깎인 대가다. 현금으로
도망가 있으면 덜 깨지는 것은 당연하고, 그건 위험관리가 아니라 투자를
덜 한 것이다.

===========================================================================
2 - 5종목은 10종목에 전부 진다
===========================================================================
  5종목  5일 14.1   vs  10종목  5일 22.4
  5종목 20일 16.5   vs  10종목 20일 20.2

낙폭도 더 나쁘다 (-18.9 vs -18.3, -18.3 vs -16.2). 맞교환이 아니라
그냥 진다. 종목이 적으면 한 종목이 어긋날 때 받는 충격이 크다.
analyze_knobs.py 의 종목 수 훑기와 같은 방향이다.

===========================================================================
3 - 그래서 답은 '절반만'
===========================================================================
맞는 부분
  선정이 지배적이라는 진단은 옳다. 이 저장소가 잰 것 중 성과를 크게
  움직인 것은 선정뿐이다 (63.5%p vs 나머지 전부 몇 %p).
  그리고 자주 거래하는 것 자체는 치명적이지 않다. 좋은 선정 위에서
  5일 주기는 22.4% 로 20일(20.2%)보다도 낫다.

틀린 부분
  익절/손절로 파는 규칙은 **선정을 고쳐도 여전히 진다** (12/12).
  5종목도 10종목에 진다 (4/4).

즉 "종목만 잘 고르면 됐다" 가 아니라 **"종목을 잘 고르고, 파는 규칙을
빼고, 종목 수를 늘려야 했다"** 다. 원래 방식에서 살아남는 것은 '자주
본다' 하나뿐이고, 그것도 --fast 에서 본 대로 슬리피지에 먹힌다.

===========================================================================
읽는 법
===========================================================================
1) 장중 10분 매매는 여기서 못 잰다. 이 패널은 일봉이라 하루 안의
   사고팔기를 재현할 수 없다. analyze_intraday.py 가 따로 쟀고 엣지를
   못 찾았다. 여기 결과를 장중에 그대로 옮기면 안 된다.
2) 익절/손절 문턱은 3가지만 봤다. analyze_stops.py 가 11가지를 더
   봤고 전부 졌다. 여기서 더 훑을 이유가 없다.
3) 2021~2026 한국 시장, 저변동 선정 기준이다.
4) 다중검정: 16칸. 채택한 것은 없다.

실행:
  python analyze_original.py
"""
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import analyze_knobs as K  # noqa: E402
import strategy as S  # noqa: E402

CAPITAL = E.CAPITAL
FEE_ONE_WAY = E.FEE_ONE_WAY
BASE_DI = 250
DAYS_PER_YEAR = 246
N_STARTS, START_GAP = 5, 37

PICKS = (5, 10)          # 원래 5종목이었다
PERIODS = (5, 20)        # 짧은 주기
# (이름, 익절%, 손절%). None 은 그 규칙을 안 쓴다는 뜻.
RULES = (("없음", None, None),
         ("익절+5 손절-5", 5, 5),
         ("익절+10 손절-5", 10, 5),
         ("익절+10 손절-10", 10, 10))


def _starts():
    return [BASE_DI + k * START_GAP for k in range(N_STARTS)]


def run(dates, panel, order, start, period, pick, tp=None, sl=None, upto=None):
    """교체 주기마다 순위대로 사고, 중간에 익절/손절이 걸리면 판다.

    판 돈은 다음 교체일까지 현금으로 둔다. 원래 방식이 그랬기 때문이다
    (analyze_takeprofit.py 에서 본 대로 이 '노는 돈' 이 손해의 큰 몫
    이지만, 여기서는 사용자의 방식을 그대로 재현하는 게 목적이다).

    익절/손절은 **교체일인지와 무관하게 매일** 본다. 주기가 1일이면
    교체가 매일 일어나서 규칙이 발동할 틈이 없어지는데, 그러면 규칙을
    안 잰 것이 되기 때문이다.
    """
    n = upto or len(dates)
    cash, hold, basis = float(CAPITAL), {}, {}
    curve, di, nsell = [], start, 0
    while di < n:
        if (di - start) % period == 0 and di in order:
            new = order[di][:pick]
            keep = {c: q for c, q in hold.items() if c in new}
            for c in [c for c in hold if c not in new]:
                v = E.price(panel, c, di)
                if v:
                    cash += hold[c] * v * (1 - FEE_ONE_WAY)
            add = [c for c in new if c not in hold]
            got, cash, _f = (E.buy_greedy(panel, cash, add, di) if add
                             else ({}, cash, 0.0))
            for c in got:
                basis[c] = E.price(panel, c, di) or 0
            hold = {**keep, **got}
        if tp is not None or sl is not None:
            for c in list(hold):
                px = E.price(panel, c, di, "close")
                if not px or not basis.get(c):
                    continue
                gain = (px / basis[c] - 1) * 100
                if ((tp is not None and gain >= tp)
                        or (sl is not None and gain <= -sl)):
                    cash += hold[c] * px * (1 - FEE_ONE_WAY)
                    del hold[c]
                    nsell += 1
        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, nsell


def annualized(curve, capital=CAPITAL):
    if not curve:
        return 0.0
    return ((curve[-1] / capital) ** (DAYS_PER_YEAR / len(curve)) - 1) * 100


def mdd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def rules_lost(box):
    """파는 규칙이 '없음' 을 한 번이라도 이겼나.

    (진 횟수, 전체 횟수) 를 돌려준다. 하나라도 이기면 '문턱을 잘 고르면
    된다' 가 되므로, 전부 지는지가 중요하다.
    """
    lost = total = 0
    for (pick, period) in {(p, q) for p, q, _r in box}:
        none = box[(pick, period, "없음")][0]
        for _n, tp, sl in RULES:
            if tp is None and sl is None:
                continue
            tag = next(n for n, a, b in RULES if (a, b) == (tp, sl))
            total += 1
            if box[(pick, period, tag)][0] < none:
                lost += 1
    return lost, total


def main():
    dates, panel = S.load_panel()
    print("순위 계산 중...", flush=True)
    order = K.ranks(dates, panel, BASE_DI)
    starts = _starts()

    print(f"\n저변동 선정 고정. 종목수/주기/파는규칙만 바꾼다 "
          f"(시작일 {N_STARTS}개 중앙값)")
    print(f"{'종목':>5}{'주기':>7}  {'파는 규칙':<18}{'연수익%':>9}"
          f"{'낙폭%':>9}{'매도':>7}")
    box = {}
    for pick in PICKS:
        for period in PERIODS:
            for tag, tp, sl in RULES:
                rs, ds, ns = [], [], []
                for s in starts:
                    c, nse = run(dates, panel, order, s, period, pick, tp, sl)
                    rs.append(annualized(c))
                    ds.append(mdd(c))
                    ns.append(nse)
                box[(pick, period, tag)] = (st.median(rs), st.median(ds),
                                            st.median(ns))
                print(f"{pick:>5}{period:>6}일  {tag:<18}{st.median(rs):>9.1f}"
                      f"{st.median(ds):>9.1f}{st.median(ns):>7.0f}", flush=True)
        print()

    lost, total = rules_lost(box)
    print(f"파는 규칙이 '없음' 에 진 횟수: {lost}/{total}")
    for period in PERIODS:
        a = box[(5, period, "없음")][0]
        b = box[(10, period, "없음")][0]
        print(f"{period}일 주기: 5종목 {a:.1f}%  vs  10종목 {b:.1f}%  "
              f"-> {'10종목이 낫다' if b > a else '5종목이 낫다'}")
    print("\n선정이 지배적이라는 진단은 맞다. 다만 익절/손절과 5종목은"
          "\n선정을 고쳐도 여전히 진다. 원래 방식에서 살아남는 것은"
          "\n'자주 본다' 하나뿐이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
