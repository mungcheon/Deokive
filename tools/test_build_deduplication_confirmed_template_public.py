from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_deduplication_confirmed_template_public as builder


class BuildDeduplicationConfirmedTemplatePublicTest(unittest.TestCase):
    def test_build_template_flattens_fast_review_groups_for_importer(self) -> None:
        fast_review = {
            "items": [
                {
                    "key_type": "barcode",
                    "key": "4901234567890",
                    "review_confidence": "high_review_confidence",
                    "review_risk": "strong_identity_review",
                    "keep_catalog_index": 2,
                    "drop_catalog_indexes": [1],
                    "stores": ["Store A"],
                    "categories": ["Badge"],
                    "evidence": ["same_barcode", "same_source_url"],
                    "merge_blockers": ["none"],
                    "fast_review_lane": "same_barcode_and_source_url",
                    "dedupe_decision_template": {
                        "manual_confirmed": False,
                        "decision": "review_required",
                        "key_type": "barcode",
                        "key": "4901234567890",
                        "keep_catalog_index": 2,
                        "drop_catalog_indexes": [1],
                    },
                    "rows": [
                        {"catalog_index": 1, "name_ko": "Drop"},
                        {"catalog_index": 2, "name_ko": "Keep"},
                    ],
                }
            ]
        }

        template = builder.build_template(fast_review, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(template["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(template["summary"]["template_items"], 1)
        self.assertEqual(template["summary"]["manual_confirmed_rows"], 0)
        self.assertEqual(template["summary"]["same_sellable_product_confirmed_rows"], 0)
        self.assertEqual(template["summary"]["drop_candidate_rows"], 1)
        self.assertEqual(template["summary"]["by_fast_review_lane"], [["same_barcode_and_source_url", 1]])
        self.assertFalse(template["summary"]["auto_delete_enabled"])
        self.assertEqual(template["automation_policy"]["import_tool"], "tools/import_confirmed_deduplication_rows.py")
        item = template["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertFalse(item["same_sellable_product_confirmed"])
        self.assertEqual(item["decision"], "review_required")
        self.assertEqual(item["keep_catalog_index"], 2)
        self.assertEqual(item["drop_catalog_indexes"], [1])
        self.assertEqual(item["rows"][0]["catalog_index"], 1)


if __name__ == "__main__":
    unittest.main()
