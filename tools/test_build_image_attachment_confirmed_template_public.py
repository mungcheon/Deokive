from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_image_attachment_confirmed_template_public as builder


class BuildImageAttachmentConfirmedTemplatePublicTest(unittest.TestCase):
    def test_build_template_flattens_action_queue_for_confirmed_import(self) -> None:
        action_queue = {
            "batches": [
                {
                    "batch_id": "image-attachment-action-001",
                    "workflow": "replace_generic_source_then_extract_image",
                    "source_store": "Stellive Store",
                    "items": [
                        {
                            "catalog_index": 10,
                            "workflow": "replace_generic_source_then_extract_image",
                            "source_store": "Stellive Store",
                            "name_ko": "Badge",
                            "category": "Can Badge",
                            "source_url": "https://fanding.kr/@stellive/shop",
                            "official_search_url": "https://stellive.example/search?q=badge",
                            "source_url_update_required": True,
                            "representative_image_review_required": False,
                            "image_url_ready": False,
                            "required_before_image_import": ["confirm_exact_product_source_url"],
                            "catalog_field_import_template": {
                                "row_index": 10,
                                "field": "image_url",
                                "source_store": "Stellive Store",
                            },
                        }
                    ],
                }
            ]
        }

        template = builder.build_template(action_queue, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(template["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(template["summary"]["template_items"], 1)
        self.assertEqual(template["summary"]["manual_confirmed_rows"], 0)
        self.assertEqual(template["summary"]["source_url_update_required_rows"], 1)
        self.assertEqual(template["summary"]["representative_image_review_required_rows"], 0)
        self.assertEqual(template["summary"]["by_batch"], [["image-attachment-action-001", 1]])
        self.assertFalse(template["summary"]["auto_apply_enabled"])
        self.assertEqual(template["automation_policy"]["import_tool"], "tools/import_confirmed_image_attachment_rows.py")
        item = template["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["field"], "image_url")
        self.assertEqual(item["manual_value"], "")
        self.assertEqual(item["candidate_source_url"], "")
        self.assertEqual(item["current_source_url"], "https://fanding.kr/@stellive/shop")
        self.assertEqual(item["row_index"], 10)
        self.assertEqual(item["catalog_index"], 10)
        self.assertTrue(item["source_url_update_required"])
        self.assertFalse(item["representative_image"])


if __name__ == "__main__":
    unittest.main()
