"""매일 전략 건강검진 - 거래하지 않고 지켜보는 자동화.

(2026-09-22 신설) 사용자: "내 목표는 Ai가 자동적으로 투자를 하는 이점을
누렸으면 해. 사람은 하기 어려운 꾸준히 장 상황을 확인한다던가 하는 거"

그리고 정당한 지적을 같이 했다: "네가 추천해준것도 결국 사람이 하는 게
더 나은 거였으니." 맞는 말이다. 지금 전략은 1년에 주문일이 2번이다.
달력 알람만 있으면 사람이 그냥 한다.

===========================================================================
자동화 이점을 네 갈래로 갈라야 한다
===========================================================================
(A) 자동화가 확실히 이기는데 **안 보이는** 것 - 선정
    1,813종목의 60일 변동성을 매일 계산해 순위를 매기는 일. 사람은
    못 한다. 이게 63.5%p 를 만든다 (analyze_styles). 주문일이 2번뿐이라
    눈에 안 보이지만, 그 2번의 결정을 만드는 계산이 전부 여기 있다.

(B) 자동화가 확실히 이기는데 **안 하는** 것 - 규율
    이 저장소가 잰 '사람이 하고 싶어지는 개입' 은 전부 졌다.
      오르면 판다        12/12 짐            [analyze_original]
      손절               낙폭도 못 줄였다     [analyze_stops]
      나쁜 날 쉰다       23가지 전부 짐       [analyze_timing]
    사람은 반드시 개입한다. 기계는 안 한다. 이건 '무엇을 하는가' 가
    아니라 '무엇을 안 하는가' 로 나타나는 이점이다.

(C) 자동화 이점처럼 보이는데 **데이터가 아니라고 한** 것
    '계속 보고 반응하기'. 타이밍 23가지, 지표 14개, 이벤트 교체, 짧은
    주기 전부 탈락했다. 신호가 없어서가 아니라 **수수료** 때문이다.
    더 봐도 더 벌리지 않고, 더 거래하면 더 잃는다 (analyze_knobs --fast:
    1일 주기가 백테스트 25.1% 인데 슬리피지 0.08% 에서 뒤집힌다).

(D) 아직 안 재본 유일한 자리 - 장중
    10분봉을 지금 모으는 중이다. '계속 보기' 가 값을 낼 수 있는 마지막
    영역이고, 채점 기준은 analyze_min10.py 에 미리 박아뒀다.

===========================================================================
이 파일이 하는 일 - (E) 거래 없이 감시하기
===========================================================================
위 네 갈래에 하나가 빠져 있다. **거래하지 않는 감시** 다. 수수료가
0 이므로 (C) 의 함정에 걸리지 않는다. 그리고 사람이 매일 하기 제일
어려운 일이다.

무엇을 보는가: analyze_why.py 가 왜 저변동이 작동하는지 분해해서
얻은 숫자들이다. 저변동은 종목을 잘 맞히는 게 아니라 **낮은 베타 +
비대칭** 으로 번다.
    오르는 날 풀의 37% 만 따라간다  (up_capture)
    내리는 날 풀의 23% 만 맞는다    (down_capture)
    => 이 비대칭이 엣지의 전부다.

그래서 엣지가 죽는 조건이 계산된다.
    손익분기 상승일/하락일 비율 = 1.318
    실제 2021~2026 = 1.061 (592/558)
    오른 날이 내린 날보다 32% 넘게 많아지면 엣지가 0 이 된다.

이건 '예측' 이 아니라 '지금 여전히 작동 중인가' 다. 예측은 이 저장소가
23가지 시도해서 전부 실패했다. 감시는 다른 일이다.

===========================================================================
경보 기준 - 미리 박아둔다
===========================================================================
  상승일/하락일 비율  1.318 을 넘으면 경보   (analyze_why 손익분기)
  하락일 포착률       0.30 을 넘으면 경보   (기준 0.23, 여유 30%)
  상승일 추종률       0.50 을 넘으면 경보   (기준 0.37, 여유 35%)

여유를 둔 이유: 분기 한두 개로 흔들리는 값이라 딱 기준선에 걸면 계속
울린다. 여유 폭도 결과를 보고 고치지 않는다.

경보가 울린다고 바로 그만두라는 뜻이 아니다. **왜 우는지 보라** 는
뜻이다. 상승장이 길게 오면 1.318 은 정상적으로 넘어간다 (그때는 저변동이
뒤처지는 것이 당연하고, 그게 전략의 설계다).

===========================================================================
첫 실행 결과 (2026-09-22) - 경보가 실제로 울린 구간이 있었다
===========================================================================
  구간              상승/하락  하락포착  상승추종  오른날  내린날  남은엣지%p
  전체 (2021~)        1.061    0.229    0.369    593    559     +115.7
  최근 120일          1.052    0.104    0.250     61     58      +12.4
  그 앞 120일         1.727    0.423    0.460     76     44      -14.5

전체 구간 숫자가 analyze_why.py 의 분해값과 맞는다 (하락포착 0.23,
상승추종 0.37, 비율 1.061). 다른 코드로 같은 값이 나오므로 계산이
어긋나지 않았다는 확인이 된다.

**그 앞 120일 구간에서 셋 다 경보였다.**
  상승/하락 1.727 > 1.318   오른 날이 내린 날보다 73% 많았다
  하락포착  0.423 > 0.30    방어가 절반으로 약해졌다
  남은 엣지 -14.5%p         그 구성에서는 엣지가 마이너스다

그 구간에 이 파일이 있었다면 **"지금 전략이 불리한 국면이다"** 를
매일 알려줬을 것이다. 사람이 매일 이 셋을 계산할 방법은 없다. 이게
사용자가 말한 '꾸준히 장 상황을 확인' 에 해당하는 일이다.

그리고 최근 120일은 정상으로 돌아왔다 (1.052 / 0.104 / 0.250).
경보는 '그만두라' 가 아니라 '지금 어떤 국면인지 알라' 다.

===========================================================================
읽는 법
===========================================================================
0) **이건 예측이 아니다.** 예측은 이 저장소가 23가지 시도해서 전부
   실패했다. 이 파일은 '앞으로 어떻게 될까' 를 말하지 않는다. '지금
   어떤 국면이고 전략의 전제가 아직 성립하나' 만 말한다. 둘은 다른
   일이고, 뒤쪽은 수수료가 들지 않는다.
1) 이 파일은 주문을 내지 않는다. 계산하고 화면에 찍는다.
2) 최근 창(기본 120거래일)으로 본다. 전체 기간으로 보면 6년 평균에
   묻혀서 변화가 안 보인다.
3) 숫자가 기준을 넘어도 그게 '틀렸다' 는 뜻은 아니다. 표본이 작으면
   많이 흔들린다. 그래서 표본 수도 같이 찍는다.

실행:
  python monitor.py            # 최근 120거래일로 건강검진
  python monitor.py --days 60  # 창 길이를 바꿔서

이름을 한글(감시.py)로 두려 했으나 .bat 내용은 ASCII 만 써야
하고(한글은 CP949 에서 깨진다) bat 에서 이 파일을 부르므로
파일명도 ASCII 로 뒀다.
"""
import argparse
import pathlib
import statistics as st
import sys

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
import analyze_event_rebal as E  # noqa: E402
import analyze_why as W  # noqa: E402
import strategy as S  # noqa: E402

