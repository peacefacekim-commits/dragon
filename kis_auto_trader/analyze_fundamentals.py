"""배당수익률 / PER / PBR 을 선정 신호로 쓸 수 있나. (PER/PBR 이 조건을 넘었다)

(2026-09-19 신설) 사용자: "1번 데이터 수집하자"

왜 이것만 남았나
  가격과 거래량에서 유도한 신호는 전부 막혔다. 그리고 손잡이 24가지를
  훑어도 바꿀 것이 없었다 (analyze_knobs.py). 엣지가 나온 유일한 차원이
  **선정**인데, 선정 차원에서 아직 안 써본 재료가 재무지표뿐이다.
  가격에서 유도할 수 없는 정보라는 점이 중요하다 - 지금까지 막힌 이유가
  매번 "지표들이 서로 같은 정보를 담고 있어서" 였다.

===========================================================================
미리 못 박는 것 - 데이터를 보기 전에 쓴다
===========================================================================
이 파일은 **데이터가 도착하기 전에** 작성했다. 결과를 보고 나서 기준을
정하면 어떤 잡음이든 통과시킬 수 있기 때문이다. 실제로 이 저장소에서
그렇게 속을 뻔한 적이 여러 번 있었고, 한 번은 내 선행참조 버그가 만든
결과가 반띵 검증까지 통과했다 (analyze_recycle.py).

시험할 것은 **여섯 가지뿐이다.** 늘리지 않는다.

  신호 3개   배당수익률 높은 순 / PER 낮은 순 / PBR 낮은 순
  방식 2개   그 신호만으로 고르기 / 저변동과 순위 평균해서 고르기
  = 6가지 (기준선 1개 별도)

채택 조건 (셋 다 넘어야 한다)
  1) 시작일 5개 중 4개 이상에서 기준선을 이긴다
  2) 반띵 양방향 모두에서 기준선을 이긴다
  3) 무작위 대조군을 넘는다 (같은 풀에서 10종목을 아무렇게나 고른 것)

하나라도 걸리면 넣지 않는다. 그리고 "아깝다" 며 조건을 고치지 않는다.

미리 정해두는 처리 방식
  적자 기업(PER <= 0)   PER 순위에서 뺀다. 적자면 PER 이 뜻을 잃는다.
                        빼는 것 자체가 선택이므로 밝혀둔다.
  무배당(DIV = 0)       뺀다고 하지 않는다. 배당이 0 인 것도 정보다.
  PBR <= 0              뺀다 (자본잠식). PER 과 같은 이유다.
  값이 없는 날          그 종목은 그 회차에서 제외한다. 앞의 값을 끌어다
                        쓰지 않는다 - 그러면 없는 정보를 만들어내게 된다.
  미래 정보             di - 1 까지만 본다. 가격 신호와 같은 규칙이다.

===========================================================================
결과 (2026-09-21, 재무 1,780종목 / 1,401일 도착 후)
===========================================================================
  신호   방식          연수익%   낙폭%   시작일
  기준(저변동)          22.3    -15.9     -
  div   alone         16.6    -22.9    0/5
  div   with_lowvol   19.0    -18.9    2/5
  per   alone         15.2    -37.4    1/5
  per   with_lowvol   26.4    -20.0    4/5
  pbr   alone         18.1    -39.2    2/5
  pbr   with_lowvol   29.7    -18.9    5/5

**재무지표를 단독으로 쓰면 여섯 중 여섯이 진다.** 낙폭도 -22.9 ~ -39.2
로 크게 나빠진다. 저변동과 섞었을 때만 올라간다. 즉 재무는 저변동을
대체하지 않고 보완한다.

조건 1 을 넘은 둘을 조건 2, 3 으로 보냈다.

  반띵 (신호 / 기준)
    per+저변동   전반 10.7 / 7.9    후반 31.3 / 16.9   양쪽 이김
    pbr+저변동   전반 11.7 / 7.9    후반 33.6 / 16.9   양쪽 이김

  무작위 대조군 500회 (같은 풀에서 10종목을 아무렇게나)
    per+저변동   관측 26.4   p = 0.0020
    pbr+저변동   관측 29.7   p = 0.0020

**둘 다 미리 정한 세 조건을 전부 넘었다.** 이 저장소에서 사전 등록한
기준을 통과한 것은 이번이 처음이다.

===========================================================================
통과했으므로 오히려 더 깐깐하게 본 것들
===========================================================================
(1) 생존편향이 다시 들어왔나 - 아니다
    재무 데이터가 현재 상장 종목만이라면, 재무값이 있는 종목만 고르는
    순간 폐지 종목이 조용히 빠진다. 확인했다.
      살아있는 종목  1,615 / 1,641 (98%) 에 재무 있음
      폐지된 종목      165 /   172 (96%) 에 재무 있음
    거의 같다. 폐지 종목이 빠지지 않았다.

(2) 버는 것이 '순위' 인가 '필터' 인가 - 순위다
    PER/PBR 은 적자·자본잠식을 빼는 **필터** 와 낮은 순으로 고르는
    **순위** 를 동시에 한다. 필터만 걸고 순위는 저변동으로만 매겨봤다.
                                 연수익%   시작일
      기준 (필터 없음)             22.3      -
      per 필터만                  17.1     1/5
      per 필터+순위                26.4     4/5
      pbr 필터만                  19.5     2/5
      pbr 필터+순위                29.7     5/5
    **필터만 쓰면 오히려 진다.** 이득은 순위에서 온다. '적자 기업을
    빼서 벌었을 뿐' 이라는 설명이 깨진다.

(3) 미래 정보 - fund_score 는 di-1 까지만 읽는다. 가격 신호와 같다.

===========================================================================
해마다 쪼개니 무너진다 - 세 조건이 서로 독립이 아니었다
===========================================================================
사용자: "수익 7.4%에 낙폭 3%면 충분히 감안할 만한 리스크인거 같은데?"

그 계산은 맞다 (수익/낙폭 1.40 -> 1.57). 그런데 **+7.4%p 라는 전제가
틀렸다.** 해마다 쪼개면 이렇다.

  해     기준    per+저변동    pbr+저변동     (기준 대비 %p)
  2022   -7.1      -0.7         +1.7
  2023   18.5      -6.5         -8.4
  2024   16.9      +6.0         +8.3
  2025   60.4      -1.8        +41.3
  2026   43.0      +1.1        -15.8

  per+저변동   양수인 해 2/5   최고 해를 빼면 나머지 평균 -2.0%p
  pbr+저변동   양수인 해 3/5   최고 해를 빼면 나머지 평균 -3.6%p

**pbr 의 이득은 2025년 한 해가 전부다.** 그 해를 빼면 기준보다 나쁘다.
per 은 26.4% 라는 중앙값이 무색하게 2/5 해만 양수다.

비교 - 저변동 자체는 6/6 해 양수였다 (analyze_decay.py)
  2021 +0.213  2022 +7.908  2023 +4.576
  2024 +9.373  2025 +4.253  2026 +5.924
저변동은 매년 벌고 PBR 은 한 해에 몰아 벌었다. 성격이 다르다.

왜 세 조건이 이걸 못 걸렀나 - **서로 독립이 아니어서다.**
  시작일 5개   37일 간격이라 다섯 개가 전부 2025년을 통과한다
  반띵         후반부가 2025년을 통째로 품는다
  대조군       전 구간을 한 덩어리로 본다
같은 2025년을 세 방향에서 본 것이지 독립된 세 증거가 아니었다.
이건 내 사전 등록의 설계 실수다. analyze_flow 에서 '개인 순매수는
기관/외국인의 거울상' 이라며 같은 지적을 해놓고 여기서 똑같이 했다.

앞으로 어떤 신호든 **연도별 지속성** 을 채택 조건에 넣는다.

===========================================================================
그런데 채택 조건에 빠진 것이 있었다 - 낙폭
===========================================================================
  기준(저변동)   연 22.3%   낙폭 -15.9%
  pbr+저변동    연 29.7%   낙폭 -18.9%
  per+저변동    연 26.4%   낙폭 -20.0%

수익이 +7.4%p 오르는 대신 낙폭이 3.0%p 나빠진다. **이건 맞교환이다.**
저변동 선정이 고변동을 이길 때는 수익도 낙폭도 둘 다 좋았다
(analyze_styles.py). 여기는 다르다.

내가 미리 정한 세 조건에 낙폭이 없었다. 이건 내 사전 등록의 구멍이다.
결과를 보고 나서 조건을 추가해 탈락시키면 그건 조건을 고치는 것이고,
그러지 않기로 한 규칙을 스스로 어기는 것이다. 그래서 **판정은 '통과'
로 둔다.**

다만 켜지 않는다. 낙폭 때문이 아니라 위의 연도별 때문이다. 이 둘을
구별하는 것이 중요하다.
  낙폭 조건을 뒤늦게 추가   -> 골대 옮기기다. 안 한다.
  연도별 지속성을 확인      -> 저변동이 이미 통과한 기존 기준이다
                              (analyze_decay.py 6/6). 같은 자를 새
                              후보에 대는 것은 골대 옮기기가 아니다.

즉 안 켜는 이유는 "낙폭 3%p 가 아까워서" 가 아니라 **"+7.4%p 가 애초에
없어서"** 다. 한 해짜리다.

===========================================================================
읽는 법
===========================================================================
1) 이득이 후반부에 크다 (후반 33.6 vs 16.9, 전반 11.7 vs 7.9). 양쪽에서
   이기므로 조건은 넘지만, 크기는 시기에 따라 많이 다르다. 연도별로
   쪼개면 그 '시기' 가 2025년 한 해라는 것이 드러난다.
1b) 2024년 2월에 정부의 밸류업 프로그램이 저PBR 종목을 직접 겨냥했다.
   2024~2025 에 이득이 몰린 것과 시기가 겹친다. 이것이 원인이라고
   증명한 것은 아니다 - 다만 '가격에서 유도되지 않는 새 정보' 가
   아니라 '한 시기의 정책' 일 수 있다는 뜻이고, 그렇다면 앞으로
   되풀이된다고 볼 근거가 없다.
2) 다중검정: 사전 등록한 6가지다. p=0.0020 이므로 6으로 보정해도
   0.012 로 유의하다. 다만 '사전 등록' 은 이 파일 안에서만의 이야기고,
   저장소 전체로는 80가지 넘게 훑었다.
3) 2021~2026 한국 시장이다. PBR 이 낮은 종목이 이긴 시기였을 수 있다.
4) 아직 strategy.py 에 넣지 않았다. 켜려면 plan_2m.py 까지 손대야 하고,
   그 전에 위의 맞교환을 결정해야 한다.

실행:
  python analyze_fundamentals.py           # 데이터가 얼마나 있는지부터 본다
  python analyze_fundamentals.py --run     # 여섯 가지 + 반띵 + 대조군
"""
import argparse
import csv
import glob
import pathlib
import random
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import strategy as S  # noqa: E402

