from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_action_queue_public as queue


class BuildSourceDiscoveryActionQueuePublicTest(unittest.TestCase):
    def test_build_report_keeps_actionable_review_states(self) -> None:
        review = {
            "batches": [
                {
                    "workflow": "official_search_url_available",
                    "review_state": "official_search_review_required",
                    "source_store": "Animate",
                    "row_count": 2,
                    "next_machine_step": "open_search",
                    "items": [
                        {"catalog_index": 2, "name_ko": "Badge", "category": "Badge"},
                        {"catalog_index": 1, "name_ko": "Stand", "category": "Acrylic"},
                    ],
                },
                {
                    "workflow": "manual_official_research",
                    "review_state": "manual_official_research_required",
                    "source_store": "Unknown",
                    "row_count": 5,
                    "items": [{"catalog_index": 3, "name_ko": "Manual"}],
                },
            ]
        }

        report = queue.build_report(review, max_rows=10, batch_size=10)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["actionable_source_rows"], 2)
        self.assertEqual(report["summary"]["queued_source_rows"], 2)
        self.assertEqual(dict(report["summary"]["excluded_review_state_rows"]), {"manual_official_research_required": 5})
        self.assertEqual(report["summary"]["action_batch_count"], 1)
        self.assertEqual([item["catalog_index"] for item in report["batches"][0]["items"]], [1, 2])

    def test_max_rows_caps_queue_not_actionable_summary(self) -> None:
        review = {
            "batches": [
                {
                    "workflow": "official_search_url_available",
                    "review_state": "official_search_review_required",
                    "source_store": "Store",
                    "row_count": 3,
                    "items": [{"catalog_index": index} for index in range(3)],
                }
            ]
        }

        report = queue.build_report(review, max_rows=2, batch_size=1)

        self.assertEqual(report["summary"]["actionable_source_rows"], 3)
        self.assertEqual(report["summary"]["queued_source_rows"], 2)
        self.assertEqual(report["summary"]["action_batch_count"], 2)


if __name__ == "__main__":
    unittest.main()
