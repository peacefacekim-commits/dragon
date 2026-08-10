"""표준 unittest 로 작성. 실행:  python -m unittest discover -s tests -v"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from budget_analyzer import charts, report  # noqa: E402
from budget_analyzer.engine import analyze, period_key, run  # noqa: E402
from budget_analyzer.expression import ExpressionError, check, evaluate, evaluate_scalar  # noqa: E402
from budget_analyzer.mapping import ColumnMapping, guess_mapping, load_profile, save_profile  # noqa: E402
from budget_analyzer.table import Table, to_date, to_number  # noqa: E402
from budget_analyzer.template import (  # noqa: E402
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
from budget_analyzer import forecast as forecast_module  # noqa: E402
from budget_analyzer.xlsx_reader import SpreadsheetError, read_table, sheet_names  # noqa: E402
from budget_analyzer.xlsx_writer import Formula, write_csv, write_xlsx  # noqa: E402


def sample_table() -> Table:
    return Table(
        ["부서", "예산액", "집행액", "집행일자"],
        [
            ["총무과", 1000, 800, dt.date(2026, 1, 15)],
            ["총무과", 0, 200, dt.date(2026, 2, 10)],
            ["복지과", 2000, 2400, dt.date(2026, 1, 20)],
            ["복지과", 0, 100, dt.date(2026, 3, 5)],
            ["문화과", 500, 100, "2026-02-28"],
        ],
        name="테스트",
    )


def standard_report():
    table = sample_table()
    return analyze(table, guess_mapping(table), source="테스트.xlsx")


def block_named(result, name: str):
    for block in result.blocks:
        if block.이름 == name:
            return block
    raise AssertionError(f"'{name}' 블록이 없습니다: {[b.이름 for b in result.blocks]}")


class TestValueParsing(unittest.TestCase):
    def test_numbers_from_messy_strings(self):
        self.assertEqual(to_number("1,234,567"), 1234567.0)
        self.assertEqual(to_number("1,200,000원"), 1200000.0)
        self.assertEqual(to_number("(1,200)"), -1200.0)  # 회계식 음수
        self.assertEqual(to_number("12.5%"), 0.125)
        self.assertEqual(to_number(" 42 "), 42.0)
        self.assertEqual(to_number(-3), -3.0)

    def test_non_numbers_return_none(self):
        for value in (None, "", "   ", "미정", "-", True, dt.date(2026, 1, 1)):
            self.assertIsNone(to_number(value), value)

    def test_dates_from_common_korean_formats(self):
        expected = dt.date(2026, 3, 9)
        for value in ("2026-03-09", "2026/03/09", "2026.03.09", "2026년 3월 9일", "20260309", "2026-3-9"):
            self.assertEqual(to_date(value), expected, value)
        self.assertEqual(to_date(dt.datetime(2026, 3, 9, 13, 0)), expected)
        self.assertIsNone(to_date("이월"))

    def test_period_key_by_grain(self):
        date = dt.date(2026, 8, 3)
        self.assertEqual(period_key(date, "월"), "2026-08")
        self.assertEqual(period_key(date, "분기"), "2026-Q3")
        self.assertEqual(period_key(date, "연도"), "2026")
        self.assertEqual(period_key("3월", "월"), "03월")
        self.assertEqual(period_key("2분기", "분기"), "Q2")
        self.assertIsNone(period_key("미정", "월"))


class TestTable(unittest.TestCase):
    def test_group_sum_keeps_totals_and_counts(self):
        grouped = sample_table().group_sum("부서", ["예산액", "집행액"])
        rows = {row[0]: row for row in grouped.rows}
        self.assertEqual(rows["총무과"][1], 1000)
        self.assertEqual(rows["총무과"][2], 1000)
        self.assertEqual(rows["총무과"][3], 2)  # 건수
        self.assertEqual(rows["복지과"][2], 2500)

    def test_share_sums_to_one(self):
        grouped = sample_table().group_sum("부서", ["집행액"]).add_share("집행액")
        shares = [row[grouped.index_of("구성비")] for row in grouped.rows]
        self.assertAlmostEqual(sum(shares), 1.0)

    def test_ragged_rows_are_padded_and_trimmed(self):
        table = Table(["a", "b", "c"], [[1], [1, 2, 3, 4]])
        self.assertEqual(table.rows[0], [1, None, None])
        self.assertEqual(table.rows[1], [1, 2, 3])

    def test_sort_by_puts_text_after_numbers(self):
        table = Table(["a", "v"], [["x", 5], ["y", "미정"], ["z", 9]]).sort_by("v")
        self.assertEqual([row[0] for row in table.rows], ["z", "x", "y"])

    def test_sort_ascending_still_puts_text_last(self):
        table = Table(["a", "v"], [["x", 5], ["y", "미정"], ["z", 9]]).sort_by("v", descending=False)
        self.assertEqual([row[0] for row in table.rows], ["x", "z", "y"])

    def test_missing_column_raises_keyerror(self):
        with self.assertRaises(KeyError):
            sample_table().column("없는컬럼")


class TestExpression(unittest.TestCase):
    def setUp(self):
        self.table = sample_table()

    def test_column_arithmetic_is_row_wise(self):
        values = evaluate("[예산액] - [집행액]", self.table)
        self.assertEqual(values, [200, -200, -400, -100, 400])

    def test_aggregate_broadcasts_to_every_row(self):
        values = evaluate("합계([집행액])", self.table)
        self.assertEqual(values, [3600] * 5)

    def test_share_formula_matches_manual_ratio(self):
        values = evaluate("[집행액] / 합계([집행액])", self.table)
        self.assertAlmostEqual(sum(values), 1.0)
        self.assertAlmostEqual(values[0], 800 / 3600)

    def test_window_functions(self):
        self.assertEqual(evaluate("누적([집행액])", self.table)[-1], 3600)
        self.assertAlmostEqual(evaluate("누적비율([집행액])", self.table)[-1], 1.0)
        self.assertEqual(evaluate("순위([집행액])", self.table)[2], 1)
        growth = evaluate("증감률([집행액])", self.table)
        self.assertIsNone(growth[0])
        self.assertAlmostEqual(growth[1], (200 - 800) / 800)

    def test_conditional_and_comparison(self):
        values = evaluate('조건([집행액] > 500, "많음", "적음")', self.table)
        self.assertEqual(values, ["많음", "적음", "많음", "적음", "적음"])

    def test_string_comparison_and_contains(self):
        self.assertEqual(evaluate('[부서] == "총무과"', self.table)[:2], [True, True])
        self.assertEqual(evaluate('포함([부서], "복지")', self.table)[2], True)

    def test_logical_operators(self):
        both = evaluate('([집행액] > 100) and ([부서] == "총무과")', self.table)
        self.assertEqual(both, [True, True, False, False, False])
        self.assertEqual(evaluate("([집행액] > 2000) | ([예산액] > 400)", self.table)[4], True)

    def test_division_by_zero_yields_none_not_crash(self):
        values = evaluate("[집행액] / [예산액]", self.table)
        self.assertIsNone(values[1])  # 예산액 0
        self.assertAlmostEqual(values[0], 0.8)

    def test_nested_conditions_build_status_bands(self):
        formula = '조건([집행액] > 1000, "상", 조건([집행액] > 300, "중", "하"))'
        self.assertEqual(evaluate(formula, self.table), ["중", "하", "상", "하", "하"])

    def test_evaluate_scalar_returns_single_value(self):
        self.assertEqual(evaluate_scalar("합계([예산액])", self.table), 3500)

    def test_unknown_column_is_reported_clearly(self):
        with self.assertRaises(ExpressionError) as caught:
            evaluate("[없는컬럼] * 2", self.table)
        self.assertIn("없는컬럼", str(caught.exception))

    def test_unknown_function_is_reported(self):
        with self.assertRaises(ExpressionError) as caught:
            evaluate("이상한함수([집행액])", self.table)
        self.assertIn("이상한함수", str(caught.exception))

    def test_syntax_error_is_reported(self):
        with self.assertRaises(ExpressionError):
            evaluate("[집행액] +", self.table)

    def test_arbitrary_code_is_not_executed(self):
        # eval 이 아니라 허용 노드만 처리하므로 접근 자체가 막혀야 한다.
        for danger in (
            "__import__('os').system('echo hi')",
            "open('/etc/passwd').read()",
            "[집행액].__class__",
            "(lambda: 1)()",
        ):
            with self.assertRaises(ExpressionError, msg=danger):
                evaluate(danger, self.table)

    def test_check_reports_problems_without_running(self):
        self.assertIsNone(check("[집행액] * 2", ["집행액"]))
        self.assertIsNotNone(check("[없음] * 2", ["집행액"]))
        self.assertIsNotNone(check("합계(", ["집행액"]))


class TestMapping(unittest.TestCase):
    def test_guesses_korean_budget_columns(self):
        mapping = guess_mapping(sample_table())
        self.assertEqual(mapping.budget, "예산액")
        self.assertEqual(mapping.actual, "집행액")
        self.assertEqual(mapping.category, "부서")
        self.assertEqual(mapping.date, "집행일자")

    def test_ignores_code_columns_as_amounts(self):
        table = Table(
            ["사업코드", "사업명", "지출액"],
            [[10001, "가", 5000], [10002, "나", 7000], [10003, "다", 9000]],
        )
        mapping = guess_mapping(table)
        self.assertEqual(mapping.actual, "지출액")

    def test_falls_back_to_largest_numeric_column(self):
        table = Table(
            ["구분", "단가", "총계"],
            [["가", 100, 900000], ["나", 200, 800000], ["다", 150, 700000]],
        )
        self.assertEqual(guess_mapping(table).amount, "총계")

    def test_profile_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "p.json")
            save_profile(path, ColumnMapping(category="부서", budget="예산액"))
            loaded = load_profile(path)
        self.assertEqual(loaded.category, "부서")


class TestTemplate(unittest.TestCase):
    def test_generated_template_matches_recognised_columns(self):
        template = template_from_mapping(guess_mapping(sample_table()))
        self.assertEqual(template.이름, "표준 예산분석")
        self.assertEqual([b.이름 for b in template.블록][:2], ["항목별 집계 · 구성비", "예산 대비 집행률"])
        self.assertTrue(any(b.유형 == "추이" for b in template.블록))

    def test_simple_template_when_only_one_amount_column(self):
        table = Table(["부서", "금액"], [["가", 10], ["나", 20]])
        template = template_from_mapping(guess_mapping(table))
        self.assertEqual(template.이름, "단순 집계")

    def test_json_round_trip_preserves_everything(self):
        template = template_from_mapping(guess_mapping(sample_table()))
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "t.json")
            save_template(path, template)
            loaded = load_template(path)

        self.assertEqual(loaded.이름, template.이름)
        self.assertEqual(len(loaded.블록), len(template.블록))
        original = template.블록[1]
        restored = loaded.블록[1]
        self.assertEqual([m.컬럼 for m in restored.측정값], [m.컬럼 for m in original.측정값])
        self.assertEqual([c.식 for c in restored.계산], [c.식 for c in original.계산])
        self.assertEqual([r.조건 for r in restored.규칙], [r.조건 for r in original.규칙])

    def test_hand_written_json_is_accepted(self):
        data = {
            "이름": "손으로 쓴 양식",
            "블록": [
                {
                    "이름": "부서별",
                    "기준": ["부서"],
                    "측정값": [{"컬럼": "집행액", "함수": "합계"}],
                    "계산": [{"이름": "구성비", "식": "비율([집행액])", "서식": "비율"}],
                }
            ],
        }
        template = Template.from_dict(data)
        self.assertEqual(template.블록[0].측정값[0].결과이름, "집행액")
        self.assertEqual(template.validate(["부서", "집행액"]), [])

    def test_unknown_keys_are_ignored_not_fatal(self):
        template = Template.from_dict(
            {"이름": "x", "미래에추가될필드": 1, "블록": [{"이름": "b", "기준": ["부서"], "측정값": []}]}
        )
        self.assertEqual(template.이름, "x")

    def test_block_without_name_is_rejected(self):
        with self.assertRaises(TemplateError):
            Template.from_dict({"블록": [{"기준": ["부서"]}]})

    def test_validate_catches_missing_columns_and_bad_formulas(self):
        template = Template(
            블록=[
                Block(
                    이름="문제 블록",
                    기준=["없는컬럼"],
                    측정값=[Measure(컬럼="집행액", 함수="이상한함수")],
                    계산=[Computed(이름="x", 식="합계(")],
                )
            ]
        )
        problems = template.validate(["부서", "집행액"])
        self.assertTrue(any("없는컬럼" in p for p in problems))
        self.assertTrue(any("이상한함수" in p for p in problems))
        self.assertTrue(any("문법" in p for p in problems))

    def test_validate_requires_group_keys(self):
        problems = Template(블록=[Block(이름="빈 블록")]).validate(["부서"])
        self.assertTrue(any("기준" in p for p in problems))

    def test_validate_passes_for_generated_template(self):
        table = sample_table()
        template = template_from_mapping(guess_mapping(table))
        self.assertEqual(template.validate(table.columns), [])

    def test_builtin_presets_all_validate(self):
        table = sample_table()
        for preset in builtin_templates(guess_mapping(table)):
            self.assertEqual(preset.validate(table.columns), [], preset.이름)

    def test_saved_json_is_human_readable(self):
        template = template_from_mapping(guess_mapping(sample_table()))
        data = json.loads(template.to_json())
        self.assertIn("블록", data)
        self.assertIn("식", json.dumps(data, ensure_ascii=False))


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.result = standard_report()

    def test_summary_tiles(self):
        tiles = {tile.이름: tile.값 for tile in self.result.tiles}
        self.assertEqual(tiles["총 예산액"], 3500)
        self.assertEqual(tiles["총 집행액"], 3600)
        self.assertEqual(tiles["잔액"], -100)
        self.assertAlmostEqual(tiles["전체 집행률"], 3600 / 3500)

    def test_execution_block_matches_manual_calculation(self):
        block = block_named(self.result, "예산 대비 집행률")
        rows = {row[0]: row for row in block.표.rows}
        columns = block.표.columns
        self.assertEqual(rows["복지과"][columns.index("상태")], "초과")
        self.assertEqual(rows["문화과"][columns.index("상태")], "부진")
        self.assertEqual(rows["총무과"][columns.index("상태")], "정상")
        self.assertEqual(rows["복지과"][columns.index("잔액")], -500)
        self.assertAlmostEqual(rows["총무과"][columns.index("집행률")], 1.0)

    def test_rules_produce_warnings(self):
        block = block_named(self.result, "예산 대비 집행률")
        self.assertTrue(any("초과" in w for w in block.경고))
        self.assertTrue(any("부진" in w for w in block.경고))

    def test_breakdown_is_sorted_with_shares(self):
        block = block_named(self.result, "항목별 집계 · 구성비")
        values = [row[block.표.index_of("집행액")] for row in block.표.rows]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertAlmostEqual(block.표.column("누적구성비")[-1], 1.0)

    def test_trend_is_sorted_and_cumulative(self):
        block = block_named(self.result, "기간별 추이")
        periods = [row[0] for row in block.표.rows]
        self.assertEqual(periods, ["2026-01", "2026-02", "2026-03"])
        self.assertEqual(block.표.column("누적집행액")[-1], 3600)

    def test_global_filter_reduces_rows(self):
        template = Template(
            전체필터='[부서] != "복지과"',
            블록=[Block(이름="집계", 기준=["부서"], 측정값=[Measure(컬럼="집행액")])],
        )
        result = run(sample_table(), template)
        self.assertEqual(result.analyzed_count, 3)
        self.assertEqual(len(block_named(result, "집계").표), 2)

    def test_block_filter_is_independent(self):
        template = Template(
            블록=[
                Block(이름="전체", 기준=["부서"], 측정값=[Measure(컬럼="집행액")]),
                Block(
                    이름="큰 건만",
                    필터="[집행액] >= 800",
                    기준=["부서"],
                    측정값=[Measure(컬럼="집행액")],
                ),
            ]
        )
        result = run(sample_table(), template)
        self.assertEqual(len(block_named(result, "전체").표), 3)
        self.assertEqual(len(block_named(result, "큰 건만").표), 2)

    def test_derived_column_is_usable_in_blocks(self):
        template = Template(
            파생컬럼=[Computed(이름="규모", 식='조건([집행액] >= 500, "대", "소")', 서식="문자")],
            블록=[Block(이름="규모별", 기준=["규모"], 측정값=[Measure(컬럼="집행액")])],
        )
        result = run(sample_table(), template)
        labels = {row[0] for row in block_named(result, "규모별").표.rows}
        self.assertEqual(labels, {"대", "소"})

    def test_multiple_group_keys_produce_cross_tab(self):
        template = Template(
            블록=[
                Block(
                    이름="교차",
                    기준=["부서", "예산액"],
                    측정값=[Measure(컬럼="집행액")],
                )
            ]
        )
        block = block_named(run(sample_table(), template), "교차")
        self.assertEqual(block.표.columns[:2], ["부서", "예산액"])
        self.assertEqual(block.기준이름, ["부서", "예산액"])
        self.assertEqual(len(block.표), 5)

    def test_aggregation_functions(self):
        template = Template(
            블록=[
                Block(
                    이름="여러 함수",
                    기준=["부서"],
                    측정값=[
                        Measure(컬럼="집행액", 함수="합계", 이름="합"),
                        Measure(컬럼="집행액", 함수="평균", 이름="평균"),
                        Measure(컬럼="집행액", 함수="최대", 이름="최대"),
                        Measure(컬럼="부서", 함수="고유건수", 이름="부서수"),
                    ],
                )
            ]
        )
        block = block_named(run(sample_table(), template), "여러 함수")
        row = next(r for r in block.표.rows if r[0] == "총무과")
        self.assertEqual(row[block.표.index_of("합")], 1000)
        self.assertEqual(row[block.표.index_of("평균")], 500)
        self.assertEqual(row[block.표.index_of("최대")], 800)
        self.assertEqual(row[block.표.index_of("부서수")], 1)

    def test_averages_are_not_marked_summable(self):
        # 평균을 세로로 더하면 뜻이 없으므로 합계 행에서 빠져야 한다.
        template = Template(
            블록=[
                Block(
                    이름="b",
                    기준=["부서"],
                    측정값=[
                        Measure(컬럼="집행액", 함수="합계", 이름="합"),
                        Measure(컬럼="집행액", 함수="평균", 이름="평균"),
                    ],
                )
            ]
        )
        block = block_named(run(sample_table(), template), "b")
        self.assertIn("합", block.합산가능)
        self.assertNotIn("평균", block.합산가능)

    def test_top_n_folds_remainder_by_reaggregating(self):
        rows = [[f"항목{i}", 100 - i, 10] for i in range(20)]
        table = Table(["항목", "금액", "건"], rows)
        template = Template(
            블록=[
                Block(
                    이름="상위",
                    기준=["항목"],
                    측정값=[
                        Measure(컬럼="금액", 함수="합계"),
                        Measure(컬럼="건", 함수="평균", 이름="평균건"),
                    ],
                    정렬="금액",
                    상위=5,
                )
            ]
        )
        block = block_named(run(table, template), "상위")
        self.assertEqual(len(block.표), 6)
        self.assertIn("기타", str(block.표.rows[-1][0]))
        self.assertEqual(block.표.total("금액"), sum(100 - i for i in range(20)))
        # 평균은 더하지 않고 남은 원본 행에서 다시 계산해야 정확하다.
        self.assertEqual(block.표.rows[-1][block.표.index_of("평균건")], 10)

    def test_list_block_shows_raw_rows(self):
        template = Template(
            블록=[
                Block(
                    이름="목록",
                    유형="목록",
                    기준=["부서", "집행액"],
                    정렬="집행액",
                    상위=2,
                )
            ]
        )
        block = block_named(run(sample_table(), template), "목록")
        self.assertEqual(block.표.columns, ["부서", "집행액"])
        self.assertEqual(len(block.표), 2)
        self.assertEqual(block.표.rows[0][1], 2400)
        self.assertFalse(block.합계표시)

    def test_trend_grain_can_be_changed(self):
        template = Template(
            블록=[
                Block(
                    이름="분기",
                    유형="추이",
                    기준=["집행일자"],
                    단위="분기",
                    측정값=[Measure(컬럼="집행액")],
                )
            ]
        )
        block = block_named(run(sample_table(), template), "분기")
        self.assertEqual([row[0] for row in block.표.rows], ["2026-Q1"])

    def test_bad_formula_warns_but_other_blocks_still_run(self):
        template = Template(
            블록=[
                Block(
                    이름="망가진 계산",
                    기준=["부서"],
                    측정값=[Measure(컬럼="집행액")],
                    계산=[Computed(이름="x", 식="[없는컬럼] * 2")],
                ),
                Block(이름="정상", 기준=["부서"], 측정값=[Measure(컬럼="집행액")]),
            ]
        )
        result = run(sample_table(), template)
        self.assertEqual(len(result.blocks), 2)
        self.assertTrue(any("없는컬럼" in w for w in result.warnings))
        self.assertNotIn("x", block_named(result, "망가진 계산").표.columns)
        self.assertEqual(len(block_named(result, "정상").표), 3)

    def test_missing_group_column_is_skipped_with_warning(self):
        template = Template(블록=[Block(이름="b", 기준=["없음"], 측정값=[Measure(컬럼="집행액")])])
        result = run(sample_table(), template)
        self.assertTrue(any("없음" in w for w in result.warnings))
        self.assertEqual(len(block_named(result, "b").표), 0)

    def test_rule_message_placeholders(self):
        template = Template(
            블록=[
                Block(
                    이름="b",
                    기준=["부서"],
                    측정값=[Measure(컬럼="집행액")],
                    규칙=[Rule(조건="[집행액] > 900", 메시지="{건수}건 초과 (예: {항목})")],
                )
            ]
        )
        warnings = block_named(run(sample_table(), template), "b").경고
        self.assertEqual(len(warnings), 1)
        self.assertIn("2건", warnings[0])

    def test_summary_expression_failure_is_reported(self):
        template = Template(
            요약=[Summary(이름="망함", 식="합계([없는것])")],
            블록=[Block(이름="b", 기준=["부서"], 측정값=[Measure(컬럼="집행액")])],
        )
        result = run(sample_table(), template)
        self.assertEqual(result.tiles, [])
        self.assertTrue(any("망함" in w for w in result.warnings))


def _write_raw_xlsx_with_date_style_overflow(path: str) -> None:
    """실제로 부딪혔던 상황을 그대로 재현한다: 셀에는 '날짜 서식'이 걸려 있는데
    값은 (예산 금액처럼) 날짜로 변환하면 오버플로가 나는 아주 큰 숫자인 경우.
    write_xlsx 는 파이썬 타입에 따라 서식을 고르므로 이런 조합을 만들 수 없어,
    xlsx 내부 XML을 직접 손으로 구성한다.
    """
    import zipfile

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="sheet" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )
    # cellXfs 의 1번 인덱스(position 1)가 내장 날짜 서식(numFmtId=14)을 쓰도록 만든다.
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="14" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        "</cellXfs>"
        "</styleSheet>"
    )
    # A1: 정상적인 날짜(2026-05-04 == 시리얼 46143). B1: 날짜 서식이 걸려 있지만
    # 값은 예산 금액 같은 매우 큰 수(시리얼로 바꾸면 datetime 이 표현할 수 있는 범위를 넘어선다).
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        '<row r="1"><c r="A1" t="inlineStr"><is><t>목</t></is></c>'
        '<c r="B1" t="inlineStr"><is><t>금액</t></is></c></row>'
        '<row r="2"><c r="A2" s="1"><v>46146</v></c>'
        '<c r="B2" s="1"><v>6699009873</v></c></row>'
        "</sheetData></worksheet>"
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


class TestSpreadsheetRoundTrip(unittest.TestCase):
    def test_date_style_on_oversized_number_falls_back_to_plain_number(self):
        """실제 업로드 파일에서 'Python int too large to convert to C int' 로 죽던 사례.

        예산 금액 셀에 날짜 서식이 잘못 걸려 있어도, 날짜로 바꾸면 오버플로가 나는
        값이면 조용히 숫자로 읽어야지 예외를 던지면 안 된다.
        """
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "overflow.xlsx")
            _write_raw_xlsx_with_date_style_overflow(path)
            table = read_table(path)

        self.assertEqual(table.rows[0][0], dt.date(2026, 5, 4))  # 진짜 날짜는 그대로 날짜로
        self.assertEqual(table.rows[0][1], 6699009873)  # 오버플로 나는 값은 숫자로 대체

    def test_xlsx_write_then_read(self):
        source = Table(
            ["항목", "금액", "일자", "비율"],
            [
                ["가 & 나", 1234, dt.date(2026, 5, 4), 0.25],
                ["<태그>", -99.5, dt.datetime(2026, 6, 1, 9, 30), 1.0],
            ],
            name="결과",
        )
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.xlsx")
            write_xlsx(path, [source])
            self.assertEqual(sheet_names(path), ["결과"])
            loaded = read_table(path)

        self.assertEqual(loaded.rows[0][0], "가 & 나")  # XML 이스케이프 복원
        self.assertEqual(loaded.rows[1][0], "<태그>")
        self.assertEqual(loaded.rows[0][2], dt.date(2026, 5, 4))
        self.assertEqual(loaded.rows[1][2], dt.datetime(2026, 6, 1, 9, 30))

    def test_multiple_sheets_and_name_sanitizing(self):
        tables = [
            Table(["a"], [[1]], name="이름이/아주:길어서[31자를]넘어가는시트제목입니다"),
            Table(["b"], [[2]], name="짧은시트"),
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "multi.xlsx")
            write_xlsx(path, tables)
            names = sheet_names(path)
        self.assertEqual(len(names), 2)
        self.assertTrue(all(len(n) <= 31 for n in names))
        self.assertNotIn("/", names[0])

    def test_duplicate_sheet_names_are_made_unique(self):
        tables = [Table(["a"], [[1]], name="같은이름"), Table(["a"], [[2]], name="같은이름")]
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "dup.xlsx")
            write_xlsx(path, tables)
            self.assertEqual(len(set(sheet_names(path))), 2)

    def test_csv_is_written_with_bom_for_excel(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.csv")
            write_csv(path, Table(["항목", "금액"], [["한글", 100]]))
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(3), b"\xef\xbb\xbf")
            loaded = read_table(path)
        self.assertEqual(loaded.rows[0][0], "한글")

    def test_cp949_csv_is_decoded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "cp949.csv")
            with open(path, "w", encoding="cp949", newline="") as handle:
                handle.write("부서,집행액\n총무과,1000\n복지과,2000\n")
            loaded = read_table(path)
        self.assertEqual(loaded.columns, ["부서", "집행액"])
        self.assertEqual(loaded.rows[1][0], "복지과")

    def test_header_row_detected_below_title_rows(self):
        table = Table(
            ["2026년도 예산 집행 현황", "", "", ""],
            [
                [None, None, None, None],
                ["부서", "예산액", "집행액", "집행일자"],
                ["총무과", 1000, 800, dt.date(2026, 1, 1)],
                ["복지과", 2000, 1500, dt.date(2026, 2, 1)],
                ["문화과", 3000, 2500, dt.date(2026, 3, 1)],
            ],
            name="현황",
        )
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "titled.xlsx")
            write_xlsx(path, [table])
            loaded = read_table(path)
        self.assertEqual(loaded.columns, ["부서", "예산액", "집행액", "집행일자"])
        self.assertEqual(len(loaded), 3)

    def test_duplicate_and_blank_headers_are_renamed(self):
        table = Table(["항목", "금액", "금액", ""], [["가", 1, 2, 3]], name="s")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "d.xlsx")
            write_xlsx(path, [table])
            loaded = read_table(path, header_row=0)
        self.assertEqual(len(set(loaded.columns)), 4)
        self.assertIn("금액_1", loaded.columns)

    def test_unknown_sheet_raises(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "x.xlsx")
            write_xlsx(path, [Table(["a"], [[1]], name="하나")])
            with self.assertRaises(SpreadsheetError):
                read_table(path, sheet="없는시트")

    def test_non_xlsx_file_raises_helpful_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "fake.xlsx")
            with open(path, "wb") as handle:
                handle.write(b"not a zip file")
            with self.assertRaises(SpreadsheetError):
                read_table(path)


class TestCharts(unittest.TestCase):
    def test_bar_chart_is_valid_svg_with_labels(self):
        svg = charts.bar_chart(["가", "나"], [100, 50], shares=[0.67, 0.33])
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        self.assertEqual(svg.count("<title>"), 2)  # 항목마다 호버 툴팁

    def test_empty_inputs_render_placeholder(self):
        self.assertIn("chart-empty", charts.bar_chart([], []))
        self.assertIn("chart-empty", charts.line_chart([], []))
        self.assertIn("chart-empty", charts.execution_chart([], [], []))

    def test_line_chart_handles_missing_points(self):
        svg = charts.line_chart(["1월", "2월", "3월"], [("집행액", [10, None, 30])])
        self.assertIn("<path", svg)
        self.assertNotIn("None", svg)

    def test_single_period_does_not_divide_by_zero(self):
        self.assertIn("<circle", charts.line_chart(["2026-01"], [("집행액", [10])]))

    def test_all_zero_values_do_not_crash(self):
        self.assertIn("<svg", charts.bar_chart(["가", "나"], [0, 0]))
        self.assertIn("<svg", charts.line_chart(["1월"], [("금액", [0])]))

    def test_axis_ticks_always_cover_the_maximum(self):
        # 눈금이 최대값보다 작으면 마크가 차트 밖으로 잘려나간다.
        for maximum in (1, 7, 99, 3200, 123456, 2_484_000_000):
            self.assertGreaterEqual(charts._nice_ticks(maximum)[-1], maximum, maximum)

    def test_marks_stay_inside_the_viewbox(self):
        svg = charts.line_chart(["1월", "2월"], [("금액", [3200, 100])], height=300)
        for y in re.findall(r'cy="(-?[\d.]+)"', svg):
            self.assertGreaterEqual(float(y), 0.0)
            self.assertLessEqual(float(y), 300.0)

    def test_status_colours_come_from_the_caller(self):
        # 상태 문구는 양식마다 다르므로 색 매핑은 호출한 쪽이 정한다.
        svg = charts.execution_chart(
            ["가"], [1.2], ["위험"], status_class=lambda _s: "over"
        )
        self.assertIn("status-over", svg)
        self.assertIn("위험", svg)  # 색 외에 문구로도 상태를 전달

    def test_long_labels_are_truncated_not_clipped(self):
        self.assertIn("…", charts.bar_chart(["가" * 60], [10]))

    def test_special_characters_are_escaped(self):
        svg = charts.bar_chart(["A & B <c>"], [10])
        self.assertIn("&amp;", svg)
        self.assertNotIn("<c>", svg)


class TestReport(unittest.TestCase):
    def setUp(self):
        self.result = standard_report()

    def test_report_is_self_contained(self):
        html = report.render_report(self.result)
        self.assertIn("<!DOCTYPE html>", html)
        # 네트워크를 타는 참조가 하나도 없어야 폐쇄망에서 그대로 열린다.
        for marker in ("<script", "@import", "src=", "<link", "url(http"):
            self.assertNotIn(marker, html, marker)
        # (SVG 의 xmlns 는 식별자일 뿐 실제로 받아오지 않으므로 제외한다.)
        without_namespaces = re.sub(r'xmlns(:\w+)?="[^"]*"', "", html)
        self.assertNotIn("http://", without_namespaces)
        self.assertNotIn("https://", without_namespaces)

    def test_report_names_the_template_and_blocks(self):
        html = report.render_report(self.result)
        self.assertIn("표준 예산분석", html)
        for block in self.result.blocks:
            self.assertIn(block.이름, html)
        self.assertIn("prefers-color-scheme", html)  # 다크 모드 대응

    def test_report_escapes_source_names(self):
        self.result.source = "<script>alert(1)</script>"
        self.assertNotIn("<script>", report.render_report(self.result))

    def test_custom_status_words_still_get_colours(self):
        for word, expected in (("위험", "over"), ("주의", "under"), ("양호", "normal"), ("기타", "unknown")):
            self.assertEqual(report.status_class(word), expected, word)

    def test_percent_columns_are_formatted_as_percent(self):
        text, right = report.format_value(0.921, "비율")
        self.assertEqual(text, "92.1%")
        self.assertTrue(right)

    def test_report_survives_empty_template(self):
        empty = run(Table(["메모"], [["가"]]), Template(이름="빈 양식"))
        self.assertIn("<!DOCTYPE html>", report.render_report(empty))

    def test_report_written_to_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "r.html")
            report.write_report(path, self.result)
            with open(path, encoding="utf-8") as handle:
                self.assertIn("표준 예산분석", handle.read())


class TestCli(unittest.TestCase):
    def test_end_to_end_from_command_line(self):
        from budget_analyzer.cli import main

        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "예산.xlsx")
            write_xlsx(source, [sample_table()])
            html = os.path.join(folder, "보고서.html")
            xlsx = os.path.join(folder, "결과.xlsx")
            csv_dir = os.path.join(folder, "csv")
            template_path = os.path.join(folder, "양식.json")

            code = main(
                [source, "-o", html, "--xlsx", xlsx, "--csv-dir", csv_dir,
                 "--save-template", template_path]
            )

            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(html))
            self.assertTrue(os.path.exists(xlsx))
            self.assertTrue(os.listdir(csv_dir))
            self.assertTrue(os.path.exists(template_path))

    def test_saved_template_can_be_replayed(self):
        from budget_analyzer.cli import main

        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "예산.xlsx")
            write_xlsx(source, [sample_table()])
            template_path = os.path.join(folder, "양식.json")

            main([source, "--no-report", "--save-template", template_path])
            code = main([source, "--no-report", "--template", template_path])
            self.assertEqual(code, 0)

    def test_check_template_reports_mismatch(self):
        from budget_analyzer.cli import main

        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "예산.xlsx")
            write_xlsx(source, [sample_table()])
            template_path = os.path.join(folder, "양식.json")
            save_template(
                template_path,
                Template(이름="안맞는 양식", 블록=[Block(이름="b", 기준=["없는컬럼"], 측정값=[Measure(컬럼="집행액")])]),
            )
            self.assertEqual(main([source, "--check-template", template_path]), 1)

    def test_missing_file_returns_error_code(self):
        from budget_analyzer.cli import main

        self.assertEqual(main(["/존재하지/않는/파일.xlsx", "--no-report"]), 2)

    def test_unknown_column_override_exits(self):
        from budget_analyzer.cli import main

        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "예산.xlsx")
            write_xlsx(source, [sample_table()])
            with self.assertRaises(SystemExit):
                main([source, "--category", "없는컬럼", "--no-report"])


class TestSampleTemplate(unittest.TestCase):
    """저장소에 들어 있는 예시 양식이 실제로 도는지 확인한다."""

    def test_example_template_runs_against_sample_data(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "samples", "양식_예시.json")
        if not os.path.exists(path):
            self.skipTest("예시 양식 파일이 없습니다.")

        template = load_template(path)
        table = Table(
            ["부서", "세부사업", "계정과목", "예산액", "집행액", "집행일자"],
            [
                ["총무과", "청사관리", "일반운영비", 100_000_000, 60_000_000, dt.date(2026, 3, 1)],
                ["총무과", "차량운영", "일반운영비", 50_000_000, 55_000_000, dt.date(2026, 9, 1)],
                ["복지과", "돌봄", "민간이전", 200_000_000, 190_000_000, dt.date(2026, 5, 1)],
            ],
            name="집행내역",
        )
        self.assertEqual(template.validate(table.columns), [])
        result = run(table, template, source="테스트")
        self.assertTrue(result.blocks)
        self.assertIn("<!DOCTYPE html>", report.render_report(result))


class TestForecast(unittest.TestCase):
    """집행 전망(작년 동기간 패턴 + 가중치) 계산과 산출 엑셀 구조를 검증한다."""

    def history_table(self) -> Table:
        return Table(
            ["원인행위일자", "원인행위금액", "목코드", "세목코드"],
            [
                # 210/01: 기준일까지 1000, 동기간(8/11~9/30)에 500 더 씀 -> 비율 0.5
                ["2025-01-01", 1000, "210", "01"],
                ["2025-09-01", 500, "210", "01"],
                # 220/02: 기준일까지 2000, 동기간엔 추가 지출 없음 -> 비율 0
                ["2025-02-01", 2000, "220", "02"],
                # 기준일 이후(작년 목표일 지남)에 벌어진 지출은 제외되어야 한다
                ["2025-11-01", 9999, "210", "01"],
            ],
            name="원인행위상세목록",
        )

    def current_table(self) -> Table:
        return Table(
            ["회계", "목", "세목", "26년예산", "8.10. 현재 집행", "3분기까지 집행 전망(누계액)"],
            [
                ["[총계]", None, None, 10000, 3900, 0],
                ["[11]일반회계", "[210]운영비", "[01]일반수용비", 5000, 3000, None],
                ["[11]일반회계", "[220]여비", "[02]국내여비", 4000, 800, None],
                ["[11]일반회계", "[230]업무추진비", "[03]사업추진비", 1000, 100, None],  # 작년 실적 없음 -> 전체 평균 대체
            ],
            name="현황",
        )

    def build(self, **overrides):
        settings = forecast_module.ForecastSettings(
            base_date=dt.date(2026, 8, 10),
            target_date=dt.date(2026, 9, 30),
            weight_percent=overrides.pop("weight_percent", 100.0),
        )
        return forecast_module.build_forecast(self.history_table(), self.current_table(), settings, **overrides)

    def test_extract_code_strips_bracket_prefix(self):
        self.assertEqual(forecast_module._extract_code("[220]여비"), "220")
        self.assertEqual(forecast_module._extract_code("맨텍스트"), "맨텍스트")
        self.assertEqual(forecast_module._extract_code(None), "")

    def test_end_of_quarter(self):
        self.assertEqual(forecast_module.end_of_quarter(dt.date(2026, 8, 10)), dt.date(2026, 9, 30))
        self.assertEqual(forecast_module.end_of_quarter(dt.date(2026, 1, 1)), dt.date(2026, 3, 31))
        self.assertEqual(forecast_module.end_of_quarter(dt.date(2026, 12, 31)), dt.date(2026, 12, 31))

    def test_settings_reject_target_before_base(self):
        with self.assertRaises(forecast_module.ForecastError):
            forecast_module.ForecastSettings(base_date=dt.date(2026, 8, 10), target_date=dt.date(2026, 1, 1))

    def test_settings_derive_last_year_window(self):
        settings = forecast_module.ForecastSettings(base_date=dt.date(2026, 8, 10), target_date=dt.date(2026, 9, 30))
        self.assertEqual(settings.history_base_date, dt.date(2025, 8, 10))
        self.assertEqual(settings.history_target_date, dt.date(2025, 9, 30))

    def test_matched_and_unmatched_counts(self):
        result = self.build()
        self.assertEqual(result.matched_rows, 2)
        self.assertEqual(result.unmatched_rows, 1)
        self.assertTrue(result.warnings)

    def test_ratio_column_matches_hand_calculated_values(self):
        result = self.build()
        ratio_idx = result.table.index_of("작년동기간증감율(%)")
        item_idx = result.table.index_of("목")

        by_item = {row[item_idx]: row[ratio_idx] for row in result.table.rows}
        # 퍼센트 서식 컬럼이라 값 자체는 분수로 저장된다 (0.5 == 50%, report.py 의 '비율' 관례와 동일).
        self.assertAlmostEqual(by_item["[210]운영비"], 0.5)
        self.assertAlmostEqual(by_item["[220]여비"], 0.0)
        # 전체 평균 = (500) / (1000 + 2000) = 16.67%
        self.assertAlmostEqual(by_item["[230]업무추진비"], 0.1667, places=3)
        self.assertAlmostEqual(result.overall_ratio, 0.1667, places=3)

    def test_detail_rows_get_formulas_referencing_same_row(self):
        result = self.build()
        table = result.table
        exec_idx = table.index_of("8.10. 현재 집행")
        target_idx = table.index_of("3분기까지 집행 전망(누계액)")
        increase_idx = table.index_of("가중치적용_예상증가액")

        exec_letter = forecast_module._column_letter(exec_idx)
        increase_letter = forecast_module._column_letter(increase_idx)

        # 2번째 행(총계 다음)이 [210]운영비 -> 엑셀 행 번호는 3
        row = table.rows[1]
        self.assertIsInstance(row[target_idx], Formula)
        self.assertEqual(str(row[target_idx]), f"={exec_letter}3+{increase_letter}3")
        self.assertIsInstance(row[increase_idx], Formula)
        self.assertIn("'설정'!$B$6", str(row[increase_idx]))

    def test_total_row_sums_detail_rows_instead_of_using_its_own_ratio(self):
        result = self.build()
        table = result.table
        target_idx = table.index_of("3분기까지 집행 전망(누계액)")
        increase_idx = table.index_of("가중치적용_예상증가액")

        total_row = table.rows[0]
        self.assertEqual(total_row[0], "[총계]")
        self.assertIsInstance(total_row[target_idx], Formula)
        self.assertTrue(str(total_row[target_idx]).startswith("=SUM("))
        self.assertIsInstance(total_row[increase_idx], Formula)
        self.assertIsNone(total_row[table.index_of("작년동기간증감율(%)")])

    def test_forecast_rate_column_present_when_budget_column_found(self):
        result = self.build()
        self.assertIn("전망집행률(%)", result.table.columns)

    def test_weight_percent_is_stored_for_settings_sheet(self):
        result = self.build(weight_percent=80.0)
        self.assertEqual(result.settings.weight_percent, 80.0)

    def test_history_amounts_after_target_date_are_excluded(self):
        # 2025-11-01 의 9999 는 작년 목표일(9/30) 이후라 비율 계산에 들어가면 안 된다.
        result = self.build()
        ratio_idx = result.table.index_of("작년동기간증감율(%)")
        item_idx = result.table.index_of("목")
        by_item = {row[item_idx]: row[ratio_idx] for row in result.table.rows}
        self.assertAlmostEqual(by_item["[210]운영비"], 0.5)

    def test_unknown_override_column_raises_clear_error(self):
        settings = forecast_module.ForecastSettings(base_date=dt.date(2026, 8, 10), target_date=dt.date(2026, 9, 30))
        with self.assertRaises(forecast_module.ForecastError):
            forecast_module.build_forecast(
                self.history_table(), self.current_table(), settings, current_exec_column="없는컬럼"
            )

    def test_write_forecast_produces_settings_and_data_sheets(self):
        result = self.build(weight_percent=100.0)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "전망.xlsx")
            forecast_module.write_forecast(path, result)
            self.assertEqual(sheet_names(path), ["설정", "집행전망"])

            settings_table = read_table(path, sheet="설정")
            rows = {row[0]: row[1] for row in settings_table.rows}
            self.assertEqual(rows["가중치(%)"], 100)
            self.assertEqual(rows["기준일(올해)"], dt.date(2026, 8, 10))

    def test_ratio_and_rate_columns_use_percent_style_not_double_scaled(self):
        """xlsx_writer 는 컬럼 이름에 '율'·'%' 가 있으면 자동으로 0.00% 서식을 입힌다.
        그러니 셀 값 자체는 분수여야 한다 — 50 을 넣으면 화면에 '5000.00%' 로 곱절
        스케일링되어 버린다."""
        result = self.build()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "전망.xlsx")
            forecast_module.write_forecast(path, result)
            import zipfile

            with zipfile.ZipFile(path) as archive:
                xml = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")

        ratio_idx = result.table.index_of("작년동기간증감율(%)")
        rate_idx = result.table.index_of("전망집행률(%)")
        ratio_letter = forecast_module._column_letter(ratio_idx)
        rate_letter = forecast_module._column_letter(rate_idx)
        # [210]운영비 행은 엑셀 행 3, 값은 0.5 (=50%) 이어야 하고 퍼센트 스타일(s="3")이어야 한다.
        self.assertIn(f'<c r="{ratio_letter}3" s="3"><v>0.5</v></c>', xml)
        self.assertIn(f'{rate_letter}3" s="3"><f>IF(', xml)

    def test_cli_forecast_flag_runs_end_to_end(self):
        from budget_analyzer.cli import main

        with tempfile.TemporaryDirectory() as folder:
            history_path = os.path.join(folder, "작년.xlsx")
            current_path = os.path.join(folder, "올해.xlsx")
            out_path = os.path.join(folder, "결과.xlsx")
            write_xlsx(history_path, [self.history_table()])
            write_xlsx(current_path, [self.current_table()])

            code = main([current_path, "--전망", history_path, "--xlsx", out_path])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(out_path))
            self.assertEqual(sheet_names(out_path), ["설정", "집행전망"])


class TestXlsxWriterFormula(unittest.TestCase):
    def test_formula_cell_is_written_as_formula_not_value(self):
        table = Table(["a", "b"], [[1, Formula("=A1*2")]], name="t")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "f.xlsx")
            write_xlsx(path, [table])
            import zipfile

            with zipfile.ZipFile(path) as archive:
                xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
            self.assertIn("<f>A1*2</f>", xml)
            self.assertNotIn("<v>A1*2</v>", xml)


if __name__ == "__main__":
    unittest.main()
