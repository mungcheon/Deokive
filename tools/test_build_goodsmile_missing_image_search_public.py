from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_goodsmile_missing_image_search_public as target


class GoodSmileMissingImageSearchPublicTests(unittest.TestCase):
    def test_build_report_keeps_search_rows_review_only(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "sample",
                    "name_ja": "Nendoroid sample",
                    "source_store": target.GOODSMILE_STORE,
                    "category": "figure",
                    "affiliation": "series",
                    "image_url": None,
                },
                {
                    "catalog_index": 2,
                    "name_ko": "has image",
                    "source_store": target.GOODSMILE_STORE,
                    "image_url": "https://example.com/2.jpg",
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": target.GOODSMILE_STORE,
                    "query": "sample ja",
                    "search_url": "https://www.goodsmile.info/ja/products/search?utf8=x&search%5Bquery%5D=sample",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                }
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["missing_goodsmile_image_rows"], 1)
        self.assertEqual(report["summary"]["matched_queue_rows"], 1)
        self.assertEqual(report["summary"]["official_search_url_rows"], 1)
        self.assertEqual(report["summary"]["reviewable_search_url_rows"], 1)
        self.assertEqual(report["summary"]["source_research_required_rows"], 0)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])
        self.assertEqual(report["items"][0]["import_template"]["blocked_until"], "exact_goodsmile_product_page_confirmed")
        self.assertEqual(report["items"][0]["research_status"], "reviewable_search_url")
        self.assertTrue(report["items"][0]["manual_review_required"])

    def test_build_report_separates_rows_requiring_source_research(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 10,
                    "name_ko": "랜덤 특전",
                    "source_store": target.GOODSMILE_STORE,
                    "category": "figure",
                    "affiliation": "series",
                    "image_url": None,
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 10,
                    "source_store": target.GOODSMILE_STORE,
                    "query": "랜덤 특전",
                    "search_url": "",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                }
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["reviewable_search_url_rows"], 0)
        self.assertEqual(report["summary"]["source_research_required_rows"], 1)
        self.assertEqual(report["items"][0]["research_status"], "needs_official_language_name")
        self.assertEqual(report["source_research_required"]["row_count"], 1)
        self.assertEqual(
            report["source_research_required"]["items"][0]["import_template"]["blocked_until"],
            "official_goodsmile_query_or_exact_product_page_confirmed",
        )

    def test_build_fallback_queue_from_catalog_when_work_queue_is_absent(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 7,
                    "name_ko": "샘플",
                    "name_ja": "Nendoroid Sample",
                    "source_store": target.GOODSMILE_STORE,
                    "image_url": None,
                }
            ]
        }

        queue = target.build_fallback_queue(catalog)

        self.assertEqual(queue["items"][0]["row_index"], 7)
        self.assertEqual(queue["items"][0]["strategy"], "official_search")
        self.assertIn("Nendoroid%20Sample", queue["items"][0]["search_url"])


if __name__ == "__main__":
    unittest.main()
