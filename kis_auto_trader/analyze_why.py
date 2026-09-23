"""저변동이 왜 통하나 - 그리고 언제 안 통하게 되나.

(2026-09-21 신설) 사용자: "지금 계속 자료 수집만 하지말고 지금 있는
자료들로 생각을 확장할 필요가 있을 거 같아."

맞는 지적이었다. 지금까지 26개 모듈이 전부 "이 규칙이 통하나?" 를 물었고
"통하는 이유가 뭔가?" 는 한 번도 안 물었다. 이유를 모르면 앞으로 성적이
나빠질 때 그게 일시적인 것인지 효과가 죽은 것인지 구별할 수가 없다.

새 규칙을 찾는 게 아니라 이미 채택한 규칙을 쪼개보는 것이므로 다중검정이
늘지 않는다. 채택/탈락을 가리는 계산이 아니다.

===========================================================================
질문 1 - 실제로 뭘 사고 있나 (쏠림이 있나)
===========================================================================
120일 주기 10회차, 슬롯 100개에 종목 37개가 들어왔다. 상위 15종목이 69%.

  KT&G       9/10회     삼성바이오로직스 5/10     삼성전자     3/10
  KT         8/10       기업은행        5/10     현대차       3/10
  우리금융지주 7/10       대한항공        4/10     삼성전자우   3/10
  SK텔레콤    7/10                               오리온       3/10
  신한지주    6/10                               하나금융지주 2/10

업종으로 묶으면
  금융(우리/신한/기업/하나/삼성화재)  22%
  통신(KT/SKT)                      15%
  담배·식품(KT&G/오리온)             12%
  제조·기타(삼성바이오/대한항공/삼성전자/현대차/기아)  20%

걱정했던 '금융 단독 베팅' 은 아니다. 다만 방어업종(금융+통신+담배)이 49%
이고, 이건 저변동 전략이 어느 시장에서든 만드는 전형적 구성이다. 한국
2021~2026 특유의 우연이 아니라는 뜻이라 오히려 안심되는 쪽이다.

그래도 사실상 몇 종목을 계속 들고 있는 전략이라는 점은 짚어둔다.
KT&G 는 10회 중 9회 들어갔다.

===========================================================================
질문 2 - 덜 떨어져서인가, 더 올라서인가  (이 파일의 핵심)
===========================================================================
풀 평균 수익의 부호로 날을 갈라서 조건부 평균을 봤다.

              날수     풀평균%    저변동10%   고변동10%   저변동-풀
  오른 날      592     +1.277     +0.472     +1.438     -0.805
  내린 날      558     -1.377     -0.316     -2.197     +1.061

**저변동은 오를 때 덜 오르고 내릴 때 덜 내린다.**
  오르는 날 풀의 37% 만 따라간다 (0.472/1.277)
  내리는 날 풀의 23% 만 맞는다   (0.316/1.377)

엣지의 정체는 이 **비대칭**이다. 따라가는 비율(37%)보다 맞는 비율(23%)이
낮아서, 그 차이가 쌓인다.

검산: 저변동 하루 평균 +0.0896% x 246일 = 연 22.0%. 백테스트 값과 같다.
      같은 기간 풀 평균은 연 -2.6% 였다.

그런데 이 엣지는 **서로 상쇄되는 두 큰 값의 차이**다.
  오른 날 기여  -477
  내린 날 기여  +592
  순            +115

내린 날에 버는 것으로 오른 날에 뒤처지는 것을 메우고 남는 구조다.

===========================================================================
질문 2b - 그래서 언제 안 통하게 되나 (손익분기)
===========================================================================
위 구조를 그대로 풀면 멈춰야 할 조건이 나온다.

  오른 날 하나당 끌림   0.805%p
  내린 날 하나당 이득   1.061%p
  상쇄되는 비율         오른날/내린날 = 1.061/0.805 = 1.318
  2021~2026 실제        592/558 = 1.061

**오른 날이 내린 날보다 32% 이상 많아지면 엣지가 0 이 된다.**

이게 "언제 멈춰야 하나" 에 대한 이 저장소의 첫 구체적 답이다. 지금까지는
"6년간 잘 됐다" 뿐이라, 앞으로 성적이 나빠져도 일시적인 것인지 효과가
죽은 것인지 구별할 방법이 없었다.

주의할 점 둘
  1) 강한 상승장이 오면 이 전략은 돈을 잃는 게 아니라 **시장에 뒤처진다.**
     둘은 다르다. 절대 수익은 플러스일 수 있다.
  2) 1.318 은 2021~2026 의 조건부 평균으로 계산한 값이다. 그 평균 자체가
     시기에 따라 변하므로 고정된 상수로 믿으면 안 된다. 경보의 눈금이지
     방아쇠가 아니다.

===========================================================================
질문 3 - 몇 종목에 의존하나
===========================================================================
종목별로 (그 종목 수익 - 풀평균)/10 을 들어간 날마다 더했다.
총 초과수익 +115.5%p 가 어떻게 갈리는지 본다.

  신한지주     +13.7 (12%)      CJ제일제당  -3.8 (-3%)
  우리금융지주 +12.0 (10%)      오리온      -4.1 (-4%)
  KT&G        +11.2 (10%)      크래프톤    -5.5 (-5%)
  KT           +9.4  (8%)
  현대차       +8.5  (7%)

  상위 1종목 제외 -> 88% 남음
  상위 2종목 제외 -> 78% 남음
  상위 3종목 제외 -> 68% 남음
  상위 5종목 제외 -> 53% 남음

한두 종목이 만든 게 아니다. 1등이 12% 뿐이고 5개를 빼도 절반이 남는다.
이건 '운 좋은 종목 몇 개' 가 아니라 성질이 작동한 쪽에 가깝다.

===========================================================================
읽는 법
===========================================================================
1) 이 전략은 '좋은 종목을 고르는 것' 이 아니라 **'시장을 덜 타는 것'** 이다.
   오를 때 37%, 내릴 때 23%. 사용자의 "큰 이득을 포기하더라도 큰 손해를
   피한다" 와 구조가 정확히 맞는다. 우연이 아니라 설계대로다.

2) 그래서 상승장에서 시장에 뒤처지는 것은 고장이 아니라 **정상 작동**이다.
   그때 전략을 의심하면 안 된다. 의심해야 할 때는 내리는 날에 풀만큼
   같이 내리기 시작할 때다 (23% 비율이 무너질 때).

3) 감시할 숫자가 둘 생겼다.
     오른날/내린날 비율   1.318 에 가까워지면 엣지가 상쇄된다
     내린 날 하락 비율    0.23 에서 올라가면 방어가 깨지는 것이다
   둘 다 전진 기록으로 매일 잴 수 있다.

4) 안 잰 것: 이 분해는 **매일 다시 뽑은 저변동 10종목**의 조건부 평균이다.
   실제 포트폴리오(120일 주기, 1주 단위, 부분교체)와 완전히 같지는 않다.
   연환산이 22.0% 로 맞아떨어졌지만 그건 신호와 포트폴리오가 가깝다는
   뜻이지 같다는 뜻은 아니다.

실행:
  python analyze_why.py
"""
import collections
import csv
import glob
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import analyze_knobs as K  # noqa: E402
import strategy as S  # noqa: E402

