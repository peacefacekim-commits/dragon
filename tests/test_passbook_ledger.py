import os
import unittest

from passbook_ledger.ocr import rows_from_tsv, parse_tsv, page_width_from_tsv

FIXTURE = os.path.join(os.path.dirname(__file__), "fixture_synthetic_passbook.tsv")


class TestPassbookOcr(unittest.TestCase):
    def setUp(self):
        with open(FIXTURE, encoding="utf-8") as f:
            self.tsv = f.read()

    def test_page_width(self):
        self.assertEqual(page_width_from_tsv(self.tsv), 900)

    def test_parse_tsv_filters_noise(self):
        words = parse_tsv(self.tsv)
        self.assertTrue(all(w.text.strip() for w in words))
        self.assertFalse(any(w.text.strip("|. ") == "" for w in words))

    def test_rows_extracted_with_correct_dates_and_amounts(self):
        rows = rows_from_tsv(self.tsv)
        self.assertEqual(len(rows), 8)
        expected = [
            ("2025-01-23", "수입", "80,000"),
            ("2025-01-23", "지급", "52,700"),
            ("2025-01-23", "수입", "0"),
            ("2025-01-23", "수입", "1,000,000"),
            ("2025-01-24", "수입", "100,000"),
            ("2025-01-25", "지급", "141,300"),
            ("2025-01-26", "지급", "300,000"),
            ("2025-01-27", "지급", "228,332"),
        ]
        for row, (date, gubun, amount) in zip(rows, expected):
            self.assertEqual(row["거래일자"], date)
            self.assertEqual(row["구분"], gubun)
            self.assertEqual(row["금액"], amount)

    def test_cd_garbled_description_is_autocorrected(self):
        rows = rows_from_tsv(self.tsv)
        self.assertEqual(rows[0]["적요"], "당행CD입금")
        self.assertEqual(rows[6]["적요"], "당행CD지급")
        self.assertIn("자동보정", rows[0]["확인사유"])

    def test_clean_rows_are_not_flagged_for_review(self):
        rows = rows_from_tsv(self.tsv)
        self.assertFalse(rows[1]["확인필요"])  # 외환카드대금, 완전히 인식됨
        self.assertEqual(rows[1]["적요"], "외환카드대금")
        self.assertEqual(rows[1]["메모"], "카드사")

    def test_uncertain_cells_are_left_blank_not_wrong(self):
        rows = rows_from_tsv(self.tsv)
        for row in rows:
            self.assertNotIn("|", row["잔액"])
            self.assertNotIn("|", row["금액"])

    def test_empty_tsv_returns_no_rows(self):
        self.assertEqual(rows_from_tsv(""), [])
        self.assertEqual(rows_from_tsv("level\tpage_num\n"), [])


if __name__ == "__main__":
    unittest.main()
