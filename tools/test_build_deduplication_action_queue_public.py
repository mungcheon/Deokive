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
        self.assertFalse(report["automation_policy"]["auto_merge"])
        self.assertEqual(dict(report["summary"]["by_review_confidence"]), {
            "high_review_confidence": 1,
            "medium_review_confidence": 1,
        })
        self.assertEqual(dict(report["summary"]["excluded_review_confidence"]), {"variant_caution": 1})
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
        self.assertEqual(
            report["batches"][0]["groups"][0]["confirmed_queue"],
            "server/catalog_dedupe_confirmed_decisions.json",
        )
        first_group = report["batches"][0]["groups"][0]
        self.assertEqual(first_group["keep_basis"]["basis"], "richest_or_equal_catalog_row")
        self.assertEqual(first_group["keep_basis"]["keep_richness"], 9)
        self.assertTrue(first_group["keep_basis"]["keep_has_image"])
        self.assertTrue(first_group["row_comparison_summary"]["name_differs"])
        self.assertTrue(first_group["row_comparison_summary"]["multi_store"])
        self.assertIn("name_differs", first_group["confirmation_risk_flags"])
        self.assertIn("multi_store_review", first_group["confirmation_risk_flags"])

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
        self.assertEqual(report["summary"]["ichiban_reissue_manual_confirmed_rows"], 0)
        self.assertEqual(
            report["ichiban_reissue_work_order"][0]["review_state"],
            "ichiban_reissue_identity_confirmation_required",
        )
        self.assertIn(
            "reissue_or_campaign_variant_keep_separate",
            report["ichiban_reissue_work_order"][0]["decision_template"]["decision_options"],
        )
        self.assertIn(
            "ichiban_reissue_manual_confirmation_required",
            report["ichiban_reissue_review_lane"][0]["merge_blockers"],
        )

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
                        "sample_rows": [{"catalog_index": 1}, {"catalog_index": 2}],
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
        self.assertEqual(len(report["ichiban_reissue_review_lane"]), 1)
        self.assertEqual(len(report["ichiban_reissue_work_order"]), 1)
        self.assertEqual(
            report["ichiban_reissue_work_order"][0]["next_machine_step"],
            "compare_campaign_pages_then_record_reissue_or_duplicate_decision",
        )
        self.assertFalse(report["ichiban_reissue_work_order"][0]["decision_template"]["manual_confirmed"])
        self.assertEqual(
            report["ichiban_reissue_review_lane"][0]["next_machine_step"],
            "verify_ichiban_campaign_pages_before_dedupe",
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


if __name__ == "__main__":
    unittest.main()
