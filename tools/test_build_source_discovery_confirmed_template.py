from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_confirmed_template as builder


class BuildSourceDiscoveryConfirmedTemplateTest(unittest.TestCase):
    def test_builds_guarded_catalog_field_import_template(self) -> None:
        payload = {
            "batches": [
                {
                    "batch_id": "source-discovery-001",
                    "workflow": "official_search_url_available",
                    "review_state": "official_search_review_required",
                    "items": [
                        {
                            "catalog_field_import_template": {
                                "manual_confirmed": False,
                                "manual_note": "",
                                "row_index": 10,
                                "field": "source_url",
                                "manual_value": "",
                                "evidence_url": "https://example.test/search?q=item",
                                "candidate_source_url": "",
                                "source_store": "Example Store",
                                "name_ko": "Example Goods",
                            }
                        }
                    ],
                }
            ]
        }

        template = builder.build_template(payload)

        self.assertEqual(template["summary"]["template_items"], 1)
        self.assertFalse(template["summary"]["auto_apply_enabled"])
        self.assertFalse(template["automation_policy"]["auto_apply_enabled"])
        item = template["items"][0]
        self.assertEqual(item["field"], "source_url")
        self.assertEqual(item["row_index"], 10)
        self.assertEqual(item["manual_value"], "")
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["source_discovery_batch_id"], "source-discovery-001")
        self.assertEqual(item["source_discovery_workflow"], "official_search_url_available")

    def test_skips_duplicate_row_field_templates(self) -> None:
        template_row = {
            "catalog_field_import_template": {
                "row_index": 10,
                "field": "source_url",
                "manual_confirmed": True,
                "manual_value": "https://example.test/unsafe",
            }
        }
        payload = {
            "batches": [
                {"batch_id": "a", "workflow": "one", "items": [template_row]},
                {"batch_id": "b", "workflow": "two", "items": [template_row]},
            ]
        }

        template = builder.build_template(payload)

        self.assertEqual(len(template["items"]), 1)
        self.assertFalse(template["items"][0]["manual_confirmed"])
        self.assertEqual(template["items"][0]["manual_value"], "")


if __name__ == "__main__":
    unittest.main()
