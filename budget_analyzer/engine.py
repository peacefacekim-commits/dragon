"""양식 실행 엔진.

:mod:`template` 이 "무엇을 분석할지" 라면 여기는 "그대로 실행하는 곳" 이다.
분석 종류가 코드에 박혀 있지 않으므로, 새로운 분석은 양식만 바꾸면 된다.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Sequence

from . import expression
from .expression import ExpressionError
from .mapping import ColumnMapping
from .table import Table, to_date, to_number
from .template import Block, Template, template_from_mapping

__all__ = ["Report", "BlockResult", "Tile", "run", "analyze", "period_key"]


@dataclass
class Tile:
    """보고서 맨 위의 숫자 하나."""

    이름: str
    값: Any
    서식: str = "자동"
    설명: str = ""


@dataclass
class BlockResult:
    """블록 하나의 실행 결과."""

    이름: str
    설명: str
    유형: str
    표: Table
    차트: str = "없음"
    차트값: str = ""
    기준이름: list[str] = field(default_factory=list)
    측정값이름: list[str] = field(default_factory=list)
    합산가능: list[str] = field(default_factory=list)
    서식: dict[str, str] = field(default_factory=dict)
    경고: list[str] = field(default_factory=list)
    합계표시: bool = True


@dataclass
class Report:
    """양식 하나를 실행한 전체 결과."""

    template: Template
    source: str = ""
    sheet: str = ""
    row_count: int = 0
    analyzed_count: int = 0
    tiles: list[Tile] = field(default_factory=list)
    blocks: list[BlockResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: _dt.datetime = field(default_factory=_dt.datetime.now)

    def tables(self) -> list[Table]:
        """내보내기용 표 목록."""
        return [block.표 for block in self.blocks if len(block.표)]


# ── 기간 키 ────────────────────────────────────────────────────────


def period_key(value: object, grain: str = "월") -> str | None:
    """날짜/기간 값을 정렬 가능한 문자열 키로 바꾼다."""
    date = to_date(value)
    if date is not None:
        if grain == "연도":
            return f"{date.year}"
        if grain == "분기":
            return f"{date.year}-Q{(date.month - 1) // 3 + 1}"
        return f"{date.year}-{date.month:02d}"

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    # 연도 없이 "3월", "2분기", "1Q" 로만 적힌 컬럼도 받아준다.
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


# ── 내부 도우미 ────────────────────────────────────────────────────


def _apply_filter(table: Table, filter_text: str, where: str, warnings: list[str]) -> Table:
    if not filter_text.strip():
        return table
    try:
        keep = expression.evaluate(filter_text, table)
    except ExpressionError as error:
        warnings.append(f"{where} 필터를 적용하지 못했습니다: {error}")
        return table

    rows = [row for row, flag in zip(table.rows, keep) if expression.truthy(flag)]
    removed = len(table) - len(rows)
    if removed:
        warnings.append(f"{where} 필터로 {removed:,}행을 제외했습니다.")
    return Table(table.columns, rows, table.name)


def _add_computed(
    table: Table, computed: Sequence[Any], where: str, warnings: list[str]
) -> tuple[Table, dict[str, str]]:
    """수식 컬럼을 차례로 붙인다. 앞에서 만든 컬럼을 뒤에서 쓸 수 있다."""
    formats: dict[str, str] = {}
    for item in computed:
        if not item.이름:
            continue
        try:
            values = expression.evaluate(item.식, table)
        except ExpressionError as error:
            warnings.append(f"{where} '{item.이름}' 을(를) 계산하지 못했습니다: {error}")
            continue
        table = table.with_column(item.이름, values)
        formats[item.이름] = item.서식
    return table, formats


def _group_indices(table: Table, keys: Sequence[str]) -> list[tuple[list[str], list[int]]]:
    """기준 컬럼 조합별로 행 번호를 모은다. 처음 등장한 순서를 유지한다."""
    indices = [table.index_of(key) for key in keys]
    buckets: dict[tuple[str, ...], list[int]] = {}
    labels: dict[tuple[str, ...], list[str]] = {}

    for position, row in enumerate(table.rows):
        parts = []
        for index in indices:
            raw = row[index]
            parts.append("(미지정)" if raw is None or str(raw).strip() == "" else str(raw).strip())
        key = tuple(parts)
        buckets.setdefault(key, []).append(position)
        labels.setdefault(key, parts)

    return [(labels[key], members) for key, members in buckets.items()]


def _aggregate(
    table: Table, measures: Sequence[Any], members: Sequence[int]
) -> list[Any]:
    """한 그룹에 대해 측정값들을 계산한다."""
    values: list[Any] = []
    for measure in measures:
        try:
            index = table.index_of(measure.컬럼)
        except KeyError:
            values.append(None)
            continue
        column = [table.rows[i][index] for i in members]
        function = expression.AGGREGATORS.get(measure.함수, expression.AGGREGATORS["합계"])
        values.append(function(column))
    return values


def _build_grouped_table(
    table: Table,
    key_columns: Sequence[str],
    groups: Sequence[tuple[list[str], list[int]]],
    measures: Sequence[Any],
    name: str,
) -> Table:
    columns = list(key_columns) + [m.결과이름 for m in measures] + ["건수"]
    rows = [
        list(labels) + _aggregate(table, measures, members) + [len(members)]
        for labels, members in groups
    ]
    return Table(columns, rows, name)


def _fold_tail(
    groups: list[tuple[list[str], list[int]]], top: int, key_count: int
) -> tuple[list[tuple[list[str], list[int]]], str | None]:
    """상위 N개만 남기고 나머지를 '기타' 한 줄로 합친다.

    합계를 더하는 대신 남은 원본 행을 통째로 다시 집계하므로, 평균·고유건수
    처럼 단순 합산이 불가능한 함수도 정확하게 나온다.
    """
    if not top or len(groups) <= top:
        return groups, None

    head, tail = groups[:top], groups[top:]
    merged: list[int] = []
    for _, members in tail:
        merged.extend(members)
    label = [f"기타 ({len(tail)}개 항목)"] + [""] * (key_count - 1)
    return head + [(label, merged)], f"항목이 많아 상위 {top}개만 표시하고 나머지는 '기타'로 묶었습니다."


def _summable(block: Block, formats: dict[str, str]) -> list[str]:
    """열 합계를 내도 뜻이 통하는 컬럼만 고른다.

    평균·최대·중앙값을 세로로 더하면 아무 의미가 없다. 합계·건수로 집계한
    측정값과, 금액·정수 서식의 계산 컬럼만 더한다.
    """
    columns = ["건수"]
    columns += [m.결과이름 for m in block.측정값 if m.함수 in ("합계", "건수")]
    columns += [c.이름 for c in block.계산 if formats.get(c.이름) in ("금액", "정수")]
    return columns


def _apply_rules(table: Table, rules: Sequence[Any], where: str) -> list[str]:
    messages: list[str] = []
    for rule in rules:
        if not rule.조건.strip():
            continue
        try:
            flags = expression.evaluate(rule.조건, table)
        except ExpressionError as error:
            messages.append(f"{where} 규칙을 확인하지 못했습니다: {error}")
            continue

        matched = [row for row, flag in zip(table.rows, flags) if expression.truthy(flag)]
        if not matched:
            continue
        first = str(matched[0][0]) if matched[0] else ""
        messages.append(rule.메시지.replace("{건수}", str(len(matched))).replace("{항목}", first))
    return messages


def _chart_kind(block: Block) -> str:
    if block.차트 != "자동":
        return block.차트
    return {"집계": "막대", "추이": "선", "목록": "없음"}[block.유형]


# ── 블록 실행 ──────────────────────────────────────────────────────


def _run_list_block(block: Block, table: Table, warnings: list[str]) -> BlockResult:
    """원본 행을 그대로 보여주는 블록."""
    columns = [c for c in block.기준 if c in table.columns] or list(table.columns)
    result = table.select(columns)

    result, formats = _add_computed(result, block.계산, f"블록 '{block.이름}'", warnings)
    if block.정렬 and block.정렬 in result.columns:
        result = result.sort_by(block.정렬, block.내림차순)
    if block.상위:
        result = Table(result.columns, result.rows[: block.상위], result.name)
    result.name = block.이름

    return BlockResult(
        이름=block.이름,
        설명=block.설명,
        유형=block.유형,
        표=result,
        차트="없음",
        기준이름=list(columns),
        서식=formats,
        경고=_apply_rules(result, block.규칙, f"블록 '{block.이름}'"),
        합계표시=False,
    )


def _run_trend_block(block: Block, table: Table, warnings: list[str]) -> BlockResult:
    """날짜/기간 컬럼을 기간 단위로 묶는 블록."""
    where = f"블록 '{block.이름}'"
    date_column = block.기준[0]
    if date_column not in table.columns:
        warnings.append(f"{where}: '{date_column}' 컬럼이 없어 건너뜁니다.")
        return BlockResult(block.이름, block.설명, block.유형, Table(["기간"], []), "없음")

    keyed = table.with_column(
        "__기간__", [period_key(value, block.단위) for value in table.column(date_column)]
    )
    unparsed = sum(1 for value in keyed.column("__기간__") if value is None)
    if unparsed:
        warnings.append(
            f"{where}: '{date_column}' 값 중 {unparsed:,}건은 기간으로 해석하지 못해 제외했습니다."
        )
    keyed = keyed.filter(lambda record: record["__기간__"] is not None)
    if not len(keyed):
        warnings.append(f"{where}: 유효한 기간을 찾지 못했습니다.")
        return BlockResult(block.이름, block.설명, block.유형, Table(["기간"], []), "없음")

    groups = sorted(_group_indices(keyed, ["__기간__"]), key=lambda item: item[0][0])
    key_columns = ["기간"]
    result = _build_grouped_table(keyed, key_columns, groups, block.측정값, block.이름)

    formats = {m.결과이름: m.서식 for m in block.측정값}
    result, computed_formats = _add_computed(result, block.계산, where, warnings)
    formats.update(computed_formats)

    return BlockResult(
        이름=block.이름,
        설명=block.설명,
        유형=block.유형,
        표=result,
        차트=_chart_kind(block),
        차트값=block.차트값,
        기준이름=list(key_columns),
        측정값이름=[m.결과이름 for m in block.측정값],
        합산가능=_summable(block, formats),
        서식=formats,
        경고=_apply_rules(result, block.규칙, where),
        합계표시=False,
    )


def _run_group_block(block: Block, table: Table, warnings: list[str]) -> BlockResult:
    """기준 컬럼으로 묶어 집계하는 블록."""
    where = f"블록 '{block.이름}'"
    keys = [column for column in block.기준 if column in table.columns]
    missing = [column for column in block.기준 if column not in table.columns]
    if missing:
        warnings.append(f"{where}: '{', '.join(missing)}' 컬럼이 없어 기준에서 제외했습니다.")
    if not keys:
        warnings.append(f"{where}: 묶을 기준 컬럼이 없어 건너뜁니다.")
        return BlockResult(block.이름, block.설명, block.유형, Table(["항목"], []), "없음")

    groups = _group_indices(table, keys)

    # 정렬 기준이 측정값이면 '기타' 로 묶기 전에 정렬해야 상위 N개가 맞는다.
    sort_column = block.정렬 or (block.측정값[0].결과이름 if block.측정값 else "")
    if sort_column:
        preview = _build_grouped_table(table, keys, groups, block.측정값, block.이름)
        if sort_column in preview.columns:
            index = preview.index_of(sort_column)
            order = sorted(
                range(len(groups)),
                key=lambda position: (
                    to_number(preview.rows[position][index]) is None,
                    -(to_number(preview.rows[position][index]) or 0.0)
                    if block.내림차순
                    else (to_number(preview.rows[position][index]) or 0.0),
                    str(preview.rows[position][index]),
                ),
            )
            groups = [groups[position] for position in order]
        else:
            warnings.append(f"{where}: 정렬 기준 '{sort_column}' 을 찾지 못해 원래 순서를 씁니다.")

    groups, folded = _fold_tail(list(groups), block.상위 if block.기타로묶기 else 0, len(keys))
    if folded:
        warnings.append(f"{where}: {folded}")
    elif block.상위 and not block.기타로묶기:
        groups = groups[: block.상위]

    key_columns = list(keys)
    result = _build_grouped_table(table, keys, groups, block.측정값, block.이름)

    formats = {m.결과이름: m.서식 for m in block.측정값}
    result, computed_formats = _add_computed(result, block.계산, where, warnings)
    formats.update(computed_formats)

    return BlockResult(
        이름=block.이름,
        설명=block.설명,
        유형=block.유형,
        표=result,
        차트=_chart_kind(block),
        차트값=block.차트값,
        기준이름=list(key_columns),
        측정값이름=[m.결과이름 for m in block.측정값],
        합산가능=_summable(block, formats),
        서식=formats,
        경고=_apply_rules(result, block.규칙, where),
    )


# ── 진입점 ─────────────────────────────────────────────────────────


def run(table: Table, template: Template, source: str = "") -> Report:
    """양식을 표에 적용해 보고서 결과를 만든다.

    블록 하나가 실패해도 나머지는 계속 진행하고, 무엇이 왜 빠졌는지는
    ``warnings`` 에 남긴다.
    """
    report = Report(
        template=template,
        source=source,
        sheet=table.name,
        row_count=len(table),
    )

    working = _apply_filter(table, template.전체필터, "전체", report.warnings)
    working, _ = _add_computed(working, template.파생컬럼, "파생컬럼", report.warnings)
    report.analyzed_count = len(working)

    for summary in template.요약:
        try:
            value = expression.evaluate_scalar(summary.식, working)
        except ExpressionError as error:
            report.warnings.append(f"요약 '{summary.이름}' 을(를) 계산하지 못했습니다: {error}")
            continue
        report.tiles.append(Tile(summary.이름, value, summary.서식, summary.설명))

    for block in template.블록:
        scoped = _apply_filter(working, block.필터, f"블록 '{block.이름}'", report.warnings)
        try:
            if block.유형 == "목록":
                result = _run_list_block(block, scoped, report.warnings)
            elif block.유형 == "추이":
                result = _run_trend_block(block, scoped, report.warnings)
            else:
                result = _run_group_block(block, scoped, report.warnings)
        except (KeyError, ValueError) as error:
            report.warnings.append(f"블록 '{block.이름}' 실행 실패: {error}")
            continue
        report.blocks.append(result)

    return report


def analyze(
    table: Table,
    mapping: ColumnMapping | None = None,
    source: str = "",
    template: Template | None = None,
) -> Report:
    """양식 없이 부를 때의 간편 진입점.

    양식을 주지 않으면 자동 인식된 컬럼으로 기본 양식을 만들어 실행한다.
    """
    if template is None:
        from .mapping import guess_mapping

        template = template_from_mapping(mapping or guess_mapping(table))
    return run(table, template, source=source)
