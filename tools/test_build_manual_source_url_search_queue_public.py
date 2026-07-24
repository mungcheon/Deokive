from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_manual_source_url_search_queue_public as queue


class BuildManualSourceUrlSearchQueuePublicTest(unittest.TestCase):
    def test_build_queue_keeps_only_manual_search_required_rows(self) -> None:
        template = {
            "items": [
                {
                    "row_index": 10,
                    "catalog_index": 10,
                    "source_store": "Stellive Store",
                    "name_ko": "Mascot plush",
                    "category": "인형",
                    "current_source_url": "https://fanding.kr/@stellive/shop",
                    "source_url_review_lane": "manual_search_required",
                    "source_url_review_blockers": ["no_exact_product_candidate"],
                    "manual_confirmation_requirements": ["confirm exact product"],
                    "store_search_hints": {
                        "storefront_url": "https://fanding.kr/@stellive/shop",
                        "store_search_url": "https://fanding.kr/@stellive/shop/search?keyword=Mascot",
                        "site_query": "site:fanding.kr/@stellive/shop",
                    },
                    "fallback_search_queries": ['site:fanding.kr/@stellive/shop "Mascot plush"'],
                    "batch_id": "image-attachment-action-001",
                },
                {
                    "row_index": 11,
                    "catalog_index": 11,
                    "source_store": "Weverse Shop",
                    "name_ko": "Photocard",
                    "category": "포토카드",
                    "source_url_review_lane": "candidate_provider_missing",
                },
                {
                    "row_index": 12,
                    "catalog_index": 12,
                    "source_store": "Stellive Store",
                    "name_ko": "Badge",
                    "category": "캔뱃지",
                    "source_url_review_lane": "weak_candidate_review",
                },
            ]
        }

        report = queue.build_queue(template, generated_at="2026-07-23T00:00:00Z")

        self.assertEqual(report["generated_at"], "2026-07-23T00:00:00Z")
        self.assertEqual(report["summary"]["manual_search_required_rows"], 1)
        self.assertEqual(report["summary"]["workstream_count"], 1)
        self.assertEqual(report["summary"]["by_source_store"], [["Stellive Store", 1]])
        self.assertEqual(report["summary"]["by_category"], [["인형", 1]])
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["review_readiness"]["status"], "manual_search_required")
        self.assertEqual(report["review_readiness"]["auto_apply_ready_rows"], 0)
        self.assertEqual(report["review_readiness"]["manual_review_rows"], 1)
        self.assertEqual(report["review_readiness"]["rows_with_store_search_url"], 1)
        self.assertEqual(report["review_readiness"]["rows_with_site_query"], 1)
        self.assertEqual(
            report["review_readiness"]["next_review_row"]["catalog_index"],
            10,
        )
        self.assertEqual(
            report["review_readiness"]["blocked_until"],
            "manual_exact_product_source_url_found",
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
        self.assertEqual(item["catalog_index"], 10)
        self.assertEqual(item["priority_bucket"], "인형")
        self.assertEqual(item["source_url_import_template"]["field"], "source_url")
        self.assertFalse(item["source_url_import_template"]["manual_confirmed"])
        self.assertEqual(item["source_url_import_template"]["manual_value"], "")
        self.assertIn("no_exact_product_candidate", item["review_blockers"])

        workstream = report["workstreams"][0]
        self.assertEqual(workstream["category"], "인형")
        self.assertEqual(workstream["row_count"], 1)
        self.assertEqual(workstream["sample_rows"][0]["catalog_index"], 10)
        self.assertFalse(workstream["auto_apply_enabled"])

    def test_empty_template_builds_empty_review_queue(self) -> None:
        report = queue.build_queue({"items": []})

        self.assertEqual(report["summary"]["manual_search_required_rows"], 0)
        self.assertEqual(report["review_readiness"]["status"], "empty")
        self.assertEqual(report["review_readiness"]["manual_review_rows"], 0)
        self.assertEqual(report["workstreams"], [])
        self.assertEqual(report["items"], [])


if __name__ == "__main__":
    unittest.main()
