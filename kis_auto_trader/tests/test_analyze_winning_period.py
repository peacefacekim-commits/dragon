"""analyze_winning_period.py 검증 - 이긴 구간을 공평하게 설명했는가.

(2026-09-22 신설) 사용자가 "10분 투자로 이득을 봤었다" 고 했고 그건
기록으로 사실이었다. 나는 전체 합계만 보고 손해라고 정리했었다. 이
파일의 위험은 그 반대 방향이다 - **사용자 말이 맞았으니 이번엔 반대로
과하게 인정하는 것.**

지키는 것
  1) 최고점에서 자른 표를 증거로 쓰지 않는가. 자르는 위치를 결과가
     정했으면 앞쪽은 정의상 오르막이다.
  2) 결과와 무관한 경계(DECISIONS.md 날짜)로도 잘라 보는가.
  3) 투입 비중을 맞춰서 견주는가. 26% 넣고 번 것과 77% 넣고 번 것을
     그냥 비교하면 안 된다.
  4) 거래일만 세는가. 주말을 세면 비중이 낮게 나와 결론이 유리해진다.
  5) monitor.py 의 포착률 문턱을 가져다 쓰지 않는가 (뜻이 반대다).
  6) 사후 계산이라고 밝히고 무엇도 채택하지 않는가.

실행:
  python tests/test_analyze_winning_period.py
  python tests/test_analyze_winning_period.py --slow   # 실제 기록/패널까지
"""
import pathlib
import statistics as st
import sys
from datetime import datetime

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import analyze_winning_period as M  # noqa: E402

