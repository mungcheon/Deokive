from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_deduplication_action_queue_public as queue


class BuildDeduplicationActionQueuePublicTest(unittest.TestCase):
    def test_build_report_keeps_only_high_and_medium_confidence_groups(self) -> None:
        review_batches = {
            "batches": [
                {
                    "identity_checklist": ["compare_product_images_for_same_sellable_item"],
                    "groups": [
                        {
                            "key_type": "barcode",
                            "key": "111",
                            "review_priority": 10,
                            "review_risk": "strong_identity_review",
                            "review_confidence": "high_review_confidence",
                            "keep_catalog_index": 1,
                            "drop_catalog_indexes": [2],
                            "dedupe_decision_template": {"decision": "review_required"},
                        },
                        {
                            "key_type": "source_url",
                            "key": "https://example.test/item",
                            "review_priority": 20,
                            "review_risk": "source_identity_review",
                            "review_confidence": "medium_review_confidence",
                            "keep_catalog_index": 3,
                            "drop_catalog_indexes": [4],
                        },
                        {
                            "key_type": "barcode",
                            "key": "222",
                            "review_priority": 40,
                            "review_risk": "variant_risk_review",
                            "review_confidence": "variant_caution",
                            "keep_catalog_index": 5,
                            "drop_catalog_indexes": [6],
                        },
                    ],
                }
            ]
        }

        report = queue.build_report(review_batches, max_groups=10, batch_size=10)

        self.assertEqual(report["summary"]["actionable_groups"], 2)
        self.assertEqual(report["summary"]["queued_groups"], 2)
        self.assertEqual(report["summary"]["unqueued_actionable_groups"], 0)
        self.assertEqual(report["summary"]["queue_coverage"], 1.0)
        self.assertEqual(report["summary"]["action_batch_count"], 1)
        self.assertFalse(report["summary"]["auto_delete_enabled"])
        self.assertFalse(report["automation_policy"]["auto_merge"])
        self.assertEqual(dict(report["summary"]["by_review_confidence"]), {
            "high_review_confidence": 1,
            "medium_review_confidence": 1,
        })
        self.assertEqual(dict(report["summary"]["excluded_review_confidence"]), {"variant_caution": 1})
        keys = [group["key"] for group in report["batches"][0]["groups"]]
        self.assertEqual(keys, ["111", "https://example.test/item"])
        self.assertEqual(
            report["batches"][0]["next_machine_step"],
            "record_manual_dedupe_decisions",
        )
        self.assertEqual(
            report["automation_policy"]["manual_confirmation_template"],
            "server/catalog_dedupe_confirmed_decisions.template.json",
        )
        self.assertEqual(
            report["automation_policy"]["import_tool"],
            "tools/import_confirmed_dedupe_decisions.py",
        )
        self.assertEqual(
            report["batches"][0]["unblocks_when"],
            "explicit_manual_keep_drop_decision_confirmed",
        )
        self.assertEqual(
            report["batches"][0]["groups"][0]["confirmed_queue"],
            "server/catalog_dedupe_confirmed_decisions.json",
        )

    def test_max_groups_caps_published_queue_only(self) -> None:
        review_batches = {
            "batches": [
                {
                    "groups": [
                        {
                            "key_type": "barcode",
                            "key": str(index),
                            "review_priority": 10,
                            "review_confidence": "high_review_confidence",
                        }
                        for index in range(5)
                    ]
                }
            ]
        }

        report = queue.build_report(review_batches, max_groups=3, batch_size=2)

        self.assertEqual(report["summary"]["actionable_groups"], 5)
        self.assertEqual(report["summary"]["queued_groups"], 3)
        self.assertEqual(report["summary"]["unqueued_actionable_groups"], 2)
        self.assertEqual(report["summary"]["queue_coverage"], 0.6)
        self.assertEqual(report["summary"]["action_batch_count"], 2)


if __name__ == "__main__":
    unittest.main()
