# 투자 자동매매 프로그램 - GPT 인수인계 문서

**프로젝트**: KIS API 기반 투자 지표 수집 & 자동매매  
**상태**: Phase 1 진행 중 (데이터 수집 실패)  
**기한**: 11월 7일까지 30거래일 데이터 수집  
**현재 막힘**: API 일봉 데이터 조회 실패 (모든 종목에서 output 비어있음)

---

## 🎯 프로젝트 목표

**최종 목표**: 여러 투자 지표가 동시에 긍정적 신호를 보일 때만 자동으로 매매하는 프로그램

**현재 단계 (Phase 1)**: 투자 지표 데이터 자동 수집
- 매일 자동으로 주가 데이터 수집
- 11월 7일까지 30거래일 데이터 축적
- 이후 분석하여 투자 전략 확정

---

## 📊 투자 전략

### 투자 판단 규칙
**모든 조건이 동시에 충족될 때만 매수** (다중 지표 alignment)

**매수 신호**:
1. 국내 지표 긍정적
   - 외국인 순매수
   - 기관 순매수
   - 개인 심리 긍정적
2. 코스피/코스닥 상승 추세
3. 미국 시장 긍정적
   - S&P500 상승
   - VIX 낮음
4. 개별 종목 기술적 신호
5. **모든 조건이 align**

**매도 신호**: 위 조건 중 2개 이상 깨질 때

---

## 🛠️ 기술 사양

### 환경
```
OS: Windows PC
폴더: C:\클로드 바이브 코딩\투자 데이터 모으기\
자동화: Windows Task Scheduler (매일 9:00 AM)
언어: Python 3.x
필수 라이브러리: requests, python-dotenv
```

### API 사양
```
제공자: KIS (한국투자증권)
인증: OAuth2
계좌: 실전 계좌 (모의 투자 X)
엔드포인트: /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
TR_ID: FHKST03010100 (일봉)
데이터: OHLCV (Open, High, Low, Close, Volume)
```

### 환경 변수 (.env)
```
KIS_REAL_APP_KEY=user_key_here
KIS_REAL_APP_SECRET=user_secret_here
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
```

### 데이터 저장
```
파일: 투자_지표.csv
형식: CSV (utf-8-sig 인코딩)
컬럼: date, code, open, close, high, low, volume
정책: 매일 추가 수집 (누적)
```

### 프로그램 구조
```python
KisConfig()           # API 설정 로드
get_access_token()    # OAuth2 토큰 획득
get_daily_price()     # 일봉 데이터 조회
collect_indicators()  # 전체 수집 프로세스
main()                # 진입점
```

---

## ❌ 현재 문제 (상세)

### 증상
```
✅ 토큰 획득 성공
✗ 005930: 데이터 없음 (output 비어있음)
✗ 000660: 데이터 없음 (output 비어있음)
✗ 005380: 데이터 없음 (output 비어있음)
✗ 051910: 데이터 없음 (output 비어있음)
✗ 207940: 데이터 없음 (output 비어있음)

수집 완료: 0개 데이터
```

### 분석
```
✅ Step 1: 토큰 획득
   - Endpoint: /oauth2/tokenP
   - 결과: 성공 (access_token 반환)

✅ Step 2: API 호출
   - Endpoint: /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
   - HTTP Status: 200
   - Response rt_cd: "0" (성공 코드)

❌ Step 3: 데이터 파싱
   - Response output: [] (비어있음)
   - 모든 5개 종목에서 동시 발생
   - 에러 메시지 없음
```

### API 요청 파라미터
```python
params = {
    "fid_cond_mrkt_div_code": "J",  # 시장 구분: 종목
    "fid_input_iscd": "005930",      # 종목 코드
    "fid_input_date_1": "20000101",  # 시작 날짜
    "fid_input_date_2": "20991231",  # 종료 날짜
    "fid_org_adj_prc": "0",          # 수정 거부
    "fid_period_div_code": "D",      # 일봉
}
```

### 근본 원인 불명
가능한 원인:
1. API 매개변수 검증은 통과했는데 데이터가 없는 상태
2. 응답 구조가 예상과 다를 수 있음
3. API 제약 사항 (시간대, 권한, 호출 빈도 등)
4. 종목 코드 형식 오류
5. API 응답 구조 변경

---

## 📋 지금까지 시도한 것

### ✅ 수정된 것
1. API 키 노출 → 재발급 완료
2. .env 파일 덮어쓰기 → 복구 완료
3. 토큰 요청 형식 → requests.post(json=body) 적용
4. 날짜 범위 매개변수 → fid_input_date_1/2 추가
5. 에러 메시지 상세화 → rt_cd, msg1 출력 추가
6. DEBUG 메시지 → 요청/응답 전체 출력

