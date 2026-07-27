"""예산 분석 엔진.

세 가지 관점을 만든다.
  1. 항목별 집계·구성비  (어디에 얼마를 쓰는가)
  2. 예산 대비 집행률     (계획대로 쓰고 있는가)
  3. 기간별 추이          (언제 쓰는가)
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from .mapping import ColumnMapping
from .table import Table, to_date, to_number

__all__ = ["AnalysisResult", "analyze", "PeriodGrain"]


# 집행률 판정 기준. 실무에서 흔히 쓰는 구간을 그대로 옮겼다.
OVER_EXECUTION = 1.0
UNDER_EXECUTION = 0.7
PeriodGrain = str  # "month" | "quarter" | "year"


@dataclass
class AnalysisResult:
    """분석 산출물 묶음. 보고서·엑셀 내보내기가 이걸 그대로 읽는다."""

    source: str
    sheet: str
    mapping: ColumnMapping
    row_count: int
    breakdown: Table | None = None
    execution: Table | None = None
    trend: Table | None = None
    totals: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    generated_at: _dt.datetime = field(default_factory=_dt.datetime.now)
    grain: PeriodGrain = "month"

    @property
    def execution_rate(self) -> float | None:
        budget = self.totals.get("예산액")
        actual = self.totals.get("집행액")
        if budget is None or actual is None or budget == 0:
            return None
        return actual / budget

    def tables(self) -> list[Table]:
        """내보내기용 표 목록 (비어있는 건 제외)."""
        found = []
        for table in (self.breakdown, self.execution, self.trend):
            if table is not None and len(table):
                found.append(table)
        return found


def _period_key(value: object, grain: PeriodGrain) -> str | None:
    """날짜/기간 값을 정렬 가능한 문자열 키로 바꾼다."""
    date = to_date(value)
    if date is not None:
        if grain == "year":
            return f"{date.year}"
        if grain == "quarter":
            return f"{date.year}-Q{(date.month - 1) // 3 + 1}"
        return f"{date.year}-{date.month:02d}"

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    # "3월", "2분기", "1Q" 처럼 연도 없이 기간만 적힌 컬럼도 받아준다.
    digits = "".join(c for c in text if c.isdigit())
    if not digits:
        return None
    number = int(digits)
    if "분기" in text or text.upper().endswith("Q") or text.upper().startswith("Q"):
        return f"Q{number}" if 1 <= number <= 4 else None
    if "월" in text or text.isdigit():
        if 1 <= number <= 12:
            return f"{number:02d}월"
        if 1900 <= number <= 2200:
            return str(number)
    return None


def _build_breakdown(
    table: Table, mapping: ColumnMapping, value_column: str, top_n: int
) -> tuple[Table, list[str]]:
    """항목별 합계 + 구성비 + 누적 구성비."""
    warnings: list[str] = []
    category = mapping.category
    if category is None:
        raise ValueError("분류 기준 컬럼을 찾지 못했습니다.")

    grouped = table.group_sum(category, [value_column]).sort_by(value_column)
    grouped = grouped.add_share(value_column, "구성비")

    running = 0.0
    total = grouped.total(value_column)
    cumulative: list[float | None] = []
    for row in grouped.rows:
        number = to_number(row[grouped.index_of(value_column)]) or 0.0
        running += number
        cumulative.append(running / total if total else None)
    grouped = grouped.with_column("누적구성비", cumulative)

    if top_n and len(grouped) > top_n:
        head = Table(grouped.columns, grouped.rows[:top_n], grouped.name)
        rest = Table(grouped.columns, grouped.rows[top_n:], grouped.name)
        rest_row = [f"기타 ({len(rest)}개 항목)", rest.total(value_column)]
        rest_row.append(sum(to_number(r[rest.index_of("건수")]) or 0 for r in rest.rows))
        rest_row.append(rest.total(value_column) / total if total else None)
        rest_row.append(1.0 if total else None)
        grouped = Table(grouped.columns, head.rows + [rest_row], grouped.name)
        warnings.append(f"항목이 많아 상위 {top_n}개만 개별 표시하고 나머지는 '기타'로 묶었습니다.")

    grouped.name = f"항목별집계({category})"
    return grouped, warnings


def _build_execution(table: Table, mapping: ColumnMapping) -> tuple[Table, list[str]]:
    """예산 대비 집행률, 잔액, 상태 판정."""
    warnings: list[str] = []
    category, budget_col, actual_col = mapping.category, mapping.budget, mapping.actual
    if not (category and budget_col and actual_col):
        raise ValueError("예산액·집행액 컬럼이 모두 필요합니다.")

    grouped = table.group_sum(category, [budget_col, actual_col])
    budget_idx = grouped.index_of(budget_col)
    actual_idx = grouped.index_of(actual_col)

    remaining: list[float] = []
    rates: list[float | None] = []
    statuses: list[str] = []
    for row in grouped.rows:
        budget = to_number(row[budget_idx]) or 0.0
        actual = to_number(row[actual_idx]) or 0.0
        remaining.append(budget - actual)
        if budget == 0:
            rates.append(None)
            statuses.append("예산없음(집행만)" if actual else "-")
            continue
        rate = actual / budget
        rates.append(rate)
        if rate > OVER_EXECUTION:
            statuses.append("초과")
        elif rate < UNDER_EXECUTION:
            statuses.append("부진")
        else:
            statuses.append("정상")

    result = (
        grouped.with_column("잔액", remaining)
        .with_column("집행률", rates)
        .with_column("상태", statuses)
        .sort_by(budget_col)
    )
    result.name = "예산대비집행률"

    over = sum(1 for s in statuses if s == "초과")
    under = sum(1 for s in statuses if s == "부진")
    no_budget = sum(1 for s in statuses if s == "예산없음(집행만)")
    if over:
        warnings.append(f"예산을 초과한 항목이 {over}개 있습니다.")
    if under:
        warnings.append(f"집행률 {UNDER_EXECUTION:.0%} 미만인 부진 항목이 {under}개 있습니다.")
    if no_budget:
        warnings.append(f"예산 없이 집행만 있는 항목이 {no_budget}개 있습니다.")
    return result, warnings


def _build_trend(
    table: Table, mapping: ColumnMapping, value_column: str, grain: PeriodGrain
) -> tuple[Table | None, list[str]]:
    """기간별 합계 + 누적 + 전기 대비 증감률."""
    warnings: list[str] = []
    date_column = mapping.date
    if date_column is None:
        return None, ["일자/기간 컬럼이 없어 기간별 추이는 건너뛰었습니다."]

    measures = [c for c in (mapping.budget, mapping.actual) if c] or [value_column]

    keyed = table.with_column(
        "__period__", lambda record: _period_key(record[date_column], grain)
    )
    unparsed = sum(1 for value in keyed.column("__period__") if value is None)
    if unparsed:
        warnings.append(
            f"'{date_column}' 값 중 {unparsed}건은 기간으로 해석하지 못해 추이에서 제외했습니다."
        )
    keyed = keyed.filter(lambda record: record["__period__"] is not None)
    if not len(keyed):
        return None, warnings + [f"'{date_column}' 에서 유효한 기간을 찾지 못했습니다."]

    grouped = keyed.group_sum("__period__", measures)
    rows = sorted(grouped.rows, key=lambda row: str(row[0]))
    grouped = Table(["기간"] + grouped.columns[1:], rows, "기간별추이")

    primary = measures[-1]
    primary_idx = grouped.index_of(primary)
    running = 0.0
    cumulative: list[float] = []
    change: list[float | None] = []
    previous: float | None = None
    for row in grouped.rows:
        number = to_number(row[primary_idx]) or 0.0
        running += number
        cumulative.append(running)
        change.append(None if not previous else (number - previous) / previous)
        previous = number

    grouped = grouped.with_column(f"누적{primary}", cumulative).with_column("전기대비", change)
    return grouped, warnings


def analyze(
    table: Table,
    mapping: ColumnMapping,
    source: str = "",
    top_n: int = 15,
    grain: PeriodGrain = "month",
) -> AnalysisResult:
    """표 하나를 세 관점으로 분석한다. 불가능한 관점은 경고만 남기고 건너뛴다."""
    result = AnalysisResult(
        source=source,
        sheet=table.name,
        mapping=mapping,
        row_count=len(table),
        grain=grain,
    )

    value_column = mapping.value_column
    if value_column is None:
        result.warnings.append("금액으로 볼 수 있는 숫자 컬럼을 찾지 못했습니다. 컬럼 매핑을 확인해 주세요.")
        return result

    for label, column in (("예산액", mapping.budget), ("집행액", mapping.actual), ("금액", mapping.amount)):
        if column:
            result.totals[label] = table.total(column)

    if mapping.category:
        try:
            result.breakdown, warnings = _build_breakdown(table, mapping, value_column, top_n)
            result.warnings.extend(warnings)
        except (ValueError, KeyError) as error:
            result.warnings.append(f"항목별 집계 실패: {error}")
    else:
        result.warnings.append("분류 기준 컬럼이 없어 항목별 집계는 건너뛰었습니다.")

    if mapping.budget and mapping.actual and mapping.category:
        try:
            result.execution, warnings = _build_execution(table, mapping)
            result.warnings.extend(warnings)
        except (ValueError, KeyError) as error:
            result.warnings.append(f"집행률 분석 실패: {error}")
    else:
        result.warnings.append("예산액·집행액 컬럼이 함께 있어야 집행률을 계산할 수 있습니다.")

    try:
        result.trend, warnings = _build_trend(table, mapping, value_column, grain)
        result.warnings.extend(warnings)
    except (ValueError, KeyError) as error:
        result.warnings.append(f"기간별 추이 분석 실패: {error}")

    return result
