from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_ichiban_prize_display_names as target


class ApplyIchibanPrizeDisplayNamesTest(unittest.TestCase):
    def test_write_updates_only_safe_rank_and_item_display_names(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "Campaign - Figure",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "Campaign - A prize mystery item",
                },
            ]
        }
        review = {
            "review_rows": [
                {
                    "catalog_index": 1,
                    "source_url": "https://1kuji.com/products/demo",
                    "series_name": "Campaign",
                    "prize_rank": "A prize",
                    "prize_item_name": "Figure",
                    "display_name_ko": "Campaign - Figure",
                    "expected_display_name_ko": "Campaign - A prize Figure",
                },
                {
                    "catalog_index": 2,
                    "series_name": "Campaign",
                    "prize_rank": "A prize",
                    "prize_item_name": "",
                    "display_name_ko": "Campaign - A prize mystery item",
                    "expected_display_name_ko": "Campaign - A prize",
                },
            ]
        }

        report = target.build_fix_report(catalog, review, write=True)

        self.assertEqual(report["summary"]["applied_rows"], 1)
        self.assertEqual(report["summary"]["skipped_rows"], 1)
        self.assertEqual(catalog["items"][0]["name_ko"], "Campaign - A prize Figure")
        self.assertEqual(catalog["items"][1]["name_ko"], "Campaign - A prize mystery item")

    def test_dry_run_does_not_mutate_catalog(self) -> None:
        catalog = {"items": [{"catalog_index": 1, "name_ko": "Campaign - Figure"}]}
        review = {
            "review_rows": [
                {
                    "catalog_index": 1,
                    "series_name": "Campaign",
                    "prize_rank": "A prize",
                    "prize_item_name": "Figure",
                    "display_name_ko": "Campaign - Figure",
                    "expected_display_name_ko": "Campaign - A prize Figure",
                }
            ]
        }

        report = target.build_fix_report(catalog, review, write=False)

        self.assertEqual(report["summary"]["applied_rows"], 1)
        self.assertFalse(report["summary"]["write"])
        self.assertEqual(catalog["items"][0]["name_ko"], "Campaign - Figure")


if __name__ == "__main__":
    unittest.main()
