"""당일 신호 비교 및 거래 결정 스크립트

09:30~10:00에 수집한 당일 신호와
전날 신호를 비교하여 거래 여부를 판단합니다.

실행 시간: 10:00~10:05 (시장 개장 후 30분 내)
"""
import json
import glob
from datetime import datetime, timedelta
from pathlib import Path
import statistics as st

import strategy as S


def load_latest_signals():
    """가장 최신 당일 신호 로드."""
    data_dir = S.BASE_DIR / "data"

    # 오늘 신호 찾기
    today_str = datetime.now().strftime('%Y%m%d')
    today_signal_file = data_dir / f"today_signals_{today_str}.json"

    if not today_signal_file.exists():
        print(f"⚠️  오늘 신호 파일 없음: {today_signal_file}")
        return None

    try:
        with open(today_signal_file, 'r', encoding='utf-8') as f:
            today_signals = json.load(f)
        return today_signals
    except Exception as e:
        print(f"⚠️  신호 파일 읽기 오류: {e}")
        return None


def load_signal_history():
    """신호 이력 파일 로드."""
    data_dir = S.BASE_DIR / "data"
    signal_history_file = data_dir / "signal_history.json"

    if not signal_history_file.exists():
        return {}

    try:
        with open(signal_history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        return history
    except Exception as e:
        print(f"⚠️  이력 파일 읽기 오류: {e}")
        return {}


def get_yesterday_signals(history):
    """어제 신호 가져오기."""
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    if yesterday_str not in history:
        print(f"⚠️  어제 신호 없음: {yesterday_str}")
        return None

    return history[yesterday_str]


def save_signal_to_history(today_signals):
    """오늘 신호를 이력에 저장."""
    data_dir = S.BASE_DIR / "data"
    signal_history_file = data_dir / "signal_history.json"

    history = load_signal_history()
    today_str = datetime.now().strftime('%Y-%m-%d')

    # 간단히 지표 부분만 저장
    history[today_str] = today_signals.get("indicators", {})

    try:
        with open(signal_history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        print(f"✅ 신호 이력 저장: {signal_history_file}")
    except Exception as e:
        print(f"⚠️  이력 저장 오류: {e}")


def extract_signal_state(indicators):
    """지표 딕셔너리에서 신호 상태 추출."""
    signals = {}

    for key in ["OVN", "SPX", "IXIC", "SOX", "VIX", "KRW", "FLOW"]:
        if key in indicators and indicators[key]:
            bullish = indicators[key].get("bullish")
            if bullish is not None:
                signals[key] = bullish

    return signals


def calculate_alignment_score(signals):
    """신호에서 정렬도 계산 (0~7)."""
    if not signals:
        return 0
    return sum(1 for v in signals.values() if v)


def compare_signals(yesterday_signals, today_signals):
    """전날 신호와 당일 신호 비교."""
    print("\n" + "=" * 80)
    print("신호 비교 분석")
    print("=" * 80)

    yesterday_states = extract_signal_state(yesterday_signals) if yesterday_signals else {}
    today_states = extract_signal_state(today_signals) if today_signals else {}

    if not yesterday_states:
        print("❌ 어제 신호 없음 - 비교 불가")
        return None

    if not today_states:
        print("❌ 오늘 신호 없음 - 비교 불가")
        return None

    # 신호별 일치도 분석
    print("\n[지표별 신호 변화]")
    agreements = []
    reversals = []

    for key in yesterday_states.keys():
        yesterday_bullish = yesterday_states[key]
        today_bullish = today_states.get(key)

        if today_bullish is None:
            continue

        agreement = yesterday_bullish == today_bullish

        direction_str = "📈 강세" if yesterday_bullish else "📉 약세"
        today_direction = "📈 강세" if today_bullish else "📉 약세"
        status = "✓ 일치" if agreement else "✗ 반전"

        print(f"  {key}: 어제 {direction_str} → 오늘 {today_direction} {status}")

        if agreement:
            agreements.append(key)
        else:
            reversals.append(key)

    # 정렬도 계산
    yesterday_align = calculate_alignment_score(yesterday_states)
    today_align = calculate_alignment_score(today_states)

    agreement_rate = len(agreements) / len(yesterday_states) if yesterday_states else 0

    print(f"\n[정렬도]")
    print(f"  어제: {yesterday_align}/{len(yesterday_states)}")
    print(f"  오늘: {today_align}/{len(today_states)}")
    print(f"  신호 일치율: {len(agreements)}/{len(yesterday_states)} ({agreement_rate*100:.1f}%)")

    return {
        "yesterday_signals": yesterday_states,
        "today_signals": today_states,
        "agreements": agreements,
        "reversals": reversals,
        "yesterday_alignment": yesterday_align,
        "today_alignment": today_align,
        "agreement_rate": agreement_rate,
        "agreement_count": len(agreements),
        "total_signals": len(yesterday_states),
    }


def determine_trade_decision(comparison, yesterday_signals):
    """거래 결정 로직."""
    if not comparison:
        return None

    print("\n" + "=" * 80)
    print("거래 결정")
    print("=" * 80)

    agreement_rate = comparison["agreement_rate"]
    yesterday_align = comparison["yesterday_alignment"]
    today_align = comparison["today_alignment"]

    # 결정 로직:
    # 1. 신호 일치율이 높을수록 신뢰도 증가
    # 2. 어제 약세(0-2/7) + 오늘도 약세 + 일치율 높음 → BUY 추천 (+0.592% 기대)
    # 3. 어제 강세(5-7/7) + 오늘도 강세 + 일치율 높음 → SELL 추천 (하지만 손실 가능성)
    # 4. 신호 혼합 → HOLD 추천

    yesterday_bullish_count = sum(1 for v in comparison["yesterday_signals"].values() if v)

    # 약세 신호 (0-3/7)
    if yesterday_bullish_count <= 3:
        signal_type = "약세 (BEARISH)"
        if agreement_rate >= 0.71 and today_align <= 3:  # 약세 유지
            decision = "BUY"
            confidence = min(100, (agreement_rate * 100))
            expected_return = 0.592  # 기대 수익률
            win_rate = 81.8  # 승률
            reason = "약세 신호 강하고 오늘도 유지 → 손실 최소화 기대"
        elif agreement_rate >= 0.57:
            decision = "HOLD"
            confidence = agreement_rate * 100
            expected_return = 0.002  # 중립
            win_rate = 50
            reason = "약세 신호지만 일부 반전 → 조심스러운 진입"
        else:
            decision = "HOLD"
            confidence = agreement_rate * 100
            expected_return = 0.0
            win_rate = 50
            reason = "약세 신호지만 상당 부분 반전 → 신뢰도 낮음"

    # 강세 신호 (4-7/7)
    elif yesterday_bullish_count >= 4:
        signal_type = "강세 (BULLISH)"
        if agreement_rate >= 0.71 and today_align >= 4:  # 강세 유지
            decision = "SELL"  # 또는 HOLD/매수 회피
            confidence = min(100, (agreement_rate * 100))
            expected_return = -0.220  # 손실 기대
            win_rate = 45
            reason = "강세 신호 강하고 오늘도 유지 → 손실 위험"
        elif agreement_rate >= 0.57:
            decision = "HOLD"
            confidence = agreement_rate * 100
            expected_return = 0.26
            win_rate = 55
            reason = "강세 신호지만 일부 반전 → 중립"
        else:
            decision = "HOLD"
            confidence = agreement_rate * 100
            expected_return = 0.0
            win_rate = 50
            reason = "강세 신호지만 상당 부분 반전 → 신뢰도 낮음"

    # 혼합 신호 (정확히 3-4/7)
    else:
        signal_type = "혼합"
        decision = "HOLD"
        confidence = agreement_rate * 100
        expected_return = 0.002
        win_rate = 50
        reason = "지표 혼합 → 신뢰도 낮음"

    print(f"\n신호 유형: {signal_type}")
    print(f"어제 정렬도: {yesterday_bullish_count}/7")
    print(f"신호 일치율: {agreement_rate*100:.1f}%")

    print(f"\n🎯 거래 결정: {decision}")
    print(f"신뢰도: {confidence:.1f}%")
    print(f"이유: {reason}")
    print(f"\n기대값:")
    print(f"  기대 수익률: {expected_return*100:+.3f}%")
    print(f"  승률: {win_rate:.1f}%")

    return {
        "decision": decision,
        "confidence": confidence,
        "signal_type": signal_type,
        "yesterday_alignment": yesterday_bullish_count,
        "today_alignment": today_align,
        "agreement_rate": agreement_rate,
        "expected_return": expected_return,
        "win_rate": win_rate,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }


def save_trade_decision(decision):
    """거래 결정 저장."""
    data_dir = S.BASE_DIR / "data"
    decision_file = data_dir / f"trade_decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        with open(decision_file, 'w', encoding='utf-8') as f:
            json.dump(decision, f, indent=2, ensure_ascii=False)
        print(f"\n✅ 거래 결정 저장: {decision_file}")
        return decision_file
    except Exception as e:
        print(f"⚠️  결정 저장 오류: {e}")
        return None


def main():
    print("\n" + "=" * 80)
    print("당일 신호 비교 및 거래 결정 (10:00 ~ 10:05)")
    print("=" * 80)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 신호 로드
    print("[1] 신호 로드...")
    today_signals = load_latest_signals()
    if not today_signals:
        print("❌ 오늘 신호 없음 - 종료")
        return 1

    print(f"✅ 오늘 신호 로드 완료")

    # 2. 어제 신호 로드
    print("\n[2] 어제 신호 로드...")
    history = load_signal_history()
    yesterday_signals = get_yesterday_signals(history)
    if not yesterday_signals:
        print("⚠️  어제 신호 없음 - 첫 거래일이거나 이력이 없습니다")
        print("    오늘 신호만 기록하고 종료합니다")
        save_signal_to_history(today_signals)
        return 0

    print(f"✅ 어제 신호 로드 완료")

    # 3. 신호 비교
    print("\n[3] 신호 비교...")
    comparison = compare_signals(yesterday_signals, today_signals)

    if not comparison:
        print("❌ 신호 비교 실패")
        return 1

    # 4. 거래 결정
    print("\n[4] 거래 결정...")
    decision = determine_trade_decision(comparison, yesterday_signals)

    if not decision:
        print("❌ 거래 결정 실패")
        return 1

    # 5. 결정 저장
    decision_file = save_trade_decision(decision)

    # 6. 오늘 신호를 이력에 저장 (내일을 위해)
    save_signal_to_history(today_signals)

    # 최종 요약
    print("\n" + "=" * 80)
    print("📌 다음 단계")
    print("=" * 80)

    if decision["decision"] == "BUY":
        print("\n🟢 10:05 이후 매수 준비:")
        print(f"   - 신뢰도: {decision['confidence']:.1f}%")
        print(f"   - 기대 수익률: {decision['expected_return']*100:+.3f}%")
        print(f"   - 예상 승률: {decision['win_rate']:.1f}%")
        print("\n   거래 스크립트: trade_execute_intraday.py 실행")
    elif decision["decision"] == "SELL":
        print("\n🔴 거래 회피:")
        print(f"   - 이유: {decision['reason']}")
        print(f"   - 예상 손실: {decision['expected_return']*100:+.3f}%")
    else:
        print("\n🟡 관망:")
        print(f"   - 이유: {decision['reason']}")
        print(f"   - 신뢰도 부족: {decision['confidence']:.1f}%")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
