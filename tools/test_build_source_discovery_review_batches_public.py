from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_review_batches_public as batches


class BuildSourceDiscoveryReviewBatchesPublicTest(unittest.TestCase):
    def test_build_report_batches_all_missing_source_rows_without_auto_apply(self) -> None:
        items = [
            {
                "catalog_index": 1,
                "name_ko": "주술회전 캔뱃지",
                "source_store": "애니메이트",
                "category": "캔뱃지",
                "source_url": None,
            },
            {
                "catalog_index": 2,
                "name_ko": "하츠네 미쿠 피규어",
                "source_store": "AmiAmi",
                "category": "피규어",
                "source_url": "",
            },
            {
                "catalog_index": 3,
                "name_ko": "출처 있음",
                "source_store": "애니메이트",
                "category": "기타",
                "source_url": "https://example.test/item",
            },
        ]

        report = batches.build_report(items, batch_size=1)

        self.assertEqual(report["summary"]["source_discovery_rows"], 2)
        self.assertEqual(report["summary"]["batch_count"], 2)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_source_url"])
        self.assertFalse(report["automation_policy"]["auto_apply_image_url"])
        self.assertEqual(report["batches"][0]["workflow"], "official_search_url_available")
        self.assertEqual(report["batches"][0]["items"][0]["catalog_index"], 1)
        self.assertIn("www.animate-onlineshop.jp", report["batches"][0]["allowed_source_domains"])
        self.assertEqual(report["batches"][1]["workflow"], "licensed_retailer_search_review")
        self.assertTrue(all(batch["auto_apply_enabled"] is False for batch in report["batches"]))


if __name__ == "__main__":
    unittest.main()
