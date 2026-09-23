"""매수/매도 타이밍을 이메일로 알린다.

(2026-09-17 신설) 사용자 요청: "그런 기회가 온다면 프로그램상 메일로
사용자에게 이제 매수 타이밍이다 매도 타이밍이다 이렇게 알려주면 될거고"

이 파일은 두 가지를 구분해서 보낸다. 섞으면 검증된 것과 아닌 것이 같은
무게로 읽히고, 그게 가장 위험한 실패 방식이다.

  [1] 검증된 것 - 월 1회 리밸런스 알림
      저변동 10종목 / 20거래일 보유. strategy.py 에서 검증했다.
      5.5년 62회차 평균 +1.054%, 기준선 -0.454%, 초과 +1.51%p.
      반기 분할·폐지 -50%·수수료 1.0%·종목수 3~30·유니버스 100~400 전부
      통과. 6년 중 5년 초과 양수.
      -> 리밸런스 예정일에 종목 목록을 보낸다. 이게 이 알림의 본체다.

  [2] 검증 안 된 것 - 수급 신호 현재 상태 (참고용)
      종목별 기관/외국인/개인 순매수 신호가 지금 어느 분위에 있는지.
      analyze_extremes.py 에서 대조군 탈락했다 (밀어놓기 우연 20.0%).
      게다가 이득의 대부분은 지표가 아니라 '손실 중엔 안 팔기' 설계가
      만든 것이었고, 그 설계는 하락장에서 416거래일 물려 있게 만들었다.
      -> 그래서 '매수하라' 고 쓰지 않는다. 상태만 적어 보낸다.

리밸런스 주기는 고정 기준일에서 20거래일 간격으로 센다. 기준일을 바꾸면
주기가 어긋나므로 ANCHOR 를 함부로 고치지 말 것.

주문은 내지 않는다. 패널 CSV 를 읽고 메일만 보낸다.

실행:
    python alert.py             # 오늘이 리밸런스일이면 보낸다
    python alert.py --force     # 오늘이 아니어도 지금 상태를 보낸다
    python alert.py --dry-run   # 보내지 않고 화면에만 출력
"""
import argparse
import statistics as st
import sys
from datetime import datetime

import strategy as S
from common import BASE_DIR

DATA_DIR = BASE_DIR / "data"
REBAL_DAYS = 20
# 리밸런스 주기를 세는 기준일. 이 날짜부터 20거래일 간격이 리밸런스일이다.
ANCHOR = "20260915"
FACTOR = "low_vol"
TOP_N = 10
LOOKBACK_FOR_QUANTILE = 250      # 수급 신호의 분위를 최근 몇 거래일로 볼지


def rebalance_due(dates: list, today: str) -> tuple[bool, int]:
    """(오늘이 리밸런스일인가, 다음 리밸런스까지 남은 거래일)"""
    if today not in dates or ANCHOR not in dates:
        return False, -1
    gap = dates.index(today) - dates.index(ANCHOR)
    if gap < 0:
        return False, -gap
    rem = (-gap) % REBAL_DAYS
    return gap % REBAL_DAYS == 0, rem


def current_picks(dates, panel) -> list:
    """오늘(패널 마지막 날) 기준 저변동 상위 10종목. 전날까지만 본다."""
    di = len(dates) - 1
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    scored = [(S.factor_score(panel, c, di, FACTOR), c) for c in cand]
    scored = [(s, c) for s, c in scored if s is not None]
    if len(scored) < TOP_N:
        return []
    scored.sort(reverse=True)
    return [c for _s, c in scored[:TOP_N]]


def name_of(panel_names: dict, code: str) -> str:
    return panel_names.get(code) or code


def flow_state(dates, panel, picks) -> dict:
    """종목별 수급 신호가 최근 분포에서 어느 분위에 있는지 (참고용).

    검증 안 된 신호다. 값만 알려주고 매매 지시는 하지 않는다.
    """
    import analyze_extremes as X

    codes = set(picks)
    flow = X.load_stock_flow(codes)
    if not flow:
        return {}
    # 최근 구간만 쓴다 (분위를 재려면 분포가 필요하고, 전 구간을 읽으면 느리다)
    recent = dates[-LOOKBACK_FOR_QUANTILE:]
    pick_map = {d: picks for d in recent}     # 분위 계산용 - 같은 바스켓 기준
    out = {}
    for which in ("기관", "외국인", "개인"):
        sig = X.basket_flow_signal(dates, panel, pick_map, flow, which)
        vals = [v for d, v in sig.items() if v is not None]
        today = sig.get(dates[-1])
        if today is None or len(vals) < 30:
            continue
        below = sum(1 for v in vals if v <= today)
        out[which] = {"value": today, "pct": below / len(vals) * 100,
                      "n": len(vals)}
    return out


