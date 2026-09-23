# 간단한 당일 거래 워크플로우 (Simple Intraday Workflow)

**핵심**: 당일 새로운 지표 수집 없음 → 전일 데이터 + OVN만 사용

---

## 📅 일일 거래 일정 (Daily Schedule)

### 09:30 - 시가 수집
```bash
# 당일 OVN(오버나이트) 계산용 시가 데이터 확인
# (자동으로 로드됨)
```

### 09:35 - 거래 결정
```bash
python trade_decision_simple.py

# 출력:
# - 전일 신호 판정 (강세 vs 약세)
# - 당일 OVN 계산
# - BUY/HOLD 결정
# - data/trade_decision_simple_YYYYMMDD_HHMMSS.json
```

**의사결정:**
- **약세 신호 + 음수 OVN** → BUY (+0.592%, 신뢰도 85%)
- **약세 신호 + 양수 OVN** → HOLD (신호 혼합, 신뢰도 50%)
- **강세 신호** → HOLD (손실 위험, 신뢰도 55%)

### 10:05 - 거래 실행 (BUY 신호 시)
```bash
python trade_execute_intraday.py

# 출력:
# - Top 10 저변동성 종목 선택
# - 초소자본(100만원) 10등분
# - 목표가/손절 설정
# - data/trade_execution_*.json
```

### 15:30 - 장 종료 처리
```bash
# 모든 포지션 매도 또는 익일 보유 결정
```

### 16:00 - 결과 분석
```bash
python analyze_daily_results.py

# 출력:
# - 실제 수익률 vs 기대값
# - 누적 성과 분석
# - data/daily_results_YYYYMMDD.json
# - data/trading_log.csv (누적)
```

---

## 🎯 의사결정 로직

### 입력값
1. **전일 신호** (어제 데이터 기반)
   - 약세 (Bearish): 당일 평균 수익률 < 0
   - 강세 (Bullish): 당일 평균 수익률 ≥ 0

2. **당일 OVN** (Overnight Return)
   - OVN = (당일 시가 - 전일 종가) / 전일 종가
   - 양수: 시장 강세로 시작
   - 음수: 시장 약세로 시작

### 거래 규칙

| 전일 신호 | OVN | 결정 | 신뢰도 | 기대 수익 | 이유 |
|---------|-----|------|--------|---------|------|
| **약세** | **음수** | **BUY** | 85% | +0.592% | 약세 강화 신호 |
| **약세** | **양수** | HOLD | 50% | +0.002% | 신호 혼합 |
| **약세** | 불명 | HOLD | 60% | +0.592% | OVN 없음 |
| **강세** | - | HOLD | 55% | -0.220% | 손실 위험 |

---

## 📊 데이터 흐름

```
┌─────────────────────┐
│  전일 종가 데이터    │ (strategy.py가 로드)
│  (panel, dates)     │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────┐
│  trade_decision_simple.py
│  - 전일 신호 판정
│  - OVN 계산
│  - 거래 결정 내림
└──────────┬──────────┘
           │
           ├─→ BUY 신호
           │   └─→ trade_execute_intraday.py
           │       └─→ 거래 실행
           │
           └─→ HOLD 신호
               └─→ 거래 스킵

┌─────────────────────┐
│  analyze_daily_results.py
│  - 실제 수익률 계산
│  - 기대값 대비 분석
│  - 누적 성과 추적
└─────────────────────┘
```

---

## 💾 파일 구조

```
kis_auto_trader/
├── trade_decision_simple.py      # 거래 결정 (간단)
├── trade_execute_intraday.py     # 거래 실행
├── analyze_daily_results.py      # 결과 분석
├── strategy.py                   # 핵심 로직
└── data/
    ├── trade_decision_simple_*.json    # 거래 결정 기록
    ├── trade_execution_*.json          # 거래 실행 기록
    ├── daily_results_YYYYMMDD.json     # 일일 결과
    └── trading_log.csv                 # 누적 로그
```

