"""analyze_extremes.py + alert.py 검증.

(2026-09-17 신설) 이 파일에서 틀리면 결과가 좋아 보이는 방향으로 틀린다 -
가장 위험한 실패 방식이다.

  1) 평가MDD 는 보유 중 평가손실을 포함해야 한다. 청산된 거래만 세면 매도에
     수익률 조건이 걸린 탓에 낙폭이 0.0% 로 나온다. 실제로 그 착각이 한 번
     났고, 그래서 두 가지 MDD 를 따로 낸다.
  2) '기본이 보유' 가 지켜져야 한다. 조건이 안 맞으면 계속 들고 있어야 하고,
     현금 구간에서는 평가금액이 변하지 않아야 한다.
  3) 손실 중에는 팔지 않아야 한다 (목표 수익률 조건).
  4) 유리한 방향은 학습 구간에서만 정해야 한다.
  5) 알림은 검증된 것과 아닌 것을 섞어 보내면 안 된다.

실행:
  python tests/test_analyze_extremes.py
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import alert as AL  # noqa: E402
import analyze_extremes as X  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# ------------------------------------------------------- MDD 두 가지
check("0) 평가MDD: 1 -> 1.2 -> 0.9 면 -25%",
      abs(X.mdd_from_curve([1.0, 1.2, 0.9]) + 25.0) < 1e-9,
      f"{X.mdd_from_curve([1.0, 1.2, 0.9])}")
check("0b) 평가MDD: 계속 오르면 0", X.mdd_from_curve([1.0, 1.1, 1.2]) == 0.0)
check("0c) 거래MDD: +10% 뒤 -20% 면 -20%",
      abs(X.mdd_from_trades([10, -20]) + 20.0) < 1e-9)
# 핵심: 전부 플러스인 거래 목록은 거래MDD 가 0 이다. 그래서 착각이 난다.
check("0d) 거래가 전부 플러스면 거래MDD 는 0 - 이게 착각의 원인",
      X.mdd_from_trades([5, 5, 5]) == 0.0)

# ------------------------------------------- 평소 보유 + AND 조건 매매
DAYS = [f"T{i:03d}" for i in range(120)]
IDX = {d: i for i, d in enumerate(DAYS)}

# 가격: 매일 +1% 로 오른다고 두고, seg 는 보유일수 x 1% 를 돌려준다.
# (수수료는 별도 인자로 받으므로 여기서는 순수 수익만)
def seg(a, b):
    return (IDX[b] - IDX[a]) * 1.0 - X.FEE


def seg_nf(a, b):
    return (IDX[b] - IDX[a]) * 1.0


# 신호 하나. T010 에서만 '유리', T050 에서만 '불리'.
SIG = {"기관": {d: 0.5 for d in DAYS}}
SIG["기관"]["T010"] = 0.0      # 유리 (낮을 때가 유리한 방향)
SIG["기관"]["T050"] = 1.0      # 불리
DIRS = {"기관": -1.0}          # 낮을 때 유리
CUTS = {"기관": {0.2: 0.0, 0.8: 1.0}}

tds, curve, eq = X.hold_simulate(DAYS, SIG, ("기관",), DIRS, CUTS,
                                 0.2, 0.0, seg, seg_nf)
check("1) 조건이 맞는 날에 진입하고 불리한 날에 청산한다",
      len(tds) == 1 and tds[0][0] == "T010" and tds[0][1] == "T050",
      str(tds))
check("1b) 보유일수가 진입~청산 거래일수와 같다",
      tds and tds[0][2] == 40, f"{tds[0][2] if tds else None}일")
check("1c) 평가금액 곡선의 길이가 날짜 수와 같다",
      len(curve) == len(DAYS), f"{len(curve)} vs {len(DAYS)}")
check("1d) 진입 전 구간은 평가금액이 1.0 으로 고정 (현금)",
      all(abs(v - 1.0) < 1e-12 for v in curve[:10]),
      f"{curve[:3]}")
check("1e) 청산 후 구간은 평가금액이 변하지 않는다 (현금)",
      len(set(round(v, 12) for v in curve[55:])) == 1,
      f"{curve[55]} ~ {curve[-1]}")

# 목표 수익률: 손실 중에는 팔지 않아야 한다
def seg_down(a, b):
    return (IDX[b] - IDX[a]) * -1.0 - X.FEE


def seg_down_nf(a, b):
    return (IDX[b] - IDX[a]) * -1.0


tds_d, curve_d, _eq = X.hold_simulate(DAYS, SIG, ("기관",), DIRS, CUTS,
                                      0.2, 5.0, seg_down, seg_down_nf)
check("2) 손실 중에는 좋은 날이 와도 팔지 않는다 (목표 5%)",
      len(tds_d) == 1 and tds_d[0][1] == DAYS[-1],
      f"청산일 {tds_d[0][1] if tds_d else None} (마지막 날이어야 함)")
check("2b) 그래서 보유기간이 길어진다 (하락장의 실패 방식)",
      tds_d and tds_d[0][2] > 100, f"{tds_d[0][2] if tds_d else None}일")
# 여기서는 마지막에 강제청산되어 손실이 실현되므로 두 MDD 가 같아진다.
# '거래MDD 가 0 으로 보이는' 착각은 청산된 거래가 전부 플러스일 때 생긴다
# (위 0d 에서 따로 확인). 여기서 볼 것은 '위험을 피한 게 아니라 오래
# 들고 있었다' 는 쪽이다.
check("2c) 평가MDD 가 큰 손실을 잡아낸다 (버티는 동안의 위험)",
      X.mdd_from_curve(curve_d) < -50.0,
      f"평가MDD {X.mdd_from_curve(curve_d):.1f}%")
check("2d) 목표 조건 때문에 창의 대부분을 들고 있었다",
      tds_d and tds_d[0][2] / len(DAYS) > 0.8,
      f"{tds_d[0][2]}/{len(DAYS)}일")

# 목표를 0 으로 내리면 손실에도 팔아야 한다
tds_d0, _c, _e = X.hold_simulate(DAYS, SIG, ("기관",), DIRS, CUTS,
                                 0.2, -999.0, seg_down, seg_down_nf)
check("2e) 목표를 없애면 손실에도 청산한다 (2번이 헛돌지 않음)",
      tds_d0 and tds_d0[0][1] == "T050", str(tds_d0[:1]))

# AND: 두 지표 중 하나만 유리하면 진입하지 않아야 한다
SIG2 = {"기관": dict(SIG["기관"]), "외국인": {d: 0.5 for d in DAYS}}
DIRS2 = {"기관": -1.0, "외국인": -1.0}
CUTS2 = {"기관": {0.2: 0.0, 0.8: 1.0}, "외국인": {0.2: 0.0, 0.8: 1.0}}
tds2, _c2, _e2 = X.hold_simulate(DAYS, SIG2, ("기관", "외국인"), DIRS2,
                                 CUTS2, 0.2, 0.0, seg, seg_nf)
check("3) AND 조건: 하나만 유리하면 진입하지 않는다", tds2 == [], str(tds2))
SIG2["외국인"]["T010"] = 0.0
tds3, _c3, _e3 = X.hold_simulate(DAYS, SIG2, ("기관", "외국인"), DIRS2,
                                 CUTS2, 0.2, 0.0, seg, seg_nf)
check("3b) 둘 다 유리해지면 진입한다 (3번이 헛돌지 않음)",
      len(tds3) == 1 and tds3[0][0] == "T010", str(tds3))

# 기준선
bc = X.baseline_curve(DAYS, seg, seg_nf)
check("4) 기준선은 항상 보유다 (평가금액이 계속 오른다)",
      bc[-1] > bc[0] and all(b >= 1.0 for b in bc[:5]),
      f"{bc[0]:.3f} -> {bc[-1]:.3f}")
check("4b) 기준선도 20일마다 수수료를 낸다 (단순 복리보다 낮다)",
      bc[-1] < (1.01 ** 119), f"{bc[-1]:.4f} vs {1.01**119:.4f}")

# 방향 학습
OUT = {d: (1.0 if SIG["기관"][d] < 0.25 else -1.0) for d in DAYS}
dirs = X.fit_directions(DAYS, {"기관": SIG["기관"]}, OUT)
check("5) 낮을 때 결과가 좋으면 방향이 -1 로 정해진다",
      dirs["기관"] == -1.0, str(dirs))
OUT_FLIP = {d: -v for d, v in OUT.items()}
check("5b) 결과 부호를 뒤집으면 방향도 뒤집힌다 (5번이 헛돌지 않음)",
      X.fit_directions(DAYS, {"기관": SIG["기관"]}, OUT_FLIP)["기관"] == 1.0)

# ------------------------------------------------------- 극단 진단
vals = {d: float(i) for i, d in enumerate(DAYS)}
out = {d: float(i) for i, d in enumerate(DAYS)}     # 완전 단조
dec = X.decile_table(DAYS, vals, out)
check("6) 십분위가 10칸이고 단조 관계면 칸 평균이 증가한다",
      dec and len(dec) == 10
      and all(dec[i][1] < dec[i + 1][1] for i in range(9)),
      str([round(m, 1) for _n, m in dec] if dec else None))
tg = X.tail_gap(DAYS, vals, out, 0.10)
check("6b) 꼬리 차이가 상위-하위 이고 표본수를 같이 낸다",
      tg and tg["gap"] > 0 and tg["n"] == 12, str(tg))
check("6c) 독립 표본 수를 (표본/20) 로 보고한다 - 겹치는 회차이므로",
      tg and tg["n_independent"] == max(1, tg["n"] // X.REBAL),
      f"{tg['n_independent']}")
check("6d) 표본이 100개 미만이면 None (억지로 계산하지 않는다)",
      X.tail_gap(DAYS[:50], vals, out, 0.1) is None)

# --------------------------------------------------------- 알림
dates = [f"2026{i:04d}" for i in range(1, 61)]
AL.ANCHOR = dates[0]
due0, rem0 = AL.rebalance_due(dates, dates[0])
check("7) 기준일은 리밸런스일이다", due0 and rem0 == 0, f"{due0} {rem0}")
check("7b) 기준일 + 20거래일도 리밸런스일",
      AL.rebalance_due(dates, dates[20])[0])
check("7c) 그 사이는 리밸런스일이 아니고 남은 일수를 알려준다",
      not AL.rebalance_due(dates, dates[15])[0]
      and AL.rebalance_due(dates, dates[15])[1] == 5,
      str(AL.rebalance_due(dates, dates[15])))
check("7d) 패널에 없는 날짜는 False", not AL.rebalance_due(dates, "19990101")[0])

src_al = (REPO_ROOT / "alert.py").read_text(encoding="utf-8")
check("8) 알림이 검증된 것과 아닌 것을 구분해 적는다",
      "[검증된 전략]" in src_al and "[검증 안 된 신호]" in src_al)
check("8b) 검증 안 된 신호에 '매매 지시가 아니다' 라고 적는다",
      "매매 지시가 아닙니다" in src_al)
check("8c) 대조군 탈락 사실을 메일 본문에 적는다", "20.0%" in src_al)
check("8d) 주문이 자동으로 나가지 않는다는 것을 본문에 적는다",
      "주문은 자동으로 나가지 않습니다" in src_al)
# 본문 문구에 'api_client.py 에 주문 함수가 없습니다' 가 들어가므로 단순
# 부분문자열 검사는 쓸 수 없다. 실제 '사용' 만 본다.
for banned in ("place_order", "import api_client", "import auth",
               "api_client.get", "api_client.place"):
    check(f"9) alert.py 가 주문/계좌 API 를 쓰지 않는다 ({banned})",
          banned not in src_al)

src_x = (REPO_ROOT / "analyze_extremes.py").read_text(encoding="utf-8")
check("10) 주의문에 두 MDD 를 같이 보라고 적혀 있다",
      "거래MDD" in X.CAUTION_HOLD and "평가MDD" in X.CAUTION_HOLD)
check("10b) 주의문에 밀어놓기 중간값과 기준선을 비교하라고 적혀 있다",
      "기준선과 비교" in X.CAUTION_HOLD)
check("10c) 주의문에 극단의 표본 한계가 적혀 있다",
      "독립 표본은 1개 미만" in X.CAUTION_DEC)
check("10d) 실행 결과가 문서에 숫자로 남아 있다",
      all(s in src_x for s in ("+129.4", "+112.7", "20.0%", "416", "-8.2")))
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"11) analyze_extremes 에 주문/통신 코드가 없다 ({banned})",
          banned not in src_x)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
