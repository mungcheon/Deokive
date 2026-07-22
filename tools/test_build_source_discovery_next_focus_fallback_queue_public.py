from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_fallback_queue_public as target


class SourceDiscoveryNextFocusFallbackQueuePublicTest(unittest.TestCase):
    def test_build_report_keeps_only_fallback_required_rows(self) -> None:
        next_pack = {
            "summary": {"focus_pack_id": "source-discovery-focus-001"},
            "items": [
                {
                    "catalog_index": 1,
                    "focus_pack_id": "source-discovery-focus-001",
                    "pack_sequence": 1,
                    "source_store": "Animate",
                    "category": "Acrylic stand",
                    "name_ko": "A",
                    "name_ja": "A",
                    "search_query": "A acrylic",
                    "review_state": "official_search_review_required",
                    "workflow": "official_search_url_available",
                    "official_search_url": "https://animate.example/products/list.php?mode=search&smt=A",
                    "web_search_url": "https://google.example/search?q=A",
                    "allowed_source_domains": ["www.animate-onlineshop.jp"],
                    "manual_review_checklist": ["Confirm exact product page"],
                    "acceptance_rule": "exact match",
                    "source_patch_template": {"catalog_index": 1, "source_url": "<exact>"},
                    "catalog_field_import_template": {"row_index": 1, "field": "source_url"},
                },
                {
                    "catalog_index": 2,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "category": "Badge",
                    "name_ko": "B",
                    "official_search_url": "https://animate.example/products/list.php?mode=search&smt=B",
                },
            ],
        }
        fetch_audit = {
            "items": [
                {
                    "catalog_index": 1,
                    "needs_fallback_web_search": True,
                    "fetch_status": "http_error",
                    "http_status": 404,
                },
                {
                    "catalog_index": 2,
                    "needs_fallback_web_search": False,
                    "fetch_status": "ok",
                    "http_status": 200,
                },
            ]
        }

        report = target.build_report(next_pack, fetch_audit, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["queue_rows"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_rows"], 0)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["by_http_status"], [("404", 1)])
        self.assertEqual(report["summary"]["fallback_query_count"], 3)
        self.assertEqual(report["summary"]["domain_limited_web_search_url_count"], 3)
        item = report["items"][0]
        self.assertEqual(item["catalog_index"], 1)
        self.assertEqual(item["manual_review_status"], "fallback_not_started")
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["search_query"], "A acrylic")
        self.assertEqual(item["review_state"], "official_search_review_required")
        self.assertEqual(item["workflow"], "official_search_url_available")
        self.assertEqual(item["manual_review_checklist"], ["Confirm exact product page"])
        self.assertIn("sphone/products/list.php", item["fallback_store_search_url"])
        self.assertEqual(item["fallback_search_terms"], ["A"])
        self.assertEqual(len(item["fallback_search_queries"]), 3)
        self.assertTrue(
            item["fallback_search_queries"][0]["query"].startswith(
                'site:www.animate-onlineshop.jp/pn/ "A"'
            )
        )
        self.assertIn("site%3Awww.animate-onlineshop.jp", item["domain_limited_web_search_urls"][0])
        self.assertEqual(item["source_patch_template"]["catalog_index"], 1)
        self.assertEqual(item["catalog_field_import_template"]["field"], "source_url")


if __name__ == "__main__":
    unittest.main()