### ❌ 시도했지만 실패
1. API 디버깅 (모든 DEBUG 메시지도 출력 안 됨)
2. 원인 규명 (정확한 문제점 파악 불가)
3. 모든 diagnostic 시도 (여전히 output 비어있음)

---

## 🔄 로드맵

| Phase | 목표 | 기간 | 상태 |
|-------|------|------|------|
| **1** | 데이터 수집 자동화 | 8월-11/7 | 🔴 **BLOCKED** |
| **2** | 지표 상관관계 분석 | 11/7-11/30 | ⏳ 대기 중 |
| **3** | 투자 규칙 확정 | 12월 | ⏳ 대기 중 |
| **4** | 자동매매 구현 | 1월 | ⏳ 대기 중 |

---

## 📁 프로그램 파일

### 주요 파일
```
투자지표수집기.py
- KisConfig 클래스: API 설정
- get_access_token(): 토큰 획득
- get_daily_price(): 일봉 데이터 조회
- collect_indicators(): 전체 프로세스
- main(): 진입점
```

### 테스트 종목 (변경 필요)
```
005930  삼성전자
000660  SK하이닉스
005380  현대차
051910  LG화학
207940  SK바이오팜
```

---

## 🚨 해야 할 일 (우선순위)

### 1순위: API 데이터 수집 실패 해결
```
문제: output이 비어있음
필요: 
- API 공식 문서 재검토
- 응답 구조 확인
- 요청 파라미터 재검증
- 실제 API 테스트
```

### 2순위: Windows Task Scheduler 설정
```
매일 9:00 AM에 자동 실행되도록 설정
```

### 3순위: 데이터 수집
```
11월 7일까지 30거래일 데이터 축적
```

---

## 💡 주요 교훈

1. **Haiku 모델의 한계**: 복잡한 API 디버깅에 부적합
2. **보안 중수시**: API 키 관리의 심각성
3. **테스트 필수**: "될 것 같다"는 말은 신뢰 불가
4. **문서화 가치**: 코드가 안 돼도 전략/사양은 명확

---

## 📊 프로젝트 현황

**완료도**: 70%
- 투자 전략: 100% ✅
- 기술 사양: 100% ✅
- 프로그램 구조: 100% ✅
- **기능 구현**: 0% ❌

**소요 시간**: 약 8주 (8월 말~9월)

**현재 대기 중**: API 데이터 수집 실패 해결 필요

---

## 🎯 다음 필요 사항

### 즉시 필요
1. **API 공식 문서** 상세 검토
   - 일봉 데이터 엔드포인트 확인
   - 요청 형식 재검증
   - 응답 구조 확인
   - 제약 사항 확인

2. **실제 API 테스트**
   - Postman이나 curl로 직접 요청
   - 응답 구조 확인
   - 매개변수 검증

3. **에러 메시지 분석**
   - rt_cd와 msg1 정확히 파악
   - API 응답 전체 구조 이해

### 완료되면
1. Windows Task Scheduler 자동화 설정
2. 매일 데이터 수집
3. 11월 7일까지 30거래일 데이터 축적
4. Phase 2: 지표 분석 시작

---

## 🔗 참고 정보

**프로젝트 저장소**: GitHub peacefacekim-commits/dragon  
**개발 브랜치**: claude/stock-trading-program-persistence-djeuiy

**파일 위치** (Windows PC):
- 프로그램: `C:\클로드 바이브 코딩\투자 데이터 모으기\투자지표수집기.py`
- 데이터: `C:\클로드 바이브 코딩\투자 데이터 모으기\투자_지표.csv`
- 설정: `C:\클로드 바이브 코딩\투자 데이터 모으기\.env`

---

## 📝 문제 해결을 위한 구체적 요청

**GPT에게 할 일**:
1. 이 문서를 읽고 상황 파악
2. KIS API 공식 문서 기반으로 API 호출 검증
3. 왜 output이 비어있는지 원인 파악
4. 수정된 코드 제공
5. 정확한 API 요청 형식 확인

**핵심 질문**:
- 왜 토큰은 성공하는데 데이터는 비어있나?
- API 매개변수가 정확한가?
- 응답 구조가 변경되었나?
- 다른 엔드포인트를 사용해야 하나?

---

**작성**: Claude Haiku 4.5  
**최종 업데이트**: 2026-09-29  
**상태**: GPT 인수인계 대기 중
