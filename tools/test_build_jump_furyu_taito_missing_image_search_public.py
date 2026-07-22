from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_jump_furyu_taito_missing_image_search_public as target


class JumpFuryuTaitoMissingImageSearchPublicTests(unittest.TestCase):
    def test_build_report_keeps_rows_review_only(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "jump",
                    "source_store": target.JUMP_STORE,
                    "category": "mascot",
                    "affiliation": "series",
                    "image_url": None,
                },
                {
                    "catalog_index": 2,
                    "name_ko": "furyu",
                    "source_store": target.FURYU_STORE,
                    "category": "figure",
                    "affiliation": "series",
                    "image_url": None,
                },
                {
                    "catalog_index": 3,
                    "name_ko": "taito",
                    "source_store": target.TAITO_STORE,
                    "category": "figure",
                    "affiliation": "series",
                    "image_url": None,
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": target.JUMP_STORE,
                    "query": "jump",
                    "search_url": "https://jumpcs.shueisha.co.jp/shop/goods/search.aspx?keyword=jump",
                    "strategy": "manual_official_search_review",
                    "automation_safety": "manual_confirmation_required",
                },
                {
                    "row_index": 2,
                    "source_store": target.FURYU_STORE,
                    "query": "furyu",
                    "search_url": "https://furyuprize.com/search?keyword=furyu",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                },
                {
                    "row_index": 3,
                    "source_store": target.TAITO_STORE,
                    "query": "taito",
                    "search_url": "https://www.taito.co.jp/prize?keyword=taito",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                },
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["missing_target_image_rows"], 3)
        self.assertEqual(report["summary"]["matched_queue_rows"], 3)
        self.assertEqual(report["summary"]["official_search_url_rows"], 3)
        self.assertEqual(report["summary"]["by_store"][target.JUMP_STORE], 1)
        self.assertEqual(report["summary"]["by_store"][target.FURYU_STORE], 1)
        self.assertEqual(report["summary"]["by_store"][target.TAITO_STORE], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])
        self.assertTrue(all(item["manual_review_required"] for item in report["items"]))


if __name__ == "__main__":
    unittest.main()
