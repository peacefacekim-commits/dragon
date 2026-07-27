"""경량 데이터 테이블.

pandas 를 쓸 수 없는 폐쇄망 환경을 전제로, 예산 분석에 필요한 만큼의
표 연산(선택, 필터, 그룹 집계, 정렬)만 표준 라이브러리로 구현한다.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Any, Callable, Iterable, Iterator, Sequence

__all__ = ["Table", "to_number", "to_date", "format_number", "format_percent"]


_NUMBER_JUNK = re.compile(r"[\s, '`]")
_CURRENCY = re.compile(r"[₩$€¥원달러천백만억]")
_PAREN_NEGATIVE = re.compile(r"^\((.*)\)$")


def to_number(value: Any) -> float | None:
    """엑셀 셀 값을 숫자로 해석한다. 실패하면 None.

    ``"1,234,567원"``, ``"(1,200)"`` (회계식 음수), ``"12.5%"`` 처럼
    실무 엑셀에서 흔한 표기를 모두 받아준다.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (_dt.datetime, _dt.date)):
        return None

    text = str(value).strip()
    if not text:
        return None

    percent = text.endswith("%")
    if percent:
        text = text[:-1]

    negative = False
    match = _PAREN_NEGATIVE.match(text)
    if match:
        negative = True
        text = match.group(1)

    text = _CURRENCY.sub("", text)
    text = _NUMBER_JUNK.sub("", text)
    if text in ("", "-", ".", "+"):
        return None

    try:
        number = float(text)
    except ValueError:
        return None

    if negative:
        number = -number
    if percent:
        number = number / 100.0
    return number


_DATE_PATTERNS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y-%m",
    "%Y/%m",
    "%Y.%m",
    "%Y년 %m월 %d일",
    "%Y년 %m월",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%Y%m%d",
)


