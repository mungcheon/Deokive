from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_catalog_operations_dashboard as dashboard


def _write_json(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class CatalogOperationsDashboardTests(unittest.TestCase):
    def test_build_collects_core_workboards_and_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = {
                "goal": _write_json(
                    root / "goal.json",
                    {
                        "rows": 10,
                        "duplicate_groups": 0,
                        "missing_enrichment": {"image_url": 2, "barcode": 3},
                        "next_actions": [{"priority": 10, "area": "images", "action": "Review", "evidence": "2"}],
                    },
                ),
                "field_batches": _write_json(root / "fields.json", {"actionable_rows": 4, "batch_count": 2}),
                "image_queue": _write_json(root / "images.json", {"missing_images": 2, "by_strategy": [["official", 2]]}),
                "image_exact_url_queue": _write_json(
                    root / "exact_urls.json",
                    {
                        "item_count": 8,
                        "by_identity_review": [
                            ["exact_url_research", 6],
                            ["blocked_by_identity_review", 2],
                        ],
                    },
                ),
                "source_discovery": _write_json(
                    root / "source_discovery.json",
                    {
                        "summary": {
                            "source_discovery_rows": 6,
                            "stale_excluded_rows": 2,
                            "by_workflow": [["official_search_url_available", 6]],
                            "top_store_categories": [
                                {"source_store": "Animate", "category": "Badge", "rows": 4}
                            ],
                            "top_official_search_store_categories": [
                                {"source_store": "Animate", "category": "Badge", "rows": 4}
                            ],
                        }
                    },
                ),
                "source_url_bottlenecks": _write_json(
                    root / "source_url_bottlenecks.json",
                    {
                        "missing_source_url": 8,
                        "missing_image_and_source_url": 6,
                        "has_image_but_missing_source_url": 2,
                        "automation_ready_source_candidates": 1,
                        "manual_review_source_candidates": 4,
                        "blocked_before_image_import": 11,
                        "bottleneck_counts": [["missing_source_url", 8]],
                        "missing_source_by_store": [["Animate", 5]],
                        "missing_both_by_store": [["Animate", 4]],
                    },
                ),
                "source_detail_candidates": _write_json(
                    root / "source_detail_candidates.json",
                    {
                        "summary": {
                            "source_queue_rows": 10,
                            "supported_provider_rows": 3,
                            "unsupported_provider_rows": 7,
                            "scanned_rows": 3,
                            "exact_candidate_rows": 1,
                            "candidate_review_rows": 1,
                            "status_counts": [["exact_candidate_available", 1]],
                            "top_unsupported_provider_stores": [{"source_store": "Animate", "rows": 5}],
                        }
                    },
                ),
                "source_detail_candidate_summary": _write_json(
                    root / "source_detail_candidate_summary.json",
                    {
                        "summary": {
                            "report_count": 3,
                            "processed_rows_reported": 30,
                            "unique_processed_store_row_pairs": 18,
                            "unique_exact_candidate_store_row_pairs": 2,
                            "unique_review_candidate_store_row_pairs": 1,
                            "actionable_report_count": 2,
                            "time_budget_exhausted_reports": 1,
                            "rate_limit_skipped_stores": [["Ensky", 1]],
                        },
                        "by_store": [
                            {
                                "store": "Ensky",
                                "report_count": 2,
                                "result_rows": 12,
                                "failure_count": 1,
                                "exact_candidate_rows": 2,
                                "candidate_review_rows": 1,
                                "no_candidate_rows": 9,
                            }
                        ],
                    },
                ),
                "image_batches": _write_json(root / "image_batches.json", {"batch_count": 9}),
                "unapplied_image_changes": _write_json(root / "unapplied_images.json", {"candidate_count": 3}),
                "image_provider": _write_json(root / "providers.json", {"actionable_or_provider_work_images": 1}),
                "image_provider_recheck": _write_json(
                    root / "provider_recheck.json",
                    {
                        "filled": 0,
                        "processed_rows": 12,
                        "time_budget_exhausted": False,
                        "allowed_stores": ["엔스카이"],
                        "unresolved_summary": {
                            "total": 12,
                            "by_reason": {
                                "no_provider_candidates": 7,
                                "best_candidate_rejected": 5,
                            },
                            "by_failed_check": {
                                "all_distinctive_token_match": 5,
                                "goods_type_compatible": 3,
                            },
                        },
                    },
                ),
                "web_image_search_candidates": _write_json(
                    root / "web_image_search.json",
                    {
                        "target_rows": 5,
                        "candidate_rows": 1,
                        "rejected_rows": 2,
                        "stopped_early": True,
                        "rejected_reason_counts": [["search_failed", 2]],
                    },
                ),
                "agent_image_candidates": _write_json(
                    root / "agent_image_candidates.json",
                    {
                        "summary": {
                            "candidate_files": 3,
                            "input_items": 2,
                            "preflight_passed_items": 1,
                            "ready_items": 1,
                            "rejected_items": 1,
                            "rejected_reasons": [["unsafe_source_image_pair", 1]],
                        }
                    },
                ),
                "agent_image_candidates_broad": _write_json(
                    root / "agent_image_candidates_broad.json",
                    {
                        "summary": {
                            "candidate_files": 80,
                            "input_items": 966,
                            "preflight_passed_items": 2,
                            "ready_items": 0,
                            "rejected_items": 966,
                            "rejected_reasons": [["image_already_present", 305]],
                        }
                    },
                ),
                "image_existing_candidates": _write_json(
                    root / "existing_candidates.json",
                    {
                        "summary": {
                            "candidate_items": 1,
                            "missing_rows": 2,
                            "scanned_files": 4,
                            "scanned_candidate_rows": 9,
                            "skipped_rows": 8,
                        },
                        "skipped_by_reason": [["candidate_title_mismatch", 4]],
                    },
                ),
                "image_existing_candidates_strict_import": _write_json(
                    root / "existing_candidates_strict.json",
                    {
                        "candidate_rows": 1,
                        "updated_rows": 0,
                        "skipped_rows": 1,
                        "skipped_reasons": [["live_title_exact_mismatch", 1]],
                    },
                ),
                "remaining_image_audit": _write_json(
                    root / "remaining_image_audit.json",
                    {
                        "missing_images": 2,
                        "provider_candidate_items": 11,
                        "manual_or_blocked_items": 5,
                        "missing_with_source_url": 4,
                        "missing_with_exact_source_url": 1,
                        "missing_with_generic_source_url": 3,
                        "candidate_reviews": {
                            "ready_items": 0,
                            "preflight_passed_items": 2,
                            "candidate_items": 10,
                            "rejected_reasons": [
                                ["image_already_present", 6],
                                ["current_name_mismatch", 4],
                            ],
                        },
                        "provider_blockers": [
                            {"source_store": "Animate", "provider_candidate_items": 7}
                        ],
                    },
                ),
                "image_auto_promotable": _write_json(
                    root / "auto_promotable.json",
                    {"summary": {"candidate_items": 5}},
                ),
                "image_auto_promotable_strict_import": _write_json(
                    root / "auto_promotable_strict.json",
                    {
                        "candidate_rows": 5,
                        "updated_rows": 0,
                        "skipped_rows": 5,
                        "skipped_reasons": [["candidate_row_name_mismatch", 5]],
                    },
                ),
                "chiikawa_gotouchi_api": _write_json(
                    root / "gotouchi.json",
                    {
                        "target_rows": 4,
                        "official_image_count": 46,
                        "status_counts": {"official_pair_available": 1, "theme_not_in_current_official_api": 3},
                    },
                ),
                "taito_brand_candidates": _write_json(
                    root / "taito_brand.json",
                    {"target_rows": 5, "exact_match_rows": 1, "brand_counts": {"desktop_cute": 181}},
                ),
                "storefront_match_review": _write_json(
                    root / "storefront_match.json",
                    {"ambiguous_reviewable_candidates": 17, "manual_only_rows": 192},
                ),
                "storefront_batches": _write_json(root / "storefront.json", {"reviewable_seed_rows": 1, "reviewable_candidate_rows": 3}),
                "fanding_stellive": _write_json(
                    root / "fanding.json",
                    {
                        "rows": 97,
                        "summary": {
                            "candidate_status_counts": {
                                "weak_manual_review_candidate": 7,
                                "low_confidence_candidate": 16,
                                "no_candidate": 74,
                            }
                        },
                    },
                ),
                "pokemon_center_official": _write_json(root / "pokemon_center.json", {"updated_rows": 0, "review_rows": 3}),
                "official_batches": _write_json(root / "official.json", {"reviewable_seed_rows": 2, "reviewable_candidate_rows": 5}),
                "official_detail_animate_merged": _write_json(
                    root / "official_detail_animate_merged.json",
                    {
                        "unique_processed_seed_rows": 151,
                        "candidate_rows": 306,
                        "reviewable_rows": 3,
                        "by_status": [["needs_manual_title_review", 3]],
                        "by_manual_review_reason": [["broad_seed_needs_representative_or_variant_choice", 3]],
                    },
                ),
                "official_detail_ensky_merged": _write_json(
                    root / "official_detail_ensky_merged.json",
                    {
                        "unique_processed_seed_rows": 151,
                        "candidate_rows": 391,
                        "reviewable_rows": 0,
                        "by_status": [["blocked_type_mismatch", 191]],
                        "by_manual_review_reason": [["candidate_goods_type_mismatch", 191]],
                    },
                ),
                "ichiban_gap": _write_json(
                    root / "gaps.json",
                    {
                        "total_items": 1,
                        "documented_terminal_items": 1,
                        "actionable_items": 0,
                        "all_gaps_documented": True,
                        "by_workflow": [["archive", 1]],
                    },
                ),
                "ichiban_replacement_urls": _write_json(
                    root / "replacement.json",
                    {
                        "by_status": [
                            ["replacement_extractable", 1],
                            ["covered_by_seeded_counterpart", 2],
                        ]
                    },
                ),
                "ichiban_sub_series_batches": _write_json(root / "sub_series.json", {"batch_count": 4}),
                "ichiban_structure": _write_json(root / "structure.json", {"missing_sub_series_rows": 7}),
                "ichiban_campaign_gap_audit": _write_json(
                    root / "campaign_gap_audit.json",
                    {
                        "campaign_count": 12,
                        "seeded_campaign_url_count": 10,
                        "campaign_gap_count": 2,
                        "audited_gap_count": 2,
                        "by_classification": [["official_online_archive_404", 2]],
                    },
                ),
                "ichiban_metadata": _write_json(
                    root / "metadata.json",
                    {
                        "urls_with_missing_metadata": 3,
                        "rows_missing_release_date": 1,
                        "rows_missing_official_price_jpy": 5,
                        "safe_release_url_count": 0,
                        "safe_price_url_count": 0,
                    },
                ),
                "ichiban_metadata_review": _write_json(
                    root / "metadata_review.json",
                    {
                        "summary": {
                            "review_items": 2,
                            "missing_release_rows": 1,
                            "missing_price_rows": 5,
                            "by_workflow": [["manual_price_review", 2]],
                        }
                    },
                ),
                "ichiban_history_status": _write_json(
                    root / "ichiban_history_status.json",
                    {
                        "status": "metadata_evidence_blocked",
                        "campaign_count": 12,
                        "seeded_campaign_url_count": 10,
                        "campaign_coverage_rate": 0.833333,
                        "campaign_gap_count": 2,
                        "documented_terminal_gap_items": 2,
                        "actionable_gap_items": 0,
                        "import_safe_now": True,
                        "prize_rows": 20,
                        "missing_sub_series_rows": 0,
                        "metadata": {
                            "blocked_rows": 6,
                            "safe_update_url_count": 0,
                        },
                    },
                ),
                "animation_categories": _write_json(
                    root / "animation.json",
                    {
                        "rows": 8,
                        "category_count": 2,
                        "unknown_categories": [],
                        "category_families": [{"family": "figure", "rows": 5}],
                        "missing_image_by_category": [{"category": "피규어", "rows": 3}],
                        "missing_source_url_by_category": [{"category": "아크릴 스탠드", "rows": 2}],
                    },
                ),
                "animation_enrichment_priority": _write_json(
                    root / "animation_priority.json",
                    {
                        "queue_groups": 4,
                        "queue_rows": 12,
                        "missing_image_rows": 8,
                        "missing_source_rows": 10,
                        "by_workflow": [["find_exact_source_url", 10], ["attach_image_from_exact_source", 2]],
                    },
                ),
                "app_folder_visuals": _write_json(
                    root / "app_folder_visuals.json",
                    {
                        "icon_count": 138,
                        "icon_group_count": 9,
                        "color_count": 186,
                        "unique_color_count": 186,
                        "palette_section_count": 8,
                        "animation_visuals_covered": True,
                        "missing_animation_icons": [],
                        "missing_animation_colors": [],
                        "duplicate_icon_keys": [],
                        "duplicate_colors": [],
                    },
                ),
                "confirmed_import": _write_json(root / "confirmed.json", {"summary": {"manual_confirmed_true": 0}}),
                "confirmed_archive": _write_json(root / "archive.json", {"summary": {"archive_items": 6}}),
                "requested_special_goods": _write_json(
                    root / "requested.json",
                    {"requested": 40, "already_present": 39, "missing": 1, "with_candidate_image": 38},
                ),
                "report_consistency": _write_json(
                    root / "consistency.json",
                    {"ok": True, "failure_count": 0, "check_count": 9},
                ),
                "db_sync": _write_json(
                    root / "db_sync.json",
                    {
                        "ok": True,
                        "seed_rows": 10,
                        "seed_keys": 10,
                        "db_count": 2,
                        "databases": [
                            {
                                "db": "server/deokive_dev.db",
                                "ok": True,
                                "active_rows": 10,
                                "missing_images": 2,
                                "stale_active_rows": 0,
                                "missing_seed_rows": 0,
                                "updated_active_rows": 0,
                                "duplicate_active_rows": 0,
                            },
                            {
                                "db": "deokive_dev.db",
                                "ok": True,
                                "active_rows": 10,
                                "missing_images": 2,
                                "stale_active_rows": 0,
                                "missing_seed_rows": 0,
                                "updated_active_rows": 0,
                                "duplicate_active_rows": 0,
                            },
                        ],
                    },
                ),
                "store_source_netloc": _write_json(
                    root / "store_source.json",
                    {"mismatch_count": 2, "by_severity": [["external_evidence_source", 2]]},
                ),
                "live_source_identity": _write_json(
                    root / "live_source.json",
                    {
                        "scoped_rows": 5,
                        "audited_urls": 3,
                        "mismatch_urls": 2,
                        "failure_count": 0,
                        "status_counts": {"live_title_mismatch": 2, "title_overlap_ok": 1},
                    },
                ),
                "stale_source_cleanup": _write_json(
                    root / "stale_cleanup.json",
                    {
                        "summary": {
                            "mismatch_rows": 4,
                            "mismatch_urls": 2,
                            "by_source_store": [["Test Store", 4]],
                        }
                    },
                ),
                "product_identity_review": _write_json(
                    root / "product_identity.json",
                    {
                        "summary": {
                            "review_rows": 3,
                            "skipped_rows": 1,
                            "by_source_store": [["Official Store", 3]],
                            "by_status": [["official_search_no_exact_product", 3]],
                        }
                    },
                ),
                "generic_source_cleanup": _write_json(
                    root / "generic_source.json",
                    {
                        "summary": {
                            "generic_source_rows": 7,
                            "generic_source_urls": 2,
                            "by_source_store": [["Storefront", 7]],
                            "by_candidate_status": [["weak_manual_review_candidate", 2], ["no_candidate_report", 5]],
                        }
                    },
                ),
                "prize_source_store_lines": _write_json(
                    root / "prize_source_store.json",
                    {
                        "summary": {
                            "line_rows": 12,
                            "mismatch_rows": 4,
                            "missing_image_mismatch_rows": 3,
                            "by_current_expected": [
                                {
                                    "current_source_store": "FuRyu",
                                    "expected_source_store": "SEGA",
                                    "rows": 2,
                                }
                            ],
                        }
                    },
                ),
                "prize_line_expected_provider": _write_json(
                    root / "prize_line_expected_provider.json",
                    {"summary": {"items": 3}},
                ),
                "prize_line_official_detail": _write_json(
                    root / "prize_line_official_detail.json",
                    {
                        "target_items": 3,
                        "candidate_rows": 5,
                        "by_status": [["weak_or_ambiguous", 2], ["no_candidates_found", 1]],
                        "target_by_store": {"SEGA": 2, "Banpresto": 1},
                    },
                ),
                "prize_provider_fallback_images": _write_json(
                    root / "prize_provider_fallback.json",
                    {
                        "summary": {
                            "target_stores": ["FuRyu", "Taito"],
                            "searched_rows": 6,
                            "fallback_candidate_rows": 4,
                            "unresolved_rows": 2,
                        }
                    },
                ),
                "focus_missing_images": _write_json(
                    root / "focus_missing_images.json",
                    {
                        "focus_count": 3,
                        "focus_rows": 20,
                        "focus_missing_image_rows": 7,
                        "focus_missing_source_rows": 6,
                        "focus_missing_image_and_source_rows": 5,
                        "focus_summaries": [
                            {
                                "focus_key": "danganronpa",
                                "focus_label": "단간론파",
                                "rows": 9,
                                "missing_image_rows": 4,
                                "missing_source_rows": 3,
                            }
                        ],
                    },
                ),
                "focus_series_missing_images": _write_json(
                    root / "focus_series_missing_images.json",
                    {
                        "focus_count": 4,
                        "missing_image_rows": 12,
                        "missing_source_rows": 9,
                        "auto_write_ready": 1,
                        "focus_summaries": [
                            {
                                "focus_key": "hunter_x_hunter",
                                "focus_label": "HUNTER\u00d7HUNTER",
                                "missing_image_rows": 7,
                                "missing_source_rows": 7,
                                "auto_write_ready": 0,
                            }
                        ],
                    },
                ),
                "public_image_actionability": _write_json(
                    root / "public_image_actionability.json",
                    {
                        "summary": {
                            "missing_image_rows": 720,
                            "readiness_classified_rows": 720,
                            "unclassified_rows": 0,
                            "source_first_rows": 692,
                            "review_before_attach_rows": 23,
                            "actionable_image_rows": 75,
                            "direct_image_action_queue_rows": 73,
                            "source_detail_candidate_review_rows": 2,
                            "source_detail_candidate_recheck_required_rows": 10,
                            "manual_image_research_rows": 5,
                            "source_discovery_focus_pack_rows": 427,
                            "source_discovery_focus_pack_count": 24,
                            "source_discovery_remaining_focus_review_rows": 427,
                            "source_discovery_confirmed_focus_source_rows": 0,
                            "source_discovery_focus_coverage": 0.6651,
                            "source_discovery_focus_template_rows": 427,
                            "source_discovery_focus_template_confirmed_rows": 0,
                            "source_discovery_focus_template_dry_run_updated_rows": 0,
                            "source_discovery_focus_template_dry_run_skipped_rows": 427,
                            "auto_apply_enabled": False,
                        }
                    },
                ),
                "public_source_focus_packs": _write_json(
                    root / "public_source_focus_packs.json",
                    {
                        "summary": {
                            "focus_pack_count": 24,
                            "not_started_focus_pack_count": 24,
                            "remaining_focus_review_rows": 427,
                            "confirmed_focus_source_rows": 0,
                            "focus_coverage": 0.6651,
                            "focus_source_stores": ["Animate", "Ensky"],
                        }
                    },
                ),
                "public_source_focus_template": _write_json(
                    root / "public_source_focus_template.json",
                    {
                        "summary": {
                            "template_items": 427,
                            "manual_confirmed_rows": 0,
                        }
                    },
                ),
                "public_source_focus_template_import": _write_json(
                    root / "public_source_focus_template_import.json",
                    {
                        "updated_rows": 0,
                        "skipped_rows": 427,
                        "skip_reason_counts": [["manual_confirmed_false", 427]],
                    },
                ),
            }

            with patch.object(dashboard, "SOURCES", sources):
                payload = dashboard.build()

        self.assertEqual(payload["summary"]["rows"], 10)
        self.assertEqual(payload["summary"]["field_actionable_rows"], 4)
        self.assertEqual(payload["summary"]["source_discovery"]["source_discovery_rows"], 6)
        self.assertEqual(payload["summary"]["source_discovery"]["stale_excluded_rows"], 2)
        self.assertEqual(
            payload["summary"]["source_discovery"]["top_official_search_store_categories"][0]["rows"],
            4,
        )
        self.assertEqual(payload["summary"]["source_url_bottlenecks"]["missing_source_url"], 8)
        self.assertEqual(payload["summary"]["source_url_bottlenecks"]["missing_image_and_source_url"], 6)
        self.assertEqual(payload["summary"]["source_url_bottlenecks"]["automation_ready_source_candidates"], 1)
        self.assertEqual(payload["summary"]["source_url_bottlenecks"]["blocked_before_image_import"], 11)
        self.assertEqual(payload["summary"]["source_detail_candidates"]["source_queue_rows"], 10)
        self.assertEqual(payload["summary"]["source_detail_candidates"]["unsupported_provider_rows"], 7)
        self.assertEqual(payload["summary"]["source_detail_candidates"]["batch_summary"]["report_count"], 3)
        self.assertEqual(
            payload["summary"]["source_detail_candidates"]["batch_summary"]["unique_processed_store_row_pairs"],
            18,
        )
        self.assertEqual(
            payload["summary"]["source_detail_candidates"]["batch_summary"]["unique_exact_candidate_store_row_pairs"],
            2,
        )
        self.assertEqual(
            payload["summary"]["source_detail_candidates"]["batch_summary"]["top_stores"][0]["store"],
            "Ensky",
        )
        self.assertEqual(
            payload["summary"]["source_detail_candidates"]["top_unsupported_provider_stores"][0]["source_store"],
            "Animate",
        )
        self.assertEqual(payload["summary"]["source_detail_candidates"]["exact_candidate_rows"], 1)
        self.assertEqual(payload["summary"]["image_exact_url_work_items"], 8)
        self.assertEqual(payload["summary"]["image_exact_url_research_items"], 6)
        self.assertEqual(payload["summary"]["image_exact_url_identity_blocked"], 2)
        self.assertEqual(payload["summary"]["image_review_batches"], 9)
        self.assertEqual(payload["summary"]["unapplied_image_candidates"], 3)
        self.assertEqual(payload["summary"]["image_provider_recheck"]["processed_rows"], 12)
        self.assertEqual(
            payload["summary"]["image_provider_recheck"]["unresolved_summary"]["by_reason"]["no_provider_candidates"],
            7,
        )
        self.assertEqual(payload["summary"]["web_image_search"]["candidate_rows"], 1)
        self.assertEqual(payload["summary"]["web_image_search"]["stopped_early"], True)
        self.assertEqual(payload["summary"]["image_auto_promotable_candidates"], 5)
        self.assertEqual(payload["summary"]["image_auto_promotable_strict_import"]["updated_rows"], 0)
        self.assertEqual(
            payload["summary"]["image_auto_promotable_strict_import"]["skipped_reasons"][0],
            ["candidate_row_name_mismatch", 5],
        )
        self.assertEqual(payload["summary"]["image_existing_candidates"]["candidate_items"], 1)
        self.assertEqual(payload["summary"]["image_existing_candidates"]["scanned_candidate_rows"], 9)
        self.assertEqual(payload["summary"]["image_existing_candidates"]["strict_import"]["updated_rows"], 0)
        self.assertEqual(
            payload["summary"]["image_existing_candidates"]["strict_import"]["skipped_reasons"][0],
            ["live_title_exact_mismatch", 1],
        )
        self.assertEqual(payload["summary"]["remaining_image_audit"]["provider_candidate_items"], 11)
        self.assertEqual(payload["summary"]["remaining_image_audit"]["manual_or_blocked_items"], 5)
        self.assertEqual(payload["summary"]["remaining_image_audit"]["candidate_reviews"]["ready_items"], 0)
        self.assertEqual(
            payload["summary"]["remaining_image_audit"]["candidate_reviews"]["rejected_reasons"][0],
            ["image_already_present", 6],
        )
        self.assertEqual(payload["summary"]["chiikawa_gotouchi_api"]["target_rows"], 4)
        self.assertEqual(payload["summary"]["chiikawa_gotouchi_api"]["official_image_count"], 46)
        self.assertEqual(payload["summary"]["taito_brand_target_rows"], 5)
        self.assertEqual(payload["summary"]["taito_brand_exact_matches"], 1)
        self.assertEqual(payload["summary"]["storefront_reviewable_seed_rows"], 1)
        self.assertEqual(payload["summary"]["storefront_reviewable_candidate_rows"], 3)
        self.assertEqual(payload["summary"]["storefront_ambiguous_candidates"], 17)
        self.assertEqual(payload["summary"]["storefront_manual_only_rows"], 192)
        self.assertEqual(payload["summary"]["fanding_stellive"]["candidate_rows"], 97)
        self.assertEqual(
            payload["summary"]["fanding_stellive"]["candidate_status_counts"]["weak_manual_review_candidate"],
            7,
        )
        self.assertEqual(payload["summary"]["official_detail_provider_sweeps"]["processed_seed_rows"], 302)
        self.assertEqual(payload["summary"]["official_detail_provider_sweeps"]["candidate_rows"], 697)
        self.assertEqual(payload["summary"]["official_detail_provider_sweeps"]["reviewable_rows"], 3)
        self.assertEqual(payload["summary"]["official_detail_provider_sweeps"]["animate"]["reviewable_rows"], 3)
        self.assertEqual(payload["summary"]["official_detail_provider_sweeps"]["ensky"]["reviewable_rows"], 0)
        self.assertEqual(payload["summary"]["pokemon_center_official"]["review_rows"], 3)
        self.assertEqual(payload["summary"]["ichiban_replacement_extractable"], 1)
        self.assertEqual(payload["summary"]["ichiban_replacement_seeded_counterparts"], 2)
        self.assertEqual(payload["summary"]["ichiban_gap_documented_terminal_items"], 1)
        self.assertEqual(payload["summary"]["ichiban_gap_actionable_items"], 0)
        self.assertEqual(payload["summary"]["ichiban_gap_all_documented"], True)
        self.assertEqual(payload["summary"]["ichiban_campaign_gap_audit"]["campaign_gap_count"], 2)
        self.assertEqual(payload["summary"]["ichiban_metadata"]["urls_with_missing_metadata"], 3)
        self.assertEqual(payload["summary"]["ichiban_metadata"]["rows_missing_official_price_jpy"], 5)
        self.assertEqual(payload["summary"]["ichiban_metadata"]["review_items"], 2)
        self.assertEqual(payload["summary"]["ichiban_metadata"]["review_missing_price_rows"], 5)
        self.assertEqual(payload["summary"]["ichiban_history_status"]["status"], "metadata_evidence_blocked")
        self.assertEqual(payload["summary"]["ichiban_history_status"]["campaign_count"], 12)
        self.assertEqual(payload["summary"]["ichiban_history_status"]["documented_terminal_gap_items"], 2)
        self.assertEqual(payload["summary"]["ichiban_history_status"]["metadata"]["blocked_rows"], 6)
        self.assertEqual(payload["summary"]["animation_category_count"], 2)
        self.assertEqual(payload["summary"]["animation_missing_image_by_category"][0]["category"], "피규어")
        self.assertEqual(payload["summary"]["animation_missing_source_url_by_category"][0]["category"], "아크릴 스탠드")
        self.assertEqual(payload["summary"]["animation_enrichment_priority"]["queue_rows"], 12)
        self.assertEqual(payload["summary"]["animation_enrichment_priority"]["missing_source_rows"], 10)
        self.assertEqual(payload["summary"]["app_folder_visuals"]["icon_count"], 138)
        self.assertEqual(payload["summary"]["app_folder_visuals"]["color_count"], 186)
        self.assertEqual(payload["summary"]["app_folder_visuals"]["palette_section_count"], 8)
        self.assertEqual(payload["summary"]["app_folder_visuals"]["animation_visuals_covered"], True)
        self.assertEqual(payload["summary"]["confirmed_archive_items"], 6)
        self.assertEqual(payload["summary"]["requested_special_goods"]["missing"], 1)
        self.assertEqual(payload["summary"]["report_consistency_ok"], True)
        self.assertEqual(payload["summary"]["db_sync"]["issue_dbs"], 0)
        self.assertEqual(payload["summary"]["store_source_mismatches"], 2)
        self.assertEqual(payload["summary"]["store_source_external_evidence"], 2)
        self.assertEqual(payload["summary"]["live_source_identity"]["mismatch_urls"], 2)
        self.assertEqual(payload["summary"]["stale_source_cleanup"]["mismatch_rows"], 4)
        self.assertEqual(payload["summary"]["stale_source_cleanup"]["mismatch_urls"], 2)
        self.assertEqual(payload["summary"]["product_identity_review"]["review_rows"], 3)
        self.assertEqual(payload["summary"]["product_identity_review"]["skipped_rows"], 1)
        self.assertEqual(payload["summary"]["generic_source_cleanup"]["generic_source_rows"], 7)
        self.assertEqual(payload["summary"]["generic_source_cleanup"]["generic_source_urls"], 2)
        self.assertEqual(
            payload["summary"]["generic_source_cleanup"]["by_candidate_status"],
            [["weak_manual_review_candidate", 2], ["no_candidate_report", 5]],
        )
        self.assertEqual(payload["summary"]["prize_source_store_lines"]["mismatch_rows"], 4)
        self.assertEqual(payload["summary"]["prize_source_store_lines"]["missing_image_mismatch_rows"], 3)
        self.assertEqual(payload["summary"]["prize_line_provider_candidates"]["expected_provider_items"], 3)
        self.assertEqual(payload["summary"]["prize_line_provider_candidates"]["candidate_rows"], 5)
        self.assertEqual(payload["summary"]["prize_provider_fallback_images"]["fallback_candidate_rows"], 4)
        self.assertEqual(payload["summary"]["prize_provider_fallback_images"]["searched_rows"], 6)
        self.assertEqual(payload["summary"]["focus_missing_images"]["focus_missing_image_rows"], 7)
        self.assertEqual(payload["summary"]["focus_missing_images"]["focus_missing_source_rows"], 6)
        self.assertEqual(payload["summary"]["focus_series_missing_images"]["missing_image_rows"], 12)
        self.assertEqual(payload["summary"]["focus_series_missing_images"]["missing_source_rows"], 9)
        self.assertEqual(payload["summary"]["public_image_recovery"]["missing_image_rows"], 720)
        self.assertEqual(payload["summary"]["public_image_recovery"]["source_first_rows"], 692)
        self.assertEqual(payload["summary"]["public_image_recovery"]["actionable_image_rows"], 75)
        self.assertEqual(payload["summary"]["public_image_recovery"]["direct_image_action_queue_rows"], 73)
        self.assertEqual(payload["summary"]["public_image_recovery"]["source_detail_candidate_review_rows"], 2)
        self.assertEqual(payload["summary"]["public_image_recovery"]["source_detail_candidate_recheck_required_rows"], 10)
        self.assertEqual(payload["summary"]["public_image_recovery"]["manual_image_research_rows"], 5)
        self.assertEqual(payload["summary"]["public_image_recovery"]["focus_pack_rows"], 427)
        self.assertEqual(payload["summary"]["public_image_recovery"]["focus_pack_count"], 24)
        self.assertEqual(payload["summary"]["public_image_recovery"]["remaining_focus_review_rows"], 427)
        self.assertEqual(payload["summary"]["public_image_recovery"]["template_rows"], 427)
        self.assertEqual(payload["summary"]["public_image_recovery"]["template_import_skipped_rows"], 427)
        self.assertEqual(payload["summary"]["public_image_recovery"]["auto_apply_enabled"], False)
        self.assertGreaterEqual(len(payload["workboards"]), 10)
        areas = [item["area"] for item in payload["workboards"]]
        self.assertIn("Field backfill", areas)
        self.assertIn("Public image recovery", areas)
        self.assertIn("Source URL bottlenecks", areas)
        self.assertIn("Web image search candidates", areas)
        self.assertIn("Agent image candidate imports", areas)
        self.assertIn("Broad image candidate imports", areas)
        self.assertIn("Chiikawa gotouchi API coverage", areas)
        self.assertIn("Taito brand API candidates", areas)
        self.assertIn("Pokemon Center candidates", areas)
        self.assertIn("Stellive Fanding candidates", areas)
        self.assertIn("Official detail provider sweeps", areas)
        self.assertIn("Ichiban Kuji gaps", areas)
        self.assertIn("Ichiban Kuji campaign audit", areas)
        self.assertIn("Ichiban Kuji history status", areas)
        self.assertIn("Store/source integrity", areas)
        self.assertIn("Generic source cleanup", areas)
        self.assertIn("Prize source-store line audit", areas)
        self.assertIn("Prize line provider candidates", areas)
        self.assertIn("Prize provider fallback images", areas)
        self.assertIn("Product identity review", areas)
        self.assertIn("App folder visuals", areas)
        self.assertIn("Report consistency", areas)
        self.assertIn("DB sync", areas)
        self.assertIn("Requested special goods", areas)
        self.assertIn("Focus missing images", areas)
        self.assertIn("Focus series image work", areas)
        storefront_board = next(item for item in payload["workboards"] if item["area"] == "Storefront candidates")
        self.assertEqual(storefront_board["ambiguous_metric"], 17)
        self.assertEqual(storefront_board["manual_only_metric"], 192)
        fanding_board = next(item for item in payload["workboards"] if item["area"] == "Stellive Fanding candidates")
        self.assertEqual(fanding_board["primary_metric"], 97)
        self.assertEqual(fanding_board["secondary_metric"], 7)
        self.assertEqual(fanding_board["manual_only_metric"], 74)
        self.assertEqual(fanding_board["artifact"], "server/fanding_stellive_match_queue.json")
        self.assertEqual(fanding_board["markdown"], "server/fanding_stellive_match_queue.csv")
        official_sweeps_board = next(item for item in payload["workboards"] if item["area"] == "Official detail provider sweeps")
        self.assertEqual(official_sweeps_board["primary_metric"], 302)
        self.assertEqual(official_sweeps_board["secondary_metric"], 3)
        self.assertEqual(official_sweeps_board["quick_win_metric"], 697)
        self.assertEqual(official_sweeps_board["status"], "manual_confirmation_needed")
        self.assertEqual(official_sweeps_board["animate_reviewable"], 3)
        self.assertEqual(official_sweeps_board["ensky_reviewable"], 0)
        generic_source_board = next(item for item in payload["workboards"] if item["area"] == "Generic source cleanup")
        self.assertEqual(
            generic_source_board["candidate_status_counts"],
            [["weak_manual_review_candidate", 2], ["no_candidate_report", 5]],
        )
        prize_source_board = next(item for item in payload["workboards"] if item["area"] == "Prize source-store line audit")
        self.assertEqual(prize_source_board["primary_metric"], 4)
        self.assertEqual(prize_source_board["secondary_metric"], 3)
        self.assertEqual(prize_source_board["status"], "provider_routing_review_needed")
        prize_line_board = next(item for item in payload["workboards"] if item["area"] == "Prize line provider candidates")
        self.assertEqual(prize_line_board["primary_metric"], 5)
        self.assertEqual(prize_line_board["secondary_metric"], 3)
        self.assertEqual(prize_line_board["quick_win_metric"], 2)
        self.assertEqual(prize_line_board["status"], "manual_confirmation_needed")
        prize_fallback_board = next(item for item in payload["workboards"] if item["area"] == "Prize provider fallback images")
        self.assertEqual(prize_fallback_board["primary_metric"], 4)
        self.assertEqual(prize_fallback_board["secondary_metric"], 6)
        self.assertEqual(prize_fallback_board["quick_win_metric"], 2)
        self.assertEqual(prize_fallback_board["status"], "manual_confirmation_needed")
        self.assertEqual(prize_fallback_board["artifact"], "server/prize_provider_fallback_image_candidates_current.html")
        focus_board = next(item for item in payload["workboards"] if item["area"] == "Focus missing images")
        self.assertEqual(focus_board["primary_metric"], 7)
        self.assertEqual(focus_board["secondary_metric"], 6)
        self.assertEqual(focus_board["status"], "source_research_needed")
        focus_series_board = next(item for item in payload["workboards"] if item["area"] == "Focus series image work")
        self.assertEqual(focus_series_board["primary_metric"], 12)
        self.assertEqual(focus_series_board["secondary_metric"], 9)
        self.assertEqual(focus_series_board["quick_win_metric"], 1)
        self.assertEqual(focus_series_board["status"], "source_research_needed")
        agent_image_board = next(item for item in payload["workboards"] if item["area"] == "Agent image candidate imports")
        self.assertEqual(agent_image_board["primary_metric"], 1)
        self.assertEqual(agent_image_board["secondary_metric"], 1)
        self.assertEqual(agent_image_board["status"], "import_ready")
        self.assertEqual(agent_image_board["candidate_files_metric"], 3)
        self.assertEqual(agent_image_board["artifact"], "server/agent_image_candidates_import_queue_current.html")
        self.assertEqual(agent_image_board["markdown"], "server/agent_image_candidates_import_queue_current.md")
        broad_agent_image_board = next(item for item in payload["workboards"] if item["area"] == "Broad image candidate imports")
        self.assertEqual(broad_agent_image_board["primary_metric"], 0)
        self.assertEqual(broad_agent_image_board["secondary_metric"], 966)
        self.assertEqual(broad_agent_image_board["candidate_files_metric"], 80)
        self.assertEqual(broad_agent_image_board["status"], "reviewed_no_safe_imports")
        self.assertEqual(broad_agent_image_board["artifact"], "server/agent_image_candidates_import_queue_broad.html")
        self.assertEqual(broad_agent_image_board["markdown"], "server/agent_image_candidates_import_queue_broad.md")
        animation_board = next(item for item in payload["workboards"] if item["area"] == "Animation categories")
        self.assertEqual(animation_board["category_count"], 2)
        self.assertEqual(animation_board["category_family_count"], 1)
        self.assertEqual(animation_board["priority_queue_groups"], 4)
        self.assertEqual(animation_board["priority_queue_rows"], 12)
        self.assertEqual(animation_board["top_missing_image_categories"][0]["rows"], 3)
        app_visual_board = next(item for item in payload["workboards"] if item["area"] == "App folder visuals")
        self.assertEqual(app_visual_board["primary_metric"], 138)
        self.assertEqual(app_visual_board["secondary_metric"], 186)
        self.assertEqual(app_visual_board["quick_win_metric"], 8)
        self.assertEqual(app_visual_board["status"], "covered")
        image_board = next(item for item in payload["workboards"] if item["area"] == "Image enrichment")
        self.assertEqual(image_board["auto_promotable"], 5)
        self.assertEqual(image_board["auto_promotable_strict_updated"], 0)
        self.assertEqual(image_board["auto_promotable_strict_skipped"], 5)
        self.assertEqual(image_board["existing_candidate_strict_updated"], 0)
        self.assertEqual(image_board["existing_candidate_strict_skipped"], 1)
        self.assertEqual(image_board["remaining_provider_candidate_items"], 11)
        self.assertEqual(image_board["remaining_manual_or_blocked_items"], 5)
        self.assertEqual(image_board["remaining_candidate_review_preflight"], 2)
        self.assertEqual(image_board["remaining_candidate_review_reasons"][0], ["image_already_present", 6])
        self.assertEqual(image_board["provider_recheck_processed_metric"], 12)
        self.assertEqual(image_board["provider_recheck_no_candidates_metric"], 7)
        self.assertEqual(image_board["provider_recheck_rejected_metric"], 5)
        self.assertEqual(image_board["provider_recheck_failed_check"][0], ["all_distinctive_token_match", 5])
        self.assertEqual(image_board["top_source_discovery_batches"][0]["source_store"], "Animate")
        public_image_board = next(item for item in payload["workboards"] if item["area"] == "Public image recovery")
        self.assertEqual(public_image_board["primary_metric"], 720)
        self.assertEqual(public_image_board["secondary_metric"], 427)
        self.assertEqual(public_image_board["quick_win_metric"], 75)
        self.assertEqual(public_image_board["direct_image_action_queue_rows"], 73)
        self.assertEqual(public_image_board["focus_pack_count"], 24)
        self.assertEqual(public_image_board["remaining_focus_review_rows"], 427)
        self.assertEqual(public_image_board["template_items"], 427)
        self.assertEqual(public_image_board["template_import_skipped_rows"], 427)
        self.assertEqual(public_image_board["status"], "manual_source_confirmation_needed")
        source_url_board = next(item for item in payload["workboards"] if item["area"] == "Source URL bottlenecks")
        self.assertEqual(source_url_board["primary_metric"], 8)
        self.assertEqual(source_url_board["secondary_metric"], 6)
        self.assertEqual(source_url_board["quick_win_metric"], 1)
        self.assertEqual(source_url_board["manual_review_metric"], 4)
        self.assertEqual(source_url_board["blocked_before_image_import"], 11)
        gap_board = next(item for item in payload["workboards"] if item["area"] == "Ichiban Kuji gaps")
        self.assertEqual(gap_board["status"], "archive_gaps_documented")
        self.assertEqual(gap_board["documented_terminal_metric"], 1)
        self.assertEqual(gap_board["actionable_gap_metric"], 0)
        campaign_board = next(item for item in payload["workboards"] if item["area"] == "Ichiban Kuji campaign audit")
        self.assertEqual(campaign_board["metadata_review_metric"], 2)
        history_board = next(item for item in payload["workboards"] if item["area"] == "Ichiban Kuji history status")
        self.assertEqual(history_board["primary_metric"], 12)
        self.assertEqual(history_board["secondary_metric"], 2)
        self.assertEqual(history_board["status"], "metadata_evidence_blocked")
        self.assertEqual(history_board["metadata_blocked_rows"], 6)
        db_sync_board = next(item for item in payload["workboards"] if item["area"] == "DB sync")
        self.assertEqual(db_sync_board["status"], "clean")
        self.assertEqual(db_sync_board["primary_metric"], 0)
        self.assertEqual(db_sync_board["db_count_metric"], 2)


if __name__ == "__main__":
    unittest.main()
