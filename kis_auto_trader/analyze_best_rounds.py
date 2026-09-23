"""잘된 회차의 전날 데이터 공통점 - 모을 수 있는 모든 지표로.

(2026-09-18 신설) 사용자: "한달마다 거래를 하는데 최대한 이득을 보는 데이터를
수집하고 사고 팔때 그 전날의 데이터가 어땠는지 공통점을 찾아줘 코스피 코스닥
지수는 얼마 외국인의 방향 기관의 방향등등 그러한 지표들이 하나로 겹치는
지점이 있을 거 같거든" + "우리가 수집할 수 있는 모든 지표를 사용해줘 거래량의
변화나 환율 미국 주식장까지"

먼저 짚어둘 것: 이 방식은 착각이 가장 잘 생긴다. 54회차에서 상위 10개를
골라 지표 25개를 보면 공통점은 **반드시** 나온다. 상위 10개는 그냥 운이
좋았던 10개일 수도 있고 그 10개도 뭔가 공통점을 갖고 있다.

그래서 판정은 상위/하위 비교가 아니라 **전반부 상위의 특징을 후반부 상위도
공유하는가** 로 한다.

지표 25개 (전부 진입일 전날까지 확정)
  지수 수준    지수/20·60·250일평균, 52주고점대비
  시장 흐름    5일·20일수익, 상승종목비율, 20일변동성
  거래량       시장 거래대금 5/60, 미국(^GSPC) 거래량 5/60
  수급         외국인·기관 전날/5일/20일누적, 개인 전날/5일누적
  해외         S&P500, 나스닥, 다우, 반도체, VIX 수준, VIX 변화
  환율         달러/원

  지수는 유니버스 200종목 동일가중 누적지수 대용이다. 실제 코스피/코스닥
  5년치 지수 파일이 없고, 코스닥 단독은 낼 수 없다. 절대 숫자(6846)는
  예측에 의미가 없고 '최근 대비 어디쯤인가' 가 중요하므로 이 형태가 맞다.

  뺀 것: 미국 선물(한국장 시간) - 2024-09 부터라 회차가 절반으로 줄어든다.
        배당수익률/PER/PBR - krx_fund 가 1,813종목 중 30개만 수집돼 있다
        (코드 앞순서 30개라 저변동 10종목과 거의 안 겹친다). 저변동 전략에
        가장 관련 있을 지표인데 지금은 못 쓴다. 채우려면
        fetch_krx_extra.py --what fundamental (약 6시간).

===========================================================================
결과 1 - 상위 10회차(평균 +8.79%) vs 하위 10회차(평균 -4.43%)
===========================================================================
잡음배수 = (상위-하위) / 무작위 10회차 평균의 표준편차. 2 를 넘는 것만.

  기관전날      -22.85 vs  +23.69   잡음배수 -3.15   <- 가장 큼
  다우           +0.95 vs   -0.39            +2.74
  S&P500        +1.06 vs   -0.48            +2.71
  나스닥          +1.25 vs   -0.57            +2.52
  개인전날      +12.88 vs  -21.78            +2.10
  기관5일누적   -28.61 vs  +41.66            -2.04
  VIX변화       -4.91 vs   +0.92            -2.01

  거래량 변화는 둘 다 잡음배수가 낮았다 (시장 +0.33, 미국 +1.10).
  지수 수준도 낮았다 (/250일 +0.47, /60일 -0.32, /20일 -0.28).

===========================================================================
결과 2 - 판정: 전반부 상위의 특징을 후반부 상위도 공유하나
===========================================================================

  양쪽 같은 방향 9개 (전반부 차이 / 후반부 차이)
    외국인5일누적  +18.21 / +57.25
    기관전날       -21.09 / -28.51   <- 가장 안정적
    VIX변화         -1.57 /  -2.98
    VIX수준         +0.40 /  +0.64
    반도체          +0.97 /  +0.40
    다우            +0.56 /  +0.40
    S&P500         +0.53 /  +0.35
    나스닥           +0.66 /  +0.34
    달러/원          -0.28 /  -0.09

  뒤집힌 것 16개 - 여기에 사용자가 명시한 것들이 들어 있다
    지수/250일평균  -6.01 /  +6.07   전반부는 지수가 낮을 때, 후반부는 높을 때
    지수/60일평균   -5.46 /  +4.65
    52주고점대비    -4.06 /  +5.01
    시장 거래대금   -0.08 /  +0.15
    미국 거래량     -0.02 /  +0.03
    개인전날        -0.89 / +21.12   상위/하위 표에서는 +2.10 이었는데 뒤집힘
    외국인전날     +23.16 /  -0.61
    시장 흐름 4개 전부 X

  부호 일치 9/25 - 우연(12.5)보다 **낮다**.

===========================================================================
결과 3 - 겹치는 지점을 규칙으로 만들면  (아래 run_intersection)
===========================================================================
양쪽에서 살아남은 셋(기관 낮음 + S&P500 높음 + VIX변화 낮음)을 AND 로 걸고
분위 30/40/50% 로 검정했다. 대조군은 같은 개수만큼 무작위 회차 2000번.

  정방향 (전반부 기준 -> 후반부 채점, 전부 투자 +1.867%)
    기관+S&P500+VIX변화  30%   3회 +11.771%  우연 0.1%  통과
    기관+S&P500          30%   3회 +11.771%  우연 0.2%  통과
    기관 단독            30%  10회  +4.253%  우연 3.8%  통과
  역방향 (후반부 기준 -> 전반부 채점, 전부 투자 +0.317%)
    기관+S&P500+VIX변화  30%   3회  +0.053%  우연 49.4%  탈락
    기관+S&P500          30%   5회  +0.988%  우연 31.7%  탈락
    기관 단독            40%  12회  +2.343%  우연 1.2%   통과
    기관 단독            50%  12회  +2.343%  우연 1.1%   통과

읽는 법

  1) 겹치는 지점은 있다. "전날 기관이 팔았고, 미국이 올랐고, VIX가 내렸고,
     외국인이 5일간 사고 있었고, 원화가 강했던 날" 이다. 이야기로도 말이 된다.
  2) 그런데 부호 일치가 9/25 로 우연보다 낮다. 즉 상위 10회차 표의
     **대부분은 그 구간의 사정** 이고, 살아남은 9개만 봐야 한다.
  3) 살아남은 9개도 실질 항목은 4~5개다. 미국 4개(다우/S&P/나스닥/반도체)는
     사실상 하나, VIX 2개도 하나다.
  4) AND 규칙은 정방향에서 +11.771%(우연 0.1%) 로 화려하지만 **발동이
     3회차** 다. 역방향에서는 같은 3회차가 +0.053%(우연 49.4%) 다. 적게
     발동하는 규칙이 크게 나오는 것은 발견이 아니라 표본이 작다는 신호다.
  5) 양방향에서 살아남는 것은 **기관 단독 하나** 다 (정방향 3.8%, 역방향
     1.1~1.2%). 이 프로젝트 전체에서 계속 나온 그것이고, 새로 찾은 게 아니다.
  6) 사용자가 명시한 것 중 지수 수준과 거래량 변화는 앞뒤가 정반대였다.
     "코스피가 얼마일 때 사야 하나" 는 전반부와 후반부가 반대 답을 준다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_best_rounds.py                # 공통점 프로파일
    python analyze_best_rounds.py --what rule    # 겹치는 지점을 규칙으로
"""
import pathlib as _pathlib
# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = str(_pathlib.Path(__file__).resolve().parent)
import argparse
import sys as _sys


