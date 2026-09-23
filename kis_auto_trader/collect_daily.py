"""하루 1회, 장 마감 뒤에 도는 데이터 수집 (새 구조의 본체).

(2026-09-13 신설) 하는 일은 셋뿐이다.

  1) 고정 유니버스가 목표 개수에 못 미치면 채운다 (universe.py)
  2) 유니버스 종목들의 빠진 일봉을 받아서 패널에 채운다 (panel.py)
     - 처음 한 번은 몇 년치를 통째로 받는다 (몇십 분 걸릴 수 있음)
     - 그 뒤로는 하루치만 받으므로 1~2분이면 끝난다
  3) 오늘자 PER/PBR 등 재무지표를 기록한다 (fundamentals.py)
     - 이건 과거치를 받아올 수 없어서, 오늘부터 쌓지 않으면 영구히 빈다
  4) 장 시작 전 시장 지표 + 그날 결과를 기록한다 (market_indicators.py)
     - "나쁜 날을 피하는 필터"를 나중에 앞검증하기 위한 채점표
  5) 전략 모의 진행을 기록하고 지난 회차를 청산한다 (paper_trade.py)
     - 얼려둔 나쁜날 게이트의 판정과 실제 결과를 나란히 남긴다
  6) GitHub 에 백업한다 (backup.py)

매매도, 가상매매도 하지 않는다. 전략은 나중에 backtest.py 가 이 패널 위에서
돌린다 - 그래야 보유기간이나 손절 기준을 바꿔볼 때마다 처음부터 다시 쌓지
않아도 된다.

수집 주기가 하루 1회인 이유: 일봉 단위 전략을 보려는 것이므로 10분마다 찍는
건 같은 정보를 열 몇 번 반복 저장하는 것에 가깝다. 실제로 기존
candidate_snapshot.csv 는 1,460행이지만 실질 내용은 4거래일 x 101종목이었다.

  python collect_daily.py
"""
import sys
import traceback
from datetime import datetime

import backup
import fundamentals
import market_indicators
import panel
import paper_trade
import universe
from common import load_config


def main() -> int:
    cfg = load_config()
    print(f"=== 일일 데이터 수집 {datetime.now():%Y-%m-%d %H:%M:%S} ===")

    # 1) 유니버스
    try:
        universe.top_up(cfg)
    except Exception as e:
        print(f"[!] 유니버스 갱신 실패 (기존 목록으로 계속 진행): {e}")

    stocks = universe.load()["stocks"]
    if not stocks:
        print("[!] 유니버스가 비어 있습니다. 장중에 한 번 실행하면 종목이 채워집니다 "
              "(순위 API가 장중에만 값을 줍니다).")
        return 1

    # 2) 일봉 패널
    print(f"[패널] {len(stocks)}종목, {cfg.panel_start_date} 이후 빠진 구간을 채웁니다.")
    try:
        panel.backfill(cfg, stocks)
    except Exception as e:
        print(f"[!] 패널 수집 중 예외: {type(e).__name__}: {e}")
        traceback.print_exc()

    print(panel.summary())

    # 3) 오늘자 재무지표 (PER/PBR/외국인지분율 등)
    try:
        fundamentals.collect(cfg, stocks)
        print(fundamentals.summary())
    except Exception as e:
        print(f"[!] 재무지표 수집 중 예외 (일봉 패널에는 영향 없음): {type(e).__name__}: {e}")

    # 4) 장 시작 전 지표 + 그날 결과 기록 (2026-09-16 추가)
    #    "나쁜 날을 피하는 필터"를 나중에 채점하려면, 기준을 미리 정해두고
    #    앞으로 기록해야 한다. 과거에 맞추면 노이즈를 외운다 - 실제로 지표
    #    11개를 앞 절반에 학습시켰더니 뒤 절반에서 무너졌다(상관 0.231->0.142,
    #    평균 수익은 마이너스). 그래서 이 기록이 본검증 재료다.
    try:
        rows = market_indicators.compute_all(verbose=False)
        if rows:
            added = market_indicators.save(rows)
            print(f"[지표] {len(rows):,}일 중 새 행 {added}개 기록")
            print(market_indicators.summary())
    except Exception as e:
        print(f"[!] 지표 기록 실패 (다른 수집에는 영향 없음): {type(e).__name__}: {e}")

    # 5) 전략 모의 진행 + 나쁜날 게이트 앞검증 기록 (2026-09-17 추가)
    #    과거 데이터로는 '손실난 날의 공통점' 이 다음 기간에 유지되지 않았다
    #    (전반부 상관 +0.187 -> 후반부 -0.102, 부호 유지 13개 중 7개 = 우연
    #    수준). 그래서 기준을 gate_frozen.json 에 얼려두고 앞으로 채점한다.
    #    이 단계가 매일 돌지 않으면 채점할 재료가 안 쌓인다.
    try:
        paper_trade.record()
        paper_trade.settle()
    except Exception as e:
        print(f"[!] 모의 기록 실패 (다른 수집에는 영향 없음): {type(e).__name__}: {e}")

    # 6) 백업
    try:
        backup.backup_trade_data()
    except Exception as e:
        print(f"[!] 백업 실패 (데이터는 로컬에 남아있음): {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
