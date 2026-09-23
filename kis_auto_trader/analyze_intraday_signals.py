"""당일 종가 기반 신호 분석

분석 1: 전날 3개 지표(SPX+SOX+FLOW) vs 당일 종가 수익률
분석 2: 전날 신호 + 당일 9~10시 신호 일치도 계산 (시뮬레이션)
"""
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


def collect_daily_signals_and_returns(
    dates, panel, indicators, flow_data, rebal_interval=20, lookback=250
):
    """
    각 리밸런스 포인트에 대해:
    - 전날(di-1) 3개 지표 신호
    - 당일(di) 포트폴리오 종가 수익률
    을 수집합니다.
    """
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

        # 당일(di) 수익률
        daily_rets = []
        for code in picks:
            ret = daily_return(panel, code, di)
            if ret is not None:
                daily_rets.append(ret)

        if not daily_rets:
            continue

        daily_avg_ret = st.mean(daily_rets)

        # 전날(di-1) 지표
        di_prev = di - 1
        if di_prev < 0:
            continue

        date_prev = dates[di_prev] if di_prev < len(dates) else None

        # 전날 3개 지표 신호 (SPX, SOX, FLOW)
        spx_signal = None
        if date_prev in indicators.get("^GSPC", {}):
            spx_signal = indicators["^GSPC"][date_prev] > 0

        sox_signal = None
        if date_prev in indicators.get("^SOX", {}):
            sox_signal = indicators["^SOX"][date_prev] > 0

        flow_signal = None
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
            flow_signal = st.mean(flow_vals) > 0

        # 3개 신호가 모두 있을 때만 저장
        if spx_signal is not None and sox_signal is not None and flow_signal is not None:
            # 정렬도 계산: 3개 모두 True면 3, 모두 False면 0
            alignment = sum([spx_signal, sox_signal, flow_signal])

            # 신호 방향: 3개 모두 True=강세(1), 3개 모두 False=약세(-1), 혼합=0
            if alignment == 3:
                signal = 1  # 강세
            elif alignment == 0:
                signal = -1  # 약세
            else:
                signal = 0  # 혼합

            data_points.append({
                "date_prev": date_prev,
                "date": dates[di],
                "prev_signals": {
                    "spx": spx_signal,
                    "sox": sox_signal,
                    "flow": flow_signal,
                },
                "alignment": alignment,
                "signal": signal,
                "daily_return": daily_avg_ret,
            })

    return data_points


def analyze_daily_signals(data_points):
    """전날 신호별 당일 수익률 분석."""
    print("\n" + "=" * 100)
    print("분석 A: 전날 3개 지표 신호 vs 당일 종가 수익률")
    print("=" * 100)

    # 신호별로 분류
    strong_signals = [d for d in data_points if d["signal"] == 1]  # 강세 (3/3)
    weak_signals = [d for d in data_points if d["signal"] == -1]   # 약세 (0/3)
    mixed_signals = [d for d in data_points if d["signal"] == 0]   # 혼합

    print(f"\n📊 샘플 분포:")
    print(f"  강세 신호 (3/3): {len(strong_signals)}일")
    print(f"  약세 신호 (0/3): {len(weak_signals)}일")
    print(f"  혼합 신호 (1-2/3): {len(mixed_signals)}일")
    print(f"  총합: {len(data_points)}일")

    # 강세 신호 분석
    if strong_signals:
        strong_rets = [d["daily_return"] for d in strong_signals]
        print(f"\n📈 강세 신호 당일 수익률 (SPX>0, SOX>0, FLOW>0):")
        print(f"  샘플: {len(strong_signals)}개")
        print(f"  평균: {st.mean(strong_rets)*100:+.3f}%")
        print(f"  중앙값: {st.median(strong_rets)*100:+.3f}%")
        print(f"  승률: {sum(1 for r in strong_rets if r > 0)/len(strong_rets)*100:.1f}%")
        if len(strong_rets) > 1:
            print(f"  편차: {st.stdev(strong_rets)*100:.3f}%")

    # 약세 신호 분석
    if weak_signals:
        weak_rets = [d["daily_return"] for d in weak_signals]
        print(f"\n📉 약세 신호 당일 수익률 (SPX<0, SOX<0, FLOW<0):")
        print(f"  샘플: {len(weak_signals)}개")
        print(f"  평균: {st.mean(weak_rets)*100:+.3f}%")
        print(f"  중앙값: {st.median(weak_rets)*100:+.3f}%")
        print(f"  승률: {sum(1 for r in weak_rets if r > 0)/len(weak_rets)*100:.1f}%")
        if len(weak_rets) > 1:
            print(f"  편차: {st.stdev(weak_rets)*100:.3f}%")

    # 혼합 신호 분석
    if mixed_signals:
        mixed_rets = [d["daily_return"] for d in mixed_signals]
        print(f"\n➡️  혼합 신호 당일 수익률 (1-2/3 정렬):")
        print(f"  샘플: {len(mixed_signals)}개")
        print(f"  평균: {st.mean(mixed_rets)*100:+.3f}%")
        print(f"  중앙값: {st.median(mixed_rets)*100:+.3f}%")
        print(f"  승률: {sum(1 for r in mixed_rets if r > 0)/len(mixed_rets)*100:.1f}%")

    # 신호별 비교
    if strong_signals and weak_signals:
        print(f"\n🔍 신호 효과성 비교:")
        strong_mean = st.mean([d["daily_return"] for d in strong_signals])
        weak_mean = st.mean([d["daily_return"] for d in weak_signals])
        diff = strong_mean - weak_mean

        print(f"  강세 평균: {strong_mean*100:+.3f}%")
        print(f"  약세 평균: {weak_mean*100:+.3f}%")
        print(f"  차이: {diff*100:+.3f}%p")

        # ANOVA 검정
        if mixed_signals:
            strong_rets = [d["daily_return"] for d in strong_signals]
            weak_rets = [d["daily_return"] for d in weak_signals]
            mixed_rets = [d["daily_return"] for d in mixed_signals]
            try:
                f_stat, p_value = stats.f_oneway(strong_rets, weak_rets, mixed_rets)
                print(f"\n  ANOVA F-통계량: {f_stat:.4f}")
                print(f"  p-value: {p_value:.4f}")
                if p_value < 0.05:
                    print(f"  ✓ 그룹 간 유의미한 차이 존재")
                else:
                    print(f"  ✗ 그룹 간 유의미한 차이 없음")
            except:
                pass

    return {
        "strong": strong_signals,
        "weak": weak_signals,
        "mixed": mixed_signals,
    }


