"""표준 unittest 로 작성. 실행:  python -m unittest discover -s tests -v"""

from __future__ import annotations

import datetime as dt
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from budget_analyzer import charts, report  # noqa: E402
from budget_analyzer.analysis import analyze  # noqa: E402
from budget_analyzer.mapping import ColumnMapping, guess_mapping, load_profile, save_profile  # noqa: E402
from budget_analyzer.table import Table, to_date, to_number  # noqa: E402
from budget_analyzer.xlsx_reader import SpreadsheetError, read_table, sheet_names  # noqa: E402
from budget_analyzer.xlsx_writer import write_csv, write_xlsx  # noqa: E402


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

    def test_share_is_none_when_total_is_zero(self):
        table = Table(["항목", "금액"], [["가", 0], ["나", 0]]).add_share("금액")
        self.assertTrue(all(row[2] is None for row in table.rows))

    def test_ragged_rows_are_padded_and_trimmed(self):
        table = Table(["a", "b", "c"], [[1], [1, 2, 3, 4]])
        self.assertEqual(table.rows[0], [1, None, None])
        self.assertEqual(table.rows[1], [1, 2, 3])

    def test_sort_by_puts_text_after_numbers(self):
        table = Table(["a", "v"], [["x", 5], ["y", "미정"], ["z", 9]]).sort_by("v")
        self.assertEqual([row[0] for row in table.rows], ["z", "x", "y"])

    def test_with_column_replaces_existing(self):
        table = sample_table().with_column("예산액", lambda record: 1)
        self.assertEqual(len(table.columns), 4)
        self.assertTrue(all(row[1] == 1 for row in table.rows))

    def test_missing_column_raises_keyerror(self):
        with self.assertRaises(KeyError):
            sample_table().column("없는컬럼")


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
        self.assertNotIn(mapping.value_column, ("사업코드",))

    def test_falls_back_to_largest_numeric_column(self):
        table = Table(
            ["구분", "단가", "총계"],
            [["가", 100, 900000], ["나", 200, 800000], ["다", 150, 700000]],
        )
        mapping = guess_mapping(table)
        self.assertEqual(mapping.amount, "총계")

    def test_value_column_prefers_actual(self):
        mapping = ColumnMapping(budget="예산액", actual="집행액", amount="금액")
        self.assertEqual(mapping.value_column, "집행액")

    def test_profile_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "p.json")
            save_profile(path, ColumnMapping(category="부서", budget="예산액"))
            loaded = load_profile(path)
        self.assertEqual(loaded.category, "부서")
        self.assertEqual(loaded.budget, "예산액")


class TestAnalysis(unittest.TestCase):
    def setUp(self):
        table = sample_table()
        self.result = analyze(table, guess_mapping(table), source="테스트.xlsx")

    def test_totals_and_overall_rate(self):
        self.assertEqual(self.result.totals["예산액"], 3500)
        self.assertEqual(self.result.totals["집행액"], 3600)
        self.assertAlmostEqual(self.result.execution_rate, 3600 / 3500)

    def test_execution_status_thresholds(self):
        rows = {row[0]: row for row in self.result.execution.rows}
        columns = self.result.execution.columns
        status = columns.index("상태")
        rate = columns.index("집행률")
        self.assertEqual(rows["복지과"][status], "초과")  # 2500/2000
        self.assertEqual(rows["문화과"][status], "부진")  # 100/500
        self.assertEqual(rows["총무과"][status], "정상")  # 1000/1000
        self.assertAlmostEqual(rows["총무과"][rate], 1.0)
        self.assertEqual(rows["복지과"][columns.index("잔액")], -500)

    def test_trend_is_sorted_and_cumulative(self):
        trend = self.result.trend
        periods = [row[0] for row in trend.rows]
        self.assertEqual(periods, sorted(periods))
        self.assertEqual(periods, ["2026-01", "2026-02", "2026-03"])
        cumulative = trend.column("누적집행액")
        self.assertEqual(cumulative[-1], 3600)

    def test_quarter_grain(self):
        table = sample_table()
        result = analyze(table, guess_mapping(table), grain="quarter")
        self.assertEqual([row[0] for row in result.trend.rows], ["2026-Q1"])

    def test_breakdown_shares_and_order(self):
        breakdown = self.result.breakdown
        values = [row[breakdown.index_of("집행액")] for row in breakdown.rows]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertAlmostEqual(breakdown.column("누적구성비")[-1], 1.0)

    def test_top_n_folds_remainder_into_other(self):
        table = Table(
            ["항목", "금액"], [[f"항목{i}", 100 - i] for i in range(20)]
        )
        result = analyze(table, ColumnMapping(category="항목", amount="금액"), top_n=5)
        self.assertEqual(len(result.breakdown), 6)
        self.assertIn("기타", str(result.breakdown.rows[-1][0]))
        self.assertEqual(result.breakdown.total("금액"), sum(100 - i for i in range(20)))

    def test_missing_columns_produce_warnings_not_crashes(self):
        table = Table(["메모"], [["가"], ["나"]])
        result = analyze(table, ColumnMapping())
        self.assertIsNone(result.breakdown)
        self.assertTrue(result.warnings)

    def test_no_date_column_skips_trend_with_warning(self):
        table = Table(["부서", "금액"], [["가", 10], ["나", 20]])
        result = analyze(table, ColumnMapping(category="부서", amount="금액"))
        self.assertIsNone(result.trend)
        self.assertTrue(any("기간" in w for w in result.warnings))

    def test_zero_budget_rows_are_flagged(self):
        table = Table(["부서", "예산액", "집행액"], [["가", 0, 500]])
        result = analyze(table, ColumnMapping(category="부서", budget="예산액", actual="집행액"))
        status = result.execution.rows[0][result.execution.index_of("상태")]
        self.assertEqual(status, "예산없음(집행만)")


