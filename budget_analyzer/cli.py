"""명령줄 인터페이스."""

from __future__ import annotations

import argparse
import os
import sys

from .analysis import analyze
from .mapping import ColumnMapping, guess_mapping, load_profile, save_profile
from .report import write_report
from .table import format_number, format_percent
from .xlsx_reader import SpreadsheetError, read_table, sheet_names
from .xlsx_writer import write_csv, write_xlsx

__all__ = ["main"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="budget_analyzer",
        description="엑셀 예산 파일을 읽어 항목별 집계·집행률·기간별 추이를 분석합니다. "
        "외부 패키지가 필요 없습니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "예시:\n"
            "  python -m budget_analyzer 예산.xlsx\n"
            "  python -m budget_analyzer 예산.xlsx --sheet 집행내역 --grain quarter\n"
            "  python -m budget_analyzer 예산.xlsx --category 부서 --budget 예산액 --actual 집행액\n"
            "  python -m budget_analyzer 예산.xlsx --save-profile 표준양식.json\n"
            "  python -m budget_analyzer --gui\n"
        ),
    )
    parser.add_argument("file", nargs="?", help="분석할 .xlsx / .csv 파일")
    parser.add_argument("--gui", action="store_true", help="창(GUI) 모드로 실행")
    parser.add_argument("--sheet", help="시트 이름 (기본: 데이터가 가장 많은 시트)")
    parser.add_argument("--list-sheets", action="store_true", help="시트 목록만 출력")
    parser.add_argument("--header-row", type=int, help="머리글 행 번호 (1부터). 기본은 자동 인식")

    columns = parser.add_argument_group("컬럼 지정 (생략하면 자동 인식)")
    columns.add_argument("--category", help="분류 기준 컬럼 (예: 부서, 계정과목)")
    columns.add_argument("--budget", help="예산액 컬럼")
    columns.add_argument("--actual", help="집행액 컬럼")
    columns.add_argument("--amount", help="단일 금액 컬럼")
    columns.add_argument("--date", dest="date_column", help="일자/기간 컬럼")

    output = parser.add_argument_group("출력")
    output.add_argument("-o", "--out", help="HTML 보고서 경로 (기본: <입력파일>_분석.html)")
    output.add_argument("--xlsx", help="분석 결과를 엑셀로도 저장할 경로")
    output.add_argument("--csv-dir", help="표별 CSV 를 저장할 폴더")
    output.add_argument("--no-report", action="store_true", help="HTML 보고서를 만들지 않음")
    output.add_argument(
        "--grain",
        choices=("month", "quarter", "year"),
        default="month",
        help="추이 집계 단위 (기본: month)",
    )
    output.add_argument("--top", type=int, default=15, help="개별 표시할 상위 항목 수 (기본: 15)")

    profile = parser.add_argument_group("매핑 프로파일")
    profile.add_argument("--profile", help="저장해 둔 컬럼 매핑 JSON 을 불러옴")
    profile.add_argument("--save-profile", help="이번에 쓴 컬럼 매핑을 JSON 으로 저장")
    return parser


def _resolve_mapping(table, args: argparse.Namespace) -> ColumnMapping:
    """자동 인식 → 프로파일 → 명령줄 인자 순으로 덮어쓴다."""
    mapping = load_profile(args.profile) if args.profile else guess_mapping(table)

    overrides = {
        "category": args.category,
        "budget": args.budget,
        "actual": args.actual,
        "amount": args.amount,
        "date": args.date_column,
    }
    for field, value in overrides.items():
        if value:
            if value not in table.columns:
                raise SystemExit(
                    f"오류: '{value}' 컬럼이 없습니다.\n사용 가능한 컬럼: {', '.join(table.columns)}"
                )
            setattr(mapping, field, value)

    # 프로파일이 지금 파일과 안 맞으면 없는 컬럼을 조용히 버린다.
    for field in ("category", "budget", "actual", "amount", "date"):
        if getattr(mapping, field) and getattr(mapping, field) not in table.columns:
            setattr(mapping, field, None)
    return mapping


def _print_summary(result) -> None:
    print(f"\n{'=' * 58}")
    print(f"  분석 완료: {result.sheet} ({result.row_count:,}행)")
    print(f"{'=' * 58}")
    print(f"  인식된 컬럼: {result.mapping.describe()}")

    for label, value in result.totals.items():
        print(f"  총 {label}: {format_number(value)} 원")
    rate = result.execution_rate
    if rate is not None:
        budget = result.totals.get("예산액", 0.0)
        actual = result.totals.get("집행액", 0.0)
        print(f"  전체 집행률: {format_percent(rate)}  (잔액 {format_number(budget - actual)} 원)")

    if result.breakdown is not None and len(result.breakdown):
        value_column = result.mapping.value_column
        print(f"\n  [상위 항목] {result.mapping.category}별 {value_column}")
        index = result.breakdown.index_of(value_column)
        share_index = result.breakdown.index_of("구성비")
        for row in result.breakdown.rows[:5]:
            share = row[share_index]
            print(
                f"    - {str(row[0])[:24]:<24} {format_number(row[index]):>16}"
                f"  ({format_percent(share) if share is not None else '-'})"
            )

    if result.warnings:
        print("\n  [확인 필요]")
        for warning in result.warnings:
            print(f"    · {warning}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.gui or (args.file is None and not args.list_sheets):
        from .gui import launch

        return launch(args.file)

    if not args.file:
        parser.error("분석할 파일을 지정하거나 --gui 를 사용하세요.")

    if not os.path.exists(args.file):
        print(f"오류: '{args.file}' 파일을 찾을 수 없습니다.", file=sys.stderr)
        return 2

    try:
        if args.list_sheets:
            for name in sheet_names(args.file):
                print(name)
            return 0

        header_row = None if args.header_row is None else max(args.header_row - 1, 0)
        table = read_table(args.file, sheet=args.sheet, header_row=header_row)
    except SpreadsheetError as error:
        print(f"오류: {error}", file=sys.stderr)
        return 2

    print(f"읽은 컬럼 ({len(table.columns)}개): {', '.join(table.columns)}")

    mapping = _resolve_mapping(table, args)
    result = analyze(table, mapping, source=args.file, top_n=args.top, grain=args.grain)
    _print_summary(result)

    base = os.path.splitext(args.file)[0]
    if not args.no_report:
        out = args.out or f"{base}_분석.html"
        write_report(out, result, title=f"예산 분석 보고서 — {os.path.basename(args.file)}")
        print(f"  HTML 보고서: {os.path.abspath(out)}")

    tables = result.tables()
    if args.xlsx:
        if tables:
            write_xlsx(args.xlsx, tables)
            print(f"  엑셀 결과:   {os.path.abspath(args.xlsx)}")
        else:
            print("  엑셀 결과:   분석 표가 비어 있어 저장하지 않았습니다.", file=sys.stderr)

    if args.csv_dir:
        os.makedirs(args.csv_dir, exist_ok=True)
        for table_out in tables:
            path = os.path.join(args.csv_dir, f"{table_out.name or 'sheet'}.csv")
            write_csv(path, table_out)
            print(f"  CSV:         {os.path.abspath(path)}")

    if args.save_profile:
        save_profile(args.save_profile, mapping)
        print(f"  매핑 프로파일: {os.path.abspath(args.save_profile)}")

    return 0
