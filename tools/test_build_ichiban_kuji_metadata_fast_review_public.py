from __future__ import annotations

import unittest

from build_ichiban_kuji_metadata_fast_review_public import build_report


class IchibanKujiMetadataFastReviewTests(unittest.TestCase):
    def test_build_report_prioritizes_release_then_larger_price_campaigns(self):
        action_queue = {
            "batches": [
                {
                    "campaigns": [
                        {
                            "slug": "small-price",
                            "url": "https://1kuji.com/products/small-price",
                            "workflow": "price_review",
                            "missing_fields": ["official_price_jpy"],
                            "catalog_item_rows": 3,
                            "campaign_field_patch_templates": [{"field": "official_price_jpy"}],
                        },
                        {
                            "slug": "release",
                            "url": "https://1kuji.com/products/release",
                            "workflow": "release_date_review",
                            "missing_fields": ["release_date"],
                            "catalog_item_rows": 2,
                            "campaign_field_patch_templates": [{"field": "release_date"}],
                        },
                        {
                            "slug": "large-price",
                            "url": "https://1kuji.com/products/large-price",
                            "workflow": "price_review",
                            "missing_fields": ["official_price_jpy"],
                            "catalog_item_rows": 8,
                            "campaign_field_patch_templates": [{"field": "official_price_jpy"}],
                        },
                    ]
                }
            ]
        }

        report = build_report(action_queue, max_campaigns=2, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["summary"]["fast_review_campaigns"], 2)
        self.assertEqual(report["summary"]["held_for_later_campaigns"], 1)
        self.assertEqual(report["summary"]["fast_review_catalog_item_rows"], 10)
        self.assertEqual([item["slug"] for item in report["items"]], ["release", "large-price"])
        self.assertEqual(report["items"][0]["campaign_field_patch_templates"][0]["manual_confirmed"], False)
        self.assertIs(report["summary"]["auto_apply_enabled"], False)
        self.assertEqual(
            report["automation_policy"]["import_tool"],
            "tools/import_confirmed_ichiban_metadata_rows.py",
        )


if __name__ == "__main__":
    unittest.main()
