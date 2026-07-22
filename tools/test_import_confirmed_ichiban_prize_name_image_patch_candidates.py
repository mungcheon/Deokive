from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_confirmed_ichiban_prize_name_image_patch_candidates as importer


class ImportConfirmedIchibanPrizeNameImagePatchCandidatesTest(unittest.TestCase):
    def test_dry_run_reports_confirmed_changes_without_mutating_catalog(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "old ko",
                    "name_ja": "old ja",
                    "sub_series": "A賞",
                    "image_url": "old.jpg",
                }
            ]
        }
        candidates = {
            "candidates": [
                {
                    "manual_confirmed": True,
                    "catalog_patch_template": {
                        "catalog_index": 1,
                        "name_ko": "new ko",
                        "name_ja": "new ja",
                        "sub_series": "モバイルくじ A賞",
                        "image_url": "new.jpg",
                        "evidence_url": "https://1kuji.com/products/demo",
                        "manual_confirmed": True,
                    },
                }
            ]
        }

        report = importer.build_import_report(catalog, candidates, write=False)

        self.assertEqual(report["summary"]["confirmed_rows"], 1)
        self.assertEqual(report["summary"]["applied_rows"], 1)
        self.assertFalse(report["summary"]["write"])
        self.assertEqual(report["applied_rows"][0]["field_changes"]["name_ja"]["to"], "new ja")
        self.assertEqual(catalog["items"][0]["name_ja"], "old ja")

    def test_write_mutates_only_double_confirmed_templates(self) -> None:
        catalog = {
            "items": [
                {"catalog_index": 1, "sub_series": "A賞"},
                {"catalog_index": 2, "sub_series": "B賞"},
            ]
        }
        candidates = {
            "candidates": [
                {
                    "manual_confirmed": True,
                    "catalog_patch_template": {
                        "catalog_index": 1,
                        "sub_series": "公式 A賞",
                        "manual_confirmed": True,
                    },
                },
                {
                    "manual_confirmed": True,
                    "catalog_patch_template": {
                        "catalog_index": 2,
                        "sub_series": "公式 B賞",
                        "manual_confirmed": False,
                    },
                },
            ]
        }

        report = importer.build_import_report(catalog, candidates, write=True)

        self.assertEqual(report["summary"]["confirmed_rows"], 1)
        self.assertEqual(report["summary"]["applied_rows"], 1)
        self.assertEqual(catalog["items"][0]["sub_series"], "公式 A賞")
        self.assertEqual(catalog["items"][1]["sub_series"], "B賞")


if __name__ == "__main__":
    unittest.main()
