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
                    "search_query": "Stand A Acrylic",
                    "review_state": "official_search_review_required",
                    "workflow": "official_search_url_available",
                    "official_search_url": "https://animate.example/search?q=stand",
                    "allowed_source_domains": ["animate.example"],
                    "manual_review_checklist": ["Confirm exact product page"],
                    "source_patch_template": {"catalog_index": 10},
                    "catalog_field_import_template": {"affiliation": "Series A"},
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
        self.assertEqual(report["summary"]["blocked_rows"], 2)
        self.assertEqual(
            report["summary"]["by_blocked_reason"],
            [["exact_product_detail_source_url_not_confirmed", 2]],
        )
        self.assertIn(
            "source_page_has_verifiable_product_image_before_image_url_import",
            report["summary"]["required_evidence"],
        )
        self.assertEqual(report["summary"]["source_store"], "Animate")
        self.assertEqual(report["summary"]["target_category"], "Acrylic stand")
        self.assertEqual(report["summary"]["official_search_url_count"], 2)
        self.assertEqual(report["summary"]["template_items"], 3)
        self.assertEqual(report["summary"]["pack_queue_preview_count"], 2)
        self.assertEqual(report["summary"]["focus_pack_progress_queue_count"], 2)
        self.assertEqual(report["summary"]["focus_pack_progress_remaining_rows"], 3)
        self.assertEqual(report["summary"]["next_pack_after_current"], "source-discovery-focus-002")
        self.assertEqual(
            [row["focus_pack_id"] for row in report["pack_queue_preview"]],
            ["source-discovery-focus-001", "source-discovery-focus-002"],
        )
        self.assertEqual(
            [row["focus_pack_id"] for row in report["focus_pack_progress_queue"]],
            ["source-discovery-focus-001", "source-discovery-focus-002"],
        )
        self.assertTrue(report["pack_queue_preview"][0]["is_current_pack"])
        self.assertFalse(report["pack_queue_preview"][1]["is_current_pack"])
        self.assertEqual(
            report["pack_queue_preview"][0]["blocked_reason"],
            "exact_product_detail_source_url_not_confirmed",
        )
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual([item["catalog_index"] for item in report["items"]], [10, 11])
        self.assertEqual(report["items"][0]["affiliation"], "Series A")
        self.assertEqual(report["items"][0]["manual_confirmed_source_url"], "")
        self.assertEqual(
            report["items"][0]["blocked_until"],
            "exact_product_detail_source_url_confirmed",
        )
        self.assertEqual(
            report["items"][0]["image_url_blocked_reason"],
            "image_url_requires_verified_exact_source_product_image",
        )
        self.assertEqual(report["items"][0]["search_query"], "Stand A Acrylic")
        self.assertEqual(report["items"][0]["review_state"], "official_search_review_required")
        self.assertEqual(report["items"][0]["workflow"], "official_search_url_available")
        self.assertEqual(report["items"][0]["manual_review_checklist"], ["Confirm exact product page"])
        self.assertEqual(report["items"][0]["source_patch_template"]["catalog_index"], 10)
        self.assertEqual(
            report["items"][0]["source_patch_template"]["blocked_reason"],
            "exact_product_detail_source_url_not_confirmed",
        )
        self.assertEqual(
            report["items"][0]["catalog_field_import_template"]["image_url_blocked_until"],
            "exact_source_page_product_image_confirmed",
        )
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
        self.assertEqual(report["summary"]["pack_queue_preview_count"], 1)
        self.assertEqual(report["summary"]["focus_pack_progress_queue_count"], 1)
        self.assertEqual(report["summary"]["focus_pack_progress_remaining_rows"], 1)
        self.assertIsNone(report["summary"]["next_pack_after_current"])
        self.assertEqual(report["pack_queue_preview"][0]["focus_pack_id"], "source-discovery-focus-002")
        self.assertEqual(report["focus_pack_progress_queue"][0]["focus_pack_id"], "source-discovery-focus-002")
        self.assertEqual([item["catalog_index"] for item in report["items"]], [12])


if __name__ == "__main__":
    unittest.main()