BASE_DI = 250
PICK = 10
PERIOD = 120
MIN_POOL = 40          # 이만큼은 수익률이 있어야 그 날을 쓴다
DAYS_PER_YEAR = 246

# 2021~2026 에서 실측한 값. 아래 함수들의 기본값으로 쓴다.
UP_DRAG = 0.805        # 오른 날 하나당 풀에 뒤처지는 폭 (%p)
DOWN_GAIN = 1.061      # 내린 날 하나당 풀보다 앞서는 폭 (%p)
UP_CAPTURE = 0.37      # 오르는 날 풀의 몇 % 를 따라가나
DOWN_CAPTURE = 0.23    # 내리는 날 풀의 몇 % 를 맞나


def breakeven_ratio(up_drag=UP_DRAG, down_gain=DOWN_GAIN):
    """오른날/내린날 비율이 이보다 커지면 엣지가 상쇄된다.

    오른 날 U 개, 내린 날 D 개일 때 총 엣지는
        -up_drag * U + down_gain * D
    이므로 0 이 되는 지점은 U/D = down_gain/up_drag 다.
    """
    if up_drag <= 0:
        return float("inf")
    return down_gain / up_drag


def edge_left(up_days, down_days, up_drag=UP_DRAG, down_gain=DOWN_GAIN):
    """그 기간의 오른날/내린날 구성에서 남는 총 엣지(%p)."""
    return -up_drag * up_days + down_gain * down_days


