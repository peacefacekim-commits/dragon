"""지표 조합별 상관성 분석

8개 지표 중에서 다양한 조합(3~8개)을 만들어
각 조합에서 정렬도와 수익률의 상관성을 계산합니다.

목표: 가장 높은 상관성을 보이는 최적 지표 조합 찾기
"""
import argparse
import csv
import glob
import statistics as st
import sys
from scipy import stats
from itertools import combinations
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


def calculate_alignment_score_with_indicators(
    date_str, di, picks, panel, indicators, flow_data, selected_indicators
):
    """지정된 지표들로만 정렬도를 계산합니다."""
    di_prev = di - 1
    if di_prev < 0:
        return None, {}

    date_prev = date_str[di_prev] if di_prev < len(date_str) else None
    conds = {}

    # 각 지표 계산
    if "OVN" in selected_indicators:
        ovn_vals = []
        for code in picks:
            ovn = overnight_return(panel, code, di)
            if ovn is not None:
                ovn_vals.append(ovn)
        if ovn_vals:
            conds["ovn"] = st.mean(ovn_vals)

    if "SPX" in selected_indicators:
        if date_prev in indicators.get("^GSPC", {}):
            conds["spx"] = indicators["^GSPC"][date_prev]

    if "IXIC" in selected_indicators:
        if date_prev in indicators.get("^IXIC", {}):
            conds["ixic"] = indicators["^IXIC"][date_prev]

    if "SOX" in selected_indicators:
        if date_prev in indicators.get("^SOX", {}):
            conds["sox"] = indicators["^SOX"][date_prev]

    if "VIX" in selected_indicators:
        if date_prev in indicators.get("^VIX", {}):
            conds["vix"] = indicators["^VIX"][date_prev]

    if "KRW" in selected_indicators:
        if date_prev in indicators.get("KRW=X", {}):
            conds["krw"] = indicators["KRW=X"][date_prev]

    if "FLOW" in selected_indicators:
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

    if "VOL" in selected_indicators:
        vol_vals = []
        for code in picks:
            ratio = volume_ratio(panel, code, di_prev)
            if ratio is not None:
                vol_vals.append(ratio)
        if vol_vals:
            conds["vol"] = st.mean(vol_vals)

    # 정렬도 계산 (지정된 지표만)
    num_indicators = len(selected_indicators)
    alignment_bullish = 0
    alignment_bearish = 0

    # OVN
    if "OVN" in selected_indicators and "ovn" in conds:
        if conds["ovn"] > 0:
            alignment_bullish += 1
        else:
            alignment_bearish += 1

    # SPX
    if "SPX" in selected_indicators and "spx" in conds:
        if conds["spx"] > 0:
            alignment_bullish += 1
        else:
            alignment_bearish += 1

    # IXIC
    if "IXIC" in selected_indicators and "ixic" in conds:
        if conds["ixic"] > 0:
            alignment_bullish += 1
        else:
            alignment_bearish += 1

    # SOX
    if "SOX" in selected_indicators and "sox" in conds:
        if conds["sox"] > 0:
            alignment_bullish += 1
        else:
            alignment_bearish += 1

    # VIX (역방향)
    if "VIX" in selected_indicators and "vix" in conds:
        if conds["vix"] < 0:
            alignment_bullish += 1
        else:
            alignment_bearish += 1

    # KRW (역방향)
    if "KRW" in selected_indicators and "krw" in conds:
        if conds["krw"] < 0:
            alignment_bullish += 1
        else:
            alignment_bearish += 1

    # FLOW
    if "FLOW" in selected_indicators and "flow" in conds:
        if conds["flow"] > 0:
            alignment_bullish += 1
        else:
            alignment_bearish += 1

    # VOL
    if "VOL" in selected_indicators and "vol" in conds:
        if conds["vol"] > 1.1:
            alignment_bullish += 1
        else:
            alignment_bearish += 1

    return (alignment_bullish, alignment_bearish), conds


def analyze_with_indicator_set(dates, panel, selected_indicators, rebal_interval=20, lookback=250):
    """특정 지표 조합으로 분석합니다."""
    top_n = 10

    indicators = load_all_us_indicators()
    flow_data = load_flow_data(set(panel.keys()))

    alignment_returns_buy = []
    alignment_returns_sell = []

    rebal_dates = [i for i in range(lookback, len(dates), rebal_interval)]

    for di in rebal_dates:
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

        alignment, conds = calculate_alignment_score_with_indicators(
            dates, di, picks, panel, indicators, flow_data, selected_indicators
        )
        if alignment is None:
            continue

        bullish_count, bearish_count = alignment

        if avg_ret > 0.001:
            alignment_returns_sell.append((bullish_count, avg_ret))
        elif avg_ret < -0.001:
            alignment_returns_buy.append((bearish_count, avg_ret))

    return alignment_returns_buy, alignment_returns_sell


def calculate_correlations(buy_data, sell_data):
    """상관계수 계산."""
    results = {
        "buy_pearson": None,
        "buy_pearson_p": None,
        "buy_count": len(buy_data),
        "sell_pearson": None,
        "sell_pearson_p": None,
        "sell_count": len(sell_data),
        "combined_pearson": None,
        "combined_pearson_p": None,
    }

    if buy_data and len(buy_data) > 2:
        alignments = [x[0] for x in buy_data]
        returns = [x[1] for x in buy_data]
        try:
            r, p = stats.pearsonr(alignments, returns)
            results["buy_pearson"] = r
            results["buy_pearson_p"] = p
        except:
            pass

    if sell_data and len(sell_data) > 2:
        alignments = [x[0] for x in sell_data]
        returns = [x[1] for x in sell_data]
        try:
            r, p = stats.pearsonr(alignments, returns)
            results["sell_pearson"] = r
            results["sell_pearson_p"] = p
        except:
            pass

    # 결합 상관성 (절댓값)
    if buy_data and sell_data:
        all_align_buy = [x[0] for x in buy_data]
        all_ret_buy = [x[1] for x in buy_data]
        all_align_sell = [x[0] for x in sell_data]
        all_ret_sell = [x[1] for x in sell_data]

        all_align = all_align_buy + all_align_sell
        all_ret = all_ret_buy + all_ret_sell

        if len(all_align) > 2:
            try:
                r, p = stats.pearsonr(all_align, all_ret)
                results["combined_pearson"] = abs(r)
                results["combined_pearson_p"] = p
            except:
                pass

    return results


