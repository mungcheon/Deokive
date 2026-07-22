from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_kotobukiya_movic_missing_image_search_public as target


class KotobukiyaMovicMissingImageSearchPublicTests(unittest.TestCase):
    def test_build_report_keeps_target_store_rows_review_only(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "koto",
                    "source_store": target.KOTOBUKIYA_STORE,
                    "category": "figure",
                    "affiliation": "series",
                    "image_url": None,
                },
                {
                    "catalog_index": 2,
                    "name_ko": "movic",
                    "source_store": target.MOVIC_STORE,
                    "category": "badge",
                    "affiliation": "series",
                    "image_url": None,
                },
                {
                    "catalog_index": 3,
                    "name_ko": "ignored",
                    "source_store": target.MOVIC_STORE,
                    "image_url": "https://example.com/3.jpg",
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": target.KOTOBUKIYA_STORE,
                    "query": "koto",
                    "search_url": "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?keyword=koto",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                },
                {
                    "row_index": 2,
                    "source_store": target.MOVIC_STORE,
                    "query": "movic",
                    "search_url": "https://www.movic.jp/shop/goods/search.aspx?keyword=movic",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                },
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["missing_target_image_rows"], 2)
        self.assertEqual(report["summary"]["matched_queue_rows"], 2)
        self.assertEqual(report["summary"]["official_search_url_rows"], 2)
        self.assertEqual(report["summary"]["by_store"][target.KOTOBUKIYA_STORE], 1)
        self.assertEqual(report["summary"]["by_store"][target.MOVIC_STORE], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])
        self.assertTrue(all(item["manual_review_required"] for item in report["items"]))


if __name__ == "__main__":
    unittest.main()