def names_from_panel():
    """종목코드 -> 이름. 표를 읽기 쉽게 하려는 용도뿐이다."""
    out = {}
    for path in sorted(glob.glob(str(_ROOT / "data" / "krx_panel_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("name") and r.get("code"):
                    out[r["code"]] = r["name"]
    return out


def daily_split(dates, panel, order, base=BASE_DI):
    """날을 풀 수익 부호로 갈라 조건부 평균을 낸다.

    반환 {up: {...}, down: {...}, contrib: Counter, appear: Counter}
    """
    up = {"pool": [], "lo": [], "hi": []}
    down = {"pool": [], "lo": [], "hi": []}
    contrib, appear = collections.Counter(), collections.Counter()

    for di in range(base, len(dates) - 1):
        if di not in order:
            continue
        lst = order[di]
        rets = {}
        for c in lst:
            a = E.price(panel, c, di, "close")
            b = E.price(panel, c, di + 1, "close")
            if a and b:
                rets[c] = (b / a - 1) * 100
        if len(rets) < MIN_POOL:
            continue
        pool = st.mean(rets.values())
        lo = [rets[c] for c in lst[:PICK] if c in rets]
        hi = [rets[c] for c in lst[-PICK:] if c in rets]
        if not lo or not hi:
            continue
        side = up if pool >= 0 else down
        side["pool"].append(pool)
        side["lo"].append(st.mean(lo))
        side["hi"].append(st.mean(hi))
        for c in lst[:PICK]:
            if c in rets:
                contrib[c] += (rets[c] - pool) / PICK
                appear[c] += 1
    return {"up": up, "down": down, "contrib": contrib, "appear": appear}


def drop_top(contrib, n):
    """상위 n종목을 빼면 총 초과수익이 얼마나 남나 (남은 비율 0~1)."""
    total = sum(contrib.values())
    if not total:
        return 0.0
    dropped = sum(v for _c, v in contrib.most_common(n))
    return (total - dropped) / total


def picks_over_time(dates, panel, order, base=BASE_DI, period=PERIOD):
    """교체일마다 뽑힌 종목. (Counter, 회차수)"""
    got, rounds, di = collections.Counter(), 0, base
    while di < len(dates):
        if di in order:
            for c in order[di][:PICK]:
                got[c] += 1
            rounds += 1
        di += period
    return got, rounds


def main():
    dates, panel = S.load_panel()
    print("일별 순위 계산 중...")
    order = K.ranks(dates, panel, BASE_DI)
    names = names_from_panel()

    print("\n=== 1) 실제로 뭘 사나 ===")
    got, rounds = picks_over_time(dates, panel, order)
    top15 = sum(v for _c, v in got.most_common(15))
    print(f"{rounds}회차 x {PICK}종목 = {rounds*PICK}슬롯에 종목 {len(got)}개")
    print(f"상위 15종목이 전체의 {top15/(rounds*PICK)*100:.0f}%")
    for c, n in got.most_common(12):
        print(f"  {names.get(c, c):<18}{n}/{rounds}회")

    d = daily_split(dates, panel, order)
    print("\n=== 2) 덜 떨어져서인가, 더 올라서인가 ===")
    print(f"{'':10}{'날수':>7}{'풀평균%':>10}{'저변동%':>10}"
          f"{'고변동%':>10}{'저변동-풀':>11}")
    for label, side in (("오른 날", d["up"]), ("내린 날", d["down"])):
        p, lo, hi = st.mean(side["pool"]), st.mean(side["lo"]), st.mean(side["hi"])
        print(f"{label:<10}{len(side['pool']):>7}{p:>10.3f}{lo:>10.3f}"
              f"{hi:>10.3f}{lo - p:>11.3f}")

    nu, nd = len(d["up"]["pool"]), len(d["down"]["pool"])
    up_drag = st.mean(d["up"]["pool"]) - st.mean(d["up"]["lo"])
    dn_gain = st.mean(d["down"]["lo"]) - st.mean(d["down"]["pool"])
    print(f"\n오른 날 따라가는 비율 {st.mean(d['up']['lo'])/st.mean(d['up']['pool']):.2f}"
          f"  /  내린 날 맞는 비율 {st.mean(d['down']['lo'])/st.mean(d['down']['pool']):.2f}")
    print(f"총 엣지 {edge_left(nu, nd, up_drag, dn_gain):+.0f}%p "
          f"(오른 날 {-up_drag*nu:+.0f}, 내린 날 {dn_gain*nd:+.0f})")

    be = breakeven_ratio(up_drag, dn_gain)
    print(f"\n손익분기 오른날/내린날 = {be:.3f}  (실제 {nu/nd:.3f})")
    print(f"=> 오른 날이 내린 날보다 {(be-1)*100:.0f}% 이상 많아지면 엣지가 0 이다.")
    print("   그때 이 전략은 손해를 보는 게 아니라 시장에 뒤처진다 - 둘은 다르다.")

    print("\n=== 3) 몇 종목에 의존하나 ===")
    total = sum(d["contrib"].values())
    print(f"총 초과수익 {total:+.1f}%p")
    for c, v in d["contrib"].most_common(5):
        print(f"  {names.get(c, c):<18}{v:>7.1f}%p ({v/total*100:>3.0f}%)")
    for n in (1, 2, 3, 5):
        print(f"  상위 {n}종목 제외 -> {drop_top(d['contrib'], n)*100:.0f}% 남음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