BASE_DI = 250
PICK = 10
WINDOW = 120

# 경보 기준. 결과를 보고 고치지 않는다.
ALARM_UD_RATIO = W.breakeven_ratio()      # 1.318 (analyze_why 손익분기)
ALARM_DOWN_CAPTURE = 0.30                 # 기준 0.23 + 여유
ALARM_UP_CAPTURE = 0.50                   # 기준 0.37 + 여유
MIN_SAMPLE = 30                           # 이보다 적으면 판정하지 않는다


def window_split(dates, panel, order, lo, hi, pick=PICK):
    """[lo, hi) 구간에서 풀과 저변동 10의 하루 수익을 날 부호로 가른다.

    analyze_why.daily_split 과 같은 계산인데 구간을 잘라서 본다.
    '지금도 작동 중인가' 를 보려면 최근 창만 봐야 한다.
    """
    up = {"pool": [], "lo": []}
    down = {"pool": [], "lo": []}
    for di in range(max(lo, BASE_DI), min(hi, len(dates) - 1)):
        if di not in order:
            continue
        lst = order[di]
        cand = lst[:pick]
        pool_r, lo_r = [], []
        for c in lst:
            a = E.price(panel, c, di, "close")
            b = E.price(panel, c, di + 1, "close")
            if not a or not b:
                continue
            r = (b / a - 1) * 100
            pool_r.append(r)
            if c in cand:
                lo_r.append(r)
        if not pool_r or not lo_r:
            continue
        pm, lm = st.mean(pool_r), st.mean(lo_r)
        (up if pm > 0 else down)["pool"].append(pm)
        (up if pm > 0 else down)["lo"].append(lm)
    return up, down


