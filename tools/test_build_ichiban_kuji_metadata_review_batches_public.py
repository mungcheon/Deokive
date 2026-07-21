from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_kuji_metadata_review_batches_public as batches


class BuildIchibanKujiMetadataReviewBatchesPublicTest(unittest.TestCase):
    def test_build_report_batches_campaign_metadata_without_auto_apply(self) -> None:
        source = {
            "summary": {
                "missing_release_date_rows": 8,
                "missing_official_price_jpy_rows": 13,
            }
        }
        queue = [
            {
                "group_key": "https://1kuji.com/products/a",
                "url": "https://1kuji.com/products/a",
                "slug": "a",
                "title": "A",
                "catalog_item_rows": 8,
                "missing_fields": ["release_date"],
                "review_priority": 10,
                "source_evidence_required": "official_1kuji_campaign_page",
                "sample_catalog_indexes": [1],
                "sample_names": ["A賞"],
            },
            {
                "group_key": "https://1kuji.com/products/b",
                "url": "https://1kuji.com/products/b",
                "slug": "b",
                "title": "B",
                "catalog_item_rows": 13,
                "missing_fields": ["official_price_jpy"],
                "review_priority": 20,
                "source_evidence_required": "official_1kuji_campaign_page",
                "sample_catalog_indexes": [2],
                "sample_names": ["B賞"],
            },
        ]

        report = batches.build_report(source, queue, batch_size=1)

        self.assertEqual(report["summary"]["source_campaigns"], 2)
        self.assertEqual(report["summary"]["batch_count"], 2)
        self.assertEqual(report["summary"]["missing_release_date_rows"], 8)
        self.assertEqual(report["summary"]["missing_official_price_jpy_rows"], 13)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_release_date"])
        self.assertFalse(report["automation_policy"]["auto_apply_official_price_jpy"])
        self.assertEqual(report["batches"][0]["campaigns"][0]["workflow"], "release_date_review")
        self.assertEqual(report["batches"][1]["campaigns"][0]["workflow"], "price_review")


if __name__ == "__main__":
    unittest.main()