def simulate_intraday_agreement(data_points):
    """
    당일 9~10시 신호 시뮬레이션.

    가정: 당일 9~10시의 3개 지표 변화는
    - 전날과 같은 방향일 확률: ~70% (대체로 지속)
    - 전날과 반대 방향일 확률: ~30% (반전)

    이것은 데이터 없이 통계 기반 시뮬레이션입니다.
    """
    print("\n" + "=" * 100)
    print("분석 B: 당일 9~10시 신호 일치도 시뮬레이션 (데이터 없음)")
    print("=" * 100)

    print("\n⚠️  주의: 당일 9~10시 실제 데이터가 없어 시뮬레이션입니다")
    print("     (10분봉/시간봉 데이터 수집 필요)\n")

    # 시나리오 1: 전날 신호가 당일 9~10시에도 유지된다고 가정 (70%)
    agreement_rate = 0.70

    print(f"📋 시뮬레이션 가정:")
    print(f"  - 당일 9~10시가 전날과 같은 방향: {agreement_rate*100:.0f}%")
    print(f"  - 당일 9~10시가 전날과 반대 방향: {(1-agreement_rate)*100:.0f}%")

    strong_signals = [d for d in data_points if d["signal"] == 1]
    weak_signals = [d for d in data_points if d["signal"] == -1]

    # 일치하는 경우와 불일치하는 경우 분리 (시뮬레이션)
    np.random.seed(42)

    strong_agree = int(len(strong_signals) * agreement_rate)
    strong_disagree = len(strong_signals) - strong_agree

    weak_agree = int(len(weak_signals) * agreement_rate)
    weak_disagree = len(weak_signals) - weak_agree

    print(f"\n강세 신호 ({len(strong_signals)}일):")
    print(f"  일치 (전날+당일 모두 강세): {strong_agree}일")
    print(f"  불일치 (전날 강세, 당일 약세): {strong_disagree}일")

    print(f"\n약세 신호 ({len(weak_signals)}일):")
    print(f"  일치 (전날+당일 모두 약세): {weak_agree}일")
    print(f"  불일치 (전날 약세, 당일 강세): {weak_disagree}일")

    # 수익률 비교 (시뮬레이션)
    if strong_agree > 0:
        strong_ret_agree = st.mean(
            [d["daily_return"] for d in strong_signals[:strong_agree]]
        )
        print(f"\n📈 강세 일치 수익률: {strong_ret_agree*100:+.3f}%")

    if weak_agree > 0:
        weak_ret_agree = st.mean(
            [d["daily_return"] for d in weak_signals[:weak_agree]]
        )
        print(f"📉 약세 일치 수익률: {weak_ret_agree*100:+.3f}%")

    print(f"\n✅ 결론:")
    print(f"  전날 신호 + 당일 9~10시 신호 일치 시만 투자하면")
    print(f"  거래 기회: {strong_agree + weak_agree}일 ({(strong_agree + weak_agree)/len(data_points)*100:.1f}%)")
    print(f"  신호 신뢰도: 더 높을 것으로 예상 (실제는 당일 9~10시 데이터 필요)")


def main():
    print("[로딩] 패널 데이터...")
    dates, panel = S.load_panel(verbose=False)
    print(f"  {len(dates)}개 거래일")

    print("[로딩] 미국 지표...")
    indicators = load_all_us_indicators()

    print("[로딩] 수급 데이터...")
    flow_data = load_flow_data(set(panel.keys()))

    print("[수집] 당일 종가 수익률 데이터...")
    data_points = collect_daily_signals_and_returns(dates, panel, indicators, flow_data)
    print(f"  {len(data_points)}개 리밸런스 포인트")

    # 분석 A
    result_a = analyze_daily_signals(data_points)

    # 분석 B (시뮬레이션)
    simulate_intraday_agreement(data_points)

    # 실제 데이터 필요
    print("\n" + "=" * 100)
    print("📌 다음 단계")
    print("=" * 100)
    print("\n당일 9~10시 신호의 정확한 영향을 보려면:")
    print("  1. 당일 9~10시(개장~10시) 3개 지표 데이터 수집")
    print("  2. 실제 당일 9~10시 신호 vs 당일 종가 수익률 상관성 분석")
    print("  3. '전날 신호 + 당일 신호 일치'할 때만 투자 시뮬레이션")
    print("\n현재: 종가 데이터만 있음 (개장~종가)")
    print("필요: 시간대별 데이터 (10분봉 또는 시간봉)")

    print("\n[완료]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
