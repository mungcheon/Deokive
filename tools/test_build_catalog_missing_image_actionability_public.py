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
                "missing_image_rows": 6,
                "manual_image_research_rows": 1,
                "by_workflow": [
                    ["extract_from_existing_source_url", 1],
                    ["replace_generic_source_then_extract_image", 2],
                    ["find_source_then_extract_image", 1],
                    ["manual_image_research", 1],
                    ["review_gotouchi_official_candidates", 1],
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
                {
                    "workflow": "review_gotouchi_official_candidates",
                    "source_store": "Gotouchi",
                    "missing_image_rows": 1,
                    "sample_items": [{"catalog_index": 9, "name_ko": "Representative"}],
                },
            ],
        }
        action_queue = {
            "summary": {
                "queued_image_rows": 2,
                "actionable_image_rows": 3,
                "primary_review_url_rows": 2,
                "primary_review_url_kind_counts": [
                    ["source_search_url", 1],
                    ["current_source_url", 1],
                ],
                "next_representative_image_review_batch_rows": 1,
                "next_representative_image_review_batch_primary_review_url_rows": 1,
                "next_representative_image_review_batch_local_path_rows": 1,
                "next_representative_image_review_batch_primary_review_url_kind_counts": [
                    ["current_source_url", 1],
                ],
            },
            "batches": [
                {
                    "batch_id": "image-attachment-action-001",
                    "workflow": "replace_generic_source_then_extract_image",
                    "source_store": "Store B",
                    "row_count": 1,
                    "primary_review_url_rows": 1,
                    "first_primary_review_url": "https://store-b.example/search?q=generic",
                    "first_primary_review_url_kind": "source_search_url",
                    "items": [
                        {
                            "catalog_index": 2,
                            "name_ko": "Generic",
                            "primary_review_url": "https://store-b.example/search?q=generic",
                            "primary_review_url_kind": "source_search_url",
                        }
                    ],
                },
                {
                    "batch_id": "image-attachment-action-002",
                    "workflow": "review_gotouchi_official_candidates",
                    "source_store": "Gotouchi",
                    "row_count": 1,
                    "primary_review_url_rows": 1,
                    "first_primary_review_url": "https://gotouchi.example/item",
                    "first_primary_review_url_kind": "current_source_url",
                    "items": [
                        {
                            "catalog_index": 9,
                            "name_ko": "Representative",
                            "primary_review_url": "https://gotouchi.example/item",
                            "primary_review_url_kind": "current_source_url",
                        }
                    ],
                },
            ],
        }
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
        focus_template = {
            "summary": {
                "template_items": 4,
                "manual_confirmed_rows": 0,
                "next_focus_pack_id": "source-discovery-focus-001",
                "next_source_store": "Store C",
                "next_target_category": "Acrylic",
                "next_focus_pack_rows": 2,
                "next_official_search_url": "https://store-c.example/search?q=acrylic",
            }
        }
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
        next_focus_detail_candidates = {
            "summary": {
                "pack_items": 2,
                "items_with_candidates": 1,
                "candidate_rows": 3,
                "manual_candidate_review_rows": 3,
                "no_candidate_items": 1,
                "next_action_lane_count": 2,
                "next_action_lanes": [
                    ["fallback_source_search", 1],
                    ["manual_candidate_identity_review", 1],
                ],
                "official_search_audit_status_counts": [
                    ["official_search_has_results", 1],
                    ["official_search_no_results", 1],
                ],
            },
            "items": [
                {
                    "catalog_index": 3,
                    "name_ko": "Source first",
                    "name_ja": "ソース優先",
                    "candidate_count": 3,
                    "official_search_audit_status": "official_search_has_results",
                    "needs_fallback_web_search": False,
                    "status": "manual_candidate_review",
                },
                {
                    "catalog_index": 33,
                    "name_ko": "Fallback needed",
                    "candidate_count": 0,
                    "official_search_audit_status": "official_search_no_results",
                    "needs_fallback_web_search": True,
                    "status": "no_candidates_found",
                },
            ],
        }
        next_focus_fallback_queue = {
            "summary": {
                "queue_rows": 1,
                "fallback_query_count": 5,
                "manual_confirmed_rows": 0,
                "first_domain_limited_web_search_url": "https://google.example/search",
                "first_fallback_store_search_url": "https://store-c.example/mobile-search",
            },
            "items": [
                {
                    "catalog_index": 33,
                    "name_ko": "Fallback needed",
                    "domain_limited_web_search_urls": ["https://google.example/search"],
                    "fallback_store_search_url": "https://store-c.example/mobile-search",
                }
            ],
        }
        next_focus_exact_url_queue = {"summary": {"queue_rows": 1}}
        next_focus_identity_backfill_queue = {"summary": {"queue_rows": 1}}
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
                            "catalog_index": 9,
                            "name_ko": "Large candidate set",
                            "source_store": "Store G",
                            "candidate_title": "Large candidate set",
                            "candidate_count": 23,
                            "candidate_count_bucket": "large_candidate_set",
                            "candidate_count_review_required": True,
                            "candidate_identity_flags": [],
                            "recommended_action": "review_large_candidate_set_before_source_or_image_patch",
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
            source_discovery_next_focus_detail_candidates=next_focus_detail_candidates,
            source_discovery_next_focus_fallback_queue=next_focus_fallback_queue,
            source_discovery_next_focus_exact_url_queue=next_focus_exact_url_queue,
            source_discovery_next_focus_identity_backfill_queue=next_focus_identity_backfill_queue,
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["missing_image_rows"], 6)
        self.assertEqual(report["summary"]["readiness_classified_rows"], 6)
        self.assertEqual(report["summary"]["unclassified_rows"], 0)
        self.assertEqual(report["summary"]["exact_source_ready_rows"], 1)
        self.assertEqual(report["summary"]["source_first_rows"], 3)
        self.assertEqual(report["summary"]["review_before_attach_rows"], 1)
        self.assertEqual(report["summary"]["source_detail_candidate_review_rows"], 1)
        self.assertEqual(report["summary"]["source_detail_candidate_count_review_required_rows"], 1)
        self.assertEqual(report["summary"]["source_detail_candidate_recheck_required_rows"], 2)
        self.assertEqual(report["summary"]["source_detail_identity_warning_rows"], 2)
        self.assertEqual(report["summary"]["source_detail_unflagged_candidate_rows"], 2)
        self.assertEqual(report["summary"]["source_detail_ready_unflagged_candidate_rows"], 1)
        self.assertEqual(report["summary"]["manual_image_research_rows"], 1)
        self.assertEqual(report["summary"]["source_discovery_focus_pack_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_focus_pack_count"], 2)
        self.assertEqual(report["summary"]["source_discovery_not_started_focus_pack_count"], 2)
        self.assertEqual(report["summary"]["source_discovery_remaining_focus_review_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_confirmed_focus_source_rows"], 0)
        self.assertEqual(report["summary"]["source_discovery_focus_template_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_focus_template_confirmed_rows"], 0)
        self.assertEqual(report["summary"]["source_discovery_next_focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(report["summary"]["source_discovery_next_focus_pack_rows"], 2)
        self.assertEqual(report["summary"]["source_discovery_next_focus_action_lane_count"], 2)
        self.assertEqual(
            report["summary"]["source_discovery_next_focus_action_lanes"],
            [
                ["exact_source_url_review", 1],
                ["catalog_variant_metadata_enrichment", 1],
            ],
        )
        self.assertEqual(report["summary"]["source_discovery_focus_template_dry_run_updated_rows"], 0)
        self.assertEqual(report["summary"]["source_discovery_focus_template_dry_run_skipped_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_focus_coverage"], 0.8)
        self.assertEqual(report["summary"]["source_discovery_non_focus_rows"], 1)
        self.assertEqual(report["summary"]["direct_image_action_queue_rows"], 2)
        self.assertEqual(report["summary"]["direct_image_action_primary_review_url_rows"], 2)
        self.assertEqual(
            report["summary"]["direct_image_action_primary_review_url_kind_counts"],
            [["source_search_url", 1], ["current_source_url", 1]],
        )
        self.assertEqual(report["summary"]["direct_image_action_next_representative_review_batch_rows"], 1)
        self.assertEqual(
            report["summary"][
                "direct_image_action_next_representative_review_batch_primary_review_url_rows"
            ],
            1,
        )
        self.assertEqual(
            report["summary"]["direct_image_action_next_representative_review_batch_local_path_rows"],
            1,
        )
        self.assertEqual(
            report["summary"][
                "direct_image_action_next_representative_review_batch_primary_review_url_kind_counts"
            ],
            [["current_source_url", 1]],
        )
        self.assertEqual(report["summary"]["direct_image_action_workflows_with_review_start"], 2)
        self.assertEqual(report["summary"]["image_attachment_template_rows"], 2)
        self.assertEqual(report["summary"]["image_attachment_template_confirmed_rows"], 0)
        self.assertEqual(report["summary"]["image_attachment_template_source_update_required_rows"], 1)
        self.assertEqual(report["summary"]["image_attachment_template_representative_review_rows"], 1)
        self.assertEqual(report["summary"]["image_attachment_template_dry_run_updated_rows"], 0)
        self.assertEqual(report["summary"]["image_attachment_template_dry_run_skipped_rows"], 2)
        self.assertEqual(report["summary"]["action_queue_rows"], 3)
        self.assertEqual(report["summary"]["actionable_image_rows"], 4)
        self.assertEqual(
            report["summary"]["by_blocked_reason"][0],
            {
                "blocked_reason": "generic_or_listing_source_url_cannot_support_image_import",
                "rows": 2,
            },
        )
        self.assertIn("exact_product_source_url", report["automation_policy"]["required_evidence"])
        self.assertEqual(
            report["automation_policy"]["blocked_until_default"],
            "exact_product_identity_and_source_url_confirmed",
        )
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
        self.assertEqual(readiness["source_detail_candidate_count_review_required"], 1)
        self.assertEqual(readiness["source_detail_candidate_recheck_required"], 2)
        count_review_row = next(
            row
            for row in report["readiness"]
            if row["readiness"] == "source_detail_candidate_count_review_required"
        )
        self.assertEqual(
            count_review_row["blocked_reason"],
            "large_candidate_set_requires_exact_identity_review",
        )
        self.assertTrue(count_review_row["sample_items"][0]["candidate_count_review_required"])
        source_detail_row = next(row for row in report["readiness"] if row["readiness"] == "source_detail_candidate_recheck_required")
        self.assertEqual(source_detail_row["sample_items"][0]["candidate_identity_flags"], ["only_generic_shared_tokens"])
        self.assertNotIn("candidate_source_url", source_detail_row["sample_items"][0])
        self.assertEqual(
            source_detail_row["sample_items"][0]["rejected_candidate_source_url"],
            "https://example.test/item",
        )
        self.assertEqual(
            source_detail_row["sample_items"][0]["candidate_status"],
            "recheck_required_not_actionable",
        )
        self.assertEqual(readiness["source_url_replacement_required"], 2)
        self.assertEqual(readiness["representative_image_review_required"], 1)
        self.assertEqual(readiness["source_url_discovery_required"], 1)
        self.assertEqual(readiness["manual_research_required"], 1)
        source_discovery_readiness = next(
            row for row in report["readiness"] if row["readiness"] == "source_url_discovery_required"
        )
        self.assertEqual(source_discovery_readiness["blocked_reason"], "missing_exact_source_url")
        self.assertIn("official_or_trusted_product_detail_source_url", source_discovery_readiness["required_evidence"])
        store_priority = {row["source_store"]: row for row in report["source_store_priority"]}
        self.assertEqual(store_priority["Store B"]["missing_image_rows"], 2)
        self.assertEqual(store_priority["Store B"]["primary_workflow"], "replace_generic_source_then_extract_image")
        self.assertEqual(
            store_priority["Store B"]["recommended_next_step"],
            "replace_generic_source_url_then_extract_image",
        )
        self.assertFalse(store_priority["Store B"]["auto_apply_enabled"])
        self.assertEqual(
            store_priority["Store B"]["blocked_until"],
            "generic_source_url_replaced_with_exact_product_source",
        )
        self.assertEqual(
            store_priority["Gotouchi"]["blocked_reason"],
            "representative_image_requires_product_type_review",
        )
        self.assertEqual(store_priority["Store B"]["sample_items"][0]["readiness"], "source_url_replacement_required")
        work_order = report["work_order"]
        self.assertEqual(
            [row["lane"] for row in work_order],
            [
                "confirm_source_detail_candidates",
                "review_large_source_detail_candidate_sets",
                "replace_generic_source_urls",
                "discover_exact_source_urls",
                "review_representative_images",
                "recheck_source_detail_candidates",
                "manual_image_research",
            ],
        )
        self.assertEqual(work_order[0]["row_count"], 1)
        self.assertEqual(work_order[1]["row_count"], 1)
        self.assertEqual(work_order[1]["blocked_reason"], "large_candidate_set_requires_exact_identity_review")
        self.assertEqual(work_order[2]["row_count"], 1)
        self.assertEqual(
            work_order[2]["review_start"]["first_primary_review_url"],
            "https://store-b.example/search?q=generic",
        )
        self.assertEqual(work_order[2]["review_start"]["first_primary_review_url_kind"], "source_search_url")
        self.assertEqual(work_order[3]["row_count"], 4)
        self.assertEqual(work_order[3]["blocked_reason"], "missing_exact_source_url")
        self.assertIn("title_character_variant_type_match", work_order[3]["required_evidence"])
        self.assertEqual(work_order[3]["top_work_packs"][0]["source_store"], "Store C")
        self.assertEqual(
            work_order[3]["current_focus_pack"]["focused_pack_report"],
            "data/source_discovery_next_focus_pack_public.json",
        )
        self.assertEqual(
            work_order[3]["current_focus_pack"]["detail_candidates_report"],
            "data/source_discovery_next_focus_detail_candidates_public.json",
        )
        self.assertEqual(
            work_order[3]["current_focus_pack"]["first_official_search_url"],
            "https://store-c.example/search?q=acrylic",
        )
        self.assertEqual(
            report["next_source_discovery_focus_pack"]["confirmed_template"],
            "data/source_discovery_focus_confirmed_template_public.json",
        )
        self.assertEqual(
            report["next_source_discovery_focus_pack"]["blocked_until"],
            "exact_product_source_url_discovered",
        )
        self.assertEqual(
            report["next_source_discovery_focus_pack"]["candidate_review_summary"][
                "candidate_rows"
            ],
            3,
        )
        self.assertEqual(
            report["next_source_discovery_focus_pack"]["candidate_review_summary"][
                "fallback_search_needed_items"
            ],
            1,
        )
        self.assertEqual(
            report["next_source_discovery_focus_pack"]["candidate_review_summary"][
                "next_action_lanes"
            ],
            [
                ["fallback_source_search", 1],
                ["manual_candidate_identity_review", 1],
            ],
        )
        self.assertEqual(
            report["next_source_discovery_focus_pack"]["fallback_review_summary"][
                "queue_rows"
            ],
            1,
        )
        self.assertEqual(
            report["next_source_discovery_focus_pack"]["candidate_review_samples"][0][
                "candidate_count"
            ],
            3,
        )
        self.assertEqual(
            report["next_source_discovery_focus_pack"]["fallback_review_samples"][0][
                "domain_limited_web_search_url_count"
            ],
            1,
        )
        self.assertFalse(work_order[0]["auto_apply_enabled"])
        self.assertTrue(work_order[0]["manual_confirmation_required"])
        self.assertEqual(
            report["image_action_review_starts"][
                "review_gotouchi_official_candidates"
            ]["first_primary_review_url_kind"],
            "current_source_url",
        )
        execution_queue = report["execution_queue_summary"]
        self.assertEqual(execution_queue["queued_rows_total"], 6)
        self.assertGreater(execution_queue["raw_queued_rows_total"], 6)
        self.assertEqual(
            execution_queue["overlapping_queue_rows"],
            execution_queue["raw_queued_rows_total"] - execution_queue["queued_rows_total"],
        )
        self.assertEqual(execution_queue["not_yet_queued_rows"], 0)
        self.assertEqual(execution_queue["unqueued_phase_rows_total"], 0)
        self.assertGreater(execution_queue["overlay_queue_rows"], 0)
        blocking_dashboard = report["blocking_dashboard"]
        self.assertEqual(blocking_dashboard["status"], "manual_evidence_required")
        self.assertEqual(blocking_dashboard["total_open_rows"], 6)
        self.assertEqual(blocking_dashboard["auto_import_ready_rows"], 1)
        self.assertEqual(blocking_dashboard["manual_validation_required_rows"], 6)
        self.assertEqual(blocking_dashboard["next_queue"]["lane"], "confirm_source_detail_candidates")
        self.assertEqual(blocking_dashboard["next_phase"]["phase_id"], "replace_generic_source_urls")
        self.assertEqual(
            blocking_dashboard["top_blocked_reason"]["blocked_reason"],
            "generic_or_listing_source_url_cannot_support_image_import",
        )
        self.assertFalse(blocking_dashboard["auto_apply_enabled"])
        phase_breakdown = {
            row["phase_id"]: row for row in execution_queue["phase_queue_breakdown"]
        }
        queue_by_lane = {row["lane"]: row for row in execution_queue["queues"]}
        self.assertEqual(
            queue_by_lane["replace_generic_source_urls"]["review_start"]["batch_id"],
            "image-attachment-action-001",
        )
        completion_phases = {
            row["phase_id"]: row for row in report["completion_plan"]["phases"]
        }
        review_start_coverage = report["completion_plan"]["review_start_coverage"]
        self.assertEqual(
            review_start_coverage["status"],
            "some_phases_need_manual_research_start",
        )
        self.assertEqual(review_start_coverage["phases_with_review_start"], 3)
        self.assertEqual(review_start_coverage["phases_missing_review_start"], 1)
        self.assertEqual(review_start_coverage["rows_missing_review_start"], 1)
        self.assertEqual(
            review_start_coverage["missing_review_start_phase_ids"],
            ["manual_nonstandard_image_research"],
        )
        self.assertEqual(
            review_start_coverage["phase_review_starts"][0]["phase_id"],
            "replace_generic_source_urls",
        )
        self.assertTrue(
            review_start_coverage["phase_review_starts"][0]["has_review_start"]
        )
        self.assertEqual(
            completion_phases["review_representative_images"]["review_start"][
                "first_primary_review_url"
            ],
            "https://gotouchi.example/item",
        )
        self.assertEqual(
            blocking_dashboard["review_start_coverage_status"],
            "some_phases_need_manual_research_start",
        )
        self.assertEqual(blocking_dashboard["phases_missing_review_start"], 1)
        self.assertEqual(
            phase_breakdown["complete_source_discovery_focus_packs"][
                "direct_queue_lane"
            ],
            "discover_exact_source_urls",
        )
        self.assertEqual(
            phase_breakdown["complete_source_discovery_focus_packs"][
                "remaining_rows"
            ],
            0,
        )

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
        self.assertTrue(any("falls back" in note for note in discover["notes"]))


if __name__ == "__main__":
    unittest.main()
