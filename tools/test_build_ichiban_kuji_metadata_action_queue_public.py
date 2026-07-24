from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_kuji_metadata_action_queue_public as queue


class BuildIchibanKujiMetadataActionQueuePublicTest(unittest.TestCase):
    def test_build_report_prioritizes_release_before_price_and_keeps_manual(self) -> None:
        review = {
            "batches": [
                {
                    "next_machine_step": "verify_ichiban_campaign_page",
                    "evidence_checklist": ["official"],
                    "campaigns": [
                        {
                            "slug": "price",
                            "url": "https://1kuji.com/products/price",
                            "title": "Price Campaign",
                            "catalog_item_rows": 12,
                            "missing_fields": ["official_price_jpy"],
                            "workflow": "price_review",
                            "review_priority": 20,
                            "campaign_field_patch_templates": [
                                {
                                    "field": "official_price_jpy",
                                    "target_scope": "all_catalog_rows_for_campaign_url",
                                    "target_catalog_item_rows": 12,
                                    "requires_labeled_official_evidence": True,
                                }
                            ],
                        },
                        {
                            "slug": "release",
                            "url": "https://1kuji.com/products/release",
                            "title": "Release Campaign",
                            "catalog_item_rows": 8,
                            "missing_fields": ["release_date"],
                            "workflow": "release_date_review",
                            "review_priority": 10,
                            "campaign_field_patch_templates": [
                                {
                                    "field": "release_date",
                                    "target_scope": "all_catalog_rows_for_campaign_url",
                                    "target_catalog_item_rows": 8,
                                    "requires_labeled_official_evidence": True,
                                }
                            ],
                        },
                    ],
                }
            ]
        }

        report = queue.build_report(review, max_campaigns=10, batch_size=10)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["actionable_campaigns"], 2)
        self.assertEqual(report["summary"]["queued_action_campaigns"], 2)
        self.assertEqual(report["summary"]["unqueued_action_campaigns"], 0)
        self.assertEqual(report["summary"]["campaign_queue_coverage"], 1.0)
        self.assertEqual(report["summary"]["queued_catalog_item_rows"], 20)
        self.assertEqual(dict(report["summary"]["field_patch_template_counts"]), {"official_price_jpy": 1, "release_date": 1})
        self.assertEqual(report["summary"]["work_order_steps"], 2)
        self.assertEqual(
            report["summary"]["work_order_lanes"],
            ["confirm_release_dates", "confirm_draw_prices"],
        )
        self.assertEqual(report["summary"]["campaign_patch_work_order_rows"], 2)
        self.assertEqual(report["summary"]["campaign_patch_work_order_template_rows"], 2)
        self.assertEqual(report["summary"]["next_campaign_patch_review_batch_rows"], 2)
        self.assertEqual(report["summary"]["next_campaign_patch_review_batch_template_rows"], 2)
        self.assertEqual(report["summary"]["next_campaign_patch_review_batch_primary_review_url_rows"], 2)
        self.assertEqual(
            dict(report["summary"]["next_campaign_patch_review_batch_field_counts"]),
            {"release_date": 1, "official_price_jpy": 1},
        )
        self.assertEqual(report["summary"]["primary_review_url_rows"], 2)
        self.assertEqual(report["summary"]["queued_primary_review_url_rows"], 2)
        self.assertEqual(
            dict(report["summary"]["primary_review_url_kind_counts"]),
            {"official_1kuji_campaign_page": 2},
        )
        self.assertEqual(
            report["summary"]["first_primary_review_url"],
            "https://1kuji.com/products/release",
        )
        self.assertEqual([step["lane"] for step in report["work_order"]], ["confirm_release_dates", "confirm_draw_prices"])
        self.assertEqual(
            report["work_order"][0]["sample_campaigns"][0]["primary_review_url"],
            "https://1kuji.com/products/release",
        )
        self.assertEqual(report["work_order"][0]["campaign_count"], 1)
        self.assertEqual(report["work_order"][0]["catalog_item_rows"], 8)
        self.assertEqual(dict(report["work_order"][0]["field_patch_template_counts"]), {"release_date": 1})
        self.assertTrue(report["work_order"][0]["requires_manual_review"])
        self.assertFalse(report["work_order"][0]["auto_apply_enabled"])
        self.assertIn(
            "release_date_must_be_labeled_campaign_release_or_sales_start_date",
            report["work_order"][0]["guardrails"],
        )
        self.assertIn(
            "official_price_jpy_must_be_labeled_draw_price_or_price_per_try",
            report["work_order"][1]["guardrails"],
        )
        self.assertEqual(
            dict(report["batches"][0]["field_patch_template_counts"]),
            {"release_date": 1, "official_price_jpy": 1},
        )
        self.assertEqual([row["slug"] for row in report["batches"][0]["campaigns"]], ["release", "price"])
        self.assertEqual(
            [row["slug"] for row in report["campaign_patch_work_order"]],
            ["release", "price"],
        )
        first_work_item = report["campaign_patch_work_order"][0]
        self.assertEqual(first_work_item["primary_review_url"], "https://1kuji.com/products/release")
        self.assertEqual(first_work_item["primary_review_url_kind"], "official_1kuji_campaign_page")
        self.assertEqual(first_work_item["evidence_url_count"], 1)
        self.assertEqual(first_work_item["fields_to_confirm"], ["release_date"])
        self.assertEqual(first_work_item["field_patch_template_count"], 1)
        self.assertFalse(first_work_item["manual_confirmed"])
        self.assertEqual(
            first_work_item["blocked_until"],
            "labeled_official_1kuji_campaign_metadata_confirmed",
        )
        self.assertEqual(
            first_work_item["field_patch_templates"][0]["field"],
            "release_date",
        )
        next_review = report["next_campaign_patch_review_batch"][0]
        self.assertFalse(next_review["manual_confirmed"])
        self.assertEqual(next_review["slug"], "release")
        self.assertEqual(next_review["review_lane"], "confirm_campaign_release_date")
        self.assertEqual(next_review["fields_to_confirm"], ["release_date"])
        self.assertEqual(next_review["primary_review_url"], "https://1kuji.com/products/release")
        self.assertEqual(next_review["manual_value_fields_to_fill"][0]["field"], "release_date")
        self.assertEqual(next_review["manual_value_fields_to_fill"][0]["manual_value"], "")
        self.assertEqual(
            next_review["manual_value_fields_to_fill"][0]["evidence_url"],
            "https://1kuji.com/products/release",
        )
        self.assertIn(
            "For release_date, ignore double chance deadlines and prize shipping dates.",
            next_review["operator_checklist"],
        )
        self.assertEqual(
            next_review["manual_confirmation_template"],
            "server/ichiban_kuji_metadata_confirmed_rows.template.json",
        )
        self.assertFalse(next_review["auto_apply_enabled"])
        self.assertEqual(
            report["batches"][0]["review_state"],
            "manual_official_campaign_metadata_confirmation_required",
        )
        self.assertEqual(
            report["automation_policy"]["manual_confirmation_template"],
            "server/ichiban_kuji_metadata_confirmed_rows.template.json",
        )
        self.assertEqual(
            report["automation_policy"]["import_tool"],
            "tools/import_confirmed_ichiban_metadata_rows.py",
        )
        self.assertEqual(
            report["batches"][0]["unblocks_when"],
            "labeled_official_1kuji_campaign_metadata_confirmed",
        )
        self.assertEqual(
            report["batches"][0]["campaigns"][0]["confirmed_queue"],
            "server/ichiban_kuji_metadata_confirmed_rows.json",
        )
        first_campaign = report["batches"][0]["campaigns"][0]
        self.assertEqual(first_campaign["primary_review_url"], "https://1kuji.com/products/release")
        self.assertEqual(first_campaign["primary_review_url_kind"], "official_1kuji_campaign_page")
        self.assertEqual(first_campaign["evidence_urls"], ["https://1kuji.com/products/release"])
        self.assertEqual(first_campaign["review_lane"], "confirm_campaign_release_date")
        self.assertEqual(first_campaign["patch_summary"]["fields"], ["release_date"])
        self.assertEqual(first_campaign["patch_summary"]["target_catalog_item_rows"], 8)
        self.assertTrue(first_campaign["patch_summary"]["requires_labeled_official_evidence"])
        self.assertIn(
            "release_date_must_be_labeled_campaign_release_or_sales_start_date",
            first_campaign["manual_confirmation_requirements"],
        )
        price_campaign = report["batches"][0]["campaigns"][1]
        self.assertEqual(price_campaign["review_lane"], "confirm_campaign_draw_price")
        self.assertIn(
            "official_price_jpy_must_be_labeled_draw_price_or_price_per_try",
            price_campaign["manual_confirmation_requirements"],
        )

    def test_max_campaigns_caps_published_queue_not_actionable_summary(self) -> None:
        review = {
            "batches": [
                {
                    "campaigns": [
                        {
                            "slug": f"campaign-{index}",
                            "catalog_item_rows": 1,
                            "missing_fields": ["official_price_jpy"],
                            "workflow": "price_review",
                            "campaign_field_patch_templates": [{"field": "official_price_jpy"}],
                        }
                        for index in range(3)
                    ]
                }
            ]
        }

        report = queue.build_report(review, max_campaigns=2, batch_size=1)

        self.assertEqual(report["summary"]["actionable_campaigns"], 3)
        self.assertEqual(report["summary"]["queued_action_campaigns"], 2)
        self.assertEqual(report["summary"]["unqueued_action_campaigns"], 1)
        self.assertEqual(report["summary"]["campaign_queue_coverage"], 0.6667)
        self.assertEqual(report["summary"]["action_batch_count"], 2)
        self.assertEqual(report["summary"]["work_order_steps"], 1)
        self.assertEqual(report["summary"]["campaign_patch_work_order_rows"], 2)
        self.assertEqual(report["summary"]["next_campaign_patch_review_batch_rows"], 2)
        self.assertEqual(report["summary"]["next_campaign_patch_review_batch_template_rows"], 2)
        self.assertEqual(report["summary"]["primary_review_url_rows"], 0)
        self.assertEqual(report["work_order"][0]["campaign_count"], 2)


if __name__ == "__main__":
    unittest.main()
