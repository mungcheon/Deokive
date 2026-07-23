from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_prize_policy_audit_public as audit


class BuildIchibanPrizePolicyAuditPublicTest(unittest.TestCase):
    def test_last_one_price_policy_flags_nonzero_rows(self) -> None:
        report = audit.build_report(
            {
                "items": [
                    {
                        "catalog_index": 1,
                        "name_ko": "一番くじ sample - ラストワン賞 prize",
                        "sub_series": "ラストワン賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 2,
                        "name_ko": "一番くじ sample - A賞 prize one",
                        "sub_series": "A賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 3,
                        "name_ko": "一番くじ sample - A賞 prize two",
                        "sub_series": "A賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 4,
                        "name_ko": "一番くじ sample - B賞 アクリル（1/3）",
                        "name_ja": "B賞 アクリル（1/3）",
                        "sub_series": "B賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 5,
                        "name_ko": "一番くじ sample - B賞 アクリル（3/3）",
                        "name_ja": "B賞 アクリル（3/3）",
                        "sub_series": "B賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 6,
                        "name_ko": "一番くじ sample（再販売） - A賞 prize one",
                        "sub_series": "A賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample-2",
                    },
                ]
            },
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(report["summary"]["kuji_rows"], 6)
        self.assertEqual(report["summary"]["last_one_rows"], 1)
        self.assertEqual(report["summary"]["last_one_nonzero_price_rows"], 1)
        self.assertFalse(report["summary"]["zero_price_exception_policy_pass"])
        self.assertEqual(report["summary"]["multi_item_prize_label_groups"], 2)
        self.assertEqual(
            report["summary"]["multi_item_prize_label_review_lanes"],
            [["unnumbered_multi_item_prize_review", 1], ["numbered_variant_gap_review", 1]],
        )
        self.assertEqual(report["summary"]["numbered_variant_prize_label_groups"], 1)
        self.assertEqual(report["summary"]["incomplete_numbered_variant_prize_label_groups"], 1)
        self.assertFalse(report["summary"]["numbered_variant_coverage_policy_pass"])
        self.assertEqual(
            report["incomplete_numbered_variant_prize_label_groups"][0]["missing_variant_numbers"],
            [2],
        )
        self.assertEqual(report["summary"]["probable_reissue_review_groups"], 1)
        self.assertEqual(
            report["summary"]["reissue_signal_reason_counts"],
            [["explicit_reissue_token_or_numbered_url", 1], ["campaign_url_slug_number_suffix_family", 1]],
        )
        self.assertEqual(report["summary"]["zero_price_violation_rows"], 1)
        self.assertEqual(report["summary"]["multi_item_prize_label_review_batch_count"], 1)
        self.assertEqual(report["summary"]["repeated_name_different_source_review_batch_count"], 1)
        self.assertEqual(report["summary"]["prize_policy_review_batch_count"], 2)
        self.assertEqual(report["review_batches"][0]["batch_id"], "ichiban-prize-policy-multi-item-001")
        self.assertEqual(report["review_batches"][0]["workflow"], "multi_item_prize_label_review")
        self.assertEqual(report["review_batches"][1]["batch_id"], "ichiban-prize-policy-repeated-name-001")
        self.assertEqual(
            report["multi_item_prize_label_groups"][0]["review_lane"],
            "unnumbered_multi_item_prize_review",
        )
        self.assertEqual(
            report["multi_item_prize_label_groups"][1]["variant_summary"]["missing_variant_numbers"],
            [2],
        )
        self.assertEqual(
            report["multi_item_prize_label_groups"][1]["variant_summary"]["numbered_variant_catalog_rows"],
            2,
        )
        self.assertEqual(
            report["probable_reissue_review_groups"][0]["reissue_signal_reasons"],
            ["explicit_reissue_token_or_numbered_url", "campaign_url_slug_number_suffix_family"],
        )
        self.assertEqual(report["next_actions"][0]["status"], "manual_fix_required")
        self.assertEqual(report["next_actions"][1]["workstream"], "numbered_variant_application")
        self.assertEqual(report["next_actions"][1]["status"], "review_required")
        self.assertEqual(report["next_actions"][2]["next_batch_id"], "ichiban-prize-policy-multi-item-001")
        self.assertFalse(report["summary"]["auto_apply_enabled"])

    def test_includes_numbered_variant_application_evidence(self) -> None:
        report = audit.build_report(
            {"items": []},
            generated_at="2026-07-22T00:00:00Z",
            numbered_variant_application={
                "write": True,
                "source_prizes_considered": 409,
                "applied_prizes": 409,
                "updated_existing_rows": 409,
                "created_variant_rows": 2518,
                "skipped": [],
            },
        )

        self.assertTrue(report["summary"]["numbered_variant_application_write"])
        self.assertEqual(report["summary"]["numbered_variant_source_prizes_considered"], 409)
        self.assertEqual(report["summary"]["numbered_variant_applied_prizes"], 409)
        self.assertEqual(report["summary"]["numbered_variant_updated_existing_rows"], 409)
        self.assertEqual(report["summary"]["numbered_variant_created_rows"], 2518)
        self.assertEqual(report["summary"]["numbered_variant_application_skipped_rows"], 0)
        self.assertEqual(report["numbered_variant_application"]["numbered_variant_created_rows"], 2518)
        self.assertEqual(report["next_actions"][1]["status"], "applied")

    def test_numbered_variant_complete_groups_are_not_manual_review_batches(self) -> None:
        report = audit.build_report(
            {
                "items": [
                    {
                        "catalog_index": 1,
                        "name_ko": "一番くじ sample - A賞 Acrylic (1/2)",
                        "name_ja": "A賞 Acrylic (1/2)",
                        "sub_series": "A賞",
                        "official_price_jpy": 700,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 2,
                        "name_ko": "一番くじ sample - A賞 Acrylic (2/2)",
                        "name_ja": "A賞 Acrylic (2/2)",
                        "sub_series": "A賞",
                        "official_price_jpy": 700,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 3,
                        "name_ko": "一番くじ sample - B賞 Plate red",
                        "name_ja": "B賞 Plate red",
                        "sub_series": "B賞",
                        "official_price_jpy": 700,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 4,
                        "name_ko": "一番くじ sample - B賞 Plate blue",
                        "name_ja": "B賞 Plate blue",
                        "sub_series": "B賞",
                        "official_price_jpy": 700,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                ]
            },
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["summary"]["multi_item_prize_label_groups"], 2)
        self.assertEqual(report["summary"]["numbered_variant_complete_prize_label_groups"], 1)
        self.assertEqual(report["summary"]["multi_item_prize_label_manual_review_groups"], 1)
        self.assertEqual(report["summary"]["multi_item_prize_label_review_batch_count"], 1)
        self.assertEqual(report["summary"]["multi_item_prize_label_review_catalog_item_rows"], 2)
        self.assertEqual(report["review_batches"][0]["group_count"], 1)
        self.assertEqual(report["review_batches"][0]["groups"][0]["sub_series"], "B賞")
        self.assertEqual(report["next_actions"][2]["rows"], 1)
        self.assertEqual(report["next_actions"][2]["total_multi_item_prize_label_groups"], 2)
        self.assertEqual(report["next_actions"][2]["numbered_variant_complete_prize_label_groups"], 1)


if __name__ == "__main__":
    unittest.main()
