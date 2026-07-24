from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_public_catalog_image_assets as target


class PublicCatalogImageAssetAuditTests(unittest.TestCase):
    def test_current_public_catalog_image_assets_are_available_locally(self) -> None:
        report = target.build_report(target.load_catalog(), generated_at="2026-01-01T00:00:00Z")
        summary = report["summary"]

        self.assertGreater(summary["rows"], 0)
        self.assertGreater(summary["image_url_rows"], 0)
        self.assertEqual(summary["image_url_without_local_path_rows"], 0)
        self.assertEqual(summary["local_path_without_image_url_rows"], 0)
        self.assertEqual(summary["missing_local_image_files"], 0)
        self.assertEqual(summary["missing_web_public_asset_files"], 0)
        self.assertEqual(summary["invalid_local_image_paths"], 0)
        self.assertEqual(summary["local_asset_coverage"], 1.0)
        self.assertEqual(summary["web_public_asset_coverage"], 1.0)
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["download_readiness_status"], "known_image_assets_complete")
        self.assertEqual(summary["known_image_download_blocker_rows"], 0)
        self.assertEqual(
            summary["rows_still_requiring_image_url_evidence"],
            summary["missing_image_url_rows"],
        )
        self.assertEqual(summary["auto_download_ready_rows"], 0)
        self.assertTrue(
            report["download_readiness"]["download_complete_for_known_image_urls"]
        )
        self.assertEqual(report["download_readiness"]["auto_download_ready_rows"], 0)
        self.assertEqual(
            report["download_readiness"]["next_safe_phase"],
            "find_exact_image_urls_for_missing_rows",
        )
        self.assertEqual(
            report["missing_image_evidence_priority"]["rows"],
            summary["missing_image_url_rows"],
        )
        self.assertGreater(
            len(report["missing_image_evidence_priority"]["by_source_store"]),
            0,
        )
        self.assertGreater(
            len(report["missing_image_evidence_priority"]["sample_rows"]),
            0,
        )
        self.assertEqual(report["findings"], [])

    def test_report_prioritizes_missing_image_evidence_rows(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "A",
                    "source_store": "Store A",
                    "category": "Figure",
                    "affiliation": "Series A",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "B",
                    "source_store": "Store A",
                    "category": "Acrylic",
                    "affiliation": "Series B",
                },
                {
                    "catalog_index": 3,
                    "name_ko": "C",
                    "source_store": "Store B",
                    "category": "Figure",
                    "affiliation": "Series A",
                    "image_url": "https://example.com/c.jpg",
                    "local_image_path": "assets/catalog_images/does-not-exist-for-audit-test.webp",
                },
            ]
        }

        report = target.build_report(catalog, generated_at="2026-01-01T00:00:00Z")
        priority = report["missing_image_evidence_priority"]

        self.assertEqual(priority["rows"], 2)
        self.assertEqual(priority["by_source_store"][0], ["Store A", 2])
        self.assertEqual(priority["by_category"], [["Figure", 1], ["Acrylic", 1]])
        self.assertEqual(priority["by_affiliation"], [["Series A", 1], ["Series B", 1]])
        self.assertEqual(priority["sample_rows"][0]["catalog_index"], 1)
        self.assertEqual(
            report["download_readiness"]["missing_image_evidence_priority"],
            priority,
        )

    def test_report_flags_image_url_without_local_path(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "샘플",
                    "image_url": "https://example.com/a.jpg",
                }
            ]
        }

        report = target.build_report(catalog, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["image_url_without_local_path_rows"], 1)
        self.assertEqual(report["summary"]["status"], "review_required")
        self.assertEqual(
            report["summary"]["download_readiness_status"],
            "known_image_asset_download_required",
        )
        self.assertFalse(
            report["download_readiness"]["download_complete_for_known_image_urls"]
        )
        self.assertEqual(
            report["download_readiness"]["next_safe_phase"],
            "download_or_repair_known_image_assets",
        )

    def test_report_flags_missing_local_file(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 2,
                    "name_ko": "샘플",
                    "image_url": "https://example.com/a.jpg",
                    "local_image_path": "assets/catalog_images/does-not-exist-for-audit-test.webp",
                }
            ]
        }

        report = target.build_report(catalog, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["missing_local_image_files"], 1)
        self.assertEqual(report["summary"]["missing_web_public_asset_files"], 1)
        self.assertEqual(report["summary"]["status"], "review_required")
        self.assertEqual(
            report["summary"]["download_readiness_status"],
            "known_image_asset_download_required",
        )
        self.assertEqual(report["download_readiness"]["known_image_download_blocker_rows"], 2)


if __name__ == "__main__":
    unittest.main()
