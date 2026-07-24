from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_focus_packs_public as focus


class BuildSourceDiscoveryFocusPacksPublicTest(unittest.TestCase):
    def test_build_report_publishes_top_store_focus_packs(self) -> None:
        action_queue = {
            "summary": {"actionable_source_rows": 5},
            "batches": [
                {
                    "batch_id": "b1",
                    "source_store": "Animate",
                    "items": [
                        {
                            "catalog_index": 2,
                            "source_store": "Animate",
                            "affiliation": "Series B",
                            "category": "Badge",
                            "name_ko": "Badge B",
                            "official_search_url": "https://animate.example/search?q=b",
                            "allowed_source_domains": ["animate.example"],
                            "source_patch_template": {"manual_confirmed": False},
                            "catalog_field_import_template": {"field": "source_url"},
                        },
                        {
                            "catalog_index": 1,
                            "source_store": "Animate",
                            "category": "Acrylic",
                            "name_ko": "Stand A",
                            "official_search_url": "https://animate.example/search?q=a",
                            "allowed_source_domains": ["animate.example"],
                            "source_patch_template": {"manual_confirmed": False},
                            "catalog_field_import_template": {
                                "affiliation": "Series A",
                                "field": "source_url",
                            },
                        },
                    ],
                },
                {
                    "batch_id": "b2",
                    "source_store": "Ensky",
                    "items": [
                        {
                            "catalog_index": 3,
                            "source_store": "Ensky",
                            "category": "Keyring",
                            "name_ko": "Keyring C",
                            "official_search_url": "https://ensky.example/search?q=c",
                            "allowed_source_domains": ["ensky.example"],
                        }
                    ],
                },
                {
                    "batch_id": "b3",
                    "source_store": "Other",
                    "items": [{"catalog_index": 4, "source_store": "Other"}],
                },
            ],
        }
        bottlenecks = {
            "stores": [
                {"source_store": "Animate", "rows": 2},
                {"source_store": "Ensky", "rows": 1},
                {"source_store": "Other", "rows": 1},
            ]
        }

        report = focus.build_report(
            action_queue,
            bottlenecks,
            generated_at="2026-07-22T00:00:00Z",
            top_store_limit=2,
            pack_size=1,
        )

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(report["summary"]["focus_store_count"], 2)
        self.assertEqual(report["summary"]["focus_source_rows"], 3)
        self.assertEqual(report["summary"]["focus_pack_count"], 3)
        self.assertEqual(report["summary"]["not_started_focus_pack_count"], 3)
        self.assertEqual(report["summary"]["in_progress_focus_pack_count"], 0)
        self.assertEqual(report["summary"]["completed_focus_pack_count"], 0)
        self.assertEqual(report["summary"]["remaining_focus_review_rows"], 3)
        self.assertEqual(report["summary"]["confirmed_focus_source_rows"], 0)
        self.assertEqual(report["summary"]["blocked_focus_rows"], 3)
        self.assertEqual(
            report["summary"]["blocked_reason_counts"][0]["blocked_reason"],
            "exact_product_detail_source_url_not_confirmed",
        )
        self.assertEqual(report["summary"]["focus_coverage"], 0.6)
        self.assertEqual(report["summary"]["non_focus_source_rows"], 2)
        self.assertEqual(report["summary"]["focus_source_stores"], ["Animate", "Ensky"])
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["packs"][0]["focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(report["packs"][0]["source_store"], "Animate")
        self.assertEqual(report["packs"][0]["review_status"], "not_started")
        self.assertEqual(report["packs"][0]["confirmed_source_rows"], 0)
        self.assertEqual(report["packs"][0]["remaining_review_rows"], 1)
        self.assertEqual(report["packs"][0]["needs_manual_review_rows"], 1)
        self.assertEqual(report["packs"][0]["blocked_rows"], 1)
        self.assertEqual(
            report["packs"][0]["blocked_until"],
            "exact_product_detail_source_url_confirmed",
        )
        self.assertEqual(report["packs"][0]["target_category"], "Acrylic")
        self.assertEqual(report["packs"][0]["items"][0]["catalog_index"], 1)
        self.assertEqual(report["packs"][0]["items"][0]["affiliation"], "Series A")
        self.assertEqual(report["packs"][0]["items"][0]["manual_review_status"], "not_started")
        self.assertEqual(report["packs"][0]["items"][0]["manual_confirmed_source_url"], "")
        self.assertEqual(
            report["packs"][0]["items"][0]["blocked_reason"],
            "exact_product_detail_source_url_not_confirmed",
        )
        self.assertIn(
            "product_title_series_character_variant_category_match",
            report["packs"][0]["items"][0]["required_evidence"],
        )
        self.assertEqual(report["packs"][0]["items"][0]["search_query"], "a")
        self.assertEqual(report["packs"][0]["items"][0]["review_state"], "official_search_review_required")
        self.assertEqual(report["packs"][0]["items"][0]["workflow"], "official_search_url_available")
        self.assertIn(
            "Confirm the page is an exact product/detail page",
            report["packs"][0]["items"][0]["manual_review_checklist"][1],
        )
        self.assertEqual(report["packs"][0]["items"][0]["catalog_field_import_template"]["field"], "source_url")
        self.assertEqual(
            report["packs"][0]["items"][0]["catalog_field_import_template"]["blocked_until"],
            "exact_product_detail_source_url_confirmed",
        )
        self.assertEqual(
            report["packs"][0]["items"][0]["catalog_field_import_template"]["image_url_blocked_until"],
            "exact_source_page_product_image_confirmed",
        )
        self.assertEqual(report["work_order"][0]["first_batch_id"], "b1")
        self.assertEqual(report["work_order"][0]["review_status"], "not_started")
        self.assertEqual(report["work_order"][0]["remaining_review_rows"], 1)
        self.assertEqual(report["work_order"][0]["blocked_rows"], 1)
        self.assertFalse(report["packs"][0]["auto_apply_enabled"])

    def test_default_focus_limit_covers_top_eight_source_stores(self) -> None:
        action_queue = {
            "summary": {"actionable_source_rows": 9},
            "batches": [
                {
                    "batch_id": f"b{index}",
                    "source_store": f"Store {index}",
                    "items": [
                        {
                            "catalog_index": index,
                            "source_store": f"Store {index}",
                            "category": "Badge",
                            "name_ko": f"Goods {index}",
                        }
                    ],
                }
                for index in range(1, 10)
            ],
        }
        bottlenecks = {
            "stores": [
                {"source_store": f"Store {index}", "rows": 1}
                for index in range(1, 10)
            ]
        }

        report = focus.build_report(
            action_queue,
            bottlenecks,
            generated_at="2026-07-22T00:00:00Z",
            pack_size=20,
        )

        self.assertEqual(report["summary"]["focus_store_count"], 8)
        self.assertEqual(report["summary"]["focus_source_rows"], 8)
        self.assertEqual(report["summary"]["focus_pack_count"], 8)
        self.assertEqual(report["summary"]["non_focus_source_rows"], 1)
        self.assertEqual(
            report["summary"]["focus_source_stores"],
            [f"Store {index}" for index in range(1, 9)],
        )


if __name__ == "__main__":
    unittest.main()
