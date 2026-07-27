"""표준 라이브러리만으로 .xlsx / .csv 를 쓴다.

읽기와 마찬가지로 xlsx 는 정해진 XML 몇 장을 zip 으로 묶은 것이라,
필요한 최소 스펙(시트, 숫자 서식, 굵은 머리글)만 직접 만들어 낸다.
"""

from __future__ import annotations

import csv
import datetime as _dt
import zipfile
from typing import Sequence

from .table import Table

__all__ = ["write_xlsx", "write_csv"]


_CONTENT_TYPES_HEAD = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    "</Relationships>"
)

# 0: 기본, 1: 굵게(머리글), 2: #,##0, 3: 0.0%, 4: yyyy-mm-dd
_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0"/></numFmts>'
    '<fonts count="2">'
    '<font><sz val="11"/><name val="맑은 고딕"/></font>'
    '<font><b/><sz val="11"/><name val="맑은 고딕"/></font>'
    "</fonts>"
    '<fills count="3">'
    '<fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FFEDF2F7"/><bgColor indexed="64"/></patternFill></fill>'
    "</fills>"
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="5">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
    '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="10" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="14" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    "</cellXfs>"
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    "</styleSheet>"
)

_HEADER_STYLE = 1
_NUMBER_STYLE = 2
_PERCENT_STYLE = 3
_DATE_STYLE = 4
_EXCEL_EPOCH = _dt.date(1899, 12, 30)

# 엑셀 시트명 제약: 31자 이내, : \ / ? * [ ] 금지.
_INVALID_SHEET_CHARS = str.maketrans({c: "_" for c in ":\\/?*[]"})


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _column_letter(index: int) -> str:
    """0 -> ``A``, 26 -> ``AA``."""
    letters = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _safe_sheet_name(name: str, used: set[str]) -> str:
    clean = (name or "Sheet").translate(_INVALID_SHEET_CHARS).strip("'")[:31] or "Sheet"
    candidate, counter = clean, 2
    while candidate.lower() in used:
        suffix = f"_{counter}"
        candidate = clean[: 31 - len(suffix)] + suffix
        counter += 1
    used.add(candidate.lower())
    return candidate


def _cell_xml(ref: str, value: object, percent_column: bool) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return ""

    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'

    if isinstance(value, (int, float)):
        style = _PERCENT_STYLE if percent_column else _NUMBER_STYLE
        return f'<c r="{ref}" s="{style}"><v>{value!r}</v></c>'

    if isinstance(value, _dt.datetime):
        serial = (value.date() - _EXCEL_EPOCH).days + (
            value.hour * 3600 + value.minute * 60 + value.second
        ) / 86400
        return f'<c r="{ref}" s="{_DATE_STYLE}"><v>{serial!r}</v></c>'

    if isinstance(value, _dt.date):
        serial = (value - _EXCEL_EPOCH).days
        return f'<c r="{ref}" s="{_DATE_STYLE}"><v>{serial}</v></c>'

    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{_escape(str(value))}</t></is></c>'


def _sheet_xml(table: Table) -> str:
    percent_columns = {
        index
        for index, name in enumerate(table.columns)
        if any(token in name for token in ("율", "률", "비율", "구성비", "%"))
    }

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
        'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
    ]

    widths = []
    for index, name in enumerate(table.columns):
        sample = [str(row[index]) for row in table.rows[:200] if row[index] is not None]
        longest = max([len(name)] + [len(s) for s in sample], default=8)
        widths.append(f'<col min="{index + 1}" max="{index + 1}" width="{min(max(longest + 4, 10), 42)}" customWidth="1"/>')
    if widths:
        parts.append("<cols>" + "".join(widths) + "</cols>")

    parts.append("<sheetData>")
    header_cells = "".join(
        f'<c r="{_column_letter(i)}1" s="{_HEADER_STYLE}" t="inlineStr"><is><t>{_escape(str(name))}</t></is></c>'
        for i, name in enumerate(table.columns)
    )
    parts.append(f'<row r="1">{header_cells}</row>')

    for row_number, row in enumerate(table.rows, start=2):
        cells = "".join(
            _cell_xml(f"{_column_letter(i)}{row_number}", value, i in percent_columns)
            for i, value in enumerate(row)
        )
        parts.append(f'<row r="{row_number}">{cells}</row>')

    parts.append("</sheetData>")
    if table.rows:
        last = f"{_column_letter(len(table.columns) - 1)}{len(table.rows) + 1}"
        parts.append(f'<autoFilter ref="A1:{last}"/>')
    parts.append("</worksheet>")
    return "".join(parts)


def write_xlsx(path: str, tables: Sequence[Table]) -> str:
    """표 여러 개를 시트별로 담은 xlsx 를 만든다. 저장 경로를 돌려준다."""
    if not tables:
        raise ValueError("저장할 표가 없습니다.")

    used: set[str] = set()
    names = [_safe_sheet_name(t.name or f"Sheet{i + 1}", used) for i, t in enumerate(tables)]

    content_types = [_CONTENT_TYPES_HEAD]
    workbook_sheets = []
    workbook_rels = []
    for index, name in enumerate(names, start=1):
        content_types.append(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
        workbook_sheets.append(
            f'<sheet name="{_escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        )
        workbook_rels.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    content_types.append("</Types>")

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{"".join(workbook_sheets)}</sheets>'
        "</workbook>"
    )
    styles_rel = (
        f'<Relationship Id="rId{len(names) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(workbook_rels)
        + styles_rel
        + "</Relationships>"
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "".join(content_types))
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", _STYLES)
        for index, table in enumerate(tables, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(table))
    return path


def write_csv(path: str, table: Table) -> str:
    """엑셀에서 한글이 깨지지 않도록 UTF-8 BOM 으로 저장한다."""
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(table.columns)
        writer.writerows(table.rows)
    return path
