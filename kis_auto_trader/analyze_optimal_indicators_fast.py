"""지표 조합별 상관성 분석 (최적화 버전)

한 번에 모든 데이터를 로드한 후, 조합별로 상관성을 빠르게 계산합니다.
"""
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


def collect_indicator_values(
    dates, panel, indicators, flow_data, rebal_interval=20, lookback=250
):
    """모든 리밸런스 데이터에 대해 지표값을 미리 계산합니다."""
    top_n = 10
    data_points = []

    rebal_dates = [i for i in range(lookback, len(dates), rebal_interval)]

    for di in rebal_dates:
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

        # 지표값 계산
        di_prev = di - 1
        if di_prev < 0:
            continue

        date_prev = dates[di_prev] if di_prev < len(dates) else None
        indicators_values = {}

        # OVN
        ovn_vals = []
        for code in picks:
            ovn = overnight_return(panel, code, di)
            if ovn is not None:
                ovn_vals.append(ovn)
        if ovn_vals:
            indicators_values["OVN"] = st.mean(ovn_vals) > 0

        # SPX
        if date_prev in indicators.get("^GSPC", {}):
            indicators_values["SPX"] = indicators["^GSPC"][date_prev] > 0

        # IXIC
        if date_prev in indicators.get("^IXIC", {}):
            indicators_values["IXIC"] = indicators["^IXIC"][date_prev] > 0

        # SOX
        if date_prev in indicators.get("^SOX", {}):
            indicators_values["SOX"] = indicators["^SOX"][date_prev] > 0

        # VIX (역방향)
        if date_prev in indicators.get("^VIX", {}):
            indicators_values["VIX"] = indicators["^VIX"][date_prev] < 0

        # KRW (역방향)
        if date_prev in indicators.get("KRW=X", {}):
            indicators_values["KRW"] = indicators["KRW=X"][date_prev] < 0

        # FLOW
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
            indicators_values["FLOW"] = st.mean(flow_vals) > 0

        # VOL
        vol_vals = []
        for code in picks:
            ratio = volume_ratio(panel, code, di_prev)
            if ratio is not None:
                vol_vals.append(ratio)
        if vol_vals:
            indicators_values["VOL"] = st.mean(vol_vals) > 1.1

        data_points.append((avg_ret, indicators_values))

    return data_points


def calculate_alignment_and_correlation(data_points, selected_indicators):
    """특정 지표 조합에 대해 정렬도와 수익률의 상관성을 계산합니다."""
    alignments_buy = []
    alignments_sell = []

    for avg_ret, indicator_values in data_points:
        # 선택된 지표만으로 정렬도 계산
        bullish_count = sum(
            1 for ind in selected_indicators if indicator_values.get(ind, False)
        )

        if avg_ret > 0.001:
            alignments_sell.append((bullish_count, avg_ret))
        elif avg_ret < -0.001:
            alignments_buy.append((bullish_count, avg_ret))

    results = {}

    # 매도일 상관계수
    if len(alignments_sell) > 2:
        try:
            align = [x[0] for x in alignments_sell]
            rets = [x[1] for x in alignments_sell]
            r, p = stats.pearsonr(align, rets)
            results["sell"] = (r, p, len(alignments_sell))
        except:
            results["sell"] = (None, None, len(alignments_sell))
    else:
        results["sell"] = (None, None, len(alignments_sell))

    # 매수일 상관계수
    if len(alignments_buy) > 2:
        try:
            align = [x[0] for x in alignments_buy]
            rets = [x[1] for x in alignments_buy]
            r, p = stats.pearsonr(align, rets)
            results["buy"] = (r, p, len(alignments_buy))
        except:
            results["buy"] = (None, None, len(alignments_buy))
    else:
        results["buy"] = (None, None, len(alignments_buy))

    return results


