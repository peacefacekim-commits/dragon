"""당일 아침 9:30~10:00 신호 수집 스크립트

매일 아침 09:30에 실행하여:
1. 당일 OVN (오버나이트) 계산
2. 당일 FLOW (기관/외국인) 수집
3. 당일 SPX, IXIC, SOX, VIX, KRW (9:30~10:00)
4. 당일 VOL (거래량)
을 수집하고 JSON으로 저장합니다.
"""
import json
import csv
import glob
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
import statistics as st

import strategy as S


def load_prev_day_data():
    """어제 데이터 로드 (OVN 계산용)."""
    data_dir = S.BASE_DIR / "data"
    prev_data = {}

    # 가장 최신 us_market 파일 로드
    us_market_files = sorted(glob.glob(str(data_dir / "us_market_*.csv")))
    if not us_market_files:
        print("⚠️  us_market_*.csv 파일 없음")
        return prev_data

    latest_file = us_market_files[-1]

    try:
        with open(latest_file, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
            if rows:
                # 마지막 행 = 어제 데이터
                last_row = rows[-1]
                prev_data["date"] = last_row.get("date")
                prev_data["close_price"] = float(last_row.get("close", 0))
    except Exception as e:
        print(f"⚠️  이전 데이터 로드 오류: {e}")

    return prev_data


def calculate_ovn(panel, today_open_price):
    """
    당일 OVN (오버나이트) 계산.
    OVN = (당일 시가 - 전일 종가) / 전일 종가
    """
    top_n = 10
    dates, _ = S.load_panel(verbose=False)

    # 마지막 데이터가 어제라고 가정
    di = len(dates) - 1

    if di < 1:
        return None

    cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
    scored = [(S.factor_score(panel, c, di, "low_vol"), c) for c in cand]
    scored = [(s, c) for s, c in scored if s is not None]

    if len(scored) < top_n:
        return None

    scored.sort(reverse=True)
    picks = [c for _s, c in scored[:top_n]]

    # OVN 계산
    ovn_vals = []
    for code in picks:
        s = panel[code]
        if di in s.pos and di + 1 in s.pos:
            prev_close = s.close[s.pos[di]]
            curr_open = s.open[s.pos[di + 1]]
            if prev_close > 0:
                ovn = (curr_open - prev_close) / prev_close
                ovn_vals.append(ovn)

    if not ovn_vals:
        return None

    return st.mean(ovn_vals)


def collect_us_indicators_intraday():
    """
    미국 지표 당일 9:30~10:00 수집.
    yfinance에서 1분봉으로 수집하여 첫 30분 추출.
    """
    indicators = {}
    tickers = {
        "^GSPC": "SPX",
        "^IXIC": "IXIC",
        "^SOX": "SOX",
        "^VIX": "VIX",
        "KRW=X": "KRW",
    }

    print("  [미국 지표] yfinance에서 수집 중...")

    for ticker, name in tickers.items():
        try:
            data = yf.Ticker(ticker)
            # 당일 1분봉 (한국시간 21:30~22:00 근처, 또는 미국시간 9:30~10:00)
            hist = data.history(period='1d', interval='1m')

            if len(hist) > 0:
                # 첫 시가와 30분 후 종가
                open_price = hist.iloc[0]['Open']
                close_price = hist.iloc[min(30, len(hist)-1)]['Close']

                if open_price > 0:
                    ret = (close_price - open_price) / open_price
                    indicators[name] = {
                        "return": ret,
                        "open": open_price,
                        "close": close_price,
                        "bullish": ret > 0,
                    }
                    print(f"    {name}: {ret*100:+.3f}% (open: {open_price:.2f}, close: {close_price:.2f})")
                else:
                    print(f"    {name}: 데이터 불완전")
            else:
                print(f"    {name}: 데이터 없음 (미국 장 마감)")

        except Exception as e:
            print(f"    {name}: 오류 - {e}")

    return indicators


def load_flow_data_today(codes):
    """
    당일 FLOW (기관/외국인) 수집.

    한국거래소에서 수동으로 기록하거나,
    웹사이트에서 스크래핑 필요.
    """
    print("  [FLOW] 수급 데이터 수집...")

    # 자동 스크래핑은 복잡하므로, 수동 입력 또는 파일 읽기
    flow_file = S.BASE_DIR / "data" / "today_flow.json"

    if flow_file.exists():
        try:
            with open(flow_file, 'r', encoding='utf-8') as f:
                flow_data = json.load(f)
            print(f"    파일에서 로드: {len(flow_data)}개")
            return flow_data
        except Exception as e:
            print(f"    파일 읽기 오류: {e}")

    print("    ⚠️  today_flow.json 없음 (수동 입력 필요)")
    print("    위치: data/today_flow.json")
    return {}


def collect_volume_data(panel):
    """
    당일 거래량 비율 계산.
    현재는 종가 기준이므로, 실시간 데이터 필요.
    """
    print("  [거래량] 당일 데이터 수집...")

    # 현재 구현: 마지막 거래일 데이터 사용
    # 실제로는 실시간 거래량이 필요
    return None


def main():
    print("\n" + "=" * 80)
    print("당일 신호 수집 (09:30 ~ 10:00)")
    print("=" * 80)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 1. 패널 데이터 로드
    print("[1] 패널 데이터 로드...")
    dates, panel = S.load_panel(verbose=False)
    print(f"    {len(dates)}개 거래일, {len(panel)}개 종목")

    # 2. OVN 계산
    print("\n[2] OVN (오버나이트) 계산...")
    ovn_val = calculate_ovn(panel, None)
    if ovn_val is not None:
        print(f"    OVN: {ovn_val*100:+.3f}%")
        ovn_bullish = ovn_val > 0
    else:
        print("    OVN: 계산 실패")
        ovn_bullish = None

    # 3. 미국 지표 수집
    print("\n[3] 미국 지표 (SPX, IXIC, SOX, VIX, KRW)...")
    us_indicators = collect_us_indicators_intraday()

    # 4. FLOW 수집
    print("\n[4] FLOW (기관/외국인) 수급...")
    flow_data = load_flow_data_today(set(panel.keys()))
    if flow_data:
        print(f"    수립됨: {len(flow_data)}개")
    else:
        print("    ⚠️  데이터 없음 (수동 입력 필요)")

    # 5. 거래량 수집
    print("\n[5] VOL (거래량)...")
    vol_data = collect_volume_data(panel)

    # 결과 정리
    today_signals = {
        "timestamp": datetime.now().isoformat(),
        "indicators": {
            "OVN": {
                "value": ovn_val,
                "bullish": ovn_bullish,
            } if ovn_val is not None else None,
            "SPX": us_indicators.get("SPX"),
            "IXIC": us_indicators.get("IXIC"),
            "SOX": us_indicators.get("SOX"),
            "VIX": us_indicators.get("VIX"),
            "KRW": us_indicators.get("KRW"),
            "FLOW": "manual_input_needed" if not flow_data else "loaded",
            "VOL": vol_data,
        },
    }

    # 파일 저장
    output_file = S.BASE_DIR / "data" / f"today_signals_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(today_signals, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 저장 완료: {output_file}")

    # 신호 요약
    print("\n" + "=" * 80)
    print("당일 신호 요약")
    print("=" * 80)
    print(f"OVN: {ovn_bullish} (강세)" if ovn_bullish else f"OVN: {ovn_bullish} (약세)" if ovn_bullish is not None else "OVN: 계산실패")

    for key, val in us_indicators.items():
        if val:
            bullish_str = "📈 강세" if val.get("bullish") else "📉 약세"
            print(f"{key}: {bullish_str} ({val['return']*100:+.3f}%)")

    print("\n" + "=" * 80)
    print("📌 다음 단계")
    print("=" * 80)
    print("1. FLOW 데이터 수동 입력 필요:")
    print("   - 한국거래소 매매현황에서 당일 기관/외국인 순매수 확인")
    print("   - data/today_flow.json 에 JSON 형식으로 저장")
    print("   형식: {\"XXXXX\": {\"inst\": 1000000, \"foreign\": 500000}, ...}")
    print("\n2. 10:00에 신호 비교 스크립트 실행:")
    print("   python compare_signals.py")
    print("\n3. 투자 결정 후 거래 진행\n")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
