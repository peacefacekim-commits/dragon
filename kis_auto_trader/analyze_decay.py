"""효과가 시간이 지나면서 닳고 있나 - 무엇이 변하고 무엇이 안 변하나.

(2026-09-18 신설) 사용자: "시간을 늘려도 시간이 지나가면서 투자 방향이
변하는 게 있을테니 그것도 완벽하진 않을거야"

맞는 지적이고 이미 흔적이 있었다. 저변동 전략의 시장 대비 초과분이
  2021 +1.30%p  2022 +2.76%p  2023 +0.92%p
  2024 +4.11%p  2025 +0.37%p  2026 -0.21%p
최근 2년이 가장 낮다. 우연인지 닳는 건지 재본다.

===========================================================================
결과 1 - 1년 이동창 초과분 추이: 변한다. 다만 추세가 아니라 주기다
===========================================================================

  창 끝        저변동     시장    초과분   저변동-고변동  금융주개수
  2022-06    -1.198  -4.270  +3.072      +4.918     2.0
  2022-12    -0.418  -3.097  +2.679      +7.908     1.5
  2023-06    -0.050  +0.747  -0.797      +2.386     1.2   <- 마이너스
  2023-09    +0.459  +0.715  -0.256      +3.953     1.4   <- 마이너스
  2024-03    +2.154  -0.816  +2.970     +11.683     2.0   <- 회복
  2024-11    +1.799  -2.005  +3.804      +9.965     1.5   <- 최고
  2025-05    +2.659  -0.984  +3.643     +10.645     1.9
  2025-11    +2.898  +3.007  -0.109      +5.469     1.9   <- 마이너스
  2026-02    +3.507  +5.630  -2.123      +2.364     2.2   <- 최저
  2026-05    +1.890  +3.795  -1.906      +0.911     2.8

  추세선 기울기 t = -1.37.  닳는다고 말하려면 -2 보다 작아야 한다.
  단정할 수 없다. 그리고 2023년에도 두 창이 마이너스였다가 돌아왔다.
  단조 감소가 아니라 오르내림이다.

===========================================================================
결과 2 - 핵심: 저변동 효과 자체는 안 닳았다
===========================================================================
변동성 낮은 10종목 - 변동성 높은 10종목 (같은 유니버스 안에서)

  2021 +0.213   2022 +7.908   2023 +4.576
  2024 +9.373   2025 +4.253   2026 +5.924

  6년 전부 양수이고 2026년이 +5.924 로 2021·2023·2025 보다 높다.
  닳는 기미가 없다.

  그렇다면 시장 대비 초과분이 왜 마이너스가 됐나. **시장이 올랐기
  때문이다.** 2025-11 창은 시장 +3.007, 2026-02 창은 시장 +5.630 이다.
  저변동은 오르는 장에서 뒤처진다 - 이건 결함이 아니라 설계된 성질이다.
  덜 빠지는 대가로 덜 오른다.

===========================================================================
결과 3 - 금융주(밸류업) 때문인가: 부분적으로만
===========================================================================
  연도   저변동10   금융주 뺀   차이   금융주 개수
  2021   -1.268    -2.278  +1.010      2.5
  2022   -0.418    -0.427  +0.009      1.5
  2023   +0.784    +0.881  -0.098      1.5
  2024   +1.608    +0.972  +0.636      1.6
  2025   +3.132    +2.438  +0.693      1.8
  2026   +1.440    +0.499  +0.942      4.4

  금융주를 빼도 2024~2025 가 여전히 +0.972, +2.438 이다. 금융주가 도움은
  됐지만(연 +0.6~0.9%p) 주된 원인은 아니다. 다만 2026년은 바스켓의 4.4개가
  금융주이고 빼면 +0.499 로 뚝 떨어진다 - 최근으로 올수록 금융주 의존이
  커지고 있다. 이건 지켜볼 것.

===========================================================================
결과 4 - 같은 전략이 사실 다른 것을 사고 있었다
===========================================================================
  2021  KT&G  삼성전자  현대차  삼성전자우  신한지주
  2023  SK텔레콤  KT  KT&G  삼성물산  삼성전자우
  2026  KT&G  우리금융  삼성바이오  KB금융  하나금융  HMM

  2021~2022 에 뽑힌 32개 / 2025~2026 에 뽑힌 40개, 겹치는 것 23개 (47%)

  절반이 바뀌었다. 삼성전자·현대차가 빠지고 금융주가 들어왔다. 규칙은
  같은데 사는 물건이 달라졌다. 이게 사용자가 말한 '투자 방향이 변한다' 의
  구체적인 모습이다.

===========================================================================
읽는 법
===========================================================================
  1) 사용자 지적이 맞다. 초과분은 +3.8%p 에서 -2.1%p 까지 오간다.
     더 긴 데이터가 주는 것은 '확신' 이 아니라 **흔들리는 범위** 다.
  2) 그런데 변하는 것은 '시장 대비 우위' 이고, 안 변하는 것은 '저변동
     효과' 다. 둘을 구별해야 한다.
  3) 시장 대비 우위가 마이너스가 되는 때는 **시장이 오를 때** 다. 그건
     이 전략이 고장난 게 아니라 원래 그런 것이다 (덜 빠지는 대가로 덜 오름).
  4) 그러므로 '요즘 안 통한다' 와 '효과가 죽었다' 는 다르다. 구별하려면
     저변동-고변동 차이를 보면 된다. 그게 죽으면 진짜 끝난 것이다.
  5) 종목은 절반 바뀌었다. 규칙을 고정해도 사는 물건은 달라진다 - 그게
     이 전략이 시대 변화를 따라가는 방식이기도 하다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_decay.py
"""
import math
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다. 사용자 PC(윈도우)에는 /home/user/... 가 없다.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import strategy as S  # noqa: E402

