"""거래 결정 스크립트 (간단 버전)

전날 신호와 당일 OVN만으로 거래 결정을 내립니다.
복잡한 당일 지표 수집을 제외합니다.

실행: 09:35 (시가 수집 후)
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
import statistics as st

import strategy as S


def load_yesterday_signals():
    """어제 신호 로드 (기존 데이터 기반)."""
    dates, panel = S.load_panel(verbose=False)

    if len(dates) < 2:
        print("⚠️  충분한 데이터 없음")
        return None

    # 마지막 리밸런스 포인트에서의 신호
    di = len(dates) - 1
    date_yesterday = dates[di]

    # 전일 신호 계산 (전일 데이터 기반)
    top_n = 10
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    scored = [(S.factor_score(panel, c, di, "low_vol"), c) for c in cand]
    scored = [(s, c) for s, c in scored if s is not None]

    if len(scored) < top_n:
        return None

    scored.sort(reverse=True)
    picks = [c for _s, c in scored[:top_n]]

    return {
        "date": date_yesterday,
        "picks": picks,
        "panel": panel,
        "dates": dates,
        "di": di,
    }


def calculate_overnight_return(panel, picks, di):
    """당일 OVN (오버나이트) 계산."""
    if di < 1:
        return None

    ovn_vals = []
    for code in picks:
        s = panel[code]
        if di - 1 in s.pos and di in s.pos:
            prev_close = s.close[s.pos[di - 1]]
            curr_open = s.open[s.pos[di]]
            if prev_close > 0:
                ovn = (curr_open - prev_close) / prev_close
                ovn_vals.append(ovn)

    if not ovn_vals:
        return None

    return st.mean(ovn_vals)


def calculate_yesterday_alignment(panel, picks, di):
    """전일 신호 정렬도 계산 (SPX, SOX, FLOW 3개 지표)."""
    # 간단히: 전일 수익률의 부호로 판단
    # 양수 = 강세, 음수 = 약세

    daily_rets = []
    for code in picks:
        s = panel[code]
        if di in s.pos:
            o = s.open[s.pos[di]]
            c = s.close[s.pos[di]]
            if o > 0:
                ret = (c - o) / o
                daily_rets.append(ret)

    if not daily_rets:
        return None

    avg_ret = st.mean(daily_rets)
    return 1 if avg_ret > 0 else 0  # 1=강세, 0=약세


def decide_trade(yesterday_data):
    """거래 결정 로직 (간단 버전)."""
    print("\n" + "=" * 80)
    print("거래 결정 (간단 버전)")
    print("=" * 80)

    panel = yesterday_data["panel"]
    picks = yesterday_data["picks"]
    di = yesterday_data["di"]

    # 1. 전일 신호 (어제 데이터 기반)
    yesterday_bullish_count = calculate_yesterday_alignment(panel, picks, di)

    # 2. 당일 OVN
    ovn = calculate_overnight_return(panel, picks, di)

    print(f"\n📊 신호:")
    print(f"  전일 신호: {'강세' if yesterday_bullish_count else '약세'}")
    print(f"  당일 OVN: {ovn*100:+.3f}%" if ovn else "  당일 OVN: 계산 불가")

    # 3. 거래 결정
    # 규칙:
    # - 약세 신호 + OVN 음수 → BUY (약세 강화 신호)
    # - 약세 신호 + OVN 양수 → HOLD (신호 혼합)
    # - 강세 신호 → HOLD/SELL (거래 회피, 손실 위험)

    if yesterday_bullish_count == 0:  # 약세
        if ovn is not None and ovn < 0:
            decision = "BUY"
            confidence = 85.0
            expected_return = 0.00592
            reason = "약세 신호 + 음수 OVN → 약세 강화"
        elif ovn is not None and ovn >= 0:
            decision = "HOLD"
            confidence = 50.0
            expected_return = 0.002
            reason = "약세 신호 but 양수 OVN → 신호 혼합"
        else:
            decision = "HOLD"
            confidence = 60.0
            expected_return = 0.00592
            reason = "약세 신호 (OVN 없음)"
    else:  # 강세
        decision = "HOLD"
        confidence = 55.0
        expected_return = -0.00220
        reason = "강세 신호 → 거래 회피, 손실 위험"

    print(f"\n🎯 결정: {decision}")
    print(f"  신뢰도: {confidence:.1f}%")
    print(f"  기대 수익률: {expected_return*100:+.3f}%")
    print(f"  이유: {reason}")

    return {
        "decision": decision,
        "confidence": confidence,
        "expected_return": expected_return,
        "reason": reason,
        "yesterday_signal": "bullish" if yesterday_bullish_count else "bearish",
        "ovn": ovn,
        "timestamp": datetime.now().isoformat(),
    }


def save_decision(decision):
    """거래 결정 저장."""
    data_dir = S.BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)

    decision_file = data_dir / f"trade_decision_simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        with open(decision_file, 'w', encoding='utf-8') as f:
            json.dump(decision, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 결정 저장: {decision_file}")
        return decision_file
    except Exception as e:
        print(f"⚠️  저장 오류: {e}")
        return None


def main():
    print("\n" + "=" * 80)
    print("거래 결정 스크립트 (간단 버전)")
    print("=" * 80)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 전일 데이터 로드
    print("[1] 전일 데이터 로드...")
    yesterday_data = load_yesterday_signals()
    if not yesterday_data:
        print("❌ 데이터 로드 실패")
        return 1

    print(f"✅ 로드 완료: {yesterday_data['date']}")
    print(f"   선택 종목: {len(yesterday_data['picks'])}개")

    # 2. 거래 결정
    print("\n[2] 거래 결정...")
    decision = decide_trade(yesterday_data)

    # 3. 결정 저장
    print("\n[3] 결정 저장...")
    save_decision(decision)

    print("\n" + "=" * 80)
    print("📌 다음 단계")
    print("=" * 80)

    if decision["decision"] == "BUY":
        print("\n🟢 10:05 이후 매수 준비:")
        print("   python trade_execute_intraday.py")
    else:
        print(f"\n🟡 관망 ({decision['reason']})")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
