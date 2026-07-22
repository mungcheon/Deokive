from __future__ import annotations

import unittest

from build_deduplication_fast_review_public import build_report


class DeduplicationFastReviewTests(unittest.TestCase):
    def test_build_report_keeps_only_high_confidence_barcode_groups(self):
        action_queue = {
            "batches": [
                {
                    "groups": [
                        {
                            "key_type": "barcode",
                            "key": "111",
                            "review_confidence": "high_review_confidence",
                            "review_risk": "strong_identity_review",
                            "keep_catalog_index": 1,
                            "drop_catalog_indexes": [2],
                            "stores": ["store a", "store b"],
                            "categories": ["badge"],
                            "evidence": ["barcode", "same_barcode", "same_source_url"],
                            "dedupe_decision_template": {"key": "111"},
                            "rows": [{"catalog_index": 1}, {"catalog_index": 2}],
                        },
                        {
                            "key_type": "source_url",
                            "key": "https://example.test/a",
                            "review_confidence": "high_review_confidence",
                            "drop_catalog_indexes": [4],
                        },
                        {
                            "key_type": "barcode",
                            "key": "222",
                            "review_confidence": "medium_review_confidence",
                            "drop_catalog_indexes": [6],
                        },
                    ]
                }
            ]
        }

        report = build_report(action_queue, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["summary"]["fast_review_groups"], 1)
        self.assertEqual(report["summary"]["held_for_later_groups"], 2)
        self.assertEqual(report["summary"]["same_source_url_groups"], 1)
        self.assertIs(report["summary"]["auto_delete_enabled"], False)
        self.assertIs(report["items"][0]["dedupe_decision_template"]["manual_confirmed"], False)
        self.assertEqual(
            report["items"][0]["dedupe_decision_template"]["fast_review_lane"],
            "same_barcode_high_confidence",
        )
        self.assertEqual(report["automation_policy"]["import_tool"], "tools/import_confirmed_dedupe_decisions.py")


if __name__ == "__main__":
    unittest.main()
