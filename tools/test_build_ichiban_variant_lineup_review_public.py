from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_ichiban_variant_lineup_review_public import build_review


class BuildIchibanVariantLineupReviewPublicTest(unittest.TestCase):
    def test_flags_expected_count_that_exceeds_same_prize_rows(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST / D\u8cde / \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 \u51683\u7a2e / \uae30\ud0c0",
                "name_ja": "D\u8cde \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 \u51683\u7a2e",
                "series_name": "\u4e00\u756a\u304f\u3058 TEST",
                "sub_series": "D\u8cde",
                "character_name": "\uae30\ud0c0",
                "source_url": "https://1kuji.com/products/test",
            }
        ]

        report = build_review(rows)

        self.assertEqual(report["summary"]["review_rows"], 1)
        self.assertEqual(report["review_rows"][0]["priority"], 1)
        self.assertEqual(report["review_rows"][0]["classification"], "expected_count_exceeds_rows")
        self.assertEqual(report["review_rows"][0]["expected_variant_count"], 3)
        self.assertEqual(report["review_rows"][0]["same_prize_row_count"], 1)

    def test_flags_assort_marker_on_generic_character_row(self) -> None:
        rows = [
            {
                "catalog_index": 2,
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST / F\u8cde / \u30bf\u30aa\u30eb\u30a2\u30bd\u30fc\u30c8 / \uae30\ud0c0",
                "name_ja": "F\u8cde \u30bf\u30aa\u30eb\u30a2\u30bd\u30fc\u30c8",
                "series_name": "\u4e00\u756a\u304f\u3058 TEST",
                "sub_series": "F\u8cde",
                "character_name": "\uae30\ud0c0",
                "source_url": "https://1kuji.com/products/test",
            },
            {
                "catalog_index": 3,
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST / F\u8cde / \u30bf\u30aa\u30eb / \uce90\ub9ad\ud130A",
                "series_name": "\u4e00\u756a\u304f\u3058 TEST",
                "sub_series": "F\u8cde",
                "character_name": "\uce90\ub9ad\ud130A",
                "source_url": "https://1kuji.com/products/test",
            },
        ]

        report = build_review(rows)

        self.assertEqual(report["summary"]["review_rows"], 1)
        self.assertEqual(report["review_rows"][0]["classification"], "generic_character_lineup_marker")
        self.assertEqual(report["review_rows"][0]["named_variant_row_count"], 1)

    def test_skips_complete_numbered_fraction_groups(self) -> None:
        rows = [
            {
                "catalog_index": index,
                "name_ko": f"\u4e00\u756a\u304f\u3058 TEST / G\u8cde / \u30bf\u30aa\u30eb\uff08{index}/3\uff09 / \uae30\ud0c0",
                "name_ja": f"G\u8cde \u30bf\u30aa\u30eb\uff08{index}/3\uff09",
                "series_name": "\u4e00\u756a\u304f\u3058 TEST",
                "sub_series": "G\u8cde",
                "character_name": "\uae30\ud0c0",
                "source_url": "https://1kuji.com/products/test",
            }
            for index in range(1, 4)
        ]

        report = build_review(rows)

        self.assertEqual(report["summary"]["review_rows"], 0)


if __name__ == "__main__":
    unittest.main()
