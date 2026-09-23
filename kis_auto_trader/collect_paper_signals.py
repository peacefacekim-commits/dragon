"""종이거래 신호 수집 스크립트 (Paper Trading Signals)

실거래 없이 매일 신호와 예상 수익률을 기록합니다.
충분한 데이터가 모이면 상관성 검증 후 실거래 시작합니다.

실행: 매일 09:35 (자동 또는 수동)
"""
import json
import csv
from datetime import datetime
from pathlib import Path
import statistics as st

import strategy as S


def load_today_data():
    """오늘 데이터 로드."""
    dates, panel = S.load_panel(verbose=False)

    if len(dates) < 2:
        print("⚠️  충분한 데이터 없음")
        return None

    di = len(dates) - 1
    today_date = dates[di]

    # 오늘 종목 선택
    top_n = 10
    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    scored = [(S.factor_score(panel, c, di, "low_vol"), c) for c in cand]
    scored = [(s, c) for s, c in scored if s is not None]

    if len(scored) < top_n:
        return None

    scored.sort(reverse=True)
    picks = [c for _s, c in scored[:top_n]]

    return {
        "date": today_date,
        "picks": picks,
        "panel": panel,
        "dates": dates,
        "di": di,
    }


def calculate_ovn(panel, picks, di):
    """OVN 계산."""
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


def calculate_yesterday_signal(panel, picks, di):
    """전일 신호 판정."""
    # 전일 당일 수익률로 신호 판정
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
        return None, None

    avg_ret = st.mean(daily_rets)
    return "bullish" if avg_ret > 0 else "bearish", avg_ret


def predict_tomorrow_return(panel, picks, di):
    """내일 예상 수익률 계산."""
    signal, signal_strength = calculate_yesterday_signal(panel, picks, di)
    ovn = calculate_ovn(panel, picks, di)

    if signal is None:
        return None, None, None

    # 예측 로직
    if signal == "bearish":
        if ovn is not None and ovn < 0:
            predicted_return = 0.00592  # +0.592%
            confidence = 85
        elif ovn is not None and ovn >= 0:
            predicted_return = 0.002
            confidence = 50
        else:
            predicted_return = 0.00592
            confidence = 60
    else:  # bullish
        predicted_return = -0.0022  # -0.22%
        confidence = 55

    return predicted_return, confidence, {
        "signal": signal,
        "signal_strength": signal_strength,
        "ovn": ovn,
    }


def get_actual_next_day_return(panel, picks, di):
    """다음날 실제 수익률 (종가 기준)."""
    if di + 1 >= len(panel[picks[0]].close):
        return None  # 아직 다음 날 데이터 없음

    next_di = di + 1
    rets = []

    for code in picks:
        s = panel[code]
        if next_di in s.pos:
            o = s.open[s.pos[next_di]]
            c = s.close[s.pos[next_di]]
            if o > 0:
                ret = (c - o) / o
                rets.append(ret)

    if not rets:
        return None

    return st.mean(rets)


def record_signal(today_data, data_dir):
    """신호 기록."""
    panel = today_data["panel"]
    picks = today_data["picks"]
    di = today_data["di"]
    today_date = today_data["date"]

    # 예측값 계산
    predicted_return, confidence, details = predict_tomorrow_return(panel, picks, di)

    if predicted_return is None:
        print("⚠️  예측 실패")
        return None

    # 실제값 계산 (다음 날이 있으면)
    actual_return = get_actual_next_day_return(panel, picks, di)

    signal_record = {
        "date": today_date,
        "timestamp": datetime.now().isoformat(),
        "num_stocks": len(picks),
        "yesterday_signal": details["signal"],
        "yesterday_signal_strength": details["signal_strength"],
        "ovn": details["ovn"],
        "predicted_return": predicted_return,
        "predicted_confidence": confidence,
        "actual_return": actual_return,
        "hit_target": actual_return > predicted_return * 0.9 if actual_return is not None else None,
        "status": "actual_available" if actual_return is not None else "waiting_for_actual",
    }

    return signal_record


