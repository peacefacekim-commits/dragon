"""전제.md 검증 - 목표가 표류하지 않는가 + 그날 두 사고의 방지책.

(2026-09-22 신설) 전제를 문서로만 적으면 표류한다. 이 테스트가 두 가지를
지킨다.

  1) 전제가 **채택 조건으로 번지지 않는가.** "자동화 이점을 쓴다" 가
     채택 이유가 되면, 1일 주기 교체(백테스트 25.1%, 반띵 뒤집힘,
     슬리피지 0.08% 에서 역전)를 채택하게 된다. 가장 자동화다운 것을
     고르면서 가장 확실하게 지는 길이다.
  2) 문서가 인용한 숫자가 원본 모듈과 맞는가. 요약이 틀리면 요약만 읽는
     사람이 틀린 판단을 한다 (test_결론.py 와 같은 이유).

그리고 그날 실제로 당한 두 사고의 방지책이 살아 있는지도 본다.
  - 반쪽짜리 마지막 날이 패널에 들어가는 것 (연 22.0% -> -21.6% 로 보였다)
  - 장 시작 전 분봉이 빈 봉으로 저장되는 것

실행:
  python tests/test_전제.py
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


src = (REPO_ROOT / "전제.md").read_text(encoding="utf-8")
flat = " ".join(src.split())


def read(name):
    return (REPO_ROOT / name).read_text(encoding="utf-8")


# =====================================================================
# A) 전제가 명확히 적혀 있는가
# =====================================================================
check("A1) 사람이 아니라 AI 가 투자한다고 못박는다",
      "사람이 투자하는 게 아니다" in flat and "AI가 자동으로 투자한다" in flat)
check("A2) 자동화만이 할 수 있는 일에서 찾는다고 적었다",
      "자동화만이 할 수 있는 일" in flat)
check("A3) 사용자 지적을 그대로 인용했다",
      "사람이 하는 게 더 나은 거였으니" in flat)
check("A4) 주문일이 2번이라는 사실을 인정한다",
      "1년에\n**주문일이 2번**" in src or "주문일이 2번" in flat)

# =====================================================================
# B) 전제가 채택 조건으로 번지지 않는가 - 이 파일의 핵심
# =====================================================================
check("B1) 탐색 방향과 채택 조건을 갈랐다",
      "어디를 찾을까" in flat and "무엇을 채택할까" in flat)
check("B2) 자동화 이점이 채택 이유가 될 수 없다고 못박는다",
      "채택 이유가 될 수는 없다" in flat)
check("B3) 채택 조건이 그대로라고 적었다",
      "사전 등록" in flat and "연도별 지속성" in flat)
check("B4) 1일 주기를 반례로 든다",
      "1일 주기 교체" in flat and "25.1%" in src)
check("B5) 그 반례의 탈락 이유를 셋 다 적었다",
      "반띵 뒤집힘" in flat and "0.08%" in src and "-18.8%" in src)
check("B6) 함정의 이름을 붙였다",
      "가장\n자동화다운 것을 채택하면서" in src
      or "가장 자동화다운 것을 채택하면서" in flat)

# =====================================================================
# C) 다섯 갈래가 다 있고 근거 숫자가 원본과 맞는가
# =====================================================================
for tag in ("(A)", "(B)", "(C)", "(D)", "(E)"):
    check(f"C) {tag} 갈래가 있다", tag in src)
check("C1) (A) 선정 63.5%p 가 analyze_styles 와 맞다",
      "63.5%p" in src and "63.5%p" in read("analyze_styles.py"))
check("C2) (A) 구간 22.0 vs 11.0 이 --slice 결과와 맞다",
      "11.0%" in src and "11.0" in read("analyze_styles.py"))
check("C3) (B) 익절 12/12 가 analyze_original 과 맞다",
      "12/12" in src and "12/12" in read("analyze_original.py"))
check("C4) (B) 타이밍 23가지가 analyze_timing 쪽과 맞다",
      "23가지" in src and "23" in read("analyze_timing.py"))
check("C5) (C) 손익분기 2.3일이 analyze_short_term 과 맞다",
      "2.3일" in src and "2.3일" in read("analyze_short_term.py"))
check("C6) (C) 1일 보유 -27.0% 가 맞다",
      "-27.0%" in src and "-27.0%" in read("analyze_short_term.py"))
check("C7) (C) 세금 86% 가 맞다",
      "86%" in src and "86%" in read("analyze_short_term.py"))
check("C8) (D) 수수료 문턱 23% 가 analyze_min10 과 맞다",
      "23%" in src and "23%" in read("analyze_min10.py"))
check("C9) (E) 감시 숫자가 monitor 와 맞다",
      all(t in src for t in ("1.061", "0.229", "1.727", "-14.5"))
      and all(t in read("monitor.py") for t in ("1.061", "1.727", "-14.5")))

# =====================================================================
# D) (C) 갈래가 닫혔다고 정확히 적었는가
# =====================================================================
check("D1) 수수료 때문이라고 짚는다 (신호가 없어서가 아니라)",
      "신호가 없어서가 아니라 수수료 때문이다" in flat)
check("D2) 순엣지 공식을 적었다", "순엣지(H)" in src)
check("D3) 이 갈래가 닫혀 있다고 밝힌다", "이 갈래는 이 프로젝트에서 닫혀" in flat)
check("D4) 세금이라 깎을 수 없다고 적었다", "깎을 방법도 없다" in flat)

# =====================================================================
# E) (E) 감시가 예측이 아니라고 적었는가
# =====================================================================
check("E1) 예측이 아니라고 못박는다", "이건 예측이 아니다" in flat)
check("E2) 수수료가 안 든다고 짚는다", "수수료가 들지 않는다" in flat)
check("E3) 사람은 매일 못 한다고 적었다", "사람이 매일 이 셋을 계산할 방법은" in flat)
check("E4) monitor.py 가 자동 실행에 걸려 있다",
      "monitor.py" in (REPO_ROOT / "매일 실행.bat").read_text(encoding="ascii"))

# =====================================================================
# F) 앞으로의 질문 셋이 박혀 있는가
# =====================================================================
check("F1) 사람이 할 수 있나를 묻는다", "사람이 이걸 할 수 있나" in flat)
check("F2) 그래도 이기면 채택한다고 단서를 달았다",
      "그래도 이기면 채택한다" in flat)
check("F3) 거래를 늘리나를 묻는다", "거래를 늘리나" in flat)
check("F4) 어느 갈래인지 적게 한다", "어느 갈래인가" in flat)

# =====================================================================
# G) 그날 두 사고와 방지책 - 코드에 실제로 남아 있는가
# =====================================================================
check("G1) 반쪽짜리 마지막 날 사고를 기록했다",
      "573종목" in src and "-21.6%" in src)
check("G2) 원인이 전략이 아니라 데이터였다고 밝힌다",
      "전략이 아니라 **데이터 한 줄**" in src
      or "전략이 아니라 데이터 한 줄" in flat)
check("G3) 오염된 측정으로 답을 적지 않았다고 밝힌다",
      "오염된 측정으로 답을 적지 않는다" in flat
      and "아직 안 답했다" in flat)

strat = read("strategy.py")
check("G4) load_panel 에 방지책이 실제로 있다",
      "_drop_incomplete_tail" in strat)
check("G5) 문턱이 상수로 박혀 있다", "INCOMPLETE_TAIL_RATIO = 0.6" in strat)
check("G6) 버릴 때 화면에 적는다 (조용히 안 버린다)",
      "아직 다 안 받은 " in strat and "제외합니다" in strat)
check("G7) 왜 load_panel 에 넣었는지 적혀 있다",
      "분석 모듈 30개가 전부 load_panel 을 지나가므로" in " ".join(strat.split()))

# 실제로 동작하는가 (마지막 날이 반쪽이면 잘라낸다)
import strategy as S  # noqa: E402

_dates = [f"2026{m:02d}{d:02d}" for m in (1, 2) for d in range(1, 16)][:25]
_raw = {f"c{i}": [(d, 1.0, 1.0, 1.0) for d in _dates[:-1]] for i in range(100)}
for i in range(20):                      # 마지막 날엔 20종목만
    _raw[f"c{i}"].append((_dates[-1], 1.0, 1.0, 1.0))
_out, _n = S._drop_incomplete_tail(_dates, _raw, verbose=False)
check("G8) 반쪽짜리 마지막 날을 잘라낸다",
      _n == 1 and _out[-1] == _dates[-2], f"{_n}일 버림, 끝 {_out[-1]}")
for i in range(100):                     # 이번엔 다 채워서
    _raw[f"c{i}"].append((("20260301"), 1.0, 1.0, 1.0))
_out2, _n2 = S._drop_incomplete_tail(_dates + ["20260301"], _raw, verbose=False)
check("G9) 온전한 날은 안 버린다", _n2 == 0, f"{_n2}일 버림")
check("G10) 날짜가 너무 적으면 아무것도 안 한다",
      S._drop_incomplete_tail(["20260101"], {}, verbose=False) == (["20260101"], 0))

check("G11) 빈 봉 사고를 기록했다",
      "거래량 0, 시=고=저=종" in flat and "6,000행" in src)
check("G12) 빈 봉 방지책이 코드에 있다",
      "is_placeholder" in read("fetch_intraday.py"))
check("G13) 두 사고의 공통 원인을 한 줄로 적었다",
      "장 시작 전에 수집을 돌렸다" in flat)

# =====================================================================
# H) 문서가 결과/규칙 문서와 역할이 겹치지 않는가
# =====================================================================
check("H1) 무엇을 하려는가를 적는 문서라고 밝힌다",
      "목표**를 못 박는다" in src or "목표" in flat)
check("H2) 결론.py / RULES.md 와 다르다고 적었다",
      "결론.py" in src and "RULES.md" in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