---

## ⚙️ 필수 설정

### 1. 초소자본 설정
```python
# trade_execute_intraday.py 내
demo_capital = 1000000  # 100만원
num_stocks = 10         # 10종목
per_stock = 100000      # 10만원/종목
```

### 2. 목표가/손절
```python
target_return = expected_return  # +0.592% (약세 신호)
stop_loss = -0.01               # -1%
```

---

## 🔧 실행 방법

### 옵션 1: 수동 실행
```bash
# 09:35
python trade_decision_simple.py

# 10:05 (BUY 신호 시)
python trade_execute_intraday.py

# 16:00
python analyze_daily_results.py
```

### 옵션 2: 스크립트로 자동화
```bash
# Windows (batch file)
python trade_decision_simple.py && python trade_execute_intraday.py

# Linux/Mac (cron job)
35 9 * * 1-5 python trade_decision_simple.py
05 10 * * 1-5 python trade_execute_intraday.py
0 16 * * 1-5 python analyze_daily_results.py
```

---

## 📈 성과 추적

### 일일 체크리스트
- [ ] 09:35 거래 결정 완료
- [ ] 10:05 거래 실행 (BUY 신호 시)
- [ ] 15:30 포지션 정리
- [ ] 16:00 결과 분석 완료

### 주간 검토
```bash
# trading_log.csv 분석
# - 총 거래 일수
# - 수익일 vs 손실일
# - 승률
# - 누적 수익
```

---

## 🎯 기대값 vs 실제 성과

### 약세 신호 + 음수 OVN (BUY 신호)
```
기대값:  +0.592% (평균 수익)
승률:    81.8%
샘플:    ~20-30일 (역사 데이터)

실제 성과는 시장 상황에 따라 변할 수 있음
```

### 강세 신호 또는 신호 혼합 (HOLD)
```
기대값:  -0.220% ~ +0.002% (손실 또는 중립)
승률:    45% ~ 50%
```

---

## 🚀 확장 가능성

### Phase 1 (현재)
- ✅ 전일 신호 + OVN만 사용
- ✅ 수동 또는 간단한 자동화
- ✅ 초소자본 데모 거래

### Phase 2 (추후)
- [ ] KIS API 연동 (자동 주문)
- [ ] Slack/Telegram 알림
- [ ] 실시간 손절/익절 모니터링

### Phase 3 (장기)
- [ ] 머신러닝 신호 최적화
- [ ] 다중 전략 동시 운영
- [ ] 포트폴리오 리밸런싱

---

## 📞 트러블슈팅

### 문제: "데이터 부족" 에러
```
원인: 로드된 패널 데이터가 부족
해결: strategy.py 확인, 데이터 파일 최신화
```

### 문제: "OVN 계산 불가"
```
원인: 당일 시가 데이터 없음 (시장 개장 전)
해결: 시가 데이터 수신 후 재실행
```

### 문제: "BUY 신호는 나왔는데 수익이 안 남"
```
원인: 마켓 타이밍, 개별 종목 변동성
해결: 
1. 누적 성과 추적 (단일 거래 아닌 장기)
2. 신뢰도 기준 재검토
3. 종목 선택 기준 개선
```

---

## 🎓 학습 자료

### 핵심 개념

**신호 역설:**
- 약세 신호 (거래 회피) → 높은 수익
- 강세 신호 (거래 진입) → 손실 위험
- 이유: 타이밍의 중요성

**OVN의 역할:**
- 당일 시장 방향 조기 신호
- 전일 신호 검증 수단
- 노이즈 필터링

**통계적 검증:**
- ANOVA F=83.44 (그룹 간 유의미한 차이)
- Cohen's d=3.64 (극도로 큰 효과)

---

**작성일**: 2026-09-23  
**버전**: 1.0 (Simple)  
**상태**: 준비 완료 ✅