def save_signal_record(signal_record, data_dir):
    """신호 기록 저장."""
    data_dir.mkdir(exist_ok=True)

    # JSON 저장
    json_file = data_dir / f"paper_signal_{signal_record['date']}.json"
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(signal_record, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON 저장: {json_file.name}")
    except Exception as e:
        print(f"⚠️  JSON 저장 오류: {e}")

    # CSV 누적 저장
    csv_file = data_dir / "paper_signals.csv"
    fieldnames = [
        "date", "yesterday_signal", "ovn", "predicted_return",
        "predicted_confidence", "actual_return", "hit_target", "status"
    ]

    try:
        # CSV 파일이 없으면 헤더 작성
        if not csv_file.exists():
            with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

        # 데이터 추가
        csv_record = {
            "date": signal_record["date"],
            "yesterday_signal": signal_record["yesterday_signal"],
            "ovn": f"{signal_record['ovn']:.6f}" if signal_record['ovn'] is not None else "N/A",
            "predicted_return": f"{signal_record['predicted_return']:.6f}",
            "predicted_confidence": signal_record["predicted_confidence"],
            "actual_return": f"{signal_record['actual_return']:.6f}" if signal_record['actual_return'] is not None else "N/A",
            "hit_target": signal_record["hit_target"],
            "status": signal_record["status"],
        }

        with open(csv_file, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(csv_record)

        print(f"✅ CSV 저장: {csv_file.name}")
    except Exception as e:
        print(f"⚠️  CSV 저장 오류: {e}")


def print_summary(signal_record):
    """요약 출력."""
    print("\n" + "=" * 80)
    print("📊 종이거래 신호 수집")
    print("=" * 80)

    print(f"\n📅 날짜: {signal_record['date']}")
    print(f"📈 어제 신호: {signal_record['yesterday_signal'].upper()}")

    if signal_record['ovn'] is not None:
        print(f"🌙 OVN: {signal_record['ovn']*100:+.3f}%")
    else:
        print(f"🌙 OVN: 계산 불가")

    print(f"\n🎯 예측 수익률: {signal_record['predicted_return']*100:+.3f}%")
    print(f"   신뢰도: {signal_record['predicted_confidence']}%")

    if signal_record['actual_return'] is not None:
        print(f"\n✅ 실제 수익률: {signal_record['actual_return']*100:+.3f}%")
        if signal_record['hit_target']:
            print(f"   ✓ 예측 달성!")
        else:
            diff = (signal_record['actual_return'] - signal_record['predicted_return']) * 100
            print(f"   ✗ 예측 대비 {diff:+.3f}%p")
    else:
        print(f"\n⏳ 실제 수익률: 아직 대기중 (다음 날 데이터 필요)")

    print(f"\n상태: {signal_record['status']}")


def main():
    print("\n" + "=" * 80)
    print("종이거래 신호 수집 (Paper Trading)")
    print("=" * 80)
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 데이터 로드
    print("[1] 데이터 로드...")
    today_data = load_today_data()
    if not today_data:
        print("❌ 데이터 로드 실패")
        return 1

    print(f"✅ {today_data['date']} 데이터 로드 완료")
    print(f"   종목: {len(today_data['picks'])}개")

    # 2. 신호 계산
    print("\n[2] 신호 계산...")
    signal_record = record_signal(today_data, S.BASE_DIR / "data")
    if not signal_record:
        print("❌ 신호 계산 실패")
        return 1

    # 3. 기록 저장
    print("\n[3] 기록 저장...")
    save_signal_record(signal_record, S.BASE_DIR / "data")

    # 4. 요약 출력
    print_summary(signal_record)

    print("\n" + "=" * 80)
    print("📌 안내")
    print("=" * 80)
    print("\n이 스크립트는 매일 신호를 기록합니다.")
    print("30-50일 데이터가 모이면 상관성 검증을 시작합니다.")
    print("\n상관성 검증:")
    print("  python validate_correlation.py")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
