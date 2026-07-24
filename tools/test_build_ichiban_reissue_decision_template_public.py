from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_reissue_decision_template_public as builder


class IchibanReissueDecisionTemplateTests(unittest.TestCase):
    def test_build_report_extracts_campaign_and_item_templates_as_manual_only(self):
        report = builder.build_report(
            {
                "ichiban_reissue_campaign_work_order": [
                    {
                        "campaign_work_order_id": "campaign-001",
                        "source_urls": ["https://1kuji.com/products/a", "https://1kuji.com/products/a2"],
                        "item_work_order_count": 2,
                        "sample_rows": [
                            {
                                "name_ko": "一番くじ Sample - A賞 Figure",
                                "name_ja": "一番くじ Sample - A賞 Figure",
                                "campaign_title": "一番くじ Sample",
                                "prize_rank": "A賞",
                                "prize_item_name": "Figure",
                                "variant_name": "Normal color",
                                "identity_label": "一番くじ Sample / A賞 / Figure",
                            }
                        ],
                        "campaign_url_comparison": {
                            "likely_same_campaign_family_reissue": True,
                        },
                        "decision_template": {
                            "campaign_work_order_id": "campaign-001",
                            "manual_confirmed": True,
                            "decision": "campaign_pair_reissue_keep_all_separate",
                            "affected_item_work_order_ids": ["item-001", "item-002"],
                        },
                    }
                ],
                "ichiban_reissue_work_order": [
                    {
                        "work_order_id": "item-001",
                        "catalog_indexes": [1, 2],
                        "source_urls": ["https://1kuji.com/products/a", "https://1kuji.com/products/a2"],
                        "sample_rows": [
                            {
                                "name_ko": "一番くじ Sample - A賞 Figure",
                                "name_ja": "一番くじ Sample - A賞 Figure",
                                "campaign_title": "一番くじ Sample",
                                "prize_rank": "A賞",
                                "prize_item_name": "Figure",
                                "variant_name": "Normal color",
                                "identity_label": "一番くじ Sample / A賞 / Figure",
                            }
                        ],
                        "campaign_url_comparison": {
                            "likely_same_campaign_family_reissue": True,
                        },
                        "decision_template": {
                            "work_order_id": "item-001",
                            "manual_confirmed": True,
                            "decision": "same_sellable_product_keep_drop_confirmed",
                            "keep_catalog_index": 1,
                            "drop_catalog_indexes": [2],
                        },
                    }
                ],
            },
            generated_at="2026-07-24T00:00:00Z",
        )

        self.assertEqual(report["summary"]["campaign_template_rows"], 1)
        self.assertEqual(report["summary"]["item_template_rows"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_campaign_rows"], 0)
        self.assertEqual(report["summary"]["manual_confirmed_item_rows"], 0)
        self.assertEqual(report["summary"]["same_sellable_product_keep_drop_ready_rows"], 0)
        self.assertEqual(
            report["summary"]["item_review_lane_counts"],
            [["same_campaign_family_reissue_review", 1]],
        )
        self.assertEqual(
            report["summary"]["campaign_review_lane_counts"],
            [["campaign_pair_first", 1]],
        )
        self.assertEqual(report["summary"]["same_campaign_family_reissue_item_rows"], 1)
        self.assertEqual(report["summary"]["zero_price_exception_reissue_item_rows"], 0)
        self.assertEqual(report["summary"]["campaign_covered_item_template_rows"], 1)
        self.assertEqual(report["summary"]["standalone_item_template_rows"], 0)
        self.assertEqual(report["summary"]["campaign_item_decision_preview_rows"], 2)
        self.assertEqual(report["summary"]["campaign_review_batch_rows"], 1)
        self.assertEqual(report["summary"]["campaign_review_batch_item_work_order_rows"], 2)
        self.assertEqual(report["summary"]["campaign_review_batch_catalog_index_rows"], 0)
        self.assertEqual(report["summary"]["campaign_review_batch_item_preview_rows"], 2)
        self.assertEqual(report["summary"]["campaign_review_batch_visible_item_preview_rows"], 2)
        self.assertEqual(report["summary"]["campaign_review_batch_truncated_campaigns"], 0)
        self.assertEqual(report["summary"]["item_templates_with_evidence_urls"], 1)
        self.assertEqual(report["summary"]["campaign_templates_with_evidence_urls"], 1)
        self.assertEqual(report["summary"]["item_templates_with_identity_fields"], 1)
        self.assertEqual(report["summary"]["campaign_templates_with_identity_fields"], 1)
        self.assertEqual(report["summary"]["first_item_evidence_url"], "https://1kuji.com/products/a")
        self.assertEqual(report["summary"]["first_campaign_evidence_url"], "https://1kuji.com/products/a")
        self.assertFalse(report["summary"]["auto_merge_enabled"])
        self.assertFalse(report["summary"]["auto_delete_enabled"])
        self.assertTrue(report["summary"]["manual_review_required_before_mutation"])
        self.assertFalse(report["campaign_templates"][0]["manual_confirmed"])
        self.assertFalse(report["item_templates"][0]["manual_confirmed"])
        self.assertEqual(report["campaign_templates"][0]["decision"], "")
        self.assertEqual(report["item_templates"][0]["decision"], "")
        self.assertEqual(
            report["campaign_templates"][0]["affected_item_work_order_ids"],
            ["item-001", "item-002"],
        )
        self.assertEqual(report["campaign_templates"][0]["item_decision_application_preview_rows"], 2)
        self.assertEqual(report["campaign_templates"][0]["first_evidence_url"], "https://1kuji.com/products/a")
        self.assertEqual(report["campaign_templates"][0]["evidence_url_count"], 2)
        self.assertEqual(report["campaign_templates"][0]["sample_rows_with_identity_fields"], 1)
        self.assertEqual(report["campaign_templates"][0]["recommended_review_lane"], "campaign_pair_first")
        self.assertIn(
            "identity_fields_complete",
            report["campaign_templates"][0]["review_risk_summary"]["review_risk_tags"],
        )
        self.assertEqual(
            report["campaign_templates"][0]["item_decision_application_preview"][0][
                "suggested_decision_if_campaign_is_reissue"
            ],
            "reissue_or_campaign_variant_keep_separate",
        )
        self.assertEqual(
            report["campaign_templates"][0]["item_decision_application_preview"][0][
                "suggested_decision_if_campaign_is_duplicate"
            ],
            "same_sellable_product_keep_drop_confirmed",
        )
        self.assertFalse(
            report["campaign_templates"][0]["item_decision_application_preview"][0][
                "manual_confirmed"
            ]
        )
        self.assertEqual(
            report["campaign_templates"][0]["item_decision_application_preview"][0]["first_evidence_url"],
            "https://1kuji.com/products/a",
        )
        self.assertEqual(
            report["campaign_templates"][0]["item_decision_application_preview"][0][
                "recommended_review_lane"
            ],
            "same_campaign_family_reissue_review",
        )
        self.assertIn(
            "likely_same_campaign_family_reissue",
            report["campaign_templates"][0]["item_decision_application_preview"][0][
                "review_risk_tags"
            ],
        )
        self.assertEqual(report["item_templates"][0]["drop_catalog_indexes"], [2])
        self.assertEqual(report["item_templates"][0]["first_evidence_url"], "https://1kuji.com/products/a")
        self.assertEqual(report["item_templates"][0]["evidence_url_count"], 2)
        self.assertEqual(report["item_templates"][0]["sample_rows_with_identity_fields"], 1)
        self.assertEqual(
            report["item_templates"][0]["recommended_review_lane"],
            "same_campaign_family_reissue_review",
        )
        self.assertIn(
            "likely_same_campaign_family_reissue",
            report["item_templates"][0]["review_risk_summary"]["review_risk_tags"],
        )
        self.assertIn(
            "identity_fields_complete",
            report["item_templates"][0]["review_risk_summary"]["review_risk_tags"],
        )
        self.assertEqual(report["next_campaign_review_batch"][0]["campaign_work_order_id"], "campaign-001")
        self.assertEqual(report["next_campaign_review_batch"][0]["item_work_order_count"], 2)
        self.assertEqual(report["next_campaign_review_batch"][0]["item_review_preview_rows"], 2)
        self.assertEqual(
            report["next_campaign_review_batch"][0]["item_review_preview"][0]["work_order_id"],
            "item-001",
        )
        self.assertEqual(
            report["next_campaign_review_batch"][0]["item_review_preview"][0]["prize_rank"],
            "A賞",
        )
        self.assertEqual(
            report["next_campaign_review_batch"][0]["item_review_preview"][0]["prize_item_name"],
            "Figure",
        )
        self.assertEqual(
            report["next_campaign_review_batch"][0]["item_review_preview"][0]["variant_name"],
            "Normal color",
        )
        self.assertEqual(
            report["next_campaign_review_batch"][0]["item_review_preview"][0]["sample_name_ko"],
            "一番くじ Sample - A賞 Figure",
        )
        self.assertTrue(
            report["next_campaign_review_batch"][0]["campaign_url_comparison"][
                "likely_same_campaign_family_reissue"
            ]
        )
        self.assertEqual(
            report["next_campaign_review_batch"][0]["item_review_preview"][0][
                "recommended_review_lane"
            ],
            "same_campaign_family_reissue_review",
        )
        self.assertTrue(
            report["next_campaign_review_batch"][0]["item_review_preview"][0][
                "keep_drop_still_requires_item_review"
            ]
        )
        self.assertFalse(report["next_campaign_review_batch"][0]["manual_confirmed"])
        self.assertFalse(report["automation_policy"]["auto_merge_enabled"])


if __name__ == "__main__":
    unittest.main()
