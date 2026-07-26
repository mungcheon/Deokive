from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_missing_image_variant_sibling_review_public as review


class BuildMissingImageVariantSiblingReviewPublicTest(unittest.TestCase):
    def test_build_report_flags_missing_image_with_imaged_sibling(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "A",
                "category": "인형",
                "character_name": "우사기",
                "source_url": "https://example.test/product",
                "source_store": "공식",
                "series_name": "Series",
                "sub_series": "A상",
                "image_url": "https://example.test/a.jpg",
            },
            {
                "catalog_index": 2,
                "name_ko": "B",
                "category": "인형",
                "character_name": "하치와레",
                "source_url": "https://example.test/product",
                "source_store": "공식",
                "series_name": "Series",
                "sub_series": "A상",
            },
        ]

        report = review.build_report(rows, generated_at="2026-07-27T00:00:00Z")

        self.assertEqual(report["summary"]["review_rows"], 1)
        item = report["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["catalog_index"], 2)
        self.assertEqual(item["review_status"], "sibling_images_different_character_or_variant")
        self.assertEqual(item["imaged_sibling_sample"][0]["catalog_index"], 1)

    def test_build_report_flags_different_product_type_before_character_match(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "category": "마스코트",
                "character_name": "치이카와",
                "source_url": "https://example.test/product",
                "source_store": "공식",
                "series_name": "Series",
                "sub_series": "공식",
                "image_url": "https://example.test/a.jpg",
            },
            {
                "catalog_index": 2,
                "category": "아크릴 키링",
                "character_name": "치이카와",
                "source_url": "https://example.test/product",
                "source_store": "공식",
                "series_name": "Series",
                "sub_series": "공식",
            },
        ]

        report = review.build_report(rows, generated_at="2026-07-27T00:00:00Z")

        self.assertEqual(
            report["items"][0]["review_status"],
            "sibling_images_different_product_type",
        )


if __name__ == "__main__":
    unittest.main()
