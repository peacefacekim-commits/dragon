"""모든 지표가 한 방향을 볼 때 투자하기 - 합의(consensus) 검사.

(2026-09-18 신설) 사용자: "뉴스/환율/외국인/개인거래/기관/코스피/코스닥/
미국지수/금리 등등 모든 지표들이 일직선 그러니까 하나의 경향을 보일 때
투자를 하는 식으로 해보면 어떨까"

이건 전에 한 AND 조합 찾기(analyze_skip_rules.py)와 다른 검사다. 거기서는
조합 11,830개를 뒤져서 제일 좋은 걸 골랐다 - 그래서 다중검정 문제가 생겼다.
여기서는 **고르는 게 없다**. 지표 전부에 미리 방향을 박아놓고 몇 개가 같은
방향인지만 센다. 그래서 미리 정한 검사가 하나뿐이다.

방향은 교과서 통념대로 결과를 보기 전에 정했다.
  위험회피(나쁜 쪽) = 미국지수 하락, VIX 상승/높음, 원화 약세,
  변동성 높음, 상승종목 적음, 시장 5일 하락, 외국인/기관 순매도,
  개인 순매수

쓴 지표 14개 (거래량 포함). 사용자가 든 것 중 빠진 것과 이유
  금리   지금 데이터에 없다. 이번에 fetch_us_market.py 에 ^TNX 를
         추가해뒀지만 과거분을 받아야 쓸 수 있다 (사용자 PC 에서
         python fetch_us_market.py --backfill 후 market_indicators
         --backfill). 이 분석에는 안 들어갔다.
  뉴스   과거 기록이 없어 백테스트 불가 (analyze_news_ceiling.py 참고)
  코스닥 5년치 지수 파일이 없어 200종목 유니버스 대용으로만 들어갔다

===========================================================================
결과 0 - 물은 그대로: 다 좋은 날과 다 나쁜 날의 '오를 확률'
===========================================================================
사용자: "다 좋은 다음날과 다 나쁜 상황에 투자했을 때 주식이 오를 확률이
지표로는 구분 할 수 없다는 거야?"

평균 수익이 아니라 오를 확률로 직접 답한다. 전체 평균은 53.4% 다.

  (A) 평소보다 좋은가/나쁜가 - 과거 250일 중앙값 기준
    좋은 쪽        나쁜 쪽      좋은날승률  나쁜날승률    차이     z    판정
    전부 좋음(11일) 전부 나쁨(8일)  54.5%    50.0%   +4.5%p  +0.20  구분 안 됨
    2개 이하(78일)  12개 이상(78일) 44.9%    46.2%   -1.3%p  -0.16  구분 안 됨
    4개 이하(245일) 10개 이상(233일)49.4%    51.9%   -2.5%p  -0.56  구분 안 됨

  (B) 진짜 좋은가/나쁜가 - 상·하위 20% 꼬리 기준
    전부 좋음 175일 / **전부 나쁨 0일**
    4개 이하(822일) 10개 이상(12일) 53.3%    58.3%   -5.0%p  -0.35  구분 안 됨

  두 가지가 다 구분 안 되는데, 이유가 서로 다르다.

  (A) 는 차이 자체가 없다. 그리고 표본이 큰 쪽으로 갈수록 차이가
      **음수** 로 간다 (다 나쁜 날이 오히려 조금 나았다). 물론 z 가
      작아서 그 음수도 의미 없다.

  (B) 는 **해당하는 날이 없다**. 14개 지표가 전부 하위 20% 꼬리에 드는
      날은 4.2년 동안 0일이었다. 지표를 엄격하게 조이면 '전부 나쁜 날'
      은 정의상 거의 존재하지 않는다.

  이게 두 번째 문제다. 조건을 AND 로 묶을수록 해당일이 급격히 줄어서
  **확인할 표본도 없고 투자할 기회도 없다.**

    구간             일수(4.2년)  연간   승률 10%p 차이 확인에
    전부 좋음(A)          11      2.6일      151년
    전부 나쁨(A)           8      1.9일      207년
    12개 이상 나쁨(A)     78     18.4일       21년
    전부 나쁨(B)           0      0.0일    해당일 없음

  승률 차이 10%p 를 확인하려면 한쪽에 392일이 필요하다. 5%p 면 1,568일,
  2%p 면 9,800일이다. '전부 일치' 같은 극단은 연 2일밖에 안 나오므로
  **150~200년을 모아야** 답이 나온다. 이건 데이터를 더 모아서 풀 수
  있는 문제가 아니다.

===========================================================================
결과 1 - 가장 중요한 것: 지표 14개는 사실 6.3개다
===========================================================================
상관행렬 고유값으로 실질 독립 개수를 재면 **약 6.3개**다 (거래량 포함).

  상관 0.7 넘는 짝
    us_sp500    us_nasdaq   +0.959
    us_sp500    us_dow      +0.914
    us_sp500    us_sox      +0.803
    us_sp500    us_vix_chg  +0.756
    us_nasdaq   us_dow      +0.794
    us_nasdaq   us_sox      +0.856
    us_nasdaq   us_vix_chg  +0.715
    us_dow      us_vix_chg  +0.714
    kr_breadth5 kr_ret5     +0.865

  미국지수 4개와 VIX변화는 사실상 한 덩어리다. 상승종목비율과 시장
  5일수익도 한 덩어리다.

  **이게 이 아이디어의 첫 번째 문제다.** "14개가 다 같은 방향이다" 는
  압도적인 증거처럼 들리지만, 실제로는 '위험선호' 라는 한 가지를 14가지
  방법으로 잰 것이다. 전부 일치했을 때 알게 되는 건 14개가 아니라
  사실 하나다. 거래량을 넣어 13개에서 14개로 늘렸을 때 실질 개수는
  5.7 에서 6.3 으로 0.6 만 올랐다. 금리를 넣어도 비슷할 것이다.

===========================================================================
결과 2 - 합의는 다음날 수익을 예측하지 못한다
===========================================================================
1일 앞은 겹치지 않아 표본 1,041개다. 검정력이 충분하다.

  앞 기간   표본    유효표본    상관    표준오차     t      판정
  1일      1041     1041    +0.002    0.031   +0.06    없음
  5일      1037      207    +0.024    0.070   +0.35    없음
  20일     1023       51    +0.051    0.143   +0.36    없음

미리 정한 단 하나의 검사 (버킷 고르기 없음):
  합의 개수 -> 다음날 수익 기울기 +0.00068%p/지표, t = +0.06

  기울기가 이 값이면 '전부 일치' 와 '0개 일치' 의 차이가 +0.0088%p 다.
  하루 변동이 보통 1.18% 인 것에 비하면 없는 것과 같다.

개수별로 쪼개 보면 추세가 아니라 흩어짐이다.
   일치 개수   일수   다음날 평균   전체대비      t
       0       11     -0.0375    -0.1335   -0.57
       1       21     -0.1350    -0.2310   -1.32
       2       46     -0.0795    -0.1755   -1.43
       3       68     +0.1031    +0.0071   +0.07
       4       99     +0.0272    -0.0688   -0.72
       5      117     +0.2736    +0.1776   +1.86   <- 하필 가운데
       6      113     +0.2626    +0.1666   +1.63
       7      144     +0.0735    -0.0225   -0.26
       8      100     +0.0242    -0.0718   -0.53
       9       89     +0.1659    +0.0699   +0.49
      10       91     +0.1016    +0.0056   +0.06
      11       64     -0.2061    -0.3021   -1.24
      12       45     -0.2156    -0.3116   -1.90
      13       25     +0.8092    +0.7132   +1.71
      14        8     (표본 5일 미만 기준 미달로 표에서 빠짐)

  합의가 진짜 중요하면 개수에 따라 수익이 한 방향으로 기울어야 한다.
  그런데 5개에서 +1.86, 8개에서 -0.53, 12개에서 -1.90, 13개에서 +1.71 이다.
  제일 큰 값들이 '가장 애매한 가운데' 와 그 근처에 흩어져 있다. 잡음의
  모양이다.

===========================================================================
결과 3 - 대조군: 어긋난 데이터가 실제보다 나은 경우가 절반이 넘는다
===========================================================================
버킷 15개 + 꼬리 6개 + 기울기 1개를 훑었으니 제일 좋은 값이 우연히
커진다. 그래서 지표를 수익과 어긋나게 밀고 같은 탐색을 500번 반복했다.

  실제 데이터의 최고 |t| = 2.02
  어긋난 데이터 500번: 중앙값 2.05 / 95%지점 2.89 / 최대 4.34
  어긋난 데이터가 실제보다 좋았던 비율 = 54.4%

  54.4% 다. 실제 데이터가 어긋난 데이터의 **중앙값보다도 낮다**.
  아무 관계 없는 데이터를 넣었을 때와 구별이 전혀 안 된다.

  (참고: 거래량을 넣기 전 13개 지표로는 이 비율이 7.8% 였다. 사용자가
  지적한 거래량을 넣자 54.4% 로 올라갔다. 7.8% 자체가 잡음이었다는
  뜻이고, 5% 를 못 넘어서 통과시키지 않았던 판단이 맞았다.)

반기 양방향
  전반부->후반부: 제일 좋은 개수 9개  -> 다른 쪽 -0.0928%p  부호 뒤집힘
  후반부->전반부: 제일 좋은 개수 13개 -> 다른 쪽 -0.7578%p  부호 뒤집힘

  이번엔 양방향 모두 뒤집혔다. 한쪽에서 제일 좋은 규칙이 다른 쪽에서
  손해로 바뀐다.

===========================================================================
결과 4 - 방향이 아니라 '큰 날' 도 못 맞춘다
===========================================================================
방향은 몰라도 '오늘은 크게 움직인다' 를 알면 그것도 정보다. 그래서
쏠림(|합의개수 - 6.5|)이 다음날 변동폭을 예측하는지 봤다.

  쏠림 -> 다음날 변동폭 기울기 t = +1.28   없음

     쏠림          일수   다음날 변동폭
   0~1.5 (섞임)     257     0.807%
   1.5~3.5         405     0.811%
   3.5~5.5         269     0.785%
   5.5+ (쏠림)      102     0.964%

  가장 쏠린 구간만 조금 크다(0.964%). 그런데 중간 구간은 순서가
  뒤죽박죽이고(0.807 -> 0.811 -> 0.785) t=1.28 이다.
  쓸 만한 크기가 아니다.

===========================================================================
읽는 법
===========================================================================
  1) 아이디어의 논리는 멀쩡하다. 막는 것은 두 가지다.
       첫째, 지표들이 독립이 아니다. 14개를 모아도 실질 6.3개고 그것들이
       다 '위험선호' 한 가지를 재고 있다. 여러 증인이 아니라 한 증인에게
       열네 번 물어본 것이다.
       둘째, 조건을 조일수록 해당일이 사라진다. 엄격한 기준으로 '전부
       나쁜 날' 은 4.2년 동안 0일이었다.
     이 둘은 데이터를 더 모아서 풀리지 않는다. 첫째는 지표의 성질이고,
     둘째는 AND 로 묶는 방식 자체의 성질이다.
  2) 승률로 물었을 때의 답: 구분 안 된다. 전부 좋은 날 54.5% vs 전부
     나쁜 날 50.0%, 차이 +4.5%p 에 z=+0.20. 표본이 11일과 8일이라
     신뢰구간이 각각 28~79% / 22~78% 로 겹친다.
  3) 1일 앞은 표본 1,041개로 검정력이 충분하다. 상관 +0.002
     (t=+0.06) 이므로 '일별로는 거의 없다' 고 말할 수 있다.
  4) 20일 앞은 유효표본 51개뿐이라 검정력이 부족하다. 여기서는
     '없다' 가 아니라 '알 수 없다' 가 맞다.
  5) 대조군 통과율 54.4% 는 '아무것도 아님이 증명됐다' 가 아니라
     '아무것도 아닌 것과 구별되지 않는다' 다. 두 말은 다르다.
  6) 금리를 넣으면 달라지나 - 거래량을 넣었을 때 실질 개수가 0.6 밖에
     안 올랐다. 금리도 위험선호와 같이 움직이는 편이라 비슷할 것이다.
     다만 받아두면 확인할 수 있으니 fetch_us_market.py 에 ^TNX 를
     넣어뒀다.

주문은 내지 않는다. CSV 만 읽는다.

실행:
    python analyze_consensus.py
"""
import csv
import glob
import math
import pathlib
import statistics as st
import sys
from collections import Counter

