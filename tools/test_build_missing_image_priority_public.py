from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_missing_image_priority_public as target


class MissingImagePriorityPublicTests(unittest.TestCase):
    def test_current_missing_image_queue_matches_public_catalog(self) -> None:
        report = target.build_report(
            target.load_json(target.CATALOG),
            target.load_json(target.WORK_QUEUE),
            generated_at="2026-01-01T00:00:00Z",
        )
        summary = report["summary"]

        self.assertEqual(summary["missing_image_rows"], 720)
        self.assertEqual(summary["work_queue_rows"], 720)
        self.assertEqual(summary["queue_matched_rows"], 720)
        self.assertEqual(summary["stale_queue_index_matches"], 0)
        self.assertEqual(summary["unmatched_catalog_missing_rows"], 0)
        self.assertIs(summary["auto_apply_enabled"], False)
        self.assertGreater(len(report["focus_groups"]), 0)
        self.assertGreater(len(report["breakdowns"]["by_source_store"]), 0)
        self.assertTrue(report["automation_policy"]["requires_exact_product_identity"])

    def test_build_report_counts_focus_groups_and_priority_samples(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "샘플 A",
                    "image_url": None,
                    "source_store": "FuRyu",
                    "affiliation": "작품",
                    "category": "피규어",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "샘플 B",
                    "image_url": "https://example.com/b.jpg",
                    "source_store": "FuRyu",
                    "affiliation": "작품",
                    "category": "피규어",
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": "FuRyu",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                    "priority": 10,
                    "search_url": "https://example.com/search",
                }
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["missing_image_rows"], 1)
        self.assertEqual(report["summary"]["queue_matched_rows"], 1)
        self.assertEqual(report["summary"]["high_priority_rows"], 1)
        self.assertEqual(report["focus_groups"][0]["rows"], 1)
        self.assertEqual(
            report["focus_groups"][0]["recommended_workflow"],
            "official_prize_provider_search_then_exact_detail_match",
        )


if __name__ == "__main__":
    unittest.main()