CAPITAL = E.CAPITAL
DAYS_PER_YEAR = 246
BASE_DI = 250
PICK = 10
N_STARTS, START_GAP = 5, 37
PERIOD = 120
N_PERM = 500
SEED = 20260919

# 미리 정한 여섯 가지. 늘리지 않는다.
SIGNALS = ("div", "per", "pbr")
MODES = ("alone", "with_lowvol")

# 채택 조건
MIN_START_WINS = 4          # 시작일 5개 중
PERM_ALPHA = 0.05


def load_fund(dates):
    """krx_fund_*.csv 를 {(di, code): {per, pbr, div}} 로 읽는다."""
    dpos = {d: i for i, d in enumerate(dates)}
    out = {}
    for path in sorted(glob.glob(str(_ROOT / "data" / "krx_fund_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                di = dpos.get(r["date"])
                if di is None:
                    continue
                rec = {}
                for k in ("per", "pbr", "div"):
                    try:
                        rec[k] = float(r[k])
                    except (KeyError, TypeError, ValueError):
                        rec[k] = None
                out[(di, r["code"])] = rec
    return out


def coverage(fund, dates):
    """몇 종목 / 몇 날짜가 모였나. 돌리기 전에 확인하는 용도."""
    codes = {c for (_di, c) in fund}
    dis = {di for (di, _c) in fund}
    return {"codes": len(codes), "days": len(dis),
            "last": dates[max(dis)] if dis else None}


def fund_score(fund, code, di, signal):
    """di 일 시가에 살 종목을 고르기 위한 재무 점수. di-1 까지만 본다.

    높을수록 좋은 값으로 맞춘다 (저변동 점수와 방향을 같게 하려고).
      배당    높을수록 좋다 -> 그대로
      PER     낮을수록 좋다 -> 부호를 뒤집는다. 적자(<=0)는 제외.
      PBR     낮을수록 좋다 -> 부호를 뒤집는다. 자본잠식(<=0)은 제외.
    """
    rec = fund.get((di - 1, code))
    if rec is None:
        return None
    v = rec.get(signal)
    if v is None:
        return None
    if signal == "div":
        return v
    if v <= 0:
        return None      # 적자 / 자본잠식 - 이 지표가 뜻을 잃는다
    return -v


def rank_map(pairs):
    """[(점수, 종목)] -> {종목: 등수}. 점수가 높을수록 1등."""
    ordered = sorted(pairs, reverse=True)
    return {c: i for i, (_s, c) in enumerate(ordered)}


def picks_at(panel, fund, di, signal, mode):
    """그 시점에 살 PICK 종목. 못 고르면 None."""
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    fs = [(x, c) for c in cand
          if (x := fund_score(fund, c, di, signal)) is not None]
    if len(fs) < PICK:
        return None
    if mode == "alone":
        fs.sort(reverse=True)
        return [c for _s, c in fs[:PICK]]

    # 저변동과 순위를 평균한다. 값의 단위가 다르므로 등수로 맞춘다.
    vs = [(x, c) for c in cand
          if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
    if len(vs) < PICK:
        return None
    fr, vr = rank_map(fs), rank_map(vs)
    both = [c for c in fr if c in vr]
    if len(both) < PICK:
        return None
    both.sort(key=lambda c: (fr[c] + vr[c]) / 2)
    return both[:PICK]


def run(dates, panel, fund, signal, mode, start, upto=None, capital=CAPITAL):
    """부분교체. 가격 신호 쪽과 같은 규칙으로 돌린다."""
    n = upto if upto is not None else len(dates)
    cash, hold = float(capital), {}
    curve, di = [], start
    while di < n:
        if (di - start) % PERIOD == 0:
            new = picks_at(panel, fund, di, signal, mode)
            if new:
                keep = {c: q for c, q in hold.items() if c in new}
                for c in [c for c in hold if c not in new]:
                    v = E.price(panel, c, di)
                    if v:
                        cash += hold[c] * v * (1 - E.FEE_ONE_WAY)
                add = [c for c in new if c not in hold]
                got, cash, _f = (E.buy_greedy(panel, cash, add, di) if add
                                 else ({}, cash, 0.0))
                hold = {**keep, **got}
        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve


def mdd(curve):
    peak, worst = curve[0], 0.0
    for v in curve:
        peak = max(peak, v)
        worst = min(worst, v / peak - 1)
    return worst * 100


def annualized(curve, capital=CAPITAL):
    if not curve:
        return 0.0
    return ((curve[-1] / capital) ** (DAYS_PER_YEAR / len(curve)) - 1) * 100


def run_random(dates, panel, start, rng, upto=None, capital=CAPITAL):
    """같은 후보 풀에서 PICK 종목을 아무렇게나 고른다. 대조군.

    신호가 진짜인지 보려면 '아무거나 골랐을 때' 와 견줘야 한다. 후보
    풀도 주기도 부분교체도 수수료도 전부 같게 두고 고르는 방법만 바꾼다.
    """
    n = upto if upto is not None else len(dates)
    cash, hold = float(capital), {}
    curve, di = [], start
    while di < n:
        if (di - start) % PERIOD == 0:
            cand = list(S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE))
            if len(cand) >= PICK:
                new = rng.sample(cand, PICK)
                keep = {c: q for c, q in hold.items() if c in new}
                for c in [c for c in hold if c not in new]:
                    v = E.price(panel, c, di)
                    if v:
                        cash += hold[c] * v * (1 - E.FEE_ONE_WAY)
                add = [c for c in new if c not in hold]
                got, cash, _f = (E.buy_greedy(panel, cash, add, di) if add
                                 else ({}, cash, 0.0))
                hold = {**keep, **got}
        curve.append(cash + sum(q * (E.price(panel, c, di, "close") or 0)
                                for c, q in hold.items()))
        di += 1
    return curve


def control_p(dates, panel, starts, observed, n_perm=N_PERM, seed=SEED):
    """무작위 대조군이 관측값 이상을 낸 비율 -> p 값.

    p = (관측값 이상인 무작위 횟수 + 1) / (전체 + 1)
    +1 은 관측값 자신을 세는 것이고, p 가 0 이 되는 것을 막는다.
    """
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_perm):
        med = st.median(annualized(run_random(dates, panel, s, rng))
                        for s in starts)
        if med >= observed:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def split_half(dates, panel, fund, signal, mode, base_di=BASE_DI):
    """전반부/후반부를 따로 돌려서 (신호, 기준) 쌍 두 개를 돌려준다.

    한 시기에만 통하는 것을 거르는 장치다. 이 저장소에서 여러 번
    여기서 걸렸다.
    """
    half = base_di + (len(dates) - base_di) // 2
    ranks, _ = E.daily_ranks(dates, panel, base_di)
    out = []
    for s, upto in ((base_di, half), (half, None)):
        sig = annualized(run(dates, panel, fund, signal, mode, s, upto=upto))
        ref = annualized(E.run_calendar(dates, panel, ranks, PERIOD, s,
                                        upto=upto)[0])
        out.append((sig, ref))
    return out


def by_year(dates, panel, fund, signal, mode, base_di=BASE_DI, min_days=100):
    """해마다 따로 돌려서 (해, 기준, 신호, 차이) 를 돌려준다.

    왜 필요한가: 시작일 5개는 37일 간격이라 **같은 구간을 겹쳐서 본다.**
    반띵도 절반씩이라 큰 해 하나가 한쪽을 통째로 끌어올릴 수 있다.
    대조군도 전 구간을 한 덩어리로 본다. 즉 미리 정한 세 조건이 서로
    독립이 아니다. 해마다 쪼개야 '한 해가 다 만든 것' 이 보인다.

    저변동 선정은 이 검사를 6/6 으로 통과했다 (analyze_decay.py).
    """
    years = {}
    for i, d in enumerate(dates):
        years.setdefault(d[:4], []).append(i)
    ranks, _ = E.daily_ranks(dates, panel, base_di)
    out = []
    for y in sorted(years):
        idx = years[y]
        lo, hi = max(idx[0], base_di), idx[-1] + 1
        if hi - lo < min_days:
            continue
        ref = annualized(E.run_calendar(dates, panel, ranks, PERIOD, lo,
                                        upto=hi)[0])
        sig = annualized(run(dates, panel, fund, signal, mode, lo, upto=hi))
        out.append((y, ref, sig, sig - ref))
    return out


def one_year_story(diffs):
    """제일 좋은 해를 빼면 뭐가 남나.

    한 해가 전부를 만들었다면 그 해를 빼는 순간 이득이 사라진다.
    (몇 해 양수인가, 최고 해를 뺀 나머지 평균)
    """
    if len(diffs) < 2:
        return (0, 0.0)
    best = max(diffs)
    rest = list(diffs)
    rest.remove(best)
    return (sum(1 for x in diffs if x > 0), st.mean(rest))


def accepted(start_wins, n_starts, first_beats, second_beats, perm_p):
    """채택 조건 세 개를 전부 넘겼나.

    조건을 함수로 박아두는 이유: 결과를 보고 나서 "이 정도면" 하고
    느슨하게 만드는 것을 막기 위해서다. 고치려면 이 함수를 고쳐야 하고,
    그러면 테스트가 걸린다.
    """
    return (start_wins >= MIN_START_WINS
            and first_beats and second_beats
            and perm_p < PERM_ALPHA)


def main():
    ap = argparse.ArgumentParser(description="재무지표를 선정 신호로 쓸 수 있나")
    ap.add_argument("--run", action="store_true",
                    help="여섯 가지를 실제로 돌린다 (데이터가 다 모인 뒤에)")
    args = ap.parse_args()

    dates, panel = S.load_panel()
    fund = load_fund(dates)
    cov = coverage(fund, dates)
    print(f"\n[재무 데이터] {cov['codes']:,}종목 / {cov['days']:,}일 "
          f"/ 마지막 {cov['last']}")

    if cov["codes"] < 500:
        print(f"[!] 종목이 너무 적습니다 ({cov['codes']}종목). 돌려도 뜻이 없습니다.")
        print("    KRX 데이터 수집.bat 로 재무 데이터를 먼저 받으세요.")
        return 1

    if not args.run:
        print("\n--run 을 붙이면 여섯 가지를 돌립니다.")
        return 0

    starts = [BASE_DI + k * START_GAP for k in range(N_STARTS)]
    print(f"\n미리 정한 {len(SIGNALS) * len(MODES)}가지만 돌립니다 (늘리지 않음).")
    print(f"{'신호':<10}{'방식':<14}{'연수익 중앙':>12}{'낙폭':>9}{'기준 이긴 횟수':>14}")

    base = [annualized(E.run_calendar(dates, panel,
                                      E.daily_ranks(dates, panel, BASE_DI)[0],
                                      PERIOD, s)[0]) for s in starts]
    print(f"{'기준(저변동)':<24}{st.median(base):>12.1f}")

    survivors = {}
    for signal in SIGNALS:
        for mode in MODES:
            rs, ds = [], []
            for s in starts:
                c = run(dates, panel, fund, signal, mode, s)
                rs.append(annualized(c))
                ds.append(mdd(c))
            wins = sum(1 for i in range(len(starts)) if rs[i] > base[i])
            survivors[(signal, mode)] = (st.median(rs), wins)
            print(f"{signal:<10}{mode:<14}{st.median(rs):>12.1f}"
                  f"{st.median(ds):>9.1f}{f'{wins}/{len(starts)}':>14}")

    # 조건 1 을 넘긴 것만 조건 2, 3 으로 보낸다 (대조군이 오래 걸린다).
    passed = {k: v for k, v in survivors.items() if v[1] >= MIN_START_WINS}
    if not passed:
        print(f"\n시작일 조건({MIN_START_WINS}/{len(starts)})을 넘은 것이 없다."
              " 여기서 끝. 조건을 고치지 않는다.")
        return 0

    print(f"\n조건 1 통과: {len(passed)}가지. 반띵과 대조군을 돌린다.")
    print(f"\n{'신호':<10}{'방식':<14}{'전반(신호/기준)':>18}"
          f"{'후반(신호/기준)':>18}  반띵")
    halves = {}
    for (signal, mode) in passed:
        h = split_half(dates, panel, fund, signal, mode)
        halves[(signal, mode)] = h
        (s1, r1), (s2, r2) = h
        v = ("양쪽 이김" if s1 > r1 and s2 > r2 else
             "뒤집힘" if (s1 > r1) != (s2 > r2) else "양쪽 짐")
        print(f"{signal:<10}{mode:<14}{f'{s1:.1f} / {r1:.1f}':>18}"
              f"{f'{s2:.1f} / {r2:.1f}':>18}  {v}", flush=True)

    print(f"\n무작위 대조군 {N_PERM}회 (같은 풀에서 10종목을 아무렇게나)")
    print(f"{'신호':<10}{'방식':<14}{'관측':>8}{'p':>9}")
    ps = {}
    for (signal, mode), (med, _w) in passed.items():
        p = control_p(dates, panel, starts, med)
        ps[(signal, mode)] = p
        print(f"{signal:<10}{mode:<14}{med:>8.1f}{p:>9.4f}", flush=True)

    print(f"\n{'신호':<10}{'방식':<14}{'조건1':>7}{'조건2':>9}{'조건3':>9}  판정")
    any_ok = False
    for (signal, mode), (med, wins) in passed.items():
        (s1, r1), (s2, r2) = halves[(signal, mode)]
        ok = accepted(wins, len(starts), s1 > r1, s2 > r2, ps[(signal, mode)])
        any_ok = any_ok or ok
        print(f"{signal:<10}{mode:<14}{f'{wins}/{len(starts)}':>7}"
              f"{'통과' if s1 > r1 and s2 > r2 else '탈락':>9}"
              f"{'통과' if ps[(signal, mode)] < PERM_ALPHA else '탈락':>9}"
              f"  {'채택' if ok else '탈락'}")
    if not any_ok:
        print("\n셋을 다 넘은 것이 없다. 넣지 않는다. 조건을 고치지 않는다.")
        return 0

    # 통과했으면 해마다 쪼개서 본다. 세 조건이 서로 독립이 아니기 때문이다.
    print(f"\n해마다 쪼개면 (기준 대비 %p)")
    print(f"{'해':<7}{'기준':>9}" + "".join(f"{s+'+저변동':>14}" for s, _m in passed))
    per_year = {k: by_year(dates, panel, fund, *k) for k in passed}
    any_key = next(iter(passed))
    for i, (y, ref, _s, _d) in enumerate(per_year[any_key]):
        line = f"{y:<7}{ref:>9.1f}"
        for k in passed:
            line += f"{per_year[k][i][3]:>+14.1f}"
        print(line, flush=True)
    for k in passed:
        diffs = [r[3] for r in per_year[k]]
        pos, rest = one_year_story(diffs)
        print(f"\n  {k[0]}+저변동: 양수인 해 {pos}/{len(diffs)}"
              f"   최고 해를 빼면 나머지 평균 {rest:+.1f}%p")
    print("\n(비교) 저변동 자체는 6/6 해 양수였다 - analyze_decay.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
