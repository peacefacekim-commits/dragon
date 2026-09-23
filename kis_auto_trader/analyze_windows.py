"""정말 무조건 이득인가 - 시작일을 전 기간에 흩뿌려서 다시 잰다.

(2026-09-18 신설) 사용자: "근데 이게 맞나? 이 방식대로면 무조건 다 이득을
볼 수 있는데"

의심이 맞았다. analyze_lowvol.py 의 갈아타기 비교에 결함이 있었다.

  starts = [START0 + k for k in range(20)]
  -> START0 = 142 이므로 시작일이 142~161일째, 즉 2021년 7~8월의 연속된
     20일이다. 전부 끝(2026-09)까지 달린다. 20개가 사실상 **같은 5년 기간
     하나** 였다. 거기서 보고한 범위(+85.7 ~ +162.6%)는 서로 다른 장세가
     아니라 '며칠에 들어갔나' 의 잔차일 뿐이고, 20개가 다 양수였던 것도
     같은 기간을 20번 센 결과다.

제대로 다시 했다. 시작일을 20거래일마다 전 기간에 흩뿌리고 보유 기간을
고정한다 (1년/2년/3년). 그러면 서로 다른 장세가 표본이 된다.

===========================================================================
결과 (2026-09-18). 6개월마다 갈아타기, 저변동 10종목
===========================================================================

  창 길이  창 개수   중간값     최악      최고      손실로 끝남   같은 창 시장
  1년       51    +19.8%  -17.5%  + 64.4%  16/51 (31%)   + 0.2%
  2년       38    +35.5%  -16.9%  +140.9%   6/38 (16%)   - 3.1%
  3년       26    +63.1%  + 4.1%  +156.8%   0/26 ( 0%)   +10.9%

  세 경우 모두 최악 창은 2021-07-26 시작이었다
    1년 전략 -17.5% / 시장 -31.6%
    2년 전략 -16.9% / 시장 -31.4%
    3년 전략  +4.1% / 시장 -40.6%

연도별

  연도      전략     시장(200종목)    차이
  2021    - 9.2%     - 6.9%      - 2.4%p   손실. 시장보다도 나빴다
  2022    - 7.7%     -42.5%      +34.8%p   손실이지만 시장은 폭락
  2023    +10.3%     +12.5%      - 2.2%p   시장보다 나빴다
  2024    +19.4%     -18.2%      +37.6%p
  2025    +57.1%     +55.1%      + 2.0%p   시장이 좋았던 해
  2026    +27.9%     + 6.6%      +21.4%p

읽는 법 - 여기가 요점이다

  1) **무조건 이득이 아니다.** 1년 단위로 들어가면 51개 창 중 16개(31%)가
     손실로 끝났고 최악은 -17.5% 다. 2021~2022 는 2년 연속 손실이었다.
  2) 5년 누적이 좋아 보였던 이유 둘. (a) 앞 테스트가 같은 기간 하나만
     20번 센 것이다. (b) 그 5년 안에 2025년(+57.1%)이 들어 있다. 그런데
     2025년은 시장도 +55.1% 였으므로 **전략의 공로가 아니라 시장이 좋았던
     것** 이다.
  3) 전략이 시장을 크게 이긴 해는 2022(+34.8%p), 2024(+37.6%p),
     2026(+21.4%p) 다. 2022년은 시장이 -42.5% 폭락한 해이고 전략은 -7.7%
     로 덜 잃었다. **이 전략이 하는 일은 돈을 버는 것이 아니라 시장이
     무너질 때 덜 잃는 것이다.**
  4) 반대로 시장이 평범하게 오른 해(2021, 2023)에는 시장보다 나빴다
     (-2.4%p, -2.2%p). 덜 빠지는 대가로 덜 오른다.
  5) 3년 창에서 손실이 0개인 것을 '3년 들고 있으면 안전' 으로 읽으면 안
     된다. 창이 26개뿐이고 서로 거의 다 겹친다. 사실상 독립 표본 2개다.
     그리고 그 26개 창 전부가 2022년 폭락과 2025년 급등을 함께 포함한다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_windows.py
"""
import pathlib as _pathlib
# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = str(_pathlib.Path(__file__).resolve().parent)
import statistics as st
import sys

sys.path.insert(0, _ROOT)
import strategy as S  # noqa: E402

