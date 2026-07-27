from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_field_update_work_packs as target


def item(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "priority": 10,
        "row_index": 7,
        "field": "source_url",
        "workstream": "animation_goods_official_detail_backfill",
        "source_store": "Animate",
        "category": "Badge",
        "applicability": "actionable",
        "risk": "medium",
        "strategy": "official_maker_or_retailer_lookup",
        "field_action": "attach_exact_official_detail_url",
        "automation_candidate": True,
        "actionable_now": True,
        "name_ko": "Sample Badge",
        "name_ja": "サンプルバッジ",
        "source_url": "",
        "search_url": "https://example.com/search?q=sample",
        "acceptance_criteria": "Exact product page.",
    }
    row.update(overrides)
    return row


class BuildFieldUpdateWorkPacksTests(unittest.TestCase):
    def test_build_work_packs_excludes_image_and_non_actionable_by_default(self) -> None:
        packs = target.build_work_packs(
            [
                item(field="source_url", row_index=1),
                item(field="image_url", row_index=2),
                item(field="barcode", row_index=3, actionable_now=False, applicability="not_publicly_available"),
            ],
            pack_size=10,
        )

        self.assertEqual(1, len(packs))
        self.assertEqual("source_url", packs[0]["field"])
        self.assertEqual(1, packs[0]["rows"])
        self.assertEqual("data/intake/field_updates/incoming", packs[0]["output_contract"]["intake_dir"])
        self.assertFalse(packs[0]["auto_apply_enabled"])
        self.assertIn("tools/import_agent_catalog_field_updates.py", packs[0]["verification_commands"][1])
        self.assertEqual(
            "https://...",
            packs[0]["target_rows"][0]["required_update_shape"]["value"],
        )

    def test_build_work_packs_can_include_non_actionable_for_research_handoff(self) -> None:
        packs = target.build_work_packs(
            [
                item(
                    field="barcode",
                    row_index=3,
                    actionable_now=False,
                    applicability="not_publicly_available",
                    risk="high",
                )
            ],
            include_non_actionable=True,
        )

        self.assertEqual(1, len(packs))
        self.assertEqual("barcode", packs[0]["field"])
        self.assertIn("Do not import yet", packs[0]["next_action"])
        self.assertEqual(
            "0000000000000",
            packs[0]["target_rows"][0]["required_update_shape"]["value"],
        )

    def test_build_work_packs_balances_fields_when_limited(self) -> None:
        rows = [
            item(field="source_url", row_index=index, category=f"Source {index}")
            for index in range(8)
        ]
        rows.extend(
            [
                item(field="release_date", row_index=20, category="Release"),
                item(field="official_price_jpy", row_index=21, category="Price", risk="high"),
                item(field="barcode", row_index=22, category="Barcode", risk="high"),
            ]
        )

        packs = target.build_work_packs(rows, pack_size=1, limit=4)

        self.assertEqual(4, len(packs))
        self.assertEqual(
            {"source_url", "release_date", "official_price_jpy", "barcode"},
            {pack["field"] for pack in packs},
        )

    def test_write_packs_outputs_manifest_and_pack_files(self) -> None:
        packs = target.build_work_packs([item(field="release_date", row_index=8)], pack_size=10)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "packs"
            manifest = target.write_packs(packs, output_dir)

            self.assertEqual(1, manifest["pack_count"])
            self.assertEqual(1, manifest["target_rows"])
            self.assertEqual("data/intake/field_updates/agent_catalog_field_update.schema.json", manifest["field_update_schema"])
            self.assertTrue((output_dir / "manifest.json").is_file())
            pack_path = output_dir / Path(manifest["packs"][0]["path"]).name
            self.assertTrue(pack_path.is_file())
            pack_payload = json.loads(pack_path.read_text(encoding="utf-8"))
            self.assertEqual("release_date", pack_payload["field"])
            self.assertEqual("YYYY-MM-DD", pack_payload["target_rows"][0]["required_update_shape"]["value"])


if __name__ == "__main__":
    unittest.main()