import numpy as np

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import strategy as S  # noqa: E402

HOLD, PICK = 20, 10
LOOK = 250              # 각 지표의 '평소' 를 정하는 과거 창
N_SHIFT = 500
SEED = 20260918

# 위험회피 방향. +1 = 클수록 나쁜 쪽, -1 = 작을수록 나쁜 쪽.
# 결과를 보기 전에 교과서 통념대로 정했다. 맞추려고 고른 게 아니다.
RISK_OFF = {
    "us_sp500": -1,      # 미국 주가 하락이 나쁜 쪽
    "us_nasdaq": -1,
    "us_dow": -1,
    "us_sox": -1,
    "us_vix_chg": +1,    # 공포 상승이 나쁜 쪽
    "us_vix_level": +1,
    "fx_krw": +1,        # 원화 약세가 나쁜 쪽
    "kr_vol20": +1,      # 변동성 높음이 나쁜 쪽
    "kr_breadth5": -1,   # 오르는 종목 적음이 나쁜 쪽
    "kr_ret5": -1,       # 시장 하락이 나쁜 쪽
    "flow_foreign": -1,  # 외국인 순매도가 나쁜 쪽
    "flow_inst": -1,     # 기관 순매도가 나쁜 쪽
    "flow_indiv": +1,    # 개인 순매수가 나쁜 쪽 (통념)
    # (2026-09-18 추가) 사용자가 거래량을 명시했는데 빠져 있었다.
    # 유니버스 전체 거래대금 5일평균/60일평균. 거래가 마르면 나쁜 쪽.
    "mkt_value": -1,
}
KEYS = list(RISK_OFF)
CSV_KEYS = [k for k in KEYS if k != "mkt_value"]


