"""종목별 수급으로 진입 시점을 정한다 - 시장 전체 합계가 아니라 내 종목.

(2026-09-17 신설) 사용자 요청: "종목별 수급 데이터로 가고, 그 전날 데이터가
안좋을 때 매수를 하고 그 전날 데이터가 좋은날 일때 파는 식으로"

지금까지 쓴 수급 지표(flow_foreign/flow_inst)는 시장 전체 합계였다. 이번엔
**내가 살 그 10종목에 전날 외국인/기관이 얼마나 들어왔나** 를 본다.
data/krx_flow_*.csv 에 종목별 순매수가 연 28만 행씩 쌓여 있다.

신호
  그날 뽑힌 10종목에 대해, 전날 순매수를 전날 거래대금으로 나눈 비율의 평균.
  높을수록 '좋은 날'(돈이 들어왔다), 낮을수록 '나쁜 날'(팔렸다).
  거래대금으로 나누는 이유: 삼성전자 100억과 BNK금융 100억은 다른 의미다.
  전날 수급은 장 마감 후 확정되므로 그날 시가에 쓸 수 있다 (미래 정보 아님).

두 가지 방식을 따로 본다 - 섞으면 뭐가 이겼는지 알 수 없다.

  (A) 나쁜날 매수 + 좋은날 매도 (진입도 청산도 신호)
      평균 보유가 4.6~5.6일로 짧아지고 거래가 57~68회로 늘어난다.
      네 신호(외국인+기관/외국인만/기관만/개인반대) x 양방향 = 8경우 모두
      밀어놓기 대조군 탈락. 게다가 후반부에서는 기준선(20일 고정, 누적
      +87.2%)이 전부를 이긴다 - 상승장에서 시장을 절반만 타는 손해가 크다.

  (B) 나쁜날에만 진입 + 보유 20일 고정 (청산은 신호와 무관)
      보유기간이 기준선과 같아 수수료 조건이 같다. '진입 시점을 고르는 것'
      만 남는다. 여기서 하나가 살아남았다.

(B) 결과 - 기관 순매수 (하위 40% 진입)

  정방향 (전반부에서 기준 -> 후반부 채점)
    (a) 기준선 20일 고정      31회 평균 +2.137%(±0.808) 누적  +87.2% MDD  -4.0%
    (b) 기관수급 나쁜날 진입   28회 평균 +2.972%(±0.922) 누적 +120.4% MDD  -4.9%
    (c) 기관수급 좋은날 진입   29회 평균 +2.503%(±1.158) 누적  +94.8% MDD -10.9%
    밀어놓기 500번: 중간값 +74.3%, 실제보다 좋은 우연 1.0%      <- 통과

  역방향 (후반부에서 기준 -> 전반부 채점)
    (a) 기준선                31회 평균 -0.134% 누적  -5.5% MDD -17.8%
    (b) 기관수급 나쁜날 진입   30회 평균 -0.094% 누적  -4.8% MDD -20.9%
    (c) 기관수급 좋은날 진입   28회 평균 -0.717% 누적 -19.5% MDD -26.0%
    밀어놓기 500번: 우연 48.4%                                   <- 탈락

  다른 세 신호는 정방향에서도 탈락했다.
    외국인+기관  나쁜날 진입 +60.4% (기준선 +87.2% 보다 낮다), 우연 78.6%
    외국인만     +57.4%, 우연 95.0%.  이 신호는 오히려 '좋은날 진입' 이
                 양쪽에서 더 좋았다 (+66.4% / +7.9%) - 기관과 방향이 반대다
    개인(반대부호) +98.5%, MDD -3.4% 로 모양은 좋은데 우연 10.2% 로 탈락
                 (개인 순매수는 기관/외국인의 거울상이라 겹치는 정보다)

  이게 앞선 시도들과 다른 점: 역방향에서 **깨지지 않았다**. 시장 전체 지표로
  같은 걸 했을 때는 역방향이 -29.1% 였다(analyze_timing.py). 여기서는
  -4.8% 로 기준선(-5.5%)과 사실상 같다. 도움이 안 됐을 뿐 해가 되지 않았다.

  그리고 (b)>(c) 방향은 양쪽 반기 모두 성립한다.
    정방향 +120.4% vs +94.8%   (b가 +25.6%p 우위)
    역방향   -4.8% vs -19.5%   (b가 +14.7%p 우위)
  '기관이 팔고 난 다음에 사는 쪽' 이 '기관이 사고 난 다음에 사는 쪽' 보다
  양쪽에서 낫다. 다른 신호는 이 일관성이 없다 (외국인만은 오히려 반대).

한계 - 이걸 '찾았다' 로 읽으면 안 되는 이유

  1) 검사를 많이 했다. 신호 4개 x 방식 2개 x 방향 2개 = 16번 가까이 봤고,
     1.8% 하나가 나왔다. 16번 중 우연히 5% 미만이 나올 기대값이 0.8개다.
  2) 반기당 거래가 28~30회뿐이다. 거래당 표준오차가 ±0.9%p 인데 (b)-(a)
     차이가 +0.835%p 다. 표준오차 한 개 안에 들어간다.
  3) 최대낙폭은 양쪽 모두 기준선보다 나빴다 (-4.9% vs -4.0%,
     -20.9% vs -17.8%). '큰 손해를 피한다' 는 목적에는 기여하지 못했다.

  그래서 결론은 '앞으로 채점할 가치가 있는 후보' 이고, 지금 켜는 것이 아니다.

평균 보유기간 (사용자 질문)
  (A) 나쁜날 매수 + 좋은날 매도  평균 4.6~5.6일, 중간 2~4일, 범위 1~20일
      절반이 2~4일 안에 닫힌다. 연 26~34거래, 수수료 연 5.5~7.1%.
  (B) 나쁜날 진입 + 20일 고정    20일 (설계상 고정), 연 11거래, 수수료 연 2.3%

===========================================================================
(C) 횡단면 - 저변동 풀 안에서 어느 종목을 고를까 (2026-09-17 추가)
===========================================================================

사용자: "그런 종목들을 뽑고 사고 파는 걸로... 그런 종목들의 오르고 내려가고는
시장 전체보다는 예측이 가능하지 않을까?"

(A),(B)는 바스켓 전체를 '언제' 들고 있을까였고 이건 '어느 것'을 살까다.
횡단면이 통계적으로 유리하다 - 상위10-하위10 차이를 보면 시장 등락이
상쇄된다. 시계열은 회차당 표준편차 4.62% 를 다 뒤집어쓰고 있었고 그
대부분이 시장 변동이었다.

대조군도 깔끔하다. 회차마다 풀 안에서 신호값만 무작위로 섞으면 '이 신호로
고르기' 와 '풀에서 아무거나 10개 고르기' 의 차이만 남는다.

결과 - 저변동 풀 60종목 중 10개, 겹치지 않는 62회차

  선택 방법            평균/회차  표준오차  승률    누적     MDD    기준대비
  변동성 낮은 순(현재)   +1.054   0.592   55%   +79.8  -17.8
  기관 낮은쪽           +1.028   0.749   60%   +69.7  -30.8   -0.026
  외국인 낮은쪽          +1.281   0.780   58%   +96.9  -19.2   +0.227
  개인 높은쪽           +1.621   0.804   58%  +140.8  -20.4   +0.567

  [대조군] 신호값 섞기 2000번, 무작위가 실제보다 좋았던 비율
    기관 20.4% 탈락 / 외국인 8.1% 탈락 / 개인 1.4% 통과
  [반기 분할] 기준 대비 초과분이 양쪽 모두 양수여야 한다
    기관   전반부 -0.408  후반부 +0.357   X
    외국인  전반부 +0.206  후반부 +0.248   O
    개인   전반부 +0.510  후반부 +0.624   O

개인 순매수가 높은 저변동 종목을 고르면 대조군과 반기 분할을 둘 다
통과했다. 이 프로젝트에서 두 검정을 같이 통과한 것은 이게 처음이다.

그래도 켜지 않는 이유

  1) 선택 방법을 10가지 봤다 (기관/외국인/개인/5일수익/변동성/12개월
     모멘텀/거래대금 + 조합 3). 1.4% 에 10을 곱하면 14% 다. 다중검정
     보정 후에는 유의하지 않다.
  2) 최대낙폭이 나빠졌다 (-20.4% vs -17.8%). '큰 손해를 피한다' 는
     목적에는 기여하지 못했다.
  3) 62회차, 표준오차 0.804. 기준대비 +0.567%p 는 표준오차 한 개 안이다.
  4) 개인 순매수는 산술적으로 기관/외국인/기타법인의 거울상이다. 기관
     단독은 탈락(20.4%), 외국인 단독도 탈락(8.1%) 인데 개인만 통과한 것은
     '기관+외국인+기타법인이 같이 팔았을 때' 를 보는 셈이라는 뜻이다.
     독립된 세 증거가 아니라 한 가지를 세 방향에서 본 것이다.

  -> paper_trade.py 가 이 선택의 종목도 같이 기록한다. 앞으로 채점된다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_flow.py                 # (B) 진입만, 세 신호 양방향
    python analyze_flow.py --mode both     # (A) 도 같이
    python analyze_flow.py --mode xsec     # (C) 횡단면 종목 선택
"""
import argparse
import csv
import glob
import math
import statistics as st
import sys

