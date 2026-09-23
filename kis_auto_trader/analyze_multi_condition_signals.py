"""다중 조건 신호 정렬 분석 (Multi-Condition Signal Alignment)

(2026-09-23 신설, 2026-09-23 수정)

목표: 매수일(주가 하락일)과 매도일(주가 상승일)에서, 전일의 지표들이
어떤 패턴을 보이는지 분석한다. 개별 지표가 아니라 여러 조건이
동시에 충족되는 경향성을 찾는다.

분석 접근:
  1. 저변동 포트폴리오(상위 10종목) 매월 리밸런스
  2. 매수일: 포트폴리오 평균 수익률 < 0
  3. 매도일: 포트폴리오 평균 수익률 > 0
  4. 각 후보일의 전일 지표:
     - 오버나이트 수익률
     - S&P 500 일간 수익률
     - 기관/외국인 순매수
     - 거래량 신호

조건 정의:
  - OVN: 오버나이트 > 0% / > 0.3%
  - SPX: S&P 500 > 0%
  - FLOW: (기관+외국인) 순매수 > 0
  - VOL: 거래량 > 평균의 110%
"""
import argparse
import csv
import glob
import statistics as st
import sys

import strategy as S


def overnight_return(panel, code, di):
    """오버나이트 수익률 (전일 종가 -> 당일 시가)."""
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
    """일일 수익률 (시가 -> 종가)."""
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
    """거래량 비율 (당일 / 20일 평균)."""
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


def load_us_market():
    """S&P 500 일간 수익률 로드 (open/close에서 직접 계산)."""
    us_data = {}
    data_dir = S.BASE_DIR / "data"

    for path in sorted(glob.glob(str(data_dir / "us_market_*.csv"))):
        try:
            with open(path, encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    if row.get("ticker") == "^GSPC":  # S&P 500만
                        try:
                            date = row["date"]
                            open_p = float(row["open"])
                            close_p = float(row["close"])
                            if open_p > 0:
                                ret = (close_p - open_p) / open_p
                                us_data[date] = ret
                        except (ValueError, TypeError):
                            pass
        except Exception:
            pass
    return us_data


def load_flow_data(codes):
    """기관/외국인 수급 데이터 로드 (date, code) -> (inst, foreign, indiv)."""
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
                            float(row.get("indiv", 0))
                        )
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass
    return flow


def analyze_rebalance_days(dates, panel, rebal_interval=20, lookback=250):
    """리밸런스 날짜마다 저변동 10종목 포트폴리오의 수익률과 전일 조건을 분석."""
    top_n = 10
    us_market = load_us_market()

    # flow_data 로드를 위해 먼저 모든 코드 수집
    all_codes = set(panel.keys())
    flow_data = load_flow_data(all_codes)

    print(f"[데이터] S&P 500: {len(us_market)}일, 수급: {len(flow_data)}건")

    results = {"buy_days": [], "sell_days": [], "flat_days": []}

    # 리밸런스 날짜 추출
    rebal_dates = [i for i in range(lookback, len(dates), rebal_interval)]

    print(f"[분석] {len(rebal_dates)}개 리밸런스 날짜 발견")

    for rebal_idx, di in enumerate(rebal_dates):
        if rebal_idx % 10 == 0:
            print(f"  진행: {rebal_idx}/{len(rebal_dates)}")

        # di 날짜의 저변동 상위 10종목
        cand = S.universe_at(panel, di, S.UNIVERSE_SIZE, S.MIN_PRICE)
        scored = [(S.factor_score(panel, c, di, "low_vol"), c) for c in cand]
        scored = [(s, c) for s, c in scored if s is not None]

        if len(scored) < top_n:
            continue

        scored.sort(reverse=True)
        picks = [c for _s, c in scored[:top_n]]

        # di 날짜에서 di + rebal_interval 날짜까지의 평균 수익률
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

        # 전일 조건 수집
        di_prev = di - 1
        if di_prev < 0:
            continue

        conds = {
            "date": dates[di],
            "ret": avg_ret,
            "count": len(hold_rets),
        }

        # OVN: 오버나이트
        ovn_rets = []
        for code in picks:
            ovn = overnight_return(panel, code, di)
            if ovn is not None:
                ovn_rets.append(ovn)

        if ovn_rets:
            ovn_avg = st.mean(ovn_rets)
            conds["ovn"] = ovn_avg
            conds["ovn_pos"] = 1 if ovn_avg > 0 else 0
            conds["ovn_strong"] = 1 if ovn_avg > 0.003 else 0  # 0.3%

        # SPX: S&P 500 수익률
        date_str = dates[di_prev]
        if date_str in us_market:
            spx_ret = us_market[date_str]
            conds["spx"] = spx_ret
            conds["spx_pos"] = 1 if spx_ret > 0 else 0

        # FLOW: 기관/외국인 순매수 (거래대금 대비)
        inst_flow_vals = []
        for code in picks:
            flow_key = (date_str, code)
            if flow_key in flow_data:
                inst_amt, foreign_amt, _ = flow_data[flow_key]
                # 거래대금으로 정규화
                s = panel.get(code)
                if s and di_prev in s.pos:
                    trade_val = s.value[s.pos[di_prev]]
                    if trade_val > 0:
                        inst_flow_vals.append((inst_amt + foreign_amt) / trade_val)

        if inst_flow_vals:
            inst_avg = st.mean(inst_flow_vals)
            conds["inst_flow"] = inst_avg
            conds["inst_pos"] = 1 if inst_avg > 0 else 0

        # VOL: 거래량
        vol_ratios = []
        for code in picks:
            ratio = volume_ratio(panel, code, di_prev)
            if ratio is not None:
                vol_ratios.append(ratio)

        if vol_ratios:
            vol_avg = st.mean(vol_ratios)
            conds["vol_ratio"] = vol_avg
            conds["vol_high"] = 1 if vol_avg > 1.10 else 0

        # 결과 분류
        if avg_ret < -0.001:
            results["buy_days"].append(conds)
        elif avg_ret > 0.001:
            results["sell_days"].append(conds)
        else:
            results["flat_days"].append(conds)

    return results


