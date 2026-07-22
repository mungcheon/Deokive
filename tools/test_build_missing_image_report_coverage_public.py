from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_missing_image_report_coverage_public as target


class MissingImageReportCoveragePublicTests(unittest.TestCase):
    def test_build_report_assigns_known_store_and_manual_rows(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "animate",
                    "source_store": target.ANIMATE_STORE,
                    "image_url": None,
                },
                {
                    "catalog_index": 2,
                    "name_ko": "manual",
                    "source_store": "Manual Store",
                    "image_url": None,
                },
                {
                    "catalog_index": 3,
                    "name_ko": "unassigned",
                    "source_store": "Unknown Store",
                    "image_url": None,
                },
                {
                    "catalog_index": 4,
                    "name_ko": "cached",
                    "source_store": target.ANIMATE_STORE,
                    "local_image_path": "assets/catalog_images/cached.webp",
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                },
                {
                    "row_index": 2,
                    "strategy": "manual_review",
                    "automation_safety": "manual_research_required",
                },
                {
                    "row_index": 3,
                    "strategy": "source_url_manual_review",
                    "automation_safety": "manual_confirmation_required",
                },
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")
        report_counts = {row["report_key"]: row["assigned_missing_image_rows"] for row in report["reports"]}

        self.assertEqual(report["summary"]["missing_image_rows"], 3)
        self.assertEqual(report["summary"]["assigned_report_rows"], 2)
        self.assertEqual(report["summary"]["unassigned_missing_image_rows"], 1)
        self.assertEqual(report_counts["animate_missing_image_search"], 1)
        self.assertEqual(report_counts["manual_missing_image_source_discovery"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])


if __name__ == "__main__":
    unittest.main()
