"""전략을 모의로 앞으로 돌리면서 '나쁜날 게이트' 를 채점한다.

(2026-09-17 신설)

왜 필요한가. 사용자 방침: "전략대로 샀을 때 하락한 날들의 지표 공통점을
찾고, 앞으로 투자를 모의로 진행했을 때 그 지표가 작동하는지 지켜보자."

먼저 과거 데이터로 그 '공통점' 을 찾아봤고, 결과는 아래와 같았다.

  보유 20일, 겹치는 회차 1,196개(독립 표본 약 61개), 손실 회차 526개.
  전반부에서 손실/이익 회차가 가장 크게 갈린 지표는 kr_vol20 (상관 +0.222).
  그런데 후반부에서 부호가 뒤집혔다 (-0.204).
  13개 지표 중 부호가 유지된 것은 7개 - 우연이면 6.5개다.
  전반부에서 만든 종합 점수의 상관은 +0.187 -> 후반부 -0.102 (음수).
  보유 5일도 같다: 부호 유지 4/13, 종합 상관 +0.082 -> -0.047.

즉 과거 데이터에서 '손실난 날의 공통점' 은 찾을 수 있지만 그 공통점이 다음
기간에 유지되지 않는다. 그래서 과거로 더 파는 대신 이 파일을 만든다.

이 파일이 하는 일은 딱 하나다: **기준을 먼저 얼려놓고, 앞으로 채점한다.**

기록하는 규칙은 둘이다.

  (A) 얼린 종합 게이트   지표 13개를 표준화해 평균낸 점수. 하위 20% 면 쉼.
  (B) 전날 하락이면 쉼    계수가 없어 얼릴 것도 없는 단순 규칙.
      과거 탐색에서 유일하게 맥박이 있었다 (보유 1일 연도별 부호 6/6 유지,
      전체 t=-2.39). 다만 무작위로 같은 비율을 쉬어도 누적 18.0% / 최대낙폭
      12.7% 확률로 더 좋았으므로 '노출을 줄인 것' 과 구별되지 않았다.
      그래서 이것도 앞으로 따로 채점한다.

  --freeze  오늘까지의 데이터로 게이트 계수를 정하고 파일에 얼린다.
            한 번 얼리면 다시 바꾸지 않는다 (--force 없이는 덮어쓰기 거부).
            이걸 나중에 고치면 앞검증이 아니라 그냥 백테스트가 된다.
  --record  매일 그날의 종목 선정 결과와 게이트 점수/판정을 기록한다.
  --settle  보유기간이 지난 회차의 실제 수익률을 채운다.
  --score   게이트가 맞았는지 채점한다.

중요 - 게이트가 '쉼' 이라고 한 날도 회차를 기록하고 수익률을 채운다.
쉰 날의 결과를 안 남기면 "쉰 게 맞았나" 를 영영 확인할 수 없다. 판정은
기록만 하고, 실제로 계산에서 빼지는 않는다.

얼마나 기다려야 답이 나오나 (과거 표본으로 계산한 값):

  보유  5일  회차당 표준편차 2.41%  ->  1.0%p 차이를 확인하려면 회차 46개 = 약 0.9년
  보유 20일  회차당 표준편차 4.62%  ->  1.0%p 차이를 확인하려면 회차 167개 = 약 13.4년

  보유 20일에서 게이트가 정말 1%p 를 보태는지 회차 단위로 확인하려면 13년이
  걸린다. 그래서 이 파일은 두 가지를 따로 채점한다.
    (1) 점수-결과 상관   매일 기록되므로 1년이면 읽을 만해진다
    (2) 쉼 판정의 효과    회차 단위. 위 표대로 훨씬 오래 걸린다
  (1) 이 0 근처면 (2) 를 기다릴 이유가 없다는 게 조기 판정 기준이다.

주문은 내지 않는다. 이 파일은 패널 CSV 만 읽고 CSV 만 쓴다.

실행:
    python paper_trade.py --freeze
    python paper_trade.py --record --settle
    python paper_trade.py --score
"""
import argparse
import csv
import glob
import json
import math
import statistics as st
import sys
from datetime import datetime

import market_indicators as mi
import strategy as S
import yearly_csv
from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
PREFIX = "paper_trades"
GATE_PATH = DATA_DIR / "gate_frozen.json"

FACTOR = "low_vol"
TOP_N = 10
HOLDS = (5, 20)
KEY_FIELDS = ("date", "hold_days")

# 게이트가 '쉼' 이라고 부를 하위 비율. 얼릴 때 같이 고정한다.
SKIP_PCT = 0.20

