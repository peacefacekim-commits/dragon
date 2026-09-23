"""날짜 대신 '밀려난 종목이 생기면' 교체하기 - 이벤트 방식.

(2026-09-19 신설) 사용자: "몇가지 종목을 두고 종목인 것들을 보고 있다가
교체할 종목이 나오면 그때 날을 정해서 팔거나?"

먼저 오해 하나를 짚는다. 사용자가 "교체일을 조짐이 있는 시기로 정해야
한다는 말이지?" 라고 물었는데, 내 결론은 **반대**였다. 조짐은 보지 말고
날짜로 고정하라는 것이었다 (좋은날/나쁜날 23가지 전부 실패).

그런데 사용자가 낸 이 아이디어는 그것과 다르고, 구조가 맞다.
  좋은날/나쁜날 - 트리거가 '시장이 좋은가' -> 타이밍 차원. 23/23 실패
  이 아이디어   - 트리거가 '내 종목이 아직 상위권인가' -> 종목 선택 차원.
                  우리가 엣지를 가진 유일한 곳이다.

틀에서 보면 이 방식은 교체비율을 **직접** 제어한다.
  날짜 방식   40일마다 확인 -> 교체비율은 그 사이 순위 변화로 결정됨
  이벤트 방식 매일 확인, 버퍼 밖으로 나가면 그때 교체
              -> 교체비율을 버퍼 폭으로 내가 정한다

버퍼가 핵심이다. 10위 밖으로 나가는 즉시 팔면 10위/11위를 오가는 종목을
계속 사고팔게 된다. 버퍼를 두면(예: 30위 밖일 때만 팔기) 그 왕복이 사라진다.

===========================================================================
결과 1 - 버퍼별 성과가 지그재그다. 추세가 없다
===========================================================================
200만원, 1주 단위, 시작일 5개 중앙값

  방식                연환산   최대낙폭   연 거래   수수료/자본
  버퍼 10위 밖 교체   +21.3%   -18.8%   265.9회     18.6%
  버퍼 12위           +17.0%   -21.0%   148.8회     10.1%
  버퍼 15위           +20.6%   -19.2%   101.0회      7.3%
  버퍼 20위           +15.8%   -20.5%    77.1회      5.0%
  버퍼 30위           +16.1%   -16.8%    49.6회      3.5%
  버퍼 50위           +21.3%   -18.5%    28.5회      1.8%
  버퍼 100위          +22.9%   -23.9%    12.4회      0.8%
  날짜 40일 (기준)    +19.3%   -16.8%    50.3회      4.0%
  날짜 60일 (기준)    +15.6%   -18.0%    38.6회      2.7%

  21.3 -> 17.0 -> 20.6 -> 15.8 -> 16.1 -> 21.3 -> 22.9.
  **버퍼를 넓힐수록 좋아지는 게 아니라 오르내린다.** 버퍼 15위가 12위와
  20위를 둘 다 이길 이유가 없다. 4.8%p 왕복은 잡음의 모양이다.

  거래 횟수를 맞춰 비교하면
    버퍼 30위  49.6회  +16.1%  낙폭 -16.8%
    날짜 40일  50.3회  +19.3%  낙폭 -16.8%   <- 같은 조건에서 날짜가 +3.2%p
  반대로
    버퍼 50위  28.5회  +21.3%
    날짜 60일  38.6회  +15.6%   <- 여기선 이벤트가 이긴다
  방향이 일관되지 않는다.

===========================================================================
결과 2 - 시작일 흔들림이 버퍼 간 차이와 같은 크기다
===========================================================================
  방식          중앙값     최소     최대     폭
  버퍼 50위    +21.3%  +11.6%  +23.4%  11.7%p
  버퍼 100위   +22.9%  +15.4%  +24.1%   8.7%p
  날짜 40일    +19.3%  +14.0%  +19.8%   5.7%p
  날짜 60일    +15.6%  +10.5%  +22.0%  11.5%p

  시작일 흔들림 폭 중앙값 **6.0%p**
  버퍼 간 최고-최저 차이  **7.1%p**

  (처음 쓴 스크립트는 '7.1 > 6.0 이니 볼 만하다' 고 찍었는데 그건
  너무 관대한 판정이었다. 두 값이 같은 자릿수면 구별이 안 되는 것이다.
  버퍼 하나를 고르면 그 선택의 근거가 흔들림 안에 있다.)

===========================================================================
결과 3 - 결정적: 반기 양방향에서 뒤집힌다
===========================================================================
  방식          전반부    후반부
  버퍼 10위      +4.1%   +42.7%
  버퍼 15위      +4.1%   +35.7%
  버퍼 30위      +4.5%   +29.8%
  버퍼 50위      +4.7%   +29.4%
  버퍼 100위     +3.0%   +39.2%
  날짜 40일      +6.5%   +30.2%
  날짜 60일      +7.3%   +30.8%

  전반부 1위: 날짜 60일 (+7.3%)
  후반부 1위: 버퍼 10위 (+42.7%)
  **1위가 완전히 다르다.**

  이벤트 최고 vs 날짜 최고
    전반부 +4.7% vs +7.3%   날짜 승
    후반부 +42.7% vs +30.8%  이벤트 승
  뒤집힌다. **이벤트 방식이 낫다고 말할 수 없다.**

  그리고 패턴이 읽힌다. 전반부(2021~2023, 약세)에는 날짜 방식이 모든
  버퍼를 이겼고, 후반부(2024~2026, 강세)에는 좁은 버퍼가 제일 좋았다.
  좁은 버퍼 = 자주 교체 = 추세에 더 많이 노출. 즉 **엣지가 아니라
  레짐 베팅이다.** 다음 구간이 강세면 이기고 약세면 진다.

===========================================================================
결과 4 - '수수료 이상 이익 나면 팔기' 는 -4.9%p 였다
===========================================================================
사용자: "내가 팔때 수수료 이상의 이윤이 나면 팔라고 해두면 해결돼지
않을까?"

먼저 수수료의 정체를 밝혀둔다.
  매수 수수료 0.015% + 매도 수수료 0.015% + 매도 증권거래세 0.180%
  = 0.21%.  **86% 가 세금이다.**
  증권사 수수료를 0 으로 만들어도 0.18% 가 남는다. 수수료를 깎아서
  해결되는 문제가 아니다.

그리고 이 규칙에는 논리 문제가 있다. **수수료는 이익에 붙는 게 아니라
거래에 붙는다.** 이익이 났든 손실이 났든 팔면 0.21% 다. 그러므로
  (X) 내 수익이 수수료보다 큰가      <- 이미 정해진 과거. 판단에 못 쓴다
  (O) 바꿔 탈 종목이 지금 것보다 0.21% 이상 더 벌어줄까  <- 미래
-5% 물린 종목의 -5% 는 팔든 안 팔든 이미 내 것이고, 안 팔아도 회복되지
않는다.

그래도 그대로 돌려봤다. 교체일에 밀려난 종목 중 무엇을 팔까
(40일 주기 / 부분교체 / 200만원 / 시작일 6개 중앙값)

  규칙                        연환산   최대낙폭   매도   안 판 것  기준대비
  밀려나면 전부 팔기 (기준)     +16.2%  -17.9%  114회    0회      -
  이익>수수료(0.21%)만 팔기   +11.3%  -17.8%   44회   90회  -4.9%p
  이익 난 것만 팔기            +11.3%  -17.8%   44회   90회  -4.9%p
  손실 난 것만 팔기 (대조군)    +14.7%  -23.3%   23회  116회  -1.4%p

  **제안한 규칙이 -4.9%p 다.** 그리고 정반대 규칙(-1.4%p)이 오히려 덜
  나쁘다. 즉 방향까지 거꾸로다 - 손실 난 것을 들고 가는 쪽이 더 해롭다.

  이유는 '안 판 것 90회' 에 있다. 저변동 10위 밖으로 밀려난 종목을
  손실이라는 이유로 계속 들고 있으면, 저변동이 아닌 종목을 들고 있게
  된다. 전략이 조금씩 망가진다.

  참고: 0.21% 문턱은 사실 아무것도 안 걸렀다 ('이익>0.21%' 와
  '이익>0' 이 똑같은 44회/90회다). 주가 움직임에 비해 0.21% 가 너무
  작아서 문턱 구실을 못 한다.

  다만 사용자의 **직관 자체는 맞다** - "거래가 수수료를 넘길 만할 때만
  하라". 그걸 제대로 구현한 것이 위의 **버퍼**다. 버퍼를 넓히는 것은
  '교체할 가치가 충분히 커졌을 때만 거래한다' 는 뜻이다. 내 손익이
  아니라 순위 차이로 재기 때문에 sunk cost 를 안 섞는다.

===========================================================================
읽는 법 - 그래도 이벤트 방식을 쓸 이유가 하나 있다 (수익이 아니다)
===========================================================================
  1) 아이디어의 구조는 맞다. 트리거가 시장이 아니라 내 종목의 순위이므로
     타이밍이 아니고, 엣지가 있는 차원이다. 실패한 23가지와 다르다.

  2) 그런데 수익으로는 날짜 방식보다 낫다고 말할 수 없다. 반기에서
     뒤집히고, 버퍼별 지그재그는 시작일 흔들림과 같은 크기다.

  3) 전반부/후반부 차이는 레짐 의존이다. 좁은 버퍼는 강세장 베팅이다.
     그걸 고르는 것은 '다음이 강세장' 에 거는 것이고, 그건 이 세션에서
     23번 실패한 그 예측이다.

  4) **실무적으로는 날짜 방식이 낫다. 이유는 수익이 아니라 운영이다.**
       날짜 방식   - 다음에 주문할 날을 미리 안다. 1년에 6번 정해져 있다.
       이벤트 방식 - 언제 주문해야 할지 모른다. 매일 확인 결과를 봐야 한다.
     사용자 목표가 '신경 안 쓰고' 였다. 수익이 구별 안 되면 **언제
     할지 미리 아는 쪽**이 목표에 맞는다. 프로그램은 어느 쪽이든 자동으로
     하지만, 주문은 사람이 낸다.

  5) 굳이 이벤트 방식을 쓰겠다면 버퍼를 넓게(30~50위) 잡아라. 좁은 버퍼는
     거래가 폭증하고(버퍼 10위는 연 266회) 강세장 베팅이 된다. 다만 이건
     검증된 권고가 아니라 '덜 위험한 선택' 이다.

  6) 주의: 여기도 호가 스프레드가 안 들어갔다. 이벤트 방식은 거래가
     많을 수 있으므로 스프레드를 넣으면 더 불리해진다. 즉 이 표는
     이벤트 방식에 이미 관대하다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_event_rebal.py           # 버퍼별 훑기
    python analyze_event_rebal.py --verify  # 흔들림 + 반기 양방향
"""
import argparse
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import strategy as S  # noqa: E402