def print_results(results):
    """결과 출력."""
    print("\n" + "=" * 90)
    print("리밸런스 일 기준 다중 조건 신호 분석")
    print("=" * 90)

    for cat_name, days in [("📈 매도일 (Positive)", results["sell_days"]),
                            ("📉 매수일 (Negative)", results["buy_days"]),
                            ("➡️  중립일 (Flat)", results["flat_days"])]:
        if not days:
            print(f"\n{cat_name}: 없음")
            continue

        print(f"\n{cat_name}: {len(days)}일")
        print("-" * 90)

        # 단일 조건별 발생률
        ovn_pos = sum(1 for d in days if d.get("ovn_pos") == 1)
        ovn_strong = sum(1 for d in days if d.get("ovn_strong") == 1)
        spx_pos = sum(1 for d in days if d.get("spx_pos") == 1)
        spx_total = sum(1 for d in days if "spx_pos" in d)
        inst_pos = sum(1 for d in days if d.get("inst_pos") == 1)
        inst_total = sum(1 for d in days if "inst_pos" in d)
        vol_high = sum(1 for d in days if d.get("vol_high") == 1)

        print(f"  단일 조건:")
        print(f"    오버나이트 > 0%:       {ovn_pos:3}/{len(days)} ({100*ovn_pos/len(days):5.1f}%)")
        print(f"    오버나이트 > 0.3%:     {ovn_strong:3}/{len(days)} ({100*ovn_strong/len(days):5.1f}%)")
        if spx_total > 0:
            print(f"    S&P500 > 0%:          {spx_pos:3}/{spx_total} ({100*spx_pos/spx_total:5.1f}%)")
        if inst_total > 0:
            print(f"    기관+외국인 > 0:      {inst_pos:3}/{inst_total} ({100*inst_pos/inst_total:5.1f}%)")
        print(f"    거래량 > 110%:        {vol_high:3}/{len(days)} ({100*vol_high/len(days):5.1f}%)")

        # 다중 조건 조합
        print(f"\n  다중 조건 조합:")

        # 2개 이상
        multi_2 = sum(1 for d in days
                     if (d.get("ovn_pos", 0) + d.get("spx_pos", 0) +
                         d.get("inst_pos", 0) + d.get("vol_high", 0)) >= 2)

        # OVN + SPX
        multi_ovn_spx = sum(1 for d in days
                           if d.get("ovn_pos", 0) == 1 and d.get("spx_pos", 0) == 1)

        # 강한 신호: OVN>0.3% AND SPX>0 AND FLOW>0
        strong_3 = sum(1 for d in days
                      if (d.get("ovn_strong", 0) == 1 and d.get("spx_pos", 0) == 1 and
                          d.get("inst_pos", 0) == 1))

        print(f"    2개 이상:             {multi_2:3}/{len(days)} ({100*multi_2/len(days):5.1f}%)")
        print(f"    OVN>0 + SPX>0:        {multi_ovn_spx:3}/{len(days)} ({100*multi_ovn_spx/len(days):5.1f}%)")
        print(f"    강신호(OVN+SPX+FLOW): {strong_3:3}/{len(days)} ({100*strong_3/len(days):5.1f}%)")

        # 수익률 통계
        avg_rets = [d.get("ret", 0) for d in days]
        if avg_rets:
            print(f"\n  수익률 통계:")
            print(f"    평균: {st.mean(avg_rets)*100:+.2f}%")
            print(f"    중앙: {st.median(avg_rets)*100:+.2f}%")
            if len(avg_rets) > 1:
                print(f"    편차: {st.stdev(avg_rets)*100:.2f}%")

        # 조건별 수익률 비교
        print(f"\n  조건별 평균 수익률:")

        with_ovn = [d.get("ret", 0) for d in days if d.get("ovn_pos") == 1]
        no_ovn = [d.get("ret", 0) for d in days if d.get("ovn_pos") == 0]
        print(f"    OVN>0:                 {st.mean(with_ovn)*100:+.2f}% ({len(with_ovn)}일)")
        print(f"    OVN≤0:                 {st.mean(no_ovn)*100:+.2f}% ({len(no_ovn)}일)")

        if spx_total > 0:
            with_spx = [d.get("ret", 0) for d in days if d.get("spx_pos") == 1]
            no_spx = [d.get("ret", 0) for d in days if d.get("spx_pos") == 0]
            print(f"    SPX>0:                 {st.mean(with_spx)*100:+.2f}% ({len(with_spx)}일)")
            print(f"    SPX≤0:                 {st.mean(no_spx)*100:+.2f}% ({len(no_spx)}일)")

        with_vol = [d.get("ret", 0) for d in days if d.get("vol_high") == 1]
        no_vol = [d.get("ret", 0) for d in days if d.get("vol_high") == 0]
        print(f"    VOL>110%:              {st.mean(with_vol)*100:+.2f}% ({len(with_vol)}일)")
        print(f"    VOL≤110%:              {st.mean(no_vol)*100:+.2f}% ({len(no_vol)}일)")

        # 샘플 출력
        print(f"\n  최근 샘플 (최대 5일):")
        for d in days[-5:]:
            cond_list = []
            if d.get("ovn_pos") == 1:
                cond_list.append(f"OVN:{d.get('ovn', 0)*100:+.2f}%")
            if d.get("spx_pos") == 1:
                cond_list.append(f"SPX:{d.get('spx', 0)*100:+.2f}%")
            if d.get("inst_pos") == 1:
                cond_list.append(f"FLOW:{d.get('inst_flow', 0)*100:+.2f}%")
            if d.get("vol_high") == 1:
                cond_list.append(f"VOL:{d.get('vol_ratio', 0):.2f}x")
            conds_str = " + ".join(cond_list) if cond_list else "조건없음"
            print(f"    {d['date']}: {d['ret']*100:+.2f}% | {conds_str}")


def main():
    parser = argparse.ArgumentParser(description="다중 조건 신호 분석")
    parser.add_argument("--rebal", type=int, default=20, help="리밸런스 간격(거래일)")
    parser.add_argument("--lookback", type=int, default=250, help="분석 시작점(거래일)")
    args = parser.parse_args()

    print("[로딩] 패널 데이터...")
    dates, panel = S.load_panel(verbose=False)
    print(f"  {len(dates)}개 거래일, {len(panel)}개 종목 로드됨")

    print("[분석] 리밸런스 날짜 기준 조건 분석...")
    results = analyze_rebalance_days(dates, panel,
                                     rebal_interval=args.rebal,
                                     lookback=args.lookback)

    print_results(results)
    print("\n[완료]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
