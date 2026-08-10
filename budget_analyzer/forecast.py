"""집행 전망: 작년 같은 기간의 지출 패턴으로 올해 목표일까지의 누계 집행액을 추정한다.

계산 방식은 일부러 단순하게 잡았다. 사업 하나하나를 정교하게 대응시키는 대신,
표준 지출과목인 "목코드+세목코드" 단위로 다음을 구한다.

    작년, 기준일까지 쓴 돈 대비 (기준일 다음날 ~ 목표일)에 "얼마나 더" 썼는지 비율

그 비율을 올해의 "기준일까지 현재 집행액"에 곱해 남은 기간의 예상 증가액으로 삼고,
사용자가 조절하는 가중치(%)를 한 번 더 곱한다. 목/세목 단위로 대충 "작년엔 이맘때
이만큼 늘었다"는 감을 옮기는 것이라 세부사업 단위까지 정확히 맞추려 하지 않는다.

    전망 증가액 = 현재 집행액 × 작년 동기간 증감율 × (가중치 / 100)
    전망 누계액 = 현재 집행액 + 전망 증가액

산출물은 엑셀이며, 가중치는 '설정' 시트의 셀 하나를 모든 행이 수식으로 참조하므로
그 값만 바꾸면 전체 전망이 다시 계산된다. 기준일·목표일은 계산 시점에 원본 데이터에서
구간을 이미 잘라 놓았기 때문에(작년 실적 자체를 다시 불러와야 함) 날짜를 바꾸려면
도구를 다시 실행해야 한다.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Sequence

from .table import Table, to_date, to_number
from .xlsx_reader import SpreadsheetError, read_table
from .xlsx_writer import Formula, write_xlsx

__all__ = [
    "ForecastError",
    "ForecastSettings",
    "ForecastResult",
    "build_forecast",
    "write_forecast",
    "add_arguments",
    "run_from_args",
]

_CODE_PREFIX = re.compile(r"^\[([^\]]*)\]")

# (역할, 정확히 일치하는 이름들, 이름에 포함되면 인정하는 조각들)
_HISTORY_DATE_HINTS = (["원인행위일자"], ["일자", "날짜"])
_HISTORY_AMOUNT_HINTS = (["원인행위금액"], ["원인행위금액", "지출액", "금액"])
_HISTORY_ITEM_HINTS = (["목코드"], ["목코드"])
_HISTORY_SUBITEM_HINTS = (["세목코드"], ["세목코드"])

_CURRENT_ITEM_HINTS = (["목"], ["목"])
_CURRENT_SUBITEM_HINTS = (["세목"], ["세목"])
_CURRENT_BUDGET_HINTS = (["26년예산"], ["예산"])
_CURRENT_EXEC_HINTS = ([], ["현재"])
_CURRENT_TARGET_HINTS = ([], ["전망"])


class ForecastError(Exception):
    """전망을 계산할 수 없을 때."""


def _extract_code(value: object) -> str:
    """``"[220]여비"`` -> ``"220"``. 대괄호가 없으면 원문을 그대로 코드로 쓴다."""
    text = "" if value is None else str(value).strip()
    match = _CODE_PREFIX.match(text)
    return match.group(1).strip() if match else text


def _find_column(columns: Sequence[str], exact: Sequence[str], contains: Sequence[str]) -> str | None:
    for name in exact:
        if name in columns:
            return name
    for column in columns:
        if any(token in column for token in contains):
            return column
    return None


def _require_column(columns: Sequence[str], override: str | None, hints: tuple, label: str) -> str:
    if override:
        if override not in columns:
            raise ForecastError(f"'{override}' 컬럼이 없습니다. 사용 가능: {', '.join(columns)}")
        return override
    found = _find_column(columns, *hints)
    if not found:
        raise ForecastError(
            f"{label} 컬럼을 자동으로 찾지 못했습니다. --history-* / --current-* 옵션으로 직접 지정하세요. "
            f"사용 가능한 컬럼: {', '.join(columns)}"
        )
    return found


def end_of_quarter(date: _dt.date) -> _dt.date:
    """``date`` 가 속한 분기의 마지막 날."""
    quarter_end_month = ((date.month - 1) // 3 + 1) * 3
    if quarter_end_month == 12:
        return _dt.date(date.year, 12, 31)
    return _dt.date(date.year, quarter_end_month + 1, 1) - _dt.timedelta(days=1)


def _shift_year(date: _dt.date, delta: int) -> _dt.date:
    try:
        return date.replace(year=date.year + delta)
    except ValueError:  # 2/29 같은 날짜의 대비책
        return date.replace(month=2, day=28, year=date.year + delta)


@dataclass
class ForecastSettings:
    base_date: _dt.date
    target_date: _dt.date
    weight_percent: float = 100.0
    history_base_date: _dt.date = field(init=False)
    history_target_date: _dt.date = field(init=False)

    def __post_init__(self) -> None:
        if self.target_date <= self.base_date:
            raise ForecastError("목표일은 기준일보다 뒤여야 합니다.")
        self.history_base_date = _shift_year(self.base_date, -1)
        self.history_target_date = _shift_year(self.target_date, -1)


@dataclass
class ForecastResult:
    settings: ForecastSettings
    table: Table
    item_column: str
    subitem_column: str
    exec_column: str
    budget_column: str | None
    target_column: str
    overall_ratio: float
    matched_rows: int
    unmatched_rows: int
    warnings: list[str] = field(default_factory=list)


def _compute_ratios(
    history: Table,
    settings: ForecastSettings,
    date_column: str,
    amount_column: str,
    item_column: str,
    subitem_column: str,
) -> tuple[dict[tuple[str, str], float], float]:
    base_totals: dict[tuple[str, str], float] = {}
    remain_totals: dict[tuple[str, str], float] = {}
    base_all = 0.0
    remain_all = 0.0

    for record in history:
        date = to_date(record.get(date_column))
        amount = to_number(record.get(amount_column))
        if date is None or amount is None:
            continue
        key = (
            str(record.get(item_column) or "").strip(),
            str(record.get(subitem_column) or "").strip(),
        )
        if date <= settings.history_base_date:
            base_totals[key] = base_totals.get(key, 0.0) + amount
            base_all += amount
        elif settings.history_base_date < date <= settings.history_target_date:
            remain_totals[key] = remain_totals.get(key, 0.0) + amount
            remain_all += amount

    overall_ratio = (remain_all / base_all) if base_all else 0.0
    ratios = {
        key: (remain_totals.get(key, 0.0) / base if base else overall_ratio)
        for key, base in base_totals.items()
    }
    return ratios, overall_ratio


def build_forecast(
    history: Table,
    current: Table,
    settings: ForecastSettings,
    *,
    history_date_column: str | None = None,
    history_amount_column: str | None = None,
    history_item_column: str | None = None,
    history_subitem_column: str | None = None,
    current_item_column: str | None = None,
    current_subitem_column: str | None = None,
    current_budget_column: str | None = None,
    current_exec_column: str | None = None,
    current_target_column: str | None = None,
) -> ForecastResult:
    """작년 상세 거래(``history``)와 올해 집행 현황(``current``)으로 집행 전망을 계산한다."""

    date_col = _require_column(history.columns, history_date_column, _HISTORY_DATE_HINTS, "작년 데이터의 원인행위일자")
    amount_col = _require_column(history.columns, history_amount_column, _HISTORY_AMOUNT_HINTS, "작년 데이터의 금액")
    hist_item_col = _require_column(history.columns, history_item_column, _HISTORY_ITEM_HINTS, "작년 데이터의 목코드")
    hist_subitem_col = _require_column(history.columns, history_subitem_column, _HISTORY_SUBITEM_HINTS, "작년 데이터의 세목코드")

    item_col = _require_column(current.columns, current_item_column, _CURRENT_ITEM_HINTS, "올해 현황의 목")
    subitem_col = _require_column(current.columns, current_subitem_column, _CURRENT_SUBITEM_HINTS, "올해 현황의 세목")
    exec_col = _require_column(current.columns, current_exec_column, _CURRENT_EXEC_HINTS, "올해 현황의 '현재 집행' 금액")
    target_col = _require_column(current.columns, current_target_column, _CURRENT_TARGET_HINTS, "올해 현황의 '집행 전망' 칸")
    budget_col = current_budget_column or _find_column(current.columns, *_CURRENT_BUDGET_HINTS)

    ratios, overall_ratio = _compute_ratios(history, settings, date_col, amount_col, hist_item_col, hist_subitem_col)

    ratio_column = "작년동기간증감율(%)"
    increase_column = "가중치적용_예상증가액"
    rate_column = "전망집행률(%)"

    columns = list(current.columns) + [ratio_column, increase_column]
    if budget_col:
        columns.append(rate_column)

    item_idx = current.index_of(item_col)
    subitem_idx = current.index_of(subitem_col)
    exec_idx = current.index_of(exec_col)
    target_idx = current.index_of(target_col)
    budget_idx = current.index_of(budget_col) if budget_col else None

    exec_letter = _column_letter(exec_idx)
    ratio_letter = _column_letter(len(current.columns))
    increase_letter = _column_letter(len(current.columns) + 1)
    target_letter = _column_letter(target_idx)
    budget_letter = _column_letter(budget_idx) if budget_idx is not None else None

    # 목/세목이 둘 다 비어 있는 행은 개별 사업이 아니라 '총계' 류의 합계 행으로 본다.
    # 그런 행은 자체적으로 비율을 적용하지 않고, 다른 상세 행들의 전망을 그대로 더한다
    # (그래야 총계가 상세 행 합계와 항상 일치한다).
    detail_row_numbers = [
        row_number
        for row_number, row in enumerate(current.rows, start=2)
        if _extract_code(row[item_idx]) or _extract_code(row[subitem_idx])
    ]

    matched = 0
    unmatched = 0
    rows: list[list[object]] = []
    for row_number, row in enumerate(current.rows, start=2):
        is_total_row = row_number not in detail_row_numbers
        new_row = list(row)

        if is_total_row and detail_row_numbers:
            target_refs = _row_ranges(target_letter, detail_row_numbers)
            increase_refs = _row_ranges(increase_letter, detail_row_numbers)
            new_row[target_idx] = Formula(f"=SUM({target_refs})")
            new_row.append(None)
            new_row.append(Formula(f"=SUM({increase_refs})"))
        else:
            key = (_extract_code(row[item_idx]), _extract_code(row[subitem_idx]))
            ratio = ratios.get(key)
            if ratio is None:
                ratio = overall_ratio
                unmatched += 1
            else:
                matched += 1

            new_row[target_idx] = Formula(
                f"={exec_letter}{row_number}+{increase_letter}{row_number}"
            )
            # 비율/퍼센트 계열 컬럼(이름에 '율'·'%' 포함)은 xlsx_writer 가 자동으로
            # 퍼센트 서식(0.00%)을 입혀 화면에 ×100 해서 보여주므로, 셀 값 자체는
            # 분수(0.5 = 50%)로 저장해야 한다 (report.py 의 '비율' 서식과 같은 관례).
            new_row.append(round(ratio, 4))
            new_row.append(
                Formula(
                    f"={exec_letter}{row_number}*{ratio_letter}{row_number}"
                    f"*'설정'!$B$6/100"
                )
            )

        if budget_col:
            new_row.append(
                Formula(
                    f"=IF({budget_letter}{row_number}=0,\"\","
                    f"{target_letter}{row_number}/{budget_letter}{row_number})"
                )
            )
        rows.append(new_row)

    table = Table(columns, rows, name="집행전망")

    warnings = []
    if unmatched:
        warnings.append(
            f"{unmatched}개 행은 작년 데이터에 같은 목/세목 실적이 없어 "
            f"전체 평균 증감율({overall_ratio * 100:.1f}%)을 대신 적용했습니다."
        )

    return ForecastResult(
        settings=settings,
        table=table,
        item_column=item_col,
        subitem_column=subitem_col,
        exec_column=exec_col,
        budget_column=budget_col,
        target_column=target_col,
        overall_ratio=overall_ratio,
        matched_rows=matched,
        unmatched_rows=unmatched,
        warnings=warnings,
    )


def _row_ranges(column_letter: str, row_numbers: Sequence[int]) -> str:
    """연속된 행 번호를 ``N3:N671`` 같은 구간으로 묶어 SUM 인자를 짧게 만든다."""
    if not row_numbers:
        return "0"
    ordered = sorted(row_numbers)
    ranges: list[str] = []
    start = previous = ordered[0]
    for number in ordered[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append(f"{column_letter}{start}" if start == previous else f"{column_letter}{start}:{column_letter}{previous}")
        start = previous = number
    ranges.append(f"{column_letter}{start}" if start == previous else f"{column_letter}{start}:{column_letter}{previous}")
    return ",".join(ranges)


def _column_letter(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _settings_table(result: ForecastResult) -> Table:
    settings = result.settings
    rows = [
        ["기준일(올해)", settings.base_date, "현재 집행 기준일 — 이 날짜까지의 실적을 그대로 씁니다"],
        ["목표일(올해)", settings.target_date, "전망하려는 목표일 (예: 분기 말)"],
        ["작년 동기간 시작", settings.history_base_date + _dt.timedelta(days=1), "작년 기준일 다음날"],
        ["작년 동기간 종료", settings.history_target_date, "작년 목표일과 같은 날짜"],
        ["가중치(%)", round(settings.weight_percent, 2), "이 값을 바꾸면 '집행전망' 시트 전체가 다시 계산됩니다. 100=작년과 같은 정도로 증가"],
        [
            "전체 평균 증감율(%)",
            round(result.overall_ratio * 100, 2),
            "작년 실적이 없는 목/세목에 대신 적용한 값 (참고용, 수식에서 쓰이지 않음)",
        ],
    ]
    return Table(["항목", "값", "설명"], rows, name="설정")


def write_forecast(path: str, result: ForecastResult) -> str:
    return write_xlsx(path, [_settings_table(result), result.table])


# ── CLI ──────────────────────────────────────────────────────────────


def add_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("집행 전망 (--전망 지정 시)")
    group.add_argument("--전망", dest="forecast_history", metavar="작년_상세파일", help="작년 원인행위상세목록 엑셀 (이 옵션을 주면 전망 모드로 실행)")
    group.add_argument("--history-sheet", help="작년 파일의 시트 이름")
    group.add_argument("--current-sheet", help="올해 파일(위치 인자 file)의 시트 이름")
    group.add_argument("--기준일", dest="base_date", help="현재 집행 기준일 YYYY-MM-DD (기본: 오늘)")
    group.add_argument("--목표일", dest="target_date", help="전망 목표일 YYYY-MM-DD (기본: 기준일이 속한 분기 말)")
    group.add_argument("--가중치", dest="weight", type=float, default=100.0, help="작년 동기간 증감율에 곱할 가중치(%%). 기본 100")
    group.add_argument("--history-date-column", help="작년 파일의 일자 컬럼 (기본 자동 인식)")
    group.add_argument("--history-amount-column", help="작년 파일의 금액 컬럼 (기본 자동 인식)")
    group.add_argument("--history-item-column", help="작년 파일의 목코드 컬럼 (기본 자동 인식)")
    group.add_argument("--history-subitem-column", help="작년 파일의 세목코드 컬럼 (기본 자동 인식)")
    group.add_argument("--current-item-column", help="올해 파일의 목 컬럼 (기본 자동 인식)")
    group.add_argument("--current-subitem-column", help="올해 파일의 세목 컬럼 (기본 자동 인식)")
    group.add_argument("--current-budget-column", help="올해 파일의 예산 컬럼 (기본 자동 인식)")
    group.add_argument("--current-exec-column", help="올해 파일의 '현재 집행' 컬럼 (기본 자동 인식: '현재' 포함)")
    group.add_argument("--current-target-column", help="올해 파일의 '집행 전망' 컬럼 (기본 자동 인식: '전망' 포함)")


def _parse_date(text: str | None, label: str) -> _dt.date | None:
    if not text:
        return None
    date = to_date(text)
    if date is None:
        raise ForecastError(f"{label} 날짜를 이해하지 못했습니다: '{text}' (예: 2026-08-10)")
    return date


def run_from_args(args: argparse.Namespace) -> int:
    import os
    import sys

    try:
        current = read_table(args.file, sheet=args.current_sheet)
        history = read_table(args.forecast_history, sheet=args.history_sheet)
    except SpreadsheetError as error:
        print(f"오류: {error}", file=sys.stderr)
        return 2

    try:
        base_date = _parse_date(args.base_date, "--기준일") or _dt.date.today()
        target_date = _parse_date(args.target_date, "--목표일") or end_of_quarter(base_date)
        settings = ForecastSettings(base_date=base_date, target_date=target_date, weight_percent=args.weight)

        result = build_forecast(
            history,
            current,
            settings,
            history_date_column=args.history_date_column,
            history_amount_column=args.history_amount_column,
            history_item_column=args.history_item_column,
            history_subitem_column=args.history_subitem_column,
            current_item_column=args.current_item_column,
            current_subitem_column=args.current_subitem_column,
            current_budget_column=args.current_budget_column,
            current_exec_column=args.current_exec_column,
            current_target_column=args.current_target_column,
        )
    except ForecastError as error:
        print(f"오류: {error}", file=sys.stderr)
        return 2

    print(f"기준일 {settings.base_date} → 목표일 {settings.target_date}  (작년 {settings.history_base_date + _dt.timedelta(days=1)} ~ {settings.history_target_date} 패턴 사용)")
    print(f"가중치 {settings.weight_percent:.0f}%")
    print(f"목/세목 매칭: {result.matched_rows}행 매칭, {result.unmatched_rows}행은 전체 평균으로 대체")
    for warning in result.warnings:
        print(f"  · {warning}")

    out = args.xlsx or f"{os.path.splitext(args.file)[0]}_집행전망.xlsx"
    write_forecast(out, result)
    print(f"  집행 전망 엑셀: {os.path.abspath(out)}")
    return 0
