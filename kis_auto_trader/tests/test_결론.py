"""결론.py 검증 - 모아놓은 숫자가 원본과 맞는지.

(2026-09-21 신설) 이 파일은 요약이라서 위험이 하나 있다. **원본 모듈의
숫자와 어긋나는 것**이다. 요약이 틀리면 요약만 읽는 사람이 틀린 판단을
한다. 그래서 여기서는 결론.py 에 적힌 숫자를 원본 파일에서 찾아 대조한다.

또 하나는 결론을 좋게 각색하는 것이다. 탈락한 것을 빼먹거나, '모른다' 를
'아니다' 로 바꿔 적으면 요약이 광고가 된다. 그것도 검사한다.

실행:
  python tests/test_결론.py
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


src = (REPO_ROOT / "결론.py").read_text(encoding="utf-8")
flat = " ".join(src.split())


def read(name):
    return (REPO_ROOT / name).read_text(encoding="utf-8")


# =====================================================================
# A) 숫자가 원본과 맞는가 - 요약이 틀리면 요약만 읽는 사람이 틀린다
# =====================================================================
PAIRS = [
    ("+22.0%", "analyze_knobs.py", "22.0", "저변동 연수익"),
    ("-15.9%", "analyze_knobs.py", "-15.9", "저변동 낙폭"),
    ("-41.5%", "analyze_knobs.py", "-41.5", "고변동 연수익"),
    ("-95.1%", "analyze_knobs.py", "-95.1", "고변동 낙폭"),
    ("0.093%", "analyze_short_term.py", "0.093", "하루당 엣지"),
    ("2.3일", "analyze_short_term.py", "2.3일", "손익분기"),
    ("-27.0%", "analyze_short_term.py", "-27.0%", "1일 보유 연환산"),
    ("+0.102%", "analyze_short_term.py", None, "1일 보유 엣지"),
    ("86%", "analyze_short_term.py", "86%", "세금 비중"),
    ("15.5%", "analyze_turnover.py", None, "전량교체 수수료"),
    ("+0.567%p", "analyze_flow.py", "0.567", "개인 순매수 초과분"),
    ("-20.4%", "analyze_flow.py", "-20.4", "개인 선택 낙폭"),
    ("20.4%", "analyze_flow.py", "20.4%", "기관 대조군 탈락률"),
    ("4.6%p", "analyze_knobs.py", "4.6%p", "손잡이 폭"),
    ("11.4%p", "analyze_knobs.py", "11.4%p", "시작일 폭"),
    ("41.1%", "plan_2m.py", "41.1", "마이너스 달 비율"),
]
for token, origin, needle, what in PAIRS:
    check(f"A) {what} ({token}) 가 {origin} 에도 있다",
          token in src and (needle or token.strip("+%일p")) in read(origin),
          f"요약에 {token in src}, 원본에 {(needle or token) in read(origin)}")

# 감쇠 표는 해마다 값을 적었으니 전부 대조한다
decay = read("analyze_decay.py")
for year, val in (("2021", "0.213"), ("2022", "7.908"), ("2023", "4.576"),
                  ("2024", "9.373"), ("2025", "4.253"), ("2026", "5.924")):
    check(f"A2) {year} 저변동 효과 {val} 가 analyze_decay.py 와 맞다",
          val in src and val in decay)

# =====================================================================
# B) 살아남은 것이 정확히 둘인가
# =====================================================================
check("B1) 살아남은 것이 둘이라고 명시한다", "둘뿐이다" in src)
check("B2) 저변동 선정이 들어 있다", "저변동 선정" in src)
check("B3) 부분교체가 들어 있다", "부분교체" in src)
check("B4) 6년 내내 양수라는 근거를 적었다",
      "해마다 양수" in flat and "닳지도 않았다" in flat)
check("B5) 종목 겹침 47% 근거를 적었다 (특정 종목 덕이 아니라는 뜻)",
      "47%" in src)

# =====================================================================
# C) 탈락한 것을 빼먹지 않았는가
# =====================================================================
for must in ("손절", "익절", "이벤트 교체", "슬롯 재활용", "모멘텀",
             "변동성 측정 기간", "뉴스", "계단식"):
    check(f"C) 탈락 목록에 {must} 가 있다", must in src)
check("C2) 탈락이 70가지가 넘는다고 적었다", "70가지" in src)
knobs = read("analyze_knobs.py")
check("C2b) 기준점 숫자를 --flip 으로 재현할 수 있다",
      '"--flip"' in knobs and "고변동 10" in knobs)
check("C2c) 출처 없는 숫자를 썼던 경위를 적어뒀다",
      "출처 없는 숫자를 인용" in " ".join(knobs.split()))
check("C3) 각 결론의 출처 파일을 적었다",
      src.count("[analyze_") >= 10, f"{src.count('[analyze_')}개")

# =====================================================================
# D) 가장 가까이 간 것을 숨기지도, 부풀리지도 않았는가
# =====================================================================
check("D1) 두 검정을 통과한 것이 있다고 밝힌다",
      "대조군과 반기 분할을 둘 다 통과" in flat)
check("D2) 그래도 안 켜는 이유를 넷 다 적었다",
      "1)" in src and "2)" in src and "3)" in src and "4)" in src
      and "거울상" in src)
check("D3) 다중검정 보정을 실제로 계산해 보였다", "1.4% x 10 = 14%" in src)
check("D4) 낙폭이 나빠졌다는 불리한 사실도 적었다",
      "낙폭이 나빠졌다" in flat)

# =====================================================================
# E) '모른다' 를 '아니다' 로 바꾸지 않았는가
# =====================================================================
check("E1) 답할 수 없는 것을 따로 적었다", "자료로 답할 수 없는 것" in src)
check("E2) 모른다고 네 번 적었다", src.count("모른다") >= 3,
      f"{src.count('모른다')}번")
check("E3) 바꿔 적지 않겠다고 못 박았다",
      "'모른다' 를 '아니다' 로 바꿔 적지 않는다" in flat)
check("E4) 백테스트 값이라는 것을 밝힌다",
      "백테스트 값이라는 점이 중요하다" in flat)
check("E5) 전진 기록이 0건이라고 밝힌다",
      "청산된 회차가 0개" in flat)
check("E6) 낙폭과 회복 기간을 숨기지 않는다",
      "412거래일" in src and "-14.3%" in src)

# =====================================================================
# F) 다음에 할 일을 좁혀놨는가
# =====================================================================
check("F1) 선택지가 셋이라고 적었다", "셋뿐이다" in src)
check("F2) 파라미터 훑기는 선택지에 없다고 못 박았다",
      "파라미터를 더 훑는 것은 목록에 없다" in flat)
check("F3) 왜 그런지 이유를 적었다", "우연에 속을 확률이 높다" in flat)
check("F4) 재무 데이터가 채워졌다는 것을 밝힌다",
      "krx_fund" in src and "1,780종목" in src)
check("F5) 사전 등록 기준을 통과했다는 사실을 적었다 (숨기지 않음)",
      "사전 등록 기준을 통과했으나" in flat and "29.7" in src)
check("F6) 해마다 쪼개면 무너진다는 것을 적었다",
      "2025년 한 해가 전부다" in flat and "+41.3" in src)
check("F7) 사전 등록의 설계 실수를 스스로 밝힌다",
      "내 사전 등록의 설계 실수" in flat and "서로 독립이 아니었다" in flat)
check("F8) 안 켜는 이유를 정확히 적었다",
      "안 켠다" in flat and "+7.4%p 가 애초에 없어서" in flat)
check("F8b) 판정 자체는 통과로 남긴다 (조건을 고치지 않는다)",
      "판정 자체는 '통과' 로 남겨둔다" in flat)
check("F8c) 앞으로 연도별을 조건에 넣겠다고 적었다",
      "연도별 지속성을 조건에 넣는다" in flat)
check("F9) 생존편향을 다시 확인했다고 적었다", "96%" in src)

# =====================================================================
# G) 안전 / 실행
# =====================================================================
check("G1) 새 계산을 하지 않는다고 밝힌다", "새 계산을 하지 않는다" in flat)
check("G2) 리눅스 절대경로가 없다", '"/home/user/' not in src)
for banned in ("place_order", "api_client", "requests"):
    check(f"G3) 주문/통신 코드가 없다 ({banned})", banned not in src)

import importlib  # noqa: E402
_m = importlib.import_module("결론")
check("G4) import 해도 안 터진다", _m.__doc__ is not None)
check("G5) main 이 0 을 돌려준다", _m.main() == 0)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
