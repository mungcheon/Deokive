from __future__ import annotations

import unittest

from tools.build_catalog_reused_image_review_public import build_report


class BuildCatalogReusedImageReviewPublicTest(unittest.TestCase):
    def test_cross_affiliation_shared_image_is_high_risk(self) -> None:
        report = build_report(
            [
                {
                    "catalog_index": 1,
                    "name_ko": "A 피규어",
                    "affiliation": "A작품",
                    "category": "피규어",
                    "character_name": "A",
                    "image_url": "https://example.com/shared.jpg",
                    "local_image_path": "assets/catalog_images/shared.webp",
                    "source_url": "https://example.com/a",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "B 피규어",
                    "affiliation": "B작품",
                    "category": "피규어",
                    "character_name": "B",
                    "image_url": "https://example.com/shared.jpg",
                    "local_image_path": "assets/catalog_images/shared.webp",
                    "source_url": "https://example.com/b",
                },
            ],
            generated_at="2026-07-26T00:00:00Z",
        )

        self.assertEqual(report["summary"]["high_risk_groups"], 1)
        self.assertEqual(report["groups"][0]["risk"], "high")
        self.assertIn("shared_across_multiple_affiliations", report["groups"][0]["reasons"])

    def test_lineup_like_same_affiliation_group_is_low_risk(self) -> None:
        report = build_report(
            [
                {
                    "catalog_index": 1,
                    "name_ko": "트레이딩 캔뱃지 A",
                    "affiliation": "A작품",
                    "category": "캔뱃지",
                    "character_name": "A",
                    "image_url": "https://example.com/lineup.jpg",
                    "local_image_path": "assets/catalog_images/lineup.webp",
                    "source_url": "https://example.com/lineup",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "트레이딩 캔뱃지 B",
                    "affiliation": "A작품",
                    "category": "캔뱃지",
                    "character_name": "B",
                    "image_url": "https://example.com/lineup.jpg",
                    "local_image_path": "assets/catalog_images/lineup.webp",
                    "source_url": "https://example.com/lineup",
                },
            ],
            generated_at="2026-07-26T00:00:00Z",
        )

        self.assertEqual(report["summary"]["low_risk_groups"], 1)
        self.assertEqual(report["groups"][0]["risk"], "low")
        self.assertIn("lineup_or_trading_image_possible", report["groups"][0]["reasons"])


if __name__ == "__main__":
    unittest.main()
