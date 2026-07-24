from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_catalog_execution_plan_public as plan


class BuildCatalogExecutionPlanPublicTest(unittest.TestCase):
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
                    "manual_research_backlog_by_source_store": [["Idol official", 2]],
                    "excluded_review_state_rows": [["manual_official_research_required", 2]],
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
            "requested_focus_review_batches_public.json": {
                "summary": {
                    "review_row_count": 5,
                    "batch_count": 1,
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
                    "action_batch_count": 1,
                    "barcode_template_rows_excluded": 3,
                    "field_counts": [["source_url", 1], ["image_url", 1]],
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
                    "by_source_store": [["Movic", 2], ["Taito", 1], ["AmiAmi", 1]],
                    "by_source_kind": [
                        ["official_manufacturer", 2],
                        ["official_prize", 1],
                        ["licensed_retailer", 1],
                    ],
                }
            },
            "catalog_deduplication_review_batches_public.json": {
                "summary": {"source_groups": 1, "batch_count": 1}
            },
            "catalog_deduplication_action_queue_public.json": {
                "summary": {
                    "actionable_groups": 2,
                    "queued_groups": 2,
                    "action_batch_count": 1,
                    "by_review_confidence": [["high_review_confidence", 2]],
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
                }
            },
            "catalog_deduplication_fast_review_public.json": {
                "summary": {
                    "fast_review_groups": 2,
                    "same_barcode_groups": 2,
                    "same_source_url_groups": 1,
                    "same_image_url_groups": 1,
                },
                "breakdowns": {
                    "by_fast_review_lane": [
                        {"fast_review_lane": "same_barcode_and_source_url", "groups": 1},
                        {"fast_review_lane": "same_barcode_and_image_url", "groups": 1},
                    ]
                },
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
                    "campaign_metadata_review_queue_rows": 3,
                }
            },
            "ichiban_kuji_metadata_action_queue_public.json": {
                "summary": {
                    "actionable_campaigns": 1,
                    "queued_action_campaigns": 1,
                    "queued_catalog_item_rows": 8,
                    "action_batch_count": 1,
                    "field_patch_template_counts": [["release_date", 1]],
                    "work_order_steps": 1,
                    "work_order_lanes": ["confirm_release_dates"],
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
            "animation_category_review_batches_public.json": {
                "summary": {"source_rows": 0}
            },
            "animation_goods_categories_public.json": {
                "summary": {
                    "unknown_category_count": 3,
                    "unknown_category_rows": 39,
                    "app_folder_color_count": 188,
                    "app_folder_icon_option_count": 211,
                    "app_folder_palette_sorted_by_family": True,
                    "app_animation_visuals_covered": True,
                }
            },
            "animation_category_action_queue_public.json": {
                "summary": {
                    "actionable_categories": 2,
                    "queued_categories": 2,
                    "queued_catalog_rows": 12,
                    "action_batch_count": 1,
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
                    "template_items": 3,
                    "public_action_queue_rows": 6,
                    "public_action_queue_batches": 2,
                    "ready_or_pending_import_rows": 0,
                    "blocked_confirmed_rows": 0,
                }
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
        self.assertEqual(report["summary"]["confirmed_import_template_rows"], 3)
        self.assertEqual(report["summary"]["confirmed_import_action_queue_rows"], 6)
        self.assertEqual(report["summary"]["confirmed_import_action_queue_batches"], 2)
        self.assertEqual(report["summary"]["confirmed_import_pending_rows"], 0)
        self.assertEqual(report["summary"]["confirmed_import_manual_confirmed_ready_rows"], 0)
        self.assertEqual(report["summary"]["confirmed_import_manual_confirmation_backlog_rows"], 9)
        self.assertEqual(report["summary"]["confirmed_import_blocked_confirmed_rows"], 0)
        requested = next(
            action
            for action in report["actions"]
            if action["workstream"] == "requested_focus_review_batches"
        )
        self.assertEqual(report["summary"]["requested_focus_actionable_template_rows"], 2)
        self.assertEqual(report["summary"]["requested_focus_barcode_template_rows"], 3)
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
        self.assertEqual(action_queue["evidence"]["barcode_template_rows_excluded"], 3)
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
        self.assertEqual(danganronpa["evidence"]["by_source_store"][0], ["Movic", 2])
        self.assertEqual(report["summary"]["danganronpa_missing_media_rows"], 4)
        self.assertEqual(report["summary"]["danganronpa_missing_image_url_rows"], 4)
        self.assertEqual(report["summary"]["danganronpa_missing_source_url_rows"], 4)
        self.assertEqual(report["summary"]["danganronpa_missing_media_review_batch_count"], 2)
        self.assertEqual(report["summary"]["danganronpa_official_search_rows"], 2)
        self.assertEqual(report["summary"]["danganronpa_licensed_retailer_review_rows"], 1)
        self.assertEqual(report["summary"]["danganronpa_official_prize_search_rows"], 1)
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
        self.assertEqual(dedupe_action["evidence"]["fast_review_groups"], 2)
        self.assertEqual(dedupe_action["evidence"]["fast_review_same_source_url_groups"], 1)
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
        self.assertEqual(kuji_action["evidence"]["queued_catalog_item_rows"], 8)
        self.assertEqual(kuji_action["evidence"]["missing_release_date_campaign_groups"], 1)
        self.assertEqual(kuji_action["evidence"]["missing_official_price_jpy_campaign_groups"], 2)
        self.assertEqual(kuji_action["evidence"]["work_order_steps"], 1)
        self.assertEqual(kuji_action["evidence"]["work_order_lanes"], ["confirm_release_dates"])
        self.assertEqual(report["summary"]["ichiban_campaign_rows"], 14)
        self.assertEqual(report["summary"]["ichiban_catalog_kuji_item_rows"], 20)
        self.assertEqual(report["summary"]["ichiban_campaigns_without_catalog_items"], 3)
        self.assertEqual(report["summary"]["ichiban_campaign_metadata_review_queue_rows"], 3)
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
        self.assertEqual(kuji_policy["evidence"]["prize_policy_review_batch_count"], 2)
        self.assertEqual(report["summary"]["ichiban_multi_item_prize_label_groups"], 4)
        self.assertEqual(report["summary"]["ichiban_numbered_variant_created_rows"], 12)
        self.assertEqual(report["summary"]["ichiban_numbered_variant_application_skipped_rows"], 0)
        self.assertEqual(report["summary"]["ichiban_prize_policy_review_batch_count"], 2)
        self.assertEqual(report["summary"]["ichiban_reissue_duplicate_review_groups"], 2)
        animation_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "animation_category_action_queue"
        )
        self.assertEqual(animation_action["rows"], 12)
        self.assertEqual(animation_action["evidence"]["queued_categories"], 2)
        self.assertEqual(animation_action["evidence"]["unknown_category_rows"], 39)
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
