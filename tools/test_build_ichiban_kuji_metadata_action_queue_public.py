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
                            "campaign_field_patch_templates": [{"field": "official_price_jpy"}],
                        },
                        {
                            "slug": "release",
                            "url": "https://1kuji.com/products/release",
                            "title": "Release Campaign",
                            "catalog_item_rows": 8,
                            "missing_fields": ["release_date"],
                            "workflow": "release_date_review",
                            "review_priority": 10,
                            "campaign_field_patch_templates": [{"field": "release_date"}],
                        },
                    ],
                }
            ]
        }

        report = queue.build_report(review, max_campaigns=10, batch_size=10)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["actionable_campaigns"], 2)
        self.assertEqual(report["summary"]["queued_action_campaigns"], 2)
        self.assertEqual(report["summary"]["queued_catalog_item_rows"], 20)
        self.assertEqual(dict(report["summary"]["field_patch_template_counts"]), {"official_price_jpy": 1, "release_date": 1})
        self.assertEqual([row["slug"] for row in report["batches"][0]["campaigns"]], ["release", "price"])
        self.assertEqual(
            report["batches"][0]["review_state"],
            "manual_official_campaign_metadata_confirmation_required",
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
        self.assertEqual(report["summary"]["action_batch_count"], 2)


if __name__ == "__main__":
    unittest.main()
