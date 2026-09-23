"""행성 정렬 신호 분석 (Planetary Alignment Signal)

(2026-09-23 신설)

전략: 모든 지표가 동일 방향으로 정렬될 때만 진입
- 8개 지표 모두 로드
- 정렬도 계산 (정렬된 지표 개수 / 8)
- 정렬도별 실제 수익률 분석

지표:
  1. OVN (오버나이트)
  2. SPX (S&P 500)
  3. IXIC (나스닥)
  4. SOX (반도체)
  5. VIX (변동성지수, 역방향)
  6. KRW (환율, 역방향)
  7. FLOW (기관/외국인)
  8. VOL (거래량)
"""
import argparse
import csv
import glob
import statistics as st
import sys

import strategy as S


def load_all_us_indicators():
    """모든 미국 지표 로드."""
    data_dir = S.BASE_DIR / "data"
    indicators = {
        "^GSPC": {},   # S&P 500
        "^IXIC": {},   # 나스닥
        "^SOX": {},    # 반도체
        "^VIX": {},    # VIX
        "KRW=X": {},   # 환율
    }

    for path in sorted(glob.glob(str(data_dir / "us_market_*.csv"))):
        try:
            with open(path, encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    ticker = row.get("ticker")
                    if ticker in indicators:
                        try:
                            date = row["date"]
                            open_p = float(row["open"])
                            close_p = float(row["close"])
                            if open_p > 0:
                                ret = (close_p - open_p) / open_p
                                indicators[ticker][date] = ret
                        except (ValueError, TypeError):
                            pass
        except Exception:
            pass

    return indicators


def load_flow_data(codes):
    """기관/외국인 수급 로드."""
    flow = {}
    data_dir = S.BASE_DIR / "data"
    want = set(codes)

    for path in sorted(glob.glob(str(data_dir / "krx_flow_*.csv"))):
        try:
            with open(path, encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    if row.get("code") not in want:
                        continue
                    try:
                        flow[(row["date"], row["code"])] = (
                            float(row.get("inst", 0)),
                            float(row.get("foreign", 0)),
                        )
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass
    return flow


def overnight_return(panel, code, di):
    """오버나이트 수익률."""
    if di < 1 or code not in panel:
        return None
    s = panel[code]
    if di - 1 not in s.pos or di not in s.pos:
        return None
    prev_close = s.close[s.pos[di - 1]]
    curr_open = s.open[s.pos[di]]
    if prev_close <= 0:
        return None
    return (curr_open - prev_close) / prev_close


def daily_return(panel, code, di):
    """일일 수익률."""
    if code not in panel:
        return None
    s = panel[code]
    if di not in s.pos:
        return None
    o = s.open[s.pos[di]]
    c = s.close[s.pos[di]]
    if o <= 0:
        return None
    return (c - o) / o


def volume_ratio(panel, code, di, lookback=20):
    """거래량 비율."""
    if code not in panel or di < lookback:
        return None
    s = panel[code]
    if di not in s.pos:
        return None

    today_val = s.value[s.pos[di]]
    if today_val <= 0:
        return None

    past_vals = []
    for j in range(di - lookback, di):
        if j in s.pos:
            past_vals.append(s.value[s.pos[j]])

    if not past_vals:
        return None
    avg_val = st.mean(past_vals)
    if avg_val <= 0:
        return None
    return today_val / avg_val


def calculate_alignment_score(date_str, di, picks, panel, indicators, flow_data):
    """정렬도 계산 (0~8, 8이 완전 정렬).

    약세 신호 (매수):
      OVN < 0, SPX < 0, IXIC < 0, SOX < 0, VIX > 0, KRW > 0, FLOW < 0, VOL < 1.1

    강세 신호 (매도):
      OVN > 0, SPX > 0, IXIC > 0, SOX > 0, VIX < 0, KRW < 0, FLOW > 0, VOL > 1.1
    """
    di_prev = di - 1
    if di_prev < 0:
        return None, {}

    date_prev = date_str[di_prev] if di_prev < len(date_str) else None
    conds = {}

    # 1. OVN
    ovn_vals = []
    for code in picks:
        ovn = overnight_return(panel, code, di)
        if ovn is not None:
            ovn_vals.append(ovn)
    if ovn_vals:
        conds["ovn"] = st.mean(ovn_vals)

    # 2. SPX (S&P 500)
    if date_prev in indicators.get("^GSPC", {}):
        conds["spx"] = indicators["^GSPC"][date_prev]

    # 3. IXIC (나스닥)
    if date_prev in indicators.get("^IXIC", {}):
        conds["ixic"] = indicators["^IXIC"][date_prev]

    # 4. SOX (반도체)
    if date_prev in indicators.get("^SOX", {}):
        conds["sox"] = indicators["^SOX"][date_prev]

    # 5. VIX (변동성, 역방향)
    if date_prev in indicators.get("^VIX", {}):
        conds["vix"] = indicators["^VIX"][date_prev]

    # 6. KRW (환율, 역방향)
    if date_prev in indicators.get("KRW=X", {}):
        conds["krw"] = indicators["KRW=X"][date_prev]

    # 7. FLOW (기관/외국인)
    flow_vals = []
    for code in picks:
        flow_key = (date_prev, code)
        if flow_key in flow_data:
            inst_amt, foreign_amt = flow_data[flow_key]
            s = panel.get(code)
            if s and di_prev in s.pos:
                trade_val = s.value[s.pos[di_prev]]
                if trade_val > 0:
                    flow_vals.append((inst_amt + foreign_amt) / trade_val)
    if flow_vals:
        conds["flow"] = st.mean(flow_vals)

    # 8. VOL (거래량)
    vol_vals = []
    for code in picks:
        ratio = volume_ratio(panel, code, di_prev)
        if ratio is not None:
            vol_vals.append(ratio)
    if vol_vals:
        conds["vol"] = st.mean(vol_vals)

    # 정렬도 계산 (약세/강세 혼합 계산)
    # 여기선 절대값으로 정렬도를 계산 (방향 무관)
    alignment_bullish = 0
    alignment_bearish = 0

    if conds.get("ovn", 0) > 0:
        alignment_bullish += 1
    else:
        alignment_bearish += 1

    if conds.get("spx", 0) > 0:
        alignment_bullish += 1
    else:
        alignment_bearish += 1

    if conds.get("ixic", 0) > 0:
        alignment_bullish += 1
    else:
        alignment_bearish += 1

    if conds.get("sox", 0) > 0:
        alignment_bullish += 1
    else:
        alignment_bearish += 1

    if conds.get("vix", 0) < 0:  # VIX 역방향
        alignment_bullish += 1
    else:
        alignment_bearish += 1

    if conds.get("krw", 0) < 0:  # KRW 역방향
        alignment_bullish += 1
    else:
        alignment_bearish += 1

    if conds.get("flow", 0) > 0:
        alignment_bullish += 1
    else:
        alignment_bearish += 1

    if conds.get("vol", 0) > 1.1:
        alignment_bullish += 1
    else:
        alignment_bearish += 1

    return (alignment_bullish, alignment_bearish), conds


def analyze_alignment(dates, panel, rebal_interval=20, lookback=250):
    """정렬도별 수익률 분석."""
    top_n = 10

    # 지표 로드
    print("[로딩] 미국 지표...")
    indicators = load_all_us_indicators()
    print(f"  SPX: {len(indicators['^GSPC'])}일")
    print(f"  IXIC: {len(indicators['^IXIC'])}일")
    print(f"  SOX: {len(indicators['^SOX'])}일")
    print(f"  VIX: {len(indicators['^VIX'])}일")
    print(f"  KRW: {len(indicators['KRW=X'])}일")

    print("[로딩] 수급 데이터...")
    flow_data = load_flow_data(set(panel.keys()))
    print(f"  FLOW: {len(flow_data)}건")

    # 결과 저장
    results = {
        "buy_by_alignment": {},  # alignment -> [returns]
        "sell_by_alignment": {},
        "neutral_by_alignment": {},
    }

    rebal_dates = [i for i in range(lookback, len(dates), rebal_interval)]
    print(f"\n[분석] {len(rebal_dates)}개 리밸런스 날짜")

    for rebal_idx, di in enumerate(rebal_dates):
        if rebal_idx % 10 == 0:
            print(f"  진행: {rebal_idx}/{len(rebal_dates)}")

        # 포트폴리오 선정
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        scored = [(S.factor_score(panel, c, di, "low_vol"), c) for c in cand]
        scored = [(s, c) for s, c in scored if s is not None]

        if len(scored) < top_n:
            continue

        scored.sort(reverse=True)
        picks = [c for _s, c in scored[:top_n]]

        # 20거래일 수익률
        hold_rets = []
        for code in picks:
            ret_lists = []
            for hold_di in range(di, min(di + rebal_interval, len(dates))):
                ret = daily_return(panel, code, hold_di)
                if ret is not None:
                    ret_lists.append(ret)
            if ret_lists:
                hold_rets.append(st.mean(ret_lists))

        if not hold_rets:
            continue

        avg_ret = st.mean(hold_rets)

        # 정렬도 계산
        alignment, conds = calculate_alignment_score(dates, di, picks, panel, indicators, flow_data)
        if alignment is None:
            continue

        bullish_count, bearish_count = alignment

        # 결과 저장 (강세 정렬도 기준)
        if avg_ret > 0.001:
            key = "sell_by_alignment"
            align_key = bullish_count
        elif avg_ret < -0.001:
            key = "buy_by_alignment"
            align_key = bearish_count
        else:
            key = "neutral_by_alignment"
            align_key = bullish_count

        if align_key not in results[key]:
            results[key][align_key] = []
        results[key][align_key].append(avg_ret)

    return results


def print_results(results):
    """결과 출력."""
    print("\n" + "=" * 100)
    print("행성 정렬도 분석 (0~8, 8이 완전 정렬)")
    print("=" * 100)

    for cat_name, cat_key in [("📈 매도일 (강세 정렬)", "sell_by_alignment"),
                               ("📉 매수일 (약세 정렬)", "buy_by_alignment"),
                               ("➡️  중립일", "neutral_by_alignment")]:
        data = results[cat_key]
        if not data:
            print(f"\n{cat_name}: 데이터 없음")
            continue

        print(f"\n{cat_name}")
        print("-" * 100)
        print(f"{'정렬도':>6} {'빈도':>6} {'평균수익률':>12} {'중앙값':>12} {'편차':>10} {'승률':>8} {'분포'}")
        print("-" * 100)

        for align_score in sorted(data.keys()):
            returns = data[align_score]
            count = len(returns)
            mean_ret = st.mean(returns)
            median_ret = st.median(returns)
            std_ret = st.stdev(returns) if len(returns) > 1 else 0
            win_rate = sum(1 for r in returns if r > 0) / count * 100 if count > 0 else 0

            # 바 그래프
            bar_len = int(count * 1.5)
            bar = "█" * min(bar_len, 40)

            print(f"{align_score:>6}/{8} {count:>6}건 {mean_ret*100:>11.2f}% "
                  f"{median_ret*100:>11.2f}% {std_ret*100:>9.2f}% {win_rate:>7.1f}% {bar}")

        # 경향성 분석
        print("\n  경향성 분석:")
        sorted_keys = sorted(data.keys())
        if len(sorted_keys) > 1:
            best_align = max(sorted_keys, key=lambda k: st.mean(data[k]))
            worst_align = min(sorted_keys, key=lambda k: st.mean(data[k]))

            best_mean = st.mean(data[best_align])
            worst_mean = st.mean(data[worst_align])

            print(f"    최고 성과: {best_align}/8 정렬 → {best_mean*100:+.2f}%")
            print(f"    최저 성과: {worst_align}/8 정렬 → {worst_mean*100:+.2f}%")
            print(f"    성과 차이: {(best_mean - worst_mean)*100:+.2f}%p")

            # 상관관계 계산
            if cat_key == "sell_by_alignment":
                print(f"    ✓ 정렬도 증가 → 수익률 증가? {best_align > worst_align}")
            else:
                print(f"    ✓ 약세 정렬도 증가 → 손실 증가? {best_align > worst_align}")


def main():
    parser = argparse.ArgumentParser(description="행성 정렬 신호 분석")
    parser.add_argument("--rebal", type=int, default=20, help="리밸런스 간격")
    parser.add_argument("--lookback", type=int, default=250, help="분석 시작점")
    args = parser.parse_args()

    print("[로딩] 패널 데이터...")
    dates, panel = S.load_panel(verbose=False)
    print(f"  {len(dates)}개 거래일, {len(panel)}개 종목")

    print("[분석] 정렬도별 수익률...")
    results = analyze_alignment(dates, panel,
                               rebal_interval=args.rebal,
                               lookback=args.lookback)

    print_results(results)
    print("\n[완료]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
