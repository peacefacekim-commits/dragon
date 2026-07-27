"""폐쇄망용 엑셀 예산 분석기.

파이썬 표준 라이브러리만 사용한다. pandas / openpyxl / matplotlib 없이
엑셀을 읽고, 분석하고, 차트가 포함된 HTML 보고서와 엑셀 결과를 만든다.

    from budget_analyzer import read_table, guess_mapping, analyze, write_report

    table = read_table("예산.xlsx")
    result = analyze(table, guess_mapping(table), source="예산.xlsx")
    write_report("보고서.html", result)
"""

from .analysis import AnalysisResult, analyze
from .mapping import ColumnMapping, guess_mapping, load_profile, save_profile
from .report import render_report, write_report
from .table import Table, format_number, format_percent, to_date, to_number
from .xlsx_reader import SpreadsheetError, read_table, read_workbook, sheet_names
from .xlsx_writer import write_csv, write_xlsx

__version__ = "1.0.0"

__all__ = [
    "AnalysisResult",
    "ColumnMapping",
    "SpreadsheetError",
    "Table",
    "analyze",
    "format_number",
    "format_percent",
    "guess_mapping",
    "load_profile",
    "read_table",
    "read_workbook",
    "render_report",
    "save_profile",
    "sheet_names",
    "to_date",
    "to_number",
    "write_csv",
    "write_report",
    "write_xlsx",
]
