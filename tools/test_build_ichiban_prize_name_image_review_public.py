from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_prize_name_image_review_public as target


class BuildIchibanPrizeNameImageReviewPublicTest(unittest.TestCase):
    def test_flags_name_policy_and_image_reuse_risks(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "series_name": "一番くじ Sample",
                    "sub_series": "A賞",
                    "name_ja": "A賞 Figure",
                    "name_ko": "一番くじ Sample - A賞 Figure",
                    "source_url": "https://1kuji.com/products/sample",
                    "image_url": "https://assets.1kuji.com/a.jpg",
                },
                {
                    "catalog_index": 2,
                    "series_name": "一番くじ Sample",
                    "sub_series": "B賞",
                    "name_ja": "Figure Without Rank",
                    "name_ko": "一番くじ Sample - B賞 Figure Without Rank",
                    "source_url": "https://1kuji.com/products/sample",
                    "image_url": "https://assets.1kuji.com/b.jpg",
                },
                {
                    "catalog_index": 3,
                    "series_name": "一番くじ Sample",
                    "sub_series": "C賞",
                    "name_ja": "C賞 Item Red",
                    "name_ko": "Wrong Display",
                    "source_url": "https://1kuji.com/products/sample",
                    "image_url": "https://assets.1kuji.com/shared.jpg",
                },
                {
                    "catalog_index": 4,
                    "series_name": "一番くじ Sample",
                    "sub_series": "C賞",
                    "name_ja": "C賞 Item Blue",
                    "name_ko": "一番くじ Sample - C賞 Item Blue",
                    "source_url": "https://1kuji.com/products/sample",
                    "image_url": "https://assets.1kuji.com/shared.jpg",
                },
            ]
        }

        report = target.build_report(catalog, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["generated_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(report["summary"]["kuji_rows"], 4)
        self.assertEqual(report["summary"]["review_rows"], 3)
        self.assertEqual(report["summary"]["name_structure_review_rows"], 2)
        self.assertEqual(report["summary"]["image_identity_review_rows"], 2)
        self.assertEqual(report["summary"]["same_campaign_image_reused_different_name_rows"], 2)
        self.assertEqual(report["summary"]["multi_item_prize_rank_groups"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        reasons = dict(report["summary"]["review_reason_counts"])
        self.assertEqual(reasons["prize_rank_not_visible_in_prize_item_name"], 1)
        self.assertEqual(reasons["display_name_does_not_match_series_and_prize_name"], 1)
        indexes = {row["catalog_index"] for row in report["review_rows"]}
        self.assertEqual(indexes, {2, 3, 4})
        self.assertEqual(report["review_rows"][0]["manual_fix_template"]["manual_confirmed"], False)
        review_by_index = {row["catalog_index"]: row for row in report["review_rows"]}
        self.assertEqual(review_by_index[2]["expected_prize_display_name"], "B賞 Figure Without Rank")
        self.assertEqual(review_by_index[2]["expected_display_name_ko"], "一番くじ Sample - B賞 Figure Without Rank")
        self.assertIn("variant", report["name_policy"]["fields"]["variant_or_character_detail"])


if __name__ == "__main__":
    unittest.main()