def build_message(dates, panel, panel_names, force: bool) -> tuple:
    today = dates[-1]
    due, rem = rebalance_due(dates, today)
    picks = current_picks(dates, panel)
    if not picks:
        return None, None

    if not due and not force:
        return None, None

    head = "[리밸런스] 오늘 교체" if due else f"[참고] 다음 리밸런스까지 {rem}거래일"
    subject = f"{head} - 저변동 {TOP_N}종목 ({today})"

    lines = [
        f"기준일: {today} (패널 마지막 거래일)",
        "",
        "=" * 58,
        "[검증된 전략] 저변동 10종목 / 20거래일 보유 / 동일가중",
        "=" * 58,
        "5.5년 62회차 평균 +1.054%/회차, 기준선 -0.454%, 초과 +1.51%p.",
        "반기 분할·폐지 -50% 처리·수수료 1.0%·종목수 3~30·유니버스 100~400",
        "전부 통과. 6년 중 5년 초과 양수. MDD -17.8% (기준선 -59.6%).",
        "",
    ]
    if due:
        lines.append("오늘이 리밸런스일입니다. 아래 10종목으로 교체:")
    else:
        lines.append(f"오늘은 리밸런스일이 아닙니다 (남은 {rem}거래일). "
                     f"현재 기준 상위 10종목:")
    lines.append("")
    for i, c in enumerate(picks, 1):
        lines.append(f"  {i:>2}. {c}  {name_of(panel_names, c)}")
    lines += [
        "",
        "동일가중입니다 (규칙 5: 고정 비중 > 변동성 조절, +29.4% vs +0.5%).",
        "익절·손절을 걸지 마십시오 (규칙 2: 필요 승률 53~57%, 실제 43~49%).",
        "",
    ]

    state = flow_state(dates, panel, picks)
    if state:
        lines += [
            "=" * 58,
            "[검증 안 된 신호] 종목별 수급 현재 상태 - 참고용",
            "=" * 58,
            "아래는 매매 지시가 아닙니다. 대조군 탈락한 신호입니다",
            "(신호를 어긋나게 밀어놓아도 같은 성적이 20.0% 확률로 나왔습니다).",
            "이득의 대부분은 지표가 아니라 '손실 중엔 안 팔기' 설계가 만든",
            "것이었고, 그 설계는 하락장에서 416거래일 물려 있게 만들었습니다.",
            "",
        ]
        for which, s in state.items():
            lines.append(f"  전날 {which} 순매수: 최근 {s['n']}일 중 "
                         f"하위 {s['pct']:.0f}% 수준")
        lines += [
            "",
            "해석하지 말고 기록만 보십시오. paper_trade.py 가 매일 같은 값을",
            "남기고 있고, 몇 년 뒤 미리 정한 기준으로 채점할 수 있습니다.",
        ]

    lines += [
        "",
        "=" * 58,
        "이 메일은 관찰·계산 결과입니다. 주문은 자동으로 나가지 않습니다",
        "(api_client.py 에 주문 함수가 없습니다).",
    ]
    return subject, "\n".join(lines)


def run(force: bool = False, dry_run: bool = False) -> bool:
    dates, panel = S.load_panel(verbose=not dry_run)
    panel_names = _load_names()
    subject, body = build_message(dates, panel, panel_names, force)
    if subject is None:
        print(f"[알림] {dates[-1]} 은 리밸런스일이 아니어서 보내지 않습니다 "
              f"(--force 로 강제 발송).")
        return False
    print(f"제목: {subject}\n")
    print(body)
    return True


def _load_names() -> dict:
    """종목코드 -> 종목명. 패널 파일에서 마지막 연도만 읽어도 충분하다."""
    import csv
    import glob
    out = {}
    paths = sorted(glob.glob(str(DATA_DIR / f"{S.PANEL_PREFIX}_*.csv")))
    for path in paths[-1:]:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("code") and r.get("name"):
                    out[r["code"]] = r["name"]
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="매수/매도 타이밍 이메일 알림")
    p.add_argument("--force", action="store_true",
                   help="리밸런스일이 아니어도 현재 상태를 보낸다")
    p.add_argument("--dry-run", action="store_true",
                   help="보내지 않고 화면에만 출력")
    a = p.parse_args()
    run(force=a.force, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
