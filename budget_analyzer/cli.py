"""명령줄 인터페이스."""

from __future__ import annotations

import argparse
import os
import sys

from . import expression
from . import forecast as forecast_module
from .engine import run
from .mapping import ColumnMapping, guess_mapping, load_profile, save_profile
from .report import write_report
from .table import format_number, format_percent, to_number
from .template import (
    Template,
    TemplateError,
    builtin_templates,
    load_template,
    save_template,
    template_from_mapping,
)
from .xlsx_reader import SpreadsheetError, read_table, sheet_names
from .xlsx_writer import write_csv, write_xlsx

__all__ = ["main"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="budget_analyzer",
        description="엑셀 파일을 '분석 양식'에 따라 분석합니다. 양식은 JSON 파일 하나이며, "
        "새로운 분석이 필요하면 코드를 고치는 대신 양식을 만들거나 고치면 됩니다. "
        "외부 패키지가 필요 없습니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "예시:\n"
            "  python -m budget_analyzer 예산.xlsx\n"
            "      양식 없이 실행 — 컬럼을 자동 인식해 기본 양식으로 분석\n\n"
            "  python -m budget_analyzer 예산.xlsx --save-template 우리양식.json\n"
            "      자동 생성된 양식을 파일로 저장 (이걸 열어 고치면 내 양식이 됩니다)\n\n"
            "  python -m budget_analyzer 예산.xlsx --template 우리양식.json\n"
            "      내 양식으로 분석\n\n"
            "  python -m budget_analyzer 예산.xlsx --check-template 우리양식.json\n"
            "      양식이 이 파일에 맞는지 검사만\n\n"
            "  python -m budget_analyzer --함수목록\n"
            "      양식 수식에서 쓸 수 있는 함수 보기\n\n"
            "  python -m budget_analyzer 올해_현황.xlsx --전망 작년_상세.xlsx --xlsx 집행전망.xlsx\n"
            "      작년 같은 기간의 지출 패턴으로 집행 전망 계산 (엑셀의 '가중치' 셀로 조절)\n\n"
            "  python -m budget_analyzer --gui\n"
        ),
    )
    parser.add_argument("file", nargs="?", help="분석할 .xlsx / .csv 파일")
    parser.add_argument("--gui", action="store_true", help="창(GUI) 모드로 실행")
    parser.add_argument("--sheet", help="시트 이름 (기본: 데이터가 가장 많은 시트)")
    parser.add_argument("--list-sheets", action="store_true", help="시트 목록만 출력")
    parser.add_argument("--header-row", type=int, help="머리글 행 번호 (1부터). 기본은 자동 인식")
    parser.add_argument(
        "--함수목록",
        "--functions",
        dest="functions",
        action="store_true",
        help="양식 수식에서 쓸 수 있는 함수 목록",
    )

    templates = parser.add_argument_group("분석 양식")
    templates.add_argument("-t", "--template", help="사용할 양식 JSON 파일")
    templates.add_argument("--save-template", help="지금 쓴 양식을 JSON 으로 저장")
    templates.add_argument("--check-template", help="양식이 이 파일에 맞는지 검사만 하고 종료")
    templates.add_argument(
        "--예시양식",
        "--list-templates",
        dest="list_templates",
        action="store_true",
        help="이 파일에 맞춰 만들어 볼 수 있는 예시 양식 목록",
    )
    templates.add_argument(
        "--예시",
        "--preset",
        dest="preset",
        help="예시 양식 이름 또는 번호로 실행 (--예시양식 으로 목록 확인)",
    )

    columns = parser.add_argument_group("컬럼 지정 (양식을 자동 생성할 때 쓰임)")
    columns.add_argument("--category", help="분류 기준 컬럼 (예: 부서, 계정과목)")
    columns.add_argument("--budget", help="예산액 컬럼")
    columns.add_argument("--actual", help="집행액 컬럼")
    columns.add_argument("--amount", help="단일 금액 컬럼")
    columns.add_argument("--date", dest="date_column", help="일자/기간 컬럼")
    columns.add_argument("--profile", help="저장해 둔 컬럼 매핑 JSON 을 불러옴")
    columns.add_argument("--save-profile", help="이번에 쓴 컬럼 매핑을 JSON 으로 저장")

    output = parser.add_argument_group("출력")
    output.add_argument("-o", "--out", help="HTML 보고서 경로 (기본: <입력파일>_분석.html)")
    output.add_argument("--xlsx", help="분석 결과를 엑셀로도 저장할 경로")
    output.add_argument("--csv-dir", help="표별 CSV 를 저장할 폴더")
    output.add_argument("--no-report", action="store_true", help="HTML 보고서를 만들지 않음")

    forecast_module.add_arguments(parser)
    return parser


def _print_functions() -> int:
    print("\n양식의 수식에서 쓸 수 있는 함수\n" + "=" * 62)
    print("  컬럼은 [컬럼명] 처럼 대괄호로 감쌉니다.  예: [집행액] / [예산액]\n")
    groups = {"행": "행마다 계산", "전체": "열 전체를 값 하나로", "누적": "열 전체를 열 전체로"}
    for group, title in groups.items():
        print(f"  [{title}]")
        for name, kind, example in expression.FUNCTION_HELP:
            if kind == group:
                print(f"    {name:<26} 예) {example}")
        print()
    print("  연산자: + - * / % **  ==  !=  <  <=  >  >=  and  or  not  &  |")
    print("  문자열은 큰따옴표로 감쌉니다.  예: [구분] == \"정기\"\n")
    return 0


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


