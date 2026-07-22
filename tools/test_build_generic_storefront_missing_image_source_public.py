from __future__ import annotations

import unittest

from build_generic_storefront_missing_image_source_public import (
    BLOCKED_UNTIL,
    build_report,
)


class GenericStorefrontMissingImageSourceTests(unittest.TestCase):
    def test_build_report_keeps_generic_storefront_rows_manual_only(self):
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "피카츄 봉제 인형",
                    "name_ja": "ピカチュウ ぬいぐるみ",
                    "source_store": "Pokemon Center",
                    "source_url": "https://www.pokemoncenter-online.com/",
                    "affiliation": "Pokemon",
                    "category": "봉제 인형",
                    "image_url": "",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "이미지 있음",
                    "source_store": "Weverse Shop",
                    "source_url": "https://shop.weverse.io/home",
                    "image_url": "https://example.com/image.jpg",
                },
                {
                    "catalog_index": 3,
                    "name_ko": "공식 검색 대상",
                    "source_store": "AmiAmi",
                    "image_url": "",
                },
                {
                    "catalog_index": 4,
                    "name_ko": "전용 리포트 있음",
                    "source_store": "Stellive Store",
                    "source_url": "https://fanding.kr/@stellive/shop",
                    "image_url": "",
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "query": "ピカチュウ ぬいぐるみ",
                    "strategy": "source_url_generic_storefront",
                    "automation_safety": "blocked_until_exact_product_url",
                },
                {
                    "row_index": 2,
                    "strategy": "source_url_generic_storefront",
                    "automation_safety": "blocked_until_exact_product_url",
                },
                {
                    "row_index": 3,
                    "strategy": "official_search",
                    "automation_safety": "manual_research_required",
                },
                {
                    "row_index": 4,
                    "strategy": "source_url_generic_storefront",
                    "automation_safety": "blocked_until_exact_product_url",
                },
            ]
        }

        report = build_report(catalog, queue, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["summary"]["generic_storefront_rows"], 1)
        self.assertIs(report["summary"]["auto_apply_enabled"], False)
        self.assertEqual(report["items"][0]["catalog_index"], 1)
        self.assertTrue(report["items"][0]["manual_review_required"])
        self.assertEqual(
            report["items"][0]["source_discovery_template"]["blocked_until"],
            BLOCKED_UNTIL,
        )
        self.assertIs(report["automation_policy"]["auto_apply_catalog_changes"], False)


if __name__ == "__main__":
    unittest.main()
