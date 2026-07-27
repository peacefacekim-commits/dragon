"""폐쇄망용 엑셀 예산 분석기.

파이썬 표준 라이브러리만 사용한다. pandas / openpyxl / matplotlib 없이
엑셀을 읽고, 분석하고, 차트가 포함된 HTML 보고서와 엑셀 결과를 만든다.

무엇을 어떻게 분석할지는 코드가 아니라 **분석 양식**(JSON) 에 적는다.
새로운 분석이 필요하면 코드를 고치는 대신 양식을 만들거나 고치면 된다.

    from budget_analyzer import read_table, guess_mapping, template_from_mapping, run, write_report

    table = read_table("예산.xlsx")
    양식 = template_from_mapping(guess_mapping(table))   # 또는 load_template("우리양식.json")
    보고서 = run(table, 양식, source="예산.xlsx")
    write_report("보고서.html", 보고서)
"""

from .engine import BlockResult, Report, Tile, analyze, run
from .expression import ExpressionError, evaluate, evaluate_scalar
from .mapping import ColumnMapping, guess_mapping, load_profile, save_profile
from .report import render_report, write_report
from .table import Table, format_number, format_percent, to_date, to_number
from .template import (
    Block,
    Computed,
    Measure,
    Rule,
    Summary,
    Template,
    TemplateError,
    builtin_templates,
    load_template,
    save_template,
    template_from_mapping,
)
from .xlsx_reader import SpreadsheetError, read_table, read_workbook, sheet_names
from .xlsx_writer import write_csv, write_xlsx

__version__ = "2.0.0"

__all__ = [
    "Block",
    "BlockResult",
    "ColumnMapping",
    "Computed",
    "ExpressionError",
    "Measure",
    "Report",
    "Rule",
    "SpreadsheetError",
    "Summary",
    "Table",
    "Template",
    "TemplateError",
    "Tile",
    "analyze",
    "builtin_templates",
    "evaluate",
    "evaluate_scalar",
    "format_number",
    "format_percent",
    "guess_mapping",
    "load_profile",
    "load_template",
    "read_table",
    "read_workbook",
    "render_report",
    "run",
    "save_profile",
    "save_template",
    "sheet_names",
    "template_from_mapping",
    "to_date",
    "to_number",
    "write_csv",
    "write_report",
    "write_xlsx",
]
