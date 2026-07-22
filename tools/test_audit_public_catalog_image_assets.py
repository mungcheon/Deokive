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
        self.assertEqual(summary["invalid_local_image_paths"], 0)
        self.assertEqual(summary["local_asset_coverage"], 1.0)
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(report["findings"], [])

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
        self.assertEqual(report["summary"]["status"], "review_required")


if __name__ == "__main__":
    unittest.main()
