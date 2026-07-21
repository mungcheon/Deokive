from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_deduplication_review_batches_public as batches


class BuildDeduplicationReviewBatchesPublicTest(unittest.TestCase):
    def test_build_report_keeps_dedupe_manual_and_batches_by_priority(self) -> None:
        groups = [
            {
                "key_type": "barcode",
                "key": "123",
                "review_priority": 10,
                "review_risk": "strong_identity_review",
                "keep_catalog_index": 1,
                "drop_catalog_indexes": [2],
                "evidence": ["barcode", "same_barcode"],
                "rows": [
                    {"catalog_index": 1, "name_ja": "Same Plush A", "source_store": "A", "category": "Plush"},
                    {"catalog_index": 2, "name_ja": "Same Plush A", "source_store": "A", "category": "Plush"},
                ],
            },
            {
                "key_type": "barcode",
                "key": "456",
                "review_priority": 40,
                "review_risk": "variant_risk_review",
                "keep_catalog_index": 3,
                "drop_catalog_indexes": [4],
                "evidence": ["barcode", "same_barcode"],
                "rows": [
                    {"catalog_index": 3, "name_ja": "Prize A Figure", "source_store": "C", "category": "Figure"},
                    {"catalog_index": 4, "name_ja": "Prize B Figure", "source_store": "C", "category": "Daily Goods"},
                ],
            },
        ]

        report = batches.build_report(groups, batch_size=1)

        self.assertEqual(report["summary"]["source_groups"], 2)
        self.assertEqual(report["summary"]["batch_count"], 2)
        self.assertEqual(report["summary"]["decision_template_count"], 2)
        self.assertFalse(report["summary"]["auto_delete_enabled"])
        self.assertFalse(report["automation_policy"]["auto_delete"])
        self.assertFalse(report["automation_policy"]["auto_merge"])
        self.assertEqual(report["batches"][0]["groups"][0]["review_confidence"], "high_review_confidence")
        self.assertEqual(report["batches"][1]["groups"][0]["review_confidence"], "variant_caution")
        self.assertEqual(report["batches"][0]["blocked_until"], "explicit_manual_keep_drop_confirmation")
        self.assertIn("decision", report["batches"][0]["dedupe_decision_template_fields"])
        self.assertFalse(report["batches"][0]["groups"][0]["auto_merge_enabled"])
        self.assertFalse(report["batches"][0]["groups"][0]["auto_delete_enabled"])
        self.assertIn("barcode_matches_all_rows", report["batches"][0]["identity_checklist"])
        variant_template = report["batches"][1]["groups"][0]["dedupe_decision_template"]
        self.assertFalse(variant_template["manual_confirmed"])
        self.assertEqual(variant_template["decision"], "review_required")
        self.assertTrue(variant_template["requires_variant_difference_disproved"])
        self.assertIn(
            "preserve_rows_unless_variant_difference_is_disproved",
            report["batches"][1]["groups"][0]["identity_checklist"],
        )
        self.assertIn("category_mismatch", report["batches"][1]["groups"][0]["merge_blockers"])
        self.assertIn("not a deletion command", report["instructions"][1])


if __name__ == "__main__":
    unittest.main()
