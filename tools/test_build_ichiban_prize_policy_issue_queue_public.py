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
                        "work_order_id": "ichiban-reissue-dedupe-001",
                        "catalog_indexes": [6, 7],
                        "source_url_count": 2,
                        "source_urls": [
                            "https://1kuji.com/products/sample",
                            "https://1kuji.com/products/sample-2",
                        ],
                        "campaign_slug_families": ["sample"],
                        "campaign_url_comparison": {
                            "source_url_count": 2,
                            "campaign_slugs": ["sample", "sample-2"],
                            "campaign_slug_families": ["sample"],
                            "likely_same_campaign_family_reissue": True,
                        },
                        "manual_review_checklist": [
                            "Open every source_url and compare official campaign title/release period/prize lineup."
                        ],
                        "decision_template": {"manual_confirmed": False},
                        "prize_identity_summary": {
                            "prize_labels": ["A賞"],
                            "official_price_jpy_values": [790],
                            "zero_price_exception_policy_pass": True,
                        },
                        "zero_price_exception_policy": {
                            "last_one_or_double_chance_rows_must_be_zero_jpy": True,
                            "current_group_pass": True,
                        },
                        "sample_rows": [
                            {
                                "catalog_index": 6,
                                "source_url": "https://1kuji.com/products/sample",
                                "sub_series": "A賞",
                                "official_price_jpy": 790,
                                "image_url": "https://img.example/a.jpg",
                            },
                            {
                                "catalog_index": 7,
                                "source_url": "https://1kuji.com/products/sample-2",
                                "sub_series": "A賞",
                                "official_price_jpy": 790,
                            },
                        ],
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
        self.assertEqual(
            dict(report["summary"]["by_blocked_reason"]),
            {
                "zero_price_exception_identity_requires_confirmation": 1,
                "same_prize_label_has_multiple_unnumbered_rows": 1,
                "same_name_across_campaign_urls_may_be_reissue": 1,
            },
        )
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["summary"]["auto_delete_enabled"])
        self.assertEqual(report["policy_status"]["last_one_and_double_chance_prices"], "manual_fix_required")
        self.assertEqual(report["policy_status"]["probable_reissues"], "manual_review")
        self.assertEqual(report["issues"][0]["issue_id"], "ichiban-last-one-price-policy")
        self.assertEqual(
            report["issues"][0]["blocked_until"],
            "last_one_or_double_chance_identity_confirmed",
        )
        self.assertIn(
            "official_campaign_page_confirms_exception_prize",
            report["issues"][0]["required_evidence"],
        )
        self.assertEqual(report["issues"][1]["issue_id"], "ichiban-unnumbered-multi-item-prize-review")
        self.assertEqual(
            report["issues"][1]["blocked_reason"],
            "same_prize_label_has_multiple_unnumbered_rows",
        )
        self.assertEqual(
            report["issues"][1]["groups"][0]["identity_summary"]["catalog_indexes"],
            [2, 3],
        )
        self.assertIn(
            "decision_separate_prizes_selectable_variants_or_duplicate",
            report["issues"][1]["required_evidence"],
        )
        self.assertEqual(report["issues"][2]["issue_id"], "ichiban-reissue-review-001")
        self.assertEqual(
            report["issues"][2]["blocked_reason"],
            "same_name_across_campaign_urls_may_be_reissue",
        )
        self.assertIn("release_periods_compared", report["issues"][2]["required_evidence"])
        self.assertEqual(report["issues"][2]["work_order_id"], "ichiban-reissue-dedupe-001")
        self.assertEqual(report["issues"][2]["source_url_count"], 2)
        self.assertTrue(
            report["issues"][2]["campaign_url_comparison"][
                "likely_same_campaign_family_reissue"
            ]
        )
        self.assertEqual(report["issues"][2]["campaign_slug_families"], ["sample"])
        self.assertIn(
            "Open every source_url",
            report["issues"][2]["manual_review_checklist"][0],
        )
        self.assertEqual(
            report["issues"][2]["source_url_evidence_rows"][0]["rows_with_image_reference"],
            1,
        )
        self.assertEqual(report["issues"][2]["prize_identity_summary"]["prize_labels"], ["A賞"])
        self.assertTrue(report["issues"][2]["zero_price_exception_policy"]["current_group_pass"])

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
        self.assertEqual(
            report["issues"][0]["blocked_until"],
            "official_prize_lineup_relationship_confirmed",
        )

    def test_protects_already_distinct_limited_parallel_prize_rows(self) -> None:
        report = queue.build_queue(
            {
                "summary": {
                    "zero_price_violation_rows": 0,
                    "zero_price_exception_policy_pass": True,
                    "numbered_variant_coverage_policy_pass": True,
                },
                "multi_item_prize_label_groups": [
                    {
                        "source_url": "https://1kuji.com/products/jojo_anniv2",
                        "sub_series": "A賞",
                        "row_count": 2,
                        "review_lane": "unnumbered_multi_item_prize_review",
                        "sample_rows": [
                            {
                                "catalog_index": 15043,
                                "name_ja": "A賞 ジョナサン波紋疾走フィギュア【書店限定】",
                            },
                            {
                                "catalog_index": 15044,
                                "name_ja": "A賞 ジョセフ波紋疾走フィギュア【ローソン限定】",
                            },
                        ],
                    }
                ],
                "incomplete_numbered_variant_prize_label_groups": [],
            },
            {},
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["summary"]["issue_rows"], 0)
        self.assertEqual(report["summary"]["unnumbered_multi_item_prize_review_groups"], 0)
        self.assertEqual(report["summary"]["protected_unnumbered_multi_item_prize_groups"], 1)
        self.assertEqual(report["summary"]["protected_unnumbered_multi_item_prize_rows"], 2)
        self.assertEqual(
            report["summary"]["protected_unnumbered_multi_item_prize_reason_counts"],
            [["distinct_limited_shop_or_channel_labels", 1]],
        )
        self.assertEqual(report["policy_status"]["unnumbered_multi_item_prizes"], "clear")
        self.assertEqual(len(report["protected_unnumbered_multi_item_prize_groups"]), 1)
        self.assertEqual(
            report["protected_unnumbered_multi_item_prize_groups"][0]["review_state"],
            "protected_already_distinct_parallel_prizes",
        )

    def test_keeps_unmarked_same_prize_rows_in_manual_review(self) -> None:
        report = queue.build_queue(
            {
                "summary": {
                    "zero_price_violation_rows": 0,
                    "zero_price_exception_policy_pass": True,
                    "numbered_variant_coverage_policy_pass": True,
                },
                "multi_item_prize_label_groups": [
                    {
                        "source_url": "https://1kuji.com/products/sample",
                        "sub_series": "A賞",
                        "row_count": 2,
                        "review_lane": "unnumbered_multi_item_prize_review",
                        "sample_rows": [
                            {"catalog_index": 1, "name_ja": "A賞 アクリルスタンド"},
                            {"catalog_index": 2, "name_ja": "A賞 アクリルスタンド"},
                        ],
                    }
                ],
                "incomplete_numbered_variant_prize_label_groups": [],
            },
            {},
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["summary"]["issue_rows"], 1)
        self.assertEqual(report["summary"]["unnumbered_multi_item_prize_review_groups"], 1)
        self.assertEqual(report["summary"]["protected_unnumbered_multi_item_prize_groups"], 0)
        self.assertEqual(
            report["issues"][0]["blocked_reason"],
            "same_prize_label_has_multiple_unnumbered_rows",
        )

    def test_protects_numbered_volume_and_related_goods_parallel_rows(self) -> None:
        report = queue.build_queue(
            {
                "summary": {
                    "zero_price_violation_rows": 0,
                    "zero_price_exception_policy_pass": True,
                    "numbered_variant_coverage_policy_pass": True,
                },
                "multi_item_prize_label_groups": [
                    {
                        "source_url": "https://1kuji.com/products/myhero11",
                        "sub_series": "OJコラボ賞",
                        "row_count": 2,
                        "review_lane": "unnumbered_multi_item_prize_review",
                        "sample_rows": [
                            {"catalog_index": 17180, "name_ja": "OJコラボ賞① 色紙"},
                            {
                                "catalog_index": 17181,
                                "name_ja": "OJコラボ賞② クリアファイルセット",
                            },
                        ],
                    },
                    {
                        "source_url": "https://1kuji.com/products/md_shopper",
                        "sub_series": "めちゃでかショッパー",
                        "row_count": 2,
                        "review_lane": "unnumbered_multi_item_prize_review",
                        "sample_rows": [
                            {
                                "catalog_index": 13318,
                                "name_ja": "一番くじ めちゃでかショッパー(2026 vol.1)",
                            },
                            {
                                "catalog_index": 13319,
                                "name_ja": "一番くじ めちゃでかショッパー(2026 vol.2)",
                            },
                        ],
                    },
                    {
                        "source_url": "https://1kuji.com/products/cho-birth",
                        "sub_series": "関連商品",
                        "row_count": 2,
                        "review_lane": "unnumbered_multi_item_prize_review",
                        "sample_rows": [
                            {
                                "catalog_index": 16170,
                                "name_ja": "菓子商品 ワンピース ハッピーバースデーチョッパー",
                            },
                            {
                                "catalog_index": 16171,
                                "name_ja": "玩具菓子 HAPPYBIRTHDAYCHOPPER キーチェーンSP",
                            },
                        ],
                    },
                ],
                "incomplete_numbered_variant_prize_label_groups": [],
            },
            {},
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["summary"]["issue_rows"], 0)
        self.assertEqual(report["summary"]["protected_unnumbered_multi_item_prize_groups"], 3)
        self.assertEqual(report["summary"]["protected_unnumbered_multi_item_prize_rows"], 6)
        self.assertEqual(len(report["protected_unnumbered_multi_item_prize_groups"]), 3)
        self.assertEqual(
            dict(report["summary"]["protected_unnumbered_multi_item_prize_reason_counts"]),
            {
                "distinct_circled_number_labels": 1,
                "distinct_related_goods_prefixes": 1,
                "distinct_volume_labels": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
