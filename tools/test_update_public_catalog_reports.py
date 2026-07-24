from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import update_public_catalog_reports as reports
from build_metadata_action_queue_public import build_report as build_metadata_action_queue_report


class PublicCatalogReportTests(unittest.TestCase):
    def test_enrich_image_action_queue_source_url_review_adds_candidate_context(self):
        action_queue = {
            "next_source_url_review_batch": [
                {
                    "row_index": 10,
                    "name_ko": "Badge",
                    "primary_review_url": "https://fanding.kr/@stellive/shop?keyword=Badge",
                }
            ]
        }
        source_url_template = {
            "items": [
                {
                    "row_index": 10,
                    "candidate_status": "low_confidence_candidate",
                    "candidate_review_lane": "low_confidence_candidate_review",
                    "candidate_score": 0.27,
                    "candidate_count": 2,
                    "candidate_options": [
                        {
                            "source_url": "https://fanding.kr/@stellive/shop/3700",
                            "title": "Badge maybe",
                        }
                    ],
                    "source_url_review_lane": "low_confidence_candidate_review",
                    "source_url_review_blockers": ["candidate_score_too_low"],
                    "match_diagnostics": {"diagnosis": "needs_review"},
                    "fallback_search_queries": ["site:fanding.kr/@stellive/shop Badge"],
                    "store_search_hints": {
                        "store_search_url": "https://fanding.kr/@stellive/shop?keyword=Badge"
                    },
                }
            ]
        }

        enriched = reports.enrich_image_action_queue_source_url_review(
            action_queue,
            source_url_template,
        )

        row = enriched["next_source_url_review_batch"][0]
        self.assertEqual(row["candidate_status"], "low_confidence_candidate")
        self.assertEqual(row["candidate_options"][0]["title"], "Badge maybe")
        self.assertEqual(row["source_url_review_blockers"], ["candidate_score_too_low"])
        self.assertEqual(row["match_diagnostics"]["diagnosis"], "needs_review")

    def test_write_json_skips_identical_payloads(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            payload = {"schema_version": 1, "items": [1, 2, 3]}
            reports.write_json(path, payload)
            first_mtime = path.stat().st_mtime_ns

            reports.write_json(path, payload)

            self.assertEqual(path.stat().st_mtime_ns, first_mtime)

            timestamp_only = {"generated_at": "later", **payload}
            reports.write_json(path, timestamp_only)

            self.assertEqual(path.stat().st_mtime_ns, first_mtime)

            summary_timestamp_only = {"summary_generated_at": "later", **payload}
            reports.write_json(path, summary_timestamp_only)

            self.assertEqual(path.stat().st_mtime_ns, first_mtime)

    def test_public_report_generation_keeps_site_data_safe_and_consistent(self):
        result = reports.update_reports(write=False)

        self.assertFalse(result["write"])
        self.assertGreater(result["rows"], 0)
        self.assertIn("source_url", result["missing"])
        self.assertIn("image_url", result["missing"])
        self.assertEqual(result["public_validation"]["status"], "pass")
        self.assertGreaterEqual(result["public_validation"]["checked_files"], 30)
        updated_files = {Path(path).as_posix() for path in result["updated_files"]}
        self.assertIn("data/catalog_operations_public.json", updated_files)
        self.assertIn("data/catalog_agent_work_queue_public.json", updated_files)
        self.assertIn("data/catalog_image_asset_audit_public.json", updated_files)
        self.assertIn("data/catalog_missing_image_priority_public.json", updated_files)
        self.assertIn("data/source_discovery_starter_queue_public.json", updated_files)
        self.assertIn("data/animate_missing_image_search_public.json", updated_files)
        self.assertIn("data/goodsmile_missing_image_search_public.json", updated_files)
        self.assertIn("data/kotobukiya_movic_missing_image_search_public.json", updated_files)
        self.assertIn("data/jump_furyu_taito_missing_image_search_public.json", updated_files)
        self.assertIn("data/secondary_official_missing_image_search_public.json", updated_files)
        self.assertIn("data/manual_missing_image_source_discovery_public.json", updated_files)
        self.assertIn("data/generic_storefront_missing_image_source_public.json", updated_files)
        self.assertIn("data/catalog_missing_image_report_coverage_public.json", updated_files)
        self.assertIn("data/ensky_missing_image_cache_coverage_public.json", updated_files)
        self.assertIn("data/ensky_cache_candidate_action_queue_public.json", updated_files)
        self.assertIn("data/ensky_search_page_probe_public.json", updated_files)
        self.assertIn("data/stellive_fanding_candidates_public.json", updated_files)
        self.assertIn("data/requested_focus_enrichment_public.json", updated_files)
        self.assertIn("data/requested_focus_review_batches_public.json", updated_files)
        self.assertIn("data/catalog_confirmed_import_readiness_public.json", updated_files)
        self.assertIn("data/catalog_execution_plan_public.json", updated_files)
        self.assertIn("data/source_discovery_store_bottlenecks_public.json", updated_files)
        self.assertIn("data/catalog_metadata_review_batches_public.json", updated_files)
        self.assertIn("data/catalog_metadata_action_queue_public.json", updated_files)
        self.assertIn("data/catalog_name_duplicate_audit_public.json", updated_files)
        self.assertIn("data/animation_category_review_batches_public.json", updated_files)
        self.assertIn("data/animation_category_coverage_audit_public.json", updated_files)
        self.assertIn("data/animation_category_action_queue_public.json", updated_files)
        self.assertIn("data/danganronpa_missing_media_public.json", updated_files)
        self.assertIn("data/danganronpa_patch_template_dry_run_public.json", updated_files)
        self.assertIn("data/gotouchi_representative_image_attachment_public.json", updated_files)
        self.assertIn("data/gotouchi_official_candidate_review_queue_public.json", updated_files)
        self.assertIn("data/catalog_image_source_url_confirmed_template_public.json", updated_files)
        self.assertIn("data/catalog_manual_source_url_search_queue_public.json", updated_files)
        self.assertIn("data/catalog_provider_missing_source_url_queue_public.json", updated_files)
        self.assertIn("data/catalog_candidate_source_url_review_queue_public.json", updated_files)
        self.assertIn("data/source_discovery_next_focus_pack_public.json", updated_files)
        self.assertIn("data/source_discovery_next_focus_pack_import_dry_run_public.json", updated_files)
        self.assertIn("data/source_discovery_next_focus_pack_fetch_audit_public.json", updated_files)
        self.assertIn("data/source_discovery_next_focus_detail_candidates_public.json", updated_files)
        self.assertIn(
            "data/source_discovery_next_focus_metadata_field_import_dry_run_public.json",
            updated_files,
        )
        self.assertIn("data/source_discovery_next_focus_fallback_queue_public.json", updated_files)
        self.assertIn("data/source_discovery_next_focus_exact_url_review_queue_public.json", updated_files)
        self.assertIn("data/source_discovery_next_focus_identity_backfill_queue_public.json", updated_files)
        self.assertIn(
            "data/source_discovery_next_focus_identity_candidate_review_queue_public.json",
            updated_files,
        )
        self.assertIn("data/source_discovery_next_focus_fallback_import_dry_run_public.json", updated_files)
        self.assertIn("data/source_discovery_completion_roadmap_public.json", updated_files)
        self.assertIn("data/catalog_missing_image_actionability_public.json", updated_files)
        self.assertIn("data/catalog_deduplication_fast_review_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_metadata_fast_review_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_prize_policy_audit_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_prize_policy_issue_queue_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_prize_name_image_review_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_prize_name_image_patch_candidates_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_historical_roadmap_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_reissue_deduplication_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_reissue_decision_template_public.json", updated_files)
        self.assertIn("data/animation_category_split_review_public.json", updated_files)
        self.assertIn("data/animation_category_unmatched_keyword_review_public.json", updated_files)
        self.assertIn("data/source_detail_probe_public.json", updated_files)
        self.assertIn("data/source_detail_candidate_action_queue_public.json", updated_files)

        quality = reports.load_json(reports.QUALITY)
        self.assertEqual(
            quality["public_catalog_crosscheck"]["public_catalog"]["rows"],
            result["rows"],
        )
        self.assertEqual(
            quality["public_catalog_crosscheck"]["public_catalog"]["missing_enrichment"]["image_url"],
            result["missing"]["image_url"],
        )
        self.assertEqual(
            quality["public_catalog_crosscheck"]["comparison"]["public_image_missing_rows"],
            result["missing"]["image_url"],
        )
        self.assertEqual(
            quality["public_catalog_crosscheck"]["comparison"]["seed_image_missing_rows"],
            715,
        )
        self.assertEqual(
            quality["public_catalog_crosscheck"]["comparison"]["image_missing_delta"],
            -5,
        )
        image_candidates = reports.load_json(reports.IMAGE_CANDIDATES)
        self.assertEqual(image_candidates["summary"]["missing_images"], result["missing"]["image_url"])
        self.assertEqual(image_candidates["summary"]["rows"], result["rows"])
        image_backlog = reports.load_json(reports.IMAGE_BACKLOG)
        self.assertEqual(image_backlog["summary"]["missing_images"], result["missing"]["image_url"])
        self.assertEqual(
            image_backlog["candidate_review_summary"]["missing_images"],
            result["missing"]["image_url"],
        )
        self.assertEqual(quality["missing_image_priority"]["missing_image_rows"], result["missing"]["image_url"])
        self.assertEqual(
            quality["source_discovery_starter_queue"]["starter_queue_rows"],
            quality["missing_image_priority"]["missing_source_url_rows"],
        )
        self.assertTrue(
            quality["source_discovery_starter_queue"]["coverage_matches_missing_source_url_rows"]
        )
        self.assertIs(quality["source_discovery_starter_queue"]["auto_apply_enabled"], False)
        self.assertEqual(quality["image_backlog"]["missing_images"], result["missing"]["image_url"])
        self.assertEqual(
            quality["image_backlog"]["candidate_review_summary"]["missing_images"],
            result["missing"]["image_url"],
        )
        if reports.ANIMATE_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["animate_missing_image_search"]["missing_animate_image_rows"], 148)
            self.assertIs(quality["animate_missing_image_search"]["auto_apply_enabled"], False)
        if reports.GOODSMILE_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["goodsmile_missing_image_search"]["missing_goodsmile_image_rows"], 57)
            self.assertIs(quality["goodsmile_missing_image_search"]["auto_apply_enabled"], False)
        if reports.KOTOBUKIYA_MOVIC_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["kotobukiya_movic_missing_image_search"]["missing_target_image_rows"], 80)
            self.assertIs(quality["kotobukiya_movic_missing_image_search"]["auto_apply_enabled"], False)
        if reports.JUMP_FURYU_TAITO_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["jump_furyu_taito_missing_image_search"]["missing_target_image_rows"], 59)
            self.assertIs(quality["jump_furyu_taito_missing_image_search"]["auto_apply_enabled"], False)
        if reports.SECONDARY_OFFICIAL_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["secondary_official_missing_image_search"]["missing_target_image_rows"], 49)
            self.assertIs(quality["secondary_official_missing_image_search"]["auto_apply_enabled"], False)
        if reports.MANUAL_MISSING_IMAGE_SOURCE_DISCOVERY.exists():
            self.assertEqual(quality["manual_missing_image_source_discovery"]["manual_source_discovery_rows"], 112)
            self.assertIs(quality["manual_missing_image_source_discovery"]["auto_apply_enabled"], False)
        if reports.GENERIC_STOREFRONT_MISSING_IMAGE_SOURCE.exists():
            self.assertEqual(quality["generic_storefront_missing_image_source"]["generic_storefront_rows"], 5)
            self.assertIs(quality["generic_storefront_missing_image_source"]["auto_apply_enabled"], False)
        if reports.MISSING_IMAGE_REPORT_COVERAGE.exists():
            self.assertEqual(quality["missing_image_report_coverage"]["missing_image_rows"], result["missing"]["image_url"])
            self.assertEqual(quality["missing_image_report_coverage"]["unassigned_missing_image_rows"], 0)
            self.assertIs(quality["missing_image_report_coverage"]["auto_apply_enabled"], False)
        if reports.MISSING_IMAGE_ACTIONABILITY.exists():
            self.assertEqual(quality["missing_image_actionability"]["missing_image_rows"], result["missing"]["image_url"])
            self.assertEqual(quality["missing_image_actionability"]["unclassified_rows"], 0)
            actionability = reports.load_json(reports.MISSING_IMAGE_ACTIONABILITY)
            completion_plan = actionability["completion_plan"]
            manual_focus = actionability["manual_validation_focus"]
            execution_queue = actionability["execution_queue_summary"]
            self.assertEqual(manual_focus["auto_import_ready_rows"], 0)
            self.assertEqual(manual_focus["manual_validation_required_rows"], result["missing"]["image_url"])
            self.assertEqual(manual_focus["next_focus_lane"], "replace_generic_source_urls")
            self.assertEqual(manual_focus["next_focus_row_count"], 50)
            self.assertEqual(execution_queue["auto_import_ready_rows"], 0)
            self.assertEqual(execution_queue["open_missing_image_rows"], result["missing"]["image_url"])
            self.assertEqual(execution_queue["queued_rows_total"], 507)
            self.assertEqual(execution_queue["not_yet_queued_rows"], 203)
            self.assertEqual(execution_queue["not_yet_queued_rows_explained"], 203)
            self.assertEqual(execution_queue["unqueued_phase_rows_total"], 215)
            self.assertEqual(execution_queue["overlay_queue_rows"], 12)
            self.assertEqual(
                execution_queue["unqueued_rows_breakdown"][0]["phase_id"],
                "triage_remaining_source_discovery_backlog",
            )
            self.assertEqual(
                execution_queue["unqueued_rows_breakdown"][0][
                    "reported_not_yet_queued_rows"
                ],
                203,
            )
            self.assertEqual(execution_queue["completion_plan_status"], "balanced")
            self.assertEqual(execution_queue["next_queue"]["lane"], "replace_generic_source_urls")
            self.assertEqual(execution_queue["next_queue"]["template"], "catalog_image_attachment_confirmed_template_public.json")
            self.assertIs(execution_queue["next_queue"]["auto_apply_enabled"], False)
            self.assertEqual(
                manual_focus["blocked_summary"]["generic_source_url_replacement_rows"],
                50,
            )
            self.assertEqual(
                quality["missing_image_actionability"]["manual_validation_focus"][
                    "auto_import_ready_rows"
                ],
                0,
            )
            self.assertEqual(
                quality["missing_image_actionability"]["execution_queue_summary"][
                    "next_queue"
                ]["lane"],
                "replace_generic_source_urls",
            )
            self.assertEqual(
                quality["missing_image_actionability"]["blocking_dashboard"][
                    "status"
                ],
                "manual_evidence_required",
            )
            self.assertEqual(
                quality["missing_image_actionability"]["blocking_dashboard"][
                    "total_open_rows"
                ],
                result["missing"]["image_url"],
            )
            self.assertEqual(
                quality["missing_image_actionability"]["blocking_dashboard"][
                    "next_queue"
                ]["lane"],
                "replace_generic_source_urls",
            )
            self.assertEqual(completion_plan["total_open_rows"], result["missing"]["image_url"])
            self.assertEqual(completion_plan["phase_rows_total"], result["missing"]["image_url"])
            self.assertEqual(completion_plan["status"], "balanced")
            self.assertEqual(
                completion_plan["phase_count"],
                len(completion_plan["phases"]),
            )
            self.assertEqual(
                quality["missing_image_actionability"]["completion_plan_phase_rows_total"],
                result["missing"]["image_url"],
            )
            self.assertIs(completion_plan["automation_policy"]["auto_apply_catalog_changes"], False)
            self.assertIs(quality["missing_image_actionability"]["auto_apply_enabled"], False)
        self.assertEqual(
            quality["image_source_url_confirmed_template"]["template_items"],
            quality["image_attachment_action_queue"]["source_url_update_template_rows"],
        )
        self.assertIs(quality["image_source_url_confirmed_template"]["auto_apply_enabled"], False)
        image_attachment_import = reports.load_json(reports.IMAGE_ATTACHMENT_TEMPLATE_IMPORT_DRY_RUN)
        self.assertEqual(
            quality["image_attachment_template_import_dry_run"]["template_items"],
            image_attachment_import["summary"]["template_items"],
        )
        self.assertEqual(quality["image_attachment_template_import_dry_run"]["updated_rows"], 0)
        self.assertEqual(quality["image_attachment_template_import_dry_run"]["skipped_rows"], 73)
        self.assertEqual(quality["image_attachment_template_import_dry_run"]["manual_confirmed_rows"], 0)
        self.assertIs(quality["image_attachment_template_import_dry_run"]["auto_apply_enabled"], False)
        image_alignment = quality["image_attachment_queue_alignment"]
        self.assertEqual(image_alignment["missing_image_rows"], result["missing"]["image_url"])
        self.assertEqual(image_alignment["actionable_image_rows"], 73)
        self.assertEqual(image_alignment["queued_image_rows"], 73)
        self.assertEqual(image_alignment["unqueued_actionable_image_rows"], 0)
        self.assertEqual(image_alignment["source_url_update_required_rows"], 50)
        self.assertEqual(image_alignment["source_url_update_template_rows"], 50)
        self.assertEqual(image_alignment["source_url_update_template_batch_count"], 3)
        self.assertEqual(image_alignment["representative_image_review_required_rows"], 23)
        self.assertEqual(image_alignment["image_url_ready_rows"], 0)
        self.assertEqual(image_alignment["template_rows"], 73)
        self.assertEqual(image_alignment["template_confirmed_rows"], 0)
        self.assertEqual(image_alignment["dry_run_updated_rows"], 0)
        self.assertEqual(image_alignment["dry_run_skipped_rows"], 73)
        self.assertEqual(image_alignment["sample_queue_coverage"], 1.0)
        self.assertIs(image_alignment["auto_apply_enabled"], False)
        self.assertIs(image_alignment["manual_confirmation_required"], True)
        self.assertEqual(
            quality["source_url_update_queue_split"]["covered_rows"],
            quality["source_url_update_queue_split"]["source_url_update_required_rows"],
        )
        self.assertEqual(quality["source_url_update_queue_split"]["manual_search_required_rows"], 42)
        self.assertEqual(quality["source_url_update_queue_split"]["provider_missing_rows"], 5)
        self.assertEqual(quality["source_url_update_queue_split"]["candidate_review_rows"], 3)
        self.assertEqual(
            quality["source_url_update_queue_split"]["review_readiness"]["status"],
            "manual_review_required",
        )
        self.assertEqual(
            quality["source_url_update_queue_split"]["review_readiness"][
                "source_url_update_required_rows"
            ],
            50,
        )
        self.assertEqual(
            quality["source_url_update_queue_split"]["review_readiness"][
                "covered_rows"
            ],
            50,
        )
        self.assertEqual(
            quality["source_url_update_queue_split"]["review_readiness"][
                "manual_review_rows"
            ],
            50,
        )
        self.assertEqual(
            quality["source_url_update_queue_split"]["review_readiness"][
                "auto_apply_ready_rows"
            ],
            0,
        )
        self.assertEqual(
            quality["source_url_update_queue_split"]["review_readiness"][
                "next_queue"
            ]["lane"],
            "candidate_review_required",
        )
        self.assertEqual(
            quality["source_url_update_queue_split"]["review_readiness"][
                "next_queue"
            ]["rows"],
            3,
        )
        self.assertIs(quality["source_url_update_queue_split"]["auto_apply_enabled"], False)
        self.assertEqual(quality["manual_source_url_search_queue"]["manual_search_required_rows"], 42)
        self.assertEqual(quality["manual_source_url_search_queue"]["with_store_search_url"], 42)
        self.assertEqual(
            quality["manual_source_url_search_queue"]["review_readiness"]["status"],
            "manual_search_required",
        )
        self.assertEqual(
            quality["manual_source_url_search_queue"]["review_readiness"][
                "manual_review_rows"
            ],
            42,
        )
        self.assertEqual(
            quality["manual_source_url_search_queue"]["review_readiness"][
                "auto_apply_ready_rows"
            ],
            0,
        )
        self.assertIs(quality["manual_source_url_search_queue"]["auto_apply_enabled"], False)
        self.assertEqual(quality["provider_missing_source_url_queue"]["provider_missing_rows"], 5)
        self.assertEqual(quality["provider_missing_source_url_queue"]["with_store_search_url"], 5)
        self.assertEqual(
            quality["provider_missing_source_url_queue"]["review_readiness"][
                "status"
            ],
            "provider_or_manual_refresh_required",
        )
        self.assertEqual(
            quality["provider_missing_source_url_queue"]["review_readiness"][
                "manual_review_rows"
            ],
            5,
        )
        self.assertEqual(
            quality["provider_missing_source_url_queue"]["review_readiness"][
                "auto_apply_ready_rows"
            ],
            0,
        )
        self.assertIs(quality["provider_missing_source_url_queue"]["auto_apply_enabled"], False)
        self.assertEqual(quality["candidate_source_url_review_queue"]["candidate_review_rows"], 3)
        self.assertEqual(quality["candidate_source_url_review_queue"]["with_candidate_options"], 3)
        self.assertEqual(
            quality["candidate_source_url_review_queue"]["review_readiness"][
                "status"
            ],
            "manual_candidate_review_required",
        )
        self.assertEqual(
            quality["candidate_source_url_review_queue"]["review_readiness"][
                "auto_apply_ready_rows"
            ],
            0,
        )
        self.assertEqual(
            quality["candidate_source_url_review_queue"]["review_readiness"][
                "manual_review_rows"
            ],
            3,
        )
        self.assertIs(quality["candidate_source_url_review_queue"]["auto_apply_enabled"], False)
        self.assertEqual(quality["source_discovery_next_focus_pack"]["pack_items"], 20)
        self.assertEqual(quality["source_discovery_next_focus_pack"]["focus_pack_id"], "source-discovery-focus-001")
        self.assertIs(quality["source_discovery_next_focus_pack"]["auto_apply_enabled"], False)
        self.assertEqual(quality["source_discovery_next_focus_pack_import_dry_run"]["updated_rows"], 0)
        self.assertEqual(quality["source_discovery_next_focus_pack_import_dry_run"]["skipped_rows"], 20)
        self.assertIs(quality["source_discovery_next_focus_pack_import_dry_run"]["write"], False)
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["pack_items"],
            quality["source_discovery_next_focus_pack"]["pack_items"],
        )
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["fallback_bridge_rows"],
            13,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["manual_review_item_rows"],
            7,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["variant_detail_required_rows"],
            4,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["metadata_enrichment_template_rows"],
            4,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["metadata_field_import_template_rows"],
            12,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["metadata_field_import_supported_rows"],
            12,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_metadata_field_import_dry_run"]["template_items"],
            12,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_metadata_field_import_dry_run"]["updated_rows"],
            0,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_metadata_field_import_dry_run"]["skipped_rows"],
            12,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_metadata_field_import_dry_run"]["skip_reason_counts"],
            [["manual_confirmed_false", 12]],
        )
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["exact_candidate_confirmation_ready_items"],
            0,
        )
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["completion_readiness_status"],
            "fallback_search_required",
        )
        self.assertEqual(
            quality["source_discovery_next_focus_detail_candidates"]["auto_apply_ready_rows"],
            0,
        )
        self.assertGreater(
            len(quality["source_discovery_next_focus_detail_candidates"]["review_decision_counts"]),
            0,
        )
        self.assertGreater(
            len(quality["source_discovery_next_focus_detail_candidates"]["candidate_blocker_counts"]),
            0,
        )
        self.assertIs(
            quality["source_discovery_next_focus_detail_candidates"]["auto_apply_enabled"],
            False,
        )
        if reports.SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT.exists():
            self.assertEqual(
                quality["source_discovery_next_focus_pack_fetch_audit"]["pack_items"],
                quality["source_discovery_next_focus_pack"]["pack_items"],
            )
            self.assertIs(
                quality["source_discovery_next_focus_pack_fetch_audit"]["auto_apply_enabled"],
                False,
            )
        self.assertEqual(
            quality["source_discovery_next_focus_fallback_queue"]["queue_rows"],
            quality["source_discovery_next_focus_pack_fetch_audit"]["official_search_unavailable_rows"],
        )
        self.assertEqual(
            quality["source_discovery_next_focus_fallback_queue"]["review_table_rows"],
            quality["source_discovery_next_focus_fallback_queue"]["queue_rows"],
        )
        self.assertEqual(
            quality["source_discovery_next_focus_fallback_queue"]["manual_entry_template_rows"],
            quality["source_discovery_next_focus_fallback_queue"]["queue_rows"],
        )
        self.assertEqual(quality["source_discovery_next_focus_fallback_queue"]["source_confirmation_ready_rows"], 15)
        self.assertEqual(quality["source_discovery_next_focus_fallback_queue"]["metadata_backfill_required_rows"], 5)
        self.assertEqual(
            quality["source_discovery_next_focus_fallback_queue"]["variant_disambiguation_required_rows"],
            2,
        )
        self.assertEqual(quality["source_discovery_next_focus_exact_url_review_queue"]["queue_rows"], 15)
        self.assertEqual(
            quality["source_discovery_next_focus_exact_url_review_queue"]["blocked_identity_rows"],
            2,
        )
        self.assertEqual(quality["source_discovery_next_focus_identity_backfill_queue"]["queue_rows"], 2)
        self.assertEqual(
            quality["source_discovery_next_focus_identity_backfill_queue"]["exact_url_review_ready_rows"],
            15,
        )
        identity_candidate_queue = quality[
            "source_discovery_next_focus_identity_candidate_review_queue"
        ]
        self.assertEqual(identity_candidate_queue["queue_rows"], 2)
        self.assertEqual(identity_candidate_queue["items_with_candidates"], 2)
        self.assertEqual(identity_candidate_queue["candidate_rows"], 5)
        self.assertEqual(identity_candidate_queue["manual_confirmed_rows"], 0)
        self.assertIs(identity_candidate_queue["auto_apply_enabled"], False)
        self.assertIs(quality["source_discovery_next_focus_fallback_queue"]["auto_apply_enabled"], False)
        self.assertEqual(quality["source_discovery_next_focus_fallback_import_dry_run"]["updated_rows"], 0)
        self.assertEqual(
            quality["source_discovery_next_focus_fallback_import_dry_run"]["skipped_rows"],
            quality["source_discovery_next_focus_fallback_queue"]["queue_rows"],
        )
        self.assertIs(quality["source_discovery_next_focus_fallback_import_dry_run"]["write"], False)
        self.assertEqual(quality["source_discovery_focus_packs"]["focus_pack_count"], 23)
        self.assertEqual(quality["source_discovery_focus_packs"]["remaining_focus_review_rows"], 417)
        self.assertEqual(
            quality["source_discovery_focus_packs"]["focus_source_rows"],
            quality["source_discovery_completion_roadmap"]["focus_source_rows"],
        )
        self.assertEqual(quality["source_discovery_completion_roadmap"]["queued_source_rows"], 632)
        reissue_deduplication = quality["ichiban_kuji_reissue_deduplication"]
        self.assertEqual(reissue_deduplication["reissue_duplicate_groups"], 149)
        self.assertEqual(reissue_deduplication["removed_rows"], 165)
        self.assertEqual(reissue_deduplication["missing_local_image_files"], 0)
        self.assertTrue(reissue_deduplication["summary_matches_top_level_counts"])
        self.assertFalse(
            reissue_deduplication["automation_policy"]["auto_merge_enabled"]
        )
        self.assertTrue(
            reissue_deduplication["automation_policy"][
                "manual_review_required_before_mutation"
            ]
        )
        reissue_decision_template = quality["ichiban_kuji_reissue_decision_template"]
        self.assertEqual(reissue_decision_template["item_template_rows"], 20)
        self.assertEqual(reissue_decision_template["campaign_template_rows"], 4)
        self.assertEqual(reissue_decision_template["manual_confirmed_item_rows"], 0)
        self.assertEqual(reissue_decision_template["manual_confirmed_campaign_rows"], 0)
        self.assertEqual(
            reissue_decision_template["item_review_lane_counts"],
            [["same_campaign_family_reissue_review", 20]],
        )
        self.assertEqual(
            reissue_decision_template["campaign_review_lane_counts"],
            [["campaign_pair_first", 4]],
        )
        self.assertEqual(
            reissue_decision_template["same_campaign_family_reissue_item_rows"],
            20,
        )
        self.assertFalse(reissue_decision_template["auto_merge_enabled"])
        self.assertFalse(reissue_decision_template["auto_delete_enabled"])
        self.assertTrue(
            reissue_decision_template["manual_review_required_before_mutation"]
        )
        self.assertEqual(quality["source_discovery_completion_roadmap"]["current_focus_pack_rows"], 20)
        self.assertEqual(
            quality["source_discovery_completion_roadmap"]["completion_readiness_status"],
            "current_focus_fallback_review_required",
        )
        self.assertEqual(
            quality["source_discovery_completion_roadmap"]["completion_readiness"]["status"],
            "current_focus_fallback_review_required",
        )
        self.assertEqual(
            quality["source_discovery_completion_roadmap"]["completion_readiness"]["current_focus_fallback_rows"],
            quality["source_discovery_next_focus_fallback_queue"]["queue_rows"],
        )
        self.assertEqual(
            quality["source_discovery_completion_roadmap"]["completion_readiness"]["next_queue"]["queue_rows"],
            17,
        )
        self.assertEqual(
            quality["source_discovery_completion_roadmap"]["completion_readiness"]["next_safe_phase"],
            "review_fallback_queue_and_fill_exact_manual_confirmed_source_urls",
        )
        self.assertEqual(
            quality["source_discovery_completion_roadmap"]["auto_apply_ready_rows"],
            0,
        )
        self.assertGreaterEqual(quality["source_discovery_completion_roadmap"]["top_10_store_coverage"], 0.8)
        self.assertIs(quality["source_discovery_completion_roadmap"]["auto_apply_enabled"], False)
        self.assertEqual(quality["ensky_cache_coverage"]["missing_ensky_image_rows"], 142)
        self.assertIs(quality["ensky_cache_coverage"]["auto_apply_enabled"], False)
        if reports.ENSKY_SEARCH_PAGE_PROBE.exists():
            self.assertEqual(quality["ensky_search_page_probe"]["processed_rows"], 30)
            self.assertIs(quality["ensky_search_page_probe"]["auto_apply_enabled"], False)
        if reports.STELLIVE_FANDING_CANDIDATES.exists():
            self.assertGreater(quality["stellive_fanding_candidates"]["missing_image_candidate_rows"], 0)
            self.assertIs(quality["stellive_fanding_candidates"]["auto_apply_enabled"], False)
        if reports.SOURCE_DISCOVERY_STORE_BOTTLENECKS.exists():
            source_alignment = quality["source_discovery_queue_alignment"]
            self.assertEqual(source_alignment["missing_source_url_rows"], 637)
            self.assertEqual(source_alignment["actionable_source_rows"], 632)
            self.assertEqual(source_alignment["queued_source_rows"], 632)
            self.assertEqual(source_alignment["source_discovery_template_rows"], 632)
            self.assertEqual(source_alignment["source_discovery_template_batch_count"], 40)
            self.assertEqual(source_alignment["focus_template_confirmed_rows"], 0)
            self.assertIs(source_alignment["auto_apply_enabled"], False)
            self.assertIs(source_alignment["manual_confirmation_required"], True)
            self.assertEqual(
                quality["source_discovery_store_bottlenecks"]["queued_source_rows"],
                quality["source_discovery_action_queue"]["queued_source_rows"],
            )
            self.assertGreater(quality["source_discovery_store_bottlenecks"]["store_count"], 0)
            self.assertIs(quality["source_discovery_store_bottlenecks"]["auto_apply_enabled"], False)
        if reports.SOURCE_DETAIL.exists():
            source_detail_summary = reports.load_json(reports.SOURCE_DETAIL)["summary"]
            self.assertEqual(
                quality["source_detail_candidate_probe"]["candidate_review_rows"],
                source_detail_summary.get(
                    "unique_review_candidate_rows",
                    source_detail_summary["candidate_review_rows"],
                ),
            )
            self.assertIs(quality["source_detail_candidate_probe"]["auto_apply_enabled"], False)
        if reports.SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.exists():
            source_detail_action = reports.load_json(reports.SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE)
            self.assertEqual(
                quality["source_detail_candidate_action_queue"]["candidate_action_rows"],
                source_detail_action["summary"]["candidate_action_rows"],
            )
            self.assertEqual(
                quality["source_detail_candidate_action_queue"]["manual_confirmation_shortlist_rows"],
                source_detail_action["summary"]["manual_confirmation_shortlist_rows"],
            )
            self.assertEqual(
                quality["source_detail_candidate_action_queue"]["candidate_count_review_required_rows"],
                source_detail_action["summary"].get("candidate_count_review_required_rows", 0),
            )
            self.assertEqual(
                quality["source_detail_candidate_action_queue"]["completion_readiness_status"],
                source_detail_action["summary"]["completion_readiness_status"],
            )
            self.assertEqual(
                quality["source_detail_candidate_action_queue"]["identity_blocked_source_image_pair_rows"],
                source_detail_action["summary"]["identity_blocked_source_image_pair_rows"],
            )
            self.assertEqual(quality["source_detail_candidate_action_queue"]["auto_apply_ready_rows"], 0)
            self.assertEqual(quality["source_detail_candidate_action_queue"]["manual_confirmed_true"], 0)
            self.assertIs(quality["source_detail_candidate_action_queue"]["auto_apply_enabled"], False)
        if reports.GOTOUCHI_REPRESENTATIVE_IMAGE_ATTACHMENT.exists():
            gotouchi_attachment = reports.load_json(reports.GOTOUCHI_REPRESENTATIVE_IMAGE_ATTACHMENT)
            self.assertEqual(
                quality["gotouchi_representative_image_attachment"]["representative_attachment_rows"],
                gotouchi_attachment["summary"]["representative_attachment_rows"],
            )
            self.assertEqual(quality["gotouchi_representative_image_attachment"]["manual_confirmed_true"], 0)
            self.assertIs(quality["gotouchi_representative_image_attachment"]["auto_apply_enabled"], False)
        self.assertEqual(quality["gotouchi_official_candidate_review_queue"]["review_rows"], 23)
        self.assertEqual(quality["gotouchi_official_candidate_review_queue"]["with_candidate_options"], 17)
        self.assertEqual(quality["gotouchi_official_candidate_review_queue"]["without_candidate_options"], 6)
        self.assertIs(quality["gotouchi_official_candidate_review_queue"]["auto_apply_enabled"], False)
        if reports.DEDUPLICATION_FAST_REVIEW.exists():
            dedupe_action = reports.load_json(reports.DEDUPLICATION_ACTION_QUEUE)
            dedupe_action_summary = dedupe_action["summary"]
            self.assertEqual(
                quality["deduplication_action_queue"]["completion_readiness_status"],
                dedupe_action_summary["completion_readiness_status"],
            )
            self.assertEqual(quality["deduplication_action_queue"]["auto_merge_ready_groups"], 0)
            self.assertEqual(quality["deduplication_action_queue"]["auto_delete_ready_groups"], 0)
            self.assertEqual(
                quality["deduplication_action_queue"]["explicit_keep_drop_required_groups"],
                dedupe_action_summary["explicit_keep_drop_required_groups"],
            )
            self.assertEqual(
                quality["deduplication_action_queue"]["ichiban_reissue_work_order_rows"],
                dedupe_action_summary["ichiban_reissue_work_order_rows"],
            )
            self.assertEqual(quality["deduplication_fast_review"]["fast_review_groups"], 42)
            self.assertEqual(quality["deduplication_fast_review"]["manual_confirmed_true"], 0)
            self.assertIs(quality["deduplication_fast_review"]["auto_delete_enabled"], False)
            alignment = quality["deduplication_queue_alignment"]
            self.assertEqual(alignment["duplicate_review_groups"], 61)
            self.assertEqual(alignment["actionable_groups"], 48)
            self.assertEqual(alignment["queued_groups"], 48)
            self.assertEqual(alignment["non_action_queue_groups"], 13)
            self.assertEqual(alignment["fast_review_groups"], 42)
            self.assertEqual(alignment["held_for_later_groups"], 6)
            self.assertEqual(alignment["name_duplicate_protected_groups"], 504)
            self.assertEqual(
                alignment["ichiban_campaign_or_reissue_protected_groups"],
                479,
            )
            self.assertEqual(alignment["queue_coverage"], 1.0)
            self.assertFalse(alignment["auto_merge_enabled"])
            self.assertFalse(alignment["auto_delete_enabled"])
            self.assertTrue(alignment["manual_confirmation_required"])
        if reports.DEDUPLICATION_CONFIRMED_TEMPLATE.exists():
            dedupe_template = reports.load_json(reports.DEDUPLICATION_CONFIRMED_TEMPLATE)
            self.assertEqual(
                quality["deduplication_confirmed_template"]["template_items"],
                dedupe_template["summary"]["template_items"],
            )
            self.assertEqual(quality["deduplication_confirmed_template"]["manual_confirmed_rows"], 0)
            self.assertIs(quality["deduplication_confirmed_template"]["auto_delete_enabled"], False)
        if reports.DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN.exists():
            dedupe_dry_run = reports.load_json(reports.DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN)
            self.assertEqual(
                quality["deduplication_template_import_dry_run"]["template_items"],
                dedupe_dry_run["summary"]["template_items"],
            )
            self.assertEqual(quality["deduplication_template_import_dry_run"]["updated_rows"], 0)
            self.assertEqual(quality["deduplication_template_import_dry_run"]["skipped_rows"], 42)
            self.assertEqual(quality["deduplication_template_import_dry_run"]["manual_confirmed_rows"], 0)
            self.assertIs(quality["deduplication_template_import_dry_run"]["write"], False)
            self.assertIs(quality["deduplication_template_import_dry_run"]["auto_delete_enabled"], False)
        self.assertGreaterEqual(quality["name_duplicate_audit"]["name_duplicate_groups"], 1)
        self.assertIs(quality["name_duplicate_audit"]["auto_merge_enabled"], False)
        self.assertIs(quality["name_duplicate_audit"]["auto_delete_enabled"], False)
        self.assertEqual(quality["animation_category_coverage_audit"]["status"], "pass")
        self.assertEqual(quality["animation_category_coverage_audit"]["unknown_category_count"], 0)
        self.assertEqual(quality["animation_category_coverage_audit"]["failed_check_count"], 0)
        self.assertIs(quality["animation_category_coverage_audit"]["auto_apply_enabled"], False)
        animation_categories = reports.load_json(reports.ANIMATION_CATEGORIES)
        normalization_queue = animation_categories["normalization_review_queue"]
        self.assertEqual(
            quality["animation_category_review"]["normalization_review_queue_count"],
            len(normalization_queue),
        )
        self.assertEqual(quality["animation_category_review"]["normalization_review_queue_count"], 4)
        self.assertEqual(
            quality["animation_category_review"]["normalization_review_queue_rows"],
            sum(int(row.get("affected_catalog_rows") or 0) for row in normalization_queue),
        )
        self.assertEqual(quality["animation_category_review"]["manual_review_categories"], 4)
        self.assertEqual(quality["animation_category_review"]["manual_review_rows"], 36)
        self.assertEqual(
            quality["animation_category_review"]["category_readiness_status"],
            "normalization_review_required",
        )
        self.assertEqual(
            quality["animation_category_review"]["category_readiness"]["status"],
            "normalization_review_required",
        )
        self.assertEqual(
            quality["animation_category_review"]["category_readiness"]["manual_review_rows"],
            36,
        )
        self.assertEqual(
            quality["animation_category_review"]["category_readiness"]["next_review_item"]["category"],
            normalization_queue[0]["category"],
        )
        self.assertEqual(
            quality["animation_category_review"]["category_readiness"]["next_review_item"]["suggested_category"],
            normalization_queue[0]["suggested_category"],
        )
        self.assertEqual(quality["animation_category_review"]["auto_apply_ready_rows"], 0)
        self.assertTrue(quality["animation_category_review"]["folder_visual_coverage_ready"])
        self.assertEqual(
            animation_categories["category_readiness"]["next_safe_phase"],
            "confirm_category_normalization_before_import",
        )
        self.assertIn(
            "canonical_category_normalization_manually_confirmed",
            animation_categories["category_readiness"]["blocked_reasons"],
        )
        self.assertFalse(normalization_queue[0]["auto_apply_enabled"])
        self.assertEqual(
            normalization_queue[0]["mapping_mode"],
            "canonical_category_normalization_review",
        )
        self.assertIn(
            "source_category_should_be_preserved_as_sub_series_or_note",
            normalization_queue[0]["required_evidence"],
        )
        if reports.ICHIIBAN_KUJI_METADATA_FAST_REVIEW.exists():
            self.assertEqual(quality["ichiban_kuji_metadata_fast_review"]["fast_review_campaigns"], 20)
            self.assertEqual(quality["ichiban_kuji_metadata_fast_review"]["manual_confirmed_true"], 0)
            self.assertIs(quality["ichiban_kuji_metadata_fast_review"]["auto_apply_enabled"], False)
        if reports.ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.exists():
            prize_audit = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT)
            self.assertEqual(
                quality["ichiban_kuji_prize_policy_audit"]["last_one_nonzero_price_rows"],
                prize_audit["summary"]["last_one_nonzero_price_rows"],
            )
            self.assertEqual(quality["ichiban_kuji_prize_policy_audit"]["double_chance_nonzero_price_rows"], 0)
            self.assertEqual(
                quality["ichiban_kuji_prize_policy_audit"]["incomplete_numbered_variant_prize_label_groups"],
                prize_audit["summary"]["incomplete_numbered_variant_prize_label_groups"],
            )
            self.assertIs(
                quality["ichiban_kuji_prize_policy_audit"]["numbered_variant_coverage_policy_pass"],
                prize_audit["summary"]["numbered_variant_coverage_policy_pass"],
            )
            self.assertEqual(
                quality["ichiban_kuji_prize_policy_audit"]["numbered_variant_created_rows"],
                prize_audit["summary"]["numbered_variant_created_rows"],
            )
            self.assertEqual(
                quality["ichiban_kuji_prize_policy_audit"]["numbered_variant_application_skipped_rows"],
                prize_audit["summary"]["numbered_variant_application_skipped_rows"],
            )
            self.assertEqual(
                quality["ichiban_kuji_prize_policy_audit"]["prize_policy_review_batch_count"],
                prize_audit["summary"]["prize_policy_review_batch_count"],
            )
            self.assertIs(quality["ichiban_kuji_prize_policy_audit"]["zero_price_exception_policy_pass"], True)
            self.assertIs(quality["ichiban_kuji_prize_policy_audit"]["auto_apply_enabled"], False)
        self.assertEqual(quality["ichiban_kuji_prize_policy_issue_queue"]["issue_rows"], 20)
        self.assertEqual(quality["ichiban_kuji_prize_policy_issue_queue"]["zero_price_violation_rows"], 0)
        self.assertIs(quality["ichiban_kuji_prize_policy_issue_queue"]["zero_price_exception_policy_pass"], True)
        self.assertEqual(
            quality["ichiban_kuji_prize_policy_issue_queue"]["unnumbered_multi_item_prize_review_groups"],
            0,
        )
        self.assertEqual(
            quality["ichiban_kuji_prize_policy_issue_queue"]["protected_unnumbered_multi_item_prize_groups"],
            6,
        )
        self.assertEqual(
            quality["ichiban_kuji_prize_policy_issue_queue"]["probable_reissue_work_order_rows"],
            20,
        )
        self.assertEqual(
            quality["ichiban_kuji_prize_policy_issue_queue"]["completion_readiness_status"],
            "ichiban_reissue_review_required",
        )
        self.assertEqual(
            quality["ichiban_kuji_prize_policy_issue_queue"]["completion_readiness"]["status"],
            "ichiban_reissue_review_required",
        )
        self.assertIs(
            quality["ichiban_kuji_prize_policy_issue_queue"]["completion_readiness"][
                "zero_price_policy_ready"
            ],
            True,
        )
        self.assertIs(
            quality["ichiban_kuji_prize_policy_issue_queue"]["completion_readiness"][
                "numbered_variant_policy_ready"
            ],
            True,
        )
        self.assertEqual(
            quality["ichiban_kuji_prize_policy_issue_queue"]["completion_readiness"][
                "auto_apply_ready_rows"
            ],
            0,
        )
        self.assertIn(
            "same_name_across_campaign_urls_requires_keep_or_merge_decision",
            quality["ichiban_kuji_prize_policy_issue_queue"]["completion_readiness"][
                "blocked_reasons"
            ],
        )
        self.assertEqual(
            quality["ichiban_kuji_prize_policy_issue_queue"]["numbered_variant_created_rows"],
            2518,
        )
        self.assertIs(quality["ichiban_kuji_prize_policy_issue_queue"]["auto_apply_enabled"], False)
        self.assertIs(quality["ichiban_kuji_prize_policy_issue_queue"]["auto_delete_enabled"], False)
        roadmap = reports.load_json(reports.ICHIIBAN_KUJI_HISTORICAL_ROADMAP)
        self.assertEqual(
            quality["ichiban_kuji_historical_roadmap"]["roadmap_phase_count"],
            len(roadmap["phases"]),
        )
        self.assertEqual(
            quality["ichiban_kuji_historical_roadmap"]["metadata_actionable_campaigns"],
            roadmap["summary"]["metadata_actionable_campaigns"],
        )
        self.assertEqual(
            quality["ichiban_kuji_historical_roadmap"]["completion_readiness"][
                "status"
            ],
            "manual_review_required",
        )
        self.assertIs(
            quality["ichiban_kuji_historical_roadmap"]["completion_readiness"][
                "zero_price_policy_ready"
            ],
            True,
        )
        ichiban_history = reports.load_json(reports.ICHIIBAN_KUJI_HISTORY)
        self.assertEqual(
            ichiban_history["summary"]["official_price_jpy_review_queue_campaigns"],
            41,
        )
        self.assertEqual(
            ichiban_history["summary"][
                "missing_official_price_jpy_campaign_groups"
            ],
            41,
        )
        self.assertTrue(
            ichiban_history["summary"][
                "metadata_review_queue_covers_all_price_campaign_groups"
            ]
        )
        self.assertEqual(
            ichiban_history["metadata_resolution_summary"][
                "price_resolution_unit"
            ],
            "campaign_draw_price",
        )
        self.assertEqual(
            ichiban_history["summary"]["metadata_resolution_readiness_status"],
            "manual_campaign_metadata_review_required",
        )
        self.assertEqual(
            ichiban_history["summary"]["metadata_manual_review_campaigns"],
            42,
        )
        self.assertEqual(
            ichiban_history["summary"]["metadata_auto_apply_ready_campaigns"],
            0,
        )
        self.assertEqual(
            ichiban_history["metadata_resolution_readiness"]["status"],
            "manual_campaign_metadata_review_required",
        )
        self.assertEqual(
            ichiban_history["metadata_resolution_readiness"]["manual_review_campaigns"],
            ichiban_history["summary"]["campaign_metadata_review_queue_rows"],
        )
        self.assertEqual(
            ichiban_history["metadata_resolution_readiness"]["next_review_campaign"]["slug"],
            "jujutsu-o",
        )
        self.assertIn(
            "release_date",
            ichiban_history["metadata_resolution_readiness"]["next_review_campaign"][
                "missing_fields"
            ],
        )
        self.assertEqual(
            quality["ichiban_kuji_history"]["metadata_resolution_readiness"]["next_safe_phase"],
            "verify_labeled_official_release_date",
        )
        self.assertIn(
            "do not overwrite zero-price Last One or Double Chance exception rows",
            ichiban_history["metadata_resolution_summary"]["guardrails"],
        )
        self.assertEqual(
            roadmap["summary"]["official_price_jpy_review_queue_campaigns"],
            41,
        )
        self.assertTrue(
            roadmap["summary"][
                "metadata_review_queue_covers_all_price_campaign_groups"
            ]
        )
        self.assertIs(roadmap["summary"]["auto_apply_enabled"], False)
        self.assertIs(roadmap["summary"]["auto_merge_enabled"], False)
        self.assertIs(roadmap["summary"]["auto_delete_enabled"], False)
        if reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.exists():
            prize_name_image = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW)
            prize_name_image_summary = prize_name_image.get("summary", {})
            self.assertEqual(
                quality["ichiban_kuji_prize_name_image_review"]["review_rows"],
                prize_name_image_summary.get("review_rows"),
            )
            self.assertEqual(
                quality["ichiban_kuji_prize_name_image_review"]["multi_item_prize_rank_groups"],
                prize_name_image_summary.get("multi_item_prize_rank_groups"),
            )
            self.assertIs(quality["ichiban_kuji_prize_name_image_review"]["auto_apply_enabled"], False)
        if reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.exists():
            patch_candidates = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES)
            patch_candidates_summary = patch_candidates.get("summary", {})
            self.assertEqual(
                quality["ichiban_kuji_prize_name_image_patch_candidates"]["candidate_rows"],
                patch_candidates_summary.get("candidate_rows"),
            )
            self.assertEqual(
                quality["ichiban_kuji_prize_name_image_patch_candidates"]["blocked_rows"],
                patch_candidates_summary.get("blocked_rows"),
            )
            self.assertIs(
                quality["ichiban_kuji_prize_name_image_patch_candidates"]["auto_apply_enabled"],
                False,
            )

    def test_all_public_json_files_are_parseable_and_safe_for_pages(self):
        public_files = reports.discover_public_json_files()
        self.assertGreaterEqual(len(public_files), 30)
        self.assertIn(reports.PUBLIC_CATALOG, public_files)
        self.assertIn(reports.OPERATIONS_REPORT, public_files)

        validation = reports.validate_all_public_json_files()
        self.assertEqual(validation["status"], "pass", validation["findings"])
        self.assertEqual(validation["checked_files"], len(public_files))

    def test_catalog_currency_invariants_reject_jpy_price_with_krw_purchase(self):
        findings = reports.catalog_currency_invariant_findings(
            {
                "items": [
                    {
                        "catalog_index": 7,
                        "name_ko": "sample",
                        "official_price_jpy": 1980,
                        "default_purchase": {
                            "price": 1980,
                            "currency": "KRW",
                        },
                    }
                ]
            }
        )

        self.assertEqual(
            findings,
            ["catalog row 7 has official_price_jpy but default_purchase.currency=KRW"],
        )

    def test_catalog_currency_invariants_accept_jpy_price_with_jpy_purchase(self):
        findings = reports.catalog_currency_invariant_findings(
            {
                "items": [
                    {
                        "catalog_index": 8,
                        "name_ko": "sample",
                        "official_price_jpy": 1980,
                        "default_purchase": {
                            "price": 1980,
                            "currency": "JPY",
                        },
                    }
                ]
            }
        )

        self.assertEqual(findings, [])

    def test_execution_plan_open_queues_match_operations(self):
        operations = reports.load_json(reports.OPERATIONS_REPORT)
        execution_plan = reports.load_json(reports.EXECUTION_PLAN)

        self.assertEqual(
            execution_plan.get("summary", {}).get("open_review_queues"),
            operations.get("summary", {}).get("open_review_queues"),
        )

    def test_public_meta_counts_match_catalog(self):
        catalog = reports.load_json(reports.PUBLIC_CATALOG)
        public_meta = reports.load_json(reports.PUBLIC_META)
        rows = len(catalog.get("items", []))

        self.assertEqual(public_meta.get("row_count"), rows)
        self.assertEqual(public_meta.get("total_items"), rows)
        self.assertEqual(public_meta.get("generated_at"), catalog.get("meta", {}).get("generated_at"))

    def test_published_reports_keep_manual_review_guards(self):
        operations = reports.load_json(reports.OPERATIONS_REPORT)
        source_discovery = reports.load_json(reports.SOURCE_DISCOVERY)
        generic_candidates = reports.load_json(reports.GENERIC_SOURCE_PATCH_CANDIDATES)
        deduplication = reports.load_json(reports.DEDUPLICATION)

        scorecard = operations.get("workstream_scorecard", [])
        self.assertGreater(len(scorecard), 0)
        self.assertTrue(all(row.get("auto_apply_enabled") is False for row in scorecard))

        source_items = source_discovery.get("items", [])
        self.assertGreater(len(source_items), 0)
        self.assertTrue(all(item.get("auto_apply_enabled") is False for item in source_items))
        self.assertTrue(all("evidence_required" in item for item in source_items))
        self.assertTrue(all("acceptance_rule" in item for item in source_items))

        generic_summary = generic_candidates.get("summary", {})
        generic_items = generic_candidates.get("items", [])
        self.assertIs(generic_summary.get("auto_apply_enabled"), False)
        self.assertEqual(generic_summary.get("candidate_rows"), len(generic_items))

        requested_focus = reports.load_json(reports.REQUESTED_FOCUS)
        focus_summary = requested_focus.get("summary", {})
        focus_topics = requested_focus.get("topics", [])
        self.assertIs(focus_summary.get("auto_apply_enabled"), False)
        self.assertEqual(focus_summary.get("topic_count"), len(focus_topics))
        self.assertTrue(all(topic.get("auto_apply_enabled") is False for topic in focus_topics))

        danganronpa_media = reports.load_json(reports.DANGANRONPA_MISSING_MEDIA)
        danganronpa_summary = danganronpa_media.get("summary", {})
        danganronpa_items = danganronpa_media.get("items", [])
        danganronpa_batches = danganronpa_media.get("review_batches", [])
        danganronpa_template = danganronpa_media.get("confirmed_patch_template", [])
        self.assertIs(danganronpa_summary.get("auto_apply_enabled"), False)
        self.assertEqual(danganronpa_summary.get("missing_media_rows"), len(danganronpa_items))
        self.assertEqual(danganronpa_summary.get("review_batch_count"), len(danganronpa_batches))
        self.assertEqual(danganronpa_summary.get("confirmed_patch_template_rows"), len(danganronpa_template))
        self.assertEqual(
            danganronpa_summary.get("confirmed_patch_template_pending_rows"),
            len(danganronpa_template),
        )
        self.assertEqual(
            danganronpa_summary.get("missing_media_rows"),
            sum(int(batch.get("rows") or 0) for batch in danganronpa_batches),
        )
        self.assertTrue(all(item.get("auto_apply_enabled") is False for item in danganronpa_items))
        self.assertTrue(all(batch.get("auto_apply_enabled") is False for batch in danganronpa_batches))
        self.assertTrue(all(row.get("auto_apply_enabled") is False for row in danganronpa_template))
        self.assertTrue(all("manual_confirmed_source_url" in row for row in danganronpa_template))
        self.assertTrue(all("manual_confirmed_image_url" in row for row in danganronpa_template))

        danganronpa_dry_run = reports.load_json(reports.DANGANRONPA_PATCH_TEMPLATE_DRY_RUN)
        danganronpa_dry_summary = danganronpa_dry_run.get("summary", {})
        danganronpa_dry_items = danganronpa_dry_run.get("items", [])
        self.assertIs(danganronpa_dry_summary.get("auto_apply_enabled"), False)
        self.assertEqual(
            danganronpa_dry_summary.get("template_rows"),
            danganronpa_summary.get("confirmed_patch_template_rows"),
        )
        self.assertEqual(danganronpa_dry_summary.get("template_rows"), len(danganronpa_dry_items))
        self.assertEqual(danganronpa_dry_summary.get("ready_rows"), 0)
        self.assertEqual(danganronpa_dry_summary.get("skipped_rows"), len(danganronpa_dry_items))
        self.assertEqual(danganronpa_dry_summary.get("blocked_rows"), 0)
        self.assertTrue(all(item.get("auto_apply_enabled") is False for item in danganronpa_dry_items))
        self.assertTrue(all(item.get("status") == "skipped_pending_manual_confirmation" for item in danganronpa_dry_items))

        dedupe_summary = deduplication.get("summary", {})
        source_url_exclusions = dedupe_summary.get("source_url_exclusions", {})
        self.assertGreater(source_url_exclusions.get("shared_source_url_value_groups", 0), 0)
        self.assertGreater(source_url_exclusions.get("excluded_shared_source_url_value_groups", 0), 0)
        self.assertLess(
            source_url_exclusions.get("source_url_name_matched_review_groups", 0),
            source_url_exclusions.get("shared_source_url_value_groups", 0),
        )
        self.assertIs(deduplication.get("automation_policy", {}).get("auto_delete"), False)
        self.assertIn(
            "broad same-source-url matches",
            deduplication.get("automation_policy", {}).get("excluded", ""),
        )

    def test_shared_campaign_urls_do_not_become_dedupe_groups(self):
        items = [
            {
                "catalog_index": 1,
                "name_ko": "이치방쿠지 샘플 A상 피규어",
                "category": "피규어",
                "source_url": "https://1kuji.com/products/sample",
                "image_url": "https://example.com/a.jpg",
            },
            {
                "catalog_index": 2,
                "name_ko": "이치방쿠지 샘플 B상 쿠션",
                "category": "생활잡화",
                "source_url": "https://1kuji.com/products/sample",
                "image_url": "https://example.com/b.jpg",
            },
        ]

        dedupe = reports.build_deduplication_public(items)
        self.assertEqual(dedupe["summary"]["duplicate_groups"], 0)
        self.assertEqual(
            dedupe["summary"]["source_url_exclusions"]["shared_source_url_value_groups"],
            1,
        )
        self.assertEqual(
            dedupe["summary"]["source_url_exclusions"]["excluded_shared_source_url_value_groups"],
            1,
        )

    def test_name_duplicate_audit_protects_reissues_and_variants(self):
        items = [
            {
                "catalog_index": 1,
                "name_ko": "이치방쿠지 샘플 A상 인형",
                "name_ja": "一番くじ サンプル A賞 ぬいぐるみ",
                "category": "인형",
                "source_url": "https://1kuji.com/products/sample-2024",
                "source_store": "이치방쿠지",
            },
            {
                "catalog_index": 2,
                "name_ko": "이치방쿠지 샘플 A상 인형",
                "name_ja": "一番くじ サンプル A賞 ぬいぐるみ",
                "category": "인형",
                "source_url": "https://1kuji.com/products/sample-2025",
                "source_store": "이치방쿠지",
            },
            {
                "catalog_index": 3,
                "name_ko": "샘플 아크릴 키링",
                "name_ja": "サンプル アクリルキーホルダー",
                "category": "아크릴 키링",
                "barcode": "111",
                "source_url": "https://example.com/a",
            },
            {
                "catalog_index": 4,
                "name_ko": "샘플 아크릴 키링",
                "name_ja": "サンプル アクリルキーホルダー",
                "category": "아크릴 키링",
                "barcode": "222",
                "source_url": "https://example.com/b",
            },
        ]

        audit = reports.build_name_duplicate_audit_public(items)
        summary = audit["summary"]
        lanes = {row["lane"] for row in audit["groups"]}

        self.assertEqual(summary["name_duplicate_groups"], 2)
        self.assertEqual(summary["protected_groups"], 2)
        self.assertIn("ichiban_campaign_or_reissue_protected", lanes)
        self.assertIn("same_name_distinct_barcode_variant_protected", lanes)
        self.assertIs(summary["auto_merge_enabled"], False)
        self.assertIs(summary["auto_delete_enabled"], False)

    def test_source_discovery_completion_roadmap_summarizes_next_steps(self):
        roadmap = reports.build_source_discovery_completion_roadmap_public(
            generated_at="2026-01-01T00:00:00Z",
            missing_image_actionability={
                "summary": {
                    "missing_image_rows": 10,
                    "source_first_rows": 8,
                }
            },
            source_discovery_action_queue={
                "summary": {
                    "queued_source_rows": 8,
                },
                "source_store_workstreams": [
                    {
                        "source_store": "스토어A",
                        "first_primary_review_url": "https://example.com/action-search",
                        "first_primary_review_url_kind": "official_search_url",
                        "official_search_url_count": 5,
                        "fallback_web_search_url_count": 0,
                    }
                ],
            },
            source_discovery_store_bottlenecks={
                "summary": {
                    "top_10_store_rows": 6,
                },
                "stores": [
                    {
                        "source_store": "스토어A",
                        "rows": 5,
                        "top_category": "인형",
                        "top_allowed_source_domain": "example.com",
                        "first_batch_id": "batch-1",
                    },
                    {
                        "source_store": "스토어B",
                        "rows": 1,
                    },
                ],
            },
            source_discovery_focus_packs={
                "summary": {
                    "focus_source_rows": 5,
                    "remaining_focus_review_rows": 5,
                },
                "focus_packs": [
                    {
                        "focus_pack_id": "source-discovery-focus-001",
                        "source_store": "스토어A",
                    }
                ],
            },
            source_discovery_next_focus_pack={
                "summary": {
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "스토어A",
                    "target_category": "인형",
                    "pack_items": 5,
                    "remaining_review_rows": 5,
                    "blocked_rows": 5,
                }
            },
            source_discovery_next_focus_fallback_queue={
                "summary": {
                    "queue_rows": 2,
                    "first_fallback_store_search_url": "https://example.com/search",
                    "first_primary_review_url": "https://google.example/fallback",
                    "first_primary_review_url_kind": "domain_limited_web_search",
                }
            },
            manual_source_url_search_queue={"summary": {"manual_search_required_rows": 3}},
            provider_missing_source_url_queue={"summary": {"provider_missing_rows": 2}},
            candidate_source_url_review_queue={"summary": {"candidate_review_rows": 1}},
            image_attachment_action_queue={
                "summary": {
                    "actionable_image_rows": 4,
                    "source_url_update_required_rows": 6,
                }
            },
        )

        summary = roadmap["summary"]
        self.assertEqual(summary["queued_source_rows"], 8)
        self.assertEqual(summary["focus_coverage"], 0.625)
        self.assertEqual(summary["top_10_store_coverage"], 0.75)
        self.assertEqual(summary["generic_source_replacement_rows"], 6)
        self.assertEqual(
            roadmap["top_store_steps"][0]["first_primary_review_url"],
            "https://example.com/action-search",
        )
        self.assertEqual(
            roadmap["top_store_steps"][0]["first_primary_review_url_kind"],
            "official_search_url",
        )
        self.assertEqual(roadmap["top_store_steps"][0]["official_search_url_count"], 5)
        self.assertEqual(
            roadmap["current_focus_pack"]["first_primary_review_url"],
            "https://google.example/fallback",
        )
        self.assertEqual(
            roadmap["completion_readiness"]["next_queue"]["first_primary_review_url"],
            "https://google.example/fallback",
        )
        self.assertEqual(
            roadmap["completion_readiness"]["next_queue"]["first_primary_review_url_kind"],
            "domain_limited_web_search",
        )
        self.assertEqual(roadmap["phases"][3]["rows"], 6)
        self.assertIs(summary["auto_apply_enabled"], False)

    def test_ichiban_kuji_historical_roadmap_summarizes_manual_phases(self):
        roadmap = reports.build_ichiban_kuji_historical_roadmap_public(
            generated_at="2026-01-01T00:00:00Z",
            ichiban_kuji_history={
                "summary": {
                    "catalog_kuji_item_rows": 12,
                    "campaign_rows": 3,
                    "campaign_metadata_review_queue_rows": 2,
                    "missing_release_date_rows": 1,
                    "missing_official_price_jpy_rows": 4,
                    "missing_official_price_jpy_campaign_groups": 2,
                    "official_price_jpy_review_queue_campaigns": 2,
                    "metadata_review_queue_covers_all_price_campaign_groups": True,
                    "avg_missing_price_rows_per_campaign_group": 2.0,
                },
                "metadata_resolution_summary": {
                    "price_resolution_unit": "campaign_draw_price",
                    "official_price_jpy_review_queue_campaigns": 2,
                    "missing_official_price_jpy_rows": 4,
                    "avg_catalog_rows_per_price_campaign": 2.0,
                    "guardrails": [
                        "do not overwrite zero-price Last One or Double Chance exception rows"
                    ],
                }
            },
            ichiban_metadata_action_queue={
                "summary": {
                    "actionable_campaigns": 2,
                    "queued_action_campaigns": 2,
                    "unqueued_action_campaigns": 0,
                    "queued_catalog_item_rows": 7,
                    "action_batch_count": 1,
                    "field_patch_template_counts": [["official_price_jpy", 1]],
                    "next_campaign_patch_review_batch_rows": 2,
                    "next_campaign_patch_review_batch_template_rows": 2,
                    "next_campaign_patch_review_batch_primary_review_url_rows": 2,
                    "next_campaign_patch_review_batch_field_counts": [
                        ["official_price_jpy", 1],
                        ["release_date", 1],
                    ],
                }
            },
            ichiban_metadata_fast_review={
                "summary": {
                    "fast_review_campaigns": 1,
                    "held_for_later_campaigns": 1,
                    "fast_review_template_rows": 1,
                    "manual_confirmed_true": 0,
                }
            },
            ichiban_kuji_prize_policy_issue_queue={
                "summary": {
                    "issue_rows": 3,
                    "open_issue_rows": 5,
                    "zero_price_violation_rows": 0,
                    "zero_price_exception_policy_pass": True,
                    "numbered_variant_coverage_policy_pass": True,
                    "probable_reissue_work_order_rows": 2,
                    "probable_reissue_review_groups": 2,
                    "repeated_name_different_source_groups": 4,
                }
            },
            deduplication_action_queue={
                "summary": {
                    "ichiban_reissue_review_groups": 4,
                    "ichiban_reissue_work_order_rows": 2,
                    "ichiban_reissue_decision_template_rows": 2,
                    "auto_merge_enabled": False,
                    "auto_delete_enabled": False,
                }
            },
            name_duplicate_audit={
                "summary": {
                    "ichiban_campaign_or_reissue_protected_groups": 9,
                    "same_barcode_name_review_groups": 1,
                    "auto_merge_enabled": False,
                    "auto_delete_enabled": False,
                }
            },
            ichiban_kuji_prize_name_image_review={
                "summary": {
                    "review_rows": 6,
                    "multi_item_prize_rank_groups": 2,
                    "auto_apply_enabled": False,
                }
            },
            ichiban_kuji_prize_name_image_patch_candidates={
                "summary": {
                    "candidate_rows": 4,
                    "open_candidate_rows": 3,
                    "manual_confirmed_rows": 0,
                    "auto_apply_enabled": False,
                },
                "candidates": [{}, {}, {}, {}],
            },
        )

        summary = roadmap["summary"]
        self.assertEqual(summary["catalog_ichiban_rows"], 12)
        self.assertEqual(summary["metadata_actionable_campaigns"], 2)
        self.assertEqual(summary["official_price_jpy_review_queue_campaigns"], 2)
        self.assertTrue(summary["metadata_review_queue_covers_all_price_campaign_groups"])
        self.assertEqual(summary["probable_reissue_review_groups"], 2)
        self.assertEqual(summary["roadmap_phase_count"], 5)
        self.assertEqual(
            summary["completion_readiness"],
            {
                "status": "manual_review_required",
                "manual_metadata_campaigns": 2,
                "manual_reissue_review_groups": 2,
                "manual_prize_name_image_patch_rows": 10,
                "zero_price_policy_ready": True,
                "numbered_variant_policy_ready": True,
                "blocked_auto_apply_reasons": [
                    "campaign_metadata_requires_official_confirmation",
                    "same_name_reissue_groups_require_keep_or_merge_decisions",
                    "prize_name_image_patches_require_official_lineup_confirmation",
                ],
                "next_safe_phase": "confirm_ichiban_campaign_metadata",
            },
        )
        self.assertEqual(roadmap["phases"][0]["phase"], "confirm_ichiban_campaign_metadata")
        self.assertEqual(roadmap["phases"][0]["rows"], 2)
        self.assertEqual(
            roadmap["phases"][0]["price_resolution_unit"],
            "campaign_draw_price",
        )
        self.assertIn(
            "do not overwrite zero-price Last One or Double Chance exception rows",
            roadmap["phases"][0]["guardrails"],
        )
        self.assertEqual(roadmap["phases"][1]["rows"], 2)
        self.assertIs(summary["auto_apply_enabled"], False)
        self.assertIs(summary["auto_merge_enabled"], False)
        self.assertIs(summary["auto_delete_enabled"], False)

    def test_deduplication_template_import_dry_run_has_actionable_summary(self):
        template = {
            "items": [
                {
                    "manual_confirmed": False,
                    "same_sellable_product_confirmed": False,
                    "decision": "review_required",
                    "key_type": "barcode",
                    "key": "123",
                    "keep_catalog_index": 2,
                    "drop_catalog_indexes": [1],
                }
            ]
        }
        catalog = {
            "items": [
                {"catalog_index": 1, "name_ko": "Drop", "barcode": "123"},
                {"catalog_index": 2, "name_ko": "Keep", "barcode": "123"},
            ]
        }

        dry_run = reports.build_deduplication_template_import_dry_run_public(
            template,
            catalog,
            "2026-07-24T00:00:00Z",
        )

        self.assertEqual(dry_run["schema_version"], 2)
        self.assertEqual(dry_run["summary"]["template_items"], 1)
        self.assertEqual(dry_run["summary"]["manual_confirmed_rows"], 0)
        self.assertEqual(dry_run["summary"]["ready_decision_rows"], 0)
        self.assertEqual(dry_run["summary"]["updated_rows"], 0)
        self.assertEqual(dry_run["summary"]["skipped_rows"], 1)
        self.assertEqual(dry_run["summary"]["skip_reason_counts"], [("manual_confirmed_false", 1)])
        self.assertIs(dry_run["summary"]["auto_delete_enabled"], False)
        self.assertEqual(dry_run["queue"], "data/catalog_deduplication_confirmed_template_public.json")
        self.assertEqual(dry_run["skipped_sample"][0]["reason"], "manual_confirmed_false")

    def test_image_actionable_groups_publish_enough_samples_for_action_queue(self):
        items = [
            {
                "catalog_index": index,
                "name_ko": f"스텔라이브 샘플 {index}",
                "category": "캔뱃지",
                "source_store": "Stellive Store",
                "source_url": "https://fanding.kr/@stellive/shop",
                "image_url": None,
            }
            for index in range(12)
        ]

        image_batches = reports.build_image_enrichment_batches_public(items)
        group = image_batches["groups"][0]

        self.assertEqual(group["workflow"], "replace_generic_source_then_extract_image")
        self.assertEqual(group["missing_image_rows"], 12)
        self.assertEqual(len(group["sample_items"]), 12)
        self.assertEqual(
            image_batches["summary"]["sample_image_import_template_count"],
            image_batches["summary"]["generic_source_url_rows"],
        )

    def test_published_reports_expose_home_catalog_work_blocks(self):
        operations = reports.load_json(reports.OPERATIONS_REPORT)
        image_batches = reports.load_json(reports.IMAGE_ENRICHMENT_BATCHES)
        agent_queue = reports.load_json(reports.AGENT_WORK_QUEUE)

        blocker_rows = sum(int(row.get("rows") or 0) for row in image_batches.get("blocker_summary", []))
        self.assertEqual(blocker_rows, image_batches["summary"]["missing_image_rows"])
        image_review_batches = image_batches.get("review_batches", [])
        self.assertEqual(image_batches["summary"]["review_batch_count"], len(image_review_batches))
        self.assertEqual(
            sum(int(batch.get("missing_image_rows") or 0) for batch in image_review_batches),
            sum(int(group.get("missing_image_rows") or 0) for group in image_batches.get("groups", [])),
        )
        self.assertTrue(all(batch.get("auto_apply_enabled") is False for batch in image_review_batches))
        self.assertGreater(image_batches["summary"].get("sample_image_import_template_count", 0), 0)
        self.assertTrue(
            all(
                len({group.get("workflow") for group in batch.get("groups", []) if isinstance(group, dict)}) <= 1
                for batch in image_review_batches
            )
        )
        sample_templates = [
            item.get("catalog_field_import_template")
            for group in image_batches.get("groups", [])
            for item in group.get("sample_items", [])
            if isinstance(item, dict)
        ]
        self.assertGreater(len(sample_templates), 0)
        self.assertTrue(all(isinstance(template, dict) for template in sample_templates))
        self.assertTrue(all(template.get("field") == "image_url" for template in sample_templates))
        self.assertTrue(all(template.get("manual_confirmed") is False for template in sample_templates))
        self.assertTrue(
            any(template.get("blocked_until") == "exact_product_source_url_confirmed" for template in sample_templates)
        )

        batches = agent_queue.get("batches", [])
        top_batches = agent_queue.get("top_next_batches", [])
        ichiban_metadata_action = reports.load_json(reports.ICHIIBAN_KUJI_METADATA_ACTION_QUEUE)
        ichiban_metadata_action_summary = ichiban_metadata_action.get("summary", {})
        confirmed_readiness = reports.load_json(reports.CONFIRMED_IMPORT_READINESS)
        requested_focus_action = reports.load_json(reports.REQUESTED_FOCUS_ACTION_QUEUE)
        requested_focus_action_summary = requested_focus_action.get("summary", {})
        requested_focus_action_batches = requested_focus_action.get("batches", [])
        focused_source_fallback = next(
            row
            for row in confirmed_readiness["workflows"]
            if row.get("workflow") == "source_discovery_next_focus_fallback"
        )
        self.assertEqual(focused_source_fallback["status"], "template_ready_for_manual_confirmation")
        self.assertEqual(focused_source_fallback["template_items"], 17)
        self.assertEqual(focused_source_fallback["public_action_rows"], 17)
        self.assertEqual(focused_source_fallback["skipped_rows"], 17)
        self.assertEqual(focused_source_fallback["skip_reason_counts"], [["manual_confirmed_false", 17]])
        source_next_focus_fallback = reports.load_json(
            reports.SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE
        )
        source_next_focus_fallback_summary = source_next_focus_fallback.get("summary", {})
        source_next_focus_detail = reports.load_json(
            reports.SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES
        )
        source_next_focus_detail_summary = source_next_focus_detail.get("summary", {})
        fallback_agent_batch = next(
            batch
            for batch in batches
            if batch.get("workstream") == "source_discovery_next_focus_fallback_queue"
            and batch.get("title") != "포커스팩 exact source 후보 15개 확인"
        )
        fallback_ready_agent_batch = next(
            batch
            for batch in batches
            if batch.get("title") == "포커스팩 exact source 후보 15개 확인"
        )
        self.assertEqual(
            fallback_agent_batch["review_summary"]["first_primary_review_url"],
            source_next_focus_fallback_summary["first_primary_review_url"],
        )
        self.assertEqual(
            fallback_agent_batch["review_summary"]["first_primary_review_url_kind"],
            source_next_focus_fallback_summary["first_primary_review_url_kind"],
        )
        self.assertTrue(
            any(item.get("primary_review_url") for item in fallback_agent_batch.get("sample_items", []))
        )
        self.assertEqual(
            fallback_ready_agent_batch.get("rows"),
            source_next_focus_fallback_summary.get("source_confirmation_ready_rows"),
        )
        self.assertEqual(
            fallback_ready_agent_batch.get("review_summary", {}).get(
                "manual_entry_template_rows"
            ),
            source_next_focus_fallback_summary.get("manual_entry_template_rows"),
        )
        self.assertTrue(
            all(
                item.get("identity_review_status") == "exact_page_match_review_ready"
                for item in fallback_ready_agent_batch.get("sample_items", [])
                if isinstance(item, dict)
            )
        )
        variant_metadata_agent_batch = next(
            batch
            for batch in batches
            if batch.get("workstream") == "source_discovery_next_focus_detail_candidates"
            and batch.get("review_summary", {}).get("metadata_enrichment_template_rows")
        )
        self.assertEqual(
            variant_metadata_agent_batch.get("rows"),
            source_next_focus_detail_summary.get("metadata_enrichment_template_rows"),
        )
        self.assertEqual(
            variant_metadata_agent_batch.get("review_summary", {}).get(
                "variant_detail_required_rows"
            ),
            source_next_focus_detail_summary.get("variant_detail_required_rows"),
        )
        self.assertTrue(
            all(
                item.get("candidate_options")
                for item in variant_metadata_agent_batch.get("sample_items", [])
                if isinstance(item, dict)
            )
        )
        ichiban_next_campaign_patch_batch = next(
            batch
            for batch in batches
            if batch.get("title") == "Ichiban Kuji metadata next campaign patch review"
        )
        self.assertEqual(
            ichiban_next_campaign_patch_batch.get("rows"),
            ichiban_metadata_action_summary.get("next_campaign_patch_review_batch_rows"),
        )
        self.assertEqual(
            ichiban_next_campaign_patch_batch.get("review_summary", {}).get(
                "next_campaign_patch_review_batch_template_rows"
            ),
            ichiban_metadata_action_summary.get(
                "next_campaign_patch_review_batch_template_rows"
            ),
        )
        self.assertEqual(
            ichiban_next_campaign_patch_batch.get("review_summary", {}).get(
                "next_campaign_patch_review_batch_field_counts"
            ),
            ichiban_metadata_action_summary.get(
                "next_campaign_patch_review_batch_field_counts"
            ),
        )
        self.assertTrue(
            all(
                item.get("primary_review_url")
                for item in ichiban_next_campaign_patch_batch.get("sample_items", [])
            )
        )
        first_requested_focus_action_batch = next(
            batch
            for batch in batches
            if batch.get("workstream") == "requested_focus_action_queue"
        )
        self.assertEqual(
            requested_focus_action_summary.get("review_url_rows"),
            requested_focus_action_summary.get("actionable_template_rows"),
        )
        self.assertGreater(requested_focus_action_summary.get("review_url_rows", 0), 0)
        self.assertTrue(
            any(
                item.get("primary_review_url")
                for batch in requested_focus_action_batches
                for item in batch.get("items", [])
                if isinstance(item, dict)
            )
        )
        self.assertTrue(
            any(
                item.get("primary_review_url")
                for item in first_requested_focus_action_batch.get("sample_items", [])
                if isinstance(item, dict)
            )
        )
        self.assertIn(
            first_requested_focus_action_batch.get("review_summary", {}).get("first_primary_review_url_kind"),
            {"domain_limited_web_search", "web_search", "existing_source_url"},
        )
        self.assertGreater(len(batches), 0)
        self.assertLessEqual(len(batches), reports.MAX_AGENT_WORK_QUEUE_BATCHES)
        self.assertEqual(agent_queue["summary"]["max_published_batches"], reports.MAX_AGENT_WORK_QUEUE_BATCHES)
        self.assertEqual(agent_queue["summary"]["top_next_batch_count"], len(top_batches))
        self.assertEqual(
            [batch["batch_id"] for batch in top_batches],
            [batch["batch_id"] for batch in batches[: len(top_batches)]],
        )
        self.assertEqual(
            agent_queue["summary"]["confirmed_import_template_rows"],
            confirmed_readiness["summary"]["template_items"],
        )
        self.assertEqual(
            agent_queue["summary"]["confirmed_import_action_queue_rows"],
            confirmed_readiness["summary"]["public_action_queue_rows"],
        )
        self.assertEqual(
            agent_queue["summary"]["confirmed_import_manual_confirmed_ready_rows"],
            confirmed_readiness["summary"]["manual_confirmed_true"],
        )
        self.assertEqual(
            agent_queue["summary"]["confirmed_import_variant_metadata_template_rows"],
            confirmed_readiness["summary"].get("variant_metadata_template_rows", 0),
        )
        self.assertEqual(
            agent_queue["summary"]["confirmed_import_variant_metadata_manual_confirmed_rows"],
            confirmed_readiness["summary"].get("variant_metadata_manual_confirmed_rows", 0),
        )
        self.assertEqual(
            agent_queue["summary"]["confirmed_import_variant_metadata_skipped_rows"],
            confirmed_readiness["summary"].get("variant_metadata_skipped_rows", 0),
        )
        self.assertEqual(
            agent_queue["summary"]["confirmed_import_manual_confirmation_backlog_rows"],
            confirmed_readiness["summary"]["template_items"]
            + confirmed_readiness["summary"]["public_action_queue_rows"]
            - confirmed_readiness["summary"]["manual_confirmed_true"],
        )

        scorecard_reports = {row.get("primary_report") for row in operations.get("workstream_scorecard", [])}
        next_action_reports = {row.get("public_report") for row in operations.get("next_actions", [])}
        report_links = {row.get("public_report") for row in operations.get("reports", [])}
        open_queues = operations.get("summary", {}).get("open_review_queues", {})
        quality = reports.load_json(reports.QUALITY)
        readiness_summary = confirmed_readiness.get("summary", {})
        danganronpa_media = reports.load_json(reports.DANGANRONPA_MISSING_MEDIA)
        danganronpa_summary = danganronpa_media.get("summary", {})
        danganronpa_dry_run = reports.load_json(reports.DANGANRONPA_PATCH_TEMPLATE_DRY_RUN)
        danganronpa_dry_summary = danganronpa_dry_run.get("summary", {})
        requested_focus_action = reports.load_json(reports.REQUESTED_FOCUS_ACTION_QUEUE)
        requested_focus_action_summary = requested_focus_action.get("summary", {})
        requested_focus_action_batches = requested_focus_action.get("batches", [])
        requested_focus_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "requested_focus_action_queue"
        )
        requested_focus_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "requested_focus_action_queue"
        )
        image_action = reports.load_json(reports.IMAGE_ATTACHMENT_ACTION_QUEUE)
        image_action_summary = image_action.get("summary", {})
        first_image_action_batch = next(
            batch
            for batch in batches
            if batch.get("workstream") == "image_attachment_action_queue"
            and batch.get("title") != "대표 이미지 후보 다음 10개 검수"
        )
        representative_image_agent_batch = next(
            batch
            for batch in batches
            if batch.get("title") == "대표 이미지 후보 다음 10개 검수"
        )
        self.assertGreater(image_action_summary.get("primary_review_url_rows", 0), 0)
        self.assertEqual(
            sum(count for _, count in image_action_summary.get("by_review_lane", [])),
            image_action_summary.get("sample_action_item_rows"),
        )
        self.assertEqual(
            image_action_summary.get("local_image_download_instruction_ready_rows"),
            image_action_summary.get("suggested_local_image_path_rows"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_local_download_ready_rows"),
            image_action_summary.get("local_image_download_instruction_ready_rows"),
        )
        self.assertGreater(
            first_image_action_batch.get("review_summary", {}).get("primary_review_url_rows", 0),
            0,
        )
        self.assertEqual(
            first_image_action_batch.get("review_summary", {}).get("suggested_local_image_path_rows"),
            first_image_action_batch.get("rows"),
        )
        self.assertEqual(
            first_image_action_batch.get("review_summary", {}).get("blocked_before_image_import_rows"),
            first_image_action_batch.get("review_summary", {})
            .get("attachment_readiness", {})
            .get("blocked_before_image_import_rows"),
        )
        self.assertEqual(
            first_image_action_batch.get("review_summary", {}).get("can_import_image_urls_now_rows"),
            first_image_action_batch.get("review_summary", {})
            .get("attachment_readiness", {})
            .get("can_import_image_urls_now_rows"),
        )
        self.assertTrue(
            first_image_action_batch.get("review_summary", {}).get("image_import_blocker_counts")
        )
        self.assertTrue(
            first_image_action_batch.get("review_summary", {}).get("first_primary_review_url")
        )
        self.assertIn(
            first_image_action_batch.get("review_summary", {}).get("first_primary_review_url_kind"),
            {"source_search_url", "official_search_url", "fallback_web_search", "current_source_url"},
        )
        self.assertTrue(
            any(
                item.get("primary_review_url")
                for item in first_image_action_batch.get("sample_items", [])
                if isinstance(item, dict)
            )
        )
        self.assertEqual(
            representative_image_agent_batch.get("rows"),
            image_action_summary.get("next_representative_image_review_batch_rows"),
        )
        self.assertEqual(
            representative_image_agent_batch.get("review_summary", {}).get(
                "next_representative_image_review_batch_primary_review_url_rows"
            ),
            image_action_summary.get(
                "next_representative_image_review_batch_primary_review_url_rows"
            ),
        )
        self.assertEqual(
            representative_image_agent_batch.get("review_summary", {}).get(
                "next_representative_image_review_batch_local_path_rows"
            ),
            image_action_summary.get("next_representative_image_review_batch_local_path_rows"),
        )
        self.assertTrue(
            all(
                item.get("suggested_local_image_path")
                for item in representative_image_agent_batch.get("sample_items", [])
                if isinstance(item, dict)
            )
        )
        image_asset = reports.load_json(reports.IMAGE_ASSET_AUDIT)
        image_asset_summary = image_asset.get("summary", {})
        image_asset_gate = next(
            row
            for row in operations.get("quality_gates", [])
            if row.get("key") == "local_image_asset_coverage"
        )
        image_asset_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "local_image_asset_audit"
        )
        source_action = reports.load_json(reports.SOURCE_DISCOVERY_ACTION_QUEUE)
        source_action_summary = source_action.get("summary", {})
        source_focus_template = reports.load_json(reports.SOURCE_DISCOVERY_FOCUS_TEMPLATE)
        source_focus_template_summary = source_focus_template.get("summary", {})
        source_focus_template_import = reports.load_json(reports.SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT)
        source_next_focus_pack = reports.load_json(reports.SOURCE_DISCOVERY_NEXT_FOCUS_PACK)
        source_next_focus_pack_summary = source_next_focus_pack.get("summary", {})
        source_next_focus_detail = reports.load_json(reports.SOURCE_DISCOVERY_NEXT_FOCUS_DETAIL_CANDIDATES)
        source_next_focus_detail_summary = source_next_focus_detail.get("summary", {})
        source_next_focus_fallback = reports.load_json(reports.SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE)
        source_next_focus_fallback_summary = source_next_focus_fallback.get("summary", {})
        source_discovery_starter = reports.load_json(reports.SOURCE_DISCOVERY_STARTER_QUEUE)
        source_discovery_starter_summary = source_discovery_starter.get("summary", {})
        ensky_cache_action = reports.load_json(reports.ENSKY_CACHE_CANDIDATE_ACTION_QUEUE)
        ensky_cache_action_summary = ensky_cache_action.get("summary", {})
        source_detail_action = reports.load_json(reports.SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE)
        source_detail_action_summary = source_detail_action.get("summary", {})
        source_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_discovery_action_queue"
        )
        source_focus_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_discovery_focus_template"
        )
        source_next_focus_fallback_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_discovery_next_focus_fallback_queue"
        )
        source_next_focus_detail_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_discovery_next_focus_detail_candidates"
        )
        source_detail_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_detail_candidate_action_queue"
        )
        ensky_cache_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "ensky_cache_candidate_action_queue"
        )
        source_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_discovery_action_queue"
        )
        source_focus_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_discovery_focus_template"
        )
        source_next_focus_pack_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_discovery_next_focus_pack"
        )
        source_next_focus_fallback_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_discovery_next_focus_fallback_queue"
        )
        source_next_focus_detail_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_discovery_next_focus_detail_candidates"
        )
        ensky_cache_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ensky_cache_candidate_action_queue"
        )
        source_detail_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_detail_candidate_action_queue"
        )
        metadata_action = reports.load_json(reports.METADATA_ACTION_QUEUE)
        metadata_action_summary = metadata_action.get("summary", {})
        metadata_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "metadata_action_queue"
        )
        metadata_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "metadata_action_queue"
        )
        image_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "image_attachment_action_queue"
        )
        image_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "image_attachment_action_queue"
        )
        dedupe_action = reports.load_json(reports.DEDUPLICATION_ACTION_QUEUE)
        dedupe_action_summary = dedupe_action.get("summary", {})
        reissue_decision = reports.load_json(reports.ICHIIBAN_KUJI_REISSUE_DECISION_TEMPLATE)
        reissue_decision_summary = reissue_decision.get("summary", {})
        dedupe_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "deduplication_action_queue"
        )
        dedupe_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "deduplication_action_queue"
        )
        ichiban_reissue_dedupe_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "ichiban_kuji_reissue_dedupe_review"
        )
        ichiban_reissue_dedupe_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ichiban_kuji_reissue_dedupe_review"
        )
        execution_plan = reports.load_json(reports.EXECUTION_PLAN)
        source_next_focus_detail_execution_action = next(
            row
            for row in execution_plan.get("actions", [])
            if row.get("workstream") == "source_discovery_next_focus_detail_candidates"
        )
        ichiban_reissue_execution_action = next(
            row
            for row in execution_plan.get("actions", [])
            if row.get("workstream") == "ichiban_kuji_reissue_dedupe_review"
        )
        source_discovery_starter_execution_action = next(
            row
            for row in execution_plan.get("actions", [])
            if row.get("workstream") == "source_discovery_starter_queue"
        )
        ichiban_action = reports.load_json(reports.ICHIIBAN_KUJI_METADATA_ACTION_QUEUE)
        ichiban_action_summary = ichiban_action.get("summary", {})
        ichiban_prize_audit = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT)
        ichiban_prize_audit_summary = ichiban_prize_audit.get("summary", {})
        ichiban_prize_issue = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_POLICY_ISSUE_QUEUE)
        ichiban_prize_issue_summary = ichiban_prize_issue.get("summary", {})
        ichiban_prize_name_image = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW)
        ichiban_prize_name_image_summary = ichiban_prize_name_image.get("summary", {})
        ichiban_prize_name_image_patch = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES)
        ichiban_prize_name_image_patch_summary = ichiban_prize_name_image_patch.get("summary", {})
        ichiban_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "ichiban_kuji_metadata_action_queue"
        )
        ichiban_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ichiban_kuji_metadata_action_queue"
        )
        ichiban_prize_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ichiban_kuji_prize_policy_audit"
        )
        ichiban_prize_name_image_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "ichiban_kuji_prize_name_image_review"
        )
        ichiban_prize_name_image_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ichiban_kuji_prize_name_image_review"
        )
        ichiban_prize_name_image_patch_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "ichiban_kuji_prize_name_image_patch_candidates"
        )
        ichiban_prize_name_image_patch_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ichiban_kuji_prize_name_image_patch_candidates"
        )
        animation_action = reports.load_json(reports.ANIMATION_CATEGORY_ACTION_QUEUE)
        animation_action_summary = animation_action.get("summary", {})
        animation_split = reports.load_json(reports.ANIMATION_CATEGORY_SPLIT_REVIEW)
        animation_split_summary = animation_split.get("summary", {})
        animation_keyword = reports.load_json(reports.ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW)
        animation_keyword_summary = animation_keyword.get("summary", {})
        animation_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "animation_category_action_queue"
        )
        animation_split_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "animation_category_split_review"
        )
        animation_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "animation_category_action_queue"
        )
        animation_split_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "animation_category_split_review"
        )
        animation_keyword_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "animation_category_unmatched_keyword_review"
        )
        animation_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "animation_category_action_queue"
        ]
        animation_split_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "animation_category_split_review"
        ]
        animation_keyword_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "animation_category_unmatched_keyword_review"
        ]
        dedupe_action_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "deduplication_action_queue"
        ]
        ichiban_reissue_dedupe_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "ichiban_kuji_reissue_dedupe_review"
        ]
        ichiban_reissue_campaign_first_batch = next(
            batch
            for batch in ichiban_reissue_dedupe_agent_batches
            if batch.get("title") == "Ichiban Kuji reissue campaign decisions first"
        )
        ichiban_prize_policy_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "ichiban_kuji_prize_policy_audit"
        ]
        ichiban_campaign_first_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "ichiban_kuji_campaign_first_reissue_review"
        ]
        ichiban_prize_name_image_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "ichiban_kuji_prize_name_image_review"
        ]
        ichiban_prize_name_image_patch_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "ichiban_kuji_prize_name_image_patch_candidates"
        ]
        danganronpa_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "danganronpa_missing_media"
        ]
        source_next_focus_pack_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "source_discovery_next_focus_pack"
        ]
        source_discovery_starter_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "source_discovery_starter_queue"
        ]
        source_discovery_starter_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_discovery_starter_queue"
        )
        source_discovery_starter_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_discovery_starter_queue"
        )
        self.assertIn(f"data/{reports.IMAGE_ENRICHMENT_BATCHES.name}", scorecard_reports)
        self.assertIn(f"data/{reports.REQUESTED_FOCUS.name}", scorecard_reports)
        self.assertIn(f"data/{reports.DANGANRONPA_MISSING_MEDIA.name}", scorecard_reports)
        self.assertIn(f"data/{reports.DANGANRONPA_PATCH_TEMPLATE_DRY_RUN.name}", scorecard_reports)
        self.assertIn(f"data/{reports.AGENT_WORK_QUEUE.name}", next_action_reports)
        self.assertIn(f"data/{reports.EXECUTION_PLAN.name}", next_action_reports)
        self.assertIn(f"data/{reports.CONFIRMED_IMPORT_READINESS.name}", report_links)
        self.assertIn(f"data/{reports.IMAGE_ASSET_AUDIT.name}", report_links)
        self.assertIn(f"data/{reports.SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.name}", report_links)
        self.assertIn(
            f"data/{reports.SOURCE_DISCOVERY_STARTER_QUEUE.name}",
            {batch.get("public_report") for batch in agent_queue.get("batches", [])},
        )
        self.assertIn(f"data/{reports.SOURCE_DISCOVERY_STARTER_QUEUE.name}", next_action_reports)
        self.assertIn(f"data/{reports.SOURCE_DISCOVERY_STARTER_QUEUE.name}", scorecard_reports)
        self.assertIn(f"data/{reports.SOURCE_DISCOVERY_STARTER_QUEUE.name}", report_links)
        self.assertIn(f"data/{reports.SOURCE_DISCOVERY_FOCUS_TEMPLATE.name}", report_links)
        self.assertIn(f"data/{reports.SOURCE_DISCOVERY_NEXT_FOCUS_PACK.name}", report_links)
        self.assertIn(f"data/{reports.SOURCE_DISCOVERY_NEXT_FOCUS_FALLBACK_QUEUE.name}", report_links)
        self.assertIn(f"data/{reports.DANGANRONPA_PATCH_TEMPLATE_DRY_RUN.name}", report_links)
        self.assertIn(f"data/{reports.ANIMATION_CATEGORY_ACTION_QUEUE.name}", report_links)
        self.assertIn(f"data/{reports.ANIMATION_CATEGORY_SPLIT_REVIEW.name}", report_links)
        self.assertIn(f"data/{reports.ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.name}", report_links)
        self.assertIn(f"data/{reports.ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.name}", report_links)
        self.assertIn(f"data/{reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.name}", report_links)
        self.assertIn(f"data/{reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_PATCH_CANDIDATES.name}", report_links)
        self.assertEqual(len(danganronpa_agent_batches), danganronpa_summary.get("review_batch_count"))
        self.assertEqual(
            {batch.get("review_state") for batch in danganronpa_agent_batches},
            {"source_and_image_evidence_required"},
        )
        self.assertEqual(
            {batch.get("next_machine_step") for batch in danganronpa_agent_batches},
            {"confirm_exact_source_then_fill_image_url_templates"},
        )
        self.assertGreater(len(dedupe_action_agent_batches), 0)
        self.assertEqual(
            {batch.get("review_state") for batch in dedupe_action_agent_batches},
            {"manual_dedupe_action_confirmation_required"},
        )
        self.assertEqual(
            {batch.get("next_machine_step") for batch in dedupe_action_agent_batches},
            {"confirm_manual_keep_drop_dedupe_decisions"},
        )
        self.assertGreater(len(ichiban_prize_policy_agent_batches), 0)
        self.assertEqual(
            ichiban_prize_issue_summary["campaign_first_review_item_work_order_rows_blocked"],
            ichiban_prize_issue["campaign_first_review_summary"][
                "item_work_order_rows_blocked_by_campaign_decision"
            ],
        )
        self.assertEqual(
            ichiban_prize_issue_summary["campaign_first_review_likely_same_family_rows"],
            ichiban_prize_issue["campaign_first_review_summary"][
                "likely_same_campaign_family_reissue_rows"
            ],
        )
        self.assertEqual(
            len(ichiban_campaign_first_agent_batches),
            ichiban_prize_issue_summary["campaign_first_review_plan_rows"],
        )
        self.assertTrue(
            all(
                batch.get("review_summary", {}).get("first_evidence_url")
                for batch in ichiban_campaign_first_agent_batches
            )
        )
        if open_queues.get("ichiban_prize_name_image_review_rows", 0):
            self.assertGreater(len(ichiban_prize_name_image_agent_batches), 0)
        else:
            self.assertEqual(len(ichiban_prize_name_image_agent_batches), 0)
        if open_queues.get("ichiban_prize_name_image_patch_candidate_rows", 0):
            self.assertGreater(len(ichiban_prize_name_image_patch_agent_batches), 0)
        else:
            self.assertEqual(len(ichiban_prize_name_image_patch_agent_batches), 0)
        self.assertEqual(
            open_queues.get("confirmed_import_action_queue_rows"),
            readiness_summary.get("public_action_queue_rows"),
        )
        self.assertEqual(
            open_queues.get("confirmed_import_variant_metadata_template_rows"),
            readiness_summary.get("variant_metadata_template_rows"),
        )
        self.assertEqual(
            open_queues.get("requested_focus_action_rows"),
            requested_focus_action_summary.get("queued_action_rows"),
        )
        self.assertEqual(
            open_queues.get("requested_focus_actionable_rows"),
            requested_focus_action_summary.get("actionable_template_rows"),
        )
        self.assertEqual(
            open_queues.get("requested_focus_unqueued_actionable_rows"),
            requested_focus_action_summary.get("unqueued_actionable_rows"),
        )
        self.assertEqual(
            open_queues.get("requested_focus_barcode_template_rows_excluded"),
            requested_focus_action_summary.get("barcode_template_rows_excluded"),
        )
        self.assertEqual(
            requested_focus_scorecard.get("queue_coverage"),
            requested_focus_action_summary.get("queue_coverage"),
        )
        self.assertEqual(
            requested_focus_next_action.get("non_barcode_template_share"),
            requested_focus_action_summary.get("non_barcode_template_share"),
        )
        self.assertEqual(
            open_queues.get("danganronpa_patch_template_pending_rows"),
            danganronpa_dry_summary.get("skipped_rows"),
        )
        self.assertEqual(
            open_queues.get("danganronpa_patch_template_ready_rows"),
            danganronpa_dry_summary.get("ready_rows"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_action_rows"),
            image_action_summary.get("queued_image_rows"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_source_url_search_hint_rows"),
            image_action_summary.get("source_url_update_search_hint_rows"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_source_url_missing_search_hint_rows"),
            image_action_summary.get("source_url_update_missing_search_hint_rows"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_source_url_fallback_web_search_rows"),
            image_action_summary.get("source_url_update_fallback_web_search_rows"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_source_url_any_search_hint_rows"),
            image_action_summary.get("source_url_update_any_search_hint_rows"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_source_url_missing_any_search_hint_rows"),
            image_action_summary.get("source_url_update_missing_any_search_hint_rows"),
        )
        self.assertEqual(image_asset_gate.get("status"), "pass")
        self.assertEqual(image_asset_gate.get("image_url_without_local_path_rows"), 0)
        self.assertEqual(image_asset_gate.get("missing_local_image_files"), 0)
        self.assertEqual(image_asset_gate.get("missing_web_public_asset_files"), 0)
        self.assertEqual(image_asset_gate.get("web_public_asset_coverage"), 1.0)
        self.assertEqual(image_asset_gate.get("image_url_rows"), image_asset_summary.get("image_url_rows"))
        self.assertEqual(
            image_asset_next_action.get("local_asset_coverage"),
            image_asset_summary.get("local_asset_coverage"),
        )
        self.assertEqual(
            image_asset_next_action.get("web_public_asset_coverage"),
            image_asset_summary.get("web_public_asset_coverage"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_action_rows"),
            source_action_summary.get("queued_source_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_actionable_rows"),
            source_action_summary.get("actionable_source_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_unqueued_actionable_rows"),
            source_action_summary.get("unqueued_actionable_source_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_manual_research_backlog_rows"),
            source_action_summary.get("manual_research_backlog_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_manual_identity_backfill_required_rows"),
            source_action_summary.get("manual_research_identity_backfill_required_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_manual_official_lookup_rows"),
            source_action_summary.get("manual_research_official_lookup_rows"),
        )
        self.assertEqual(
            source_scorecard.get("queue_coverage"),
            source_action_summary.get("queue_coverage"),
        )
        self.assertEqual(
            source_scorecard.get("by_review_state"),
            source_action_summary.get("by_review_state"),
        )
        self.assertEqual(
            source_scorecard.get("by_source_store"),
            source_action_summary.get("by_source_store"),
        )
        expected_source_workstreams = [
            {
                "source_store": row.get("source_store"),
                "priority": row.get("priority"),
                "queued_source_rows": row.get("queued_source_rows"),
                "batch_count": row.get("batch_count", 0),
                "next_batch_id": row.get("next_batch_id"),
                "batch_ids": row.get("batch_ids", []),
                "allowed_source_domains": row.get("allowed_source_domains", []),
                "official_search_url_count": row.get("official_search_url_count", 0),
                "workflow_rows": row.get("workflow_rows", []),
                "review_state_rows": row.get("review_state_rows", []),
                "category_rows": row.get("category_rows", []),
                "recommended_next_step": row.get("recommended_next_step"),
                "auto_apply_enabled": row.get("auto_apply_enabled", False),
            }
            for row in source_action.get("source_store_workstreams", [])[:8]
        ]
        self.assertEqual(
            source_scorecard.get("top_source_store_workstreams"),
            expected_source_workstreams,
        )
        self.assertEqual(
            source_next_action.get("unqueued_actionable_source_rows"),
            source_action_summary.get("unqueued_actionable_source_rows"),
        )
        self.assertEqual(
            source_next_action.get("excluded_review_state_rows"),
            source_action_summary.get("excluded_review_state_rows"),
        )
        self.assertEqual(
            source_next_action.get("top_source_store_workstreams"),
            expected_source_workstreams,
        )
        self.assertEqual(
            open_queues.get("source_discovery_focus_template_rows"),
            source_focus_template_summary.get("template_items"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_focus_template_work_order_packs"),
            source_focus_template_summary.get("work_order_pack_count"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_focus_template_dry_run_skipped_rows"),
            source_focus_template_import.get("skipped_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_next_focus_pack_rows"),
            source_next_focus_pack_summary.get("pack_items"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_focus_pack_progress_queues"),
            source_next_focus_pack_summary.get("focus_pack_progress_queue_count"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_focus_pack_progress_remaining_rows"),
            source_next_focus_pack_summary.get("focus_pack_progress_remaining_rows"),
        )
        self.assertEqual(
            source_next_focus_pack_next_action.get("focus_pack_progress_queue_count"),
            source_next_focus_pack_summary.get("focus_pack_progress_queue_count"),
        )
        self.assertGreater(len(source_next_focus_pack_agent_batches), 0)
        self.assertEqual(
            source_next_focus_pack_agent_batches[0]["review_summary"].get(
                "focus_pack_progress_queue_count"
            ),
            len(source_next_focus_pack.get("focus_pack_progress_queue", [])),
        )
        self.assertEqual(len(source_discovery_starter_agent_batches), 10)
        self.assertEqual(
            sum(batch["rows"] for batch in source_discovery_starter_agent_batches),
            sum(group["rows"] for group in source_discovery_starter["groups"][:10]),
        )
        self.assertEqual(
            source_discovery_starter_summary["starter_queue_rows"],
            quality["source_discovery_starter_queue"]["starter_queue_rows"],
        )
        self.assertEqual(
            open_queues.get("source_discovery_starter_queue_rows"),
            source_discovery_starter_summary["starter_queue_rows"],
        )
        self.assertEqual(
            open_queues.get("source_discovery_starter_queue_groups"),
            source_discovery_starter_summary["starter_queue_groups"],
        )
        self.assertEqual(
            source_discovery_starter_scorecard["open_rows"],
            source_discovery_starter_summary["starter_queue_rows"],
        )
        self.assertEqual(
            source_discovery_starter_scorecard["starter_queue_groups"],
            source_discovery_starter_summary["starter_queue_groups"],
        )
        self.assertEqual(
            source_discovery_starter_next_action["starter_queue_rows"],
            source_discovery_starter_summary["starter_queue_rows"],
        )
        self.assertEqual(
            source_discovery_starter_next_action["starter_queue_groups"],
            source_discovery_starter_summary["starter_queue_groups"],
        )
        self.assertGreater(len(source_discovery_starter_next_action["top_search_urls"]), 0)
        self.assertGreater(len(source_discovery_starter_next_action["top_fallback_web_search_urls"]), 0)
        self.assertEqual(
            source_discovery_starter_scorecard["next_step"],
            "find_exact_official_product_source_url",
        )
        self.assertEqual(
            source_discovery_starter_execution_action["rows"],
            source_discovery_starter_summary["starter_queue_rows"],
        )
        self.assertEqual(
            source_discovery_starter_execution_action["next_step"],
            "find_exact_official_product_source_url",
        )
        self.assertEqual(
            source_discovery_starter_execution_action["evidence"]["starter_queue_groups"],
            source_discovery_starter_summary["starter_queue_groups"],
        )
        self.assertGreater(
            len(source_discovery_starter_execution_action["evidence"]["top_groups"][0]["search_urls"]),
            0,
        )
        self.assertEqual(
            {batch.get("review_state") for batch in source_discovery_starter_agent_batches},
            {"exact_source_discovery_required"},
        )
        self.assertEqual(
            {batch.get("next_machine_step") for batch in source_discovery_starter_agent_batches},
            {"find_exact_official_product_source_url"},
        )
        for field in (
            "next_focus_pack_id",
            "next_source_store",
            "next_target_category",
            "next_focus_pack_rows",
            "next_official_search_url",
            "work_order_pack_count",
        ):
            self.assertEqual(source_focus_scorecard.get(field), source_focus_template_summary.get(field))
            self.assertEqual(source_focus_next_action.get(field), source_focus_template_summary.get(field))
        self.assertEqual(
            source_focus_scorecard.get("dry_run_skipped_rows"),
            source_focus_template_import.get("skipped_rows"),
        )
        self.assertFalse(source_focus_scorecard.get("auto_apply_enabled"))
        self.assertEqual(
            open_queues.get("source_discovery_next_focus_fallback_rows"),
            source_next_focus_fallback_summary.get("queue_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_next_focus_fallback_manual_confirmed_rows"),
            source_next_focus_fallback_summary.get("manual_confirmed_rows"),
        )
        self.assertEqual(
            source_next_focus_fallback_scorecard.get("open_rows"),
            source_next_focus_fallback_summary.get("queue_rows"),
        )
        self.assertEqual(
            source_next_focus_fallback_next_action.get("queue_rows"),
            source_next_focus_fallback_summary.get("queue_rows"),
        )
        self.assertEqual(
            source_next_focus_fallback_next_action.get("work_order_steps"),
            source_next_focus_fallback_summary.get("work_order_steps"),
        )
        self.assertEqual(
            source_next_focus_fallback_next_action.get("work_order_lanes"),
            source_next_focus_fallback_summary.get("work_order_lanes"),
        )
        self.assertEqual(
            source_next_focus_fallback_next_action.get("first_primary_review_url"),
            source_next_focus_fallback_summary.get("first_primary_review_url"),
        )
        self.assertEqual(
            source_next_focus_fallback_next_action.get("first_primary_review_url_kind"),
            source_next_focus_fallback_summary.get("first_primary_review_url_kind"),
        )
        self.assertEqual(
            source_next_focus_fallback_scorecard.get("work_order_lanes"),
            source_next_focus_fallback_summary.get("work_order_lanes"),
        )
        self.assertEqual(
            source_next_focus_fallback_scorecard.get("first_primary_review_url"),
            source_next_focus_fallback_summary.get("first_primary_review_url"),
        )
        source_next_focus_fallback_execution_action = next(
            row
            for row in execution_plan.get("actions", [])
            if row.get("workstream") == "source_discovery_next_focus_fallback_queue"
        )
        self.assertEqual(
            source_next_focus_fallback_execution_action["evidence"].get(
                "first_primary_review_url"
            ),
            source_next_focus_fallback_summary.get("first_primary_review_url"),
        )
        self.assertEqual(
            execution_plan["summary"].get("source_next_focus_detail_action_lane_count"),
            source_next_focus_detail_summary.get("next_action_lane_count"),
        )
        self.assertEqual(
            execution_plan["summary"].get("source_next_focus_detail_action_lanes"),
            source_next_focus_detail_summary.get("next_action_lanes"),
        )
        self.assertEqual(
            execution_plan["summary"].get(
                "source_next_focus_detail_metadata_enrichment_template_rows"
            ),
            source_next_focus_detail_summary.get("metadata_enrichment_template_rows"),
        )
        self.assertEqual(
            execution_plan["summary"].get(
                "source_next_focus_detail_metadata_field_import_template_rows"
            ),
            source_next_focus_detail_summary.get("metadata_field_import_template_rows"),
        )
        self.assertEqual(
            execution_plan["summary"].get(
                "source_next_focus_detail_metadata_field_import_supported_rows"
            ),
            source_next_focus_detail_summary.get("metadata_field_import_supported_rows"),
        )
        field_import_dry_run = quality[
            "source_discovery_next_focus_metadata_field_import_dry_run"
        ]
        self.assertEqual(
            execution_plan["summary"].get(
                "source_next_focus_detail_metadata_field_import_dry_run_updated_rows"
            ),
            field_import_dry_run.get("updated_rows"),
        )
        self.assertEqual(
            execution_plan["summary"].get(
                "source_next_focus_detail_metadata_field_import_dry_run_skipped_rows"
            ),
            field_import_dry_run.get("skipped_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_execution_action.get("rows"),
            source_next_focus_detail_summary.get("pack_items"),
        )
        self.assertEqual(
            source_next_focus_detail_execution_action["evidence"].get(
                "metadata_enrichment_template_rows"
            ),
            source_next_focus_detail_summary.get("metadata_enrichment_template_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_execution_action["evidence"].get(
                "metadata_field_import_template_rows"
            ),
            source_next_focus_detail_summary.get("metadata_field_import_template_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_execution_action["evidence"].get(
                "metadata_field_import_supported_rows"
            ),
            source_next_focus_detail_summary.get("metadata_field_import_supported_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_execution_action["evidence"].get(
                "metadata_field_import_dry_run_updated_rows"
            ),
            field_import_dry_run.get("updated_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_execution_action["evidence"].get(
                "metadata_field_import_dry_run_skipped_rows"
            ),
            field_import_dry_run.get("skipped_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_execution_action["evidence"].get(
                "metadata_field_import_dry_run_skip_reason_counts"
            ),
            field_import_dry_run.get("skip_reason_counts"),
        )
        self.assertEqual(
            source_next_focus_detail_execution_action["evidence"].get("next_action_lanes"),
            source_next_focus_detail_summary.get("next_action_lanes"),
        )
        self.assertEqual(
            source_next_focus_detail_scorecard.get("next_action_lanes"),
            source_next_focus_detail_summary.get("next_action_lanes"),
        )
        self.assertEqual(
            source_next_focus_detail_scorecard.get("metadata_enrichment_template_rows"),
            source_next_focus_detail_summary.get("metadata_enrichment_template_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_scorecard.get("metadata_field_import_template_rows"),
            source_next_focus_detail_summary.get("metadata_field_import_template_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_scorecard.get("metadata_field_import_supported_rows"),
            source_next_focus_detail_summary.get("metadata_field_import_supported_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_scorecard.get("metadata_field_import_dry_run_updated_rows"),
            field_import_dry_run.get("updated_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_scorecard.get("metadata_field_import_dry_run_skipped_rows"),
            field_import_dry_run.get("skipped_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_next_action.get("next_action_lanes"),
            source_next_focus_detail_summary.get("next_action_lanes"),
        )
        self.assertEqual(
            source_next_focus_detail_next_action.get("metadata_enrichment_template_rows"),
            source_next_focus_detail_summary.get("metadata_enrichment_template_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_next_action.get("metadata_field_import_template_rows"),
            source_next_focus_detail_summary.get("metadata_field_import_template_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_next_action.get("metadata_field_import_supported_rows"),
            source_next_focus_detail_summary.get("metadata_field_import_supported_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_next_action.get("metadata_field_import_dry_run_updated_rows"),
            field_import_dry_run.get("updated_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_next_action.get("metadata_field_import_dry_run_skipped_rows"),
            field_import_dry_run.get("skipped_rows"),
        )
        self.assertEqual(
            source_next_focus_detail_scorecard.get("open_rows"),
            source_next_focus_detail_summary.get("pack_items"),
        )
        self.assertEqual(
            quality["source_discovery_action_queue"].get("top_source_store_workstreams"),
            expected_source_workstreams,
        )
        self.assertEqual(
            open_queues.get("ensky_cache_candidate_action_rows"),
            ensky_cache_action_summary.get("candidate_action_rows"),
        )
        self.assertEqual(
            open_queues.get("ensky_cache_candidate_manual_confirmed_rows"),
            ensky_cache_action_summary.get("manual_confirmed_true"),
        )
        self.assertEqual(
            ensky_cache_next_action.get("candidate_action_rows"),
            ensky_cache_action_summary.get("candidate_action_rows"),
        )
        for field in (
            "candidate_source_url_ready_rows",
            "candidate_image_url_ready_rows",
            "safe_exact_top_candidate_rows",
            "can_import_now_rows",
            "blocked_manual_review_rows",
        ):
            self.assertEqual(
                ensky_cache_next_action.get(field),
                ensky_cache_action_summary.get(field),
            )
            self.assertEqual(
                ensky_cache_scorecard.get(field),
                ensky_cache_action_summary.get(field),
            )
            self.assertEqual(
                quality["ensky_cache_candidate_action_queue"].get(field),
                ensky_cache_action_summary.get(field),
            )
        self.assertEqual(
            ensky_cache_next_action.get("import_readiness"),
            ensky_cache_action.get("import_readiness"),
        )
        self.assertEqual(
            ensky_cache_scorecard.get("import_readiness"),
            ensky_cache_action.get("import_readiness"),
        )
        self.assertEqual(
            quality["ensky_cache_candidate_action_queue"].get("candidate_action_rows"),
            ensky_cache_action_summary.get("candidate_action_rows"),
        )
        self.assertFalse(quality["ensky_cache_candidate_action_queue"].get("auto_apply_enabled"))
        self.assertEqual(
            open_queues.get("source_detail_candidate_action_rows"),
            source_detail_action_summary.get("candidate_action_rows"),
        )
        self.assertEqual(
            open_queues.get("source_detail_candidate_manual_confirmed_rows"),
            source_detail_action_summary.get("manual_confirmed_true"),
        )
        self.assertEqual(
            open_queues.get("source_detail_candidate_count_review_required_rows"),
            source_detail_action_summary.get("candidate_count_review_required_rows"),
        )
        self.assertEqual(
            source_detail_scorecard.get("open_rows"),
            source_detail_action_summary.get("candidate_action_rows"),
        )
        self.assertEqual(
            source_detail_scorecard.get("candidate_count_review_required_rows"),
            source_detail_action_summary.get("candidate_count_review_required_rows"),
        )
        self.assertEqual(
            source_detail_scorecard.get("by_review_risk"),
            source_detail_action_summary.get("by_review_risk"),
        )
        self.assertEqual(
            source_detail_next_action.get("candidate_action_rows"),
            source_detail_action_summary.get("candidate_action_rows"),
        )
        self.assertEqual(
            source_detail_next_action.get("candidate_count_review_required_rows"),
            source_detail_action_summary.get("candidate_count_review_required_rows"),
        )
        self.assertEqual(
            open_queues.get("metadata_action_missing_cells"),
            metadata_action_summary.get("queued_missing_cells"),
        )
        self.assertEqual(
            open_queues.get("metadata_actionable_groups"),
            metadata_action_summary.get("actionable_group_count"),
        )
        self.assertEqual(
            open_queues.get("metadata_unqueued_actionable_groups"),
            metadata_action_summary.get("unqueued_actionable_group_count"),
        )
        self.assertEqual(
            open_queues.get("metadata_actionable_missing_cells"),
            metadata_action_summary.get("actionable_missing_cells"),
        )
        self.assertEqual(
            open_queues.get("metadata_unqueued_actionable_missing_cells"),
            metadata_action_summary.get("unqueued_actionable_missing_cells"),
        )
        self.assertGreater(metadata_action_summary.get("primary_review_url_groups", 0), 0)
        self.assertEqual(
            open_queues.get("metadata_primary_review_url_groups"),
            metadata_action_summary.get("primary_review_url_groups"),
        )
        self.assertEqual(
            metadata_scorecard.get("missing_cell_queue_coverage"),
            metadata_action_summary.get("missing_cell_queue_coverage"),
        )
        self.assertEqual(
            metadata_scorecard.get("primary_review_url_groups"),
            metadata_action_summary.get("primary_review_url_groups"),
        )
        self.assertEqual(
            metadata_scorecard.get("first_primary_review_url"),
            metadata_action_summary.get("first_primary_review_url"),
        )
        self.assertEqual(
            metadata_scorecard.get("primary_review_url_kind_counts"),
            metadata_action_summary.get("primary_review_url_kind_counts"),
        )
        self.assertEqual(
            metadata_scorecard.get("missing_cells_by_field"),
            metadata_action_summary.get("missing_cells_by_field"),
        )
        self.assertEqual(
            metadata_scorecard.get("top_action_groups"),
            metadata_action_summary.get("top_action_groups"),
        )
        catalog_items = reports.load_json(reports.PUBLIC_CATALOG).get("items", [])
        metadata_review = reports.build_metadata_review_batches_public(catalog_items, "2026-01-01T00:00:00Z")
        rebuilt_metadata_action = build_metadata_action_queue_report(metadata_review)
        rebuilt_field_cells = [
            list(row) for row in rebuilt_metadata_action.get("summary", {}).get("missing_cells_by_field", [])
        ]
        self.assertEqual(
            rebuilt_field_cells,
            metadata_action_summary.get("missing_cells_by_field"),
        )
        self.assertEqual(
            rebuilt_metadata_action.get("summary", {}).get("primary_review_url_groups"),
            metadata_action_summary.get("primary_review_url_groups"),
        )
        self.assertEqual(
            metadata_next_action.get("unqueued_actionable_missing_cells"),
            metadata_action_summary.get("unqueued_actionable_missing_cells"),
        )
        self.assertEqual(
            metadata_next_action.get("primary_review_url_groups"),
            metadata_action_summary.get("primary_review_url_groups"),
        )
        self.assertEqual(
            metadata_next_action.get("first_primary_review_url"),
            metadata_action_summary.get("first_primary_review_url"),
        )
        first_metadata_batch = next(
            batch
            for batch in agent_queue["batches"]
            if batch.get("workstream") == "metadata_action_queue"
        )
        self.assertEqual(
            first_metadata_batch.get("review_summary", {}).get("first_primary_review_url"),
            metadata_action["batches"][0].get("first_primary_review_url"),
        )
        self.assertEqual(
            metadata_next_action.get("missing_cells_by_source_store"),
            metadata_action_summary.get("missing_cells_by_source_store"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_actionable_rows"),
            image_action_summary.get("actionable_image_rows"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_unqueued_actionable_rows"),
            image_action_summary.get("unqueued_actionable_image_rows"),
        )
        self.assertEqual(
            image_scorecard.get("unqueued_actionable_image_rows"),
            image_action_summary.get("unqueued_actionable_image_rows"),
        )
        self.assertEqual(
            image_scorecard.get("by_workflow"),
            image_action_summary.get("by_workflow"),
        )
        self.assertEqual(
            image_scorecard.get("excluded_workflow_rows"),
            image_action_summary.get("excluded_workflow_rows"),
        )
        self.assertEqual(
            image_next_action.get("sample_queue_coverage"),
            image_action_summary.get("sample_queue_coverage"),
        )
        self.assertEqual(
            image_next_action.get("source_url_update_template_rows"),
            image_action_summary.get("source_url_update_template_rows"),
        )
        self.assertEqual(
            image_next_action.get("source_url_update_search_hint_rows"),
            image_action_summary.get("source_url_update_search_hint_rows"),
        )
        self.assertEqual(
            image_scorecard.get("source_url_update_missing_search_hint_rows"),
            image_action_summary.get("source_url_update_missing_search_hint_rows"),
        )
        self.assertEqual(
            image_scorecard.get("primary_review_url_rows"),
            image_action_summary.get("primary_review_url_rows"),
        )
        self.assertEqual(
            image_scorecard.get("primary_review_url_missing_rows"),
            image_action_summary.get("primary_review_url_missing_rows"),
        )
        self.assertEqual(
            image_scorecard.get("by_review_lane"),
            image_action_summary.get("by_review_lane"),
        )
        self.assertEqual(
            image_scorecard.get("image_import_blocker_counts"),
            image_action_summary.get("image_import_blocker_counts"),
        )
        self.assertEqual(
            image_scorecard.get("local_image_download_instruction_ready_rows"),
            image_action_summary.get("local_image_download_instruction_ready_rows"),
        )
        self.assertEqual(
            image_scorecard.get("blocked_before_image_import_rows"),
            image_action_summary.get("blocked_before_image_import_rows"),
        )
        self.assertEqual(
            image_scorecard.get("download_ready_after_manual_image_url_rows"),
            image_action_summary.get("download_ready_after_manual_image_url_rows"),
        )
        self.assertEqual(
            image_scorecard.get("attachment_readiness"),
            image_action.get("attachment_readiness"),
        )
        self.assertEqual(
            image_next_action.get("primary_review_url_rows"),
            image_action_summary.get("primary_review_url_rows"),
        )
        self.assertEqual(
            image_next_action.get("by_review_lane"),
            image_action_summary.get("by_review_lane"),
        )
        self.assertEqual(
            image_next_action.get("primary_review_url_kind_counts"),
            image_action_summary.get("primary_review_url_kind_counts"),
        )
        self.assertEqual(
            image_next_action.get("by_source_store"),
            image_action_summary.get("by_source_store"),
        )
        self.assertEqual(
            open_queues.get("dedupe_action_groups"),
            dedupe_action_summary.get("queued_groups"),
        )
        self.assertEqual(
            open_queues.get("dedupe_actionable_groups"),
            dedupe_action_summary.get("actionable_groups"),
        )
        self.assertEqual(
            open_queues.get("dedupe_unqueued_actionable_groups"),
            dedupe_action_summary.get("unqueued_actionable_groups"),
        )
        self.assertEqual(
            dedupe_scorecard.get("queue_coverage"),
            dedupe_action_summary.get("queue_coverage"),
        )
        self.assertEqual(
            dedupe_next_action.get("unqueued_actionable_groups"),
            dedupe_action_summary.get("unqueued_actionable_groups"),
        )
        for field in (
            "ichiban_reissue_review_groups",
            "ichiban_probable_reissue_review_groups",
            "ichiban_reissue_protected_groups",
        ):
            self.assertEqual(dedupe_scorecard.get(field), dedupe_action_summary.get(field))
            self.assertEqual(dedupe_next_action.get(field), dedupe_action_summary.get(field))
        self.assertEqual(
            open_queues.get("ichiban_reissue_dedupe_review_groups"),
            dedupe_action_summary.get("ichiban_reissue_review_groups"),
        )
        self.assertEqual(
            open_queues.get("ichiban_probable_reissue_dedupe_review_groups"),
            dedupe_action_summary.get("ichiban_probable_reissue_review_groups"),
        )
        self.assertEqual(
            ichiban_reissue_dedupe_scorecard.get("open_rows"),
            dedupe_action_summary.get("ichiban_reissue_review_groups"),
        )
        self.assertEqual(
            ichiban_reissue_dedupe_next_action.get("review_groups"),
            dedupe_action_summary.get("ichiban_reissue_review_groups"),
        )
        self.assertEqual(
            ichiban_reissue_dedupe_next_action.get("work_order_rows"),
            dedupe_action_summary.get("ichiban_reissue_work_order_rows"),
        )
        self.assertTrue(
            ichiban_reissue_dedupe_next_action.get("campaign_url_comparison_preview")
        )
        self.assertEqual(
            ichiban_reissue_dedupe_next_action.get("decision_template_rows"),
            dedupe_action_summary.get("ichiban_reissue_decision_template_rows"),
        )
        self.assertEqual(
            ichiban_reissue_dedupe_next_action.get("public_report"),
            "data/ichiban_kuji_reissue_decision_template_public.json",
        )
        self.assertEqual(
            ichiban_reissue_dedupe_next_action.get("work_order_report"),
            "data/catalog_deduplication_action_queue_public.json",
        )
        self.assertEqual(
            dedupe_action_summary.get("ichiban_reissue_work_orders_with_evidence_urls"),
            dedupe_action_summary.get("ichiban_reissue_work_order_rows"),
        )
        self.assertEqual(
            dedupe_action_summary.get("ichiban_reissue_campaign_work_orders_with_evidence_urls"),
            dedupe_action_summary.get("ichiban_reissue_campaign_work_order_rows"),
        )
        self.assertTrue(dedupe_action_summary.get("ichiban_reissue_first_evidence_url"))
        self.assertEqual(
            dedupe_action["ichiban_reissue_work_order"][0]["first_evidence_url"],
            dedupe_action_summary.get("ichiban_reissue_first_evidence_url"),
        )
        self.assertGreater(
            dedupe_action["ichiban_reissue_work_order"][0]["evidence_url_count"],
            0,
        )
        self.assertEqual(ichiban_reissue_dedupe_next_action.get("item_decision_template_rows"), 20)
        self.assertEqual(ichiban_reissue_dedupe_next_action.get("campaign_decision_template_rows"), 4)
        self.assertEqual(
            ichiban_reissue_dedupe_next_action.get("manual_confirmed_rows"),
            dedupe_action_summary.get("ichiban_reissue_manual_confirmed_rows"),
        )
        self.assertEqual(
            ichiban_reissue_dedupe_next_action.get("next_step"),
            "fill_ichiban_reissue_decision_template_before_dedupe",
        )
        self.assertGreater(len(ichiban_reissue_dedupe_agent_batches), 0)
        self.assertEqual(
            ichiban_reissue_campaign_first_batch.get("rows"),
            reissue_decision_summary.get("campaign_review_batch_rows"),
        )
        self.assertEqual(
            ichiban_reissue_campaign_first_batch.get("review_summary", {}).get(
                "campaign_review_batch_item_work_order_rows"
            ),
            reissue_decision_summary.get("campaign_review_batch_item_work_order_rows"),
        )
        self.assertEqual(
            ichiban_reissue_campaign_first_batch.get("review_summary", {}).get(
                "campaign_review_batch_visible_item_preview_rows"
            ),
            reissue_decision_summary.get("campaign_review_batch_visible_item_preview_rows"),
        )
        self.assertTrue(
            all(
                item.get("source_urls")
                for item in ichiban_reissue_campaign_first_batch.get("sample_items", [])
            )
        )
        ichiban_reissue_lane_batch = next(
            batch
            for batch in ichiban_reissue_dedupe_agent_batches
            if batch.get("title") != "Ichiban Kuji reissue campaign decisions first"
        )
        self.assertEqual(
            ichiban_reissue_lane_batch.get("public_report"),
            "data/ichiban_kuji_reissue_decision_template_public.json",
        )
        self.assertEqual(ichiban_reissue_lane_batch["rows"], 2)
        self.assertEqual(len(ichiban_reissue_lane_batch["sample_items"]), 2)
        self.assertTrue(
            ichiban_reissue_lane_batch.get("review_summary", {}).get("first_evidence_url")
        )
        self.assertGreater(
            ichiban_reissue_lane_batch.get("review_summary", {}).get("source_url_count", 0),
            1,
        )
        self.assertTrue(
            all(item.get("source_url") for item in ichiban_reissue_lane_batch["sample_items"])
        )
        self.assertEqual(
            open_queues.get("ichiban_metadata_action_campaigns"),
            ichiban_action_summary.get("queued_action_campaigns"),
        )
        self.assertEqual(
            open_queues.get("ichiban_metadata_actionable_campaigns"),
            ichiban_action_summary.get("actionable_campaigns"),
        )
        self.assertEqual(
            open_queues.get("ichiban_metadata_unqueued_action_campaigns"),
            ichiban_action_summary.get("unqueued_action_campaigns"),
        )
        self.assertEqual(
            open_queues.get("ichiban_metadata_queued_catalog_item_rows"),
            ichiban_action_summary.get("queued_catalog_item_rows"),
        )
        self.assertEqual(
            open_queues.get("ichiban_metadata_next_campaign_patch_review_batch_rows"),
            ichiban_action_summary.get("next_campaign_patch_review_batch_rows"),
        )
        self.assertEqual(
            open_queues.get(
                "ichiban_metadata_next_campaign_patch_review_batch_template_rows"
            ),
            ichiban_action_summary.get("next_campaign_patch_review_batch_template_rows"),
        )
        self.assertEqual(
            open_queues.get(
                "ichiban_metadata_next_campaign_patch_review_batch_primary_review_url_rows"
            ),
            ichiban_action_summary.get(
                "next_campaign_patch_review_batch_primary_review_url_rows"
            ),
        )
        self.assertEqual(
            ichiban_scorecard.get("campaign_queue_coverage"),
            ichiban_action_summary.get("campaign_queue_coverage"),
        )
        self.assertEqual(
            ichiban_next_action.get("field_patch_template_counts"),
            ichiban_action_summary.get("field_patch_template_counts"),
        )
        self.assertEqual(
            ichiban_next_action.get("next_campaign_patch_review_batch_rows"),
            ichiban_action_summary.get("next_campaign_patch_review_batch_rows"),
        )
        self.assertEqual(
            ichiban_next_action.get("next_campaign_patch_review_batch_field_counts"),
            ichiban_action_summary.get("next_campaign_patch_review_batch_field_counts"),
        )
        self.assertEqual(
            ichiban_next_action.get("work_order_steps"),
            ichiban_action_summary.get("work_order_steps"),
        )
        self.assertEqual(
            ichiban_next_action.get("work_order_lanes"),
            ichiban_action_summary.get("work_order_lanes"),
        )
        self.assertEqual(
            ichiban_scorecard.get("work_order_lanes"),
            ichiban_action_summary.get("work_order_lanes"),
        )
        self.assertEqual(
            ichiban_prize_next_action.get("last_one_nonzero_price_rows"),
            ichiban_prize_audit_summary.get("last_one_nonzero_price_rows"),
        )
        self.assertEqual(
            ichiban_prize_next_action.get("double_chance_nonzero_price_rows"),
            ichiban_prize_audit_summary.get("double_chance_nonzero_price_rows"),
        )
        self.assertEqual(
            ichiban_prize_next_action.get("multi_item_prize_label_review_batch_count"),
            ichiban_prize_audit_summary.get("multi_item_prize_label_review_batch_count"),
        )
        self.assertEqual(
            ichiban_prize_next_action.get("repeated_name_different_source_review_batch_count"),
            ichiban_prize_audit_summary.get("repeated_name_different_source_review_batch_count"),
        )
        self.assertEqual(
            ichiban_prize_next_action.get("prize_policy_review_batch_count"),
            ichiban_prize_audit_summary.get("prize_policy_review_batch_count"),
        )
        self.assertEqual(
            ichiban_reissue_execution_action["evidence"].get("ichiban_reissue_work_order_rows"),
            dedupe_action_summary.get("ichiban_reissue_work_order_rows"),
        )
        self.assertEqual(
            ichiban_reissue_execution_action["evidence"].get("ichiban_reissue_decision_template_rows"),
            dedupe_action_summary.get("ichiban_reissue_decision_template_rows"),
        )
        self.assertEqual(
            ichiban_reissue_execution_action["evidence"].get("ichiban_reissue_manual_confirmed_rows"),
            dedupe_action_summary.get("ichiban_reissue_manual_confirmed_rows"),
        )
        self.assertEqual(
            ichiban_reissue_execution_action.get("public_report"),
            "data/ichiban_kuji_reissue_decision_template_public.json",
        )
        self.assertEqual(
            ichiban_reissue_execution_action["evidence"].get(
                "ichiban_reissue_decision_template_report"
            ),
            "data/ichiban_kuji_reissue_decision_template_public.json",
        )
        self.assertEqual(
            ichiban_reissue_execution_action["evidence"].get(
                "ichiban_reissue_item_template_rows"
            ),
            20,
        )
        self.assertEqual(
            ichiban_reissue_execution_action["evidence"].get(
                "ichiban_reissue_campaign_template_rows"
            ),
            4,
        )
        self.assertEqual(
            ichiban_reissue_execution_action["evidence"].get(
                "ichiban_reissue_item_review_lane_counts"
            ),
            reissue_decision_summary.get("item_review_lane_counts"),
        )
        self.assertEqual(
            ichiban_reissue_execution_action["evidence"].get(
                "ichiban_reissue_campaign_review_lane_counts"
            ),
            reissue_decision_summary.get("campaign_review_lane_counts"),
        )
        self.assertEqual(
            ichiban_reissue_execution_action["evidence"].get(
                "ichiban_reissue_same_campaign_family_item_rows"
            ),
            reissue_decision_summary.get("same_campaign_family_reissue_item_rows"),
        )
        self.assertEqual(
            ichiban_reissue_execution_action.get("next_step"),
            "fill_ichiban_reissue_decision_template_before_dedupe",
        )
        self.assertIs(ichiban_prize_next_action.get("zero_price_exception_policy_pass"), True)
        self.assertEqual(
            open_queues.get("ichiban_prize_name_image_review_rows"),
            ichiban_prize_name_image_summary.get("review_rows"),
        )
        self.assertEqual(
            open_queues.get("ichiban_prize_multi_item_rank_groups"),
            ichiban_prize_name_image_summary.get("multi_item_prize_rank_groups"),
        )
        self.assertEqual(
            ichiban_prize_name_image_scorecard.get("open_rows"),
            ichiban_prize_name_image_summary.get("review_rows"),
        )
        self.assertEqual(
            ichiban_prize_name_image_scorecard.get("multi_item_prize_rank_groups"),
            ichiban_prize_name_image_summary.get("multi_item_prize_rank_groups"),
        )
        self.assertEqual(
            ichiban_prize_name_image_next_action.get("name_structure_review_rows"),
            ichiban_prize_name_image_summary.get("name_structure_review_rows"),
        )
        self.assertEqual(
            ichiban_prize_name_image_next_action.get("image_identity_review_rows"),
            ichiban_prize_name_image_summary.get("image_identity_review_rows"),
        )
        self.assertEqual(
            open_queues.get("ichiban_prize_name_image_patch_candidate_rows"),
            ichiban_prize_name_image_patch_summary.get(
                "open_candidate_rows",
                ichiban_prize_name_image_patch_summary.get("candidate_rows"),
            ),
        )
        self.assertEqual(
            open_queues.get("ichiban_prize_name_image_patch_manual_confirmed_rows"),
            ichiban_prize_name_image_patch_summary.get("manual_confirmed_rows", 0),
        )
        self.assertEqual(
            open_queues.get("ichiban_prize_name_image_patch_blocked_rows"),
            ichiban_prize_name_image_patch_summary.get("blocked_rows"),
        )
        self.assertEqual(
            ichiban_prize_name_image_patch_scorecard.get("open_rows"),
            ichiban_prize_name_image_patch_summary.get(
                "open_candidate_rows",
                ichiban_prize_name_image_patch_summary.get("candidate_rows"),
            ),
        )
        self.assertEqual(
            ichiban_prize_name_image_patch_next_action.get("exact_image_match_rows"),
            ichiban_prize_name_image_patch_summary.get("exact_image_match_rows"),
        )
        self.assertEqual(
            open_queues.get("animation_category_action_rows"),
            animation_action_summary.get("queued_catalog_rows"),
        )
        self.assertEqual(
            open_queues.get("animation_category_split_review_categories"),
            animation_action_summary.get("split_review_categories"),
        )
        self.assertEqual(
            open_queues.get("animation_category_direct_mapping_categories"),
            animation_action_summary.get("direct_mapping_categories"),
        )
        self.assertEqual(
            open_queues.get("animation_category_name_split_rows"),
            animation_split_summary.get("affected_catalog_rows"),
        )
        self.assertEqual(
            open_queues.get("animation_category_name_split_candidates"),
            animation_split_summary.get("candidate_split_rules"),
        )
        self.assertEqual(
            open_queues.get("animation_category_name_split_unmatched_catalog_rows"),
            animation_split_summary.get("unmatched_catalog_rows"),
        )
        self.assertEqual(
            open_queues.get("animation_category_unmatched_keyword_rows"),
            animation_keyword_summary.get("unmatched_rows"),
        )
        self.assertEqual(
            open_queues.get("animation_category_unmatched_keyword_candidates"),
            animation_keyword_summary.get("token_candidate_count"),
        )
        self.assertEqual(
            open_queues.get("animation_category_unmatched_keyword_product_type_candidates"),
            animation_keyword_summary.get("product_type_candidate_count"),
        )
        self.assertEqual(
            animation_scorecard.get("split_review_categories"),
            animation_action_summary.get("split_review_categories"),
        )
        self.assertEqual(
            animation_next_action.get("direct_mapping_categories"),
            animation_action_summary.get("direct_mapping_categories"),
        )
        self.assertEqual(animation_action_summary.get("app_folder_color_count"), 188)
        self.assertEqual(animation_action_summary.get("app_folder_icon_option_count"), 211)
        self.assertTrue(animation_action_summary.get("app_folder_palette_sorted_by_family"))
        animation_visual_catalog = animation_action.get("app_folder_visual_catalog") or {}
        self.assertEqual(len(animation_visual_catalog.get("palette_color_families") or []), 8)
        self.assertEqual(len(animation_visual_catalog.get("palette_picker_order") or []), 188)
        self.assertEqual(
            animation_scorecard.get("app_folder_color_count"),
            animation_action_summary.get("app_folder_color_count"),
        )
        self.assertEqual(
            animation_next_action.get("app_folder_icon_option_count"),
            animation_action_summary.get("app_folder_icon_option_count"),
        )
        self.assertEqual(
            animation_split_scorecard.get("candidate_split_rules"),
            animation_split_summary.get("candidate_split_rules"),
        )
        self.assertEqual(
            animation_split_next_action.get("matched_sample_names"),
            animation_split_summary.get("matched_sample_names"),
        )
        self.assertEqual(
            animation_split_scorecard.get("matched_catalog_rows"),
            animation_split_summary.get("matched_catalog_rows"),
        )
        self.assertEqual(
            animation_split_next_action.get("unmatched_catalog_rows"),
            animation_split_summary.get("unmatched_catalog_rows"),
        )
        self.assertFalse(animation_split_summary.get("auto_apply_enabled"))
        self.assertEqual(
            animation_keyword_next_action.get("token_candidate_count"),
            animation_keyword_summary.get("token_candidate_count"),
        )
        self.assertEqual(
            animation_keyword_next_action.get("product_type_candidate_count"),
            animation_keyword_summary.get("product_type_candidate_count"),
        )
        self.assertFalse(animation_keyword_summary.get("auto_apply_enabled"))
        if animation_action_summary.get("queued_catalog_rows") or animation_action_summary.get("normalization_review_rows"):
            self.assertGreater(len(animation_agent_batches), 0)
        else:
            self.assertEqual(len(animation_agent_batches), 0)
        if animation_split_summary.get("affected_catalog_rows"):
            self.assertGreater(len(animation_split_agent_batches), 0)
        else:
            self.assertEqual(len(animation_split_agent_batches), 0)
        if animation_keyword_summary.get("unmatched_rows"):
            self.assertGreater(len(animation_keyword_agent_batches), 0)
        else:
            self.assertEqual(len(animation_keyword_agent_batches), 0)
        self.assertTrue(
            all(
                "split_review_categories" in batch.get("review_summary", {})
                for batch in animation_agent_batches
            )
        )
        self.assertTrue(
            all(
                "split_candidate_count" in batch.get("review_summary", {})
                for batch in animation_split_agent_batches
            )
        )
        self.assertTrue(
            all(
                "token_candidate_count" in batch.get("review_summary", {})
                for batch in animation_keyword_agent_batches
            )
        )
        self.assertTrue(
            all(
                "sample_source" in batch.get("review_summary", {})
                for batch in animation_keyword_agent_batches
            )
        )


    def test_image_attachment_template_import_dry_run_has_actionable_summary(self):
        template = {
            "items": [
                {
                    "manual_confirmed": False,
                    "row_index": 0,
                    "catalog_index": 10,
                    "field": "image_url",
                    "manual_value": "",
                    "candidate_source_url": "",
                    "name_ko": "Sample",
                    "source_url_update_required": True,
                    "representative_image_review_required": False,
                    "image_url_ready": False,
                }
            ]
        }
        catalog = {
            "items": [
                {
                    "catalog_index": 10,
                    "name_ko": "Sample",
                    "source_url": "https://fanding.kr/@stellive/shop",
                    "image_url": None,
                }
            ]
        }

        dry_run = reports.build_image_attachment_template_import_dry_run_public(
            template,
            catalog,
            "2026-07-24T00:00:00Z",
        )

        self.assertEqual(dry_run["schema_version"], 2)
        self.assertEqual(dry_run["summary"]["template_items"], 1)
        self.assertEqual(dry_run["summary"]["manual_confirmed_rows"], 0)
        self.assertEqual(dry_run["summary"]["ready_image_rows"], 0)
        self.assertEqual(dry_run["summary"]["source_url_update_required_rows"], 1)
        self.assertEqual(dry_run["summary"]["updated_rows"], 0)
        self.assertEqual(dry_run["summary"]["skipped_rows"], 1)
        self.assertEqual(dry_run["summary"]["skip_reason_counts"], [("manual_confirmed_false", 1)])
        self.assertIs(dry_run["summary"]["auto_apply_enabled"], False)
        self.assertEqual(dry_run["queue"], "data/catalog_image_attachment_confirmed_template_public.json")
        self.assertEqual(dry_run["skipped_sample"][0]["reason"], "manual_confirmed_false")


if __name__ == "__main__":
    unittest.main()
