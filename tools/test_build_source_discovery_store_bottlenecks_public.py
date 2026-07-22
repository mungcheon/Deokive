from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_store_bottlenecks_public as bottlenecks


class BuildSourceDiscoveryStoreBottlenecksPublicTest(unittest.TestCase):
    def test_build_report_groups_action_rows_by_store(self) -> None:
        action_queue = {
            "summary": {"actionable_source_rows": 3, "queued_source_rows": 3},
            "batches": [
                {
                    "batch_id": "b1",
                    "source_store": "Animate",
                    "workflow": "official_search_url_available",
                    "review_state": "official_search_review_required",
                    "row_count": 2,
                    "items": [
                        {
                            "catalog_index": 2,
                            "name_ko": "Badge",
                            "category": "캔뱃지",
                            "allowed_source_domains": ["animate.example"],
                        },
                        {
                            "catalog_index": 1,
                            "name_ko": "Stand",
                            "category": "아크릴 스탠드",
                            "allowed_source_domains": ["animate.example"],
                        },
                    ],
                },
                {
                    "batch_id": "b2",
                    "source_store": "Manual",
                    "workflow": "licensed_retailer_search_review",
                    "review_state": "licensed_retailer_review_required",
                    "row_count": 1,
                    "items": [{"catalog_index": 3, "name_ko": "Manual"}],
                },
            ],
        }

        report = bottlenecks.build_report(action_queue, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["store_count"], 2)
        self.assertEqual(report["summary"]["top_store"], "Animate")
        self.assertEqual(report["summary"]["top_store_rows"], 2)
        self.assertEqual(report["summary"]["domainless_store_rows"], 1)
        self.assertEqual(report["summary"]["stores_without_allowed_domain"], 1)
        animate = report["stores"][0]
        self.assertEqual(animate["source_store"], "Animate")
        self.assertEqual(animate["rows"], 2)
        self.assertTrue(animate["has_allowed_source_domain"])
        self.assertEqual(animate["allowed_source_domains"][0]["domain"], "animate.example")
        self.assertEqual([item["catalog_index"] for item in animate["sample_items"]], [2, 1])


if __name__ == "__main__":
    unittest.main()
