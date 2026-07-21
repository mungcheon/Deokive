from __future__ import annotations

import unittest

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
                "evidence": ["barcode"],
                "rows": [
                    {"catalog_index": 1, "name_ja": "ちいかわ ぬいぐるみ", "source_store": "A", "category": "인형"},
                    {"catalog_index": 2, "name_ja": "ちいかわ ぬいぐるみ", "source_store": "B", "category": "인형"},
                ],
            },
            {
                "key_type": "barcode",
                "key": "456",
                "review_priority": 40,
                "review_risk": "variant_risk_review",
                "keep_catalog_index": 3,
                "drop_catalog_indexes": [4],
                "evidence": ["barcode"],
                "rows": [
                    {"catalog_index": 3, "name_ja": "A賞 フィギュア", "source_store": "C", "category": "피규어"},
                    {"catalog_index": 4, "name_ja": "B賞 タオル", "source_store": "C", "category": "타월"},
                ],
            },
        ]
        report = batches.build_report(groups, batch_size=1)

        self.assertEqual(report["summary"]["source_groups"], 2)
        self.assertEqual(report["summary"]["batch_count"], 2)
        self.assertFalse(report["summary"]["auto_delete_enabled"])
        self.assertFalse(report["automation_policy"]["auto_delete"])
        self.assertFalse(report["automation_policy"]["auto_merge"])
        self.assertEqual(report["batches"][0]["groups"][0]["review_confidence"], "high_review_confidence")
        self.assertEqual(report["batches"][1]["groups"][0]["review_confidence"], "variant_caution")
        self.assertIn("not a deletion command", report["instructions"][1])


if __name__ == "__main__":
    unittest.main()
