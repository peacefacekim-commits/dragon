"""monitor.py 검증 - 거래 없는 감시가 감시로 남아 있는가.

(2026-09-22 신설) 이 파일의 위험은 다른 분석 파일과 다르다. 감시가
슬그머니 **예측** 으로 바뀌는 것이다. "하락포착이 올라갔으니 팔아라"
같은 말이 붙으면, 이 저장소가 23가지 시도해서 전부 실패한 그 자리로
돌아간다.

그래서 여기서 지키는 것
  1) 경보 기준이 미리 박혀 있고 결과를 보고 안 바뀐다
  2) 표본이 적으면 판정하지 않는다 (흔들리는 값으로 울리면 못 쓴다)
  3) 예측이 아니라고 문서에 못박혀 있다
  4) 주문 코드가 없다

실행:
  python tests/test_monitor.py
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


import importlib  # noqa: E402

M = importlib.import_module("monitor")

src = (REPO_ROOT / "monitor.py").read_text(encoding="utf-8")
flat = " ".join(src.split())

# =====================================================================
# A) 경보 기준이 미리 박혀 있는가
# =====================================================================
check("A1) 상승/하락 기준이 analyze_why 손익분기에서 온다",
      abs(M.ALARM_UD_RATIO - 1.318) < 0.001, f"{M.ALARM_UD_RATIO:.4f}")
check("A2) 하락포착 기준이 0.30", M.ALARM_DOWN_CAPTURE == 0.30)
check("A3) 상승추종 기준이 0.50", M.ALARM_UP_CAPTURE == 0.50)
check("A4) 기준이 analyze_why 실측값보다 여유가 있다",
      M.ALARM_DOWN_CAPTURE > M.W.DOWN_CAPTURE
      and M.ALARM_UP_CAPTURE > M.W.UP_CAPTURE)
check("A5) 왜 여유를 뒀는지 적었다", "딱 기준선에 걸면 계속" in flat)
check("A6) 여유 폭도 결과를 보고 안 고친다고 적었다",
      "여유 폭도 결과를 보고 고치지 않는다" in flat)
check("A7) 표본 하한이 있다", M.MIN_SAMPLE == 30)

# =====================================================================
# B) 판정 - 표본이 적으면 울리지 않는다
# =====================================================================
check("B1) 셋 다 기준 안이면 이상 없음",
      M.verdict(1.0, 0.2, 0.3, 60, 60) == [])
check("B2) 표본이 적으면 판정하지 않는다",
      M.verdict(9.9, 0.9, 0.9, 5, 5) == ["표본 부족 - 판정하지 않음"],
      str(M.verdict(9.9, 0.9, 0.9, 5, 5)))
check("B3) 비율이 넘으면 울린다",
      any("상승일/하락일" in a for a in M.verdict(1.5, 0.2, 0.3, 60, 60)))
check("B4) 하락포착이 넘으면 울린다",
      any("하락일 포착률" in a for a in M.verdict(1.0, 0.45, 0.3, 60, 60)))
check("B5) 상승추종이 넘으면 울린다",
      any("상승일 추종률" in a for a in M.verdict(1.0, 0.2, 0.6, 60, 60)))
check("B6) 셋이 다 넘으면 셋 다 울린다",
      len(M.verdict(1.8, 0.5, 0.6, 60, 60)) == 3)
check("B7) 경계값은 안 울린다 (초과일 때만)",
      M.verdict(M.ALARM_UD_RATIO, M.ALARM_DOWN_CAPTURE,
                M.ALARM_UP_CAPTURE, 60, 60) == [])
check("B8) 값이 없으면 그 항목은 건너뛴다",
      M.verdict(1.0, None, None, 60, 60) == [])

# =====================================================================
# C) 포착률과 비율 계산
# =====================================================================
g = {"pool": [1.0, 2.0], "lo": [0.3, 0.6]}
check("C1) 포착률은 저변동 평균 / 풀 평균",
      abs(M.capture(g) - 0.3) < 1e-9, f"{M.capture(g)}")
check("C2) 표본이 없으면 None",
      M.capture({"pool": [], "lo": []}) is None)
check("C3) 풀 평균이 0 이면 None (0으로 안 나눈다)",
      M.capture({"pool": [1.0, -1.0], "lo": [0.5, 0.5]}) is None)
up = {"pool": [1.0] * 60, "lo": [0.4] * 60}
dn = {"pool": [-1.0] * 50, "lo": [-0.2] * 50}
check("C4) 비율은 오른날 / 내린날",
      abs(M.ud_ratio(up, dn) - 1.2) < 1e-9, f"{M.ud_ratio(up, dn)}")
check("C5) 내린날이 0 이면 무한대",
      M.ud_ratio(up, {"pool": [], "lo": []}) == float("inf"))
check("C6) 남은 엣지는 analyze_why 공식을 그대로 쓴다",
      abs(M.net_edge_left(up, dn) - M.W.edge_left(60, 50)) < 1e-9)

# =====================================================================
# D) 구간을 잘라서 보는가 - 전체 평균에 묻히면 변화가 안 보인다
# =====================================================================
check("D1) 창 길이 기본이 120", M.WINDOW == 120)
check("D2) 구간을 받아서 자른다",
      "def window_split(dates, panel, order, lo, hi" in src)
check("D3) 왜 최근 창만 보는지 적었다",
      "6년 평균에\n   묻혀서" in src or "6년 평균에 묻혀서" in flat)
check("D4) 미래 정보를 안 쓴다 (di 에서 di+1 수익을 보되 순위는 di 것)",
      'E.price(panel, c, di, "close")' in src
      and 'E.price(panel, c, di + 1, "close")' in src)
check("D5) 순위는 daily_ranks 를 쓴다 (그 시점 정보만)",
      "E.daily_ranks(dates, panel, BASE_DI)" in src)

# =====================================================================
# E) 감시가 예측으로 바뀌지 않았는가 - 이 파일의 핵심
# =====================================================================
check("E1) 예측이 아니라고 못박는다", "이건 예측이 아니다" in flat)
check("E2) 예측은 23가지 실패했다고 잇는다",
      "23가지 시도해서 전부" in flat)
check("E3) 감시와 예측이 다른 일이라고 적었다",
      "둘은 다른\n   일이고" in src or "둘은 다른 일이고" in flat)
check("E4) 감시는 수수료가 안 든다고 짚는다", "수수료가 들지 않는다" in flat)
check("E5) 경보가 '그만두라' 가 아니라고 적었다",
      "그만두라는 뜻이 아니다" in flat or "그만두라' 가 아니라" in flat)
check("E6) 상승장에서는 정상적으로 넘는다고 적었다",
      "정상적으로 넘어간다" in flat)
check("E7) '팔아라' 같은 말이 없다",
      "팔아라" not in src and "매도하라" not in src and "사라" not in src)

# =====================================================================
# F) 자동화 이점을 갈라서 적었는가 - 사용자 지적에 대한 답
# =====================================================================
check("F1) 사용자 지적을 그대로 적었다",
      "사람이 하는 게" in flat and "주문일이 2번" in flat)
check("F2) 네 갈래로 갈랐다",
      "(A)" in src and "(B)" in src and "(C)" in src and "(D)" in src)
check("F3) (A) 선정이 안 보이는 이점이라고 짚었다",
      "안 보이는" in flat and "63.5%p" in src)
check("F4) (B) 안 하는 것이 이점이라고 짚었다",
      "무엇을 안 하는가" in flat and "12/12" in src)
check("F5) (C) 계속 보기가 수수료에 진다고 짚었다",
      "수수료** 때문이다" in src or "수수료 때문이다" in flat)
check("F6) (C) 근거로 슬리피지 역전을 든다", "0.08%" in src)
check("F7) (D) 장중이 유일하게 안 재본 자리라고 적었다",
      "안 재본 유일한 자리" in flat and "analyze_min10" in src)
check("F8) (E) 거래 없는 감시를 따로 세웠다",
      "거래하지 않는 감시" in flat)

# =====================================================================
# G) 첫 실행 결과가 적혀 있고 analyze_why 와 맞는가
# =====================================================================
for tok in ("1.061", "0.229", "0.369", "1.727", "0.423", "-14.5", "+12.4"):
    check(f"G) 결과표에 {tok} 가 있다", tok in src)
check("G1) analyze_why 분해값과 맞다고 밝힌다",
      "analyze_why.py 의 분해값과 맞는다" in flat)
check("G2) 다른 코드로 같은 값이 나온 것이 확인이라고 적었다",
      "계산이" in flat and "어긋나지 않았다는 확인" in flat)
check("G3) 경보가 실제로 울린 구간이 있었다고 적었다",
      "그 앞 120일 구간에서 셋 다 경보였다" in flat)
check("G4) 그 구간에서 무엇을 알려줬을지 적었다",
      "불리한 국면이다" in flat)
check("G5) 사람은 매일 못 한다는 것을 짚었다",
      "사람이 매일 이 셋을 계산할 방법은 없다" in flat)
check("G6) 최근 구간은 정상으로 돌아왔다고 적었다",
      "정상으로 돌아왔다" in flat)

# =====================================================================
# H) 안전
# =====================================================================
check("H1) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "auth", "requests"):
    check(f"H2) 주문/통신 코드가 없다 ({banned})", banned not in src)
check("H3) 주문을 내지 않는다고 적었다", "주문을 내지 않는다" in flat)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
