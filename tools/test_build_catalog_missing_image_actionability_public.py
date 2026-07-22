from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_catalog_missing_image_actionability_public as actionability


class BuildCatalogMissingImageActionabilityPublicTest(unittest.TestCase):
    def test_build_report_classifies_missing_image_work_by_next_required_action(self) -> None:
        enrichment = {
            "summary": {
                "missing_image_rows": 5,
                "manual_image_research_rows": 1,
                "by_workflow": [
                    ["extract_from_existing_source_url", 1],
                    ["replace_generic_source_then_extract_image", 2],
                    ["find_source_then_extract_image", 1],
                    ["manual_image_research", 1],
                ],
            },
            "groups": [
                {
                    "workflow": "extract_from_existing_source_url",
                    "source_store": "Store A",
                    "missing_image_rows": 1,
                    "sample_items": [{"catalog_index": 1, "name_ko": "Ready"}],
                },
                {
                    "workflow": "replace_generic_source_then_extract_image",
                    "source_store": "Store B",
                    "missing_image_rows": 2,
                    "sample_items": [{"catalog_index": 2, "name_ko": "Generic"}],
                },
                {
                    "workflow": "find_source_then_extract_image",
                    "source_store": "Store C",
                    "missing_image_rows": 1,
                    "sample_items": [{"catalog_index": 3, "name_ko": "Source first"}],
                },
                {
                    "workflow": "manual_image_research",
                    "source_store": "Store D",
                    "missing_image_rows": 1,
                    "sample_items": [{"catalog_index": 4, "name_ko": "Manual"}],
                },
            ],
        }
        action_queue = {"summary": {"queued_image_rows": 2, "actionable_image_rows": 3}}
        source_detail_queue = {
            "batches": [
                {
                    "items": [
                        {
                            "catalog_index": 5,
                            "name_ko": "Candidate",
                            "source_store": "Store E",
                            "candidate_source_url": "https://example.test/item",
                            "candidate_image_url": "https://example.test/item.jpg",
                            "review_risk": "near_single_candidate_review",
                            "recommended_action": "confirm_exact_identity_before_source_or_image_patch",
                            "current_catalog_state": {"catalog_has_display_image": False},
                        },
                        {
                            "catalog_index": 6,
                            "name_ko": "Already solved",
                            "source_store": "Store E",
                            "recommended_action": "skip_current_catalog_row_already_has_display_image",
                            "current_catalog_state": {"catalog_has_display_image": True},
                        },
                    ]
                }
            ]
        }

        report = actionability.build_report(
            enrichment,
            action_queue,
            source_detail_queue,
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["missing_image_rows"], 5)
        self.assertEqual(report["summary"]["readiness_classified_rows"], 5)
        self.assertEqual(report["summary"]["unclassified_rows"], 0)
        self.assertEqual(report["summary"]["exact_source_ready_rows"], 1)
        self.assertEqual(report["summary"]["source_first_rows"], 3)
        self.assertEqual(report["summary"]["source_detail_candidate_review_rows"], 1)
        self.assertEqual(report["summary"]["manual_image_research_rows"], 1)
        self.assertEqual(report["summary"]["direct_image_action_queue_rows"], 2)
        self.assertEqual(report["summary"]["action_queue_rows"], 3)
        self.assertEqual(report["summary"]["actionable_image_rows"], 4)
        readiness = {row["readiness"]: row["rows"] for row in report["readiness"]}
        self.assertEqual(readiness["image_url_candidate_review"], 1)
        self.assertEqual(readiness["source_detail_candidate_review"], 1)
        self.assertEqual(readiness["source_url_replacement_required"], 2)
        self.assertEqual(readiness["source_url_discovery_required"], 1)
        self.assertEqual(readiness["manual_research_required"], 1)
        store_priority = {row["source_store"]: row for row in report["source_store_priority"]}
        self.assertEqual(store_priority["Store B"]["missing_image_rows"], 2)
        self.assertEqual(store_priority["Store B"]["primary_workflow"], "replace_generic_source_then_extract_image")
        self.assertEqual(
            store_priority["Store B"]["recommended_next_step"],
            "replace_generic_source_url_then_extract_image",
        )
        self.assertFalse(store_priority["Store B"]["auto_apply_enabled"])
        self.assertEqual(store_priority["Store B"]["sample_items"][0]["readiness"], "source_url_replacement_required")


if __name__ == "__main__":
    unittest.main()
