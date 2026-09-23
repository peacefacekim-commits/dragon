"""analyze_decay.py 검증 - '닳고 있나' 를 재는 방식이 흐려지지 않게.

(2026-09-18 신설) 사용자 지적 "시간을 늘려도 시간이 지나가면서 투자 방향이
변하는 게 있을테니 그것도 완벽하진 않을거야" 에 답하는 파일이다.

이 파일이 지켜야 하는 것 - 하나라도 무너지면 결론이 뒤집힌다

  1) 두 가지를 반드시 구별해서 잰다
       시장 대비 초과분  = 저변동10 - 유니버스 전체   (변한다)
       저변동 효과 자체  = 저변동10 - 고변동10        (안 변한다)
     하나만 재면 "요즘 안 통한다" 와 "효과가 죽었다" 를 섞게 된다.
     이 파일의 결론 전체가 이 구별 위에 서 있다.

  2) 추세 판정에 t 값을 쓴다. 기울기가 음수라는 것만으로 '닳는다' 고
     말하면 안 된다. t=-1.37 은 단정할 수 없다는 뜻이다.

  3) 금융주를 뺀 수익을 같이 낸다. 밸류업은 한 번뿐인 사건이라
     거기서 나온 초과분이면 다음에 없다.

  4) 뽑히는 종목의 변화를 본다. 규칙이 같아도 사는 물건이 달라진다.

  5) 미래 정보를 안 쓴다 - 종목 선정은 di 시점 정보로, 수익은 di 이후로.

실행:
  python tests/test_analyze_decay.py
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


src = (REPO_ROOT / "analyze_decay.py").read_text(encoding="utf-8")

# ---------------------------------------------------------------- 1) 두 측정
check("1) 시장 대비 초과분을 잰다 (저변동 - 유니버스 전체)",
      '"excess": r_low - r_all' in src)
check("1b) 저변동 효과 자체를 따로 잰다 (저변동 - 고변동)",
      '"lowhigh": r_low - r_high' in src)
check("1c) 고변동 10종목은 점수 반대쪽 끝에서 뽑는다",
      "high = [c for _s, c in sc[-PICK:]]" in src)
check("1d) 둘이 다른 것이라는 설명이 문서에 있다",
      "둘을 구별해야 한다" in src)
check("1e) 초과분이 마이너스가 되는 이유(시장이 오름)를 적어놨다",
      "시장이 올랐기" in src and "덜 빠지는 대가로 덜 오른다" in src)
check("1f) '안 통한다' 와 '효과가 죽었다' 를 구별하는 법을 적어놨다",
      "요즘 안 통한다" in src and "효과가 죽었다" in src)

# ------------------------------------------------------------ 2) 추세 판정
check("2) 이동창으로 추이를 본다", "for i in range(W, len(rounds) + 1, 3)" in src)
check("2b) 1년 = 12회차로 잡았다", "W = 12" in src)
check("2c) 기울기만 보지 않고 표준오차와 t 를 낸다",
      "slope/se" in src and "표준오차" in src)
check("2d) t 가 -2 보다 작아야 한다는 기준이 코드 출력에 있다",
      "t 가 -2 보다 작아야 한다" in src)
check("2e) t=-1.37 이 단정 불가라는 해석이 문서에 있다",
      "t = -1.37" in src and "단정할 수 없다" in src)
check("2f) 단조 감소가 아니라 오르내림이라고 적어놨다",
      "단조 감소가 아니라 오르내림" in src)
check("2g) 2023년에 마이너스였다가 돌아온 사실을 남겼다",
      "-0.797" in src and "회복" in src)

# ------------------------------------------------------------ 3) 금융주
check("3) 금융주를 뺀 수익을 따로 낸다", "nonfin = [c for c in low if c not in FIN]" in src)
check("3b) 금융주가 3개 미만 남으면 계산하지 않는다",
      "if len(nonfin) >= 3 else None" in src)
check("3c) 바스켓의 금융주 개수를 센다",
      "nfin = sum(1 for c in low if c in FIN)" in src)
check("3d) 밸류업이 한 번뿐인 사건이라는 이유가 적혀 있다",
      "한 번뿐인 사건" in src)
check("3e) 금융주가 주된 원인이 아니라는 결론과 근거가 같이 있다",
      "주된 원인은 아니다" in src and "+0.972" in src)
check("3f) 2026년 금융주 의존이 커진 것을 경고로 남겼다",
      "4.4" in src and "지켜볼 것" in src)

# ------------------------------------------------- 4) 뽑히는 종목의 변화
check("4) 연도별로 많이 뽑힌 종목을 센다", "freq[c] = freq.get(c, 0) + 1" in src)
check("4b) 초기와 최근의 겹침 비율을 낸다",
      "len(first & last)/len(first|last)" in src)
check("4c) 47% 라는 결과가 문서에 있다", "47%" in src)
check("4d) 규칙이 같아도 사는 물건이 달라진다는 해석이 있다",
      "사는 물건이 달라" in src)

# -------------------------------------------------------- 5) 미래 정보 차단
check("5) 종목 선정은 진입 시점 정보로만 한다",
      "S.factor_score(panel, c, di" in src and "S.universe_at(panel, di" in src)
check("5b) 수익은 진입 이후 구간에서만 잰다",
      "S.trade_return(panel, c, di, di + HOLD)" in src)
check("5c) 수수료를 뺀다", "st.mean(rs) - FEE" in src)

# ---------------------------------------------- 6) 결론이 과장되지 않았나
check("6) 더 긴 데이터가 주는 것이 확신이 아니라는 말이 있다",
      "'확신' 이 아니라" in src and "흔들리는 범위" in src)
check("6b) 저변동 효과가 6년 전부 양수라는 근거 수치가 있다",
      "+0.213" in src and "+7.908" in src and "+5.924" in src)
check("6c) 사용자 지적이 맞다고 인정하는 문장이 있다",
      "사용자 지적이 맞다" in src)

# ------------------------------------------------------- 7) 이식성 / 안전
check("7) 리눅스 절대경로를 박아두지 않았다",
      '"/home/user/kis_auto_trader' not in src)
check("7b) 경로는 __file__ 기준으로 만든다",
      "pathlib.Path(__file__).resolve().parent" in src)
for banned in ("place_order", "api_client", "import auth", "requests"):
    check(f"7c) 주문/통신 코드가 없다 ({banned})", banned not in src)

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