class TestSpreadsheetRoundTrip(unittest.TestCase):
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

        self.assertEqual(loaded.columns, ["항목", "금액", "일자", "비율"])
        self.assertEqual(loaded.rows[0][0], "가 & 나")  # XML 이스케이프 복원
        self.assertEqual(loaded.rows[1][0], "<태그>")
        self.assertEqual(loaded.rows[0][1], 1234)
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
            names = sheet_names(path)
        self.assertEqual(len(set(names)), 2)

    def test_csv_is_written_with_bom_for_excel(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "out.csv")
            write_csv(path, Table(["항목", "금액"], [["한글", 100]]))
            with open(path, "rb") as handle:
                self.assertTrue(handle.read(3) == b"\xef\xbb\xbf")
            loaded = read_table(path)
        self.assertEqual(loaded.columns, ["항목", "금액"])
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

    def test_explicit_header_row_overrides_detection(self):
        table = Table(["제목", "", ""], [["부서", "예산액", "집행액"], ["가", 1, 2]], name="s")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "h.xlsx")
            write_xlsx(path, [table])
            loaded = read_table(path, header_row=0)
        self.assertEqual(loaded.columns[0], "제목")

    def test_duplicate_and_blank_headers_are_renamed(self):
        table = Table(["항목", "금액", "금액", ""], [["가", 1, 2, 3]], name="s")
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "d.xlsx")
            write_xlsx(path, [table])
            loaded = read_table(path, header_row=0)
        self.assertEqual(len(set(loaded.columns)), 4)
        self.assertIn("금액", loaded.columns)
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
        self.assertIn("가", svg)
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
        svg = charts.line_chart(["2026-01"], [("집행액", [10])])
        self.assertIn("<circle", svg)

    def test_all_zero_values_do_not_crash(self):
        self.assertIn("<svg", charts.bar_chart(["가", "나"], [0, 0]))
        self.assertIn("<svg", charts.line_chart(["1월"], [("금액", [0])]))

    def test_execution_chart_marks_status_without_relying_on_color(self):
        svg = charts.execution_chart(["가", "나"], [1.2, None], ["초과", "-"])
        self.assertIn("초과", svg)  # 색 외에 문구로도 상태를 전달
        self.assertIn("status-over", svg)

    def test_axis_ticks_always_cover_the_maximum(self):
        # 눈금이 최대값보다 작으면 마크가 차트 밖으로 잘려나간다.
        for maximum in (1, 7, 99, 3200, 123456, 2_484_000_000):
            self.assertGreaterEqual(charts._nice_ticks(maximum)[-1], maximum, maximum)

    def test_marks_stay_inside_the_viewbox(self):
        svg = charts.line_chart(["1월", "2월"], [("금액", [3200, 100])], height=300)
        for y in re.findall(r'cy="(-?[\d.]+)"', svg):
            self.assertGreaterEqual(float(y), 0.0)
            self.assertLessEqual(float(y), 300.0)

    def test_long_labels_are_truncated_not_clipped(self):
        svg = charts.bar_chart(["가" * 60], [10])
        self.assertIn("…", svg)

    def test_special_characters_are_escaped(self):
        svg = charts.bar_chart(["A & B <c>"], [10])
        self.assertIn("&amp;", svg)
        self.assertNotIn("<c>", svg)


class TestReport(unittest.TestCase):
    def setUp(self):
        table = sample_table()
        self.result = analyze(table, guess_mapping(table), source="테스트.xlsx")

    def test_report_is_self_contained(self):
        html = report.render_report(self.result)
        self.assertIn("<!DOCTYPE html>", html)
        # 네트워크를 타는 참조가 하나도 없어야 폐쇄망에서 그대로 열린다.
        # (SVG 의 xmlns 는 식별자일 뿐 실제로 받아오지 않으므로 제외한다.)
        for marker in ("<script", "@import", "src=", "<link", "url(http"):
            self.assertNotIn(marker, html, marker)

        without_namespaces = re.sub(r'xmlns(:\w+)?="[^"]*"', "", html)
        self.assertNotIn("http://", without_namespaces)
        self.assertNotIn("https://", without_namespaces)

    def test_report_contains_all_three_sections(self):
        html = report.render_report(self.result)
        self.assertIn("항목별 집계", html)
        self.assertIn("예산 대비 집행률", html)
        self.assertIn("추이", html)
        self.assertIn("prefers-color-scheme", html)  # 다크 모드 대응

    def test_report_escapes_source_names(self):
        self.result.source = '<script>alert(1)</script>'
        html = report.render_report(self.result)
        self.assertNotIn("<script>", html)

    def test_report_written_to_disk(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "r.html")
            report.write_report(path, self.result)
            with open(path, encoding="utf-8") as handle:
                self.assertIn("예산 분석 보고서", handle.read())

    def test_report_survives_empty_analysis(self):
        empty = analyze(Table(["메모"], [["가"]]), ColumnMapping())
        html = report.render_report(empty)
        self.assertIn("<!DOCTYPE html>", html)


class TestCli(unittest.TestCase):
    def test_end_to_end_from_command_line(self):
        from budget_analyzer.cli import main

        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "예산.xlsx")
            write_xlsx(source, [sample_table()])
            html = os.path.join(folder, "보고서.html")
            xlsx = os.path.join(folder, "결과.xlsx")
            csv_dir = os.path.join(folder, "csv")

            code = main([source, "-o", html, "--xlsx", xlsx, "--csv-dir", csv_dir])

            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(html))
            self.assertTrue(os.path.exists(xlsx))
            self.assertTrue(os.listdir(csv_dir))

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


if __name__ == "__main__":
    unittest.main()
