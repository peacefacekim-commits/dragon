# 예산 분석기 (오프라인 / 내부망용)

엑셀 예산 파일을 넣으면 **항목별 집계·구성비**, **예산 대비 집행률**, **기간별 추이**를
분석해 차트가 들어간 HTML 보고서와 엑셀 결과를 만들어 줍니다.

> **인터넷이 없는 PC에서 그대로 동작합니다.**
> `pip install` 이 필요 없습니다. pandas · openpyxl · matplotlib 을 쓰지 않고
> 파이썬 표준 라이브러리만으로 엑셀 읽기/쓰기와 차트를 직접 구현했습니다.

---

## 필요한 것

| 항목 | 내용 |
|---|---|
| 파이썬 | 3.9 이상 (Windows 공식 설치본이면 충분) |
| 추가 패키지 | **없음** |
| 인터넷 | **불필요** |

GUI(창 모드)는 `tkinter` 를 씁니다. Windows·macOS 공식 설치본에는 기본 포함이고,
리눅스만 `python3-tk` 가 따로 필요합니다. GUI 가 없어도 명령줄은 항상 동작합니다.

## 내부망 PC로 옮기기

1. 이 폴더 전체(`budget_analyzer/`, `samples/`, `tests/`)를 USB 등으로 복사합니다.
2. 대상 PC에 파이썬이 없다면 [python.org] 설치 파일을 함께 받아가 설치합니다.
   설치 시 **"Add python.exe to PATH"** 를 체크하세요.
3. 복사한 폴더에서 아래 명령을 실행하면 끝입니다.

설치·빌드 과정이 없습니다. 폴더를 복사하는 것이 곧 설치입니다.

## 사용법

### 창(GUI) 모드 — 가장 간편

Windows 라면 `실행.bat` 을 더블클릭하세요. 또는:

```
python -m budget_analyzer --gui
```

1. **파일 열기** 로 엑셀 선택 → 시트와 머리글 행이 자동으로 잡힙니다
2. **컬럼 지정** 에서 자동 인식 결과를 확인하고, 틀렸으면 드롭다운으로 수정
3. **분석 실행** → 보고서가 만들어지고 브라우저로 열립니다

자주 쓰는 양식은 **매핑 저장…** 으로 JSON 을 남겨두면, 다음부터 같은 양식은
**매핑 불러오기…** 한 번으로 끝납니다.

### 명령줄 모드

```bash
# 가장 단순한 형태 — 컬럼을 알아서 인식합니다
python -m budget_analyzer 예산.xlsx

# 시트와 집계 단위를 지정
python -m budget_analyzer 예산.xlsx --sheet 집행내역 --grain quarter

# 컬럼을 직접 지정 (자동 인식이 틀렸을 때)
python -m budget_analyzer 예산.xlsx --category 부서 --budget 예산액 --actual 집행액 --date 집행일자

# 엑셀·CSV 로도 함께 내보내기
python -m budget_analyzer 예산.xlsx --xlsx 결과.xlsx --csv-dir ./csv

# 시트 목록만 확인
python -m budget_analyzer 예산.xlsx --list-sheets

# 컬럼 매핑을 저장해 두고 다음에 재사용
python -m budget_analyzer 예산.xlsx --save-profile 표준양식.json
python -m budget_analyzer 다음달.xlsx --profile 표준양식.json
```

`python -m budget_analyzer --help` 로 전체 옵션을 볼 수 있습니다.

### 파이썬 코드에서 직접

```python
from budget_analyzer import read_table, guess_mapping, analyze, write_report

table = read_table("예산.xlsx", sheet="집행내역")
mapping = guess_mapping(table)      # 필요하면 mapping.category = "부서" 처럼 수정
result = analyze(table, mapping, source="예산.xlsx", grain="month")

print(result.execution_rate)        # 전체 집행률
write_report("보고서.html", result)
```

---

## 어떤 엑셀이든 받아주려고 한 것들

실무 파일은 양식이 제각각이라, 다음 경우를 자동으로 처리합니다.

- **머리글이 1행이 아닌 경우** — 위에 제목 줄·빈 줄이 있어도 실제 머리글 행을 찾습니다
  (`--header-row` 로 직접 지정 가능)
