from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_requested_focus_review_batches_public as batches


class BuildRequestedFocusReviewBatchesPublicTest(unittest.TestCase):
    def test_build_report_batches_requested_focus_rows_with_import_templates(self) -> None:
        catalog = [
            {
                "catalog_index": 1,
                "name_ko": "Danganronpa Nui",
                "name_ja": "Danganronpa Nui JP",
                "category": "Plush",
                "source_store": "Movic",
                "source_url": "",
                "image_url": "",
                "release_date": "",
                "official_price_jpy": None,
                "barcode": "",
            },
            {
                "catalog_index": 2,
                "name_ko": "Maho Saba Plush",
                "name_ja": "Maho Saba Plush JP",
                "category": "Plush",
                "source_store": "Animate",
                "source_url": "https://example.test/item",
                "image_url": "https://example.test/item.jpg",
                "release_date": "2026-01",
                "official_price_jpy": 2200,
                "barcode": "1234567890123",
            },
        ]
        requested = [
            {
                "request_label": "Danganronpa Nui",
                "status": "already_present",
                "matched_name_ko": "Danganronpa Nui",
                "has_candidate_image": False,
                "existing_count": 1,
                "review_note": "image still needs review",
            }
        ]

        report = batches.build_report(catalog, requested, batch_size=2)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])
        self.assertGreaterEqual(report["summary"]["batch_count"], 1)
        template_fields = [
            item["catalog_field_import_template"]["field"]
            for batch in report["batches"]
            for item in batch.get("items", [])
            if isinstance(item.get("catalog_field_import_template"), dict)
        ]
        self.assertEqual(report["summary"]["field_patch_template_count"], len(template_fields))
        self.assertGreater(report["summary"]["field_patch_template_count"], 0)
        template_counts = dict(report["summary"]["field_patch_template_counts"])
        self.assertEqual(template_counts["source_url"], template_fields.count("source_url"))
        self.assertEqual(template_counts["image_url"], template_fields.count("image_url"))
        danganronpa_batches = [
            batch for batch in report["batches"] if batch["topic_id"] == "danganronpa"
        ]
        self.assertTrue(danganronpa_batches)
        self.assertIn("source_url", {batch["missing_field"] for batch in danganronpa_batches})
        self.assertTrue(all(batch["auto_apply_enabled"] is False for batch in report["batches"]))

        source_batch = next(batch for batch in danganronpa_batches if batch["missing_field"] == "source_url")
        self.assertIn("manual_value", source_batch["catalog_field_import_template_fields"])
        source_template = source_batch["items"][0]["catalog_field_import_template"]
        self.assertEqual(source_template["field"], "source_url")
        self.assertFalse(source_template["manual_confirmed"])
        self.assertEqual(source_template["blocked_until"], "exact_product_source_url_confirmed")
        self.assertTrue(source_template["requires_exact_source_url"])

        image_batch = next(batch for batch in danganronpa_batches if batch["missing_field"] == "image_url")
        image_template = image_batch["items"][0]["catalog_field_import_template"]
        self.assertEqual(image_template["field"], "image_url")
        self.assertEqual(image_template["blocked_until"], "exact_product_source_url_confirmed")

    def test_requested_special_goods_matches_catalog_by_requested_name(self) -> None:
        catalog = [
            {
                "catalog_index": 10,
                "name_ko": "Pop Team Epic Bukubu Goods",
                "name_ja": "Pop Team Epic Bukubu Goods JP",
                "category": "Other Goods",
                "source_store": "Manual Review",
                "source_url": "https://example.test/pop",
                "image_url": "https://example.test/pop.jpg",
                "release_date": "",
                "official_price_jpy": None,
                "barcode": "",
            }
        ]
        requested = [
            {
                "request_label": "Pop Team Epic Bukubu Goods",
                "matched_name_ko": "Pop Team Epic Bukubu Goods",
                "status": "already_present",
                "has_candidate_image": True,
                "existing_count": 1,
            }
        ]

        report = batches.build_report(catalog, requested, batch_size=10)
        topic = next(
            row for row in report["topic_summaries"] if row["topic_id"] == "requested_special_goods"
        )

        self.assertEqual(topic["catalog_rows"], 1)
        self.assertEqual(topic["field_missing_totals"]["release_date"], 1)
        release_batch = next(batch for batch in report["batches"] if batch["missing_field"] == "release_date")
        release_template = release_batch["items"][0]["catalog_field_import_template"]
        self.assertEqual(release_template["field"], "release_date")
        self.assertTrue(release_template["requires_labeled_official_evidence"])
        self.assertEqual(release_template["evidence_url"], "https://example.test/pop")


if __name__ == "__main__":
    unittest.main()
