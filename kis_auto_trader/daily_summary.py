"""
장마감 후 그날 매매 결과를 사람이 읽을 수 있게 정리한다 (2026-08-21).

daemon.py 가 매일 저녁 evening_screen.py 를 실행할 때 이 요약을 먼저 출력하고
logs/daily_summary.log 에 남긴다 - "오늘 결과를 정리하고, 그 경험을 반영해서
다음날 종목을 고른다"는 흐름을 한 곳에서 보이게 하기 위함. 실제로 그 경험을
다음날 선정에 반영하는 판단 로직 자체는 loss_cooldown.py 가 담당하고,
evening_screen.py 가 바로 이어서 부르는 auto_pick_and_apply() 안에 이미
연결돼 있다 - 이 요약은 그 판단 근거를 사람이 확인할 수 있게 보여주는 역할.
"""
import csv
from datetime import datetime

import loss_cooldown
from common import LOG_DIR, TRADE_LOG_PATH

DAILY_SUMMARY_PATH = LOG_DIR / "daily_summary.log"


def _code_name_map() -> dict:
    names = {}
    if not TRADE_LOG_PATH.exists():
        return names
    with open(TRADE_LOG_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("code") and row.get("name"):
                names[row["code"]] = row["name"]
    return names


def build_summary(today: datetime | None = None) -> str:
    """오늘자 매매 결과 + 그 경험이 다음날 후보 선정에 어떻게 반영되는지를
    사람이 읽을 수 있는 텍스트로 만든다."""
    today = today or datetime.now()
    today_str = today.strftime("%Y-%m-%d")

    rows = []
    if TRADE_LOG_PATH.exists():
        with open(TRADE_LOG_PATH, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row.get("side") == "sell" and row.get("realized_pnl") and row["timestamp"][:10] == today_str:
                    rows.append(row)

    lines = [f"===== {today_str} 매매 결과 요약 ====="]
    if not rows:
        lines.append("오늘 체결된 매도 기록이 없습니다.")
    else:
        pnls = [float(r["realized_pnl"]) for r in rows]
        total = sum(pnls)
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p < 0)
        lines.append(f"실현손익 합계: {total:+,.0f}원 ({wins}승 {losses}패, 총 {len(rows)}건)")
        for r in rows:
            pnl = float(r["realized_pnl"])
            lines.append(f"  - {r['timestamp'][11:16]} {r['name']}({r['code']}) {pnl:+,.0f}원 ({r['note']})")

    names = _code_name_map()
    recent_excluded = loss_cooldown.recent_loss_excluded_codes(today=today)
    lifetime_excluded = loss_cooldown.lifetime_loss_excluded_codes()
    all_excluded = recent_excluded | lifetime_excluded
    if all_excluded:
        lines.append("이 경험을 반영해 다음날 후보 선정에서 제외되는 종목:")
        for code in sorted(all_excluded):
            reasons = []
            if code in recent_excluded:
                reasons.append(f"최근 {loss_cooldown.LOOKBACK_TRADING_DAYS}거래일 반복 손실")
            if code in lifetime_excluded:
                reasons.append("전체 기록 누적 손실")
            name = names.get(code, code)
            lines.append(f"  - {name}({code}): {', '.join(reasons)}")
    else:
        lines.append("현재 손실 이력으로 제외되는 종목 없음.")

    lines.append("=" * 40)
    return "\n".join(lines)


def write_summary(today: datetime | None = None) -> str:
    """요약을 만들어서 logs/daily_summary.log 에 이어붙이고, 그 텍스트를 그대로 돌려준다
    (evening_screen.py 가 콘솔에도 그대로 출력해서 daemon 의 run_console.log 에도 남게 한다)."""
    text = build_summary(today)
    try:
        with open(DAILY_SUMMARY_PATH, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")
    except Exception:
        pass
    return text
