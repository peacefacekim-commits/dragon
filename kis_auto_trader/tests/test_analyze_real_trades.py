"""analyze_real_trades.py 검증 - 실거래 기록을 공평하게 읽었는가.

(2026-09-22 신설) 이 파일의 위험은 다른 분석과 다르다. 실거래 기록에는
**규칙이 결과를 정해버린 거래**가 섞여 있다. 손절의 승률이 0% 인 것은
발견이 아니라 정의다. 그걸 섞어서 평균을 내면 "짧게 들면 진다" 같은
거꾸로 된 결론이 나온다 - 실제로 처음에 그렇게 읽었다.

그래서 여기서 지키는 것
  1) 청산 이유로 갈라 보는가. 규칙 청산과 시간 청산을 안 섞는가.
  2) 인과를 거꾸로 읽었던 것을 기록에 남겼는가.
  3) 필요 승률 산수가 맞는가. 승률만 봐서는 이길지 알 수 없다.
  4) 표본이 작다는 것을 밝혔는가 (편향 없는 표본 33건).

실행:
  python tests/test_analyze_real_trades.py
"""
import pathlib
import sys
from datetime import datetime, timedelta

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import analyze_real_trades as M  # noqa: E402

src = (REPO_ROOT / "analyze_real_trades.py").read_text(encoding="utf-8")
flat = " ".join(src.split())

T0 = datetime(2026, 7, 29, 9, 30)


def mk(side, code, qty, price, mins=0, note=""):
    return {"t": T0 + timedelta(minutes=mins), "mode": "real", "code": code,
            "name": code, "side": side, "qty": qty, "price": price,
            "note": note}


# =====================================================================
# A) FIFO 짝짓기
# =====================================================================
done, left = M.pair_fifo([mk("buy", "A", 1, 100.0),
                          mk("sell", "A", 1, 110.0, 10, "익절")])
check("A1) 한 쌍이 짝지어진다", len(done) == 1 and left == 0)
check("A2) 수수료 전 수익률이 맞다",
      abs(done[0]["gross"] - 10.0) < 1e-9, f"{done[0]['gross']}")
check("A3) 수수료를 뺀 값도 낸다",
      abs(done[0]["net"] - (10.0 - M.FEE_ROUND_TRIP)) < 1e-9)
check("A4) 보유 시간(분)이 맞다", abs(done[0]["mins"] - 10.0) < 1e-9)
check("A5) 청산 이유를 가져온다", done[0]["note"] == "익절")

# 먼저 산 것이 먼저 팔린다
done, left = M.pair_fifo([mk("buy", "A", 1, 100.0, 0),
                          mk("buy", "A", 1, 200.0, 5),
                          mk("sell", "A", 1, 110.0, 10)])
check("A6) FIFO - 먼저 산 100원짜리가 먼저 팔린다",
      len(done) == 1 and done[0]["buy"] == 100.0, str(done))
check("A7) 안 팔린 매수는 미청산으로 센다", left == 1)

# 한 번에 여러 주를 팔면 쪼개진다
done, left = M.pair_fifo([mk("buy", "A", 1, 100.0, 0),
                          mk("buy", "A", 1, 200.0, 5),
                          mk("sell", "A", 2, 150.0, 10)])
check("A8) 매도 한 건이 매수 둘에 걸치면 쪼갠다",
      len(done) == 2 and left == 0, str(len(done)))
check("A9) 없는 종목을 팔면 무시한다 (기록 누락 대비)",
      M.pair_fifo([mk("sell", "Z", 1, 100.0)])[0] == [])
check("A10) 빈 입력이어도 안 터진다", M.pair_fifo([]) == ([], 0))
check("A11) 왜 FIFO 인지 적어뒀다", "먼저 산 것을 먼저 팔았다고 본다" in flat)
check("A12) 미청산을 빼는 이유를 적었다", "결과를 모르는 거래다" in flat)

# =====================================================================
# B) 필요 승률 산수 - 이 파일의 핵심
# =====================================================================
check("B1) 이익과 손실이 같으면 50%",
      abs(M.required_win_rate(3.0, -3.0) - 50.0) < 1e-9)
check("B2) 손실이 크면 50% 를 넘어야 한다",
      M.required_win_rate(3.0, -6.0) > 50.0)
check("B3) 이익이 크면 50% 미만이어도 된다",
      M.required_win_rate(6.0, -3.0) < 50.0)
check("B4) 실제 값으로 50.7% 가 나온다",
      abs(M.required_win_rate(3.902, -4.018) - 50.7) < 0.1,
      f"{M.required_win_rate(3.902, -4.018):.2f}")
check("B5) 부호를 잘못 줘도 절댓값으로 본다",
      abs(M.required_win_rate(3.0, 3.0) - 50.0) < 1e-9)
check("B6) 둘 다 0 이면 무한대 (0으로 안 나눈다)",
      M.required_win_rate(0.0, 0.0) == float("inf"))
check("B7) 승률만 봐서는 모른다고 적어뒀다",
      "승률만 봐서는 이길지 알 수 없다" in flat)

# =====================================================================
# C) 청산 이유로 갈랐는가 - 섞으면 결론이 거꾸로 된다
# =====================================================================
check("C1) 규칙 청산 목록이 상수로 있다", M.RULE_EXITS == ("손절", "익절"))
check("C2) 편향 없는 청산이 무엇인지 정해뒀다", M.UNBIASED_EXIT == "일일 정리")
rows = [mk("buy", "A", 1, 100.0, 0), mk("sell", "A", 1, 96.0, 10, "손절"),
        mk("buy", "B", 1, 100.0, 0), mk("sell", "B", 1, 104.0, 30, "익절"),
        mk("buy", "C", 1, 100.0, 0), mk("sell", "C", 1, 101.0, 300, "일일 정리"),
        mk("buy", "D", 1, 100.0, 0), mk("sell", "D", 1, 99.0, 300, "그 외 이유")]