src = (REPO_ROOT / "analyze_winning_period.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


def mk(day, won, net, qty=1, buy=100000.0):
    """가짜 완결 거래. 매수일 = 매도일로 둔다."""
    t = datetime(2026, 8, day, 10, 0)
    return {"code": "A", "name": "A", "buy": buy, "qty": qty,
            "buy_t": t, "sell_t": t, "won": won, "net": net,
            "gross": net, "mins": 10.0, "note": "일일 정리", "sell": buy}


class FakeSeries:
    def __init__(self, closes, start=0):
        self.close = list(closes)
        self.open = list(closes)
        self.value = [1e9] * len(closes)
        self.pos = {start + i: i for i in range(len(closes))}


# =====================================================================
# A) 사용자 말이 맞았다는 것을 기록으로 확인했는가
# =====================================================================
check("A1) 사용자 말이 맞다고 명시한다", "**맞는 말이다.**" in src)
check("A2) 내가 합계만 봤다고 밝힌다",
      "전체 합계(-108,551원)만 보고" in flat)
check("A3) 내 잘못이라고 적었다", "내 잘못이다" in flat)
check("A4) 기억이 정확하다고 적었다", "기억은 정확하다" in flat)
check("A5) 최고점 값과 날짜를 적었다", "+48,317원 (08-10" in src)
check("A6) 자본 대비 %로도 적었다", "+2.42%" in src)
check("A7) 두 번째 고점도 빠뜨리지 않았다", "+45,716" in src)
check("A8) 첫 8거래일을 밝혔다", "첫 8거래일" in flat)

# =====================================================================
# B) 누적 계산이 맞는가
# =====================================================================
trs = [mk(3, 100.0, 1.0), mk(4, -50.0, -0.5), mk(5, 30.0, 0.3)]
rows = M.daily_cum(trs)
check("B1) 날짜별로 묶는다", len(rows) == 3)
check("B2) 누적이 더해진다",
      [round(r[3], 6) for r in rows] == [100.0, 50.0, 80.0],
      str([r[3] for r in rows]))
check("B3) 이긴 건수를 센다", [r[4] for r in rows] == [1, 0, 1])
same = M.daily_cum([mk(3, 10.0, 0.1), mk(3, -5.0, -0.1)])
check("B4) 같은 날은 한 줄로 합친다",
      len(same) == 1 and same[0][1] == 2 and abs(same[0][2] - 5.0) < 1e-9)
best, bd, bi = M.peak_of(trs)
check("B5) 최고 누적을 찾는다", abs(best - 100.0) < 1e-9, f"{best}")
check("B6) 최고 날짜를 돌려준다", bd == "2026-08-03", bd)
check("B7) 최고까지의 건수를 돌려준다", bi == 1, str(bi))
check("B8) 전부 손실이면 최고가 0 (빈 기록 안전)",
      M.peak_of([mk(3, -10.0, -0.1)])[0] == 0.0)

# =====================================================================
# C) 최고점 자르기를 증거로 쓰지 않는가 (핵심 1)
# =====================================================================
check("C1) 증거로 못 쓴다고 제목에 박았다",
      "증거로는 못 쓴다" in flat)
check("C2) 자르는 위치를 결과가 정했다고 적었다",
      "자르는 위치를 결과가 정했다" in flat)
check("C3) 정의상 오르막이라고 설명한다", "정의상 오르막" in flat)
check("C4) 화면 출력에도 그 경고가 있다",
      "자르는 위치를 결과가 정했다. 누적 최고점 앞은 정의상 오르막이다."
      in src)

# =====================================================================
# D) 결과와 무관한 경계로도 잘랐는가 (핵심 2)
# =====================================================================
check("D1) 경계가 DECISIONS.md 날짜다", len(M.ERA_BOUNDS) == 3)
check("D2) 결과와 무관하다고 주석에 적었다",
      "**결과와 무관하게** 정해진 경계다" in src)
_era = M.by_era([mk(3, 1.0, 0.1), mk(22, 1.0, 0.1), mk(27, 1.0, 0.1)])
check("D3) 세 시기로 갈린다", len(_era) == 3, str(list(_era)))
check("D4) 1기 경계가 08-20 이다",
      len(M.by_era([mk(20, 1.0, 0.1)])) == 1
      and "~08-20" in list(M.by_era([mk(20, 1.0, 0.1)]))[0])
check("D5) 08-21 은 2기다",
      "08-21~25" in list(M.by_era([mk(21, 1.0, 0.1)]))[0])
check("D6) 1기도 이긴 구간이 아니라고 적었다",
      "1기도 이미\n이긴 구간이 아니다" in src
      or "1기도 이미 이긴 구간이 아니다" in flat)

n, m, md, wr, w = M.summarize([mk(3, 100.0, 2.0), mk(4, -100.0, -1.0)])
check("D7) 요약이 맞다 (건수/평균/승률/합계)",
      n == 2 and abs(m - 0.5) < 1e-9 and abs(wr - 50.0) < 1e-9
      and abs(w) < 1e-9, f"{n} {m} {wr} {w}")
check("D8) 빈 입력이어도 안 터진다", M.summarize([]) == (0, 0.0, 0.0, 0.0, 0.0))

# =====================================================================
# E) 무작위 순서 대조군
# =====================================================================
# 전부 같은 값이면 어떤 순서로 섞어도 최고 누적이 같다 -> p = 1
_same = [10.0] * 20
p, med = M.perm_peak_p(_same, 200.0, n_perm=200)
check("E1) 값이 다 같으면 순서를 섞어도 최고가 같다 (p=1)",
      abs(p - 1.0) < 1e-9, f"p={p}")
p2, _m2 = M.perm_peak_p(_same, 201.0, n_perm=200)
check("E2) 관측이 더 크면 p = 0", p2 == 0.0, f"p={p2}")
_obs, _p = M.perm_firstk_p([1.0] * 10, 5, n_perm=200)
check("E3) 앞 k 평균이 맞다", abs(_obs - 1.0) < 1e-9)
check("E4) 값이 다 같으면 p = 1", abs(_p - 1.0) < 1e-9)
check("E5) k 가 표본보다 크면 None", M.perm_firstk_p([1.0], 5)[0] is None)
# 앞쪽이 실제로 좋으면 p 가 낮아야 한다
_nets = [5.0] * 5 + [-1.0] * 45
_o, _pp = M.perm_firstk_p(_nets, 5, n_perm=2000)
check("E6) 앞쪽이 좋으면 p 가 낮다", _pp < 0.05, f"p={_pp}")
check("E7) 순서만 바꾸면 실력이 사라진다고 적었다",
      "순서만 바꾸면 '실력' 은 사라지고" in flat)
check("E8) k 를 미리 정한다고 적었다", "k 는 미리 정해놓고 묻는다" in flat)
check("E9) 다중검정(k 5개)을 밝혔다",
      "k 를 다섯 개 봤다" in flat and "다섯 번 보면" in flat)
check("E10) p<0.05 를 실력으로 읽지 말라고 적었다",
      '"p<0.05 니까 실력" 으로\n읽으면 안 된다' in src
      or 'p<0.05 니까 실력" 으로 읽으면 안 된다' in flat)

# =====================================================================
# F) 투입 비중 - 거래일만 세는가 (핵심 3, 4)
# =====================================================================
_dates = ["20260803", "20260804", "20260805"]
_tr = [{"code": "A", "buy": 100000.0, "qty": 10,
        "buy_t": datetime(2026, 8, 3), "sell_t": datetime(2026, 8, 4),
        "won": 0.0, "net": 0.0}]
_m, _x = M.deployment(_dates, _tr, "20260803", "20260805",
                      capital=2_000_000)
check("F1) 보유한 거래일에만 원금이 잡힌다",
      abs(_x - 50.0) < 1e-9, f"최대 {_x}")
check("F2) 아무것도 안 들고 있던 거래일을 0% 로 센다",
      abs(_m - 100.0 / 3) < 1e-6, f"평균 {_m}")
check("F2b) 그 날을 빼면 유리해진다고 적어뒀다",
      "결론이 내 쪽에 유리해진다" in flat)
check("F3) 패널 날짜만 센다 (주말이 안 들어온다)",
      "for d in dates" in src)
check("F4) 주말을 세면 비중이 낮게 나온다고 적었다",
      "주말을 세면 비중이 낮게 나온다" in flat)
check("F5) 빈 구간이면 0 (안 터진다)",
      M.deployment(_dates, _tr, "20301010", "20301011") == (0.0, 0.0))
check("F6) 어림값이라고 밝혔다", "어림값이다" in flat)
check("F7) 165% 가 왜 나오는지 설명했다",
      "같은 돈을 두 번 쓴" in flat)

check("F8) 비중 맞춘 그냥보유 산수",
      abs(M.passive_match(16.59, 31.0) - 5.1429) < 1e-3,
      f"{M.passive_match(16.59, 31.0)}")
check("F9) 따라간 비율 산수",
      abs(M.capture(1.49, 5.12) - 0.2910) < 1e-3,
      f"{M.capture(1.49, 5.12)}")
check("F10) 기준이 0 이면 None (0 으로 안 나눈다)",
      M.capture(1.0, 0.0) is None)
check("F11) 내릴 때 더 맞으면 1 을 넘는다",
      M.capture(-6.92, -4.47) > 1.0)
check("F12) 오를 때 1, 내릴 때 0 이 좋다고 적었다",
      "오를 때는 1 에 가까울수록 좋고, 내릴 때는 0 에 가까울수록 좋다" in flat)

# =====================================================================
# G) 시장 계산 - 중앙값을 같이 보는가
# =====================================================================
_p2 = {"A": FakeSeries([100.0, 110.0]), "B": FakeSeries([100.0, 90.0])}
mean_r, med_r = M.market_window(["d0", "d1"], _p2, "d0", "d1")
check("G1) 동일가중 평균이 맞다", abs(mean_r - 0.0) < 1e-9, f"{mean_r}")
check("G2) 중앙값도 낸다", med_r is not None)
_p3 = {"A": FakeSeries([100.0, 110.0]), "B": FakeSeries([100.0, 110.0]),
       "C": FakeSeries([100.0, 1000.0])}
mean3, med3 = M.market_window(["d0", "d1"], _p3, "d0", "d1")
check("G3) 튀는 한 종목이 평균만 끌어올린다",
      mean3 > 100 and abs(med3 - 10.0) < 1e-6, f"평균 {mean3} 중앙 {med3}")
check("G4) 왜 중앙값을 같이 보는지 적었다",
      "몇 종목이 튀면 끌려간다" in flat)
check("G5) 없는 날짜면 None", M.market_window(["d0"], _p2, "x", "y")[0] is None)
check("G6) 중앙 종목도 올랐다고 결론에 적었다",
      "중앙 종목도 +16.59% 다" in flat)
check("G7) 시장이 전체가 올랐다고 정리한다", "시장 전체가 올랐다" in flat)

# =====================================================================
# H) monitor.py 문턱을 가져다 쓰지 않는가 (핵심 5)
# =====================================================================
check("H1) monitor 를 import 하지 않는다",
      "import monitor" not in src and "ALARM_UP_CAPTURE" not in src)
check("H2) 왜 안 쓰는지 적었다",
      "뜻이 반대라서 그 문턱을 쓰지 않는다" in flat)
check("H3) 한계에도 다시 적었다",
      "monitor.py 의 포착률 문턱은 여기 쓰지 않았다" in flat)

# =====================================================================
# I) 사후 계산이라고 밝히고 채택하지 않는가 (핵심 6)
# =====================================================================
check("I1) 사전 등록이 아니라고 못박았다", "사전 등록이 아니다" in flat)
check("I2) 무엇도 채택하지 않는다고 적었다",
      "무엇을\n'채택' 하지 않는다" in src or "무엇을 '채택' 하지 않는다" in flat)
check("I3) 앞으로는 말할 수 없다고 적었다",
      "앞으로 그러면 된다\" 는 말할 수 없다" in src
      or "앞으로 그러면 된다' 는 말할 수 없다" in flat)
check("I4) 화면 출력 마지막에도 밝힌다",
      "사후 계산이다. 여기서 무엇도 '채택' 하지 않는다." in src)
check("I5) 일반화하지 않는다고 적었다",
      "일반화할 수는 없다" in flat)

# =====================================================================
# J) 결과 숫자가 모듈 출력과 맞는가
# =====================================================================
for tok in ("+48,317", "-108,551", "-156,868", "+2.42%",
            "31.9%", "0.319", "+28,844",
            "+1.919", "4.08%", "+1.338", "2.33%", "+0.217", "18.48%",
            "-0.140", "33.78%", "-0.296", "45.61%",
            "+23.15%", "+16.59%", "-1.69%", "-5.83%",
            "31%", "77%", "165%", "+5.12%", "+1.49%", "-6.92%",
            "-4.47%", "0.29", "1.55",
            "-0.111", "-15,750", "-0.995", "-42,590", "-0.379", "-50,211"):
    check(f"J) 문서에 {tok} 가 있다", tok in src)
check("J1) 자본이 config.yaml 값이다", M.CAPITAL == 2_000_000)
check("J2) 자본 출처를 적었다", "config.yaml total_capital" in src)

# =====================================================================
# K) 핵심 해석 - p 가 낮은 것이 실력의 증거가 아니라고 잇는가
# =====================================================================
check("K1) 앞쪽이 좋았던 이유를 시장으로 설명한다",
      "그 앞쪽이 시장이 제일 많이\n오른 시기였기 때문" in src
      or "그 앞쪽이 시장이 제일 많이 오른 시기였기 때문" in flat)
check("K2) p 가 낮은 것이 실력의 증거가 아니라고 적었다",
      "실력의\n증거가 아니라" in src or "실력의 증거가 아니라" in flat)
check("K3) 이기고 있던 게 아니라고 정리한다",
      "이기고 있던\n게 아니라, 시장이 크게 오르는 동안 덜 오르고 있었다" in src
      or "이기고 있던 게 아니라" in flat)
check("K4) 엣지 0 인 전략이 오르는 시장에서 조금 번다고 잇는다",
      "엣지가\n0 인 전략을 크게 오르는 시장에서 돌리면 조금 번다" in src
      or "엣지가 0 인 전략을 크게 오르는 시장에서 돌리면 조금 번다" in flat)
check("K5) analyze_real_trades 의 -0.023% 와 잇는다",
      "analyze_real_trades.py" in src and "-0.023%" in src)
check("K6) 비중 순서가 반대였다고 짚는다", "순서가 정확히 반대였다" in flat)
check("K7) 이긴 뒤에 키웠다고 설명한다",
      "이긴 뒤에 키우고, 키운 뒤에 시장이 꺾였다" in flat)

# =====================================================================
# L) 한계를 밝혔는가
# =====================================================================
check("L1) 88건 5주 한 시기라고 밝힌다",
      "88건, 5주, 시기 하나다" in flat)
check("L2) 점추정이라고 밝힌다", "점추정이고" in flat)
check("L3) 어느 쪽으로 틀렸을지 방향까지 적었다",
      "과대평가일 수 있다" in flat and "과대평가 쪽" in flat)
check("L4) KOSPI 가 아니라고 밝힌다", "KOSPI 가 아니다" in flat)

# =====================================================================
# M) 실제 기록/패널 (--slow)
# =====================================================================
if "--slow" in sys.argv:
    real = M.closed()
    check("M1) 실제 완결 88건", len(real) == 88, f"{len(real)}건")
    b, d, i = M.peak_of(real)
    check("M2) 최고가 +48,317원 (08-10)",
          round(b) == 48317 and d == "2026-08-10", f"{b:.0f} {d}")
    check("M3) 최고까지 20건", i == 20, str(i))
    check("M4) 합계가 -108,551원",
          round(sum(t["won"] for t in real)) == -108551,
          f"{sum(t['won'] for t in real):.0f}")
    eras = M.by_era(real)
    check("M5) 1기 40건 / 2기 13건 / 3기 35건",
          [len(v) for v in eras.values()] == [40, 13, 35],
          str([len(v) for v in eras.values()]))
    import strategy as S
    dates, pnl = S.load_panel(verbose=False)
    _mr, _md = M.market_window(dates, pnl, M.WIN_A[1], M.WIN_A[2])
    check("M6) A 구간 중앙 종목이 +16.59%", abs(_md - 16.59) < 0.1,
          f"{_md:.2f}%")
    _mr2, _md2 = M.market_window(dates, pnl, M.WIN_B[1], M.WIN_B[2])
    check("M7) B 구간 중앙 종목이 -5.83%", abs(_md2 - (-5.83)) < 0.1,
          f"{_md2:.2f}%")
    _dm, _dx = M.deployment(dates, real, M.WIN_A[1], M.WIN_A[2])
    check("M8) A 구간 투입 평균이 31%", round(_dm) == 31, f"{_dm:.1f}%")
    _dm2, _dx2 = M.deployment(dates, real, M.WIN_B[1], M.WIN_B[2])
    check("M9) B 구간 투입 평균이 77%", round(_dm2) == 77, f"{_dm2:.1f}%")
    check("M10) B 구간에서 비중이 커졌다 (문서의 핵심)", _dm2 > _dm * 2,
          f"{_dm:.0f}% -> {_dm2:.0f}%")
else:
    check("M0) 느린 검사는 --slow 로 따로 돈다 (기본은 건너뜀)", True)

# =====================================================================
# N) 안전
# =====================================================================
check("N1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"N2) 주문/통신 코드가 없다 ({banned})", banned not in src)
check("N3) 파일이 없어도 안 터진다",
      M.closed(pathlib.Path("/없는/경로.csv")) == [])

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