- **문자열로 들어간 금액** — `"1,234,567"`, `"1,200,000원"`, `"(1,200)"`(회계식 음수), `"12.5%"`
- **날짜 표기 혼재** — 엑셀 날짜 셀, `2026-03-09`, `2026.3.9`, `2026년 3월 9일`, `20260309`
- **한글 CSV** — `cp949`/`euc-kr` 로 저장된 파일도 자동 판별
- **중복·빈 머리글** — `금액`, `금액_1`, `컬럼5` 처럼 살려 씁니다
- **시트가 여러 개** — 지정하지 않으면 내용이 가장 많은 시트를 고릅니다(표지 시트 회피)

### 컬럼 자동 인식

머리글 이름(`예산액`, `집행액`, `계정과목`, `집행일자` …)과 실제 값의 성격
(숫자 비율, 날짜 비율, 반복도, 자릿수)을 함께 보고 역할을 추정합니다.
`사업코드`·`연번` 처럼 숫자지만 금액이 아닌 컬럼은 후보에서 제외합니다.

**추정은 반드시 확인하세요.** 보고서 머리말과 GUI 상단에 인식 결과가 표시되며,
틀렸으면 GUI 드롭다운이나 `--category` / `--budget` / `--actual` / `--date` 로 바로잡습니다.

---

## 분석 내용

**1. 항목별 집계 · 구성비** — 분류 기준별 합계, 건수, 구성비, 누적구성비.
항목이 많으면 상위 N개만 개별 표시하고 나머지는 `기타` 로 묶습니다(`--top`).

**2. 예산 대비 집행률** — 예산액·집행액·잔액·집행률과 상태 판정.

| 상태 | 기준 |
|---|---|
| 정상 | 집행률 70% 이상 100% 이하 |
| 부진 | 70% 미만 |
| 초과 | 100% 초과 |
| 예산없음(집행만) | 예산 0원인데 집행 실적이 있음 |

기준을 바꾸려면 `budget_analyzer/analysis.py` 의 `OVER_EXECUTION` /
`UNDER_EXECUTION` 값을 수정하세요.

**3. 기간별 추이** — 월·분기·연도별 합계와 누적, 직전 기간 대비 증감률.
예산액을 연초에 한 번만 계상하는 양식이면 기간별 예산 계열은 대부분 0이라
그래프가 "예산이 급감한 것처럼" 읽히므로, 그런 계열은 그래프에서 빼고 표에만 남깁니다.

**보고서** — 차트·표·경고가 담긴 HTML 파일 하나. 외부 CSS/JS/폰트/이미지를
전혀 참조하지 않아 인터넷 없이 열리고, 브라우저에서 그대로 인쇄(PDF 저장)됩니다.
라이트/다크 모드를 모두 지원합니다.

---

## 구조

```
budget_analyzer/
  table.py         경량 표 자료구조 (pandas 대체) — 값 파싱, 그룹 집계, 정렬
  xlsx_reader.py   zipfile + xml.etree 로 xlsx/csv 읽기
  xlsx_writer.py   최소 스펙 xlsx 쓰기 (숫자·퍼센트·날짜 서식, 자동 필터, 틀 고정)
  mapping.py       컬럼 역할 자동 인식 + 매핑 프로파일 저장/불러오기
  analysis.py      집계·집행률·추이 계산
  charts.py        SVG 차트 직접 생성 (matplotlib 대체)
  report.py        자기완결형 HTML 보고서
  cli.py           명령줄 인터페이스
  gui.py           tkinter 창 인터페이스
samples/
  make_sample.py   시연·테스트용 예산 엑셀 생성기
tests/
  test_budget_analyzer.py
```

## 개발

```bash
python samples/make_sample.py                 # 샘플 엑셀 생성
python -m budget_analyzer samples/예산_샘플.xlsx
python -m unittest discover -s tests -v       # 테스트 (52개)
```

## 알려진 제한

- **`.xls` (구형 바이너리) 는 읽지 못합니다.** 엑셀에서 `.xlsx` 로 다시 저장해 주세요.
- 수식이 든 셀은 **엑셀이 마지막으로 계산해 저장한 값**을 읽습니다. 수식을 다시
  계산하지는 않으므로, 다른 도구로 만든 파일이라면 엑셀에서 한 번 열어 저장하세요.
- 병합된 셀은 좌상단 값만 인식합니다.
- 매우 큰 파일(수십만 행)은 메모리에 전부 올리므로 느려질 수 있습니다.

[python.org]: https://www.python.org/downloads/windows/
