from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_prize_name_image_patch_candidates_public as candidates


class BuildIchibanPrizeNameImagePatchCandidatesPublicTest(unittest.TestCase):
    def test_exact_image_match_builds_manual_patch_candidate(self) -> None:
        review = {
            "review_rows": [
                {
                    "catalog_index": 1,
                    "series_name": "一番くじ Demo",
                    "prize_rank": "A賞",
                    "prize_item_name": "フィギュア",
                    "display_name_ko": "一番くじ Demo - フィギュア",
                    "source_url": "https://1kuji.com/products/demo",
                    "image_url": "https://assets.1kuji.com/demo/a.jpg",
                }
            ]
        }

        def fetch_campaign(url: str):
            self.assertEqual(url, "https://1kuji.com/products/demo")
            return [
                {
                    "name_ja": "A賞 フィギュア",
                    "sub_series": "A賞",
                    "image_url": "https://assets.1kuji.com/demo/a.jpg",
                }
            ]

        report = candidates.build_report(review, fetch_campaign=fetch_campaign)

        self.assertEqual(report["summary"]["candidate_rows"], 1)
        self.assertEqual(report["summary"]["exact_image_match_rows"], 1)
        row = report["candidates"][0]
        self.assertFalse(row["auto_apply_enabled"])
        self.assertEqual(row["match_type"], "exact_image_match")
        self.assertEqual(row["field_changes"]["name_ja"]["to"], "A賞 フィギュア")
        self.assertEqual(row["official_prize_display_name"], "A賞 フィギュア")
        self.assertEqual(row["suggested_display_name_ko"], "一番くじ Demo - A賞 フィギュア")
        self.assertEqual(row["catalog_patch_template"]["name_ko"], "一番くじ Demo - A賞 フィギュア")
        self.assertFalse(row["catalog_patch_template"]["manual_confirmed"])

    def test_display_name_includes_rank_when_official_name_omits_it(self) -> None:
        review = {
            "review_rows": [
                {
                    "catalog_index": 3,
                    "series_name": "一番くじ Demo",
                    "prize_rank": "C賞",
                    "prize_item_name": "アクリルチャーム",
                    "display_name_ko": "一番くじ Demo - アクリルチャーム",
                    "source_url": "https://1kuji.com/products/demo",
                    "image_url": "https://assets.1kuji.com/demo/c.jpg",
                }
            ]
        }

        report = candidates.build_report(
            review,
            fetch_campaign=lambda _url: [
                {
                    "name_ja": "アクリルチャーム",
                    "sub_series": "C賞",
                    "image_url": "https://assets.1kuji.com/demo/c.jpg",
                }
            ],
        )

        row = report["candidates"][0]
        self.assertEqual(row["official_prize_display_name"], "C賞 アクリルチャーム")
        self.assertEqual(row["suggested_display_name_ko"], "一番くじ Demo - C賞 アクリルチャーム")
        self.assertEqual(row["catalog_patch_template"]["name_ko"], "一番くじ Demo - C賞 アクリルチャーム")

    def test_uncertain_rows_are_blocked_without_patch(self) -> None:
        review = {
            "review_rows": [
                {
                    "catalog_index": 2,
                    "series_name": "一番くじ Demo",
                    "prize_rank": "B賞",
                    "prize_item_name": "タオル",
                    "display_name_ko": "一番くじ Demo - タオル",
                    "source_url": "https://1kuji.com/products/demo",
                    "image_url": "https://assets.1kuji.com/demo/missing.jpg",
                }
            ]
        }

        report = candidates.build_report(
            review,
            fetch_campaign=lambda _url: [
                {
                    "name_ja": "A賞 フィギュア",
                    "sub_series": "A賞",
                    "image_url": "https://assets.1kuji.com/demo/a.jpg",
                }
            ],
        )

        self.assertEqual(report["summary"]["candidate_rows"], 0)
        self.assertEqual(report["summary"]["blocked_rows"], 1)
        self.assertEqual(report["blocked_rows"][0]["reason"], "no_safe_official_name_or_image_match")


if __name__ == "__main__":
    unittest.main()
