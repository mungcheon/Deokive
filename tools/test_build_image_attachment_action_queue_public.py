from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_image_attachment_action_queue_public as queue


class BuildImageAttachmentActionQueuePublicTest(unittest.TestCase):
    def test_build_report_keeps_actionable_image_workflows(self) -> None:
        enrichment = {
            "groups": [
                {
                    "workflow": "replace_generic_source_then_extract_image",
                    "source_store": "Stellive Store",
                    "missing_image_rows": 2,
                    "sample_items": [
                        {
                            "catalog_index": 2,
                            "name_ko": "Badge",
                            "category": "Can Badge",
                            "source_url": "https://example.com/shop",
                            "catalog_field_import_template": {"field": "image_url"},
                        },
                        {
                            "catalog_index": 1,
                            "name_ko": "Plush",
                            "category": "Plush",
                            "source_url": "https://example.com/shop",
                            "catalog_field_import_template": {"field": "image_url"},
                        },
                    ],
                },
                {
                    "workflow": "find_source_then_extract_image",
                    "source_store": "Movic",
                    "missing_image_rows": 5,
                    "sample_items": [
                        {
                            "catalog_index": 3,
                            "name_ko": "Acrylic",
                            "category": "Acrylic",
                            "catalog_field_import_template": {"field": "image_url"},
                        }
                    ],
                },
            ]
        }

        report = queue.build_report(enrichment, max_batches=10, batch_size=20)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["actionable_image_rows"], 2)
        self.assertEqual(report["summary"]["queued_image_rows"], 2)
        self.assertEqual(dict(report["summary"]["excluded_workflow_rows"]), {"find_source_then_extract_image": 5})
        self.assertEqual(report["summary"]["action_batch_count"], 1)
        self.assertEqual(report["batches"][0]["workflow"], "replace_generic_source_then_extract_image")
        self.assertEqual([item["catalog_index"] for item in report["batches"][0]["items"]], [1, 2])

    def test_max_batches_caps_published_batches_not_actionable_summary(self) -> None:
        enrichment = {
            "groups": [
                {
                    "workflow": "review_gotouchi_official_candidates",
                    "source_store": f"Store {index}",
                    "missing_image_rows": 1,
                    "sample_items": [
                        {
                            "catalog_index": index,
                            "name_ko": f"Item {index}",
                            "catalog_field_import_template": {"field": "image_url"},
                        }
                    ],
                }
                for index in range(3)
            ]
        }

        report = queue.build_report(enrichment, max_batches=1, batch_size=1)

        self.assertEqual(report["summary"]["actionable_image_rows"], 3)
        self.assertEqual(report["summary"]["queued_image_rows"], 1)
        self.assertEqual(report["summary"]["action_batch_count"], 1)


if __name__ == "__main__":
    unittest.main()