def run_profile():
    import csv
    import glob
    import math
    import statistics as st
    import sys

    import numpy as np

    sys.path.insert(0, _ROOT)
    import strategy as S  # noqa: E402

    HOLD, PICK, TOPN = 20, 10, 10
    FEE = S.FEE_ROUND_TRIP_PCT
    N_PERM = 2000
    rng = np.random.default_rng(20260929)

    dates, panel = S.load_panel()
    N = len(dates)
    START = max(140, S.LIQUIDITY_DAYS + 2)
    dpos = {d: i for i, d in enumerate(dates)}

    # ------------------------------------------------------------ 시장 지표
    raw = {}
    for path in sorted(glob.glob(f"{_ROOT}/data/market_indicators_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                raw[r["date"]] = r
    md = sorted(raw)
    mdpos = {d: i for i, d in enumerate(md)}


    def g(d, key):
        try:
            return float(raw[d][key])
        except (TypeError, ValueError, KeyError):
            return None


    idx, v = {}, 100.0
    for d in md:
        c = g(d, "result_c2c")
        if c is not None:
            v *= (1 + c / 100)
        idx[d] = v

    # ------------------------------------------------- 미국 지수 거래량 (^GSPC)
    us_vol = {}
    for path in sorted(glob.glob(f"{_ROOT}/data/us_market_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("ticker") == "^GSPC":
                    try:
                        us_vol[r["date"]] = float(r["volume"])
                    except (TypeError, ValueError):
                        pass
    us_dates = sorted(us_vol)
    us_pos = {d: i for i, d in enumerate(us_dates)}

    # ------------------------------------------------- 종목별 재무 (PER/PBR/배당)
    fund = {}
    for path in sorted(glob.glob(f"{_ROOT}/data/krx_fund_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    fund[(r["date"], r["code"])] = (
                        float(r["div"]), float(r["per"]), float(r["pbr"]))
                except (TypeError, ValueError):
                    pass
    print(f"재무 데이터 {len(fund):,}건, 미국 거래량 {len(us_vol):,}일")

    # ------------------------------------ 유니버스 전체 거래대금 (시장 거래량 대용)
    mkt_value = {}
    for di in range(len(dates)):
        d = dates[di]
        tot = 0.0
        for s in panel.values():
            j = s.pos.get(di)
            if j is not None:
                tot += s.value[j]
        mkt_value[d] = tot
    print("시장 거래대금 계산 완료")


    def signals(entry_date, picks):
        i = mdpos.get(entry_date)
        di = dpos.get(entry_date)
        if i is None or di is None or i < 255 or di < 61:
            return None
        p = md[i - 1]
        out = {}

        lv = idx[p]
        for w, label in ((20, "지수/20일평균"), (60, "지수/60일평균"),
                         (250, "지수/250일평균")):
            ma = st.mean([idx[md[k]] for k in range(i - 1 - w, i)])
            out[label] = (lv / ma - 1) * 100 if ma else 0.0
        hi = max(idx[md[k]] for k in range(i - 251, i))
        out["52주고점대비"] = (lv / hi - 1) * 100 if hi else 0.0
        out["시장5일수익"] = (lv / idx[md[i - 6]] - 1) * 100
        out["시장20일수익"] = (lv / idx[md[i - 21]] - 1) * 100
        out["상승종목비율"] = g(p, "kr_breadth5")
        out["시장변동성"] = g(p, "kr_vol20")

        # 시장 거래대금 변화 (5일 / 60일)
        v5 = st.mean([mkt_value[dates[k]] for k in range(di - 5, di)])
        v60 = st.mean([mkt_value[dates[k]] for k in range(di - 60, di)])
        out["시장거래대금 5/60"] = v5 / v60 if v60 else 1.0

        for key, label in (("flow_foreign", "외국인"), ("flow_inst", "기관"),
                           ("flow_indiv", "개인")):
            out[f"{label}전날"] = g(p, key)
            for w in (5, 20):
                if label == "개인" and w == 20:
                    continue
                xs = [g(md[k], key) for k in range(i - w, i)]
                xs = [x for x in xs if x is not None]
                out[f"{label}{w}일누적"] = sum(xs) if xs else None

        for key, label in (("us_sp500", "S&P500"), ("us_nasdaq", "나스닥"),
                           ("us_dow", "다우"), ("us_sox", "반도체"),
                           ("us_vix_level", "VIX수준"), ("us_vix_chg", "VIX변화"),
                           ("fx_krw", "달러/원")):
            out[label] = g(p, key)

        # 미국 거래량 변화
        up = us_pos.get(p)
        if up is None or up < 60:
            cands = [k for k in us_dates if k <= p]
            up = us_pos.get(cands[-1]) if cands else None
        if up is None or up < 60:
            return None
        u5 = st.mean([us_vol[us_dates[k]] for k in range(up - 5, up)])
        u60 = st.mean([us_vol[us_dates[k]] for k in range(up - 60, up)])
        out["미국거래량 5/60"] = u5 / u60 if u60 else 1.0

        # 바스켓 재무(배당수익률/PER/PBR)는 뺐다. krx_fund 가 1,813종목 중 30개만
        # 수집돼 있고(코드 앞순서 30개) 저변동 10종목과 거의 겹치지 않는다.
        # fetch_krx_extra.py --what fundamental 로 채우면 쓸 수 있다 (약 6시간).

        if any(x is None for x in out.values()):
            return None
        return out


    def picks_and_ret(di):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(sc) < PICK:
            return None, None
        sc.sort(reverse=True)
        picks = [c for _s, c in sc[:PICK]]
        rs = []
        for c in picks:
            r, _cut = S.trade_return(panel, c, di, di + HOLD)
            if r is not None:
                rs.append(r)
        return picks, (st.mean(rs) - FEE if rs else None)


    rounds = []
    di = START
    while di + HOLD < N:
        d = dates[di]
        picks, r = picks_and_ret(di)
        sg = signals(d, picks) if picks else None
        if sg and r is not None:
            rounds.append((d, r, sg))
        di += HOLD

    KEYS = list(rounds[0][2])
    rets = [r for _d, r, _s in rounds]
    print(f"\n회차 {len(rounds)}개 ({rounds[0][0]} ~ {rounds[-1][0]}), "
          f"지표 {len(KEYS)}개")
    print(f"회차 수익 평균 {st.mean(rets):+.2f}%  최고 {max(rets):+.2f}%  "
          f"최악 {min(rets):+.2f}%")

    srt = sorted(rounds, key=lambda t: -t[1])
    top, bot = srt[:TOPN], srt[-TOPN:]

    noise = {}
    for k in KEYS:
        vals = [s[k] for _d, _r, s in rounds]
        ms = [st.mean([vals[i] for i in
                       rng.choice(len(vals), size=TOPN, replace=False)])
              for _ in range(N_PERM)]
        noise[k] = st.pstdev(ms) or 1.0

    print("\n" + "=" * 100)
    print(f"=== 상위 {TOPN}회차(평균 {st.mean([t[1] for t in top]):+.2f}%) vs "
          f"하위 {TOPN}회차(평균 {st.mean([t[1] for t in bot]):+.2f}%) ===")
    print("=== 잡음배수 2 를 넘어야 눈여겨볼 값. 지표가 많으니 몇 개는 "
          "우연히 넘는다 ===")
    print("=" * 100)
    print(f"  {'지표':<18} {'상위10':>11} {'하위10':>11} {'전체':>11} {'잡음배수':>9}")
    prof = []
    for k in KEYS:
        a = st.mean([s[k] for _d, _r, s in top])
        b = st.mean([s[k] for _d, _r, s in bot])
        allm = st.mean([s[k] for _d, _r, s in rounds])
        prof.append((k, a, b, allm, (a - b) / (noise[k] * math.sqrt(2))))
    for k, a, b, allm, z in sorted(prof, key=lambda t: -abs(t[4])):
        print(f"  {k:<18} {a:>11.2f} {b:>11.2f} {allm:>11.2f} {z:>+9.2f}")

    print("\n" + "=" * 100)
    print("=== 판정: 전반부 상위의 특징을 후반부 상위도 공유하나 ===")
    print("=" * 100)
    half = len(rounds) // 2
    A, B = rounds[:half], rounds[half:]
    ta = sorted(A, key=lambda t: -t[1])[:5]
    tb = sorted(B, key=lambda t: -t[1])[:5]
    print(f"  전반부 상위 5 평균 {st.mean([t[1] for t in ta]):+.2f}% / "
          f"후반부 상위 5 평균 {st.mean([t[1] for t in tb]):+.2f}%")
    print(f"\n  {'지표':<18} {'전반부 차이':>12} {'후반부 차이':>12} {'부호':>5}")
    rows = []
    for k in KEYS:
        da = st.mean([s[k] for _d, _r, s in ta]) - st.mean([s[k] for _d, _r, s in A])
        db = st.mean([s[k] for _d, _r, s in tb]) - st.mean([s[k] for _d, _r, s in B])
        rows.append((k, da, db, (da > 0) == (db > 0)))
    for k, da, db, ok in sorted(rows, key=lambda t: (not t[3], -abs(t[2]))):
        print(f"  {k:<18} {da:>+12.2f} {db:>+12.2f} {'O' if ok else 'X':>5}")
    same = sum(1 for _k, _a, _b, ok in rows if ok)
    print(f"\n  부호 일치 {same}/{len(KEYS)}개 (우연이면 {len(KEYS)/2:.1f}개)")
    print("\n  양쪽에서 같은 방향인 지표만:")
    for k, da, db, ok in sorted([r for r in rows if r[3]], key=lambda t: -abs(t[2])):
        print(f"    {k:<18} 전반부 {da:>+9.2f}  후반부 {db:>+9.2f}")


def run_intersection():
    import csv
    import glob
    import itertools
    import math
    import statistics as st
    import sys

    import numpy as np

    sys.path.insert(0, _ROOT)
    import strategy as S  # noqa: E402

    HOLD, PICK = 20, 10
    FEE = S.FEE_ROUND_TRIP_PCT
    N_PERM = 2000
    rng = np.random.default_rng(20260928)

    dates, panel = S.load_panel()
    N = len(dates)
    START = max(140, S.LIQUIDITY_DAYS + 2)

    raw = {}
    for path in sorted(glob.glob(f"{_ROOT}/data/market_indicators_*.csv")):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                raw[r["date"]] = r
    md = sorted(raw)
    mdpos = {d: i for i, d in enumerate(md)}


    def g(d, key):
        try:
            return float(raw[d][key])
        except (TypeError, ValueError, KeyError):
            return None


    COND = {"기관": ("flow_inst", -1), "S&P500": ("us_sp500", +1),
            "VIX변화": ("us_vix_chg", -1)}


    def sigs(entry_date):
        i = mdpos.get(entry_date)
        if i is None or i < 2:
            return None
        p = md[i - 1]
        out = {}
        for label, (key, _d) in COND.items():
            v = g(p, key)
            if v is None:
                return None
            out[label] = v
        return out


    def round_ret(di):
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        sc = [(x, c) for c in cand
              if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
        if len(sc) < PICK:
            return None
        sc.sort(reverse=True)
        rs = []
        for _s, c in sc[:PICK]:
            r, _cut = S.trade_return(panel, c, di, di + HOLD)
            if r is not None:
                rs.append(r)
        return st.mean(rs) - FEE if rs else None


    rounds = []
    di = START
    while di + HOLD < N:
        d = dates[di]
        sg = sigs(d)
        r = round_ret(di) if sg else None
        if sg and r is not None:
            rounds.append((d, r, sg))
        di += HOLD

    print(f"회차 {len(rounds)}개 ({rounds[0][0]} ~ {rounds[-1][0]})")
    half = len(rounds) // 2


    def fire(part, cuts, keys):
        out = []
        for d, r, s in part:
            ok = True
            for k in keys:
                _key, direction = COND[k]
                if direction < 0 and s[k] > cuts[k]:
                    ok = False
                if direction > 0 and s[k] < cuts[k]:
                    ok = False
            if ok:
                out.append((d, r))
        return out


    def summary(xs):
        if len(xs) < 3:
            return None
        m = st.mean(xs)
        return m, (st.stdev(xs) / math.sqrt(len(xs)) if len(xs) > 1 else 0.0)


    for label, A, B in (("정방향", rounds[:half], rounds[half:]),
                        ("역방향", rounds[half:], rounds[:half])):
        print("\n" + "=" * 92)
        print(f"=== {label}: 기준을 {A[0][0]}~{A[-1][0]} 에서 정하고 "
              f"{B[0][0]}~{B[-1][0]} 에서 채점 ===")
        print("=" * 92)
        base = [r for _d, r, _s in B]
        print(f"  전부 투자: {len(base)}회 평균 {st.mean(base):+.3f}% "
              f"(±{st.stdev(base)/math.sqrt(len(base)):.3f})")
        print(f"\n  {'조건':<26} {'분위':>5} {'발동':>5} {'평균':>9} "
              f"{'표준오차':>8} {'전부대비':>9} | {'우연':>7}")
        for q in (0.3, 0.4, 0.5):
            cuts = {}
            for k, (key, direction) in COND.items():
                vals = sorted(s[k] for _d, _r, s in A)
                p = q if direction < 0 else (1 - q)
                cuts[k] = vals[min(int(len(vals) * p), len(vals) - 1)]
            for r_ in range(1, 4):
                for keys in itertools.combinations(COND, r_):
                    got = fire(B, cuts, keys)
                    s_ = summary([r for _d, r in got])
                    if s_ is None:
                        continue
                    # 대조군: 같은 개수만큼 무작위 회차
                    perm = []
                    for _ in range(N_PERM):
                        idxs = rng.choice(len(base), size=len(got), replace=False)
                        perm.append(st.mean([base[i] for i in idxs]))
                    perm.sort()
                    beat = sum(1 for x in perm if x >= s_[0]) / len(perm)
                    print(f"  {'+'.join(keys):<26} {int(q*100):>4}% "
                          f"{len(got):>5} {s_[0]:>+9.3f} {s_[1]:>8.3f} "
                          f"{s_[0]-st.mean(base):>+9.3f} | {beat*100:>6.1f}%"
                          + ("  탈락" if beat > 0.05 else "  통과"))


def main() -> int:
    p = argparse.ArgumentParser(description="잘된 회차의 전날 공통점")
    p.add_argument("--what", choices=("profile", "rule", "both"),
                   default="profile")
    a_ = p.parse_args()
    if a_.what in ("profile", "both"):
        run_profile()
    if a_.what in ("rule", "both"):
        run_intersection()
    return 0


if __name__ == "__main__":
    _sys.exit(main())