import numpy as np

import strategy as S
from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
FLOW_PREFIX = "krx_flow"
HOLD = 20
ENTRY_Q = 0.40          # 하위 40% 를 '수급이 나쁜 날' 로 본다
LOW_Q, HIGH_Q = 0.30, 0.70   # (A) 방식의 매수/매도 기준
MIN_STOCKS_WITH_FLOW = 5     # 10종목 중 최소 이만큼은 수급 데이터가 있어야
N_SHIFT = 500
SEED = 20260921

SIGNALS = {
    "외국인+기관": lambda inst, frgn, indiv: inst + frgn,
    "외국인만": lambda inst, frgn, indiv: frgn,
    "기관만": lambda inst, frgn, indiv: inst,
    "개인(반대부호)": lambda inst, frgn, indiv: -indiv,
}


def cumulative(rets) -> float:
    v = 1.0
    for x in rets:
        v *= (1 + x / 100)
    return (v - 1) * 100


def max_drawdown(rets) -> float:
    v, peak, worst = 1.0, 1.0, 0.0
    for x in rets:
        v *= (1 + x / 100)
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def load_flow(codes) -> dict:
    """(날짜, 종목) -> (기관, 외국인, 개인) 순매수. 필요한 종목만 읽는다."""
    want = set(codes)
    out = {}
    for path in sorted(glob.glob(str(DATA_DIR / f"{FLOW_PREFIX}_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r["code"] not in want:
                    continue
                try:
                    out[(r["date"], r["code"])] = (
                        float(r["inst"]), float(r["foreign"]),
                        float(r["indiv"]))
                except (TypeError, ValueError):
                    pass
    return out


def build_signal(dates, panel, picks, flow, fn) -> dict:
    """날짜 -> 전날 수급을 전날 거래대금으로 나눈 비율의 바스켓 평균.

    거래대금으로 나누지 않으면 큰 종목의 수급만 보는 지표가 된다.
    """
    dmap = {d: i for i, d in enumerate(dates)}
    out = {}
    for d, codes in picks.items():
        i = dmap[d]
        if i == 0:
            continue
        prev = dates[i - 1]
        pi = i - 1
        vals = []
        for c in codes:
            f = flow.get((prev, c))
            s = panel.get(c)
            if f is None or s is None:
                continue
            j = s.pos.get(pi)
            if j is None or not s.value[j]:
                continue
            vals.append(fn(*f) / s.value[j])
        if len(vals) >= MIN_STOCKS_WITH_FLOW:
            out[d] = st.mean(vals)
    return out


def entry_only(days, sig, cut, ret_fn, hold: int = HOLD, invert=False):
    """신호가 기준을 넘는 날에만 진입하고 hold 일 뒤 청산. 겹치지 않는다.

    청산이 신호와 무관하므로 보유기간이 기준선과 같다 - 수수료 조건을
    맞춘 상태에서 '진입 시점 고르기' 만 남긴다.
    """
    rets, n = [], 0
    while n < len(days) - hold:
        s = sig.get(days[n])
        if s is None:
            n += 1
            continue
        if (s >= cut) if invert else (s <= cut):
            r = ret_fn(days[n], days[n + hold])
            if r is not None:
                rets.append(r)
            n += hold
        else:
            n += 1
    return rets


def both_sides(days, sig, low, high, ret_fn, max_hold: int = HOLD,
               invert=False):
    """(A) 나쁜날 매수 + 좋은날 매도. -> [(진입일, 청산일, 보유일, 수익)]"""
    trades, entry = [], None
    for n, d in enumerate(days):
        s = sig.get(d)
        if s is None:
            continue
        buy = (s >= high) if invert else (s <= low)
        sell = (s <= low) if invert else (s >= high)
        if entry is None:
            if buy:
                entry = (d, n)
        elif sell or n - entry[1] >= max_hold:
            r = ret_fn(entry[0], d)
            if r is not None:
                trades.append((entry[0], d, n - entry[1], r))
            entry = None
    return trades


def shift_control(days, sig, test_fn, real_cum, n_shift=N_SHIFT, seed=SEED):
    """신호만 통째로 밀어 짝을 어긋나게 한다. 설정이 하나이므로 탐색 보정이
    필요 없다 - 순수하게 '신호와 결과의 짝이 우연인가' 만 본다."""
    rng = np.random.default_rng(seed)
    vals = [sig.get(d) for d in days]
    nt = len(days)
    cums = []
    for off in rng.integers(HOLD, max(HOLD + 1, nt - HOLD), size=n_shift):
        sh = {days[j]: vals[(j + int(off)) % nt] for j in range(nt)}
        c = test_fn(sh)
        if c is not None:
            cums.append(c)
    if not cums:
        return None
    cums.sort()
    return {"n": len(cums), "med": cums[len(cums) // 2],
            "p05": cums[int(len(cums) * 0.05)],
            "p95": cums[int(len(cums) * 0.95)],
            "beat": sum(1 for c in cums if c >= real_cum) / len(cums)}


def _stat(rets, label, fee=S.FEE_ROUND_TRIP_PCT):
    if len(rets) < 5:
        return None
    return {"label": label, "n": len(rets), "mean": st.mean(rets),
            "se": st.stdev(rets) / math.sqrt(len(rets)),
            "cum": cumulative(rets), "mdd": max_drawdown(rets),
            "worst": min(rets), "fee": len(rets) * fee}


# ===================================================================== 횡단면
# (2026-09-17 추가) 사용자: "그런 종목들을 뽑고 사고 파는 걸로... 그런 종목들의
# 오르고 내려가고는 시장 전체보다는 예측이 가능하지 않을까?"
#
# 지금까지와 다른 물건이다.
#   지금까지  바스켓 전체를 '언제' 들고 있을까 (시계열). 날짜를 맞히는 문제.
#   이번      저변동 후보들 중 '어느 것' 을 살까 (횡단면). 종목을 고르는 문제.
#
# 횡단면이 통계적으로 유리한 이유: 상위 10 - 하위 10 의 차이를 보면 시장
# 등락이 상쇄된다. 시계열 검정은 회차당 표준편차 4.62% 를 다 뒤집어쓰고
# 있었는데 그 대부분이 시장 변동이었다.
#
# 그리고 대조군이 훨씬 깔끔하다. 회차마다 풀 안에서 신호값만 무작위로 섞으면
# '이 신호로 고르기' 와 '풀에서 아무거나 10개 고르기' 의 차이만 남는다.
# 시장 등락, 그 회차의 좋고 나쁨, 풀 구성은 전부 그대로다.
POOL = 60           # 변동성 낮은 순 상위 몇 종목을 후보 풀로 둘지
PICK = 10
N_PERM = 2000
# 방향은 반기 분할에서 양쪽 모두 같게 나온 값이다 (아래 문서 참고).
XSEC_DIRS = {"기관": -1, "외국인": -1, "개인": +1}


def build_pool_rounds(dates, panel, flow, hold: int = HOLD,
                      pool: int = POOL, verbose: bool = True) -> list:
    """겹치지 않는 회차마다 (날짜, [종목별 레코드]) 를 만든다.

    레코드에는 변동성 순위, 전날 수급 3종(거래대금 정규화), 실현 수익이 들어간다.
    전날까지의 정보만 쓴다.
    """
    dmap = {d: i for i, d in enumerate(dates)}
    out = []
    di = max(140, S.LIQUIDITY_DAYS + 2)
    while di + hold < len(dates):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        vols = [(sc, c) for c in cand
                if (sc := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(vols) < pool:
            di += hold
            continue
        vols.sort(reverse=True)     # low_vol 점수는 -표준편차라 높은 게 저변동
        recs = []
        for rank, (_s, c) in enumerate(vols[:pool]):
            ser = panel.get(c)
            prev = dates[di - 1]
            f = flow.get((prev, c))
            j = ser.pos.get(di - 1) if ser else None
            if f is None or j is None or not ser.value[j]:
                continue
            r, _cut = S.trade_return(panel, c, di, di + hold)
            if r is None:
                continue
            v = ser.value[j]
            recs.append({"code": c, "volrank": rank, "ret": r,
                         "기관": f[0] / v, "외국인": f[1] / v,
                         "개인": f[2] / v})
        if len(recs) >= 2 * PICK:
            out.append((dates[di], recs))
        di += hold
    if verbose:
        print(f"겹치지 않는 회차 {len(out)}개, 회차당 풀 평균 "
              f"{st.mean([len(r) for _d, r in out]):.0f}종목")
    return out


def _top_ret(recs, keyfn, pick: int = PICK) -> float:
    xs = sorted(recs, key=keyfn)
    return st.mean([r["ret"] for r in xs[:pick]]) - S.FEE_ROUND_TRIP_PCT


def select_by(which: str):
    """수급 지표로 고르는 정렬 키. XSEC_DIRS 의 방향을 따른다."""
    d = XSEC_DIRS[which]
    return lambda r: -d * r[which]


def select_by_volrank(r):
    """현재 전략: 변동성이 낮은 순서."""
    return r["volrank"]


def cross_section(rounds, n_perm: int = N_PERM, seed=SEED,
                  verbose: bool = True) -> dict:
    """풀에서 10종목을 고르는 방법들을 비교하고, 신호를 섞은 대조군과 댄다."""
    rng = np.random.default_rng(seed)
    base = [_top_ret(recs, select_by_volrank) for _d, recs in rounds]
    out = {"n": len(rounds), "base": _summary(base), "cands": {}}

    for which in XSEC_DIRS:
        real = [_top_ret(recs, select_by(which)) for _d, recs in rounds]
        real_m = st.mean(real)
        perm = []
        for _ in range(n_perm):
            tot = 0.0
            for _d, recs in rounds:
                order = rng.permutation(len(recs))
                sh = [{**r, which: recs[order[i]][which]}
                      for i, r in enumerate(recs)]
                tot += _top_ret(sh, select_by(which))
            perm.append(tot / len(rounds))
        perm.sort()
        out["cands"][which] = {
            **_summary(real),
            "vs_base": real_m - out["base"]["mean"],
            "perm_med": perm[len(perm) // 2],
            "perm_p05": perm[int(len(perm) * 0.05)],
            "perm_p95": perm[int(len(perm) * 0.95)],
            "beat": sum(1 for p in perm if p >= real_m) / len(perm),
        }
    # 반기 분할도 같이 낸다 - 대조군 통과와는 별개의 증거다
    half = len(rounds) // 2
    out["halves"] = {}
    for which in XSEC_DIRS:
        h = []
        for part in (rounds[:half], rounds[half:]):
            b = st.mean([_top_ret(r, select_by_volrank) for _d, r in part])
            s = st.mean([_top_ret(r, select_by(which)) for _d, r in part])
            h.append((s, b, s - b))
        out["halves"][which] = h
    if verbose:
        _report_xsec(out)
    return out


def _summary(xs) -> dict:
    m = st.mean(xs)
    se = st.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0
    return {"n": len(xs), "mean": m, "se": se,
            "win": sum(1 for x in xs if x > 0) / len(xs),
            "cum": cumulative(xs), "mdd": max_drawdown(xs)}


def _report_xsec(o: dict) -> None:
    b = o["base"]
    print(f"\n{'='*94}")
    print(f"=== 횡단면: 저변동 풀 {POOL}종목 중 {PICK}개를 어떻게 고를까 "
          f"({o['n']}회차) ===")
    print(f"{'='*94}")
    print(f"  {'선택 방법':<22} {'평균':>8} {'표준오차':>8} {'승률':>6} "
          f"{'누적':>9} {'MDD':>8} {'기준대비':>9}")
    print(f"  {'변동성 낮은 순 (현재)':<22} {b['mean']:>+8.3f} {b['se']:>8.3f} "
          f"{b['win']*100:>5.0f}% {b['cum']:>+9.1f} {b['mdd']:>+8.1f}")
    for which, c in o["cands"].items():
        arrow = "높은쪽" if XSEC_DIRS[which] > 0 else "낮은쪽"
        print(f"  {which + ' ' + arrow:<22} {c['mean']:>+8.3f} {c['se']:>8.3f} "
              f"{c['win']*100:>5.0f}% {c['cum']:>+9.1f} {c['mdd']:>+8.1f} "
              f"{c['vs_base']:>+9.3f}")
    print(f"\n  [대조군] 회차마다 풀 안에서 신호값만 무작위로 섞기 "
          f"({N_PERM}번)")
    for which, c in o["cands"].items():
        print(f"    {which:<8} 실제 {c['mean']:+.3f}%  무작위 중간값 "
              f"{c['perm_med']:+.3f}%  5~95% [{c['perm_p05']:+.3f} ~ "
              f"{c['perm_p95']:+.3f}]")
        print(f"    {'':<8} 무작위가 실제보다 좋았던 비율 {c['beat']*100:.1f}%"
              + ("   <- 탈락" if c["beat"] > 0.05 else "   <- 통과"))
    print(f"\n  [반기 분할] 대조군과 별개의 증거. 양쪽 모두 양수여야 한다")
    for which, h in o["halves"].items():
        print(f"    {which:<8} 전반부 {h[0][0]:+.3f} vs 기준 {h[0][1]:+.3f} "
              f"({h[0][2]:+.3f})   후반부 {h[1][0]:+.3f} vs 기준 "
              f"{h[1][1]:+.3f} ({h[1][2]:+.3f})")
    print(CAUTION_XSEC)


CAUTION_XSEC = """
[결과를 볼 때]
  - 선택 방법을 여러 개 보면 하나는 걸린다. 몇 개를 봤는지 세고, 통과한
    것의 우연 비율에 그 개수를 곱해서 읽을 것 (7가지를 봤다면 2.0% 는
    보정 후 14% 쯤이다).
  - 대조군 통과와 반기 분할은 서로 다른 증거다. 둘 다 봐야 한다. 대조군은
    '풀에서 아무거나 고르는 것보다 나은가', 반기 분할은 '다음 구간에서도
    남는가' 를 본다.
  - 최대낙폭을 현재 전략과 비교할 것. 수익이 늘어도 낙폭이 깊어지면 '큰
    손해를 피한다' 는 목적에는 기여하지 못한 것이다.
  - 개인 순매수는 산술적으로 기관/외국인/기타법인 순매수의 거울상이다.
    '개인이 샀다' 와 '기관이 팔았다' 는 거의 같은 말이므로 독립된 증거
    두 개로 세면 안 된다.
  - 62회차가 전부다. 표준오차가 0.6~0.8%p 이므로 기준대비 +0.4%p 는
    표준오차 한 개 안에 있다.
"""


def analyze(mode: str = "entry", n_shift: int = N_SHIFT,
            verbose: bool = True) -> dict:
    import analyze_timing as T

    dates, panel = S.load_panel(verbose=verbose)
    picks = T.build_picks(dates, panel, verbose)
    dmap = {d: i for i, d in enumerate(dates)}
    codes = {c for ps in picks.values() for c in ps}
    flow = load_flow(codes)
    if verbose:
        print(f"종목 {len(codes)}개, 수급 {len(flow):,}건")

    def ret_fn(a, b):
        return T.trade_return(panel, picks.get(a) or [], a, b, dmap)

    out = {"n_codes": len(codes), "n_flow": len(flow), "signals": {}}
    for name, fn in SIGNALS.items():
        sig = build_signal(dates, panel, picks, flow, fn)
        usable = sorted(sig)
        if len(usable) < 200:
            continue
        half = len(usable) // 2
        res = {}
        for dirname, fit, test in (
                ("forward", usable[:half], usable[half:]),
                ("reverse", usable[half:], usable[:half])):
            fv = sorted(v for d in fit if (v := sig.get(d)) is not None)

            def q(p):
                return fv[min(int(len(fv) * p), len(fv) - 1)]

            base, i = [], dmap[test[0]]
            end = dmap[test[-1]]
            while i + HOLD <= end:
                r = ret_fn(dates[i], dates[i + HOLD])
                if r is not None:
                    base.append(r)
                i += HOLD
            d = {"fit_span": (fit[0], fit[-1]), "test_span": (test[0], test[-1]),
                 "base": _stat(base, "기준선 20일 고정")}

            bad = entry_only(test, sig, q(ENTRY_Q), ret_fn)
            good = entry_only(test, sig, q(1 - ENTRY_Q), ret_fn, invert=True)
            d["entry_bad"] = _stat(bad, "나쁜날에만 진입")
            d["entry_good"] = _stat(good, "좋은날에만 진입")
            if d["entry_bad"] and n_shift:
                d["entry_shift"] = shift_control(
                    test, sig,
                    lambda sh: (cumulative(entry_only(test, sh, q(ENTRY_Q),
                                                      ret_fn))
                                if len(entry_only(test, sh, q(ENTRY_Q),
                                                  ret_fn)) >= 5 else None),
                    d["entry_bad"]["cum"], n_shift)

            if mode == "both":
                tds = both_sides(test, sig, q(LOW_Q), q(HIGH_Q), ret_fn)
                if len(tds) >= 5:
                    hs = [t[2] for t in tds]
                    s = _stat([t[3] for t in tds], "나쁜날매수+좋은날매도")
                    s.update({"hold": st.mean(hs), "hold_med": st.median(hs),
                              "hold_min": min(hs), "hold_max": max(hs),
                              "inmkt": sum(hs) / len(test) * 100})
                    d["both"] = s
            res[dirname] = d
        out["signals"][name] = res

    if verbose:
        _report(out, mode)
    return out


def _fmt(s) -> str:
    if not s:
        return "    표본 부족"
    base = (f"    {s['label']:<20} {s['n']:>3}회 평균 {s['mean']:+6.3f}% "
            f"(±{s['se']:.3f}) 누적 {s['cum']:+7.1f}% MDD {s['mdd']:+6.1f}% "
            f"최악 {s['worst']:+6.2f}% 수수료 {s['fee']:4.1f}%")
    if "hold" in s:
        base += (f"\n{'':<24} 보유 평균 {s['hold']:.1f}일 "
                 f"중간 {s['hold_med']:.1f}일 [{s['hold_min']}~{s['hold_max']}] "
                 f"시장체류 {s['inmkt']:.0f}%")
    return base


def _report(o: dict, mode: str) -> None:
    for name, res in o["signals"].items():
        print(f"\n{'='*82}")
        print(f"=== 신호: {name}  (전날 순매수 / 전날 거래대금, 10종목 평균) ===")
        print(f"{'='*82}")
        for dirname, label in (("forward", "정방향: 전반부기준 -> 후반부채점"),
                               ("reverse", "역방향: 후반부기준 -> 전반부채점")):
            d = res.get(dirname)
            if not d:
                continue
            print(f"\n  {label}  ({d['test_span'][0]}~{d['test_span'][1]})")
            for key in ("base", "entry_bad", "entry_good"):
                print(_fmt(d.get(key)))
            sh = d.get("entry_shift")
            if sh:
                print(f"    [대조군] 신호 밀어놓기 {sh['n']}번: 중간값 "
                      f"{sh['med']:+.1f}%  5~95% [{sh['p05']:+.1f}% ~ "
                      f"{sh['p95']:+.1f}%]")
                print(f"      실제 {d['entry_bad']['cum']:+.1f}% 보다 좋은 우연 "
                      f"{sh['beat']*100:.1f}%"
                      + ("   <- 탈락" if sh["beat"] > 0.05 else "   <- 통과"))
            if mode == "both" and d.get("both"):
                print(_fmt(d["both"]))
    print(CAUTION)


CAUTION = """
[결과를 볼 때]
  - 신호 4개 x 방식 2개 x 방향 2개를 보면 16번 가까운 검사다. 우연히 5%
    미만이 나올 기대값이 0.8개다. 하나 통과한 것을 '찾았다' 로 읽으면 안 된다.
  - 반기당 거래가 30회 안팎이다. 거래당 표준오차가 ±0.9%p 이므로, 기준선과의
    차이가 1%p 이내면 표준오차 한 개 안에 있다.
  - 진입만 신호로 정하고 보유를 고정해야 수수료 조건이 같아진다. 청산까지
    신호로 정하면 보유가 4~5일로 짧아지고 거래가 두 배로 늘어, 신호가 나빠서
    진 것인지 수수료로 진 것인지 구별할 수 없다.
  - 최대낙폭을 기준선과 비교할 것. 수익이 늘어도 낙폭이 깊어지면 '큰 손해를
    피한다' 는 목적에는 실패다.
  - 상승장에서는 시장에 덜 머무는 것 자체가 손해다. 채점 구간이 상승장이었는지
    기준선 수익으로 확인할 것.
  - 전날 수급은 장 마감 후 확정되므로 그날 시가에 쓸 수 있다. 같은 날 수급을
    쓰면 미래 정보가 된다 - build_signal 은 반드시 dates[i-1] 을 본다.
"""


def main() -> int:
    p = argparse.ArgumentParser(description="종목별 수급으로 진입 시점 정하기")
    p.add_argument("--mode", choices=("entry", "both", "xsec"),
                   default="entry",
                   help="entry: 진입만 신호(기본) / both: 매수·매도 둘 다 / "
                        "xsec: 저변동 풀 안에서 종목 고르기 (횡단면)")
    p.add_argument("--no-shift", action="store_true", help="대조군 생략")
    a = p.parse_args()
    if a.mode == "xsec":
        import analyze_timing as T
        dates, panel = S.load_panel()
        picks = T.build_picks(dates, panel)
        codes = {c for ps in picks.values() for c in ps}
        # 풀은 200종목에서 뽑으므로 유니버스 전체의 수급이 필요하다
        wide = set()
        for di in range(max(140, S.LIQUIDITY_DAYS + 2), len(dates), HOLD):
            wide |= set(S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE))
        flow = load_flow(wide | codes)
        print(f"종목 {len(wide | codes)}개, 수급 {len(flow):,}건")
        rounds = build_pool_rounds(dates, panel, flow)
        cross_section(rounds, n_perm=0 if a.no_shift else N_PERM)
    else:
        analyze(mode=a.mode, n_shift=0 if a.no_shift else N_SHIFT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