def market_value_ratio(dates, panel):
    """유니버스 전체 거래대금의 5일평균/60일평균. '거래량' 지표다."""
    tot = {}
    for di in range(len(dates)):
        t = 0.0
        for s in panel.values():
            j = s.pos.get(di)
            if j is not None:
                t += s.value[j]
        tot[dates[di]] = t
    out = {}
    for i, d in enumerate(dates):
        if i < 60:
            continue
        v5 = st.mean([tot[dates[k]] for k in range(i - 5, i)])
        v60 = st.mean([tot[dates[k]] for k in range(i - 60, i)])
        if v60 > 0:
            out[d] = v5 / v60
    return out


def load_indicators(mkt=None):
    """지표가 모두 있는 날만 남긴다. mkt 를 주면 거래량까지 포함한다."""
    raw = {}
    for path in sorted(glob.glob(str(_ROOT / "data" / "market_indicators_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                raw[r["date"]] = r

    def g(d, key):
        try:
            return float(raw[d][key])
        except (TypeError, ValueError, KeyError):
            return None

    rows = []
    for d in sorted(raw):
        v = {k: g(d, k) for k in CSV_KEYS}
        v["mkt_value"] = (mkt or {}).get(d)
        keys = KEYS if mkt is not None else CSV_KEYS
        if all(v[k] is not None for k in keys):
            rows.append((d, {k: v[k] for k in keys}))
    return rows


def wilson(k, n, z=1.96):
    """승률의 신뢰구간. 표본이 작으면 여기서 바로 드러난다.

    19일짜리 표본의 승률은 ±20%p 넘게 흔들린다. 숫자만 보면 착각한다.
    """
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    # 부동소수점 때문에 0 아래나 1 위로 새는 것을 막는다 (전승/전패에서 생김)
    return p, max(0.0, c - h), min(1.0, c + h)


def need_days(gap, z=2.80):
    """승률 차이 gap(비율)을 확인하는 데 필요한 한쪽 표본 일수.

    5% 유의 + 80% 검정력. z = 1.96 + 0.84.
    """
    return 2 * z * z * 0.25 / (gap * gap) if gap > 0 else float("inf")


def effective_count(rows):
    """상관행렬 고유값으로 실질 독립 지표 개수를 잰다 (participation ratio).

    지표가 다 같은 방향이어도 서로 베껴 쓴 것이면 증거가 그 개수가 아니다.
    """
    keys = [k for k in KEYS if k in rows[0][1]]
    M = np.array([[v[k] * RISK_OFF[k] for k in keys] for _d, v in rows], float)
    M = (M - M.mean(0)) / M.std(0)
    ev = np.linalg.eigvalsh(np.corrcoef(M.T))
    ev = ev[ev > 1e-9]
    return (ev.sum() ** 2) / (ev ** 2).sum(), np.corrcoef(M.T), keys


def agreement(rows, mode="median"):
    """날짜 -> 위험회피 쪽으로 기운 지표 개수.

    mode="median" 은 '평소보다 나쁜가' (과거 LOOK일 중앙값 초과).
    mode="tail"   은 '진짜 나쁜가'   (과거 LOOK일 중 위험회피 쪽 상위 20%).

    어느 쪽이든 수준을 그대로 쓰지 않고 과거 창과 비교한다. 수준을 그대로
    쓰면 장기 추세 때문에 시간에 따라 편향된다 (예: 환율이 5년간 오르면
    뒤쪽 해가 전부 '나쁜 쪽' 으로 몰린다).

    사용자가 물은 '진이인짜 나쁜 날' 에 가까운 것은 tail 쪽이다. 다만
    tail 로 조이면 해당하는 날이 급격히 줄어든다 - 그게 이 아이디어의
    두 번째 문제다.

    어느 쪽이든 과거만 본다. 미래 정보가 없다.
    """
    keys = [k for k in KEYS if k in rows[0][1]]
    out = {}
    for n in range(LOOK, len(rows)):
        d, v = rows[n]
        cnt = 0
        for k in keys:
            x = v[k] * RISK_OFF[k]
            hist = sorted(rows[m][1][k] * RISK_OFF[k]
                          for m in range(n - LOOK, n))
            thr = (hist[len(hist) // 2] if mode == "median"
                   else hist[int(len(hist) * 0.80)])
            if x > thr:
                cnt += 1
        out[d] = cnt
    return out


def basket_daily(dates=None, panel=None):
    """전략 바스켓의 일별 등락. 20일마다 갈아타는 실제 곡선이다."""
    if dates is None or panel is None:
        dates, panel = S.load_panel()
    n = len(dates)
    start = max(140, S.LIQUIDITY_DAYS + 2)
    out = {}
    di, cur = start, []
    while di < n:
        if (di - start) % HOLD == 0:
            cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
            sc = [(x, c) for c in cand
                  if (x := S.factor_score(panel, c, di, "low_vol")) is not None]
            if len(sc) >= PICK:
                sc.sort(reverse=True)
                cur = [c for _s, c in sc[:PICK]]
        if cur:
            rs = []
            for c in cur:
                s = panel.get(c)
                if s is None:
                    continue
                j, jp = s.pos.get(di), s.pos.get(di - 1)
                if j is None or jp is None or not s.close[jp]:
                    continue
                rs.append((s.close[j] / s.close[jp] - 1) * 100)
            if len(rs) >= 5:
                out[dates[di]] = st.mean(rs)
        di += 1
    return out


def slope_t(x, y):
    """기울기와 t. 이게 미리 정한 단 하나의 검사다."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mx, my = x.mean(), y.mean()
    vx = ((x - mx) ** 2).sum()
    if vx == 0 or len(x) < 4:
        return 0.0, 0.0
    b = ((x - mx) * (y - my)).sum() / vx
    resid = y - (my + b * (x - mx))
    se = math.sqrt((resid ** 2).sum() / (len(x) - 2) / vx)
    return b, (b / se if se else 0.0)


def max_abs_t(cnt, y):
    """이 파일이 실제로 훑어본 탐색 전부의 최고 |t|.

    버킷 14 + 위꼬리 3 + 아래꼬리 3 + 기울기 1 = 21가지.
    대조군과 똑같은 탐색을 해야 비교가 성립하므로 함수로 묶어둔다.
    """
    cnt = np.asarray(cnt)
    y = np.asarray(y, float)
    base = y.mean()
    best = 0.0

    def upd(sel, need):
        nonlocal best
        if len(sel) >= need:
            se = sel.std(ddof=1) / math.sqrt(len(sel))
            if se > 0:
                best = max(best, abs((sel.mean() - base) / se))

    for c in range(14):
        upd(y[cnt == c], 10)
    for thr in (11, 12, 13):
        upd(y[cnt >= thr], 5)
    for thr in (0, 1, 2):
        upd(y[cnt <= thr], 5)
    return max(best, abs(slope_t(cnt.astype(float), y)[1]))


def main():
    dates, panel = S.load_panel()
    mkt = market_value_ratio(dates, panel)
    rows = load_indicators(mkt)
    K = len(KEYS)
    print(f"지표 {K}개(거래량 포함)가 모두 있는 날 {len(rows):,}일 "
          f"({rows[0][0]} ~ {rows[-1][0]})")

    # ------------------------------------------- 1) 실질 독립 개수
    n_eff, C, ekeys = effective_count(rows)
    print("\n" + "=" * 92)
    print(f"=== 1) 지표 {K}개 중 실질적으로 독립인 것은 약 {n_eff:.1f}개 ===")
    print("=== 서로 베껴 쓴 지표는 증거를 늘려주지 않는다 ===")
    print("=" * 92)
    print("  상관 0.7 넘는 짝:")
    found = False
    for i in range(len(ekeys)):
        for j in range(i + 1, len(ekeys)):
            if abs(C[i, j]) > 0.7:
                print(f"    {ekeys[i]:<14} {ekeys[j]:<14} {C[i,j]:+.3f}")
                found = True
    if not found:
        print("    없음")
    print(f"\n  '{K}개가 다 같은 방향' 은 압도적으로 들리지만,")
    print(f"  실제로는 '위험선호' 한 가지를 {K}가지로 잰 것이다.")

    # ================================================================
    # 0) 사용자가 물은 그 질문: 다 좋은 날과 다 나쁜 날의 '오를 확률'
    # ================================================================
    basket0 = basket_daily(dates, panel)
    bd0 = sorted(basket0)
    bp0 = {d: i for i, d in enumerate(bd0)}
    print("\n" + "=" * 92)
    print("=== 0) 다 좋은 날 vs 다 나쁜 날 - 오를 확률이 구분되나 ===")
    print("=== 평균 수익이 아니라 '오를 확률' 을 직접 낸다 ===")
    print("=" * 92)
    for mode, mlabel in (("median", "평소보다 좋은가/나쁜가 (중앙값 기준)"),
                         ("tail", "진짜 좋은가/나쁜가 (상·하위 20% 기준)")):
        ag = agreement(rows, mode)
        prs = [(c, basket0[bd0[bp0[d] + 1]])
               for d, c in sorted(ag.items())
               if d in bp0 and bp0[d] + 1 < len(bd0)]
        Xc = np.array([a for a, _b in prs])
        Yc = np.array([b for _a, b in prs], float)
        bp, _l, _h = wilson(int((Yc > 0).sum()), len(Yc))
        print(f"\n  [{mlabel}]")
        print(f"  표본 {len(prs):,}일. 전체 다음날 오를 확률 {bp*100:.1f}%")
        print(f"  나쁜 지표 개수 평균 {Xc.mean():.1f} / "
              f"최소 {Xc.min()} / 최대 {Xc.max()}")
        print(f"\n  {'나쁜 지표':>9} {'일수':>5} {'오를 확률':>9} "
              f"{'95% 구간':>16} {'전체대비':>9}")
        for c in range(K + 1):
            sel = Yc[Xc == c]
            if len(sel) < 5:
                continue
            p, lo, hi = wilson(int((sel > 0).sum()), len(sel))
            print(f"  {c:>9} {len(sel):>5} {p*100:>8.1f}% "
                  f"{f'{lo*100:.0f} ~ {hi*100:.0f}':>16} "
                  f"{(p-bp)*100:>+8.1f}%p")
        print(f"\n  {'좋은 쪽':<15}{'나쁜 쪽':<15}"
              f"{'좋은날 승률':>11}{'나쁜날 승률':>11}{'차이':>8}{'z':>7}  판정")
        for glab, gs, blab, bs in (
                ("전부 좋음", Xc == 0, "전부 나쁨", Xc == K),
                ("2개 이하", Xc <= 2, f"{K-2}개 이상", Xc >= K - 2),
                ("4개 이하", Xc <= 4, f"{K-4}개 이상", Xc >= K - 4)):
            yg, yb = Yc[gs], Yc[bs]
            if len(yg) < 5 or len(yb) < 5:
                print(f"  {glab:<15}{blab:<15}"
                      f"{'표본 부족':>22} ({len(yg)}일 / {len(yb)}일)")
                continue
            kg, kb = int((yg > 0).sum()), int((yb > 0).sum())
            pg, pb = kg / len(yg), kb / len(yb)
            pp = (kg + kb) / (len(yg) + len(yb))
            se = math.sqrt(pp * (1 - pp) * (1 / len(yg) + 1 / len(yb)))
            z = (pg - pb) / se if se > 0 else 0.0
            print(f"  {glab:<15}{blab:<15}{pg*100:>10.1f}%{pb*100:>10.1f}%"
                  f"{(pg-pb)*100:>+7.1f}%p{z:>+7.2f}  "
                  f"{'구분된다' if abs(z) > 1.96 else '구분 안 된다'}")

        # ------- 극단이 얼마나 드문가 -> 확인에 몇 년 걸리나
        yrs = len(prs) / 246
        print(f"\n  극단이 얼마나 드문가 ({yrs:.1f}년 기준)")
        print(f"  {'구간':<14} {'일수':>5} {'연간':>7} "
              f"{'승률 10%p 차이 확인에':>22}")
        for lab, sel in (("전부 좋음", Xc == 0), ("전부 나쁨", Xc == K),
                         (f"{K-2}개 이상 나쁨", Xc >= K - 2)):
            nd = int(sel.sum())
            per = nd / yrs
            need = need_days(0.10)
            txt = (f"{need/per:,.0f}년" if per > 0 else "해당일 없음")
            print(f"  {lab:<14} {nd:>5} {per:>6.1f}일 {txt:>22}")
        print(f"  (승률 10%p 차이를 확인하려면 한쪽에 "
              f"{need_days(0.10):,.0f}일이 필요하다)")

    agree = agreement(rows)
    basket = basket0
    bd = sorted(basket)
    bpos = {d: i for i, d in enumerate(bd)}

    def fwd(d, k):
        i = bpos.get(d)
        if i is None or i + k >= len(bd):
            return None
        acc = 1.0
        for m in range(i + 1, i + 1 + k):
            acc *= (1 + basket[bd[m]] / 100)
        return (acc - 1) * 100

    pairs = []
    for d, c in sorted(agree.items()):
        if d in bpos and fwd(d, 1) is not None:
            pairs.append((d, c, fwd(d, 1), fwd(d, 5), fwd(d, 20)))
    X = np.array([p[1] for p in pairs])
    Y1 = np.array([p[2] for p in pairs], float)
    print(f"\n  짝지은 표본 {len(pairs):,}개 (전날 합의 -> 다음날 수익)")
    print(f"  합의 개수 분포: 평균 {X.mean():.1f} / 중앙값 "
          f"{int(np.median(X))} / 최소 {X.min()} / 최대 {X.max()}")
    cc = Counter(X.tolist())
    print("  " + "  ".join(f"{k}개:{cc[k]}일" for k in sorted(cc)))

    # ------------------------------------------- 2) 예측력
    print("\n" + "=" * 88)
    print("=== 2) 합의가 앞으로의 수익을 예측하나 ===")
    print("=== 1일 앞은 겹치지 않아 검정력이 충분하다 ===")
    print("=" * 88)
    print(f"  {'앞 기간':<9} {'표본':>7} {'유효표본':>9} {'상관':>8} "
          f"{'표준오차':>9} {'t':>7} {'판정':>10}")
    for k, idx, label in ((1, 2, "1일"), (5, 3, "5일"), (20, 4, "20일")):
        sub = [(p[1], p[idx]) for p in pairs if p[idx] is not None]
        xs = np.array([a for a, _b in sub], float)
        ys = np.array([b for _a, b in sub], float)
        r = float(np.corrcoef(xs, ys)[0, 1])
        neff = len(sub) / k                 # 겹침 보정
        se = 1 / math.sqrt(neff - 2) if neff > 3 else float("nan")
        t = r / se if se == se and se > 0 else float("nan")
        print(f"  {label:<9} {len(sub):>7} {neff:>9.0f} {r:>+8.3f} "
              f"{se:>9.3f} {t:>+7.2f} "
              f"{('눈여겨볼 값' if abs(t) > 2 else '없음'):>10}")

    b, t = slope_t(X, Y1)
    print(f"\n  미리 정한 단 하나의 검사 (버킷을 고르지 않는다):")
    print(f"    합의 개수 -> 다음날 수익 기울기 {b:+.5f}%p/지표  t = {t:+.2f}")
    print(f"    13개 전부 일치와 0개 일치의 차이 = {b*13:+.4f}%p")
    print(f"    (하루 변동이 보통 {Y1.std():.2f}% 다. 비교해보면 무의미하다)")

    print(f"\n  {'일치 개수':>9} {'일수':>6} {'다음날 평균':>12} "
          f"{'전체대비':>10} {'t':>7}")
    allm = Y1.mean()
    for c in range(14):
        sel = Y1[X == c]
        if len(sel) < 10:
            continue
        se = sel.std(ddof=1) / math.sqrt(len(sel))
        print(f"  {c:>9} {len(sel):>6} {sel.mean():>+12.4f} "
              f"{sel.mean()-allm:>+10.4f} {(sel.mean()-allm)/se:>+7.2f}")
    print("\n  합의가 중요하면 개수에 따라 한 방향으로 기울어야 한다.")
    print("  가장 큰 값이 어디서 나왔는지 보라 - 가운데면 잡음이다.")

    # ------------------------------------------- 3) 대조군
    print("\n" + "=" * 88)
    print("=== 3) 밀어놓기 대조군 - 어긋난 데이터에서도 이만큼 나오나 ===")
    print("=== 훑어본 21가지를 전부 똑같이 다시 한다 ===")
    print("=" * 88)
    rng = np.random.default_rng(SEED)
    real = max_abs_t(X, Y1)
    print(f"  실제 데이터의 최고 |t| = {real:.2f}")
    vals = []
    n = len(X)
    for _ in range(N_SHIFT):
        k = int(rng.integers(20, n - 20))
        vals.append(max_abs_t(np.roll(X, k), Y1))
    vals.sort()
    beat = sum(1 for v in vals if v >= real) / N_SHIFT
    print(f"  어긋난 데이터 {N_SHIFT}번의 최고 |t|: 중앙값 "
          f"{vals[len(vals)//2]:.2f} / 95%지점 {vals[int(len(vals)*0.95)]:.2f} "
          f"/ 최대 {vals[-1]:.2f}")
    print(f"  어긋난 데이터가 실제보다 좋았던 비율 = {beat*100:.1f}%")
    print("  " + ("-> 5% 미만. 눈여겨볼 값" if beat < 0.05
                  else "-> 어긋난 데이터에서도 흔하다. 찾은 게 아니다"))
    print("  (이 비율은 '아무것도 아님이 증명됐다' 가 아니라")
    print("   '아무것도 아닌 것과 구별되지 않는다' 는 뜻이다)")

    # ------------------------------------------- 4) 쏠림 -> 변동폭
    print("\n" + "=" * 88)
    print("=== 4) 방향은 몰라도 '큰 날' 은 알려주나 ===")
    print("=== 쏠림 = |합의개수 - 6.5| (양쪽 극단이 다 큰 값) ===")
    print("=" * 88)
    EXT = np.abs(X - 6.5)
    AY = np.abs(Y1)
    _b2, t2 = slope_t(EXT, AY)
    print(f"  쏠림 -> 다음날 변동폭  t = {t2:+.2f}  "
          f"{'눈여겨볼 값' if abs(t2) > 2 else '없음'}")
    print(f"\n  {'쏠림':>14} {'일수':>6} {'다음날 변동폭':>14}")
    for lo, hi, lab in ((0, 1.5, "0~1.5 (섞임)"), (1.5, 3.5, "1.5~3.5"),
                        (3.5, 5.5, "3.5~5.5"), (5.5, 7.0, "5.5+ (쏠림)")):
        sel = AY[(EXT >= lo) & (EXT < hi)]
        if len(sel) >= 10:
            print(f"  {lab:>14} {len(sel):>6} {sel.mean():>13.3f}%")

    # ------------------------------------------- 5) 반기 양방향
    print("\n" + "=" * 88)
    print("=== 5) 반기 양방향: 한쪽에서 제일 좋은 기준이 다른 쪽에서도 사나 ===")
    print("=" * 88)
    half = len(X) // 2
    for lab, xa, ya, xb, yb in (
            ("전반부->후반부", X[:half], Y1[:half], X[half:], Y1[half:]),
            ("후반부->전반부", X[half:], Y1[half:], X[:half], Y1[:half])):
        base_a, base_b = ya.mean(), yb.mean()
        best_c, best_e = None, -9e9
        for c in range(14):
            sel = ya[xa == c]
            if len(sel) >= 10 and sel.mean() - base_a > best_e:
                best_e, best_c = sel.mean() - base_a, c
        selb = yb[xb == best_c]
        eb = (selb.mean() - base_b) if len(selb) else float("nan")
        print(f"  {lab}: 제일 좋은 일치개수 {best_c}개 "
              f"(그쪽 {best_e:+.4f}%p) -> 다른 쪽 {eb:+.4f}%p  "
              f"{'부호 유지' if eb > 0 else '부호 뒤집힘'}")

    print("\n" + "=" * 88)
    print("=== 결론 ===")
    print("=" * 88)
    print(f"  아이디어의 논리는 멀쩡하다. 문제는 지표들이 독립이 아닌 것이다.")
    print(f"  {len(KEYS)}개를 모아도 실질 {n_eff:.1f}개고, 그것들이 다 "
          f"'위험선호' 한 가지를 재고 있다.")
    print("  여러 증인을 모은 게 아니라 한 증인에게 열네 번 물어본 것이다.")
    print("  1일 앞은 표본이 1,000개 넘어 검정력이 충분하므로 "
          "'일별로는 거의 없다' 고 말할 수 있다.")
    print(f"  20일 앞은 유효표본 {len(pairs)//20}개뿐이라 '없다' 가 아니라 "
          "'알 수 없다' 가 맞다.")


if __name__ == "__main__":
    main()
