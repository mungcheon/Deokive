from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_ichiban_multi_character_review_public import build_review


class BuildIchibanMultiCharacterReviewPublicTest(unittest.TestCase):
    def test_classifies_pair_marker_as_likely_combined_goods(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST / A\u8cde / \u5b6b\u609f\u7a7a\uff06\u5b6b\u609f\u98ef \u30d5\u30a3\u30ae\u30e5\u30a2 / \ud63c\ud569",
                "series_name": "\u4e00\u756a\u304f\u3058 TEST",
                "sub_series": "A\u8cde",
                "character_name": "\ud63c\ud569",
                "source_url": "https://1kuji.com/products/test",
            }
        ]
        policy = {
            "ichiban_multi_character_product_review_candidates": [
                {
                    "catalog_index": 1,
                    "product_name": "\u5b6b\u609f\u7a7a\uff06\u5b6b\u609f\u98ef \u30d5\u30a3\u30ae\u30e5\u30a2",
                    "character_name": "\ud63c\ud569",
                    "matched_characters": ["\uc190\uc624\uacf5", "\uc190\uc624\ubc18"],
                }
            ]
        }

        report = build_review(rows, policy)

        self.assertEqual(report["summary"]["review_rows"], 1)
        self.assertEqual(report["summary"]["safe_auto_split_rows"], 0)
        self.assertEqual(report["summary"]["combined_goods_exception_rows"], 1)
        self.assertEqual(report["summary"]["actionable_split_review_rows"], 0)
        self.assertEqual(report["summary"]["requires_official_source_review_rows"], 0)
        self.assertEqual(report["review_rows"][0]["classification"], "likely_combined_goods")
        self.assertEqual(report["review_rows"][0]["split_name_templates"], [])
        self.assertIn("\ud63c\ud569", report["review_rows"][0]["preserve_name_template"])

    def test_prioritizes_rows_with_existing_individual_same_prize_context(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST / A\u8cde / \u5b6b\u609f\u7a7a\u30fb\u5b6b\u609f\u98ef \u30d5\u30a3\u30ae\u30e5\u30a2 / \ud63c\ud569",
                "series_name": "\u4e00\u756a\u304f\u3058 TEST",
                "sub_series": "A\u8cde",
                "character_name": "\ud63c\ud569",
                "source_url": "https://1kuji.com/products/test",
            },
            {
                "catalog_index": 2,
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST / A\u8cde / \u5b6b\u609f\u7a7a \u30d5\u30a3\u30ae\u30e5\u30a2 / \uc190\uc624\uacf5",
                "series_name": "\u4e00\u756a\u304f\u3058 TEST",
                "sub_series": "A\u8cde",
                "character_name": "\uc190\uc624\uacf5",
                "source_url": "https://1kuji.com/products/test",
            },
        ]
        policy = {
            "ichiban_multi_character_product_review_candidates": [
                {
                    "catalog_index": 1,
                    "product_name": "\u5b6b\u609f\u7a7a\u30fb\u5b6b\u609f\u98ef \u30d5\u30a3\u30ae\u30e5\u30a2",
                    "character_name": "\ud63c\ud569",
                    "matched_characters": ["\uc190\uc624\uacf5", "\uc190\uc624\ubc18"],
                }
            ]
        }

        report = build_review(rows, policy)

        self.assertEqual(report["review_rows"][0]["priority"], 1)
        self.assertEqual(report["review_rows"][0]["classification"], "split_context_review")
        self.assertEqual(report["review_rows"][0]["same_prize_row_count"], 2)
        self.assertEqual(report["summary"]["actionable_split_review_rows"], 1)


if __name__ == "__main__":
    unittest.main()
