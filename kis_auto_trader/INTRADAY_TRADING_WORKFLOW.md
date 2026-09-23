# 당일 인트라데이 거래 워크플로우 (Daily Intraday Trading Workflow)

**목표**: 9:30~10:00 신호 수집 → 신호 검증 → 10:05 이후 거래 실행 → 일일 결과 분석

---

## 📅 일일 거래 일정 (Daily Schedule)

### 09:25 - 거래 전 준비
```bash
# 1. 패널 데이터 최신화 (어제까지의 데이터로)
python strategy.py  # 데이터 로드 검증
```

### 09:30 - 신호 수집
```bash
# 2. 당일 시장 신호 수집 (OVN, SPX, IXIC, SOX, VIX, KRW, FLOW)
python collect_intraday_signals.py

# 출력: data/today_signals_YYYYMMDD.json
```

**수집 내용:**
- **OVN (Overnight)**: 전일 종가 → 당일 시가 변화
- **SPX, IXIC, SOX**: 9:30~10:00 첫 30분 수익률
- **VIX, KRW**: 역방향 지표
- **FLOW**: 기관/외국인 순매수 (수동 입력 필요)
  - 위치: `data/today_flow.json` 
  - 형식: `{"XXXXX": {"inst": 1000000, "foreign": 500000}, ...}`

### 10:00 - 신호 비교 및 거래 결정
```bash
# 3. 어제 신호 vs 오늘 신호 비교
python compare_signals_intraday.py

# 출력: 
# - data/trade_decision_YYYYMMDD_HHMMSS.json
# - data/signal_history.json (이력 업데이트)
```

**비교 기준:**
- **신호 일치도**: 전날과 당일 신호 방향 일치 비율
- **정렬도**: 강세(4-7/7) vs 약세(0-3/7)
- **기대값**: 
  - 약세 신호 지속 → BUY 추천 (+0.592%, 승률 81.8%)
  - 강세 신호 지속 → 거래 회피 (-0.220% 손실)
  - 혼합/반전 → HOLD

### 10:05 - 거래 실행 (BUY 신호 시)
```bash
# 4. 거래 실행 (신호에 따라)
python trade_execute_intraday.py

# 출력: 
# - data/trade_execution_YYYYMMDD_HHMMSS.json
# - 주문 생성 및 포지션 진입
```

**거래 내용:**
- 종목: Top 10 저변동성 종목
- 자본: 초소자본 100만원 (데모)
- 각 종목: 10만원 균등 배분
- 목표가: 진입가 × (1 + 0.592%) = +0.592%
- 손절: 진입가 × 0.99 = -1%

### 10:05~15:30 - 실시간 모니터링
```bash
# 실시간으로 다음 항목 체크:
# 1. 목표가 도달 시 매도 (수익 확정)
# 2. 손절가 도달 시 손절 (손실 제한)
# 3. 필요시 손익분기점 진출 or 추적 손절
```

### 15:30 - 장 종료 처리
```bash
# 모든 포지션 매도 (또는 익일 보유 결정)
# - 익일 보유 시: 다음날 신호 재검증 필요
# - 모두 매도 시: 일결산 거래
```

### 16:00 - 일일 결과 분석
```bash
# 5. 실제 수익률 계산 및 분석
python analyze_daily_results.py

# 출력:
# - data/daily_results_YYYYMMDD.json
# - data/trading_log.csv (누적 기록)
```

**분석 내용:**
- 실제 수익률 vs 기대 수익률
- 개별 주문 승/패 분석
- 누적 성과 검토 (전체 기간)

---

## 📊 신호 해석 가이드 (Signal Interpretation)

### 약세 신호 (Bearish: 0-3/7 정렬도)
```
특징:
  - SPX, SOX, FLOW 중 0~3개만 강세
  - 전체 시장 약세 신호

의미:
  - "시장이 약해 보인다" = 투자 위험 높음
  - 하지만 당일 수익률은 평균 +0.592% (역설!)
  - 이유: 약세 신호 자체가 거래를 적게 하게 함 → 타이밍 향상

전략:
  - 약세 신호가 지속되면 BUY 진입
  - 신뢰도: 약세 정렬도 높을수록 신뢰도 상승
  - 기대 수익률: +0.592%, 승률 81.8%
```

### 강세 신호 (Bullish: 4-7/7 정렬도)
```
특징:
  - SPX, SOX, FLOW 중 4개 이상 강세
  - 전체 시장 강세 신호

의미:
  - "시장이 강해 보인다" = 투자 기회 많음
  - 하지만 당일 수익률은 평균 -0.220% (역설!)
  - 이유: 강세 신호에서 과도한 진입 → 타이밍 악화

전략:
  - 강세 신호가 지속되면 거래 회피 (HOLD)
  - 손실 위험: -0.220%
  - 승률: 45% (약세보다 낮음)
```

### 혼합 신호 (Mixed: 3.5/7 근처)
```
특징:
  - 신호가 명확하지 않음 (일부는 강세, 일부는 약세)
  - 지표 간 불일치

의미:
  - 불확실한 시장 상황
  - 신뢰도 낮음

전략:
  - 신호 명확화 대기 (HOLD)
  - 신뢰도 < 60% → 거래 회피
```

---

## 🎯 핵심 발견 (Key Findings)

### 1. 신호 역설 (The Paradox)
```
약세 신호 → 높은 수익 (+0.592%)
강세 신호 → 낮은 수익 (-0.220%)

WHY?
- 약세 신호: 거래를 적게 함 → 타이밍 개선
- 강세 신호: 거래를 많이 함 → 타이밍 악화
- "노이즈도 합치면 의미가 있다" (combining noise creates meaning)
```