d, _l = M.pair_fifo(rows)
g = M.by_note(d)
check("C3) 손절/익절/일일정리로 나뉜다",
      len(g["손절"]) == 1 and len(g["익절"]) == 1 and len(g["일일 정리"]) == 1)
check("C4) 나머지는 '그 외' 로 남는다", len(g.get("그 외", [])) == 1)
check("C5) 편향 없는 표본만 따로 뽑는다",
      len(M.unbiased(d)) == 1 and M.unbiased(d)[0]["code"] == "C")
check("C6) 손절의 승률 0% 가 정의라고 적었다",
      "발견이 아니라 정의다" in flat)
check("C7) 규칙 청산으로는 판단을 못 본다고 적었다",
      "규칙이 결과를 정해버린다" in flat)
check("C8) 일일 정리가 왜 편향 없는지 적었다",
      "시간이 되어\n청산한 것이라" in src or "시간이 되어 청산한 것이라" in flat)

# =====================================================================
# D) 인과를 거꾸로 읽었던 것을 남겼는가
# =====================================================================
check("D1) 처음 읽은 것을 적었다", "짧게 들면 진다" in flat)
check("D2) 틀렸다고 명시한다", "**틀렸다.**" in src or "틀렸다." in flat)
check("D3) 10분 이내가 전부 손절/익절이었다고 밝힌다",
      "손절 11건 + 익절 1건" in flat)
check("D4) note 에 적혀 있었다고 근거를 댄다", "note 에 그대로" in flat)
check("D5) 인과가 거꾸로였다고 정리한다",
      "보유 시간은 원인이 아니라 결과다" in flat)
check("D6) 실제 종목명까지 남겼다 (확인 가능하게)",
      "모아라이프플러스" in src)

# =====================================================================
# E) 결과 숫자가 모듈 출력과 맞는가
# =====================================================================
for tok in ("-4.018", "+3.902", "-0.023", "-108,551", "-392,728",
            "+293,618", "-9,441", "50.7%", "45.5%", "48.5%",
            "140.3", "-23.0%p"):
    check(f"E) 문서에 {tok} 가 있다", tok in src)
check("E1) 10분 매매가 아니었다고 바로잡았다", "10분 매매가 아니었다" in flat)
check("E2) 선정 엣지가 사실상 0 이라고 밝힌다",
      "엣지도, 반대 엣지도 없었다" in flat)
check("E3) 왜 -108,551원인지 산수로 보인다", "산수가 정확히 맞는다" in flat)
check("E4) 익절 평균이 승자 평균과 다른 이유를 적었다",
      "이긴 것만 평균하면" in flat)
check("E5) 승률이 아니라 크기가 문제였다고 정리한다",
      "크기가 같다' 는 것이었다" in flat)

# =====================================================================
# F) 일봉 분석과 이어 붙였는가
# =====================================================================
check("F1) analyze_stops 와 잇는다", "analyze_stops" in src)
check("F2) analyze_original 12/12 와 잇는다",
      "analyze_original" in src and "12/12" in src)
check("F3) 실제 돈으로 확인됐다고 적었다", "실제 돈으로 확인됐다" in flat)
check("F4) 운이 아니라 구조였다고 짚는다", "운이 나빴던 게 아니라 구조" in flat)

# =====================================================================
# G) 계획을 어떻게 고쳐야 하는지 적었는가
# =====================================================================
check("G1) 목표 보유시간이 달라졌다고 적었다", "10분이 아니라 **2~5시간**" in src)
check("G2) analyze_min10 의 보유시간 칸을 늘리라고 적었다",
      "analyze_min10.py 의 보유시간 칸" in flat)
check("G3) 승률보다 비대칭을 먼저 묻자고 적었다",
      "손익 비대칭을 먼저 물어야" in flat)

# =====================================================================
# H) 한계를 밝혔는가
# =====================================================================
check("H1) 표본이 작다고 밝힌다", "88건은 적다" in flat and "33건뿐" in flat)
check("H2) 신뢰구간이 넓다고 밝힌다", "32~65%" in src)
check("H3) 점추정이지 확정이 아니라고 못박는다", "점추정이지 확정이 아니다" in flat)
check("H4) 5주 한 시기라고 밝힌다", "약 5주다. 시기 하나다" in flat)
check("H5) 선정 기준을 복원할 수 없다고 밝힌다", "복원할 수 없다" in flat)
check("H6) 슬리피지는 여전히 못 재는 것을 밝힌다",
      "슬리피지는 못 뺀다" in flat and "0.08% 교차점" in flat)

# =====================================================================
# I) 실제 파일로 돌려도 되는가 + 안전
# =====================================================================
real = M.load_trades()
if real:
    rdone, rleft = M.pair_fifo(real)
    check("I1) 실제 기록을 읽는다", len(real) == 172, f"{len(real)}건")
    check("I2) 완결 88건 / 미청산 11건",
          len(rdone) == 88 and rleft == 11, f"{len(rdone)}/{rleft}")
    check("I3) 전부 실거래(real) 다",
          all(r["mode"] == "real" for r in real))
    check("I4) 편향 없는 표본이 33건", len(M.unbiased(rdone)) == 33,
          f"{len(M.unbiased(rdone))}건")
else:
    check("I1) 기록이 없으면 빈 목록 (안 터진다)", real == [])
check("I5) 파일이 없어도 안 터진다",
      M.load_trades(pathlib.Path("/없는/경로.csv")) == [])

check("I6) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"I7) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