def main():
    print("[로딩] 패널 데이터...")
    dates, panel = S.load_panel(verbose=False)
    print(f"  {len(dates)}개 거래일, {len(panel)}개 종목")

    print("[로딩] 미국 지표...")
    indicators = load_all_us_indicators()
    print(f"  로드 완료")

    print("[로딩] 수급 데이터...")
    flow_data = load_flow_data(set(panel.keys()))
    print(f"  로드 완료")

    print("[수집] 모든 리밸런스 데이터의 지표값...")
    data_points = collect_indicator_values(dates, panel, indicators, flow_data)
    print(f"  {len(data_points)}개 리밸런스 포인트")

    all_indicators = ["OVN", "SPX", "IXIC", "SOX", "VIX", "KRW", "FLOW", "VOL"]
    all_results = []

    print("\n" + "=" * 130)
    print("지표 조합별 상관성 분석")
    print("=" * 130)

    # 3개부터 8개까지 조합
    for combo_size in range(3, 9):
        print(f"\n[{combo_size}개 지표 조합] ({combo_size}개 조합 수 계산 중...)")

        results_for_size = []
        combos = list(combinations(all_indicators, combo_size))
        print(f"  총 {len(combos)}개 조합 분석 중...")

        for idx, combo in enumerate(combos):
            if (idx + 1) % max(1, len(combos) // 10) == 0:
                print(f"    진행: {idx + 1}/{len(combos)}")

            selected = set(combo)
            corr_results = calculate_alignment_and_correlation(data_points, selected)

            sell_r, sell_p, sell_n = corr_results.get("sell", (None, None, 0))
            buy_r, buy_p, buy_n = corr_results.get("buy", (None, None, 0))

            max_r = max(
                [x for x in [sell_r, buy_r] if x is not None],
                default=0,
            )

            all_results.append({
                "combo": combo,
                "size": combo_size,
                "sell_r": sell_r,
                "sell_p": sell_p,
                "sell_n": sell_n,
                "buy_r": buy_r,
                "buy_p": buy_p,
                "buy_n": buy_n,
                "max_r": max_r,
            })

    # 상위 15개 조합 표시
    print("\n" + "=" * 130)
    print("상위 15개 조합 (최고 상관성 기준)")
    print("=" * 130)
    print(
        f"{'순위':<6} {'지표 조합':<40} {'크기':<6} "
        f"{'매도 상관':<12} {'매도 p':<10} {'매도 n':<8} "
        f"{'매수 상관':<12} {'매수 p':<10} {'매수 n':<8} "
        f"{'최고':<10}"
    )
    print("-" * 130)

    sorted_results = sorted(all_results, key=lambda x: abs(x["max_r"]), reverse=True)

    for idx, result in enumerate(sorted_results[:15], 1):
        combo_str = "+".join(result["combo"])

        sell_r_str = f"{result['sell_r']:+.4f}" if result["sell_r"] is not None else "N/A"
        sell_p_str = f"{result['sell_p']:.4f}" if result["sell_p"] is not None else "N/A"

        buy_r_str = f"{result['buy_r']:+.4f}" if result["buy_r"] is not None else "N/A"
        buy_p_str = f"{result['buy_p']:.4f}" if result["buy_p"] is not None else "N/A"

        print(
            f"{idx:<6} {combo_str:<40} {result['size']:<6} "
            f"{sell_r_str:>11} {sell_p_str:>9} {result['sell_n']:>7} "
            f"{buy_r_str:>11} {buy_p_str:>9} {result['buy_n']:>7} "
            f"{result['max_r']:>9.4f}"
        )

    # 최고 조합 상세 분석
    print("\n" + "=" * 130)
    best = sorted_results[0]
    print(
        f"🏆 최고 조합: {'+'.join(best['combo'])} "
        f"(상관성: {best['max_r']:+.4f}, 크기: {best['size']}/8)"
    )
    print("=" * 130)

    print(f"\n📈 매도일 (강세 정렬):")
    print(f"  샘플: {best['sell_n']}개")
    if best["sell_r"] is not None:
        print(f"  상관계수: {best['sell_r']:+.4f}")
        print(f"  p-value: {best['sell_p']:.4f}")
        if best["sell_p"] < 0.05:
            print(f"  ✓ 통계적으로 유의미 (p < 0.05)")
        else:
            print(f"  ✗ 유의미하지 않음")

    print(f"\n📉 매수일 (약세 정렬):")
    print(f"  샘플: {best['buy_n']}개")
    if best["buy_r"] is not None:
        print(f"  상관계수: {best['buy_r']:+.4f}")
        print(f"  p-value: {best['buy_p']:.4f}")
        if best["buy_p"] < 0.05:
            print(f"  ✓ 통계적으로 유의미 (p < 0.05)")
        else:
            print(f"  ✗ 유의미하지 않음")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
