from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_image_update_work_packs as target


class BuildImageUpdateWorkPacksTests(unittest.TestCase):
    def test_build_work_packs_groups_and_chunks_missing_image_rows(self) -> None:
        items = [
            {
                "row_index": index,
                "name_ko": f"샘플 {index}",
                "name_ja": f"サンプル {index}",
                "category": "피규어",
                "affiliation": "시리즈",
                "source_store": "FuRyu",
                "strategy": "official_search",
                "provider_status": "search_only",
                "automation_safety": "candidate_provider_script_required",
                "priority": 10,
                "query": f"サンプル {index}",
                "search_url": f"https://example.com/search?q={index}",
            }
            for index in (3, 1, 2)
        ]

        packs = target.build_work_packs(items, pack_size=2, limit=10)

        self.assertEqual(2, len(packs))
        self.assertEqual(2, packs[0]["rows"])
        self.assertEqual(1, packs[1]["rows"])
        self.assertEqual([1, 2], [row["catalog_index"] for row in packs[0]["target_rows"]])
        self.assertEqual(3, packs[1]["target_rows"][0]["catalog_index"])
        self.assertIn("data/intake/image_updates/incoming", packs[0]["output_contract"])
        self.assertEqual(
            "https://...",
            packs[0]["target_rows"][0]["required_update_shape"]["image_url"],
        )

    def test_manual_confirmation_packs_sort_after_provider_script_packs(self) -> None:
        items = [
            {
                "row_index": 1,
                "source_store": "Manual Store",
                "category": "badge",
                "strategy": "manual_official_search_review",
                "provider_status": "search_only_manual",
                "automation_safety": "manual_confirmation_required",
                "priority": 20,
            },
            {
                "row_index": 2,
                "source_store": "FuRyu",
                "category": "figure",
                "strategy": "official_search",
                "provider_status": "search_only",
                "automation_safety": "candidate_provider_script_required",
                "priority": 10,
            },
        ]

        packs = target.build_work_packs(items, pack_size=10, limit=10)

        self.assertEqual("FuRyu", packs[0]["source_store"])
        self.assertEqual("candidate_provider_script_required", packs[0]["automation_safety"])

    def test_write_packs_creates_manifest_and_pack_files(self) -> None:
        packs = target.build_work_packs(
            [
                {
                    "row_index": 7,
                    "name_ko": "샘플",
                    "source_store": "FuRyu",
                    "category": "피규어",
                    "strategy": "official_search",
                    "provider_status": "search_only",
                    "automation_safety": "candidate_provider_script_required",
                    "priority": 10,
                }
            ],
            pack_size=10,
            limit=10,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "packs"
            manifest = target.write_packs(packs, output_dir)

            self.assertEqual(1, manifest["pack_count"])
            self.assertEqual(1, manifest["target_rows"])
            self.assertTrue((output_dir / "manifest.json").is_file())
            pack_path = output_dir / f"{packs[0]['pack_id']}.json"
            self.assertTrue(pack_path.is_file())
            saved_pack = json.loads(pack_path.read_text(encoding="utf-8"))
            self.assertEqual(7, saved_pack["target_rows"][0]["catalog_index"])


if __name__ == "__main__":
    unittest.main()
