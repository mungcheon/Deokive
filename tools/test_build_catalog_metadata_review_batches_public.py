from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_catalog_metadata_review_batches_public as batches


class BuildCatalogMetadataReviewBatchesPublicTest(unittest.TestCase):
    def test_build_report_groups_all_missing_metadata_by_field_and_store(self) -> None:
        items = [
            {
                "catalog_index": 1,
                "name_ko": "A",
                "name_ja": "",
                "source_store": "스토어A",
                "source_url": "",
                "image_url": "",
                "release_date": "",
                "official_price_jpy": "",
                "barcode": "",
            },
            {
                "catalog_index": 2,
                "name_ko": "B",
                "name_ja": "B ja",
                "source_store": "스토어A",
                "source_url": "https://example.test/b",
                "image_url": "https://example.test/b.jpg",
                "release_date": "2026-01",
                "official_price_jpy": 1000,
                "barcode": "",
            },
            {
                "catalog_index": 3,
                "name_ko": "C",
                "name_ja": "",
                "source_store": "스토어B",
                "source_url": "https://example.test/c",
                "image_url": "https://example.test/c.jpg",
                "release_date": "2026-01",
                "official_price_jpy": 1000,
                "barcode": "123",
            },
        ]

        report = batches.build_report(items, batch_size=2)

        self.assertEqual(report["summary"]["catalog_rows"], 3)
        self.assertEqual(report["summary"]["field_missing_totals"]["name_ja"], 2)
        self.assertEqual(report["summary"]["field_missing_totals"]["barcode"], 2)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_metadata"])
        self.assertGreater(report["summary"]["batch_count"], 0)
        first_group = report["batches"][0]["groups"][0]
        self.assertEqual(first_group["field"], "source_url")
        self.assertEqual(first_group["workflow"], "source_url_discovery")
        self.assertTrue(all(group["auto_apply_enabled"] is False for batch in report["batches"] for group in batch["groups"]))


if __name__ == "__main__":
    unittest.main()