def capture(group):
    """풀이 움직인 것의 몇 %를 따라갔나. 표본이 없으면 None."""
    if not group["pool"] or not group["lo"]:
        return None
    pm = st.mean(group["pool"])
    if not pm:
        return None
    return st.mean(group["lo"]) / pm


def ud_ratio(up, down):
    """상승일/하락일 비율. 하락일이 0 이면 무한대."""
    nd = len(down["pool"])
    if nd == 0:
        return float("inf")
    return len(up["pool"]) / nd


def verdict(ratio, dn_cap, up_cap, n_up, n_down):
    """경보 목록. 빈 목록이면 이상 없음.

    표본이 적으면 판정하지 않는다 - 흔들리는 값으로 경보를 울리면
    쓸 수 없는 알림이 된다.
    """
    out = []
    if n_up + n_down < MIN_SAMPLE:
        return ["표본 부족 - 판정하지 않음"]
    if ratio > ALARM_UD_RATIO:
        out.append(f"상승일/하락일 {ratio:.3f} > {ALARM_UD_RATIO:.3f} "
                   f"(엣지 상쇄 구간)")
    if dn_cap is not None and dn_cap > ALARM_DOWN_CAPTURE:
        out.append(f"하락일 포착률 {dn_cap:.3f} > {ALARM_DOWN_CAPTURE:.2f} "
                   f"(방어가 약해졌다)")
    if up_cap is not None and up_cap > ALARM_UP_CAPTURE:
        out.append(f"상승일 추종률 {up_cap:.3f} > {ALARM_UP_CAPTURE:.2f} "
                   f"(저변동 성질이 흐려졌다)")
    return out


def net_edge_left(up, down):
    """그 창의 오른날/내린날 구성에서 남는 총 엣지(%p)."""
    return W.edge_left(len(up["pool"]), len(down["pool"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="전략 건강검진 (주문 없음)")
    ap.add_argument("--days", type=int, default=WINDOW,
                    help="최근 몇 거래일로 볼까 (기본 120)")
    args = ap.parse_args(argv)

    dates, panel = S.load_panel()
    print("순위 계산 중...", flush=True)
    order, _rank = E.daily_ranks(dates, panel, BASE_DI)
    n = len(dates)

    print(f"\n=== 전략 건강검진 ({dates[-1]} 기준) ===")
    print("주문을 내지 않습니다. 지금도 작동 중인가만 봅니다.\n")

    rows = []
    for label, lo, hi in (("전체 (2021~)", BASE_DI, n),
                          (f"최근 {args.days}일", n - args.days, n),
                          (f"그 앞 {args.days}일", n - 2 * args.days,
                           n - args.days)):
        up, down = window_split(dates, panel, order, lo, hi)
        r = ud_ratio(up, down)
        dc, uc = capture(down), capture(up)
        rows.append((label, r, dc, uc, len(up["pool"]), len(down["pool"]),
                     net_edge_left(up, down)))

    print(f"{'구간':<16}{'상승/하락':>10}{'하락포착':>10}{'상승추종':>10}"
          f"{'오른날':>7}{'내린날':>7}{'남은엣지%p':>11}")
    for label, r, dc, uc, nu, nd, edge in rows:
        rs = "inf" if r == float("inf") else f"{r:.3f}"
        print(f"{label:<16}{rs:>10}"
              f"{('-' if dc is None else f'{dc:.3f}'):>10}"
              f"{('-' if uc is None else f'{uc:.3f}'):>10}"
              f"{nu:>7}{nd:>7}{edge:>11.1f}")

    print(f"\n경보 기준 (미리 박아둔 값)")
    print(f"  상승일/하락일 {ALARM_UD_RATIO:.3f} 초과 / "
          f"하락포착 {ALARM_DOWN_CAPTURE:.2f} 초과 / "
          f"상승추종 {ALARM_UP_CAPTURE:.2f} 초과")

    label, r, dc, uc, nu, nd, _e = rows[1]
    alarms = verdict(r, dc, uc, nu, nd)
    print(f"\n[{label}] 판정")
    if not alarms:
        print("  이상 없음 - 세 숫자 모두 기준 안에 있습니다.")
    else:
        for a in alarms:
            print(f"  [!] {a}")
        print("  울린다고 그만두라는 뜻이 아닙니다. 왜 우는지 보십시오.")
        print("  상승장이 길면 1.318 은 정상적으로 넘어갑니다 "
              "(저변동이 뒤처지는 게 설계입니다).")

    # 다음 교체일까지
    print(f"\n[교체] 120거래일 주기. 마지막 패널일 {dates[-1]}")
    picks = order.get(n - 1, [])[:PICK]
    if picks:
        print(f"  지금 순위 상위 {PICK}종목: {', '.join(picks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
