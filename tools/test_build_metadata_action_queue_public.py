from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_metadata_action_queue_public as queue


class BuildMetadataActionQueuePublicTest(unittest.TestCase):
    def test_build_report_excludes_dedicated_queue_fields(self) -> None:
        review = {
            "batches": [
                {
                    "recommended_action": "Review metadata",
                    "groups": [
                        {
                            "field": "release_date",
                            "source_store": "Store A",
                            "missing_rows": 3,
                            "workflow": "official_metadata_review",
                            "sample_catalog_indexes": [1, 2],
                        },
                        {
                            "field": "source_url",
                            "source_store": "Store B",
                            "missing_rows": 5,
                            "workflow": "source_url_discovery",
                        },
                    ],
                }
            ]
        }

        report = queue.build_report(review, max_groups=10, batch_size=10)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["actionable_group_count"], 1)
        self.assertEqual(report["summary"]["queued_missing_cells"], 3)
        self.assertEqual(dict(report["summary"]["excluded_field_missing_cells"]), {"source_url": 5})
        self.assertEqual(report["batches"][0]["groups"][0]["field"], "release_date")

    def test_max_groups_caps_queue_not_actionable_summary(self) -> None:
        review = {
            "batches": [
                {
                    "groups": [
                        {
                            "field": "name_ja",
                            "source_store": f"Store {index}",
                            "missing_rows": 1,
                        }
                        for index in range(3)
                    ]
                }
            ]
        }

        report = queue.build_report(review, max_groups=2, batch_size=1)

        self.assertEqual(report["summary"]["actionable_group_count"], 3)
        self.assertEqual(report["summary"]["queued_group_count"], 2)
        self.assertEqual(report["summary"]["action_batch_count"], 2)


if __name__ == "__main__":
    unittest.main()