# 컬럼은 항상 맨 끝에 추가한다 (yearly_csv 문서 참고).
FIELDS = [
    "date", "hold_days", "exit_date",
    "picks",                 # 종목코드 세미콜론 구분
    "gate_score",            # 얼린 게이트의 점수 (높을수록 좋은 날)
    "gate_verdict",          # 투자 / 쉼  - 미리 정한 기준에 따른 판정
    "realized_pct",          # 실제 수익률 (수수료 차감). 청산일이 지나야 채워짐
    "delisted",              # 보유 중 데이터가 끊긴 종목 수
    "settled_at",            # 수익률을 채운 시각
] + mi.PREDICTOR_FIELDS + [  # 그날 지표를 같이 남긴다 (나중에 재분석용)
    # (2026-09-17 추가, 반드시 맨 끝) 13개 지표에는 '전날 시장 1일 등락' 이
    # 없었다. kr_ret5 는 5일 수익률이다. 그런데 탐색에서 유일하게 맥박이
    # 있었던 규칙이 '전날 하락이면 쉼' 이었다 (보유 1일 연도별 부호 6/6
    # 유지, 전체 t=-2.39). 다만 무작위로 같은 비율을 쉬어도 18% 는 더
    # 좋았으므로 노출 감소와 구별되지 않았다.
    # 그래서 이것도 앞으로 따로 채점한다. 얼린 게이트는 건드리지 않는다 -
    # 계수를 다시 맞추면 앞검증이 아니게 되므로, 이 규칙은 계수가 필요
    # 없는 별개의 판정으로 나란히 기록만 한다.
    "prev_c2c",              # 전날 시장 종가대비 등락 (오늘 장 전에 확정)
    "rule_prevdown",         # 투자 / 쉼  - '전날 하락이면 쉼' 규칙의 판정
]