FEE = S.FEE_ROUND_TRIP_PCT
PICK = 10

dates, panel = S.load_panel()
N = len(dates)
START0 = max(140, S.LIQUIDITY_DAYS + 2)


def picks_at(di):
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    sc = [(v, c) for c in cand
          if (v := S.factor_score(panel, c, di, "low_vol")) is not None]
    if len(sc) < PICK:
        return []
    sc.sort(reverse=True)
    return [c for _s, c in sc[:PICK]]


def seg_mult(codes, i0, i1):
    """i0 시가 -> i1 시가 배수. 끊긴 종목은 마지막 종가로 얼린다."""
    rs = []
    for c in codes:
        s = panel.get(c)
        if s is None:
            continue
        a = s.pos.get(i0)
        if a is None or not s.open[a]:
            continue
        b = s.pos.get(i1)
        end = s.open[b] if b is not None else s.close[-1]
        rs.append(end / s.open[a])
    return st.mean(rs) if rs else None


def run(i0, i1, period):
    """period 거래일마다 갈아타며 i0 -> i1. 수수료는 구간마다 한 번."""
    eq, i = 1.0, i0
    while i < i1:
        j = min(i + period, i1)
        codes = picks_at(i)
        if codes:
            m = seg_mult(codes, i, j)
            if m is not None:
                eq *= m * (1 - FEE / 100)
        i = j
    return (eq - 1) * 100


def market(i0, i1, period=120):
    """기준선: 유니버스 200종목 동일가중, 같은 주기로 갈아탐."""
    eq, i = 1.0, i0
    while i < i1:
        j = min(i + period, i1)
        codes = S.universe_at(panel, i, S.UNIVERSE_SIZE, S.MIN_PRICE)
        if codes:
            m = seg_mult(codes, i, j)
            if m is not None:
                eq *= m * (1 - FEE / 100)
        i = j
    return (eq - 1) * 100


print("=" * 92)
print("=== 보유 기간을 고정하고 시작일을 전 기간에 흩뿌린다 (6개월마다 갈아타기) ===")
print("=== 서로 다른 장세가 표본이 된다. 손실로 끝난 창이 있는지가 핵심 ===")
print("=" * 92)
print(f"  {'창 길이':<8} {'창 개수':>6} {'중간값':>9} {'최악':>9} {'최고':>9} "
      f"{'손실로 끝남':>12} | {'같은 창 시장':>12}")

for label, W in (("1년", 250), ("2년", 500), ("3년", 750)):
    outs, mks = [], []
    i0 = START0
    while i0 + W <= N - 1:
        r = run(i0, i0 + W, 120)
        m = market(i0, i0 + W, 120)
        outs.append((dates[i0], r, m))
        i0 += 20
    if not outs:
        continue
    rs = sorted(x[1] for x in outs)
    ms = sorted(x[2] for x in outs)
    neg = sum(1 for x in rs if x < 0)
    print(f"  {label:<8} {len(outs):>6} {rs[len(rs)//2]:>+8.1f}% "
          f"{rs[0]:>+8.1f}% {rs[-1]:>+8.1f}% "
          f"{neg:>6}/{len(rs):<5} | {ms[len(ms)//2]:>+11.1f}%")
    # 최악 창이 언제였는지
    worst = min(outs, key=lambda x: x[1])
    print(f"           최악 창: {worst[0]} 시작, 전략 {worst[1]:+.1f}% / "
          f"시장 {worst[2]:+.1f}%")

print("\n" + "=" * 92)
print("=== 연도별 (6개월마다 갈아타기). 이 5년이 특별한 기간이었나 ===")
print("=" * 92)
print(f"  {'연도':<6} {'전략':>10} {'시장(200종목)':>14} {'차이':>10}")
for y in ("2021", "2022", "2023", "2024", "2025", "2026"):
    lo = next((i for i, d in enumerate(dates) if d >= y + "0101"), None)
    hi = next((i for i, d in enumerate(dates) if d >= str(int(y) + 1) + "0101"),
              N - 1)
    lo = max(lo or 0, START0)
    if lo >= hi:
        continue
    r, m = run(lo, hi, 120), market(lo, hi, 120)
    print(f"  {y:<6} {r:>+9.1f}% {m:>+13.1f}% {r - m:>+9.1f}%p")
