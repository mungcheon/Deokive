from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.build_ichiban_reissue_deduplication_summary_public import build_summary


class BuildIchibanReissueDeduplicationSummaryPublicTest(unittest.TestCase):
    def test_summary_counts_removed_rows_and_mismatches(self) -> None:
        report = {
            "price_zero_updates": 3,
            "duplicate_groups_removed": 2,
            "duplicate_rows_removed": 3,
            "groups": [
                {
                    "reason": "reissue_or_secondary_order_duplicate",
                    "kept": {
                        "release_date": "2026-05-21",
                        "source_url": "https://1kuji.com/products/a",
                        "image_url": "https://assets.1kuji.com/a.webp",
                        "local_image_path": "assets/catalog_images/a.webp",
                        "official_price_jpy": 900,
                    },
                    "removed": [
                        {
                            "release_date": "2026-06-23",
                            "source_url": "https://1kuji.com/products/a-2",
                            "image_url": "https://assets.1kuji.com/b.webp",
                            "local_image_path": "assets/catalog_images/b.webp",
                            "official_price_jpy": 900,
                        }
                    ],
                },
                {
                    "reason": "manual_exact_duplicate",
                    "kept": {
                        "release_date": "2026-01-01",
                        "source_url": "https://1kuji.com/products/c",
                        "image_url": "https://assets.1kuji.com/c.webp",
                        "local_image_path": "assets/catalog_images/c.webp",
                        "official_price_jpy": 790,
                    },
                    "removed": [
                        {
                            "release_date": "2026-01-01",
                            "source_url": "https://1kuji.com/products/c",
                            "image_url": "https://assets.1kuji.com/c.webp",
                            "local_image_path": "assets/catalog_images/c.webp",
                            "official_price_jpy": 790,
                        },
                        {
                            "release_date": "2026-01-01",
                            "source_url": "https://1kuji.com/products/c",
                            "image_url": "https://assets.1kuji.com/c.webp",
                            "local_image_path": "assets/catalog_images/c.webp",
                            "official_price_jpy": 990,
                        },
                    ],
                },
            ],
        }

        summary = build_summary(report)

        self.assertEqual(summary["reissue_duplicate_groups"], 2)
        self.assertEqual(summary["kept_rows"], 2)
        self.assertEqual(summary["removed_rows"], 3)
        self.assertEqual(
            summary["reason_counts"],
            [["manual_exact_duplicate", 1], ["reissue_or_secondary_order_duplicate", 1]],
        )
        self.assertEqual(summary["release_date_mismatch_groups"], 1)
        self.assertEqual(summary["source_url_mismatch_groups"], 1)
        self.assertEqual(summary["image_url_mismatch_groups"], 1)
        self.assertEqual(summary["local_image_path_mismatch_groups"], 1)
        self.assertEqual(summary["official_price_jpy_mismatch_groups"], 1)
        self.assertTrue(summary["summary_matches_top_level_counts"])
        self.assertFalse(summary["automation_policy"]["auto_delete_enabled"])
        self.assertTrue(summary["automation_policy"]["manual_review_required_before_mutation"])

    def test_summary_reports_missing_local_image_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            existing = root / "assets" / "catalog_images" / "exists.webp"
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b"image")
            report = {
                "duplicate_groups_removed": 1,
                "duplicate_rows_removed": 1,
                "groups": [
                    {
                        "kept": {"local_image_path": "assets/catalog_images/exists.webp"},
                        "removed": [{"local_image_path": "assets/catalog_images/missing.webp"}],
                    }
                ],
            }

            summary = build_summary(report, asset_root=root)

        self.assertEqual(summary["missing_local_image_files"], 1)


if __name__ == "__main__":
    unittest.main()
