from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_image_attachment_action_queue_public as queue


class BuildImageAttachmentActionQueuePublicTest(unittest.TestCase):
    def test_build_report_keeps_actionable_image_workflows(self) -> None:
        enrichment = {
            "groups": [
                {
                    "workflow": "replace_generic_source_then_extract_image",
                    "source_store": "Stellive Store",
                    "missing_image_rows": 2,
                    "sample_items": [
                        {
                            "catalog_index": 2,
                            "name_ko": "Badge",
                            "category": "Can Badge",
                            "source_url": "https://example.com/shop",
                            "catalog_field_import_template": {
                                "field": "image_url",
                                "source_search_url": "https://stellive.fanding.kr/search?keyword=Badge",
                            },
                        },
                        {
                            "catalog_index": 1,
                            "name_ko": "Plush",
                            "category": "Plush",
                            "source_url": "https://example.com/shop",
                            "catalog_field_import_template": {"field": "image_url"},
                        },
                    ],
                },
                {
                    "workflow": "find_source_then_extract_image",
                    "source_store": "Movic",
                    "missing_image_rows": 5,
                    "sample_items": [
                        {
                            "catalog_index": 3,
                            "name_ko": "Acrylic",
                            "category": "Acrylic",
                            "catalog_field_import_template": {"field": "image_url"},
                        }
                    ],
                },
            ]
        }

        report = queue.build_report(enrichment, max_batches=10, batch_size=20)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["actionable_image_rows"], 2)
        self.assertEqual(report["summary"]["queued_image_rows"], 2)
        self.assertEqual(report["summary"]["unqueued_actionable_image_rows"], 0)
        self.assertEqual(report["summary"]["sample_queue_coverage"], 1.0)
        self.assertEqual(dict(report["summary"]["excluded_workflow_rows"]), {"find_source_then_extract_image": 5})
        self.assertEqual(report["summary"]["source_url_update_required_rows"], 2)
        self.assertEqual(report["summary"]["source_url_update_template_rows"], 2)
        self.assertEqual(report["summary"]["source_url_update_search_hint_rows"], 1)
        self.assertEqual(report["summary"]["source_url_update_missing_search_hint_rows"], 1)
        self.assertEqual(report["summary"]["source_url_update_fallback_web_search_rows"], 1)
        self.assertEqual(report["summary"]["source_url_update_any_search_hint_rows"], 2)
        self.assertEqual(report["summary"]["source_url_update_missing_any_search_hint_rows"], 0)
        self.assertEqual(report["summary"]["source_url_candidate_status_counts"], [])
        self.assertEqual(report["summary"]["source_url_review_lane_counts"], [])
        self.assertEqual(report["summary"]["primary_review_url_rows"], 2)
        self.assertEqual(report["summary"]["primary_review_url_missing_rows"], 0)
        self.assertEqual(
            dict(report["summary"]["primary_review_url_kind_counts"]),
            {"source_search_url": 1, "fallback_web_search": 1},
        )
        self.assertEqual(
            report["summary"]["first_primary_review_url"],
            report["batches"][0]["items"][0]["primary_review_url"],
        )
        self.assertEqual(report["summary"]["first_primary_review_url_kind"], "fallback_web_search")
        self.assertEqual(report["summary"]["representative_image_review_required_rows"], 0)
        self.assertEqual(report["summary"]["representative_candidate_status_counts"], [])
        self.assertEqual(report["summary"]["image_url_ready_rows"], 0)
        self.assertEqual(report["summary"]["blocked_before_image_import_rows"], 2)
        self.assertEqual(report["summary"]["download_ready_after_manual_image_url_rows"], 2)
        self.assertEqual(report["summary"]["suggested_local_image_path_rows"], 2)
        self.assertEqual(report["summary"]["workstream_count"], 1)
        self.assertEqual(report["summary"]["source_url_update_workstream_count"], 1)
        self.assertEqual(report["summary"]["source_url_update_work_order_count"], 1)
        self.assertEqual(report["summary"]["source_url_update_template_batch_count"], 1)
        self.assertEqual(report["summary"]["next_source_url_review_batch_rows"], 2)
        self.assertEqual(report["summary"]["next_source_url_review_batch_store_count"], 1)
        self.assertEqual(report["summary"]["next_source_url_review_batch_primary_review_url_rows"], 2)
        self.assertEqual(
            dict(report["summary"]["next_source_url_review_batch_primary_review_url_kind_counts"]),
            {"source_search_url": 1, "fallback_web_search": 1},
        )
        self.assertEqual(report["summary"]["next_representative_image_review_batch_rows"], 0)
        self.assertEqual(report["summary"]["next_representative_image_review_batch_store_count"], 0)
        self.assertEqual(report["summary"]["next_representative_image_review_batch_primary_review_url_rows"], 0)
        self.assertEqual(report["summary"]["next_representative_image_review_batch_local_path_rows"], 0)
        self.assertEqual(
            report["summary"]["next_representative_image_review_batch_primary_review_url_kind_counts"],
            [],
        )
        self.assertEqual(
            report["summary"]["next_representative_image_review_batch_candidate_status_counts"],
            [],
        )
        self.assertEqual(report["summary"]["representative_image_review_workstream_count"], 0)
        self.assertEqual(report["summary"]["action_batch_count"], 1)
        self.assertEqual(
            report["attachment_readiness"],
            {
                "row_count": 2,
                "local_image_download_instruction_ready_rows": 2,
                "suggested_local_image_path_rows": 2,
                "primary_review_url_rows": 2,
                "primary_review_url_missing_rows": 0,
                "blocked_by_source_url_rows": 2,
                "blocked_by_representative_review_rows": 0,
                "image_url_review_ready_rows": 0,
                "blocked_before_image_import_rows": 2,
                "can_import_image_urls_now_rows": 0,
                "download_ready_after_manual_image_url_rows": 2,
                "readiness_lane_counts": [
                    ["source_url_replacement_first", 2],
                    ["representative_image_candidate_review", 0],
                    ["image_url_review_ready", 0],
                ],
                "manual_confirmation_required": True,
                "auto_apply_enabled": False,
            },
        )
        self.assertEqual(
            report["execution_readiness"]["status"],
            "source_url_replacement_required",
        )
        self.assertFalse(report["execution_readiness"]["can_auto_apply_catalog_changes"])
        self.assertFalse(report["execution_readiness"]["can_import_image_urls_now"])
        self.assertEqual(report["execution_readiness"]["blocked_before_image_import_rows"], 2)
        self.assertEqual(
            report["execution_readiness"]["recommended_first_batch_id"],
            "image-attachment-action-001",
        )
        self.assertEqual(
            report["execution_readiness"]["evidence"][
                "source_url_replacement_first_primary_review_url"
            ],
            report["batches"][0]["items"][0]["primary_review_url"],
        )
        self.assertEqual(
            report["execution_readiness"]["evidence"][
                "source_url_replacement_first_primary_review_url_kind"
            ],
            "fallback_web_search",
        )
        self.assertEqual(len(report["next_operator_actions"]), 1)
        self.assertEqual(
            report["next_operator_actions"][0]["lane"],
            "source_url_replacement_first",
        )
        self.assertEqual(
            report["next_operator_actions"][0]["first_primary_review_url"],
            report["batches"][0]["items"][0]["primary_review_url"],
        )
        self.assertEqual(
            report["next_operator_actions"][0]["first_primary_review_url_kind"],
            "fallback_web_search",
        )
        self.assertEqual(
            report["next_operator_actions"][0]["status"],
            "manual_source_url_confirmation_required",
        )
        self.assertEqual(report["next_operator_actions"][0]["candidate_status_counts"], [])
        self.assertEqual(report["next_operator_actions"][0]["candidate_review_lane_counts"], [])
        self.assertEqual(report["workstreams"][0]["source_store"], "Stellive Store")
        self.assertEqual(report["workstreams"][0]["next_batch_id"], "image-attachment-action-001")
        self.assertEqual(report["workstreams"][0]["source_url_update_template_rows"], 2)
        self.assertEqual(
            report["workstreams"][0]["attachment_readiness"]["blocked_by_source_url_rows"],
            2,
        )
        self.assertEqual(report["workstreams"][0]["review_summary"]["review_lane"], "source_url_replacement_first")
        self.assertEqual(
            report["workstreams"][0]["review_summary"]["attachment_readiness"][
                "download_ready_after_manual_image_url_rows"
            ],
            2,
        )
        self.assertIn(
            "generic_storefront_source_url",
            report["workstreams"][0]["review_summary"]["primary_blockers"],
        )
        self.assertEqual(report["next_actions"][0]["next_batch_id"], "image-attachment-action-001")
        self.assertEqual(
            report["next_actions"][0]["first_primary_review_url"],
            report["batches"][0]["items"][0]["primary_review_url"],
        )
        self.assertEqual(report["next_actions"][0]["first_primary_review_url_kind"], "fallback_web_search")
        self.assertEqual(report["batches"][0]["workflow"], "replace_generic_source_then_extract_image")
        self.assertEqual(report["batches"][0]["primary_review_url_rows"], 2)
        self.assertEqual(
            report["batches"][0]["attachment_readiness"]["blocked_before_image_import_rows"],
            2,
        )
        self.assertEqual(
            report["batches"][0]["first_primary_review_url"],
            report["batches"][0]["items"][0]["primary_review_url"],
        )
        self.assertEqual(
            report["batches"][0]["first_primary_review_url_kind"],
            "fallback_web_search",
        )
        self.assertEqual([item["catalog_index"] for item in report["batches"][0]["items"]], [1, 2])
        self.assertEqual(report["batches"][0]["items"][0]["review_lane"], "source_url_replacement_first")
        self.assertEqual(
            report["batches"][0]["items"][0]["primary_review_url"],
            report["batches"][0]["items"][0]["first_fallback_web_search_url"],
        )
        self.assertEqual(
            report["batches"][0]["items"][0]["primary_review_url_kind"],
            "fallback_web_search",
        )
        self.assertTrue(report["batches"][0]["items"][0]["source_url_update_required"])
        self.assertFalse(report["batches"][0]["items"][0]["image_url_ready"])
        self.assertEqual(
            report["batches"][0]["items"][0]["suggested_local_image_path"],
            "assets/catalog_images/catalog_1.webp",
        )
        self.assertEqual(
            report["batches"][0]["items"][0]["catalog_field_import_template"]["suggested_local_image_path"],
            "assets/catalog_images/catalog_1.webp",
        )
        self.assertEqual(
            report["batches"][0]["items"][0]["local_image_download_instruction"]["target_public_asset_path"],
            "assets/assets/catalog_images/catalog_1.webp",
        )
        self.assertEqual(
            report["batches"][0]["items"][0]["image_import_blockers"],
            [
                "generic_storefront_source_url",
                "missing_exact_product_detail_url",
                "missing_product_page_image_url",
            ],
        )
        self.assertIn(
            "Find the exact product detail page",
            report["batches"][0]["items"][0]["manual_confirmation_requirements"][0],
        )
        source_template = report["batches"][0]["items"][0]["source_url_import_template"]
        self.assertEqual(source_template["field"], "source_url")
        self.assertEqual(source_template["manual_value"], "")
        self.assertEqual(source_template["candidate_source_url"], "")
        self.assertEqual(source_template["current_source_url"], "https://example.com/shop")
        self.assertFalse(source_template["manual_confirmed"])
        self.assertIn(
            "google.com/search",
            report["batches"][0]["items"][0]["first_fallback_web_search_url"],
        )
        self.assertIn(
            "site%3Aexample.com",
            report["batches"][0]["items"][0]["first_fallback_web_search_url"],
        )
        self.assertEqual(
            source_template["first_fallback_web_search_url"],
            report["batches"][0]["items"][0]["first_fallback_web_search_url"],
        )
        self.assertEqual(
            report["batches"][0]["items"][1]["source_search_url"],
            "https://fanding.kr/@stellive/shop?keyword=Badge",
        )
        self.assertEqual(
            report["batches"][0]["items"][1]["primary_review_url"],
            "https://fanding.kr/@stellive/shop?keyword=Badge",
        )
        self.assertEqual(
            report["batches"][0]["items"][1]["primary_review_url_kind"],
            "source_search_url",
        )
        self.assertEqual(
            report["batches"][0]["items"][1]["source_url_import_template"]["source_search_url"],
            "https://fanding.kr/@stellive/shop?keyword=Badge",
        )
        self.assertEqual(
            report["batches"][0]["items"][1]["catalog_field_import_template"]["source_search_url"],
            "https://fanding.kr/@stellive/shop?keyword=Badge",
        )
        self.assertEqual(
            report["workstreams"][0]["sample_items"][0]["suggested_local_image_path"],
            "assets/catalog_images/catalog_1.webp",
        )
        self.assertEqual(
            report["batches"][0]["items"][0]["required_before_image_import"],
            [
                "confirm_exact_product_source_url",
                "replace_generic_source_url",
                "confirm_product_page_image_url",
            ],
        )
        work_order = report["source_url_update_work_order"][0]
        self.assertEqual(work_order["source_store"], "Stellive Store")
        self.assertEqual(work_order["row_count"], 2)
        self.assertEqual(work_order["source_url_update_template_rows"], 2)
        self.assertEqual(work_order["fallback_web_search_url_rows"], 1)
        self.assertEqual(work_order["current_source_urls"], [{"source_url": "https://example.com/shop", "rows": 2}])
        self.assertEqual(work_order["sample_items"][0]["catalog_index"], 2)
        self.assertEqual(
            work_order["sample_items"][0]["suggested_local_image_path"],
            "assets/catalog_images/catalog_2.webp",
        )
        self.assertEqual(
            work_order["sample_items"][0]["local_image_download_instruction"]["target_local_image_path"],
            "assets/catalog_images/catalog_2.webp",
        )
        self.assertEqual(
            work_order["sample_items"][0]["source_url_import_template"]["source_search_url"],
            "https://fanding.kr/@stellive/shop?keyword=Badge",
        )
        self.assertEqual(
            work_order["sample_items"][0]["primary_review_url"],
            "https://fanding.kr/@stellive/shop?keyword=Badge",
        )
        self.assertEqual(work_order["sample_items"][0]["primary_review_url_kind"], "source_search_url")
        self.assertEqual(
            work_order["sample_items"][0]["source_url_import_template"]["field"],
            "source_url",
        )
        self.assertIn(
            "first_fallback_web_search_url",
            work_order["recommended_review_order"][1],
        )
        self.assertIn("exact product detail page", work_order["recommended_review_order"][2])
        flat_template = report["source_url_update_template"]
        self.assertEqual([row["row_index"] for row in flat_template], [2, 1])
        self.assertEqual(flat_template[0]["field"], "source_url")
        self.assertEqual(flat_template[0]["manual_value"], "")
        self.assertEqual(
            flat_template[0]["source_search_url"],
            "https://fanding.kr/@stellive/shop?keyword=Badge",
        )
        self.assertEqual(flat_template[1]["first_fallback_web_search_url"], report["batches"][0]["items"][0]["first_fallback_web_search_url"])
        template_batch = report["source_url_update_template_batches"][0]
        self.assertEqual(template_batch["template_batch_id"], "source-url-update-template-001")
        self.assertEqual(template_batch["source_store"], "Stellive Store")
        self.assertEqual(template_batch["row_count"], 2)
        self.assertEqual(template_batch["official_search_url_rows"], 1)
        self.assertEqual(template_batch["fallback_web_search_url_rows"], 1)
        self.assertEqual([row["row_index"] for row in template_batch["rows"]], [2, 1])
        self.assertEqual([row["row_index"] for row in report["next_source_url_review_batch"]], [2, 1])
        self.assertFalse(report["next_source_url_review_batch"][0]["manual_confirmed"])
        self.assertEqual(
            report["next_source_url_review_batch"][0]["primary_review_url"],
            "https://fanding.kr/@stellive/shop?keyword=Badge",
        )
        self.assertIn(
            "exact product detail page",
            report["next_source_url_review_batch"][0]["operator_checklist"][1],
        )
        self.assertEqual(
            report["next_source_url_review_batch"][0]["unblocks"],
            "image_url_extraction_and_attachment_review",
        )
        self.assertEqual(
            report["workstreams"][0]["review_summary"]["first_primary_review_url"],
            report["batches"][0]["first_primary_review_url"],
        )
        self.assertEqual(report["workstreams"][0]["review_summary"]["primary_review_url_rows"], 2)

    def test_max_batches_caps_published_batches_not_actionable_summary(self) -> None:
        enrichment = {
            "groups": [
                {
                    "workflow": "review_gotouchi_official_candidates",
                    "source_store": f"Store {index}",
                    "missing_image_rows": 1,
                    "sample_items": [
                        {
                            "catalog_index": index,
                            "name_ko": f"Item {index}",
                            "catalog_field_import_template": {"field": "image_url"},
                        }
                    ],
                }
                for index in range(3)
            ]
        }
        representative_candidates = {
            "items": [
                {
                    "catalog_index": index,
                    "candidate_status": "motif_only_type_mismatch",
                    "top_candidates": [
                        {
                            "image_url": f"https://example.com/candidate-{index}.png",
                            "alt": f"Candidate {index}",
                            "type": "wrong_type",
                            "type_match": False,
                        }
                    ],
                }
                for index in range(3)
            ]
        }

        report = queue.build_report(
            enrichment,
            representative_candidates=representative_candidates,
            max_batches=1,
            batch_size=1,
        )

        self.assertEqual(report["summary"]["actionable_image_rows"], 3)
        self.assertEqual(report["summary"]["queued_image_rows"], 1)
        self.assertEqual(report["summary"]["unqueued_actionable_image_rows"], 2)
        self.assertEqual(report["summary"]["sample_queue_coverage"], 0.3333)
        self.assertEqual(report["summary"]["representative_image_review_required_rows"], 3)
        self.assertEqual(
            report["summary"]["representative_candidate_status_counts"],
            [["motif_only_type_mismatch", 3]],
        )
        self.assertEqual(report["summary"]["source_url_update_template_rows"], 0)
        self.assertEqual(report["summary"]["source_url_update_work_order_count"], 0)
        self.assertEqual(report["summary"]["source_url_update_template_batch_count"], 0)
        self.assertEqual(report["summary"]["next_source_url_review_batch_rows"], 0)
        self.assertEqual(report["summary"]["next_representative_image_review_batch_rows"], 3)
        self.assertEqual(report["summary"]["next_representative_image_review_batch_store_count"], 3)
        self.assertEqual(report["summary"]["next_representative_image_review_batch_primary_review_url_rows"], 3)
        self.assertEqual(report["summary"]["next_representative_image_review_batch_local_path_rows"], 3)
        self.assertEqual(
            dict(report["summary"]["next_representative_image_review_batch_primary_review_url_kind_counts"]),
            {"fallback_web_search": 3},
        )
        self.assertEqual(
            report["summary"]["next_representative_image_review_batch_candidate_status_counts"],
            [["motif_only_type_mismatch", 3]],
        )
        self.assertEqual(report["summary"]["action_batch_count"], 1)
        self.assertEqual(report["summary"]["workstream_count"], 1)
        self.assertEqual(report["summary"]["representative_image_review_workstream_count"], 1)
        self.assertEqual(
            report["execution_readiness"]["status"],
            "representative_image_review_required",
        )
        self.assertEqual(report["execution_readiness"]["blocked_before_image_import_rows"], 3)
        self.assertEqual(report["next_operator_actions"][0]["lane"], "representative_image_candidate_review")
        self.assertEqual(
            report["next_operator_actions"][0]["status"],
            "manual_variant_confirmation_required",
        )
        self.assertEqual(
            report["next_operator_actions"][0]["representative_candidate_status_counts"],
            [["motif_only_type_mismatch", 3]],
        )
        self.assertEqual(report["next_actions"][1]["next_batch_id"], "image-attachment-action-001")
        self.assertEqual(
            report["batches"][0]["items"][0]["review_lane"],
            "representative_image_candidate_review",
        )
        self.assertEqual(
            report["batches"][0]["items"][0]["representative_candidate_status"],
            "motif_only_type_mismatch",
        )
        self.assertEqual(
            report["batches"][0]["items"][0]["representative_top_candidates"][0]["alt"],
            "Candidate 0",
        )
        self.assertIn(
            "product_type_confirmation_required",
            report["batches"][0]["items"][0]["image_import_blockers"],
        )
        representative_review = report["next_representative_image_review_batch"][0]
        self.assertFalse(representative_review["manual_confirmed"])
        self.assertEqual(representative_review["catalog_index"], 0)
        self.assertEqual(representative_review["source_store"], "Store 0")
        self.assertEqual(representative_review["name_ko"], "Item 0")
        self.assertEqual(
            representative_review["primary_review_url"],
            report["batches"][0]["items"][0]["first_fallback_web_search_url"],
        )
        self.assertEqual(representative_review["primary_review_url_kind"], "fallback_web_search")
        self.assertEqual(
            representative_review["suggested_local_image_path"],
            "assets/catalog_images/catalog_0.webp",
        )
        self.assertEqual(
            representative_review["representative_candidate_status"],
            "motif_only_type_mismatch",
        )
        self.assertEqual(
            representative_review["representative_top_candidates"][0]["image_url"],
            "https://example.com/candidate-0.png",
        )
        self.assertEqual(representative_review["manual_image_url"], "")
        self.assertIn(
            "Confirm character, regional motif, product type, and variant.",
            representative_review["operator_checklist"],
        )
        self.assertEqual(
            representative_review["unblocks"],
            "manual_catalog_image_url_import",
        )
        self.assertFalse(representative_review["auto_apply_enabled"])

    def test_catalog_images_are_skipped_from_action_items(self) -> None:
        enrichment = {
            "groups": [
                {
                    "workflow": "review_gotouchi_official_candidates",
                    "source_store": "ご当地ちいかわ 공식(API)",
                    "missing_image_rows": 2,
                    "sample_items": [
                        {"catalog_index": 1, "name_ko": "Already cached"},
                        {"catalog_index": 2, "name_ko": "Still missing"},
                    ],
                }
            ]
        }
        catalog = {
            "items": [
                {"catalog_index": 1, "local_image_path": "assets/catalog_images/cached.webp"},
                {"catalog_index": 2},
            ]
        }

        report = queue.build_report(enrichment, catalog, max_batches=10, batch_size=20)

        self.assertEqual(report["summary"]["actionable_image_rows"], 2)
        self.assertEqual(report["summary"]["sample_action_item_rows"], 1)
        self.assertEqual(report["summary"]["queued_image_rows"], 1)
        self.assertEqual(report["summary"]["skipped_already_has_image_rows"], 1)
        self.assertEqual(report["batches"][0]["items"][0]["catalog_index"], 2)


if __name__ == "__main__":
    unittest.main()
