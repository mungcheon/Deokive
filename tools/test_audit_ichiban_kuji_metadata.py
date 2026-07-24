from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_ichiban_kuji_metadata as audit


class IchibanKujiMetadataAuditTests(unittest.TestCase):
    def test_extracts_exact_release_date_after_label(self) -> None:
        result = audit._extract_safe_release_date("■発売日：2026年07月20日より順次発売予定")

        self.assertEqual(result["value"], "2026-07-20")
        self.assertEqual(result["reason"], "exact date after release-date label")

    def test_extracts_release_month_without_inventing_day(self) -> None:
        result = audit._extract_safe_release_date("■発売日：店頭販売：2008年02月上旬発売予定")

        self.assertEqual(result["value"], "2008-02")
        self.assertEqual(result["reason"], "month after release-date label")

    def test_release_undecided_stays_missing(self) -> None:
        result = audit._extract_safe_release_date("■発売日：未定 ダブルチャンスキャンペーン期間：2026年07月20日")

        self.assertIsNone(result["value"])
        self.assertTrue(result["ambiguous"])

    def test_double_chance_date_is_not_release_date(self) -> None:
        result = audit._extract_safe_release_date("■ダブルチャンスキャンペーン期間：発売日～2026年07月20日")

        self.assertIsNone(result["value"])

    def test_zero_price_counts_as_present_metadata(self) -> None:
        rows = [
            {
                "source_url": "https://1kuji.com/products/example",
                "release_date": "2026-07-20",
                "official_price_jpy": 0,
            }
        ]

        self.assertEqual(audit._group_missing_1kuji_rows(rows), {})

    def test_zero_price_is_not_missing_with_missing_release_date(self) -> None:
        rows = [
            {
                "source_url": "https://1kuji.com/products/example",
                "official_price_jpy": 0,
            }
        ]

        grouped = audit._group_missing_1kuji_rows(rows)

        self.assertEqual(grouped["https://1kuji.com/products/example"]["missing_price_rows"], 0)
        self.assertEqual(grouped["https://1kuji.com/products/example"]["missing_release_rows"], 1)


if __name__ == "__main__":
    unittest.main()
