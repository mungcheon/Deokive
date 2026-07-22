from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_manual_missing_image_source_discovery_public as target


class ManualMissingImageSourceDiscoveryPublicTests(unittest.TestCase):
    def test_build_report_publishes_only_manual_research_rows(self) -> None:
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "name_ko": "manual",
                    "source_store": "Manual Store",
                    "category": "figure",
                    "affiliation": "series",
                    "query": "manual",
                    "strategy": "manual_review",
                    "automation_safety": "manual_research_required",
                },
                {
                    "row_index": 2,
                    "name_ko": "search",
                    "source_store": "Search Store",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                },
            ]
        }

        report = target.build_report(queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["manual_source_discovery_rows"], 1)
        self.assertEqual(report["summary"]["source_store_count"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])
        self.assertEqual(report["items"][0]["source_discovery_template"]["blocked_until"], "exact_official_product_source_url_found")
        self.assertTrue(report["items"][0]["manual_review_required"])


if __name__ == "__main__":
    unittest.main()
