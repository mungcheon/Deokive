from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_requested_focus_action_queue_public as queue


class BuildRequestedFocusActionQueuePublicTest(unittest.TestCase):
    def test_build_report_excludes_barcode_and_keeps_actionable_templates(self) -> None:
        review_batches = {
            "batches": [
                {
                    "topic_id": "requested_special_goods",
                    "topic_label": "Requested",
                    "missing_field": "source_url",
                    "source_store": "Movic",
                    "next_machine_step": "find_exact_source",
                    "recommended_action": "Find source",
                    "items": [
                        {
                            "catalog_index": 2,
                            "missing_field": "source_url",
                            "name_ko": "Acrylic Stand",
                            "category": "Acrylic",
                            "source_store": "Movic",
                            "catalog_field_import_template": {
                                "field": "source_url",
                                "manual_confirmed": False,
                            },
                        },
                        {
                            "catalog_index": 1,
                            "missing_field": "barcode",
                            "name_ko": "Badge",
                            "category": "Badge",
                            "source_store": "Movic",
                            "catalog_field_import_template": {
                                "field": "barcode",
                                "manual_confirmed": False,
                            },
                        },
                    ],
                },
                {
                    "topic_id": "danganronpa",
                    "topic_label": "Danganronpa",
                    "missing_field": "image_url",
                    "source_store": "Good Smile",
                    "next_machine_step": "extract_image",
                    "recommended_action": "Extract image",
                    "items": [
                        {
                            "catalog_index": 3,
                            "missing_field": "image_url",
                            "name_ko": "Nui",
                            "category": "Plush",
                            "source_store": "Good Smile",
                            "catalog_field_import_template": {
                                "field": "image_url",
                                "manual_confirmed": False,
                            },
                        }
                    ],
                },
            ]
        }

        report = queue.build_report(review_batches, max_batches=10, batch_size=10)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["actionable_template_rows"], 2)
        self.assertEqual(report["summary"]["queued_action_rows"], 2)
        self.assertEqual(report["summary"]["unqueued_actionable_rows"], 0)
        self.assertEqual(report["summary"]["queue_coverage"], 1.0)
        self.assertEqual(report["summary"]["barcode_template_rows_excluded"], 1)
        self.assertEqual(report["summary"]["non_barcode_template_rows"], 2)
        self.assertEqual(report["summary"]["total_review_template_rows"], 3)
        self.assertEqual(report["summary"]["non_barcode_template_share"], 0.6667)
        self.assertEqual(dict(report["summary"]["field_counts"]), {"source_url": 1, "image_url": 1})
        self.assertEqual(report["summary"]["action_batch_count"], 2)
        fields = [batch["missing_field"] for batch in report["batches"]]
        self.assertEqual(fields, ["source_url", "image_url"])
        queued_names = [item["name_ko"] for batch in report["batches"] for item in batch["items"]]
        self.assertEqual(queued_names, ["Acrylic Stand", "Nui"])

    def test_max_batches_caps_published_batches_not_total_summary(self) -> None:
        review_batches = {
            "batches": [
                {
                    "topic_id": "ichiban_kuji",
                    "topic_label": "Ichiban",
                    "missing_field": "official_price_jpy",
                    "source_store": "1kuji",
                    "items": [
                        {
                            "catalog_index": index,
                            "missing_field": "official_price_jpy",
                            "name_ko": f"Prize {index}",
                            "catalog_field_import_template": {"field": "official_price_jpy"},
                        }
                        for index in range(5)
                    ],
                }
            ]
        }

        report = queue.build_report(review_batches, max_batches=1, batch_size=2)

        self.assertEqual(report["summary"]["actionable_template_rows"], 5)
        self.assertEqual(report["summary"]["queued_action_rows"], 2)
        self.assertEqual(report["summary"]["unqueued_actionable_rows"], 3)
        self.assertEqual(report["summary"]["queue_coverage"], 0.4)
        self.assertEqual(report["summary"]["action_batch_count"], 1)


if __name__ == "__main__":
    unittest.main()
