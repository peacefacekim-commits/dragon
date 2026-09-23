"""슬롯 재활용 - 익절까지 버티고 팔면 바로 다시 산다. 넣지 않는다.

(2026-09-19 신설) 사용자: "종목을 하나 정해서 정해진 익절률까지 계속
버티고 판매한 슬롯은 다시 정해놓은 종목을 사면서 계속 순환시키는 전략은?"

이건 analyze_stops.py 에서 잰 익절과 **다르다.** 거기서는 익절한 뒤 슬롯이
다음 교체일까지 현금으로 놀았다. 여기서는 바로 다시 산다. 그리고 손절도
시간 제한도 없다 - 익절선에 닿을 때까지 버틴다. 현금이 노는 손해가 없으니
결과가 달라질 수 있어서 따로 쟀다.

구조
  자본을 슬롯 10개로 나눈다 (슬롯당 20만원).
  빈 슬롯은 그 시점 저변동 상위에서 아직 안 들고 있는 종목을 산다.
  익절선에 닿으면 판다. 손절 없음, 시간 제한 없음.
  판 슬롯은 **다음 거래일부터** 다시 산다 (아래 '고친 것' 참고).

===========================================================================
고친 것 - 처음 결과는 내 버그가 만든 것이었다
===========================================================================
처음 쓴 코드는 익절한 그날 시가로 다시 샀다. 익절은 장중에 체결되는데
시가는 그보다 앞선 가격이다. 즉 **오후에 받은 돈으로 오전 가격을 사고
있었다.** 그날 오른 종목이 공짜로 싸게 잡히는 미래 정보다.

그 버그가 결과의 전부였다.

  익절률      고치기 전    고친 뒤     기준(120일 부분교체)
  +3%         25.4%       13.3%       22.0%
  +5%         20.1%       12.8%       22.0%
  +10%        18.2%       16.0%       22.0%
  +20%        18.8%       11.4%       22.0%

고치기 전에는 반띵 검증도 통과했다 (전반부 +2.3%p, 후반부 +16.0%p).
지금까지 모든 후보를 죽였던 그 검증을 처음으로 넘긴 것이었는데, 통과의
정체가 미래 정보였다. **반띵 검증도 입력이 오염돼 있으면 통과시킨다.**

===========================================================================
결과 1 - 시작일 5개 전부에서 기준에 진다 (0/5)
===========================================================================
같은 시작일끼리 짝지어 비교했다.

  규칙            연수익 중앙   최소    최대   낙폭 중앙   기준 이긴 횟수
  기준(120일)       22.0     16.7   26.6     -15.9        -
  익절 +3%          13.3     11.2   14.2     -12.5       0/5
  익절 +5%          14.9     12.6   16.8     -12.3       0/5
  익절 +10%         14.6     13.8   21.4     -13.5       0/5
  익절 +20%         14.2     11.4   18.4     -13.8       0/5

하나도 못 이긴다. 익절률을 바꿔도 마찬가지다.

===========================================================================
결과 2 - 낙폭은 실제로 낮다. 그런데 거래가 안 맞는다
===========================================================================
낙폭 -15.9% -> -12.3% 로 3.6%p 줄어든다. 이건 다섯 시작일 전부에서
일관되게 나오므로 우연이 아니다. 시작일에 따른 편차도 훨씬 작다
(익절 +3% 는 11.2~14.2 로 3.0%p, 기준은 16.7~26.6 으로 9.9%p).

문제는 값이다. 낙폭 3.6%p 를 사는 데 수익 7.1%p 를 낸다.

  기준        22.0 / 15.9 = 1.38
  익절 +5%    14.9 / 12.3 = 1.21

위험 대비로 따져도 기준이 낫다. "큰 이득을 포기하고 큰 손해를 피한다"
가 목표라도, 이건 포기하는 이득이 피하는 손해보다 크다.

===========================================================================
결과 3 - 왜 지는가: 이긴 것만 팔고 진 것만 남는다
===========================================================================
끝난 시점에 슬롯이 어떤 상태인지 봤다.

  익절률    익절 횟수   평균 보유   최장 묶임   끝에 남은 10슬롯
  +3%        235회      43일      531일    10/10 마이너스, 최악 -32.7%
  +5%        157회      60일      869일    10/10 마이너스, 최악 -32.7%
  +10%        91회     113일      223일    10/10 마이너스, 최악 -35.4%

**10슬롯이 전부 마이너스로 끝난다.** 우연이 아니라 규칙의 구조다.
오른 종목은 익절선에 닿아서 팔려 나가고, 안 오른 종목은 팔 조건이 없어서
계속 남는다. 그래서 시간이 갈수록 포트폴리오가 "못 오른 것들의 모음"이
된다. 익절률을 낮출수록(+3%) 이기는 종목이 더 빨리 빠져나가므로 이
쏠림이 더 심해진다 - 실제로 +3% 가 제일 나쁘다.

최장 869거래일(약 3.5년) 동안 +5% 를 한 번도 못 찍은 슬롯이 있었다.
그 기간 내내 자본의 10%가 거기 잠겨 있었다. 상장폐지되면 그 슬롯은 0이
된다 (이 패널에는 상장폐지 종목이 들어 있으므로 그 경우가 실제로 잡힌다).

===========================================================================
읽는 법
===========================================================================
1) 아이디어 자체는 analyze_stops.py 의 익절과 다른 것이 맞았다. 현금이
   노는 손해가 없어서 따로 잴 값어치가 있었고, 실제로 따로 쟀다.
2) 그런데 결과는 같은 방향이다 - 익절선으로 파는 규칙은 넣지 않는다.
   이유가 새로 밝혀졌다: 이익이 난 것만 골라 파는 규칙은 포트폴리오를
   못 오른 것들로 채운다.
3) 낙폭이 낮아지는 것은 진짜다. 다만 그 대가가 더 크다. 낙폭을 줄이고
   싶으면 파는 규칙이 아니라 **종목 수(분산)** 쪽을 봐야 한다 - 그건
   아직 안 쟀다.
4) 내 버그 하나가 "처음으로 반띵을 통과한 후보"를 만들어냈다. 검증이
   통과했다는 것만으로는 부족하고, 입력이 깨끗한지를 따로 봐야 한다.

실행:
  python analyze_recycle.py            # 전체
  python analyze_recycle.py --verify   # 반띵 + 시작일 5개
"""
import argparse
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_stops as A  # noqa: E402
import strategy as S  # noqa: E402

