from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_focus_confirmed_template_public as builder


class BuildSourceDiscoveryFocusConfirmedTemplatePublicTest(unittest.TestCase):
    def test_build_template_publishes_empty_manual_confirmation_rows(self) -> None:
        focus_packs = {
            "packs": [
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "pack_sequence": 1,
                    "row_count": 1,
                    "source_store_total_rows": 5,
                    "source_store_remaining_after_pack": 4,
                    "review_status": "not_started",
                    "remaining_review_rows": 1,
                    "target_category": "Acrylic",
                    "batch_ids": ["source-discovery-action-001"],
                    "first_official_search_url": "https://animate.example/search?q=stand",
                    "allowed_source_domains": [{"domain": "animate.example", "rows": 1}],
                    "items": [
                        {
                            "catalog_index": 10,
                            "source_store": "Animate",
                            "category": "Acrylic",
                            "name_ko": "Stand",
                            "search_query": "Stand Acrylic",
                            "review_state": "official_search_review_required",
                            "workflow": "official_search_url_available",
                            "official_search_url": "https://animate.example/search?q=stand",
                            "allowed_source_domains": ["animate.example"],
                            "manual_review_checklist": ["Confirm exact product page"],
                            "source_patch_template": {"catalog_index": 10},
                            "catalog_field_import_template": {"field": "source_url"},
                        }
                    ],
                }
            ]
        }

        template = builder.build_template(focus_packs, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(template["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(template["summary"]["template_items"], 1)
        self.assertEqual(template["summary"]["manual_confirmed_rows"], 0)
        self.assertEqual(template["summary"]["focus_pack_count"], 1)
        self.assertEqual(template["summary"]["work_order_pack_count"], 1)
        self.assertEqual(template["summary"]["next_focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(template["summary"]["next_source_store"], "Animate")
        self.assertEqual(template["summary"]["next_target_category"], "Acrylic")
        self.assertEqual(template["summary"]["next_focus_pack_rows"], 1)
        self.assertEqual(
            template["summary"]["by_blocked_reason"],
            [["exact_product_detail_source_url_not_confirmed", 1]],
        )
        self.assertIn(
            "exact_product_detail_url_on_allowed_domain",
            template["summary"]["required_evidence"],
        )
        self.assertFalse(template["summary"]["auto_apply_enabled"])
        self.assertEqual(template["automation_policy"]["import_tool"], "tools/import_confirmed_source_discovery_rows.py")
        self.assertEqual(template["work_order"][0]["priority"], 1)
        self.assertEqual(template["work_order"][0]["first_batch_id"], "source-discovery-action-001")
        item = template["items"][0]
        self.assertEqual(item["manual_review_status"], "not_started")
        self.assertEqual(item["manual_confirmed_source_url"], "")
        self.assertEqual(item["manual_confirmed_image_url"], "")
        self.assertEqual(item["focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(item["pack_sequence"], 1)
        self.assertEqual(item["row_index"], 10)
        self.assertEqual(item["target_category"], "Acrylic")
        self.assertEqual(item["source_store_remaining_after_pack"], 4)
        self.assertEqual(item["blocked_reason"], "exact_product_detail_source_url_not_confirmed")
        self.assertEqual(item["blocked_until"], "exact_product_detail_source_url_confirmed")
        self.assertIn("page_is_not_search_or_category_result", item["required_evidence"])
        self.assertEqual(
            item["image_url_blocked_until"],
            "exact_source_page_product_image_confirmed",
        )
        self.assertEqual(item["search_query"], "Stand Acrylic")
        self.assertEqual(item["review_state"], "official_search_review_required")
        self.assertEqual(item["workflow"], "official_search_url_available")
        self.assertEqual(item["manual_review_checklist"], ["Confirm exact product page"])
        self.assertEqual(item["catalog_field_import_template"]["field"], "source_url")
        self.assertEqual(
            item["source_patch_template"]["blocked_reason"],
            "exact_product_detail_source_url_not_confirmed",
        )
        self.assertEqual(
            item["catalog_field_import_template"]["image_url_blocked_reason"],
            "image_url_requires_verified_exact_source_product_image",
        )


if __name__ == "__main__":
    unittest.main()
