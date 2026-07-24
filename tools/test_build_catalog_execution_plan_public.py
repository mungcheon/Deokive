from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_catalog_execution_plan_public as plan


class BuildCatalogExecutionPlanPublicTest(unittest.TestCase):
    def test_write_report_skips_timestamp_only_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "execution_plan.json"
            report = {
                "schema_version": 1,
                "generated_at": "2026-01-01T00:00:00Z",
                "summary": {"action_count": 1},
                "actions": [],
            }
            plan.write_report(report, path)
            first_mtime = path.stat().st_mtime_ns

            plan.write_report({**report, "generated_at": "2026-01-01T00:01:00Z"}, path)

            self.assertEqual(path.stat().st_mtime_ns, first_mtime)

    def test_plan_prefers_manual_confirmation_before_import(self) -> None:
        payloads = {
            "catalog_operations_public.json": {
                "summary": {"open_review_queues": {"image_missing_rows": 10}}
            },
            "catalog_image_enrichment_batches_public.json": {
                "summary": {"missing_image_rows": 10, "source_url_ready_rows": 0, "needs_source_discovery_rows": 10}
            },
            "catalog_image_candidate_review_public.json": {
                "summary": {
                    "provider_candidate_items": 7,
                    "manual_or_blocked_items": 3,
                }
            },
            "catalog_image_asset_audit_public.json": {
                "summary": {
                    "status": "pass",
                    "download_readiness_status": "known_image_assets_complete",
                    "image_url_rows": 90,
                    "local_image_path_rows": 90,
                    "image_url_without_local_path_rows": 0,
                    "missing_local_image_files": 0,
                    "missing_web_public_asset_files": 0,
                    "known_image_download_blocker_rows": 0,
                    "auto_download_ready_rows": 0,
                    "rows_still_requiring_image_url_evidence": 10,
                }
            },
            "catalog_image_attachment_action_queue_public.json": {
                "summary": {
                    "actionable_image_rows": 2,
                    "queued_image_rows": 2,
                    "action_batch_count": 1,
                    "excluded_workflow_rows": [["find_source_then_extract_image", 8]],
                    "source_url_update_required_rows": 2,
                    "source_url_update_template_rows": 2,
                    "source_url_update_template_batch_count": 1,
                    "representative_image_review_required_rows": 0,
                    "image_url_ready_rows": 0,
                    "download_ready_after_manual_image_url_rows": 2,
                    "suggested_local_image_path_rows": 2,
                    "local_image_download_instruction_ready_rows": 2,
                    "workstream_count": 1,
                    "source_url_update_workstream_count": 1,
                    "representative_image_review_workstream_count": 0,
                },
                "workstreams": [
                    {
                        "workflow": "replace_generic_source_then_extract_image",
                        "source_store": "Stellive Store",
                        "queued_image_rows": 2,
                        "batch_count": 1,
                        "next_batch_id": "image-attachment-action-001",
                        "source_url_update_template_rows": 2,
                        "representative_image_review_rows": 0,
                    }
                ],
            },
            "catalog_missing_image_actionability_public.json": {
                "summary": {
                    "image_attachment_template_rows": 2,
                    "image_attachment_template_confirmed_rows": 0,
                    "image_attachment_template_dry_run_updated_rows": 0,
                    "image_attachment_template_dry_run_skipped_rows": 2,
                    "source_discovery_focus_template_rows": 8,
                    "source_discovery_focus_template_confirmed_rows": 0,
                }
            },
            "source_discovery_review_batches_public.json": {
                "summary": {"source_discovery_rows": 10, "batch_count": 2}
            },
            "source_discovery_action_queue_public.json": {
                "summary": {
                    "actionable_source_rows": 8,
                    "queued_source_rows": 4,
                    "unqueued_actionable_source_rows": 4,
                    "action_batch_count": 1,
                    "manual_research_backlog_rows": 2,
                    "source_discovery_template_rows": 4,
                    "source_discovery_template_batch_count": 1,
                    "source_patch_template_count": 4,
                    "catalog_field_import_template_count": 4,
                    "primary_review_url_rows": 4,
                    "primary_review_url_kind_counts": [["official_search_url", 4]],
                    "manual_research_backlog_by_source_store": [["Idol official", 2]],
                    "excluded_review_state_rows": [["manual_official_research_required", 2]],
                    "by_review_state": [["official_search_review_required", 3], ["licensed_retailer_review_required", 1]],
                    "by_workflow": [["official_search_url_available", 3], ["licensed_retailer_search_review", 1]],
                    "by_source_store": [["Animate", 3], ["AmiAmi", 1]],
                    "first_primary_review_url": "https://animate.example/search?q=source",
                    "first_primary_review_url_kind": "official_search_url",
                }
            },
            "source_discovery_focus_confirmed_template_public.json": {
                "summary": {
                    "template_items": 8,
                    "manual_confirmed_rows": 0,
                    "work_order_pack_count": 2,
                    "next_focus_pack_id": "source-discovery-focus-001",
                    "next_source_store": "Animate",
                    "next_target_category": "Acrylic stand",
                    "next_focus_pack_rows": 4,
                    "next_official_search_url": "https://animate.example/search?q=stand",
                    "auto_apply_enabled": False,
                }
            },
            "source_discovery_focus_template_import_dry_run_public.json": {
                "updated_rows": 0,
                "skipped_rows": 8,
            },
            "source_discovery_next_focus_pack_public.json": {
                "summary": {
                    "focus_pack_id": "source-discovery-focus-001",
                    "pack_queue_preview_count": 2,
                    "next_pack_after_current": "source-discovery-focus-002",
                },
                "pack_queue_preview": [
                    {
                        "focus_pack_id": "source-discovery-focus-001",
                        "is_current_pack": True,
                        "source_store": "Animate",
                        "target_category": "Acrylic stand",
                        "remaining_review_rows": 4,
                    },
                    {
                        "focus_pack_id": "source-discovery-focus-002",
                        "is_current_pack": False,
                        "source_store": "Animate",
                        "target_category": "Badge",
                        "remaining_review_rows": 4,
                    },
                ],
            },
            "source_discovery_next_focus_pack_fetch_audit_public.json": {
                "summary": {
                    "focus_pack_id": "source-discovery-focus-001",
                    "pack_items": 4,
                    "official_search_ok_rows": 0,
                    "official_search_unavailable_rows": 4,
                    "status_counts": [["http_error_404", 4]],
                    "fallback_web_search_required": True,
                    "auto_apply_enabled": False,
                }
            },
            "source_discovery_next_focus_fallback_queue_public.json": {
                "summary": {
                    "focus_pack_id": "source-discovery-focus-001",
                    "queue_rows": 4,
                    "manual_confirmed_rows": 0,
                    "source_confirmation_ready_rows": 3,
                    "metadata_backfill_required_rows": 1,
                    "variant_disambiguation_required_rows": 1,
                    "by_identity_review_status": [
                        ["exact_page_match_review_ready", 3],
                        ["variant_disambiguation_required", 1],
                    ],
                    "fallback_reason": "official_search_url_unavailable",
                    "by_http_status": [["404", 4]],
                    "by_source_store": [["Animate", 4]],
                    "by_category": [["Acrylic stand", 4]],
                    "work_order_steps": 3,
                    "work_order_lanes": [
                        "domain_limited_exact_title_search",
                        "legacy_mobile_store_search",
                        "evidence_fill_and_dry_run",
                    ],
                    "first_domain_limited_web_search_url": "https://google.example/search?q=site%3Aanimate",
                    "first_fallback_store_search_url": "https://animate.example/sphone/products/list.php",
                    "auto_apply_enabled": False,
                }
            },
            "source_discovery_next_focus_exact_url_review_queue_public.json": {
                "summary": {
                    "queue_rows": 3,
                    "manual_confirmed_rows": 0,
                    "blocked_identity_rows": 1,
                    "by_source_store": [["Animate", 3]],
                    "by_category": [["Acrylic stand", 3]],
                    "by_identity_review_status": [
                        ["exact_page_match_review_ready", 3]
                    ],
                    "primary_review_url_rows": 3,
                    "primary_review_url_kind_counts": [
                        ["domain_limited_web_search", 3]
                    ],
                    "first_primary_review_url": "https://google.example/search?q=exact",
                    "first_primary_review_url_kind": "domain_limited_web_search",
                    "auto_apply_enabled": False,
                }
            },
            "source_discovery_next_focus_identity_backfill_queue_public.json": {
                "summary": {
                    "queue_rows": 1,
                    "manual_confirmed_rows": 0,
                }
            },
            "source_discovery_next_focus_identity_candidate_review_queue_public.json": {
                "summary": {
                    "queue_rows": 1,
                    "candidate_rows": 2,
                    "manual_confirmed_rows": 0,
                }
            },
            "source_discovery_next_focus_fallback_import_dry_run_public.json": {
                "write": False,
                "updated_rows": 0,
                "skipped_rows": 4,
                "skip_reason_counts": [["manual_confirmed_false", 4]],
            },
            "source_discovery_starter_queue_public.json": {
                "summary": {
                    "starter_queue_rows": 12,
                    "starter_queue_groups": 3,
                    "coverage_matches_missing_source_url_rows": True,
                    "by_source_store": [["Animate", 8], ["Good Smile Company", 4]],
                    "auto_apply_enabled": False,
                },
                "groups": [
                    {
                        "group_key": "Animate|Acrylic stand",
                        "rows": 8,
                        "source_store": "Animate",
                        "category": "Acrylic stand",
                        "first_search_url": "https://animate.example/search?q=acrylic",
                        "search_urls": ["https://animate.example/search?q=acrylic"],
                    },
                    {
                        "group_key": "Good Smile Company|Figure",
                        "rows": 4,
                        "source_store": "Good Smile Company",
                        "category": "Figure",
                        "first_search_url": "https://goodsmile.example/search?q=figure",
                        "search_urls": ["https://goodsmile.example/search?q=figure"],
                    },
                    {
                        "group_key": "Fallback|Mascot",
                        "rows": 1,
                        "source_store": "Fallback Store",
                        "category": "Mascot",
                        "first_fallback_web_search_url": "https://www.google.com/search?q=fallback",
                        "fallback_web_search_urls": ["https://www.google.com/search?q=fallback"],
                    },
                ],
            },
            "ensky_cache_candidate_action_queue_public.json": {
                "summary": {
                    "candidate_action_rows": 5,
                    "action_batch_count": 1,
                    "manual_confirmed_true": 0,
                    "candidate_source_url_ready_rows": 5,
                    "candidate_image_url_ready_rows": 4,
                    "safe_exact_top_candidate_rows": 0,
                    "can_import_now_rows": 0,
                    "blocked_manual_review_rows": 5,
                    "by_affiliation": [["Chiikawa", 3], ["Danganronpa", 2]],
                    "by_category": [["Acrylic stand", 3], ["Mascot", 2]],
                    "auto_apply_enabled": False,
                },
                "import_readiness": {
                    "candidate_rows": 5,
                    "candidate_source_url_ready_rows": 5,
                    "candidate_image_url_ready_rows": 4,
                    "safe_exact_top_candidate_rows": 0,
                    "identity_warning_rows": 5,
                    "can_import_now_rows": 0,
                    "blocked_manual_review_rows": 5,
                    "manual_confirmation_required": True,
                    "auto_apply_enabled": False,
                },
            },
            "catalog_metadata_review_batches_public.json": {
                "summary": {"missing_cell_count": 20, "batch_count": 2, "field_missing_totals": {"barcode": 20}}
            },
            "catalog_metadata_action_queue_public.json": {
                "summary": {
                    "actionable_group_count": 2,
                    "queued_group_count": 2,
                    "actionable_missing_cells": 8,
                    "queued_missing_cells": 8,
                    "action_batch_count": 1,
                    "field_counts": [["release_date", 1], ["name_ja", 1]],
                    "missing_cells_by_field": [["release_date", 6], ["name_ja", 2]],
                    "missing_cells_by_source_store": [["Store A", 6], ["Store B", 2]],
                    "top_action_groups": [
                        {"field": "release_date", "source_store": "Store A", "missing_rows": 6}
                    ],
                }
            },
            "requested_focus_enrichment_public.json": {
                "summary": {
                    "topic_count": 2,
                    "total_matched_catalog_rows": 9,
                    "total_requested_labels": 4,
                    "topics_with_open_work": 2,
                    "open_rows": 7,
                    "missing_image_rows": 1,
                    "missing_source_url_rows": 1,
                    "missing_release_date_rows": 2,
                    "missing_official_price_jpy_rows": 3,
                    "requested_needs_review": 1,
                }
            },
            "requested_focus_review_batches_public.json": {
                "summary": {
                    "review_row_count": 5,
                    "batch_count": 1,
                    "topic_with_batches_count": 2,
                    "by_topic": [["ichiban_kuji", 3], ["danganronpa", 2]],
                    "by_missing_field": [["barcode", 3], ["source_url", 1], ["image_url", 1]],
                    "field_patch_template_count": 5,
                    "field_patch_template_counts": [
                        ["barcode", 3],
                        ["source_url", 1],
                        ["image_url", 1],
                    ],
                }
            },
            "requested_focus_action_queue_public.json": {
                "summary": {
                    "actionable_template_rows": 2,
                    "queued_action_rows": 2,
                    "unqueued_actionable_rows": 0,
                    "queue_coverage": 1.0,
                    "action_batch_count": 1,
                    "barcode_template_rows_excluded": 3,
                    "non_barcode_template_rows": 2,
                    "total_review_template_rows": 5,
                    "non_barcode_template_share": 0.4,
                    "skipped_non_template_rows": 0,
                    "field_counts": [["source_url", 1], ["image_url", 1]],
                    "topic_counts": [["danganronpa", 2]],
                    "blocked_reason_counts": [
                        ["missing_exact_source_url_for_requested_focus", 1],
                    ],
                    "blocked_until_counts": [
                        ["exact_product_source_url_confirmed", 1],
                    ],
                    "review_url_rows": 2,
                    "primary_review_url_kind_counts": [
                        ["existing_source_url", 1],
                        ["domain_limited_web_search", 1],
                    ],
                    "barcode_template_rows_excluded_blocked_reason": "barcode_research_deferred",
                    "barcode_template_rows_excluded_blocked_until": "source_image_date_price_queue_reviewed",
                }
            },
            "danganronpa_missing_media_public.json": {
                "summary": {
                    "missing_media_rows": 4,
                    "missing_image_url_rows": 4,
                    "missing_source_url_rows": 4,
                    "review_batch_count": 2,
                    "official_search_rows": 2,
                    "licensed_retailer_review_rows": 1,
                    "official_prize_search_rows": 1,
                    "confirmed_patch_template_rows": 4,
                    "confirmed_patch_template_pending_rows": 4,
                    "by_source_store": [["Movic", 2], ["Taito", 1], ["AmiAmi", 1]],
                    "by_source_kind": [
                        ["official_manufacturer", 2],
                        ["official_prize", 1],
                        ["licensed_retailer", 1],
                    ],
                }
            },
            "danganronpa_patch_template_dry_run_public.json": {
                "summary": {
                    "template_rows": 4,
                    "ready_rows": 0,
                    "skipped_rows": 4,
                    "blocked_rows": 0,
                    "manual_confirmed_source_rows": 0,
                    "manual_confirmed_image_rows": 0,
                    "by_status": [["skipped_pending_manual_confirmation", 4]],
                }
            },
            "catalog_deduplication_public.json": {
                "summary": {
                    "duplicate_groups": 3,
                    "duplicate_rows": 6,
                    "published_groups": 3,
                    "by_key_type": [["barcode", 2], ["source_url", 1]],
                    "by_review_risk": [
                        ["strong_identity_review", 2],
                        ["variant_risk_review", 1],
                    ],
                    "top_review_risk": "strong_identity_review",
                }
            },
            "catalog_deduplication_review_batches_public.json": {
                "summary": {"source_groups": 1, "batch_count": 1}
            },
            "catalog_deduplication_action_queue_public.json": {
                "summary": {
                    "actionable_groups": 2,
                    "queued_groups": 2,
                    "unqueued_actionable_groups": 0,
                    "queue_coverage": 1.0,
                    "action_batch_count": 1,
                    "by_key_type": [["barcode", 2]],
                    "by_review_confidence": [["high_review_confidence", 2]],
                    "by_merge_blocker": [
                        ["multi_store_variant_or_retailer_review", 2]
                    ],
                    "by_manual_review_required_reason": [
                        ["manual_keep_drop_confirmation_required", 2]
                    ],
                    "excluded_review_confidence": [["variant_caution", 1]],
                    "ichiban_reissue_review_groups": 46,
                    "ichiban_reissue_review_rows": 92,
                    "ichiban_probable_reissue_review_groups": 20,
                    "ichiban_probable_reissue_sample_rows": 8,
                    "ichiban_reissue_work_order_rows": 20,
                    "ichiban_reissue_decision_template_rows": 20,
                    "ichiban_reissue_manual_confirmed_rows": 0,
                    "ichiban_reissue_protected_groups": 0,
                    "ichiban_reissue_protected_rows": 0,
                    "completion_readiness_status": "ichiban_reissue_review_required",
                    "auto_merge_ready_groups": 0,
                    "auto_delete_ready_groups": 0,
                    "explicit_keep_drop_required_groups": 2,
                },
                "completion_readiness": {
                    "status": "ichiban_reissue_review_required",
                    "blocked_reasons": [
                        "explicit_manual_keep_drop_confirmation_required"
                    ],
                    "next_safe_phase": "verify_ichiban_campaign_pages_before_dedupe",
                }
            },
            "catalog_deduplication_fast_review_public.json": {
                "summary": {
                    "fast_review_groups": 2,
                    "same_barcode_groups": 2,
                    "same_source_url_groups": 1,
                    "same_image_url_groups": 1,
                    "manual_confirmed_true": 0,
                    "variant_warning_groups": 2,
                },
                "breakdowns": {
                    "by_fast_review_lane": [
                        {"fast_review_lane": "same_barcode_and_source_url", "groups": 1},
                        {"fast_review_lane": "same_barcode_and_image_url", "groups": 1},
                    ]
                },
            },
            "catalog_deduplication_template_import_dry_run_public.json": {
                "summary": {
                    "template_items": 2,
                    "manual_confirmed_rows": 0,
                    "ready_decision_rows": 0,
                    "blocked_rows": 2,
                    "skip_reason_counts": [["manual_confirmed_false", 2]],
                    "write": False,
                }
            },
            "ichiban_kuji_metadata_review_batches_public.json": {
                "summary": {"catalog_item_rows": 0}
            },
            "ichiban_kuji_history_public.json": {
                "summary": {
                    "campaign_rows": 14,
                    "catalog_kuji_item_rows": 20,
                    "campaigns_with_catalog_items": 11,
                    "campaigns_without_catalog_items": 3,
                    "missing_release_date_rows": 2,
                    "missing_release_date_campaign_groups": 1,
                    "missing_official_price_jpy_rows": 7,
                    "missing_official_price_jpy_campaign_groups": 2,
                    "official_price_jpy_review_queue_campaigns": 2,
                    "avg_missing_price_rows_per_campaign_group": 3.5,
                    "metadata_resolution_readiness_status": "manual_campaign_metadata_review_required",
                    "metadata_manual_review_campaigns": 3,
                    "metadata_auto_apply_ready_campaigns": 0,
                    "metadata_review_queue_covers_all_price_campaign_groups": True,
                    "campaign_metadata_review_queue_rows": 3,
                }
            },
            "ichiban_kuji_historical_roadmap_public.json": {
                "summary": {
                    "completion_readiness": {
                        "status": "manual_review_required",
                        "manual_metadata_campaigns": 3,
                        "manual_reissue_review_groups": 2,
                        "zero_price_policy_ready": True,
                        "numbered_variant_policy_ready": True,
                        "next_safe_phase": "confirm_ichiban_campaign_metadata",
                    }
                }
            },
            "ichiban_kuji_metadata_action_queue_public.json": {
                "summary": {
                    "actionable_campaigns": 1,
                    "queued_action_campaigns": 1,
                    "unqueued_action_campaigns": 0,
                    "campaign_queue_coverage": 1.0,
                    "queued_catalog_item_rows": 8,
                    "action_batch_count": 1,
                    "field_patch_template_count": 1,
                    "field_patch_template_counts": [["release_date", 1]],
                    "next_campaign_patch_review_batch_rows": 2,
                    "next_campaign_patch_review_batch_template_rows": 2,
                    "next_campaign_patch_review_batch_primary_review_url_rows": 2,
                    "next_campaign_patch_review_batch_field_counts": [
                        ["official_price_jpy", 1],
                        ["release_date", 1],
                    ],
                    "primary_review_url_rows": 1,
                    "queued_primary_review_url_rows": 1,
                    "first_primary_review_url": "https://1kuji.example/campaign",
                    "work_order_steps": 1,
                    "work_order_lanes": ["confirm_release_dates"],
                }
            },
            "ichiban_kuji_metadata_fast_review_public.json": {
                "summary": {
                    "fast_review_campaigns": 1,
                    "held_for_later_campaigns": 0,
                    "fast_review_template_rows": 1,
                    "manual_confirmed_true": 0,
                }
            },
            "ichiban_kuji_prize_name_image_review_public.json": {
                "summary": {
                    "kuji_rows": 20,
                    "review_rows": 2,
                    "name_structure_review_rows": 1,
                    "image_identity_review_rows": 1,
                    "same_campaign_prize_rank_name_duplicate_rows": 0,
                    "same_campaign_image_reused_different_name_rows": 1,
                    "multi_item_prize_rank_groups": 1,
                    "multi_item_prize_rank_catalog_rows": 3,
                    "review_reason_counts": [["prize_rank_not_visible_in_prize_item_name", 1]],
                    "auto_apply_enabled": False,
                }
            },
            "ichiban_kuji_prize_name_image_patch_candidates_public.json": {
                "summary": {
                    "review_rows": 2,
                    "candidate_rows": 1,
                    "exact_image_match_rows": 1,
                    "strong_name_match_rows": 0,
                    "blocked_rows": 1,
                    "fetch_failure_urls": 0,
                    "auto_apply_enabled": False,
                }
            },
            "ichiban_kuji_prize_policy_audit_public.json": {
                "summary": {
                    "kuji_rows": 20,
                    "last_one_rows": 2,
                    "last_one_nonzero_price_rows": 0,
                    "last_one_missing_price_rows": 0,
                    "double_chance_rows": 1,
                    "double_chance_nonzero_price_rows": 0,
                    "double_chance_missing_price_rows": 0,
                    "zero_price_exception_policy_pass": True,
                    "numbered_variant_application_write": True,
                    "numbered_variant_source_prizes_considered": 4,
                    "numbered_variant_applied_prizes": 4,
                    "numbered_variant_updated_existing_rows": 4,
                    "numbered_variant_created_rows": 12,
                    "numbered_variant_application_skipped_rows": 0,
                    "multi_item_prize_label_groups": 4,
                    "multi_item_prize_label_review_batch_count": 1,
                    "multi_item_prize_label_review_catalog_item_rows": 9,
                    "repeated_name_different_source_groups": 2,
                    "repeated_name_different_source_review_batch_count": 1,
                    "repeated_name_different_source_review_catalog_item_rows": 5,
                    "prize_policy_review_batch_count": 2,
                }
            },
            "ichiban_kuji_prize_policy_issue_queue_public.json": {
                "summary": {
                    "issue_rows": 2,
                    "open_issue_rows": 4,
                    "manual_review_rows": 4,
                    "manual_confirmed_rows": 0,
                    "auto_apply_ready_rows": 0,
                    "protected_unnumbered_multi_item_prize_groups": 1,
                    "protected_unnumbered_multi_item_prize_rows": 2,
                    "probable_reissue_work_order_rows": 2,
                    "campaign_first_review_plan_rows": 1,
                    "campaign_first_review_item_work_order_rows": 2,
                    "campaign_first_review_plans_with_evidence_urls": 1,
                    "campaign_first_review_first_evidence_url": "https://1kuji.example/reissue",
                    "completion_readiness_status": "ichiban_reissue_review_required",
                    "auto_merge_enabled": False,
                    "auto_delete_enabled": False,
                },
                "completion_readiness": {
                    "status": "ichiban_reissue_review_required",
                    "zero_price_policy_ready": True,
                    "numbered_variant_policy_ready": True,
                    "reissue_review_ready": False,
                },
            },
            "animation_category_review_batches_public.json": {
                "summary": {"source_rows": 0}
            },
            "animation_goods_categories_public.json": {
                "summary": {
                    "unknown_category_count": 3,
                    "unknown_category_rows": 39,
                    "category_readiness_status": "normalization_review_required",
                    "normalization_review_queue_count": 4,
                    "normalization_review_queue_rows": 36,
                    "app_folder_color_count": 188,
                    "app_folder_icon_option_count": 211,
                    "app_folder_palette_sorted_by_family": True,
                    "app_animation_visuals_covered": True,
                }
            },
            "animation_category_coverage_audit_public.json": {
                "summary": {
                    "status": "pass",
                    "failed_check_count": 0,
                    "missing_visual_token_categories": 0,
                }
            },
            "animation_category_action_queue_public.json": {
                "summary": {
                    "actionable_categories": 2,
                    "queued_categories": 2,
                    "queued_catalog_rows": 12,
                    "action_batch_count": 1,
                    "normalization_review_categories": 4,
                    "normalization_review_rows": 36,
                    "normalization_review_target_categories": [["문구", 3]],
                    "target_visual_token_rows": 4,
                    "target_visual_token_catalog_rows": 36,
                    "target_visual_palette_ordered": True,
                    "split_review_categories": 2,
                    "direct_mapping_categories": 0,
                    "by_suggested_family": [["acrylic", 1], ["keyring", 1]],
                    "work_order_steps": 1,
                    "work_order_lanes": ["name_level_split_review"],
                    "split_first_blocked_categories": ["Acrylic"],
                }
            },
            "animation_category_split_review_public.json": {
                "summary": {
                    "split_review_categories": 2,
                    "candidate_split_rules": 5,
                    "matched_catalog_rows": 30,
                    "unmatched_catalog_rows": 7,
                }
            },
            "animation_category_unmatched_keyword_review_public.json": {
                "summary": {
                    "token_candidate_count": 4,
                }
            },
            "catalog_confirmed_import_readiness_public.json": {
                "summary": {
                    "workflow_count": 2,
                    "template_items": 3,
                    "public_action_queue_rows": 6,
                    "public_action_queue_batches": 2,
                    "ready_or_pending_import_rows": 0,
                    "blocked_confirmed_rows": 0,
                    "work_order_lanes": 2,
                    "top_work_order_row_count": 4,
                    "top_work_order_lane": "confirm_template_rows",
                    "top_work_order_workflow": "source_discovery",
                    "by_status": [["template_ready_for_manual_confirmation", 1]],
                },
                "work_order": [
                    {
                        "workflow": "source_discovery",
                        "public_workstream": "source_discovery_source_urls",
                        "lane": "confirm_template_rows",
                        "row_count": 4,
                        "batch_count": 0,
                        "next_step": "review_template_rows_then_copy_exact_confirmed_rows",
                        "template_file_exists": True,
                        "manual_confirmation_required": True,
                        "auto_apply_enabled": False,
                    }
                ],
            },
        }

        with patch.object(plan, "_load", side_effect=lambda name: payloads.get(name, {})):
            report = plan.build_plan()

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        first = report["actions"][0]
        self.assertEqual(first["workstream"], "confirmed_import_readiness")
        self.assertEqual(first["status"], "needs_manual_confirmation")
        self.assertEqual(first["rows"], 9)
        self.assertIn("manual_confirmed=true", first["blocker"])
        self.assertEqual(first["evidence"]["public_action_queue_rows"], 6)
        self.assertEqual(first["evidence"]["public_action_queue_batches"], 2)
        self.assertEqual(first["evidence"]["manual_confirmed_ready_rows"], 0)
        self.assertEqual(first["evidence"]["manual_confirmation_backlog_rows"], 9)
        self.assertEqual(first["evidence"]["workflow_count"], 2)
        self.assertEqual(first["evidence"]["work_order_lanes"], 2)
        self.assertEqual(first["evidence"]["top_work_order_row_count"], 4)
        self.assertEqual(first["evidence"]["top_work_order_lane"], "confirm_template_rows")
        self.assertEqual(first["evidence"]["top_work_order_workflow"], "source_discovery")
        self.assertEqual(
            first["evidence"]["by_status"],
            [["template_ready_for_manual_confirmation", 1]],
        )
        self.assertEqual(
            first["evidence"]["top_work_orders"][0]["public_workstream"],
            "source_discovery_source_urls",
        )
        self.assertTrue(first["evidence"]["top_work_orders"][0]["template_file_exists"])
        self.assertFalse(first["evidence"]["top_work_orders"][0]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["confirmed_import_template_rows"], 3)
        self.assertEqual(report["summary"]["confirmed_import_action_queue_rows"], 6)
        self.assertEqual(report["summary"]["confirmed_import_action_queue_batches"], 2)
        self.assertEqual(report["summary"]["confirmed_import_pending_rows"], 0)
        self.assertEqual(report["summary"]["confirmed_import_manual_confirmed_ready_rows"], 0)
        self.assertEqual(report["summary"]["confirmed_import_manual_confirmation_backlog_rows"], 9)
        self.assertEqual(report["summary"]["confirmed_import_blocked_confirmed_rows"], 0)
        self.assertEqual(report["summary"]["confirmed_import_workflow_count"], 2)
        self.assertEqual(report["summary"]["confirmed_import_work_order_lanes"], 2)
        self.assertEqual(report["summary"]["confirmed_import_top_work_order_row_count"], 4)
        self.assertEqual(
            report["summary"]["confirmed_import_top_work_order_lane"],
            "confirm_template_rows",
        )
        self.assertEqual(
            report["summary"]["confirmed_import_top_work_order_workflow"],
            "source_discovery",
        )
        requested = next(
            action
            for action in report["actions"]
            if action["workstream"] == "requested_focus_review_batches"
        )
        self.assertEqual(requested["evidence"]["topic_count"], 2)
        self.assertEqual(requested["evidence"]["total_matched_catalog_rows"], 9)
        self.assertEqual(requested["evidence"]["total_requested_labels"], 4)
        self.assertEqual(requested["evidence"]["topics_with_open_work"], 2)
        self.assertEqual(requested["evidence"]["open_rows"], 7)
        self.assertEqual(requested["evidence"]["missing_image_rows"], 1)
        self.assertEqual(requested["evidence"]["missing_source_url_rows"], 1)
        self.assertEqual(requested["evidence"]["missing_release_date_rows"], 2)
        self.assertEqual(requested["evidence"]["missing_official_price_jpy_rows"], 3)
        self.assertEqual(requested["evidence"]["requested_needs_review"], 1)
        self.assertEqual(requested["evidence"]["topic_with_batches_count"], 2)
        self.assertEqual(requested["evidence"]["by_topic"][0], ["ichiban_kuji", 3])
        self.assertEqual(requested["evidence"]["by_missing_field"][0], ["barcode", 3])
        self.assertEqual(report["summary"]["requested_focus_topic_count"], 2)
        self.assertEqual(report["summary"]["requested_focus_open_rows"], 7)
        self.assertEqual(report["summary"]["requested_focus_topics_with_open_work"], 2)
        self.assertEqual(report["summary"]["requested_focus_missing_image_rows"], 1)
        self.assertEqual(report["summary"]["requested_focus_missing_source_url_rows"], 1)
        self.assertEqual(report["summary"]["requested_focus_missing_release_date_rows"], 2)
        self.assertEqual(report["summary"]["requested_focus_missing_official_price_jpy_rows"], 3)
        self.assertEqual(report["summary"]["requested_focus_actionable_template_rows"], 2)
        self.assertEqual(report["summary"]["requested_focus_barcode_template_rows"], 3)
        self.assertEqual(report["summary"]["requested_focus_queued_action_rows"], 2)
        self.assertEqual(report["summary"]["requested_focus_unqueued_actionable_rows"], 0)
        self.assertEqual(report["summary"]["requested_focus_queue_coverage"], 1.0)
        self.assertEqual(report["summary"]["requested_focus_non_barcode_template_rows"], 2)
        self.assertEqual(report["summary"]["requested_focus_total_review_template_rows"], 5)
        self.assertEqual(report["summary"]["requested_focus_non_barcode_template_share"], 0.4)
        self.assertEqual(report["summary"]["requested_focus_review_url_rows"], 2)
        self.assertEqual(requested["evidence"]["actionable_non_barcode_template_rows"], 2)
        metadata_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "metadata_action_queue"
        )
        self.assertEqual(metadata_action["evidence"]["missing_cells_by_field"][0], ["release_date", 6])
        self.assertEqual(metadata_action["evidence"]["top_action_groups"][0]["source_store"], "Store A")
        self.assertEqual(requested["evidence"]["barcode_template_rows"], 3)
        action_queue = next(
            action
            for action in report["actions"]
            if action["workstream"] == "requested_focus_action_queue"
        )
        self.assertEqual(action_queue["priority"], 11)
        self.assertEqual(action_queue["rows"], 2)
        self.assertEqual(action_queue["evidence"]["unqueued_actionable_rows"], 0)
        self.assertEqual(action_queue["evidence"]["queue_coverage"], 1.0)
        self.assertEqual(action_queue["evidence"]["barcode_template_rows_excluded"], 3)
        self.assertEqual(action_queue["evidence"]["non_barcode_template_rows"], 2)
        self.assertEqual(action_queue["evidence"]["total_review_template_rows"], 5)
        self.assertEqual(action_queue["evidence"]["non_barcode_template_share"], 0.4)
        self.assertEqual(action_queue["evidence"]["skipped_non_template_rows"], 0)
        self.assertEqual(
            action_queue["evidence"]["blocked_reason_counts"][0],
            ["missing_exact_source_url_for_requested_focus", 1],
        )
        self.assertEqual(
            action_queue["evidence"]["blocked_until_counts"][0],
            ["exact_product_source_url_confirmed", 1],
        )
        self.assertEqual(action_queue["evidence"]["review_url_rows"], 2)
        self.assertEqual(
            action_queue["evidence"]["primary_review_url_kind_counts"],
            [["existing_source_url", 1], ["domain_limited_web_search", 1]],
        )
        self.assertEqual(
            action_queue["evidence"]["barcode_template_rows_excluded_blocked_reason"],
            "barcode_research_deferred",
        )
        self.assertEqual(
            action_queue["evidence"]["barcode_template_rows_excluded_blocked_until"],
            "source_image_date_price_queue_reviewed",
        )
        danganronpa = next(
            action
            for action in report["actions"]
            if action["workstream"] == "danganronpa_missing_media"
        )
        self.assertEqual(danganronpa["priority"], 12)
        self.assertEqual(danganronpa["rows"], 4)
        self.assertEqual(danganronpa["evidence"]["missing_image_url_rows"], 4)
        self.assertEqual(danganronpa["evidence"]["missing_source_url_rows"], 4)
        self.assertEqual(danganronpa["evidence"]["review_batch_count"], 2)
        self.assertEqual(danganronpa["evidence"]["official_search_rows"], 2)
        self.assertEqual(danganronpa["evidence"]["licensed_retailer_review_rows"], 1)
        self.assertEqual(danganronpa["evidence"]["official_prize_search_rows"], 1)
        self.assertEqual(danganronpa["evidence"]["confirmed_patch_template_rows"], 4)
        self.assertEqual(danganronpa["evidence"]["confirmed_patch_template_pending_rows"], 4)
        self.assertEqual(danganronpa["evidence"]["template_dry_run_rows"], 4)
        self.assertEqual(danganronpa["evidence"]["template_dry_run_ready_rows"], 0)
        self.assertEqual(danganronpa["evidence"]["template_dry_run_skipped_rows"], 4)
        self.assertEqual(danganronpa["evidence"]["template_dry_run_blocked_rows"], 0)
        self.assertEqual(danganronpa["evidence"]["manual_confirmed_source_rows"], 0)
        self.assertEqual(danganronpa["evidence"]["manual_confirmed_image_rows"], 0)
        self.assertEqual(
            danganronpa["evidence"]["template_dry_run_by_status"],
            [["skipped_pending_manual_confirmation", 4]],
        )
        self.assertEqual(danganronpa["evidence"]["by_source_store"][0], ["Movic", 2])
        self.assertEqual(report["summary"]["danganronpa_missing_media_rows"], 4)
        self.assertEqual(report["summary"]["danganronpa_missing_image_url_rows"], 4)
        self.assertEqual(report["summary"]["danganronpa_missing_source_url_rows"], 4)
        self.assertEqual(report["summary"]["danganronpa_missing_media_review_batch_count"], 2)
        self.assertEqual(report["summary"]["danganronpa_official_search_rows"], 2)
        self.assertEqual(report["summary"]["danganronpa_licensed_retailer_review_rows"], 1)
        self.assertEqual(report["summary"]["danganronpa_official_prize_search_rows"], 1)
        self.assertEqual(report["summary"]["danganronpa_confirmed_patch_template_rows"], 4)
        self.assertEqual(
            report["summary"]["danganronpa_confirmed_patch_template_pending_rows"],
            4,
        )
        self.assertEqual(report["summary"]["danganronpa_patch_template_ready_rows"], 0)
        self.assertEqual(report["summary"]["danganronpa_patch_template_skipped_rows"], 4)
        self.assertEqual(
            report["summary"]["danganronpa_patch_template_manual_confirmed_source_rows"],
            0,
        )
        self.assertEqual(
            report["summary"]["danganronpa_patch_template_manual_confirmed_image_rows"],
            0,
        )
        source_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "source_discovery_action_queue"
        )
        self.assertEqual(source_action["priority"], 21)
        self.assertEqual(source_action["rows"], 4)
        self.assertEqual(source_action["evidence"]["actionable_source_rows"], 8)
        self.assertEqual(source_action["evidence"]["queued_source_rows"], 4)
        self.assertEqual(source_action["evidence"]["source_discovery_template_rows"], 4)
        self.assertEqual(source_action["evidence"]["source_discovery_template_batch_count"], 1)
        self.assertEqual(source_action["evidence"]["source_patch_template_count"], 4)
        self.assertEqual(source_action["evidence"]["catalog_field_import_template_count"], 4)
        self.assertEqual(source_action["evidence"]["primary_review_url_rows"], 4)
        self.assertEqual(
            source_action["evidence"]["primary_review_url_kind_counts"],
            [["official_search_url", 4]],
        )
        self.assertEqual(
            source_action["evidence"]["by_review_state"],
            [["official_search_review_required", 3], ["licensed_retailer_review_required", 1]],
        )
        self.assertEqual(source_action["evidence"]["by_source_store"], [["Animate", 3], ["AmiAmi", 1]])
        self.assertEqual(
            source_action["evidence"]["first_primary_review_url"],
            "https://animate.example/search?q=source",
        )
        self.assertEqual(source_action["evidence"]["first_primary_review_url_kind"], "official_search_url")
        self.assertEqual(source_action["evidence"]["manual_research_backlog_rows"], 2)
        self.assertEqual(
            source_action["evidence"]["manual_research_backlog_by_source_store"],
            [["Idol official", 2]],
        )
        self.assertEqual(report["summary"]["source_discovery_action_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_actionable_rows"], 8)
        self.assertEqual(report["summary"]["source_discovery_template_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_template_batch_count"], 1)
        self.assertEqual(report["summary"]["source_discovery_unqueued_actionable_rows"], 4)
        self.assertEqual(report["summary"]["source_discovery_manual_research_backlog_rows"], 2)
        source_focus = next(
            action
            for action in report["actions"]
            if action["workstream"] == "source_discovery_focus_template"
        )
        self.assertEqual(source_focus["priority"], 20)
        self.assertEqual(source_focus["rows"], 8)
        self.assertEqual(source_focus["next_step"], "work_source_focus_template_work_order_top_to_bottom")
        self.assertEqual(source_focus["evidence"]["work_order_pack_count"], 2)
        self.assertEqual(source_focus["evidence"]["next_focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(source_focus["evidence"]["next_source_store"], "Animate")
        self.assertEqual(source_focus["evidence"]["next_target_category"], "Acrylic stand")
        self.assertEqual(source_focus["evidence"]["next_focus_pack_rows"], 4)
        self.assertEqual(source_focus["evidence"]["current_focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(source_focus["evidence"]["pack_queue_preview_count"], 2)
        self.assertEqual(source_focus["evidence"]["next_pack_after_current"], "source-discovery-focus-002")
        self.assertEqual(
            [row["focus_pack_id"] for row in source_focus["evidence"]["pack_queue_preview"]],
            ["source-discovery-focus-001", "source-discovery-focus-002"],
        )
        self.assertEqual(source_focus["evidence"]["dry_run_skipped_rows"], 8)
        self.assertEqual(report["summary"]["source_focus_template_rows"], 8)
        self.assertEqual(report["summary"]["source_focus_template_work_order_pack_count"], 2)
        self.assertEqual(report["summary"]["source_focus_template_next_pack_rows"], 4)
        fetch_audit = next(
            action
            for action in report["actions"]
            if action["workstream"] == "source_discovery_next_focus_pack_fetch_audit"
        )
        self.assertEqual(fetch_audit["priority"], 20)
        self.assertEqual(fetch_audit["status"], "fallback_required")
        self.assertEqual(fetch_audit["rows"], 4)
        self.assertIn("not fetchable", fetch_audit["blocker"])
        self.assertEqual(fetch_audit["evidence"]["focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(fetch_audit["evidence"]["official_search_unavailable_rows"], 4)
        fallback_queue = next(
            action
            for action in report["actions"]
            if action["workstream"] == "source_discovery_next_focus_fallback_queue"
        )
        self.assertEqual(fallback_queue["priority"], 20)
        self.assertEqual(fallback_queue["rows"], 4)
        self.assertEqual(fallback_queue["evidence"]["by_source_store"], [["Animate", 4]])
        self.assertEqual(fallback_queue["evidence"]["source_confirmation_ready_rows"], 3)
        self.assertEqual(fallback_queue["evidence"]["exact_url_review_queue_rows"], 3)
        self.assertEqual(fallback_queue["evidence"]["identity_backfill_queue_rows"], 1)
        self.assertEqual(
            fallback_queue["evidence"]["identity_candidate_review_queue_rows"], 1
        )
        self.assertEqual(
            fallback_queue["evidence"]["identity_candidate_review_candidate_rows"], 2
        )
        self.assertEqual(
            fallback_queue["evidence"]["fallback_import_dry_run_updated_rows"], 0
        )
        self.assertEqual(
            fallback_queue["evidence"]["fallback_import_dry_run_skipped_rows"], 4
        )
        self.assertEqual(
            fallback_queue["evidence"]["fallback_import_dry_run_skip_reason_counts"],
            [["manual_confirmed_false", 4]],
        )
        self.assertFalse(fallback_queue["evidence"]["fallback_import_dry_run_write"])
        self.assertEqual(
            fallback_queue["evidence"]["metadata_backfill_required_rows"], 1
        )
        self.assertEqual(
            fallback_queue["evidence"]["variant_disambiguation_required_rows"], 1
        )
        self.assertEqual(
            fallback_queue["evidence"]["by_identity_review_status"][0][0],
            "exact_page_match_review_ready",
        )
        self.assertEqual(fallback_queue["evidence"]["work_order_steps"], 3)
        self.assertEqual(
            fallback_queue["evidence"]["work_order_lanes"],
            [
                "domain_limited_exact_title_search",
                "legacy_mobile_store_search",
                "evidence_fill_and_dry_run",
            ],
        )
        self.assertEqual(report["summary"]["source_next_focus_fallback_rows"], 4)
        exact_url_queue = next(
            action
            for action in report["actions"]
            if action["workstream"] == "source_discovery_next_focus_exact_url_review_queue"
        )
        self.assertEqual(exact_url_queue["priority"], 20)
        self.assertEqual(exact_url_queue["rows"], 3)
        self.assertEqual(exact_url_queue["evidence"]["blocked_identity_rows"], 1)
        self.assertEqual(exact_url_queue["evidence"]["primary_review_url_rows"], 3)
        self.assertEqual(
            exact_url_queue["evidence"]["first_primary_review_url"],
            "https://google.example/search?q=exact",
        )
        self.assertFalse(exact_url_queue["evidence"]["auto_apply_enabled"])
        self.assertEqual(
            report["summary"]["source_next_focus_source_confirmation_ready_rows"], 3
        )
        self.assertEqual(report["summary"]["source_next_focus_exact_url_review_rows"], 3)
        self.assertEqual(
            report["summary"]["source_next_focus_exact_url_manual_confirmed_rows"], 0
        )
        self.assertEqual(report["summary"]["source_next_focus_identity_backfill_rows"], 1)
        self.assertEqual(
            report["summary"]["source_next_focus_identity_candidate_review_rows"], 1
        )
        self.assertEqual(
            report["summary"]["source_next_focus_identity_candidate_review_candidate_rows"],
            2,
        )
        self.assertEqual(
            report["summary"]["source_next_focus_fallback_import_dry_run_updated_rows"],
            0,
        )
        self.assertEqual(
            report["summary"]["source_next_focus_fallback_import_dry_run_skipped_rows"],
            4,
        )
        source_starter = next(
            action
            for action in report["actions"]
            if action["workstream"] == "source_discovery_starter_queue"
        )
        self.assertEqual(source_starter["priority"], 20)
        self.assertEqual(source_starter["rows"], 12)
        self.assertEqual(source_starter["next_step"], "find_exact_official_product_source_url")
        self.assertTrue(source_starter["evidence"]["coverage_matches_missing_source_url_rows"])
        self.assertEqual(source_starter["evidence"]["starter_queue_groups"], 3)
        self.assertEqual(source_starter["evidence"]["top_groups"][0]["group_key"], "Animate|Acrylic stand")
        self.assertEqual(
            source_starter["evidence"]["top_groups"][0]["first_search_url"],
            "https://animate.example/search?q=acrylic",
        )
        self.assertEqual(
            source_starter["evidence"]["fallback_groups"][0]["first_fallback_web_search_url"],
            "https://www.google.com/search?q=fallback",
        )
        self.assertEqual(report["summary"]["source_discovery_starter_queue_rows"], 12)
        self.assertEqual(report["summary"]["source_discovery_starter_queue_groups"], 3)
        ensky = next(
            action
            for action in report["actions"]
            if action["workstream"] == "ensky_cache_candidate_action_queue"
        )
        self.assertEqual(ensky["priority"], 23)
        self.assertEqual(ensky["rows"], 5)
        self.assertEqual(ensky["evidence"]["candidate_source_url_ready_rows"], 5)
        self.assertEqual(ensky["evidence"]["candidate_image_url_ready_rows"], 4)
        self.assertEqual(ensky["evidence"]["safe_exact_top_candidate_rows"], 0)
        self.assertEqual(ensky["evidence"]["can_import_now_rows"], 0)
        self.assertEqual(ensky["evidence"]["blocked_manual_review_rows"], 5)
        self.assertEqual(ensky["evidence"]["import_readiness"]["identity_warning_rows"], 5)
        image = next(action for action in report["actions"] if action["workstream"] == "image_url_attachment")
        self.assertEqual(image["status"], "blocked")
        self.assertEqual(image["evidence"]["known_image_asset_status"], "pass")
        self.assertEqual(
            image["evidence"]["download_readiness_status"],
            "known_image_assets_complete",
        )
        self.assertEqual(image["evidence"]["image_url_rows"], 90)
        self.assertEqual(image["evidence"]["local_image_path_rows"], 90)
        self.assertEqual(image["evidence"]["image_url_without_local_path_rows"], 0)
        self.assertEqual(image["evidence"]["missing_local_image_files"], 0)
        self.assertEqual(image["evidence"]["missing_web_public_asset_files"], 0)
        self.assertEqual(image["evidence"]["known_image_download_blocker_rows"], 0)
        self.assertEqual(image["evidence"]["auto_download_ready_rows"], 0)
        self.assertEqual(
            image["evidence"]["rows_still_requiring_image_url_evidence"], 10
        )
        self.assertEqual(image["evidence"]["provider_candidate_items"], 7)
        self.assertEqual(image["evidence"]["manual_or_blocked_items"], 3)
        image_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "image_attachment_action_queue"
        )
        self.assertEqual(image_action["priority"], 31)
        self.assertEqual(image_action["rows"], 2)
        self.assertEqual(image_action["evidence"]["actionable_image_rows"], 2)
        self.assertEqual(image_action["evidence"]["source_url_update_required_rows"], 2)
        self.assertEqual(image_action["evidence"]["source_url_update_template_rows"], 2)
        self.assertEqual(image_action["evidence"]["source_url_update_template_batch_count"], 1)
        self.assertEqual(image_action["evidence"]["image_url_ready_rows"], 0)
        self.assertEqual(
            image_action["evidence"]["download_ready_after_manual_image_url_rows"], 2
        )
        self.assertEqual(image_action["evidence"]["suggested_local_image_path_rows"], 2)
        self.assertEqual(
            image_action["evidence"]["local_image_download_instruction_ready_rows"], 2
        )
        self.assertEqual(image_action["evidence"]["image_attachment_template_rows"], 2)
        self.assertEqual(
            image_action["evidence"]["image_attachment_template_confirmed_rows"], 0
        )
        self.assertEqual(
            image_action["evidence"]["image_attachment_template_dry_run_updated_rows"], 0
        )
        self.assertEqual(
            image_action["evidence"]["image_attachment_template_dry_run_skipped_rows"], 2
        )
        self.assertEqual(
            image_action["evidence"]["source_discovery_focus_template_rows"], 8
        )
        self.assertEqual(
            image_action["evidence"]["source_discovery_focus_template_confirmed_rows"], 0
        )
        self.assertEqual(image_action["evidence"]["workstream_count"], 1)
        self.assertEqual(image_action["evidence"]["source_url_update_workstream_count"], 1)
        self.assertEqual(
            image_action["evidence"]["top_image_attachment_workstreams"][0]["next_batch_id"],
            "image-attachment-action-001",
        )
        self.assertEqual(report["summary"]["image_action_source_url_update_required_rows"], 2)
        self.assertEqual(report["summary"]["image_candidate_provider_items"], 7)
        self.assertEqual(report["summary"]["image_candidate_manual_or_blocked_items"], 3)
        self.assertEqual(report["summary"]["image_action_source_url_update_template_rows"], 2)
        self.assertEqual(report["summary"]["image_action_source_url_update_template_batch_count"], 1)
        self.assertEqual(report["summary"]["image_action_image_url_ready_rows"], 0)
        self.assertEqual(report["summary"]["image_action_workstream_count"], 1)
        self.assertEqual(report["summary"]["image_known_asset_status"], "pass")
        self.assertEqual(
            report["summary"]["image_download_readiness_status"],
            "known_image_assets_complete",
        )
        self.assertEqual(report["summary"]["image_url_without_local_path_rows"], 0)
        self.assertEqual(report["summary"]["image_missing_local_image_files"], 0)
        self.assertEqual(report["summary"]["image_rows_still_requiring_url_evidence"], 10)
        self.assertEqual(report["summary"]["image_auto_download_ready_rows"], 0)
        self.assertEqual(report["summary"]["image_attachment_template_rows"], 2)
        self.assertEqual(report["summary"]["image_attachment_template_confirmed_rows"], 0)
        self.assertEqual(
            report["summary"]["image_attachment_template_dry_run_skipped_rows"], 2
        )
        metadata_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "metadata_action_queue"
        )
        self.assertEqual(metadata_action["rows"], 8)
        self.assertEqual(metadata_action["evidence"]["actionable_missing_cells"], 8)
        dedupe_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "deduplication_action_queue"
        )
        self.assertEqual(dedupe_action["rows"], 2)
        self.assertEqual(dedupe_action["evidence"]["actionable_groups"], 2)
        self.assertEqual(dedupe_action["evidence"]["unqueued_actionable_groups"], 0)
        self.assertEqual(dedupe_action["evidence"]["queue_coverage"], 1.0)
        self.assertEqual(dedupe_action["evidence"]["by_key_type"], [["barcode", 2]])
        self.assertEqual(
            dedupe_action["evidence"]["by_manual_review_required_reason"][0][0],
            "manual_keep_drop_confirmation_required",
        )
        self.assertEqual(
            dedupe_action["evidence"]["completion_readiness_status"],
            "ichiban_reissue_review_required",
        )
        self.assertEqual(
            dedupe_action["evidence"]["completion_readiness"]["next_safe_phase"],
            "verify_ichiban_campaign_pages_before_dedupe",
        )
        self.assertEqual(dedupe_action["evidence"]["auto_merge_ready_groups"], 0)
        self.assertEqual(dedupe_action["evidence"]["auto_delete_ready_groups"], 0)
        self.assertEqual(
            dedupe_action["evidence"]["explicit_keep_drop_required_groups"], 2
        )
        self.assertEqual(dedupe_action["evidence"]["template_blocked_rows"], 2)
        self.assertEqual(dedupe_action["evidence"]["template_ready_decision_rows"], 0)
        self.assertFalse(dedupe_action["evidence"]["template_write_enabled"])
        self.assertEqual(
            dedupe_action["evidence"]["template_skip_reason_counts"],
            [["manual_confirmed_false", 2]],
        )
        self.assertEqual(dedupe_action["evidence"]["fast_review_groups"], 2)
        self.assertEqual(dedupe_action["evidence"]["fast_review_same_source_url_groups"], 1)
        self.assertEqual(dedupe_action["evidence"]["fast_review_manual_confirmed_true"], 0)
        self.assertEqual(dedupe_action["evidence"]["fast_review_variant_warning_groups"], 2)
        self.assertEqual(dedupe_action["evidence"]["ichiban_reissue_review_groups"], 46)
        self.assertEqual(
            dedupe_action["evidence"]["ichiban_probable_reissue_review_groups"], 20
        )
        self.assertEqual(dedupe_action["evidence"]["ichiban_reissue_protected_groups"], 0)
        self.assertEqual(
            dedupe_action["evidence"]["fast_review_lanes"][0]["fast_review_lane"],
            "same_barcode_and_source_url",
        )
        self.assertEqual(report["summary"]["dedupe_fast_review_groups"], 2)
        self.assertEqual(report["summary"]["dedupe_duplicate_groups"], 3)
        self.assertEqual(report["summary"]["dedupe_duplicate_rows"], 6)
        self.assertEqual(report["summary"]["dedupe_actionable_groups"], 2)
        self.assertEqual(report["summary"]["dedupe_queued_groups"], 2)
        self.assertEqual(report["summary"]["dedupe_auto_merge_ready_groups"], 0)
        self.assertEqual(report["summary"]["dedupe_auto_delete_ready_groups"], 0)
        self.assertEqual(report["summary"]["dedupe_template_blocked_rows"], 2)
        self.assertEqual(report["summary"]["dedupe_template_ready_decision_rows"], 0)
        self.assertEqual(report["summary"]["dedupe_fast_review_same_source_url_groups"], 1)
        self.assertEqual(report["summary"]["dedupe_ichiban_reissue_review_groups"], 46)
        self.assertEqual(
            report["summary"]["dedupe_ichiban_probable_reissue_review_groups"], 20
        )
        ichiban_reissue_dedupe_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "ichiban_kuji_reissue_dedupe_review"
        )
        self.assertEqual(ichiban_reissue_dedupe_action["rows"], 46)
        self.assertEqual(
            ichiban_reissue_dedupe_action["evidence"]["ichiban_probable_reissue_review_groups"],
            20,
        )
        self.assertEqual(
            ichiban_reissue_dedupe_action["evidence"]["ichiban_reissue_work_order_rows"],
            20,
        )
        self.assertEqual(
            ichiban_reissue_dedupe_action["evidence"]["ichiban_reissue_decision_template_rows"],
            20,
        )
        self.assertEqual(
            ichiban_reissue_dedupe_action["evidence"]["ichiban_reissue_manual_confirmed_rows"],
            0,
        )
        self.assertEqual(
            ichiban_reissue_dedupe_action["next_step"],
            "fill_ichiban_reissue_decision_template_before_dedupe",
        )
        self.assertEqual(report["summary"]["dedupe_ichiban_reissue_work_order_rows"], 20)
        self.assertEqual(report["summary"]["dedupe_ichiban_reissue_decision_template_rows"], 20)
        kuji_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "ichiban_kuji_metadata_action_queue"
        )
        self.assertEqual(kuji_action["rows"], 1)
        self.assertEqual(
            kuji_action["evidence"]["historical_readiness_status"],
            "manual_review_required",
        )
        self.assertEqual(
            kuji_action["evidence"]["historical_next_safe_phase"],
            "confirm_ichiban_campaign_metadata",
        )
        self.assertEqual(
            kuji_action["evidence"]["metadata_resolution_readiness_status"],
            "manual_campaign_metadata_review_required",
        )
        self.assertEqual(kuji_action["evidence"]["metadata_manual_review_campaigns"], 3)
        self.assertEqual(
            kuji_action["evidence"]["metadata_auto_apply_ready_campaigns"], 0
        )
        self.assertTrue(
            kuji_action["evidence"][
                "metadata_review_queue_covers_all_price_campaign_groups"
            ]
        )
        self.assertEqual(kuji_action["evidence"]["unqueued_action_campaigns"], 0)
        self.assertEqual(kuji_action["evidence"]["campaign_queue_coverage"], 1.0)
        self.assertEqual(kuji_action["evidence"]["queued_catalog_item_rows"], 8)
        self.assertEqual(kuji_action["evidence"]["missing_release_date_campaign_groups"], 1)
        self.assertEqual(kuji_action["evidence"]["missing_official_price_jpy_campaign_groups"], 2)
        self.assertEqual(kuji_action["evidence"]["official_price_jpy_review_queue_campaigns"], 2)
        self.assertEqual(
            kuji_action["evidence"]["avg_missing_price_rows_per_campaign_group"],
            3.5,
        )
        self.assertEqual(kuji_action["evidence"]["field_patch_template_count"], 1)
        self.assertEqual(kuji_action["evidence"]["next_campaign_patch_review_batch_rows"], 2)
        self.assertEqual(
            kuji_action["evidence"]["next_campaign_patch_review_batch_template_rows"],
            2,
        )
        self.assertEqual(
            kuji_action["evidence"][
                "next_campaign_patch_review_batch_primary_review_url_rows"
            ],
            2,
        )
        self.assertEqual(
            kuji_action["evidence"]["next_campaign_patch_review_batch_field_counts"],
            [["official_price_jpy", 1], ["release_date", 1]],
        )
        self.assertEqual(kuji_action["evidence"]["primary_review_url_rows"], 1)
        self.assertEqual(kuji_action["evidence"]["queued_primary_review_url_rows"], 1)
        self.assertEqual(
            kuji_action["evidence"]["first_primary_review_url"],
            "https://1kuji.example/campaign",
        )
        self.assertEqual(kuji_action["evidence"]["fast_review_campaigns"], 1)
        self.assertEqual(kuji_action["evidence"]["held_for_later_campaigns"], 0)
        self.assertEqual(kuji_action["evidence"]["fast_review_template_rows"], 1)
        self.assertEqual(kuji_action["evidence"]["fast_review_manual_confirmed_true"], 0)
        self.assertEqual(kuji_action["evidence"]["work_order_steps"], 1)
        self.assertEqual(kuji_action["evidence"]["work_order_lanes"], ["confirm_release_dates"])
        self.assertEqual(report["summary"]["ichiban_campaign_rows"], 14)
        self.assertEqual(report["summary"]["ichiban_catalog_kuji_item_rows"], 20)
        self.assertEqual(report["summary"]["ichiban_campaigns_without_catalog_items"], 3)
        self.assertEqual(report["summary"]["ichiban_campaign_metadata_review_queue_rows"], 3)
        self.assertEqual(
            report["summary"]["ichiban_historical_readiness_status"],
            "manual_review_required",
        )
        self.assertEqual(
            report["summary"]["ichiban_historical_next_safe_phase"],
            "confirm_ichiban_campaign_metadata",
        )
        self.assertEqual(report["summary"]["ichiban_metadata_manual_review_campaigns"], 3)
        self.assertEqual(report["summary"]["ichiban_metadata_auto_apply_ready_campaigns"], 0)
        self.assertEqual(report["summary"]["ichiban_metadata_actionable_campaigns"], 1)
        self.assertEqual(report["summary"]["ichiban_metadata_queued_action_campaigns"], 1)
        self.assertEqual(report["summary"]["ichiban_metadata_fast_review_campaigns"], 1)
        self.assertEqual(
            report["summary"]["ichiban_metadata_fast_review_manual_confirmed_true"], 0
        )
        self.assertEqual(report["summary"]["ichiban_missing_release_date_campaign_groups"], 1)
        self.assertEqual(report["summary"]["ichiban_missing_official_price_jpy_campaign_groups"], 2)
        kuji_name_image = next(
            action
            for action in report["actions"]
            if action["workstream"] == "ichiban_kuji_prize_name_image_review"
        )
        self.assertEqual(kuji_name_image["priority"], 45)
        self.assertEqual(kuji_name_image["rows"], 2)
        self.assertEqual(kuji_name_image["evidence"]["kuji_rows"], 20)
        self.assertEqual(kuji_name_image["evidence"]["name_structure_review_rows"], 1)
        self.assertEqual(kuji_name_image["evidence"]["image_identity_review_rows"], 1)
        self.assertEqual(kuji_name_image["evidence"]["multi_item_prize_rank_groups"], 1)
        self.assertEqual(report["summary"]["ichiban_prize_name_image_review_rows"], 2)
        self.assertEqual(report["summary"]["ichiban_prize_name_image_multi_item_groups"], 1)
        kuji_name_image_patch = next(
            action
            for action in report["actions"]
            if action["workstream"] == "ichiban_kuji_prize_name_image_patch_candidates"
        )
        self.assertEqual(kuji_name_image_patch["priority"], 46)
        self.assertEqual(kuji_name_image_patch["rows"], 1)
        self.assertEqual(kuji_name_image_patch["evidence"]["exact_image_match_rows"], 1)
        self.assertEqual(kuji_name_image_patch["evidence"]["blocked_rows"], 1)
        self.assertEqual(report["summary"]["ichiban_prize_name_image_patch_candidate_rows"], 1)
        kuji_policy = next(
            action
            for action in report["actions"]
            if action["workstream"] == "ichiban_kuji_prize_policy_audit"
        )
        self.assertEqual(kuji_policy["rows"], 6)
        self.assertTrue(kuji_policy["evidence"]["zero_price_exception_policy_pass"])
        self.assertTrue(kuji_policy["evidence"]["numbered_variant_application_write"])
        self.assertEqual(kuji_policy["evidence"]["numbered_variant_created_rows"], 12)
        self.assertEqual(kuji_policy["evidence"]["numbered_variant_application_skipped_rows"], 0)
        self.assertEqual(kuji_policy["evidence"]["multi_item_prize_label_groups"], 4)
        self.assertEqual(kuji_policy["evidence"]["multi_item_prize_label_review_batch_count"], 1)
        self.assertEqual(kuji_policy["evidence"]["repeated_name_different_source_review_batch_count"], 1)
        self.assertEqual(kuji_policy["evidence"]["issue_queue_rows"], 2)
        self.assertEqual(kuji_policy["evidence"]["open_issue_rows"], 4)
        self.assertEqual(kuji_policy["evidence"]["manual_review_rows"], 4)
        self.assertEqual(kuji_policy["evidence"]["manual_confirmed_rows"], 0)
        self.assertEqual(kuji_policy["evidence"]["auto_apply_ready_rows"], 0)
        self.assertEqual(kuji_policy["evidence"]["protected_unnumbered_multi_item_prize_groups"], 1)
        self.assertEqual(kuji_policy["evidence"]["probable_reissue_work_order_rows"], 2)
        self.assertEqual(kuji_policy["evidence"]["campaign_first_review_plan_rows"], 1)
        self.assertEqual(
            kuji_policy["evidence"]["campaign_first_review_item_work_order_rows"], 2
        )
        self.assertEqual(
            kuji_policy["evidence"]["campaign_first_review_plans_with_evidence_urls"], 1
        )
        self.assertEqual(
            kuji_policy["evidence"]["campaign_first_review_first_evidence_url"],
            "https://1kuji.example/reissue",
        )
        self.assertEqual(
            kuji_policy["evidence"]["completion_readiness_status"],
            "ichiban_reissue_review_required",
        )
        self.assertTrue(kuji_policy["evidence"]["completion_readiness"]["zero_price_policy_ready"])
        self.assertEqual(
            kuji_policy["evidence"]["historical_roadmap_completion_readiness"][
                "next_safe_phase"
            ],
            "confirm_ichiban_campaign_metadata",
        )
        self.assertFalse(kuji_policy["evidence"]["auto_merge_enabled"])
        self.assertFalse(kuji_policy["evidence"]["auto_delete_enabled"])
        self.assertEqual(kuji_policy["evidence"]["prize_policy_review_batch_count"], 2)
        self.assertEqual(report["summary"]["ichiban_multi_item_prize_label_groups"], 4)
        self.assertEqual(report["summary"]["ichiban_numbered_variant_created_rows"], 12)
        self.assertEqual(report["summary"]["ichiban_numbered_variant_application_skipped_rows"], 0)
        self.assertEqual(report["summary"]["ichiban_prize_policy_review_batch_count"], 2)
        self.assertEqual(report["summary"]["ichiban_reissue_duplicate_review_groups"], 2)
        self.assertEqual(report["summary"]["ichiban_probable_reissue_work_order_rows"], 2)
        self.assertEqual(report["summary"]["ichiban_campaign_first_review_plan_rows"], 1)
        animation_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "animation_category_action_queue"
        )
        self.assertEqual(animation_action["rows"], 36)
        self.assertEqual(
            animation_action["evidence"]["category_readiness_status"],
            "normalization_review_required",
        )
        self.assertEqual(animation_action["evidence"]["queued_categories"], 2)
        self.assertEqual(animation_action["evidence"]["unknown_category_rows"], 39)
        self.assertEqual(animation_action["evidence"]["normalization_review_categories"], 4)
        self.assertEqual(animation_action["evidence"]["normalization_review_rows"], 36)
        self.assertEqual(
            animation_action["evidence"]["normalization_review_target_categories"],
            [["문구", 3]],
        )
        self.assertEqual(animation_action["evidence"]["target_visual_token_rows"], 4)
        self.assertEqual(
            animation_action["evidence"]["target_visual_token_catalog_rows"], 36
        )
        self.assertTrue(animation_action["evidence"]["target_visual_palette_ordered"])
        self.assertEqual(animation_action["evidence"]["coverage_audit_status"], "pass")
        self.assertEqual(animation_action["evidence"]["failed_check_count"], 0)
        self.assertEqual(
            animation_action["evidence"]["missing_visual_token_categories"], 0
        )
        self.assertEqual(animation_action["evidence"]["app_folder_color_count"], 188)
        self.assertEqual(animation_action["evidence"]["app_folder_icon_option_count"], 211)
        self.assertTrue(animation_action["evidence"]["app_folder_palette_sorted_by_family"])
        self.assertEqual(animation_action["evidence"]["split_review_categories"], 2)
        self.assertEqual(animation_action["evidence"]["work_order_steps"], 1)
        self.assertEqual(animation_action["evidence"]["work_order_lanes"], ["name_level_split_review"])
        self.assertEqual(animation_action["evidence"]["split_first_blocked_categories"], ["Acrylic"])
        self.assertEqual(animation_action["evidence"]["candidate_split_rules"], 5)
        self.assertEqual(animation_action["evidence"]["matched_catalog_rows"], 30)
        self.assertEqual(animation_action["evidence"]["unmatched_keyword_candidates"], 4)
        self.assertEqual(report["summary"]["animation_unknown_category_rows"], 39)
        self.assertEqual(report["summary"]["animation_unknown_category_count"], 3)
        self.assertEqual(
            report["summary"]["animation_category_readiness_status"],
            "normalization_review_required",
        )
        self.assertEqual(report["summary"]["animation_normalization_review_categories"], 4)
        self.assertEqual(report["summary"]["animation_normalization_review_rows"], 36)
        self.assertEqual(report["summary"]["animation_coverage_audit_status"], "pass")
        self.assertEqual(report["summary"]["animation_missing_visual_token_categories"], 0)
        self.assertEqual(report["summary"]["animation_failed_visual_check_count"], 0)
        self.assertEqual(report["summary"]["animation_candidate_split_rules"], 5)
        self.assertEqual(report["summary"]["animation_split_matched_catalog_rows"], 30)
        self.assertEqual(report["summary"]["animation_unmatched_keyword_candidates"], 4)
        self.assertEqual(report["summary"]["animation_app_folder_color_count"], 188)
        self.assertEqual(report["summary"]["animation_app_folder_icon_option_count"], 211)
        self.assertTrue(report["summary"]["animation_app_folder_palette_sorted_by_family"])
        self.assertTrue(report["summary"]["animation_app_visuals_covered"])

    def test_pending_import_rows_are_prioritized(self) -> None:
        payloads = {
            "catalog_operations_public.json": {"summary": {"open_review_queues": {}}},
            "catalog_confirmed_import_readiness_public.json": {
                "summary": {
                    "template_items": 0,
                    "ready_or_pending_import_rows": 2,
                    "blocked_confirmed_rows": 0,
                }
            },
        }

        with patch.object(plan, "_load", side_effect=lambda name: payloads.get(name, {})):
            report = plan.build_plan()

        self.assertEqual(report["actions"][0]["status"], "pending_import")
        self.assertIsNone(report["actions"][0]["blocker"])
        self.assertEqual(report["summary"]["pending_import_action_count"], 1)


if __name__ == "__main__":
    unittest.main()
