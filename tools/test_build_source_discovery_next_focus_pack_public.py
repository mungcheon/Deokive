from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_pack_public as builder


class BuildSourceDiscoveryNextFocusPackPublicTest(unittest.TestCase):
    def test_build_report_publishes_only_next_focus_pack_items(self) -> None:
        template = {
            "summary": {
                "template_items": 3,
                "work_order_pack_count": 2,
                "next_focus_pack_id": "source-discovery-focus-001",
            },
            "work_order": [
                {
                    "priority": 1,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "row_count": 2,
                    "review_status": "not_started",
                    "remaining_review_rows": 2,
                    "target_category": "Acrylic stand",
                    "first_official_search_url": "https://animate.example/search?q=stand",
                },
                {
                    "priority": 2,
                    "focus_pack_id": "source-discovery-focus-002",
                    "source_store": "Animate",
                    "row_count": 1,
                    "review_status": "not_started",
                    "remaining_review_rows": 1,
                    "target_category": "Badge",
                },
            ],
            "items": [
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "pack_sequence": 1,
                    "row_index": 10,
                    "catalog_index": 10,
                    "source_store": "Animate",
                    "category": "Acrylic stand",
                    "name_ko": "Stand A",
                    "name_ja": "スタンドA",
                    "official_search_url": "https://animate.example/search?q=stand",
                    "allowed_source_domains": ["animate.example"],
                    "source_patch_template": {"catalog_index": 10},
                },
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "pack_sequence": 1,
                    "row_index": 11,
                    "catalog_index": 11,
                    "source_store": "Animate",
                    "category": "Acrylic stand",
                    "name_ko": "Stand B",
                    "official_search_url": "https://animate.example/search?q=stand-b",
                },
                {
                    "focus_pack_id": "source-discovery-focus-002",
                    "row_index": 12,
                    "catalog_index": 12,
                    "source_store": "Animate",
                    "category": "Badge",
                    "name_ko": "Badge",
                },
            ],
        }

        report = builder.build_report(template, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(report["summary"]["focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(report["summary"]["pack_items"], 2)
        self.assertEqual(report["summary"]["confirmed_source_rows"], 0)
        self.assertEqual(report["summary"]["remaining_review_rows"], 2)
        self.assertEqual(report["summary"]["source_store"], "Animate")
        self.assertEqual(report["summary"]["target_category"], "Acrylic stand")
        self.assertEqual(report["summary"]["official_search_url_count"], 2)
        self.assertEqual(report["summary"]["template_items"], 3)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual([item["catalog_index"] for item in report["items"]], [10, 11])
        self.assertEqual(report["items"][0]["manual_confirmed_source_url"], "")
        self.assertEqual(report["items"][0]["source_patch_template"]["catalog_index"], 10)
        self.assertFalse(report["automation_policy"]["auto_apply_source_url"])

    def test_build_report_advances_after_current_pack_is_confirmed(self) -> None:
        template = {
            "summary": {"template_items": 3, "work_order_pack_count": 2},
            "work_order": [
                {
                    "priority": 1,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "row_count": 2,
                    "review_status": "not_started",
                    "remaining_review_rows": 2,
                    "target_category": "Acrylic stand",
                },
                {
                    "priority": 2,
                    "focus_pack_id": "source-discovery-focus-002",
                    "source_store": "Animate",
                    "row_count": 1,
                    "review_status": "not_started",
                    "remaining_review_rows": 1,
                    "target_category": "Badge",
                },
            ],
            "items": [
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "catalog_index": 10,
                    "manual_review_status": "source_confirmed",
                },
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "catalog_index": 11,
                    "manual_review_status": "source_and_image_confirmed",
                },
                {
                    "focus_pack_id": "source-discovery-focus-002",
                    "catalog_index": 12,
                    "manual_review_status": "not_started",
                    "source_store": "Animate",
                    "category": "Badge",
                    "name_ko": "Badge",
                },
            ],
        }

        report = builder.build_report(template, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["summary"]["focus_pack_id"], "source-discovery-focus-002")
        self.assertEqual(report["summary"]["pack_priority"], 2)
        self.assertEqual(report["summary"]["pack_items"], 1)
        self.assertEqual(report["summary"]["confirmed_source_rows"], 0)
        self.assertEqual(report["summary"]["remaining_review_rows"], 1)
        self.assertEqual([item["catalog_index"] for item in report["items"]], [12])


if __name__ == "__main__":
    unittest.main()