def _resolve_template(table, mapping: ColumnMapping, args: argparse.Namespace) -> Template:
    if args.template:
        return load_template(args.template)

    presets = builtin_templates(mapping)
    if args.preset:
        if args.preset.isdigit():
            index = int(args.preset) - 1
            if not 0 <= index < len(presets):
                raise SystemExit(f"오류: 예시 양식 번호는 1~{len(presets)} 사이여야 합니다.")
            return presets[index]
        for preset in presets:
            if preset.이름 == args.preset:
                return preset
        raise SystemExit(
            f"오류: '{args.preset}' 예시 양식이 없습니다. "
            f"사용 가능: {', '.join(p.이름 for p in presets)}"
        )
    return template_from_mapping(mapping)


def _print_summary(report) -> None:
    print(f"\n{'=' * 62}")
    print(f"  {report.template.이름} — {report.sheet} ({report.row_count:,}행)")
    print(f"{'=' * 62}")

    for tile in report.tiles:
        number = to_number(tile.값)
        if number is None:
            text = "-" if tile.값 is None else str(tile.값)
        elif tile.서식 == "비율":
            text = format_percent(number)
        else:
            text = format_number(number)
        unit = f" {tile.설명}" if tile.설명 and len(tile.설명) <= 3 else ""
        print(f"  {tile.이름}: {text}{unit}")

    for block in report.blocks:
        table = block.표
        if not len(table):
            continue
        value_column = block.차트값 or (block.측정값이름[0] if block.측정값이름 else "")
        if value_column not in table.columns:
            continue
        print(f"\n  [{block.이름}]")
        index = table.index_of(value_column)
        key_count = max(1, len(block.기준이름))
        for row in table.rows[:5]:
            label = " · ".join(str(cell) for cell in row[:key_count] if str(cell).strip())
            number = to_number(row[index])
            shown = format_percent(number) if block.서식.get(value_column) == "비율" else format_number(number)
            print(f"    - {label[:30]:<30} {shown:>16}")
        for warning in block.경고:
            print(f"    ! {warning}")

    if report.warnings:
        print("\n  [확인 필요]")
        for warning in report.warnings:
            print(f"    · {warning}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.functions:
        return _print_functions()

    if args.gui or (args.file is None and not args.list_sheets):
        from .gui import launch

        return launch(args.file)

    if not args.file:
        parser.error("분석할 파일을 지정하거나 --gui 를 사용하세요.")

    if not os.path.exists(args.file):
        print(f"오류: '{args.file}' 파일을 찾을 수 없습니다.", file=sys.stderr)
        return 2

    if args.forecast_history:
        if not os.path.exists(args.forecast_history):
            print(f"오류: '{args.forecast_history}' 파일을 찾을 수 없습니다.", file=sys.stderr)
            return 2
        return forecast_module.run_from_args(args)

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

    if args.list_templates:
        print("\n이 파일에 맞춰 만들 수 있는 예시 양식:")
        for number, preset in enumerate(builtin_templates(mapping), start=1):
            print(f"  {number}. {preset.이름} — {preset.설명}")
            for block in preset.블록:
                print(f"       · {block.이름} ({block.유형})")
        print("\n  --예시 <번호> 로 실행하거나, --save-template 로 저장해 고쳐 쓰세요.\n")
        return 0

    if args.check_template:
        try:
            template = load_template(args.check_template)
        except (TemplateError, OSError) as error:
            print(f"오류: {error}", file=sys.stderr)
            return 2
        problems = template.validate(table.columns)
        if problems:
            print(f"\n'{template.이름}' 양식에서 {len(problems)}건의 문제를 찾았습니다:")
            for problem in problems:
                print(f"  · {problem}")
            return 1
        print(f"\n'{template.이름}' 양식은 이 파일에 정상적으로 적용할 수 있습니다.")
        return 0

    try:
        template = _resolve_template(table, mapping, args)
    except (TemplateError, OSError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 2

    problems = template.validate(table.columns)
    if problems:
        print(f"\n[양식 경고] '{template.이름}' 에서 {len(problems)}건:", file=sys.stderr)
        for problem in problems:
            print(f"  · {problem}", file=sys.stderr)
        print("  문제가 있는 부분은 건너뛰고 진행합니다.\n", file=sys.stderr)

    report = run(table, template, source=args.file)
    _print_summary(report)

    base = os.path.splitext(args.file)[0]
    if not args.no_report:
        out = args.out or f"{base}_분석.html"
        write_report(out, report, title=f"{template.이름} — {os.path.basename(args.file)}")
        print(f"  HTML 보고서: {os.path.abspath(out)}")

    tables = report.tables()
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

    if args.save_template:
        save_template(args.save_template, template)
        print(f"  분석 양식:   {os.path.abspath(args.save_template)}  (열어서 고쳐 쓰세요)")

    if args.save_profile:
        save_profile(args.save_profile, mapping)
        print(f"  컬럼 매핑:   {os.path.abspath(args.save_profile)}")

    return 0
