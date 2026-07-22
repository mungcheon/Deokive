from __future__ import annotations

import unittest

from tools.build_public_catalog_integrity_report import build_report


class PublicCatalogIntegrityReportTests(unittest.TestCase):
    def test_counts_display_image_from_local_path(self) -> None:
        report = build_report(
            [
                {"catalog_index": 1, "name_ko": "A", "local_image_path": "assets/catalog_images/a.webp"},
                {"catalog_index": 2, "name_ko": "B", "image_url": "https://example.com/b.webp"},
                {"catalog_index": 3, "name_ko": "C"},
            ],
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["summary"]["row_count"], 3)
        self.assertEqual(report["summary"]["display_image_missing_rows"], 1)

    def test_flags_duplicate_review_groups_without_deleting(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "Same Goods",
                "source_store": "Store",
                "source_url": "https://example.com/shop",
            },
            {
                "catalog_index": 2,
                "name_ko": "Same  Goods",
                "source_store": "Store",
                "source_url": "https://example.com/shop/",
            },
        ]

        report = build_report(rows, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["summary"]["duplicate_review_needed_groups"], 1)
        self.assertFalse(report["summary"]["auto_delete_enabled"])

    def test_flags_kuji_last_one_nonzero_price(self) -> None:
        report = build_report(
            [
                {
                    "catalog_index": 1,
                    "name_ja": "ラストワン賞 フィギュア",
                    "source_url": "https://1kuji.com/products/example",
                    "official_price_jpy": 790,
                },
                {
                    "catalog_index": 2,
                    "name_ja": "ダブルチャンスキャンペーン",
                    "source_url": "https://1kuji.com/products/example",
                    "official_price_jpy": 0,
                },
            ],
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["summary"]["kuji_last_or_double_chance_price_violations"], 1)
        self.assertFalse(report["summary"]["auto_price_mutation_enabled"])


if __name__ == "__main__":
    unittest.main()
