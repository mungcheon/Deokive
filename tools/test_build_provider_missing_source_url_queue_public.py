from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_provider_missing_source_url_queue_public as queue


class BuildProviderMissingSourceUrlQueuePublicTest(unittest.TestCase):
    def test_build_queue_keeps_only_provider_missing_rows(self) -> None:
        template = {
            "items": [
                {
                    "row_index": 1,
                    "catalog_index": 1,
                    "source_store": "Weverse Shop",
                    "name_ko": "SEVENTEEN photocard",
                    "category": "photocard",
                    "current_source_url": "https://shop.weverse.io/home",
                    "source_url_review_lane": "candidate_provider_missing",
                    "source_url_review_blockers": ["no_candidate_provider_result"],
                    "manual_confirmation_requirements": ["confirm exact product"],
                    "store_search_hints": {
                        "storefront_url": "https://shop.weverse.io/home",
                        "store_search_url": "https://shop.weverse.io/search?keyword=SEVENTEEN",
                        "site_query": "site:shop.weverse.io",
                    },
                    "fallback_search_queries": ['site:shop.weverse.io "SEVENTEEN photocard"'],
                    "batch_id": "image-attachment-action-001",
                },
                {
                    "row_index": 2,
                    "catalog_index": 2,
                    "source_store": "Stellive Store",
                    "name_ko": "Badge",
                    "category": "badge",
                    "source_url_review_lane": "weak_candidate_review",
                },
            ]
        }

        report = queue.build_queue(template, generated_at="2026-07-23T00:00:00Z")

        self.assertEqual(report["generated_at"], "2026-07-23T00:00:00Z")
        self.assertEqual(report["summary"]["provider_missing_rows"], 1)
        self.assertEqual(report["summary"]["workstream_count"], 1)
        self.assertEqual(report["summary"]["by_source_store"], [["Weverse Shop", 1]])
        self.assertEqual(report["summary"]["by_category"], [["photocard", 1]])
        self.assertEqual(report["summary"]["with_store_search_url"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(
            report["review_readiness"]["status"],
            "provider_or_manual_refresh_required",
        )
        self.assertEqual(report["review_readiness"]["auto_apply_ready_rows"], 0)
        self.assertEqual(report["review_readiness"]["manual_review_rows"], 1)
        self.assertEqual(report["review_readiness"]["rows_with_store_search_url"], 1)
        self.assertEqual(report["review_readiness"]["rows_with_site_query"], 1)
        self.assertEqual(
            report["review_readiness"]["next_review_row"]["catalog_index"],
            1,
        )
        self.assertEqual(
            report["review_readiness"]["blocked_until"],
            "provider_refreshed_or_manual_exact_source_url_found",
        )
        self.assertFalse(report["automation_policy"]["auto_apply_source_url"])
        self.assertEqual(
            report["automation_policy"]["import_tool"],
            "tools/import_confirmed_source_urls.py",
        )
        self.assertIn(
            "tools/import_confirmed_source_urls.py",
            report["instructions"][3],
        )

        item = report["items"][0]
        self.assertEqual(item["catalog_index"], 1)
        self.assertEqual(item["store_search_url"], "https://shop.weverse.io/search?keyword=SEVENTEEN")
        self.assertEqual(item["site_query"], "site:shop.weverse.io")
        self.assertEqual(item["source_url_import_template"]["field"], "source_url")
        self.assertFalse(item["source_url_import_template"]["manual_confirmed"])
        self.assertEqual(item["source_url_import_template"]["manual_value"], "")
        self.assertIn("no_candidate_provider_result", item["review_blockers"])

        workstream = report["workstreams"][0]
        self.assertEqual(workstream["source_store"], "Weverse Shop")
        self.assertEqual(workstream["row_count"], 1)
        self.assertEqual(workstream["rows"][0]["catalog_index"], 1)
        self.assertFalse(workstream["auto_apply_enabled"])

    def test_empty_template_builds_empty_review_queue(self) -> None:
        report = queue.build_queue({"items": []})

        self.assertEqual(report["summary"]["provider_missing_rows"], 0)
        self.assertEqual(report["review_readiness"]["status"], "empty")
        self.assertEqual(report["review_readiness"]["manual_review_rows"], 0)
        self.assertEqual(report["workstreams"], [])
        self.assertEqual(report["items"], [])


if __name__ == "__main__":
    unittest.main()