def main():
    parser = argparse.ArgumentParser(description="지표 조합별 상관성 분석")
    parser.add_argument("--rebal", type=int, default=20)
    parser.add_argument("--lookback", type=int, default=250)
    args = parser.parse_args()

    print("[로딩] 패널 데이터...")
    dates, panel = S.load_panel(verbose=False)
    print(f"  {len(dates)}개 거래일, {len(panel)}개 종목\n")

    # 모든 지표 조합 생성
    all_indicators = ["OVN", "SPX", "IXIC", "SOX", "VIX", "KRW", "FLOW", "VOL"]
    all_results = []

    print("=" * 120)
    print("지표 조합별 상관성 분석")
    print("=" * 120)

    # 3개부터 8개까지 조합
    for combo_size in range(3, 9):
        print(f"\n[{combo_size}개 지표 조합]\n")
        print(f"{'지표 조합':<40} {'매도일':<15} {'매수일':<15} {'통합':<15} {'최고점':<10}")
        print("-" * 120)

        results_for_size = []

        for combo in combinations(all_indicators, combo_size):
            selected = set(combo)

            buy_data, sell_data = analyze_with_indicator_set(
                dates, panel, selected,
                rebal_interval=args.rebal,
                lookback=args.lookback
            )

            corr = calculate_correlations(buy_data, sell_data)

            results_for_size.append({
                "combo": combo,
                "corr": corr,
                "buy_data": buy_data,
                "sell_data": sell_data,
            })

            # 결과 출력
            combo_str = "+".join(combo)
            sell_str = (
                f"{corr['sell_pearson']:+.4f}" if corr["sell_pearson"] is not None else "N/A"
            )
            buy_str = (
                f"{corr['buy_pearson']:+.4f}" if corr["buy_pearson"] is not None else "N/A"
            )
            combined_str = (
                f"{corr['combined_pearson']:+.4f}" if corr["combined_pearson"] is not None else "N/A"
            )

            max_corr = max(
                [x for x in [corr["sell_pearson"], corr["buy_pearson"], corr["combined_pearson"]]
                 if x is not None],
                default=0
            )
            max_str = f"{max_corr:+.4f}"

            print(f"{combo_str:<40} {sell_str:>14} {buy_str:>14} {combined_str:>14} {max_str:>9}")

            all_results.append({
                "combo": combo,
                "size": combo_size,
                "corr": corr,
                "buy_data": buy_data,
                "sell_data": sell_data,
                "max_corr": max_corr,
            })

    # 최고 상관성 조합 추출
    print("\n" + "=" * 120)
    print("상위 10개 조합 (최고 상관성 기준)")
    print("=" * 120)
    print(f"{'순위':<6} {'지표 조합':<40} {'크기':<6} {'매도':<12} {'매수':<12} {'통합':<12} {'최고':<10}")
    print("-" * 120)

    sorted_results = sorted(all_results, key=lambda x: x["max_corr"], reverse=True)

    for idx, result in enumerate(sorted_results[:10], 1):
        combo_str = "+".join(result["combo"])
        sell_corr = result["corr"]["sell_pearson"]
        buy_corr = result["corr"]["buy_pearson"]
        combined = result["corr"]["combined_pearson"]

        sell_str = f"{sell_corr:+.4f}" if sell_corr is not None else "N/A"
        buy_str = f"{buy_corr:+.4f}" if buy_corr is not None else "N/A"
        combined_str = f"{combined:+.4f}" if combined is not None else "N/A"

        print(f"{idx:<6} {combo_str:<40} {result['size']:<6} {sell_str:>11} {buy_str:>11} {combined_str:>11} {result['max_corr']:>9.4f}")

    # 최고 조합 상세 분석
    best_result = sorted_results[0]
    print("\n" + "=" * 120)
    print(f"최고 조합: {'+'.join(best_result['combo'])} (상관성: {best_result['max_corr']:+.4f})")
    print("=" * 120)

    best_corr = best_result["corr"]
    print(f"\n매도일 (강세 정렬):")
    print(f"  샘플: {best_corr['sell_count']}개")
    if best_corr["sell_pearson"] is not None:
        print(f"  상관계수: {best_corr['sell_pearson']:+.4f} (p={best_corr['sell_pearson_p']:.4f})")
        if best_corr['sell_pearson_p'] < 0.05:
            print(f"  ✓ 통계적으로 유의미")
        else:
            print(f"  ✗ 유의미하지 않음")

    print(f"\n매수일 (약세 정렬):")
    print(f"  샘플: {best_corr['buy_count']}개")
    if best_corr["buy_pearson"] is not None:
        print(f"  상관계수: {best_corr['buy_pearson']:+.4f} (p={best_corr['buy_pearson_p']:.4f})")
        if best_corr['buy_pearson_p'] < 0.05:
            print(f"  ✓ 통계적으로 유의미")
        else:
            print(f"  ✗ 유의미하지 않음")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
