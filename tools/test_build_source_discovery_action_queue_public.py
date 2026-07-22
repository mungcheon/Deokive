from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_action_queue_public as queue


class BuildSourceDiscoveryActionQueuePublicTest(unittest.TestCase):
    def test_build_report_keeps_actionable_review_states(self) -> None:
        review = {
            "batches": [
                {
                    "workflow": "official_search_url_available",
                    "review_state": "official_search_review_required",
                    "source_store": "Animate",
                    "row_count": 2,
                    "next_machine_step": "open_search",
                    "items": [
                        {
                            "catalog_index": 2,
                            "name_ko": "Badge",
                            "category": "Badge",
                            "official_search_url": "https://animate.example/search?q=badge",
                            "allowed_source_domains": ["animate.example"],
                            "source_patch_template": {
                                "catalog_index": 2,
                                "source_url": "<exact_product_detail_url>",
                            },
                            "catalog_field_import_template": {
                                "row_index": 2,
                                "field": "source_url",
                            },
                        },
                        {
                            "catalog_index": 1,
                            "name_ko": "Stand",
                            "category": "Acrylic",
                            "official_search_url": "https://animate.example/search?q=stand",
                            "allowed_source_domains": ["animate.example"],
                            "source_patch_template": {
                                "catalog_index": 1,
                                "source_url": "<exact_product_detail_url>",
                            },
                            "catalog_field_import_template": {
                                "row_index": 1,
                                "field": "source_url",
                            },
                        },
                    ],
                },
                {
                    "workflow": "manual_official_research",
                    "review_state": "manual_official_research_required",
                    "source_store": "Unknown",
                    "row_count": 5,
                    "items": [{"catalog_index": 3, "name_ko": "Manual"}],
                },
            ]
        }

        report = queue.build_report(review, max_rows=10, batch_size=10)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["actionable_source_rows"], 2)
        self.assertEqual(report["summary"]["queued_source_rows"], 2)
        self.assertEqual(report["summary"]["unqueued_actionable_source_rows"], 0)
        self.assertEqual(report["summary"]["queue_coverage"], 1.0)
        self.assertEqual(report["summary"]["source_patch_template_count"], 2)
        self.assertEqual(report["summary"]["catalog_field_import_template_count"], 2)
        self.assertEqual(report["summary"]["missing_template_item_count"], 0)
        self.assertEqual(report["summary"]["source_store_workstream_count"], 1)
        self.assertEqual(report["summary"]["high_volume_source_store_workstream_count"], 0)
        self.assertEqual(report["summary"]["largest_source_store_workstream_rows"], 2)
        self.assertEqual(dict(report["summary"]["excluded_review_state_rows"]), {"manual_official_research_required": 5})
        self.assertEqual(report["summary"]["manual_research_backlog_rows"], 1)
        self.assertEqual(report["summary"]["manual_research_backlog_by_source_store"], [["Unknown", 1]])
        self.assertEqual(report["manual_research_backlog"][0]["catalog_index"], 3)
        self.assertEqual(
            report["manual_research_backlog"][0]["recommended_next_step"],
            "find_official_domain_then_record_exact_product_detail_source",
        )
        self.assertEqual(report["summary"]["action_batch_count"], 1)
        self.assertEqual([item["catalog_index"] for item in report["batches"][0]["items"]], [1, 2])
        self.assertEqual(report["source_store_workstreams"][0]["source_store"], "Animate")
        self.assertEqual(report["source_store_workstreams"][0]["queued_source_rows"], 2)
        self.assertEqual(report["source_store_workstreams"][0]["batch_count"], 1)
        self.assertEqual(report["source_store_workstreams"][0]["next_batch_id"], "source-discovery-action-001")
        self.assertEqual(report["source_store_workstreams"][0]["allowed_source_domains"], ["animate.example"])
        self.assertEqual(report["source_store_workstreams"][0]["official_search_url_count"], 2)
        self.assertEqual(report["source_store_workstreams"][0]["batch_ids"], ["source-discovery-action-001"])
        self.assertEqual(report["source_store_workstreams"][0]["workflow_rows"], [["official_search_url_available", 2]])
        self.assertEqual(report["source_store_workstreams"][0]["sample_items"][0]["catalog_index"], 1)
        self.assertFalse(report["source_store_workstreams"][0]["auto_apply_enabled"])
        self.assertEqual(
            report["batches"][0]["items"][0]["source_patch_template"]["catalog_index"],
            1,
        )

    def test_max_rows_caps_queue_not_actionable_summary(self) -> None:
        review = {
            "batches": [
                {
                    "workflow": "official_search_url_available",
                    "review_state": "official_search_review_required",
                    "source_store": "Store",
                    "row_count": 3,
                    "items": [{"catalog_index": index} for index in range(3)],
                }
            ]
        }

        report = queue.build_report(review, max_rows=2, batch_size=1)

        self.assertEqual(report["summary"]["actionable_source_rows"], 3)
        self.assertEqual(report["summary"]["queued_source_rows"], 2)
        self.assertEqual(report["summary"]["unqueued_actionable_source_rows"], 1)
        self.assertEqual(report["summary"]["queue_coverage"], 0.6667)
        self.assertEqual(report["summary"]["missing_template_item_count"], 2)
        self.assertEqual(report["summary"]["missing_template_sample_catalog_indexes"], [1, 2])
        self.assertEqual(report["summary"]["action_batch_count"], 2)


if __name__ == "__main__":
    unittest.main()
