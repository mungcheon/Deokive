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
        focus_packs = {
            "summary": {
                "focus_source_rows": 4,
                "focus_pack_count": 2,
                "not_started_focus_pack_count": 2,
                "remaining_focus_review_rows": 4,
                "confirmed_focus_source_rows": 0,
                "focus_coverage": 0.8,
                "non_focus_source_rows": 1,
            }
        }
        focus_template = {"summary": {"template_items": 4, "manual_confirmed_rows": 0}}
        focus_template_dry_run = {"updated_rows": 0, "skipped_rows": 4}
        image_attachment_template = {
            "summary": {
                "template_items": 2,
                "manual_confirmed_rows": 0,
                "source_url_update_required_rows": 1,
                "representative_image_review_required_rows": 1,
            }
        }
        image_attachment_template_dry_run = {"updated_rows": 0, "skipped_rows": 2}
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
                            "candidate_identity_flags": ["only_generic_shared_tokens"],
                            "recommended_action": "recheck_candidate_identity_before_source_or_image_patch",
                            "current_catalog_state": {"catalog_has_display_image": False},
                        },
                        {
                            "catalog_index": 7,
                            "name_ko": "Needs recheck",
                            "source_store": "Store E",
                            "candidate_title": "Wrong crossover",
                            "candidate_identity_flags": ["candidate_title_mentions_crossover"],
                            "recommended_action": "recheck_candidate_identity_before_source_or_image_patch",
                            "current_catalog_state": {"catalog_has_display_image": False},
                        },
                        {
                            "catalog_index": 8,
                            "name_ko": "Safe ready",
                            "source_store": "Store F",
                            "candidate_title": "Safe ready",
                            "candidate_identity_flags": [],
                            "recommended_action": "priority_manual_review_safe_source_image_candidate",
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
            focus_packs,
            focus_template,
            focus_template_dry_run,
            image_attachment_template,
            image_attachment_template_dry_run,
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
        self.assertEqual(report["summary"]["source_detail_candidate_recheck_required_rows"], 2)
        self.assertEqual(report["summary"]["source_detail_identity_warning_rows"], 2)
        self.assertEqual(report["summary"]["source_detail_unflagged_candidate_rows"], 1)
        self.assertEqual(report["summary"]["source_detail_ready_unflagged_candidate_rows"], 1)
        self.assertEqual(report["summary"]["manual_image_research_rows"], 1)
        self.assertEqual(report["summary"]["source_discovery_focus_pack_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_focus_pack_count"], 2)
        self.assertEqual(report["summary"]["source_discovery_not_started_focus_pack_count"], 2)
        self.assertEqual(report["summary"]["source_discovery_remaining_focus_review_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_confirmed_focus_source_rows"], 0)
        self.assertEqual(report["summary"]["source_discovery_focus_template_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_focus_template_confirmed_rows"], 0)
        self.assertEqual(report["summary"]["source_discovery_focus_template_dry_run_updated_rows"], 0)
        self.assertEqual(report["summary"]["source_discovery_focus_template_dry_run_skipped_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_focus_coverage"], 0.8)
        self.assertEqual(report["summary"]["source_discovery_non_focus_rows"], 1)
        self.assertEqual(report["summary"]["direct_image_action_queue_rows"], 2)
        self.assertEqual(report["summary"]["image_attachment_template_rows"], 2)
        self.assertEqual(report["summary"]["image_attachment_template_confirmed_rows"], 0)
        self.assertEqual(report["summary"]["image_attachment_template_source_update_required_rows"], 1)
        self.assertEqual(report["summary"]["image_attachment_template_representative_review_rows"], 1)
        self.assertEqual(report["summary"]["image_attachment_template_dry_run_updated_rows"], 0)
        self.assertEqual(report["summary"]["image_attachment_template_dry_run_skipped_rows"], 2)
        self.assertEqual(report["summary"]["action_queue_rows"], 3)
        self.assertEqual(report["summary"]["actionable_image_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_work_pack_count"], 1)
        self.assertEqual(report["summary"]["source_discovery_work_pack_rows"], 1)
        work_packs = report["source_discovery_work_packs"]
        self.assertEqual(len(work_packs), 1)
        self.assertEqual(work_packs[0]["source_store"], "Store C")
        self.assertEqual(work_packs[0]["row_count"], 1)
        self.assertTrue(work_packs[0]["manual_confirmation_required"])
        self.assertFalse(work_packs[0]["auto_apply_enabled"])
        self.assertEqual(work_packs[0]["sample_items"][0]["catalog_index"], 3)
        readiness = {row["readiness"]: row["rows"] for row in report["readiness"]}
        self.assertEqual(readiness["image_url_candidate_review"], 1)
        self.assertEqual(readiness["source_detail_candidate_review"], 1)
        self.assertEqual(readiness["source_detail_candidate_recheck_required"], 2)
        source_detail_row = next(row for row in report["readiness"] if row["readiness"] == "source_detail_candidate_recheck_required")
        self.assertEqual(source_detail_row["sample_items"][0]["candidate_identity_flags"], ["only_generic_shared_tokens"])
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
        work_order = report["work_order"]
        self.assertEqual(
            [row["lane"] for row in work_order],
            [
                "confirm_source_detail_candidates",
                "replace_generic_source_urls",
                "discover_exact_source_urls",
                "review_representative_images",
                "recheck_source_detail_candidates",
                "manual_image_research",
            ],
        )
        self.assertEqual(work_order[0]["row_count"], 1)
        self.assertEqual(work_order[1]["row_count"], 1)
        self.assertEqual(work_order[2]["row_count"], 4)
        self.assertEqual(work_order[2]["top_work_packs"][0]["source_store"], "Store C")
        self.assertFalse(work_order[0]["auto_apply_enabled"])
        self.assertTrue(work_order[0]["manual_confirmation_required"])

    def test_work_order_falls_back_to_source_discovery_readiness_when_focus_pack_is_empty(self) -> None:
        enrichment = {
            "summary": {
                "missing_image_rows": 4,
                "by_workflow": [["find_source_then_extract_image", 4]],
            },
            "groups": [
                {
                    "workflow": "find_source_then_extract_image",
                    "source_store": "Animate",
                    "missing_image_rows": 3,
                    "sample_items": [{"catalog_index": 1, "name_ko": "Needs source"}],
                },
                {
                    "workflow": "find_source_then_extract_image",
                    "source_store": "Ensky",
                    "missing_image_rows": 1,
                    "sample_items": [{"catalog_index": 2, "name_ko": "Needs source too"}],
                },
            ],
        }

        report = actionability.build_report(
            enrichment,
            {"summary": {}},
            {"batches": []},
            {"summary": {"remaining_focus_review_rows": 0}},
            generated_at="2026-07-22T00:00:00Z",
        )

        work_order = report["work_order"]
        self.assertEqual([row["lane"] for row in work_order], ["discover_exact_source_urls"])
        discover = work_order[0]
        self.assertEqual(discover["row_count"], 4)
        self.assertEqual(discover["top_source_stores"][0]["source_store"], "Animate")
        self.assertEqual(discover["top_source_stores"][0]["missing_image_rows"], 3)
        self.assertEqual(report["summary"]["source_discovery_work_pack_count"], 2)
        self.assertEqual(report["summary"]["source_discovery_work_pack_rows"], 4)
        self.assertEqual(report["source_discovery_work_packs"][0]["source_store"], "Animate")
        self.assertEqual(report["source_discovery_work_packs"][0]["row_count"], 3)
        self.assertEqual(discover["top_work_packs"][0]["source_store"], "Animate")
        self.assertEqual(discover["top_work_packs"][0]["row_count"], 3)
        self.assertIn("falls back", discover["notes"][1])


if __name__ == "__main__":
    unittest.main()
