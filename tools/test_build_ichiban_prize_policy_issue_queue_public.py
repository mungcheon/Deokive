from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_prize_policy_issue_queue_public as queue


class BuildIchibanPrizePolicyIssueQueuePublicTest(unittest.TestCase):
    def test_builds_manual_policy_issue_queue(self) -> None:
        report = queue.build_queue(
            {
                "summary": {
                    "last_one_nonzero_price_rows": 1,
                    "double_chance_nonzero_price_rows": 0,
                    "zero_price_violation_rows": 1,
                    "zero_price_exception_policy_pass": False,
                    "numbered_variant_coverage_policy_pass": True,
                    "numbered_variant_created_rows": 12,
                    "numbered_variant_application_skipped_rows": 0,
                    "probable_reissue_review_groups": 1,
                    "repeated_name_different_source_groups": 2,
                },
                "last_one_price_violations": [{"catalog_index": 1, "official_price_jpy": 790}],
                "double_chance_price_violations": [],
                "incomplete_numbered_variant_prize_label_groups": [],
                "multi_item_prize_label_groups": [
                    {
                        "source_url": "https://1kuji.com/products/sample",
                        "sub_series": "A賞",
                        "row_count": 2,
                        "review_lane": "unnumbered_multi_item_prize_review",
                        "sample_rows": [{"catalog_index": 2}, {"catalog_index": 3}],
                    },
                    {
                        "source_url": "https://1kuji.com/products/sample",
                        "sub_series": "B賞",
                        "row_count": 2,
                        "review_lane": "numbered_variant_complete",
                        "sample_rows": [{"catalog_index": 4}, {"catalog_index": 5}],
                    },
                ],
            },
            {
                "summary": {
                    "ichiban_probable_reissue_review_groups": 1,
                    "ichiban_probable_reissue_sample_rows": 2,
                },
                "ichiban_reissue_work_order": [
                    {
                        "normalized_name": "sample prize",
                        "catalog_indexes": [6, 7],
                        "source_urls": [
                            "https://1kuji.com/products/sample",
                            "https://1kuji.com/products/sample-2",
                        ],
                        "decision_template": {"manual_confirmed": False},
                        "sample_rows": [{"catalog_index": 6}, {"catalog_index": 7}],
                    }
                ],
            },
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-23T00:00:00Z")
        self.assertEqual(report["summary"]["issue_rows"], 3)
        self.assertEqual(report["summary"]["open_issue_rows"], 5)
        self.assertEqual(report["summary"]["zero_price_violation_rows"], 1)
        self.assertEqual(report["summary"]["unnumbered_multi_item_prize_review_groups"], 1)
        self.assertEqual(report["summary"]["probable_reissue_work_order_rows"], 1)
        self.assertEqual(
            report["summary"]["lane_counts"],
            [
                ["zero_price_policy_violation", 1],
                ["unnumbered_multi_item_prize_review", 1],
                ["probable_reissue_or_campaign_variant_review", 1],
            ],
        )
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["summary"]["auto_delete_enabled"])
        self.assertEqual(report["policy_status"]["last_one_and_double_chance_prices"], "manual_fix_required")
        self.assertEqual(report["policy_status"]["probable_reissues"], "manual_review")
        self.assertEqual(report["issues"][0]["issue_id"], "ichiban-last-one-price-policy")
        self.assertEqual(report["issues"][1]["issue_id"], "ichiban-unnumbered-multi-item-prize-review")
        self.assertEqual(report["issues"][2]["issue_id"], "ichiban-reissue-review-001")

    def test_clean_price_policy_still_surfaces_remaining_reviews(self) -> None:
        report = queue.build_queue(
            {
                "summary": {
                    "zero_price_violation_rows": 0,
                    "zero_price_exception_policy_pass": True,
                    "numbered_variant_coverage_policy_pass": True,
                    "numbered_variant_created_rows": 2518,
                    "numbered_variant_application_skipped_rows": 0,
                },
                "multi_item_prize_label_groups": [],
                "incomplete_numbered_variant_prize_label_groups": [],
            },
            {},
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["summary"]["issue_rows"], 0)
        self.assertTrue(report["summary"]["zero_price_exception_policy_pass"])
        self.assertEqual(report["policy_status"]["last_one_and_double_chance_prices"], "pass")
        self.assertEqual(report["policy_status"]["unnumbered_multi_item_prizes"], "clear")

    def test_uses_review_batches_when_top_multi_item_sample_omits_manual_groups(self) -> None:
        report = queue.build_queue(
            {
                "summary": {
                    "zero_price_violation_rows": 0,
                    "zero_price_exception_policy_pass": True,
                    "numbered_variant_coverage_policy_pass": True,
                    "multi_item_prize_label_manual_review_groups": 1,
                },
                "multi_item_prize_label_groups": [
                    {
                        "source_url": "https://1kuji.com/products/sample",
                        "sub_series": "A賞",
                        "row_count": 2,
                        "review_lane": "numbered_variant_complete",
                    }
                ],
                "review_batches": [
                    {
                        "workflow": "multi_item_prize_label_review",
                        "groups": [
                            {
                                "source_url": "https://1kuji.com/products/manual",
                                "sub_series": "B賞",
                                "row_count": 2,
                                "review_lane": "unnumbered_multi_item_prize_review",
                                "sample_rows": [{"catalog_index": 10}, {"catalog_index": 11}],
                            }
                        ],
                    }
                ],
            },
            {},
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["summary"]["issue_rows"], 1)
        self.assertEqual(report["summary"]["unnumbered_multi_item_prize_review_groups"], 1)
        self.assertEqual(report["summary"]["unnumbered_multi_item_prize_review_rows"], 2)
        self.assertEqual(report["policy_status"]["unnumbered_multi_item_prizes"], "manual_review")
        self.assertEqual(report["issues"][0]["issue_id"], "ichiban-unnumbered-multi-item-prize-review")


if __name__ == "__main__":
    unittest.main()
