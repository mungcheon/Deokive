from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_secondary_official_missing_image_search_public as target


class SecondaryOfficialMissingImageSearchPublicTests(unittest.TestCase):
    def test_build_report_keeps_rows_review_only(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "amiami",
                    "source_store": target.AMIAMI_STORE,
                    "category": "card",
                    "affiliation": "series",
                    "image_url": None,
                },
                {
                    "catalog_index": 2,
                    "name_ko": "sega",
                    "source_store": target.SEGA_STORE,
                    "category": "figure",
                    "affiliation": "series",
                    "image_url": None,
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": target.AMIAMI_STORE,
                    "query": "amiami",
                    "search_url": "https://www.amiami.jp/top/search/list?s_keywords=amiami",
                    "strategy": "manual_official_search_review",
                    "automation_safety": "manual_confirmation_required",
                },
                {
                    "row_index": 2,
                    "source_store": target.SEGA_STORE,
                    "query": "sega",
                    "search_url": "https://segaplaza.jp/search/?word=sega",
                    "strategy": "prize_detail_validation",
                    "automation_safety": "detail_page_validation_required",
                },
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["missing_target_image_rows"], 2)
        self.assertEqual(report["summary"]["matched_queue_rows"], 2)
        self.assertEqual(report["summary"]["official_search_url_rows"], 2)
        self.assertEqual(report["summary"]["by_store"][target.AMIAMI_STORE], 1)
        self.assertEqual(report["summary"]["by_store"][target.SEGA_STORE], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])
        self.assertTrue(all(item["manual_review_required"] for item in report["items"]))


if __name__ == "__main__":
    unittest.main()