HOLD, PICK, POOL = 20, 10, 60
FEE = S.FEE_ROUND_TRIP_PCT

dates, panel = S.load_panel()
N = len(dates)
START = max(140, S.LIQUIDITY_DAYS + 2)

# 금융주 (밸류업 수혜 의심 대상). 코드로 직접 지정한다 - 업종 데이터가 없다.
FIN = {"316140", "055550", "105560", "086790", "138040", "138930",
       "024110", "029780", "139130", "138040", "071050", "006800",
       "003540", "001450", "000810", "032830", "088350"}

rounds = []
di = START
while di + HOLD < N:
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    sc = [(x, c) for c in cand
          if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
    if len(sc) < POOL:
        di += HOLD
        continue
    sc.sort(reverse=True)
    low = [c for _s, c in sc[:PICK]]
    high = [c for _s, c in sc[-PICK:]]
    pool = [c for _s, c in sc[:POOL]]

    def avg(codes):
        rs = []
        for c in codes:
            r, _cut = S.trade_return(panel, c, di, di + HOLD)
            if r is not None:
                rs.append(r)
        return st.mean(rs) - FEE if rs else None

    r_low, r_high = avg(low), avg(high)
    r_all = avg(cand)
    if r_low is None or r_all is None or r_high is None:
        di += HOLD
        continue
    # 금융주 비중과 금융주 뺀 수익
    nfin = sum(1 for c in low if c in FIN)
    nonfin = [c for c in low if c not in FIN]
    r_nonfin = avg(nonfin) if len(nonfin) >= 3 else None
    rounds.append({"date": dates[di], "low": r_low, "high": r_high,
                   "all": r_all, "excess": r_low - r_all,
                   "lowhigh": r_low - r_high, "nfin": nfin,
                   "nonfin": r_nonfin, "picks": low})
    di += HOLD

print(f"회차 {len(rounds)}개 ({rounds[0]['date']} ~ {rounds[-1]['date']})\n")

# ---------------------------------------- 1) 1년 이동창 초과분 추이
print("=" * 88)
print("=== 1) 1년 이동창(12회차) 초과분 추이 - 닳고 있나 ===")
print("=" * 88)
W = 12
xs, ys = [], []
print(f"  {'창 끝':<10} {'저변동':>9} {'시장':>9} {'초과분':>9} "
      f"{'저변동-고변동':>13} {'금융주 개수':>11}")
for i in range(W, len(rounds) + 1, 3):
    seg = rounds[i - W:i]
    ex = st.mean([r["excess"] for r in seg])
    lh = st.mean([r["lowhigh"] for r in seg])
    print(f"  {seg[-1]['date']:<10} {st.mean([r['low'] for r in seg]):>+9.3f} "
          f"{st.mean([r['all'] for r in seg]):>+9.3f} {ex:>+9.3f} "
          f"{lh:>+13.3f} {st.mean([r['nfin'] for r in seg]):>11.1f}")
    xs.append(i)
    ys.append(ex)

if len(xs) >= 4:
    mx, my = st.mean(xs), st.mean(ys)
    varx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / varx if varx else 0
    resid = [y - (my + slope * (x - mx)) for x, y in zip(xs, ys)]
    se = (math.sqrt(sum(r * r for r in resid) / (len(xs) - 2) / varx)
          if len(xs) > 2 and varx else 0)
    print(f"\n  추세선 기울기 {slope*100:+.4f}%p / 창 100개당  "
          f"(표준오차 {se*100:.4f}) t={slope/se if se else 0:+.2f}")
    print("  " + ("-> 닳고 있다고 말하려면 t 가 -2 보다 작아야 한다"
                  if slope < 0 else "-> 기울기가 양수다. 닳는 증거가 아니다"))

# ---------------------------------------- 2) 금융주 의존도
print("\n" + "=" * 88)
print("=== 2) 초과분이 금융주에서 나왔나 (밸류업은 한 번뿐인 사건이다) ===")
print("=" * 88)
print(f"  {'연도':<6} {'회차':>4} {'저변동10':>9} {'금융주 뺀':>10} {'차이':>8} "
      f"{'금융주 개수':>11} {'시장':>9}")
for y in ("2021", "2022", "2023", "2024", "2025", "2026"):
    seg = [r for r in rounds if r["date"].startswith(y)]
    if len(seg) < 3:
        continue
    nf = [r["nonfin"] for r in seg if r["nonfin"] is not None]
    print(f"  {y:<6} {len(seg):>4} {st.mean([r['low'] for r in seg]):>+9.3f} "
          f"{(st.mean(nf) if nf else float('nan')):>+10.3f} "
          f"{(st.mean([r['low'] for r in seg]) - st.mean(nf)) if nf else 0:>+8.3f} "
          f"{st.mean([r['nfin'] for r in seg]):>11.1f} "
          f"{st.mean([r['all'] for r in seg]):>+9.3f}")

# ---------------------------------------- 3) 저변동 효과 자체
print("\n" + "=" * 88)
print("=== 3) 저변동 효과 자체 (변동성 낮은 10 - 높은 10) ===")
print("=" * 88)
print(f"  {'연도':<6} {'저변동10':>10} {'고변동10':>10} {'차이':>10}")
for y in ("2021", "2022", "2023", "2024", "2025", "2026"):
    seg = [r for r in rounds if r["date"].startswith(y)]
    if len(seg) < 3:
        continue
    print(f"  {y:<6} {st.mean([r['low'] for r in seg]):>+10.3f} "
          f"{st.mean([r['high'] for r in seg]):>+10.3f} "
          f"{st.mean([r['lowhigh'] for r in seg]):>+10.3f}")

# ---------------------------------------- 4) 뽑히는 종목이 바뀌었나
print("\n" + "=" * 88)
print("=== 4) 뽑히는 종목이 시간에 따라 바뀌었나 ===")
print("=== (많이 바뀌었으면 '같은 전략'이 사실은 다른 것을 사고 있었다) ===")
print("=" * 88)
for y in ("2021", "2022", "2023", "2024", "2025", "2026"):
    seg = [r for r in rounds if r["date"].startswith(y)]
    if not seg:
        continue
    freq = {}
    for r in seg:
        for c in r["picks"]:
            freq[c] = freq.get(c, 0) + 1
    tops = sorted(freq.items(), key=lambda kv: -kv[1])[:6]
    print(f"  {y}  " + "  ".join(f"{c}({n})" for c, n in tops))

first = set()
last = set()
for r in rounds:
    if r["date"].startswith("2021") or r["date"].startswith("2022"):
        first.update(r["picks"])
    if r["date"].startswith("2025") or r["date"].startswith("2026"):
        last.update(r["picks"])
print(f"\n  2021~2022 에 뽑힌 종목 {len(first)}개 / "
      f"2025~2026 에 뽑힌 종목 {len(last)}개")
print(f"  겹치는 종목 {len(first & last)}개 "
      f"({len(first & last)/len(first|last)*100:.0f}%)")
