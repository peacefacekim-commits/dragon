"""행성 정렬 신호 상관성 분석

정렬도(alignment score)와 실제 수익률 간의 통계적 상관성을 검증합니다.
- 피어슨 상관계수
- 스피어만 순위 상관계수
- 선형 회귀 분석
- 각 범주별 ANOVA
"""
import argparse
import csv
import glob
import statistics as st
import sys
from scipy import stats
import numpy as np

import strategy as S


def load_all_us_indicators():
    """모든 미국 지표 로드."""
    data_dir = S.BASE_DIR / "data"
    indicators = {
        "^GSPC": {},
        "^IXIC": {},
        "^SOX": {},
        "^VIX": {},
        "KRW=X": {},
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
    """정렬도 계산."""
    di_prev = di - 1
    if di_prev < 0:
        return None, {}

    date_prev = date_str[di_prev] if di_prev < len(date_str) else None
    conds = {}

    ovn_vals = []
    for code in picks:
        ovn = overnight_return(panel, code, di)
        if ovn is not None:
            ovn_vals.append(ovn)
    if ovn_vals:
        conds["ovn"] = st.mean(ovn_vals)

    if date_prev in indicators.get("^GSPC", {}):
        conds["spx"] = indicators["^GSPC"][date_prev]

    if date_prev in indicators.get("^IXIC", {}):
        conds["ixic"] = indicators["^IXIC"][date_prev]

    if date_prev in indicators.get("^SOX", {}):
        conds["sox"] = indicators["^SOX"][date_prev]

    if date_prev in indicators.get("^VIX", {}):
        conds["vix"] = indicators["^VIX"][date_prev]

    if date_prev in indicators.get("KRW=X", {}):
        conds["krw"] = indicators["KRW=X"][date_prev]

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

    vol_vals = []
    for code in picks:
        ratio = volume_ratio(panel, code, di_prev)
        if ratio is not None:
            vol_vals.append(ratio)
    if vol_vals:
        conds["vol"] = st.mean(vol_vals)

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

    if conds.get("vix", 0) < 0:
        alignment_bullish += 1
    else:
        alignment_bearish += 1

    if conds.get("krw", 0) < 0:
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


def analyze_correlation(dates, panel, rebal_interval=20, lookback=250):
    """정렬도와 수익률의 상관성 분석."""
    top_n = 10

    print("[로딩] 미국 지표...")
    indicators = load_all_us_indicators()
    print(f"  SPX: {len(indicators['^GSPC'])}일")

    print("[로딩] 수급 데이터...")
    flow_data = load_flow_data(set(panel.keys()))
    print(f"  FLOW: {len(flow_data)}건")

    # 데이터 수집: (정렬도, 수익률, 카테고리)
    alignment_returns_buy = []  # (약세_정렬도, 수익률)
    alignment_returns_sell = []  # (강세_정렬도, 수익률)
    alignment_returns_all = []  # (정렬도, 수익률, 카테고리)

    rebal_dates = [i for i in range(lookback, len(dates), rebal_interval)]
    print(f"\n[분석] {len(rebal_dates)}개 리밸런스 날짜")

    for rebal_idx, di in enumerate(rebal_dates):
        if rebal_idx % 10 == 0:
            print(f"  진행: {rebal_idx}/{len(rebal_dates)}")

        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        scored = [(S.factor_score(panel, c, di, "low_vol"), c) for c in cand]
        scored = [(s, c) for s, c in scored if s is not None]

        if len(scored) < top_n:
            continue

        scored.sort(reverse=True)
        picks = [c for _s, c in scored[:top_n]]

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

        alignment, conds = calculate_alignment_score(dates, di, picks, panel, indicators, flow_data)
        if alignment is None:
            continue

        bullish_count, bearish_count = alignment

        if avg_ret > 0.001:
            alignment_returns_sell.append((bullish_count, avg_ret))
            alignment_returns_all.append((bullish_count, avg_ret, "sell"))
        elif avg_ret < -0.001:
            alignment_returns_buy.append((bearish_count, avg_ret))
            alignment_returns_all.append((bearish_count, avg_ret, "buy"))
        else:
            alignment_returns_all.append((bullish_count, avg_ret, "neutral"))

    return alignment_returns_buy, alignment_returns_sell, alignment_returns_all


def print_correlation_analysis(buy_data, sell_data, all_data):
    """상관성 분석 결과 출력."""
    print("\n" + "=" * 100)
    print("정렬도와 수익률의 상관성 분석")
    print("=" * 100)

    # 매도일 분석
    if sell_data:
        print("\n📈 매도일 (강세 정렬)")
        print("-" * 100)
        alignments = [x[0] for x in sell_data]
        returns = [x[1] for x in sell_data]

        pearson_r, pearson_p = stats.pearsonr(alignments, returns)
        spearman_r, spearman_p = stats.spearmanr(alignments, returns)

        print(f"샘플 수: {len(sell_data)}개")
        print(f"\n상관계수:")
        print(f"  피어슨 (Pearson): {pearson_r:+.4f} (p-value: {pearson_p:.4f})")
        print(f"  스피어만 (Spearman): {spearman_r:+.4f} (p-value: {spearman_p:.4f})")

        if pearson_p < 0.05:
            print(f"  ✓ 통계적으로 유의미한 상관성 (p < 0.05)")
        else:
            print(f"  ✗ 통계적으로 유의미하지 않음 (p >= 0.05)")

        # 선형 회귀
        slope, intercept, r_value, p_value, std_err = stats.linregress(alignments, returns)
        print(f"\n선형 회귀:")
        print(f"  기울기: {slope:+.6f} (정렬도 1 증가 시 수익률 {slope*100:+.4f}%p 변화)")
        print(f"  절편: {intercept:+.6f}")
        print(f"  R²: {r_value**2:.4f} (설명력 {r_value**2*100:.2f}%)")
        print(f"  p-value: {p_value:.4f}")

    # 매수일 분석
    if buy_data:
        print("\n📉 매수일 (약세 정렬)")
        print("-" * 100)
        alignments = [x[0] for x in buy_data]
        returns = [x[1] for x in buy_data]

        pearson_r, pearson_p = stats.pearsonr(alignments, returns)
        spearman_r, spearman_p = stats.spearmanr(alignments, returns)

        print(f"샘플 수: {len(buy_data)}개")
        print(f"\n상관계수:")
        print(f"  피어슨 (Pearson): {pearson_r:+.4f} (p-value: {pearson_p:.4f})")
        print(f"  스피어만 (Spearman): {spearman_r:+.4f} (p-value: {spearman_p:.4f})")

        if abs(pearson_p) < 0.05:
            print(f"  ✓ 통계적으로 유의미한 상관성 (p < 0.05)")
        else:
            print(f"  ✗ 통계적으로 유의미하지 않음 (p >= 0.05)")

        # 선형 회귀
        slope, intercept, r_value, p_value, std_err = stats.linregress(alignments, returns)
        print(f"\n선형 회귀:")
        print(f"  기울기: {slope:+.6f} (정렬도 1 증가 시 손실 {slope*100:+.4f}%p 악화)")
        print(f"  절편: {intercept:+.6f}")
        print(f"  R²: {r_value**2:.4f} (설명력 {r_value**2*100:.2f}%)")
        print(f"  p-value: {p_value:.4f}")

    # 전체 데이터 ANOVA (카테고리별 유의미한 차이)
    if all_data:
        print("\n🔍 카테고리별 ANOVA 검정")
        print("-" * 100)

        sell_only = [x[1] for x in all_data if x[2] == "sell"]
        buy_only = [x[1] for x in all_data if x[2] == "buy"]
        neutral_only = [x[1] for x in all_data if x[2] == "neutral"]

        if sell_only and buy_only and neutral_only:
            f_stat, p_value = stats.f_oneway(sell_only, buy_only, neutral_only)
            print(f"매도일 vs 매수일 vs 중립일 평균 수익률 차이:")
            print(f"  F-통계량: {f_stat:.4f}")
            print(f"  p-value: {p_value:.4f}")

            if p_value < 0.05:
                print(f"  ✓ 그룹 간 유의미한 차이 존재 (p < 0.05)")
            else:
                print(f"  ✗ 그룹 간 유의미한 차이 없음")

            print(f"\n그룹별 통계:")
            print(f"  매도일: {len(sell_only)}개, 평균 {st.mean(sell_only)*100:+.3f}%, "
                  f"중앙값 {st.median(sell_only)*100:+.3f}%")
            print(f"  매수일: {len(buy_only)}개, 평균 {st.mean(buy_only)*100:+.3f}%, "
                  f"중앙값 {st.median(buy_only)*100:+.3f}%")
            print(f"  중립일: {len(neutral_only)}개, 평균 {st.mean(neutral_only)*100:+.3f}%, "
                  f"중앙값 {st.median(neutral_only)*100:+.3f}%")

    # 효과 크기 (Effect Size)
    print("\n📊 효과 크기 (Effect Size)")
    print("-" * 100)
    if sell_data and buy_data:
        sell_mean = st.mean([x[1] for x in sell_data])
        buy_mean = st.mean([x[1] for x in buy_data])
        sell_std = st.stdev([x[1] for x in sell_data]) if len(sell_data) > 1 else 0
        buy_std = st.stdev([x[1] for x in buy_data]) if len(buy_data) > 1 else 0

        pooled_std = np.sqrt((sell_std**2 + buy_std**2) / 2)
        cohens_d = (sell_mean - buy_mean) / pooled_std if pooled_std > 0 else 0

        print(f"Cohen's d (매도일 vs 매수일): {cohens_d:.4f}")
        if abs(cohens_d) < 0.2:
            effect = "무시할 수 있는 정도"
        elif abs(cohens_d) < 0.5:
            effect = "작은 효과"
        elif abs(cohens_d) < 0.8:
            effect = "중간 효과"
        else:
            effect = "큰 효과"
        print(f"  해석: {effect}")

    print("\n[완료]")


def main():
    parser = argparse.ArgumentParser(description="행성 정렬 상관성 분석")
    parser.add_argument("--rebal", type=int, default=20, help="리밸런스 간격")
    parser.add_argument("--lookback", type=int, default=250, help="분석 시작점")
    args = parser.parse_args()

    print("[로딩] 패널 데이터...")
    dates, panel = S.load_panel(verbose=False)
    print(f"  {len(dates)}개 거래일, {len(panel)}개 종목")

    print("[분석] 정렬도와 수익률의 상관성...")
    buy_data, sell_data, all_data = analyze_correlation(
        dates, panel,
        rebal_interval=args.rebal,
        lookback=args.lookback
    )

    print_correlation_analysis(buy_data, sell_data, all_data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