# --------------------------------------------------------------- 게이트 얼리기
def freeze(force: bool = False) -> dict | None:
    """오늘까지의 데이터로 게이트를 정하고 파일에 얼린다."""
    if GATE_PATH.exists() and not force:
        print(f"[!] 이미 얼려져 있습니다: {GATE_PATH.name}")
        print("    덮어쓰면 앞검증이 무의미해집니다. 정말 바꿀 때만 --force.")
        return None

    dates, panel = S.load_panel()
    day_vals = S.load_day_scores()
    keys = mi.PREDICTOR_FIELDS

    # 게이트가 맞혀야 하는 것은 '시장의 등락' 이 아니라 '이 전략의 회차 수익' 이다.
    # 그래서 매일 진입했다고 보고 회차를 겹쳐서 만들어 학습 표본을 늘린다.
    # 겹치므로 독립 표본은 (일수 / 보유일) 임을 잊지 말아야 한다.
    hold = HOLDS[-1]
    outcome = {}
    start = max(140, S.LIQUIDITY_DAYS + 2)
    for di in range(start, len(dates) - hold):
        r = _round_return(panel, di, di + hold)
        if r is not None:
            outcome[dates[di]] = r[0]

    usable = [d for d in sorted(outcome)
              if d in day_vals and all(day_vals[d][k] is not None for k in keys)]
    if len(usable) < 50:
        print(f"[!] 표본이 {len(usable)}개뿐입니다. 얼릴 수 없습니다.")
        return None

    stats, signs = {}, {}
    ys = [outcome[d] for d in usable]
    my = st.mean(ys)
    for k in keys:
        xs = [day_vals[d][k] for d in usable]
        m, sd = st.mean(xs), (st.pstdev(xs) or 1.0)
        stats[k] = [m, sd]
        cov = sum((x - m) * (y - my) for x, y in zip(xs, ys))
        signs[k] = 1.0 if cov >= 0 else -1.0

    scores = sorted(_score_with(day_vals[d], keys, signs, stats) for d in usable)
    cut = scores[int(len(scores) * SKIP_PCT)]
    fitted = [_score_with(day_vals[d], keys, signs, stats) for d in usable]
    train_corr = _corr(fitted, ys)

    gate = {
        "frozen_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": "한 번 얼린 뒤 고치면 앞검증이 아니다. 고쳐야 하면 새 파일을 만들 것.",
        "factor": FACTOR, "top_n": TOP_N, "hold_days_fitted": hold,
        "keys": keys, "signs": signs, "stats": stats,
        "skip_pct": SKIP_PCT, "skip_below": cut,
        "train_from": usable[0], "train_to": usable[-1],
        "train_n": len(usable),
        "train_n_independent": len(usable) // hold,
        "train_corr": train_corr,
    }
    DATA_DIR.mkdir(exist_ok=True)
    with open(GATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(gate, fh, ensure_ascii=False, indent=2)

    print(f"[얼림] {GATE_PATH.name}")
    print(f"  학습 구간 {usable[0]} ~ {usable[-1]}  회차 {len(usable)}개 "
          f"(독립 표본 약 {len(usable)//hold}개)")
    print(f"  학습 구간 상관 {train_corr:+.3f}  <- 이 값은 '맞춘' 값이라 성능이 아니다")
    print(f"  하위 {int(SKIP_PCT*100)}% ({cut:+.3f} 미만) 를 '쉼' 으로 부른다")
    print("  각 지표의 방향:")
    for k in keys:
        print(f"    {k:<14} {'+' if signs[k] > 0 else '-'}")
    return gate


def load_gate() -> dict | None:
    if not GATE_PATH.exists():
        return None
    with open(GATE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def load_prev_c2c() -> dict:
    """날짜 -> 전날 시장 종가대비 등락.

    result_c2c 는 '그날' 결과라 그날 예측에 쓰면 미래 정보다. 전날 것을
    가져오면 오늘 장이 열리기 전에 확정된 값이 된다.
    """
    out = {}
    rows = {}
    for path in sorted(glob.glob(str(DATA_DIR / f"{mi.PREFIX}_*.csv"))):
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                rows[r["date"]] = r
    days = sorted(rows)
    for i, d in enumerate(days):
        if i == 0:
            continue
        try:
            out[d] = float(rows[days[i - 1]]["result_c2c"])
        except (TypeError, ValueError, KeyError):
            pass
    return out


def _score_with(vals, keys, signs, stats) -> float | None:
    if not vals or any(vals.get(k) is None for k in keys):
        return None
    return st.mean([signs[k] * (vals[k] - stats[k][0]) / stats[k][1]
                    for k in keys])


def gate_score(gate: dict, vals: dict) -> float | None:
    return _score_with(vals, gate["keys"], gate["signs"], gate["stats"])


# ------------------------------------------------------------------- 회차 계산
def _picks_at(panel, di) -> list:
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    sc = [(S.factor_score(panel, c, di, FACTOR), c) for c in cand]
    sc = [(s, c) for s, c in sc if s is not None]
    if len(sc) < TOP_N:
        return []
    sc.sort(reverse=True)
    return [c for _s, c in sc[:TOP_N]]


def _round_return(panel, entry_di, exit_di, picks=None):
    """(수익률%, 끊김수). 계산 불가면 None."""
    if picks is None:
        picks = _picks_at(panel, entry_di)
    if not picks:
        return None
    rets, cuts = [], 0
    for c in picks:
        r, cut = S.trade_return(panel, c, entry_di, exit_di)
        if r is None:
            continue
        rets.append(r)
        cuts += bool(cut)
    if not rets:
        return None
    return st.mean(rets) - S.FEE_ROUND_TRIP_PCT, cuts


def _corr(xs, ys):
    if len(xs) < 10:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


# ---------------------------------------------------------------------- 기록
def record(verbose: bool = True) -> int:
    """패널의 마지막 날짜에 대해 회차를 기록한다. 이미 있으면 건너뛴다."""
    gate = load_gate()
    if gate is None:
        print("[!] 게이트가 아직 안 얼려져 있습니다. --freeze 를 먼저 하세요.")
        return 0

    dates, panel = S.load_panel(verbose=verbose)
    day_vals = S.load_day_scores()
    prev = load_prev_c2c()
    rows = yearly_csv.load_rows(DATA_DIR, PREFIX, KEY_FIELDS)

    di = len(dates) - 1
    d = dates[di]
    vals = day_vals.get(d, {})
    sc = gate_score(gate, vals)
    pc = prev.get(d)
    added, touched = 0, set()

    for hold in HOLDS:
        key = (d, str(hold))
        if key in rows:
            continue
        picks = _picks_at(panel, di)
        if not picks:
            if verbose:
                print(f"[기록] {d} 보유{hold}일: 후보가 모자라 건너뜀")
            continue
        row = {f: "" for f in FIELDS}
        row["date"] = d
        row["hold_days"] = str(hold)
        row["exit_date"] = ""          # 청산일은 --settle 때 확정된다
        row["picks"] = ";".join(picks)
        row["gate_score"] = f"{sc:.4f}" if sc is not None else ""
        row["gate_verdict"] = ("" if sc is None else
                               ("쉼" if sc < gate["skip_below"] else "투자"))
        row["realized_pct"] = ""
        row["delisted"] = ""
        row["settled_at"] = ""
        for k in mi.PREDICTOR_FIELDS:
            v = vals.get(k)
            row[k] = "" if v is None else f"{v:g}"
        # '전날 하락이면 쉼' 규칙은 계수가 없으므로 부호만 보면 된다.
        row["prev_c2c"] = "" if pc is None else f"{pc:g}"
        row["rule_prevdown"] = "" if pc is None else ("쉼" if pc < 0 else "투자")
        rows[key] = row
        touched.add(d[:4])
        added += 1
        if verbose:
            print(f"[기록] {d} 보유{hold}일 {len(picks)}종목 "
                  f"점수 {row['gate_score'] or '-'} 판정 {row['gate_verdict'] or '-'}"
                  f" / 전날 {row['prev_c2c'] or '-'}% -> "
                  f"{row['rule_prevdown'] or '-'}")

    if added:
        bad = yearly_csv.check_header(DATA_DIR, PREFIX, FIELDS)
        if bad:
            print(f"[!] 헤더가 다른 파일: {bad} - 컬럼을 가운데 끼워넣지 않았는지 확인")
        yearly_csv.write_years(DATA_DIR, PREFIX, FIELDS, rows, touched)
    elif verbose:
        print(f"[기록] {d} 은 이미 기록되어 있습니다")
    return added


def settle(verbose: bool = True) -> int:
    """보유기간이 지난 회차의 실제 수익률을 채운다."""
    dates, panel = S.load_panel(verbose=verbose)
    idx = {d: i for i, d in enumerate(dates)}
    rows = yearly_csv.load_rows(DATA_DIR, PREFIX, KEY_FIELDS)
    filled, touched = 0, set()

    for (d, hold_s), row in rows.items():
        if row.get("realized_pct"):
            continue
        hold = int(hold_s)
        entry_di = idx.get(d)
        if entry_di is None or entry_di + hold >= len(dates):
            continue
        picks = [c for c in (row.get("picks") or "").split(";") if c]
        out = _round_return(panel, entry_di, entry_di + hold, picks)
        if out is None:
            continue
        ret, cuts = out
        row["exit_date"] = dates[entry_di + hold]
        row["realized_pct"] = f"{ret:.4f}"
        row["delisted"] = str(cuts)
        row["settled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        touched.add(d[:4])
        filled += 1

    if filled:
        yearly_csv.write_years(DATA_DIR, PREFIX, FIELDS, rows, touched)
    if verbose:
        print(f"[청산] {filled}개 회차의 수익률을 채웠습니다")
    return filled


# ---------------------------------------------------------------------- 채점
def score(verbose: bool = True) -> dict:
    gate = load_gate()
    rows = yearly_csv.load_rows(DATA_DIR, PREFIX, KEY_FIELDS)
    out = {}
    if gate is None:
        print("[!] 얼린 게이트가 없습니다.")
        return out

    print(f"\n=== 앞검증 채점 (게이트 얼린 날 {gate['frozen_at'][:10]}) ===")
    print(f"  학습 구간 {gate['train_from']} ~ {gate['train_to']}, "
          f"학습 상관 {gate['train_corr']:+.3f}")
    print("  아래 숫자는 얼린 날 이후에 기록된 것만 센다 - 그래야 앞검증이다.\n")

    frozen_day = gate["frozen_at"][:10].replace("-", "")
    for hold in HOLDS:
        done = [r for (d, h), r in rows.items()
                if h == str(hold) and r.get("realized_pct") and d > frozen_day]
        print(f"  [보유 {hold}일]  기록 {len(done)}개")
        if len(done) < 10:
            need_corr = 250 // 1
            print(f"    아직 채점할 수 없습니다. 상관을 읽으려면 대략 "
                  f"{need_corr}개(약 1년), 쉼 판정의 효과를 보려면 "
                  f"{'46개(약 0.9년)' if hold == 5 else '167개(약 13년)'} 필요합니다.")
            continue
        xs = [float(r["gate_score"]) for r in done if r.get("gate_score")]
        ys = [float(r["realized_pct"]) for r in done if r.get("gate_score")]
        c = _corr(xs, ys)
        inv = [float(r["realized_pct"]) for r in done if r["gate_verdict"] == "투자"]
        skip = [float(r["realized_pct"]) for r in done if r["gate_verdict"] == "쉼"]
        print(f"    (1) 점수-결과 상관 {c:+.3f}" if c is not None
              else "    (1) 상관: 표본 부족")
        print(f"    (2) 게이트가 '투자' 라 한 회차  {len(inv):>4}개 "
              f"평균 {st.mean(inv):+.3f}%" if inv else "    (2) 투자 회차 없음")
        if skip:
            print(f"        게이트가 '쉼' 이라 한 회차  {len(skip):>4}개 "
                  f"평균 {st.mean(skip):+.3f}%")
            gap = st.mean(inv) - st.mean(skip) if inv else None
            if gap is not None:
                print(f"        차이 {gap:+.3f}%p  <- 양수여야 게이트가 일한 것이다")
        else:
            print("        게이트가 '쉼' 이라 한 회차 없음")

        # '전날 하락이면 쉼' 도 나란히 채점한다. 과거에서 유일하게 맥박이
        # 있었던 규칙이고, 계수가 없으니 얼릴 것도 없다. 대조군(무작위로
        # 같은 만큼 쉼)은 analyze_skip_rules.judge_exposure 로 볼 것 -
        # 노출 감소와 구별되는지가 이 규칙의 관문이다.
        p_inv = [float(r["realized_pct"]) for r in done
                 if r.get("rule_prevdown") == "투자"]
        p_skip = [float(r["realized_pct"]) for r in done
                  if r.get("rule_prevdown") == "쉼"]
        if p_inv and p_skip:
            print(f"    (3) 전날상승 '투자' {len(p_inv):>4}개 "
                  f"평균 {st.mean(p_inv):+.3f}%  /  "
                  f"전날하락 '쉼' {len(p_skip):>4}개 평균 {st.mean(p_skip):+.3f}%")
            print(f"        차이 {st.mean(p_inv)-st.mean(p_skip):+.3f}%p  "
                  f"<- 양수여야 이 규칙이 일한 것이다")
        else:
            print("    (3) 전날 등락 기록이 아직 양쪽으로 모이지 않았다")

        out[hold] = {"n": len(done), "corr": c,
                     "invest": st.mean(inv) if inv else None,
                     "skip": st.mean(skip) if skip else None,
                     "prevdown_invest": st.mean(p_inv) if p_inv else None,
                     "prevdown_skip": st.mean(p_skip) if p_skip else None}
    print(CAUTION)
    return out


CAUTION = """
[채점 결과를 볼 때]
  - 게이트가 '쉼' 이라 한 날도 회차를 기록하고 수익률을 채운다. 그래야
    "쉰 게 맞았나" 를 확인할 수 있다. 실제로 빼지는 않는다.
  - 상관이 0 근처로 계속 나오면 그 자체가 결론이다. 회차가 쌓일 때까지
    기다릴 필요 없이 게이트를 버리는 근거가 된다.
  - 반대로 상관이 양수로 나와도, 보유 20일에서 '쉼' 의 효과를 회차 단위로
    확인하려면 167회차(약 13년)가 필요하다. 짧은 기간의 회차 평균 차이는
    읽지 않는 것이 맞다.
  - 겹치는 회차(매일 진입)를 세므로 독립 표본은 (회차 / 보유일) 이다.
  - (3) '전날 하락이면 쉼' 이 좋아 보이더라도, 그것만으로는 부족하다. 이
    규칙은 회차의 약 40%를 쉬므로 노출이 줄고, 노출만으로도 결과가 움직인다.
    analyze_skip_rules.judge_exposure 로 '무작위로 같은 만큼 쉰 경우' 의
    분포와 비교해야 한다. 과거 데이터에서는 그 대조군을 통과하지 못했다
    (무작위가 누적 18.0%, 최대낙폭 12.7% 확률로 더 좋았다).
"""


def main() -> int:
    p = argparse.ArgumentParser(description="전략 모의 진행 + 나쁜날 게이트 앞검증")
    p.add_argument("--freeze", action="store_true", help="게이트 계수를 얼린다 (한 번만)")
    p.add_argument("--force", action="store_true", help="얼린 게이트를 덮어쓴다")
    p.add_argument("--record", action="store_true", help="오늘 회차를 기록한다")
    p.add_argument("--settle", action="store_true", help="지난 회차의 수익률을 채운다")
    p.add_argument("--score", action="store_true", help="게이트를 채점한다")
    a = p.parse_args()

    if not any([a.freeze, a.record, a.settle, a.score]):
        a.record = a.settle = a.score = True

    if a.freeze:
        freeze(force=a.force)
    if a.record:
        record()
    if a.settle:
        settle()
    if a.score:
        score()
    return 0


if __name__ == "__main__":
    sys.exit(main())
