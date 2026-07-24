from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_deduplication_action_queue_public as queue


class BuildDeduplicationActionQueuePublicTest(unittest.TestCase):
    def test_build_report_keeps_only_high_and_medium_confidence_groups(self) -> None:
        review_batches = {
            "batches": [
                {
                    "identity_checklist": ["compare_product_images_for_same_sellable_item"],
                    "groups": [
                        {
                            "key_type": "barcode",
                            "key": "111",
                            "review_priority": 10,
                            "review_risk": "strong_identity_review",
                            "review_confidence": "high_review_confidence",
                            "keep_catalog_index": 1,
                            "drop_catalog_indexes": [2],
                            "merge_blockers": ["multi_store_variant_or_retailer_review"],
                            "dedupe_decision_template": {"decision": "review_required"},
                            "rows": [
                                {
                                    "catalog_index": 1,
                                    "name_ko": "Sample goods",
                                    "source_store": "Official",
                                    "category": "figure",
                                    "barcode": "111",
                                    "source_url": "https://example.test/item",
                                    "image_url": "https://example.test/item.jpg",
                                    "richness": 9,
                                },
                                {
                                    "catalog_index": 2,
                                    "name_ko": "Sample goods resale",
                                    "source_store": "Retailer",
                                    "category": "figure",
                                    "barcode": "111",
                                    "source_url": "https://example.test/item",
                                    "image_url": "https://example.test/item.jpg",
                                    "richness": 7,
                                },
                            ],
                        },
                        {
                            "key_type": "source_url",
                            "key": "https://example.test/item",
                            "review_priority": 20,
                            "review_risk": "source_identity_review",
                            "review_confidence": "medium_review_confidence",
                            "keep_catalog_index": 3,
                            "drop_catalog_indexes": [4],
                        },
                        {
                            "key_type": "barcode",
                            "key": "222",
                            "review_priority": 40,
                            "review_risk": "variant_risk_review",
                            "review_confidence": "variant_caution",
                            "keep_catalog_index": 5,
                            "drop_catalog_indexes": [6],
                        },
                    ],
                }
            ]
        }

        report = queue.build_report(review_batches, max_groups=10, batch_size=10)

        self.assertEqual(report["summary"]["actionable_groups"], 2)
        self.assertEqual(report["summary"]["queued_groups"], 2)
        self.assertEqual(report["summary"]["unqueued_actionable_groups"], 0)
        self.assertEqual(report["summary"]["queue_coverage"], 1.0)
        self.assertEqual(report["summary"]["action_batch_count"], 1)
        self.assertFalse(report["summary"]["auto_delete_enabled"])
        self.assertEqual(report["summary"]["completion_readiness_status"], "manual_keep_drop_confirmation_required")
        self.assertEqual(report["summary"]["auto_merge_ready_groups"], 0)
        self.assertEqual(report["summary"]["auto_delete_ready_groups"], 0)
        self.assertEqual(report["summary"]["explicit_keep_drop_required_groups"], 2)
        self.assertEqual(report["summary"]["primary_review_url_groups"], 1)
        self.assertEqual(report["summary"]["first_primary_review_url"], "https://example.test/item")
        self.assertEqual(
            dict(report["summary"]["by_primary_review_url_kind"]),
            {"keep_source_url": 1},
        )
        self.assertEqual(report["completion_readiness"]["status"], "manual_keep_drop_confirmation_required")
        self.assertEqual(report["completion_readiness"]["next_safe_phase"], "record_manual_keep_drop_decisions")
        self.assertEqual(report["summary"]["dedupe_safety_gate_status"], "blocked_until_manual_review")
        self.assertEqual(report["summary"]["dedupe_safety_gate_blocked_reason_count"], 2)
        self.assertEqual(report["dedupe_safety_gate"]["manual_decision_required_groups"], 2)
        self.assertEqual(report["dedupe_safety_gate"]["auto_merge_ready_groups"], 0)
        self.assertEqual(report["dedupe_safety_gate"]["auto_delete_ready_groups"], 0)
        self.assertIn(
            "explicit_manual_keep_drop_confirmation_required",
            report["completion_readiness"]["blocked_reasons"],
        )
        self.assertFalse(report["automation_policy"]["auto_merge"])
        self.assertEqual(dict(report["summary"]["by_review_confidence"]), {
            "high_review_confidence": 1,
            "medium_review_confidence": 1,
        })
        self.assertEqual(dict(report["summary"]["excluded_review_confidence"]), {"variant_caution": 1})
        self.assertEqual(
            dict(report["summary"]["by_manual_review_required_reason"])[
                "manual_keep_drop_confirmation_required"
            ],
            2,
        )
        self.assertEqual(
            report["automation_policy"]["blocked_until"],
            "explicit_manual_keep_drop_decision_confirmed",
        )
        self.assertIn(
            "same_sellable_product_identity_confirmed",
            report["automation_policy"]["required_evidence"],
        )
        self.assertIn("variant_caution", report["automation_policy"]["protected_lanes"])
        keys = [group["key"] for group in report["batches"][0]["groups"]]
        self.assertEqual(keys, ["111", "https://example.test/item"])
        self.assertEqual(
            report["batches"][0]["next_machine_step"],
            "record_manual_dedupe_decisions",
        )
        self.assertEqual(
            report["automation_policy"]["manual_confirmation_template"],
            "server/catalog_dedupe_confirmed_decisions.template.json",
        )
        self.assertEqual(
            report["automation_policy"]["import_tool"],
            "tools/import_confirmed_dedupe_decisions.py",
        )
        self.assertEqual(
            report["batches"][0]["unblocks_when"],
            "explicit_manual_keep_drop_decision_confirmed",
        )
        self.assertEqual(report["batches"][0]["primary_review_url_groups"], 1)
        self.assertEqual(report["batches"][0]["first_primary_review_url"], "https://example.test/item")
        self.assertEqual(
            report["batches"][0]["groups"][0]["confirmed_queue"],
            "server/catalog_dedupe_confirmed_decisions.json",
        )
        first_group = report["batches"][0]["groups"][0]
        self.assertEqual(first_group["primary_review_url"], "https://example.test/item")
        self.assertEqual(first_group["primary_review_url_kind"], "keep_source_url")
        self.assertEqual(first_group["review_url_count"], 2)
        self.assertEqual(first_group["keep_basis"]["basis"], "richest_or_equal_catalog_row")
        self.assertEqual(first_group["keep_basis"]["keep_richness"], 9)
        self.assertTrue(first_group["keep_basis"]["keep_has_image"])
        self.assertEqual(
            first_group["auto_merge_blocked_reason"],
            "explicit_manual_keep_drop_confirmation_required",
        )
        self.assertTrue(first_group["row_comparison_summary"]["name_differs"])
        self.assertTrue(first_group["row_comparison_summary"]["multi_store"])
        self.assertIn("name_differs", first_group["confirmation_risk_flags"])
        self.assertIn("multi_store_review", first_group["confirmation_risk_flags"])
        self.assertIn("name_differs", first_group["manual_review_required_reasons"])
        self.assertIn(
            "multi_store_variant_or_retailer_review",
            first_group["manual_review_required_reasons"],
        )

    def test_max_groups_caps_published_queue_only(self) -> None:
        review_batches = {
            "batches": [
                {
                    "groups": [
                        {
                            "key_type": "barcode",
                            "key": str(index),
                            "review_priority": 10,
                            "review_confidence": "high_review_confidence",
                        }
                        for index in range(5)
                    ]
                }
            ]
        }

        report = queue.build_report(review_batches, max_groups=3, batch_size=2)

        self.assertEqual(report["summary"]["actionable_groups"], 5)
        self.assertEqual(report["summary"]["queued_groups"], 3)
        self.assertEqual(report["summary"]["unqueued_actionable_groups"], 2)
        self.assertEqual(report["summary"]["queue_coverage"], 0.6)
        self.assertEqual(report["summary"]["action_batch_count"], 2)

    def test_ichiban_reissue_candidates_are_excluded_from_action_queue(self) -> None:
        review_batches = {
            "batches": [
                {
                    "groups": [
                        {
                            "key_type": "barcode",
                            "key": "ichiban-shared-barcode",
                            "review_priority": 10,
                            "review_risk": "strong_identity_review",
                            "review_confidence": "high_review_confidence",
                            "rows": [
                                {
                                    "catalog_index": 101,
                                    "name_ko": "一番くじ Sample - A賞 Figure",
                                    "source_url": "https://1kuji.com/products/sample",
                                    "barcode": "4900000000001",
                                },
                                {
                                    "catalog_index": 102,
                                    "name_ko": "一番くじ Sample - A賞 Figure",
                                    "source_url": "https://1kuji.com/products/sample2",
                                    "barcode": "4900000000001",
                                },
                            ],
                        },
                        {
                            "key_type": "barcode",
                            "key": "ordinary-shared-barcode",
                            "review_priority": 10,
                            "review_risk": "strong_identity_review",
                            "review_confidence": "high_review_confidence",
                            "rows": [
                                {"catalog_index": 201, "barcode": "4900000000002"},
                                {"catalog_index": 202, "barcode": "4900000000002"},
                            ],
                        },
                    ]
                }
            ]
        }
        ichiban_policy_audit = {
                "probable_reissue_review_groups": [
                    {
                        "has_reissue_signal": True,
                        "normalized_name": "一番くじ Sample - A賞 Figure",
                        "sample_rows": [
                            {
                                "catalog_index": 101,
                            "series_name": "一番くじ Sample",
                            "sub_series": "ラストワン賞",
                            "name_ja": "ラストワン賞 Sample Figure",
                            "official_price_jpy": 0,
                            "source_url": "https://1kuji.com/products/sample",
                        },
                        {
                            "catalog_index": 102,
                            "series_name": "一番くじ Sample",
                            "sub_series": "ラストワン賞",
                            "name_ja": "ラストワン賞 Sample Figure",
                            "official_price_jpy": 0,
                            "source_url": "https://1kuji.com/products/sample2",
                            },
                        ],
                    }
                ]
        }

        report = queue.build_report(
            review_batches,
            max_groups=10,
            batch_size=10,
            ichiban_policy_audit=ichiban_policy_audit,
        )

        self.assertEqual(report["summary"]["actionable_groups"], 1)
        self.assertEqual(report["summary"]["queued_groups"], 1)
        self.assertEqual(
            dict(report["summary"]["excluded_review_confidence"])["ichiban_reissue_protection"],
            1,
        )
        self.assertEqual(report["summary"]["ichiban_reissue_protected_groups"], 1)
        self.assertEqual(report["summary"]["ichiban_reissue_protected_rows"], 2)
        self.assertEqual(report["summary"]["ichiban_reissue_review_groups"], 0)
        self.assertEqual(report["summary"]["ichiban_probable_reissue_review_groups"], 0)
        self.assertEqual(report["batches"][0]["groups"][0]["key"], "ordinary-shared-barcode")
        self.assertEqual(len(report["ichiban_reissue_review_lane"]), 1)
        self.assertEqual(
            report["ichiban_reissue_review_lane"][0]["review_state"],
            "probable_reissue_manual_confirmation_required",
        )
        self.assertEqual(report["summary"]["ichiban_reissue_work_order_rows"], 1)
        self.assertEqual(report["summary"]["ichiban_reissue_decision_template_rows"], 1)
        self.assertEqual(report["summary"]["ichiban_reissue_campaign_work_order_rows"], 1)
        self.assertEqual(report["summary"]["ichiban_reissue_campaign_decision_template_rows"], 1)
        self.assertEqual(report["summary"]["ichiban_reissue_work_orders_with_evidence_urls"], 1)
        self.assertEqual(report["summary"]["ichiban_reissue_campaign_work_orders_with_evidence_urls"], 1)
        self.assertEqual(
            report["summary"]["ichiban_reissue_first_evidence_url"],
            "https://1kuji.com/products/sample",
        )
        self.assertEqual(report["summary"]["ichiban_reissue_manual_confirmed_rows"], 0)
        self.assertEqual(report["summary"]["completion_readiness_status"], "ichiban_reissue_review_required")
        self.assertEqual(report["summary"]["dedupe_safety_gate_status"], "blocked_until_manual_review")
        self.assertEqual(report["dedupe_safety_gate"]["manual_decision_required_groups"], 1)
        self.assertEqual(report["dedupe_safety_gate"]["protected_reissue_overlap_groups"], 1)
        self.assertEqual(report["completion_readiness"]["status"], "ichiban_reissue_review_required")
        self.assertEqual(
            report["completion_readiness"]["next_safe_phase"],
            "verify_ichiban_campaign_pages_before_dedupe",
        )
        self.assertIn(
            "ichiban_reissue_manual_confirmation_required",
            report["completion_readiness"]["blocked_reasons"],
        )
        self.assertEqual(len(report["ichiban_reissue_campaign_work_order"]), 1)
        campaign_order = report["ichiban_reissue_campaign_work_order"][0]
        self.assertEqual(campaign_order["item_work_order_count"], 1)
        self.assertEqual(campaign_order["catalog_row_count"], 2)
        self.assertEqual(
            campaign_order["decision_template"]["decision_options"][0],
            "campaign_pair_reissue_keep_all_separate",
        )
        self.assertEqual(
            report["ichiban_reissue_work_order"][0]["review_state"],
            "ichiban_reissue_identity_confirmation_required",
        )
        self.assertEqual(
            report["ichiban_reissue_work_order"][0]["first_evidence_url"],
            "https://1kuji.com/products/sample",
        )
        self.assertEqual(report["ichiban_reissue_work_order"][0]["evidence_url_count"], 2)
        self.assertEqual(
            campaign_order["first_evidence_url"],
            "https://1kuji.com/products/sample",
        )
        self.assertEqual(campaign_order["evidence_url_count"], 2)
        self.assertIn(
            "reissue_or_campaign_variant_keep_separate",
            report["ichiban_reissue_work_order"][0]["decision_template"]["decision_options"],
        )
        self.assertIn(
            "ichiban_reissue_manual_confirmation_required",
            report["ichiban_reissue_review_lane"][0]["merge_blockers"],
        )
        identity_summary = report["ichiban_reissue_work_order"][0]["prize_identity_summary"]
        self.assertEqual(identity_summary["prize_labels"], ["ラストワン賞"])
        self.assertEqual(identity_summary["campaign_titles"], ["一番くじ Sample"])
        self.assertEqual(identity_summary["prize_ranks"], ["ラストワン賞"])
        self.assertEqual(identity_summary["prize_item_names"], ["Sample Figure"])
        self.assertEqual(
            identity_summary["identity_labels"],
            ["一番くじ Sample / ラストワン賞 / Sample Figure"],
        )
        self.assertEqual(identity_summary["official_price_jpy_values"], [0])
        self.assertEqual(identity_summary["zero_price_exception_rows"], 2)
        self.assertTrue(identity_summary["zero_price_exception_policy_pass"])
        self.assertIn(
            "prize_rank_or_sub_series",
            identity_summary["identity_fields_required"],
        )
        self.assertIn(
            "variant_name_when_same_rank_has_multiple_kinds",
            identity_summary["identity_fields_required"],
        )
        self.assertEqual(
            report["ichiban_reissue_work_order"][0]["sample_rows"][0]["campaign_title"],
            "一番くじ Sample",
        )
        self.assertEqual(
            report["ichiban_reissue_work_order"][0]["sample_rows"][0]["prize_rank"],
            "ラストワン賞",
        )
        self.assertEqual(
            report["ichiban_reissue_work_order"][0]["sample_rows"][0]["prize_item_name"],
            "Sample Figure",
        )
        self.assertTrue(
            report["ichiban_reissue_work_order"][0]["zero_price_exception_policy"][
                "last_one_or_double_chance_rows_must_be_zero_jpy"
            ]
        )
        campaign_comparison = report["ichiban_reissue_work_order"][0]["campaign_url_comparison"]
        self.assertEqual(campaign_comparison["campaign_slugs"], ["sample", "sample2"])
        self.assertEqual(campaign_comparison["campaign_slug_families"], ["sample"])
        self.assertEqual(campaign_comparison["numeric_suffixes"], ["2"])
        self.assertTrue(campaign_comparison["has_numbered_campaign_suffixes"])
        self.assertTrue(campaign_comparison["likely_same_campaign_family_reissue"])
        self.assertIn("reissue/campaign-wave", campaign_comparison["dedupe_risk_note"])

    def test_ichiban_reissue_policy_counts_are_reported_even_without_queue_overlap(self) -> None:
        report = queue.build_report(
            {"batches": []},
            ichiban_policy_audit={
                "summary": {
                    "repeated_name_different_source_groups": 46,
                    "repeated_name_different_source_review_catalog_item_rows": 92,
                    "probable_reissue_review_groups": 20,
                },
                "probable_reissue_review_groups": [
                    {
                        "has_reissue_signal": True,
                        "sample_rows": [
                            {
                                "catalog_index": 1,
                                "source_url": "https://1kuji.com/products/sample",
                            },
                            {
                                "catalog_index": 2,
                                "source_url": "https://1kuji.com/products/sample2",
                            },
                        ],
                    }
                ],
            },
        )

        self.assertEqual(report["summary"]["actionable_groups"], 0)
        self.assertEqual(report["summary"]["ichiban_reissue_review_groups"], 46)
        self.assertEqual(report["summary"]["ichiban_reissue_review_rows"], 92)
        self.assertEqual(report["summary"]["ichiban_probable_reissue_review_groups"], 20)
        self.assertEqual(report["summary"]["ichiban_probable_reissue_sample_rows"], 2)
        self.assertEqual(report["summary"]["ichiban_reissue_protected_groups"], 0)
        self.assertEqual(report["summary"]["completion_readiness_status"], "ichiban_reissue_review_required")
        self.assertEqual(report["summary"]["dedupe_safety_gate_status"], "blocked_until_manual_review")
        self.assertEqual(report["dedupe_safety_gate"]["manual_decision_required_groups"], 0)
        self.assertEqual(report["dedupe_safety_gate"]["ichiban_reissue_manual_review_groups"], 46)
        self.assertEqual(report["completion_readiness"]["ichiban_reissue_work_order_rows"], 1)
        self.assertEqual(len(report["ichiban_reissue_review_lane"]), 1)
        self.assertEqual(len(report["ichiban_reissue_work_order"]), 1)
        self.assertEqual(len(report["ichiban_reissue_campaign_work_order"]), 1)
        self.assertEqual(
            report["ichiban_reissue_work_order"][0]["next_machine_step"],
            "compare_campaign_pages_then_record_reissue_or_duplicate_decision",
        )
        self.assertFalse(report["ichiban_reissue_work_order"][0]["decision_template"]["manual_confirmed"])
        self.assertEqual(
            report["ichiban_reissue_review_lane"][0]["next_machine_step"],
            "verify_ichiban_campaign_pages_before_dedupe",
        )

    def test_ichiban_reissue_campaign_work_order_groups_shared_url_pairs(self) -> None:
        review_batches = {"batches": []}
        ichiban_policy_audit = {
            "probable_reissue_review_groups": [
                {
                    "normalized_name": "一番くじ Sample - A賞 Figure",
                    "has_reissue_signal": True,
                    "sample_rows": [
                        {
                            "catalog_index": 101,
                            "sub_series": "A賞",
                            "name_ja": "A賞 Figure",
                            "source_url": "https://1kuji.com/products/sample",
                        },
                        {
                            "catalog_index": 102,
                            "sub_series": "A賞",
                            "name_ja": "A賞 Figure",
                            "source_url": "https://1kuji.com/products/sample2",
                        },
                    ],
                },
                {
                    "normalized_name": "一番くじ Sample - B賞 Towel",
                    "has_reissue_signal": True,
                    "sample_rows": [
                        {
                            "catalog_index": 103,
                            "sub_series": "B賞",
                            "name_ja": "B賞 Towel",
                            "source_url": "https://1kuji.com/products/sample",
                        },
                        {
                            "catalog_index": 104,
                            "sub_series": "B賞",
                            "name_ja": "B賞 Towel",
                            "source_url": "https://1kuji.com/products/sample2",
                        },
                    ],
                },
            ],
        }

        report = queue.build_report(
            review_batches,
            ichiban_policy_audit=ichiban_policy_audit,
        )

        self.assertEqual(report["summary"]["ichiban_reissue_work_order_rows"], 2)
        self.assertEqual(report["summary"]["ichiban_reissue_campaign_work_order_rows"], 1)
        campaign_order = report["ichiban_reissue_campaign_work_order"][0]
        self.assertEqual(campaign_order["item_work_order_count"], 2)
        self.assertEqual(campaign_order["catalog_indexes"], [101, 102, 103, 104])
        self.assertEqual(campaign_order["prize_labels"], ["A賞", "B賞"])
        self.assertEqual(campaign_order["first_evidence_url"], "https://1kuji.com/products/sample")
        self.assertEqual(campaign_order["evidence_url_count"], 2)
        self.assertEqual(
            campaign_order["next_machine_step"],
            "compare_campaign_pair_once_then_apply_decision_to_item_work_orders",
        )

    def test_ichiban_reissue_overlap_is_flagged_on_unprotected_dedupe_group(self) -> None:
        review_batches = {
            "batches": [
                {
                    "groups": [
                        {
                            "key_type": "barcode",
                            "key": "ichiban-shared-barcode",
                            "review_priority": 10,
                            "review_risk": "strong_identity_review",
                            "review_confidence": "high_review_confidence",
                            "rows": [
                                {"catalog_index": 101, "barcode": "4900000000001"},
                                {"catalog_index": 102, "barcode": "4900000000001"},
                            ],
                        },
                    ]
                }
            ]
        }
        ichiban_policy_audit = {
            "probable_reissue_review_groups": [
                {
                    "normalized_name": "一番くじ sample prize",
                    "has_reissue_signal": False,
                    "reissue_signal_reasons": ["same_name_different_campaign_url"],
                    "sample_rows": [
                        {"catalog_index": 101},
                        {"catalog_index": 102},
                    ],
                }
            ]
        }

        report = queue.build_report(
            review_batches,
            max_groups=10,
            batch_size=10,
            ichiban_policy_audit=ichiban_policy_audit,
        )

        group = report["batches"][0]["groups"][0]
        self.assertTrue(group["ichiban_reissue_review"])
        self.assertFalse(group["ichiban_probable_reissue_review"])
        self.assertEqual(group["ichiban_reissue_catalog_indexes"], [101, 102])
        self.assertIn("same_name_different_campaign_url", group["ichiban_reissue_signal_reasons"])
        self.assertIn("ichiban_reissue_manual_confirmation_required", group["merge_blockers"])
        self.assertIn("ichiban_reissue_manual_confirmation_required", group["confirmation_risk_flags"])
        self.assertIn(
            "ichiban_reissue_manual_confirmation_required",
            group["manual_review_required_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
