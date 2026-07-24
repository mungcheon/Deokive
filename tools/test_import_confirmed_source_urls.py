from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_confirmed_source_urls as importer


class ImportConfirmedSourceUrlsTests(unittest.TestCase):
    def test_import_replaces_matching_generic_source_url(self) -> None:
        rows = [
            {
                "catalog_index": 2325,
                "name_ko": "스텔라이브 1주년 뱃지 세트",
                "source_store": "Stellive Store",
                "source_url": "https://fanding.kr/@stellive/shop",
            }
        ]

        result = importer.import_confirmed(
            rows,
            [
                {
                    "catalog_index": 2325,
                    "name_ko": "스텔라이브 1주년 뱃지 세트",
                    "manual_confirmed": True,
                    "manual_value": "https://fanding.kr/@stellive/shop/3700",
                    "current_source_url": "https://fanding.kr/@stellive/shop",
                    "evidence_url": "https://fanding.kr/@stellive/shop/3700",
                }
            ],
        )

        self.assertEqual(rows[0]["source_url"], "https://fanding.kr/@stellive/shop/3700")
        self.assertEqual(len(result["changes"]), 1)
        self.assertEqual(result["skipped"], [])

    def test_import_accepts_public_template_items_and_row_index(self) -> None:
        rows = [
            {
                "catalog_index": 99,
                "name_ko": "템플릿 행",
                "source_url": "https://fanding.kr/@stellive/shop",
            }
        ]
        confirmations = importer._confirmation_items(
            {
                "items": [
                    {
                        "row_index": 0,
                        "name_ko": "템플릿 행",
                        "manual_confirmed": True,
                        "manual_value": "https://fanding.kr/@stellive/shop/123",
                        "current_source_url": "https://fanding.kr/@stellive/shop",
                    }
                ]
            }
        )

        result = importer.import_confirmed(rows, confirmations)

        self.assertEqual(rows[0]["source_url"], "https://fanding.kr/@stellive/shop/123")
        self.assertEqual(len(result["changes"]), 1)

    def test_import_rejects_search_or_storefront_url(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "강지 마스코트 인형",
                "source_url": "https://fanding.kr/@stellive/shop",
            }
        ]

        result = importer.import_confirmed(
            rows,
            [
                {
                    "catalog_index": 1,
                    "manual_confirmed": True,
                    "manual_value": "https://fanding.kr/@stellive/shop?keyword=test",
                    "current_source_url": "https://fanding.kr/@stellive/shop",
                }
            ],
        )

        self.assertEqual(rows[0]["source_url"], "https://fanding.kr/@stellive/shop")
        self.assertEqual(result["skipped"][0]["reason"], "source_url_not_product_detail")

    def test_import_rejects_stale_current_source_url_guard(self) -> None:
        rows = [
            {
                "catalog_index": 7,
                "name_ko": "Changed",
                "source_url": "https://example.com/product/current",
            }
        ]

        result = importer.import_confirmed(
            rows,
            [
                {
                    "catalog_index": 7,
                    "manual_confirmed": True,
                    "manual_value": "https://example.com/product/new",
                    "current_source_url": "https://example.com/product/old",
                }
            ],
        )

        self.assertEqual(rows[0]["source_url"], "https://example.com/product/current")
        self.assertEqual(result["skipped"][0]["reason"], "source_url_already_different")

    def test_import_rejects_unconfirmed_template_row(self) -> None:
        rows = [
            {
                "catalog_index": 8,
                "name_ko": "Candidate",
                "source_url": "https://fanding.kr/@stellive/shop",
            }
        ]

        result = importer.import_confirmed(
            rows,
            [
                {
                    "catalog_index": 8,
                    "manual_confirmed": False,
                    "manual_value": "https://fanding.kr/@stellive/shop/3700",
                    "current_source_url": "https://fanding.kr/@stellive/shop",
                }
            ],
        )

        self.assertEqual(rows[0]["source_url"], "https://fanding.kr/@stellive/shop")
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmation_false")


if __name__ == "__main__":
    unittest.main()