CAPITAL = 2_000_000
FEE_ONE_WAY = S.FEE_ROUND_TRIP_PCT / 2 / 100
PICK, DAYS_PER_YEAR = 10, 246
N_STARTS, START_GAP = 5, 37
BUFFERS = (10, 12, 15, 20, 30, 50, 100)
PERIODS = (40, 60)


def price(panel, code, di, field="open"):
    s = panel.get(code)
    if s is None:
        return None
    j = s.pos.get(di)
    if j is None:
        return None
    v = (s.open[j] if field == "open" else s.close[j]) or s.close[j]
    return v or None


def daily_ranks(dates, panel, base):
    """날짜별 저변동 순위. 매일 쓰므로 미리 계산해둔다.

    factor_score 는 그 시점까지의 정보만 쓰므로 미래 정보가 없다.
    """
    order, rank = {}, {}
    di = base
    n = len(dates)
    while di < n:
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(sc) >= PICK:
            sc.sort(reverse=True)
            codes = [c for _s, c in sc]
            order[di] = codes
            rank[di] = {c: i + 1 for i, c in enumerate(codes)}
        di += 1
    return order, rank


def buy_greedy(panel, cash, codes, di):
    p = {c: price(panel, c, di) for c in codes}
    p = {c: v for c, v in p.items() if v}
    if not p:
        return {}, cash, 0.0
    slot = cash / len(p)
    hold, spent, fee = {}, 0.0, 0.0
    for c, v in p.items():
        cost = v * (1 + FEE_ONE_WAY)
        q = int(slot // cost)
        if q:
            hold[c] = q
            spent += q * cost
            fee += q * v * FEE_ONE_WAY
    left = cash - spent
    ordered = sorted(p.items(), key=lambda kv: kv[1])
    added = True
    while added:
        added = False
        for c, v in ordered:
            cost = v * (1 + FEE_ONE_WAY)
            if left >= cost:
                hold[c] = hold.get(c, 0) + 1
                left -= cost
                fee += v * FEE_ONE_WAY
                added = True
    return hold, left, fee


def run_event(dates, panel, order, rank, buffer_rank, start, upto=None,
              capital=CAPITAL):
    """매일 확인. 보유 종목 순위가 buffer_rank 밖이면 그때 교체."""
    n = upto if upto is not None else len(dates)
    cash, hold = float(capital), {}
    fees, n_trade = 0.0, 0
    curve = []
    di = start
    while di < n:
        rk = rank.get(di)
        if rk is not None:
            if not hold:
                hold, cash, f = buy_greedy(panel, cash, order[di][:PICK], di)
                fees += f
                n_trade += len(hold)
            else:
                # 유니버스에서 빠진 종목도 순위를 매우 크게 봐서 교체한다
                out = [c for c in hold if rk.get(c, 10 ** 9) > buffer_rank]
                if out:
                    for c in out:
                        v = price(panel, c, di)
                        if v:
                            cash += hold[c] * v * (1 - FEE_ONE_WAY)
                            fees += hold[c] * v * FEE_ONE_WAY
                            n_trade += 1
                        del hold[c]
                    need = PICK - len(hold)
                    add = [c for c in order[di] if c not in hold][:need]
                    got, cash, f = buy_greedy(panel, cash, add, di)
                    fees += f
                    n_trade += len(got)
                    hold.update(got)
        curve.append(cash + sum(q * (price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, fees, n_trade


def run_calendar(dates, panel, order, period, start, upto=None,
                 capital=CAPITAL):
    """날짜 방식 + 부분교체. 비교 기준이다."""
    n = upto if upto is not None else len(dates)
    cash, hold = float(capital), {}
    fees, n_trade = 0.0, 0
    curve = []
    di = start
    while di < n:
        if (di - start) % period == 0 and di in order:
            new = order[di][:PICK]
            keep = {c: q for c, q in hold.items() if c in new}
            for c in [c for c in hold if c not in new]:
                v = price(panel, c, di)
                if v:
                    cash += hold[c] * v * (1 - FEE_ONE_WAY)
                    fees += hold[c] * v * FEE_ONE_WAY
                    n_trade += 1
            add = [c for c in new if c not in hold]
            got, cash, f = (buy_greedy(panel, cash, add, di) if add
                            else ({}, cash, 0.0))
            fees += f
            n_trade += len(got)
            hold = {**keep, **got}
        curve.append(cash + sum(q * (price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve, fees, n_trade


def mdd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def annualized(curve, capital=CAPITAL):
    yrs = len(curve) / DAYS_PER_YEAR
    return ((curve[-1] / capital) ** (1 / yrs) - 1) * 100 if yrs > 0 else 0.0


def is_zigzag(values):
    """값이 오르내리면 True. 단조면 False.

    버퍼를 넓힐수록 좋아지는 '추세' 가 있으면 단조여야 한다. 지그재그면
    그 차이는 잡음이라고 봐야 한다.
    """
    if len(values) < 3:
        return False
    ups = sum(1 for a, b in zip(values, values[1:]) if b > a)
    downs = sum(1 for a, b in zip(values, values[1:]) if b < a)
    return ups > 0 and downs > 0


def pickable(buffer_spread, start_spread):
    """버퍼를 고를 수 있나. 흔들림과 같은 자릿수면 못 고른다.

    처음 쓴 스크립트는 'spread 차이가 크다' 를 '>=' 하나로 판정해서
    7.1 vs 6.0 을 '볼 만하다' 고 찍었다. 그건 너무 관대했다. 최소
    두 배는 돼야 구별했다고 할 수 있다.
    """
    return buffer_spread >= start_spread * 2


def main(do_verify=False):
    dates, panel = S.load_panel()
    base = max(140, S.LIQUIDITY_DAYS + 2)
    print("일별 순위 계산 중...")
    order, rank = daily_ranks(dates, panel, base)
    print(f"순위 있는 날 {len(rank):,}일")
    starts = [base + k * START_GAP for k in range(N_STARTS)]
    n = len(dates)

    if do_verify:
        # ------------------------------------- 흔들림
        print("\n" + "=" * 96)
        print("=== 검증 1) 시작일 흔들림이 버퍼 간 차이와 같은 크기인가 ===")
        print("=" * 96)
        print(f"  {'방식':<16} {'중앙값':>9} {'최소':>9} {'최대':>9} {'폭':>8}")
        spreads, meds = [], []
        for buf in (10, 15, 20, 30, 50, 100):
            anns = [annualized(run_event(dates, panel, order, rank, buf, s0)[0])
                    for s0 in starts]
            spreads.append(max(anns) - min(anns))
            meds.append(st.median(anns))
            print(f"  {'버퍼 ' + str(buf) + '위':<16} "
                  f"{st.median(anns):>+8.1f}% {min(anns):>+8.1f}% "
                  f"{max(anns):>+8.1f}% {max(anns)-min(anns):>7.1f}%p")
        for period in PERIODS:
            anns = [annualized(run_calendar(dates, panel, order, period, s0)[0])
                    for s0 in starts]
            spreads.append(max(anns) - min(anns))
            print(f"  {'날짜 ' + str(period) + '일':<16} "
                  f"{st.median(anns):>+8.1f}% {min(anns):>+8.1f}% "
                  f"{max(anns):>+8.1f}% {max(anns)-min(anns):>7.1f}%p")
        ss, bs = st.median(spreads), max(meds) - min(meds)
        print(f"\n  시작일 흔들림 폭 중앙값 {ss:.1f}%p")
        print(f"  버퍼 간 최고-최저 차이  {bs:.1f}%p")
        print("  " + ("-> 버퍼를 고를 수 있다" if pickable(bs, ss) else
                      "-> 두 값이 같은 자릿수다. 버퍼를 고를 수 없다."))

        # ------------------------------------- 반기 양방향
        mid = base + (n - base) // 2
        print("\n" + "=" * 96)
        print("=== 검증 2) 반기 양방향 - 1위가 양쪽에서 같은가 ===")
        print("=" * 96)

        def seg(fn, arg, lo, hi):
            outs = []
            for s0 in [lo + k * 41 for k in range(4)]:
                if s0 + 100 >= hi:
                    continue
                cv = fn(arg, s0, hi)[0]
                if len(cv) >= 180:
                    outs.append(annualized(cv))
            return st.median(outs) if outs else None

        def ev(arg, s0, hi):
            return run_event(dates, panel, order, rank, arg, s0, upto=hi)

        def cal(arg, s0, hi):
            return run_calendar(dates, panel, order, arg, s0, upto=hi)

        print(f"  {'방식':<16} {'전반부':>10} {'후반부':>10}")
        res = []
        for buf in (10, 15, 30, 50, 100):
            a, b = seg(ev, buf, base, mid), seg(ev, buf, mid, n)
            if a is not None and b is not None:
                res.append((f"버퍼 {buf}위", a, b, "event"))
                print(f"  {'버퍼 ' + str(buf) + '위':<16} "
                      f"{a:>+9.1f}% {b:>+9.1f}%")
        for period in PERIODS:
            a, b = seg(cal, period, base, mid), seg(cal, period, mid, n)
            if a is not None and b is not None:
                res.append((f"날짜 {period}일", a, b, "cal"))
                print(f"  {'날짜 ' + str(period) + '일':<16} "
                      f"{a:>+9.1f}% {b:>+9.1f}%")
        if res:
            ra = max(res, key=lambda r: r[1])
            rb = max(res, key=lambda r: r[2])
            print(f"\n  전반부 1위 {ra[0]} ({ra[1]:+.1f}%) / "
                  f"후반부 1위 {rb[0]} ({rb[2]:+.1f}%)")
            print(f"  1위가 같은가: "
                  f"{'예' if ra[0] == rb[0] else '아니다 - 고를 수 없다'}")
            ea = max((r[1] for r in res if r[3] == "event"), default=None)
            eb = max((r[2] for r in res if r[3] == "event"), default=None)
            ca = max((r[1] for r in res if r[3] == "cal"), default=None)
            cb = max((r[2] for r in res if r[3] == "cal"), default=None)
            if None not in (ea, eb, ca, cb):
                print("\n  이벤트 최고 vs 날짜 최고")
                print(f"    전반부 {ea:+.1f}% vs {ca:+.1f}%  "
                      f"{'이벤트 승' if ea > ca else '날짜 승'}")
                print(f"    후반부 {eb:+.1f}% vs {cb:+.1f}%  "
                      f"{'이벤트 승' if eb > cb else '날짜 승'}")
                flip = (ea > ca) != (eb > cb)
                print("  " + ("-> 뒤집힌다. 이벤트가 낫다고 말할 수 없다."
                              if flip else "-> 양쪽 같은 방향이다."))
        return 0

    # ------------------------------------- 버퍼별 훑기
    print(f"\n{CAPITAL:,}원, 1주 단위, 시작일 {N_STARTS}개 중앙값")
    print("=" * 96)
    print("=== 보유 종목이 N위 밖으로 나가면 교체 ===")
    print("=== 버퍼가 좁으면 10/11위를 오가는 종목을 계속 사고팔게 된다 ===")
    print("=" * 96)
    print(f"  {'방식':<20} {'연환산':>9} {'최대낙폭':>9} {'연 거래':>8} "
          f"{'수수료/자본':>11}")
    ev_meds = []
    for buf in BUFFERS:
        anns, mds, trs, fs = [], [], [], []
        for s0 in starts:
            cv, fee, nt = run_event(dates, panel, order, rank, buf, s0)
            anns.append(annualized(cv))
            mds.append(mdd(cv))
            trs.append(nt / (len(cv) / DAYS_PER_YEAR))
            fs.append(fee / CAPITAL * 100)
        ev_meds.append(st.median(anns))
        print(f"  {'버퍼 ' + str(buf) + '위':<20} {st.median(anns):>+8.1f}% "
              f"{st.median(mds):>8.1f}% {st.median(trs):>7.1f}회 "
              f"{st.median(fs):>10.1f}%")
    print()
    for period in PERIODS:
        anns, mds, trs, fs = [], [], [], []
        for s0 in starts:
            cv, fee, nt = run_calendar(dates, panel, order, period, s0)
            anns.append(annualized(cv))
            mds.append(mdd(cv))
            trs.append(nt / (len(cv) / DAYS_PER_YEAR))
            fs.append(fee / CAPITAL * 100)
        print(f"  {'날짜 ' + str(period) + '일 (기준)':<20} "
              f"{st.median(anns):>+8.1f}% {st.median(mds):>8.1f}% "
              f"{st.median(trs):>7.1f}회 {st.median(fs):>10.1f}%")

    print(f"\n  버퍼별 연환산: "
          + " -> ".join(f"{v:+.1f}" for v in ev_meds))
    if is_zigzag(ev_meds):
        print("  **지그재그다.** 버퍼를 넓힐수록 좋아지는 추세가 없다.")
        print("  추세가 없으면 그 차이는 잡음으로 봐야 한다.")
    else:
        print("  단조 추세가 있다. 버퍼가 성과를 가른다는 뜻이다.")
    print("\n  --verify 로 흔들림과 반기 양방향을 확인하라.")
    return 0


if __name__ == "__main__":
    _ap = argparse.ArgumentParser(description="이벤트 방식 교체 검사")
    _ap.add_argument("--verify", action="store_true",
                     help="시작일 흔들림 + 반기 양방향만 돌린다")
    _a = _ap.parse_args()
    raise SystemExit(main(_a.verify))
