"""analyze_timing.py 검증 - 매매 시늉이 실제로 그 규칙대로 도는지.

(2026-09-17 신설) 이 파일의 결론은 "정방향은 통과했지만 역방향에서 깨졌다"
이고, 그 판정이 매매 시늉의 버그에서 나온 것이면 안 된다. 특히 위험한 곳:

  1) 거래가 겹치면 안 된다. 겹치면 표본 수가 부풀려지고, '거래 하나가
     독립 표본 하나' 라는 이 방식의 유일한 장점이 사라진다.
  2) 진입은 그날 시가, 청산도 그날 시가여야 한다. 신호를 본 날의 종가로
     사면 미래 정보다.
  3) max_hold 는 반드시 걸려야 한다. 안 걸리면 '영원히 보유' 가 섞여서
     전략이 다른 물건이 된다.
  4) invert=True 가 정말로 규칙을 뒤집어야 한다. 안 뒤집히면 '반대 규칙이
     손실' 이라는 비교가 무의미해진다.

합성 데이터로 검증한다 - 정답을 손으로 계산할 수 있어야 하기 때문이다.

실행:
  python tests/test_analyze_timing.py
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import analyze_timing as T  # noqa: E402

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


# ------------------------------------------------------------- 기본 산수
check("0) 누적수익: +10% 두 번이면 +21%",
      abs(T.cumulative([10, 10]) - 21.0) < 1e-9)
check("0b) 최대낙폭: +10% 뒤 -20% 면 -20%",
      abs(T.max_drawdown([10, -20]) + 20.0) < 1e-9)
check("0c) 계속 오르면 최대낙폭 0", T.max_drawdown([1, 2]) == 0.0)

# ----------------------------------------------------------- 매매 시늉
# 점수를 손으로 만든다. 20일 = 날짜 0~19.
#   점수: 0,1,2,...,9 로 오르다가 다시 0..9  (두 번의 골짜기와 봉우리)
DAYS = [f"T{i:02d}" for i in range(20)]
SIG = {d: float(i % 10) for i, d in enumerate(DAYS)}
# 수익률 함수는 '보유일수 x 1%' 로 둔다 - 손으로 검산 가능하게.
IDX = {d: i for i, d in enumerate(DAYS)}


def ret_fn(a, b):
    return (IDX[b] - IDX[a]) * 1.0


tds = T.simulate(DAYS, SIG, low=1.0, high=8.0, max_hold=99, ret_fn=ret_fn)
check("1) 점수가 낮은기준 이하일 때 사고 높은기준 이상일 때 판다",
      len(tds) == 2, f"{len(tds)}거래: {[(t[0], t[1]) for t in tds]}")
if len(tds) == 2:
    check("1b) 첫 거래는 점수 0(T00)에 사서 점수 8(T08)에 판다",
          tds[0][0] == "T00" and tds[0][1] == "T08",
          f"{tds[0][0]} -> {tds[0][1]}")
    check("1c) 두 번째 거래는 점수 0(T10)에 사서 점수 8(T18)에 판다",
          tds[1][0] == "T10" and tds[1][1] == "T18",
          f"{tds[1][0]} -> {tds[1][1]}")
    check("1d) 보유일수와 수익이 손계산과 같다 (8일 x 1% = 8%)",
          tds[0][2] == 8 and abs(tds[0][3] - 8.0) < 1e-9,
          f"{tds[0][2]}일 {tds[0][3]}%")

# 거래가 겹치지 않는지 - 이 방식의 유일한 장점이다
spans = [(IDX[t[0]], IDX[t[1]]) for t in tds]
overlap = any(a2 < b1 for (b1, _e1), (a2, _e2) in zip(spans, spans[1:]))
check("2) 거래가 겹치지 않는다 (겹치면 표본 수가 부풀려진다)",
      not overlap, str(spans))
check("2b) 다음 진입일이 앞 거래의 청산일보다 늦거나 같다",
      all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1)),
      str(spans))

# max_hold 가 걸리는지
tds_h = T.simulate(DAYS, SIG, low=1.0, high=8.0, max_hold=3, ret_fn=ret_fn)
check("3) max_hold 가 걸려서 강제 청산된다",
      all(t[2] <= 3 for t in tds_h),
      f"보유일수 {[t[2] for t in tds_h]}")
# 거래 '횟수' 가 늘어난다고 단정할 수는 없다 - 다시 사려면 점수가 또 낮은
# 기준 아래로 내려와야 하므로, 짧게 끊어도 재진입이 안 될 수 있다. 확실한
# 것은 청산이 더 일찍 일어난다는 것이다.
check("3b) max_hold 를 줄이면 청산이 더 일찍 일어난다",
      IDX[tds_h[0][1]] < IDX[tds[0][1]],
      f"{tds_h[0][1]} vs {tds[0][1]}")

# invert 가 정말 뒤집히는지
tds_i = T.simulate(DAYS, SIG, low=1.0, high=8.0, max_hold=99, ret_fn=ret_fn,
                   invert=True)
check("4) invert=True 면 높은 점수에 사고 낮은 점수에 판다",
      len(tds_i) >= 1 and SIG[tds_i[0][0]] >= 8.0,
      f"첫 진입 점수 {SIG[tds_i[0][0]] if tds_i else None}")
check("4b) invert 의 진입일은 정방향 진입일과 다르다",
      not tds_i or tds_i[0][0] != tds[0][0],
      f"{tds_i[0][0] if tds_i else None} vs {tds[0][0]}")

# 점수가 없는 날은 건너뛴다 (지표 결측)
SIG_GAP = dict(SIG)
for d in ("T00", "T01"):
    SIG_GAP[d] = None
tds_g = T.simulate(DAYS, SIG_GAP, low=1.0, high=8.0, max_hold=99,
                   ret_fn=ret_fn)
check("5) 점수가 없는 날은 매수/매도 판단을 하지 않는다",
      all(t[0] not in ("T00", "T01") for t in tds_g),
      str([t[0] for t in tds_g]))

# 청산 시점에 수익을 못 구하면 그 거래는 버린다 (조용히 0 으로 세지 않는다)
tds_n = T.simulate(DAYS, SIG, low=1.0, high=8.0, max_hold=99,
                   ret_fn=lambda a, b: None)
check("5b) 수익을 계산할 수 없는 거래는 목록에 넣지 않는다",
      tds_n == [], str(tds_n))

# --------------------------------------------- trade_return: 시가->시가
import strategy as S  # noqa: E402


class _S:
    def __init__(self, opens):
        self.open = opens
        self.pos = {i: i for i in range(len(opens))}


panel = {"A": _S([100.0, 110.0, 121.0]), "B": _S([200.0, 210.0, 220.5])}
dmap = {"D0": 0, "D1": 1, "D2": 2}
r = T.trade_return(panel, ["A", "B"], "D0", "D2", dmap, fee=0.0)
# A: 121/100-1 = +21%,  B: 220.5/200-1 = +10.25%  -> 평균 +15.625%
check("6) 수익은 시가->시가 평균이다 (갭을 안 먹는 보수적 가정)",
      abs(r - 15.625) < 1e-9, f"{r}")
r_fee = T.trade_return(panel, ["A", "B"], "D0", "D2", dmap)
check("6b) 수수료가 왕복 한 번만 빠진다",
      abs((r - r_fee) - S.FEE_ROUND_TRIP_PCT) < 1e-9,
      f"{r} - {r_fee}")
check("6c) 패널에 없는 종목은 건너뛰고 나머지로 계산한다",
      abs(T.trade_return(panel, ["A", "없음"], "D0", "D2", dmap, fee=0.0)
          - 21.0) < 1e-9)
check("6d) 종목이 하나도 안 남으면 None",
      T.trade_return(panel, ["없음"], "D0", "D2", dmap) is None)

# --------------------------------------------------- 주의문과 관찰 전용
src = (REPO_ROOT / "analyze_timing.py").read_text(encoding="utf-8")
check("7) 주의문에 양방향 검사가 필요하다고 적혀 있다",
      "앞뒤를 바꿔서" in T.CAUTION)
check("7b) 주의문에 상승장 함정이 적혀 있다", "상승장" in T.CAUTION)
check("7c) 주의문에 대조군 통과가 다음 구간을 보장하지 않는다고 적혀 있다",
      "다음 구간에서도 남는다는 뜻이 아니다" in T.CAUTION)
check("7d) 주의문에 최대낙폭을 기준선과 비교하라고 적혀 있다",
      "최대낙폭을 기준선과" in T.CAUTION)
check("7e) 실행 결과가 문서에 숫자로 남아 있다",
      all(s in src for s in ("+113.0", "-29.1", "44등", "2.0%", "6/13")))
check("7f) 일관된 발견(반대 규칙은 양쪽 모두 손실)이 문서에 있다",
      "-13.7" in src and "-12.9" in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"8) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
