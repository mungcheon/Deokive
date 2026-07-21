from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_kuji_metadata_review_batches_public as batches


class BuildIchibanKujiMetadataReviewBatchesPublicTest(unittest.TestCase):
    def test_build_report_batches_campaign_metadata_without_auto_apply(self) -> None:
        source = {
            "summary": {
                "missing_release_date_rows": 8,
                "missing_official_price_jpy_rows": 13,
            }
        }
        queue = [
            {
                "group_key": "https://1kuji.com/products/a",
                "url": "https://1kuji.com/products/a",
                "slug": "a",
                "title": "Campaign A",
                "catalog_item_rows": 8,
                "missing_fields": ["release_date"],
                "review_priority": 10,
                "source_evidence_required": "official_1kuji_campaign_page",
                "sample_catalog_indexes": [1, 2, 3, 4, 5, 6, 7, 8],
                "sample_names": ["A Prize"],
            },
            {
                "group_key": "https://1kuji.com/products/b",
                "url": "https://1kuji.com/products/b",
                "slug": "b",
                "title": "Campaign B",
                "catalog_item_rows": 13,
                "missing_fields": ["official_price_jpy"],
                "review_priority": 20,
                "source_evidence_required": "official_1kuji_campaign_page",
                "sample_catalog_indexes": [9, 10],
                "sample_names": ["B Prize"],
            },
        ]

        report = batches.build_report(source, queue, batch_size=1)

        self.assertEqual(report["summary"]["source_campaigns"], 2)
        self.assertEqual(report["summary"]["batch_count"], 2)
        self.assertEqual(report["summary"]["missing_release_date_rows"], 8)
        self.assertEqual(report["summary"]["missing_official_price_jpy_rows"], 13)
        self.assertEqual(report["summary"]["field_patch_template_count"], 2)
        self.assertEqual(
            report["summary"]["field_patch_template_counts"],
            [("release_date", 1), ("official_price_jpy", 1)],
        )
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_release_date"])
        self.assertFalse(report["automation_policy"]["auto_apply_official_price_jpy"])
        self.assertEqual(report["batches"][0]["campaigns"][0]["workflow"], "release_date_review")
        self.assertEqual(report["batches"][1]["campaigns"][0]["workflow"], "price_review")
        self.assertEqual(report["batches"][0]["blocked_until"], "manual_official_evidence_confirmed")
        self.assertEqual(report["batches"][0]["campaign_field_patch_template_fields"], ["release_date"])
        self.assertEqual(report["batches"][1]["campaign_field_patch_template_fields"], ["official_price_jpy"])
        self.assertIn(
            "double_chance_or_unlabeled_dates_are_not_used_as_release_date",
            report["batches"][0]["evidence_checklist"],
        )
        self.assertIn(
            "price_is_labeled_as_kuji_draw_price_or_official_price",
            report["batches"][1]["evidence_checklist"],
        )
        release_template = report["batches"][0]["campaigns"][0]["campaign_field_patch_templates"][0]
        self.assertEqual(release_template["field"], "release_date")
        self.assertEqual(release_template["target_scope"], "all_catalog_rows_for_campaign_url")
        self.assertFalse(release_template["manual_confirmed"])
        self.assertFalse(release_template["requires_full_campaign_index_expansion"])
        price_template = report["batches"][1]["campaigns"][0]["campaign_field_patch_templates"][0]
        self.assertTrue(price_template["requires_full_campaign_index_expansion"])
        self.assertIn(
            "campaign_title_matches_catalog_series",
            report["batches"][0]["campaigns"][0]["evidence_checklist"],
        )


if __name__ == "__main__":
    unittest.main()