CAPITAL = A.CAPITAL
FEE_ONE_WAY = A.FEE_ONE_WAY
N_SLOT, DAYS_PER_YEAR = 10, 246
POOL_SIZE = 40            # 빈 슬롯을 채울 후보 (저변동 상위 몇 개까지 볼지)
TAKES = (3, 5, 10, 20)
N_STARTS, START_GAP, BASE_DI = 5, 37, 250


def pool_at(panel, di, n=POOL_SIZE):
    """그 시점 저변동 상위 n종목. 미래 정보 없음 (factor_score 가 보장)."""
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    sc = [(x, c) for c in cand
          if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
    sc.sort(reverse=True)
    return [c for _s, c in sc[:n]]


def run_recycle(dates, panel, hl, take, start, upto=None,
                capital=CAPITAL, n_slot=N_SLOT):
    """익절까지 버티고 슬롯을 재활용한다.

    반환 {curve, fees, takes, holds, open, }.

    판 날에는 다시 사지 못하게 막는다. 익절은 장중 체결인데 매수는 그날
    시가로 잡으면 오후에 받은 돈으로 오전 가격을 사는 것이 된다. 그
    한 줄이 연수익을 13.3% 에서 25.4% 로 부풀렸다.
    """
    n = upto if upto is not None else len(dates)
    slot_cash = capital / n_slot
    slots = [None] * n_slot          # (종목, 수량, 매수가, 들어간 날)
    cash = [slot_cash] * n_slot
    last_px = [0.0] * n_slot
    free_from = [start] * n_slot     # 이 날부터 다시 살 수 있다
    fees, n_take, holds = 0.0, 0, []
    curve = []

    di = start
    while di < n:
        pool = pool_at(panel, di)
        held = {s[0] for s in slots if s}

        # 1) 익절 체결
        for i, s in enumerate(slots):
            if not s:
                continue
            code, qty, basis, edi = s
            v = hl.get((di, code))
            op = A.price(panel, code, di, "open")
            if v is None or op is None:
                continue          # 거래정지/데이터 공백 - 그냥 들고 간다
            hit = A.exit_price(basis, op, v[0], v[1], None, take)
            if hit:
                px, _kind = hit
                cash[i] += qty * px * (1 - FEE_ONE_WAY)
                fees += qty * px * FEE_ONE_WAY
                n_take += 1
                holds.append(di - edi)
                slots[i] = None
                free_from[i] = di + 1
                held.discard(code)

        # 2) 빈 슬롯 채우기
        for i, s in enumerate(slots):
            if s or not pool or di < free_from[i]:
                continue
            for code in pool:
                if code in held:
                    continue
                px = A.price(panel, code, di, "open")
                if not px:
                    continue
                qty = int(cash[i] // (px * (1 + FEE_ONE_WAY)))
                if qty < 1:
                    continue
                cash[i] -= qty * px * (1 + FEE_ONE_WAY)
                fees += qty * px * FEE_ONE_WAY
                slots[i] = (code, qty, px, di)
                last_px[i] = px
                held.add(code)
                break

        # 3) 그날 평가액
        tot = sum(cash)
        for i, s in enumerate(slots):
            if s:
                v = A.price(panel, s[0], di, "close")
                if v:
                    last_px[i] = v
                # 거래정지/공백을 0원으로 잡으면 가짜 낙폭이 생긴다.
                # 마지막으로 알려진 값을 들고 간다.
                tot += s[1] * last_px[i]
        curve.append(tot)
        di += 1

    open_slots = []
    for i, s in enumerate(slots):
        if s:
            pnl = (last_px[i] / s[2] - 1) * 100 if s[2] else 0.0
            open_slots.append((s[0], di - 1 - s[3], pnl))
    return {"curve": curve, "fees": fees, "takes": n_take,
            "holds": holds, "open": open_slots}


def mdd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def annualized(curve, capital=CAPITAL):
    if not curve:
        return 0.0
    yrs = len(curve) / DAYS_PER_YEAR
    return ((curve[-1] / capital) ** (1 / yrs) - 1) * 100 if yrs > 0 else 0.0


def worth_it(base_ret, base_dd, new_ret, new_dd):
    """낙폭을 줄인 대가가 값어치가 있나.

    낙폭이 줄었다는 것만으로는 부족하다. 포기한 수익과 견줘야 한다.
    수익/낙폭 비가 나빠지면 '보호를 산 것' 이 아니라 그냥 손해다.
    """
    if base_dd == 0 or new_dd == 0:
        return False
    return (new_ret / abs(new_dd)) > (base_ret / abs(base_dd))


def losers_only(open_slots):
    """끝에 남은 슬롯이 전부 마이너스인가.

    익절선으로만 파는 규칙은 오른 것을 내보내고 안 오른 것을 남긴다.
    그 쏠림이 실제로 일어나는지 보는 지표다.
    """
    if not open_slots:
        return False
    return all(p < 0 for _c, _d, p in open_slots)


def main():
    ap = argparse.ArgumentParser(description="슬롯 재활용 익절 전략 검증")
    ap.add_argument("--verify", action="store_true",
                    help="반띵 + 시작일 5개까지 돌린다 (오래 걸린다)")
    args = ap.parse_args()

    dates, panel = S.load_panel()
    hl = A.load_high_low(dates)
    import analyze_event_rebal as E
    order, _rank = E.daily_ranks(dates, panel, BASE_DI)

    print(f"\n{CAPITAL:,}원 / 슬롯 {N_SLOT}개 / 손절 없음 / 시간 제한 없음")
    print(f"{'규칙':<14}{'연수익%':>9}{'최대낙폭%':>10}{'익절횟수':>9}"
          f"{'평균보유':>9}{'끝에 마이너스':>13}")

    bc, _f, _t = E.run_calendar(dates, panel, order, 120, BASE_DI)
    br, bd = annualized(bc), mdd(bc)
    print(f"{'기준(120일)':<14}{br:>9.1f}{bd:>10.1f}{'-':>9}{'-':>9}{'-':>13}")

    for take in TAKES:
        r = run_recycle(dates, panel, hl, take, BASE_DI)
        ret, dd = annualized(r["curve"]), mdd(r["curve"])
        open_slots = r["open"]
        neg = sum(1 for _c, _d, p in open_slots if p < 0)
        hold = st.mean(r["holds"]) if r["holds"] else 0.0
        label = f"익절 +{take}%"
        tail = f"{neg}/{len(open_slots)}"
        print(f"{label:<14}{ret:>9.1f}{dd:>10.1f}"
              f"{r['takes']:>9}{hold:>9.0f}{tail:>13}")
        print(f"{'':14}낙폭을 줄인 값어치: "
              f"{'있음' if worth_it(br, bd, ret, dd) else '없음'}"
              f" (수익/낙폭 {ret/abs(dd):.2f} vs 기준 {br/abs(bd):.2f})")

    if not args.verify:
        print("\n--verify 를 붙이면 반띵과 시작일 5개까지 돌린다.")
        return 0

    n = len(dates)
    half = BASE_DI + (n - BASE_DI) // 2
    print("\n=== 반띵 검증 ===")
    ca, _f, _t = E.run_calendar(dates, panel, order, 120, BASE_DI, upto=half)
    cb, _f, _t = E.run_calendar(dates, panel, order, 120, half, upto=n)
    ba, bb = annualized(ca), annualized(cb)
    print(f"{'기준(120일)':<14}{ba:>9.1f}{bb:>9.1f}")
    for take in TAKES:
        x = annualized(run_recycle(dates, panel, hl, take, BASE_DI,
                                   upto=half)["curve"])
        y = annualized(run_recycle(dates, panel, hl, take, half, upto=n)["curve"])
        v = ("양쪽 이김" if x > ba and y > bb
             else "뒤집힘" if (x > ba) != (y > bb) else "양쪽 짐")
        print(f"{'익절 +' + str(take) + '%':<14}{x:>9.1f}{y:>9.1f}   {v}")

    print("\n=== 시작일 5개 (같은 시작일끼리 짝지어 비교) ===")
    starts = [BASE_DI + k * START_GAP for k in range(N_STARTS)]
    base = []
    for s in starts:
        c, _f, _t = E.run_calendar(dates, panel, order, 120, s)
        base.append(annualized(c))
    print(f"{'기준(120일)':<14}{st.median(base):>9.1f}")
    for take in TAKES:
        rs = [annualized(run_recycle(dates, panel, hl, take, s)["curve"])
              for s in starts]
        wins = sum(1 for i in range(len(starts)) if rs[i] > base[i])
        print(f"{'익절 +' + str(take) + '%':<14}{st.median(rs):>9.1f}"
              f"   기준 이긴 횟수 {wins}/{len(starts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