def to_date(value: Any) -> _dt.date | None:
    """셀 값을 날짜로 해석한다. 실패하면 None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("년", "-").replace("월", "-").replace("일", "")
    normalized = re.sub(r"\s+", "", normalized).rstrip("-")

    for pattern in _DATE_PATTERNS:
        for candidate in (text, normalized):
            try:
                return _dt.datetime.strptime(candidate, pattern).date()
            except ValueError:
                continue

    # "2026-3" 처럼 0 을 뺀 표기.
    match = re.fullmatch(r"(\d{4})[-/.](\d{1,2})(?:[-/.](\d{1,2}))?", normalized)
    if match:
        year, month, day = match.group(1), match.group(2), match.group(3) or "1"
        try:
            return _dt.date(int(year), int(month), int(day))
        except ValueError:
            return None
    return None


def format_number(value: float | None, decimals: int = 0) -> str:
    """천단위 구분 기호를 넣은 문자열. None 은 ``-``."""
    if value is None:
        return "-"
    return f"{value:,.{decimals}f}"


def format_percent(value: float | None, decimals: int = 1) -> str:
    """0.873 -> ``87.3%``. None 은 ``-``."""
    if value is None:
        return "-"
    return f"{value * 100:,.{decimals}f}%"


class Table:
    """헤더가 있는 2차원 표."""

    __slots__ = ("columns", "rows", "name")

    def __init__(
        self,
        columns: Sequence[str],
        rows: Iterable[Sequence[Any]],
        name: str = "",
    ) -> None:
        self.columns: list[str] = [str(c) for c in columns]
        width = len(self.columns)
        normalized: list[list[Any]] = []
        for row in rows:
            row = list(row)
            if len(row) < width:
                row.extend([None] * (width - len(row)))
            elif len(row) > width:
                row = row[:width]
            normalized.append(row)
        self.rows = normalized
        self.name = name

    # ── 기본 조회 ────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        for row in self.rows:
            yield dict(zip(self.columns, row))

    def index_of(self, column: str) -> int:
        try:
            return self.columns.index(column)
        except ValueError:
            raise KeyError(f"'{column}' 컬럼이 없습니다. 사용 가능: {self.columns}") from None

    def column(self, column: str) -> list[Any]:
        idx = self.index_of(column)
        return [row[idx] for row in self.rows]

    def numbers(self, column: str) -> list[float | None]:
        return [to_number(v) for v in self.column(column)]

    def head(self, count: int = 5) -> "Table":
        return Table(self.columns, self.rows[:count], self.name)

    # ── 변형 ────────────────────────────────────────────────────────

    def select(self, columns: Sequence[str]) -> "Table":
        idxs = [self.index_of(c) for c in columns]
        return Table(columns, ([row[i] for i in idxs] for row in self.rows), self.name)

    def filter(self, predicate: Callable[[dict[str, Any]], bool]) -> "Table":
        kept = [row for row, record in zip(self.rows, self) if predicate(record)]
        return Table(self.columns, kept, self.name)

    def with_column(
        self, name: str, values: Callable[[dict[str, Any]], Any] | Sequence[Any]
    ) -> "Table":
        """컬럼을 추가(또는 교체)한 새 표를 만든다."""
        if callable(values):
            computed = [values(record) for record in self]
        else:
            computed = list(values)
            if len(computed) != len(self.rows):
                raise ValueError("값 개수가 행 개수와 다릅니다.")

        if name in self.columns:
            idx = self.index_of(name)
            rows = [row[:idx] + [value] + row[idx + 1 :] for row, value in zip(self.rows, computed)]
            return Table(self.columns, rows, self.name)

        rows = [row + [value] for row, value in zip(self.rows, computed)]
        return Table(self.columns + [name], rows, self.name)

    def sort_by(self, column: str, descending: bool = True) -> "Table":
        """숫자 행을 먼저 정렬하고, 숫자로 읽히지 않는 행은 언제나 뒤에 붙인다.

        정렬 방향을 뒤집어도 '미정' 같은 값이 맨 위로 올라오면 안 되므로
        두 무리를 나눠서 정렬한다.
        """
        idx = self.index_of(column)

        numeric: list[tuple[float, Sequence[Any]]] = []
        textual: list[tuple[str, Sequence[Any]]] = []
        for row in self.rows:
            number = to_number(row[idx])
            if number is None:
                textual.append(("" if row[idx] is None else str(row[idx]), row))
            else:
                numeric.append((number, row))

        numeric.sort(key=lambda pair: pair[0], reverse=descending)
        textual.sort(key=lambda pair: pair[0])
        rows = [row for _, row in numeric] + [row for _, row in textual]
        return Table(self.columns, rows, self.name)

    def drop_empty_rows(self) -> "Table":
        rows = [
            row
            for row in self.rows
            if any(cell is not None and str(cell).strip() != "" for cell in row)
        ]
        return Table(self.columns, rows, self.name)

    # ── 집계 ────────────────────────────────────────────────────────

    def group_sum(
        self,
        by: str,
        measures: Sequence[str],
        empty_label: str = "(미지정)",
    ) -> "Table":
        """``by`` 기준으로 ``measures`` 합계와 건수를 낸다. 등장 순서를 유지한다."""
        by_idx = self.index_of(by)
        measure_idxs = [self.index_of(m) for m in measures]

        totals: dict[str, list[float]] = {}
        counts: dict[str, int] = {}
        for row in self.rows:
            raw = row[by_idx]
            key = empty_label if raw is None or str(raw).strip() == "" else str(raw).strip()
            bucket = totals.setdefault(key, [0.0] * len(measure_idxs))
            counts[key] = counts.get(key, 0) + 1
            for position, idx in enumerate(measure_idxs):
                number = to_number(row[idx])
                if number is not None:
                    bucket[position] += number

        columns = [by] + list(measures) + ["건수"]
        rows = [[key] + totals[key] + [counts[key]] for key in totals]
        return Table(columns, rows, self.name)

    def total(self, column: str) -> float:
        return sum(n for n in self.numbers(column) if n is not None)

    def add_share(self, value_column: str, share_column: str = "구성비") -> "Table":
        """``value_column`` 이 전체 합계에서 차지하는 비율 컬럼을 붙인다."""
        grand_total = self.total(value_column)
        idx = self.index_of(value_column)

        def share(row_number: int) -> float | None:
            if not grand_total:
                return None
            number = to_number(self.rows[row_number][idx])
            return None if number is None else number / grand_total

        return self.with_column(share_column, [share(i) for i in range(len(self.rows))])