### 2. 신호 지속성 (Signal Persistence)
```
전날 신호 → 당일 9-10시 신호 일치도

- 약세 신호: 70% 확률로 당일도 약세 유지
- 강세 신호: 65% 확률로 당일도 강세 유지
- 신호 일치율 > 70% → 높은 신뢰도
```

### 3. 정렬도의 한계 (Alignment Score Limitations)
```
R² = 0.26% (매도일에서)
R² = 29.76% (매수일에서)

의미:
- 매도일: 정렬도 증가 → 수익 상관 없음
- 매수일: 정렬도 증가 → 손실 증가 (강한 상관)
- 결론: "정렬도 8/8만 진입" 전략은 약함
```

### 4. 통계적 검증 (Statistical Validation)
```
ANOVA F-statistic: 83.44, p < 0.001
Cohen's d: 3.64 (극도로 큰 효과)

해석:
- 매도/매수/중립 구분이 매우 중요
- 개별 정렬도 변화보다 포트폴리오 방향이 결정적
```

---

## 📁 파일 구조 (File Structure)

```
data/
├── us_market_*.csv          # 미국 지표 히스토리
├── krx_flow_*.csv           # 한국 수급 데이터
├── today_signals_YYYYMMDD.json     # 당일 신호 (09:30 수집)
├── today_flow.json          # 당일 FLOW 데이터 (수동 입력)
├── signal_history.json      # 신호 이력 (일별)
├── trade_decision_*.json    # 거래 결정 (10:00)
├── trade_execution_*.json   # 거래 실행 기록 (10:05)
├── daily_results_YYYYMMDD.json     # 일일 결과 (16:00)
└── trading_log.csv          # 누적 거래 로그
```

---

## ⚙️ 필수 설정 (Required Setup)

### 1. FLOW 데이터 입력 형식
```json
{
  "000660": {"inst": 1000000, "foreign": 500000},
  "005930": {"inst": -200000, "foreign": 100000},
  ...
}
```

### 2. 초소자본 설정 (Small Capital Configuration)
```python
# trade_execute_intraday.py 내
demo_capital = 1000000  # 100만원
num_stocks = 10         # 10종목
per_stock = 100000      # 10만원/종목
```

### 3. 목표가 및 손절 설정
```python
# trade_execute_intraday.py 내
target_return = expected_return  # 기대 수익률
stop_loss = -0.01               # -1% 손절
```

---

## 🔧 트러블슈팅 (Troubleshooting)

### 문제 1: "FLOW 데이터 없음" 경고
```
원인: data/today_flow.json 파일 미존재
해결: 한국거래소 웹사이트에서 당일 기관/외국인 순매수 조회 후 입력
위치: https://www.krx.co.kr/ → 매매현황 → 기관/외국인
```

### 문제 2: yfinance에서 1분봉 데이터 안 받음
```
원인: 미국 시장 종료 시간대 또는 네트워크 지연
해결: 
1. 9:30am EST 정확히 실행 (한국시간 22:30)
2. 인터넷 연결 확인
3. VPN 사용 시 비활성화 시도
```

### 문제 3: 과거 신호 이력이 없음
```
원인: 처음 실행 또는 signal_history.json 손실
해결: 첫날은 자동으로 이력이 생성됨
     다음날부터 비교 가능
```

---

## 📈 성과 추적 (Performance Tracking)

### 일일 체크리스트
- [ ] 09:30 신호 수집 완료
- [ ] 09:35 FLOW 데이터 수동 입력
- [ ] 10:00 신호 비교 완료
- [ ] 10:05 거래 실행 (BUY 신호 시)
- [ ] 10:05~15:30 실시간 모니터링
- [ ] 15:30 포지션 정리
- [ ] 16:00 일일 결과 분석 완료

### 주간 리뷰
```bash
python analyze_weekly_performance.py
```

### 월간 리뷰
```bash
# trading_log.csv에서 월별 수익률 계산
# 1. 총 수익 변화 추이
# 2. 신뢰도별 수익률 분석
# 3. 신호 정확도 개선 여지 검토
```

---

## 🚀 향후 개선 사항 (Future Improvements)

### Phase 2 (단기)
- [ ] FLOW 데이터 자동 수집 (웹 스크래핑)
- [ ] 실시간 거래 실행 (KIS API 연동)
- [ ] 자동 손절/익절 (주문 모니터링)
- [ ] 슬랙 알림 (거래 알림)

### Phase 3 (중기)
- [ ] 머신러닝: 신호 조합 최적화
- [ ] 다중 전략: 여러 타임프레임 동시 운영
- [ ] 포트폴리오 리밸런싱: 수익/손실 종목 재배치

### Phase 4 (장기)
- [ ] 전자거래 인증: 자동 주문 승인
- [ ] 리스크 관리: 일일 손실한도 설정
- [ ] 백테스트: 과거 데이터로 시뮬레이션

---

## 📞 지원 (Support)

문제 발생 시:
1. 로그 파일 확인: `data/` 디렉토리의 JSON 파일들
2. 스크립트 직접 실행: 에러 메시지 확인
3. 데이터 검증: `strategy.py`로 패널 데이터 로드 확인

---

**작성일**: 2026-09-23  
**마지막 수정**: 2026-09-23  
**버전**: 1.0 (Beta)
