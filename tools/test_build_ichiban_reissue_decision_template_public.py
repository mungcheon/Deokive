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
        self.assertEqual(report["item_templates"][0]["drop_catalog_indexes"], [2])
        self.assertFalse(report["automation_policy"]["auto_merge_enabled"])


if __name__ == "__main__":
    unittest.main()
