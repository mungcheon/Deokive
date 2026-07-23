from __future__ import annotations

import sys
import unittest
import re
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_animation_goods_categories as audit


class AnimationGoodsCategoryAuditTests(unittest.TestCase):
    def test_category_visuals_include_icon_and_color_hints(self) -> None:
        rows = [
            {
                "source_store": "\uc560\ub2c8\uba54\uc774\ud2b8",
                "category": "\ud53c\uaddc\uc5b4",
                "name_ko": "figure",
            },
            {
                "source_store": "\uc560\ub2c8\uba54\uc774\ud2b8",
                "category": "\uce94\ubc43\uc9c0",
                "name_ko": "badge",
            },
        ]

        result = audit.build_audit(rows)
        visuals = {item["category"]: item for item in result["category_visuals"]}

        self.assertEqual(visuals["\ud53c\uaddc\uc5b4"]["family"], "figure")
        self.assertEqual(visuals["\ud53c\uaddc\uc5b4"]["recommended_icon_key"], "toys")
        self.assertEqual(visuals["\ud53c\uaddc\uc5b4"]["recommended_color_hex"], "0xFF28D6C8")
        self.assertEqual(visuals["\uce94\ubc43\uc9c0"]["recommended_color_hint"], "red")

    def test_other_goods_category_gets_canonical_suggestion(self) -> None:
        rows = [
            {
                "source_store": "\uc560\ub2c8\uba54\uc774\ud2b8",
                "category": "\uae30\ud0c0 \uad7f\uc988",
                "name_ko": "misc goods",
            },
        ]

        result = audit.build_audit(rows)

        self.assertEqual(
            result["normalization_suggestions"][0]["suggested_category"],
            "\uc561\uc138\uc11c\ub9ac",
        )

    def test_requested_taxonomy_categories_have_folder_families(self) -> None:
        rows = [
            {
                "source_store": "\uc560\ub2c8\uba54\uc774\ud2b8",
                "category": category,
                "name_ko": category,
            }
            for category in [
                "\ubcf4\ub4dc",
                "\uc0c9\uc9c0",
                "\uc544\ud06c\ub9b4 \ud0a4\ub9c1",
                "\uce74\ub4dc/\ube0c\ub85c\ub9c8\uc774\ub4dc",
                "\ucf5c\ub77c\ubcf4 \uad7f\uc988",
                "\uad7f\uc988",
                "\uc544\ud06c\ub9b4",
            ]
        ]

        result = audit.build_audit(rows)
        visuals = {item["category"]: item for item in result["category_visuals"]}
        unknown = {item["category"] for item in result["unknown_categories"]}

        self.assertEqual(visuals["\ubcf4\ub4dc"]["family"], "display_goods")
        self.assertEqual(visuals["\uc0c9\uc9c0"]["family"], "stationery")
        self.assertEqual(visuals["\uc544\ud06c\ub9b4 \ud0a4\ub9c1"]["family"], "keyring")
        self.assertEqual(visuals["\uce74\ub4dc/\ube0c\ub85c\ub9c8\uc774\ub4dc"]["family"], "stationery")
        self.assertEqual(visuals["\ucf5c\ub77c\ubcf4 \uad7f\uc988"]["family"], "fan_goods")
        self.assertNotIn("\ubcf4\ub4dc", unknown)
        self.assertNotIn("\uc0c9\uc9c0", unknown)
        self.assertNotIn("\uc544\ud06c\ub9b4 \ud0a4\ub9c1", unknown)
        self.assertNotIn("\uce74\ub4dc/\ube0c\ub85c\ub9c8\uc774\ub4dc", unknown)
        self.assertNotIn("\ucf5c\ub77c\ubcf4 \uad7f\uc988", unknown)
        self.assertIn("\uad7f\uc988", unknown)
        self.assertIn("\uc544\ud06c\ub9b4", unknown)

    def test_load_rows_accepts_public_catalog_shape(self) -> None:
        payload = {
            "meta": {"row_count": 1},
            "items": [
                {
                    "source_store": "\uc560\ub2c8\uba54\uc774\ud2b8",
                    "category": "\ud53c\uaddc\uc5b4",
                    "name_ko": "figure",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            rows = audit._load_rows(path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "\ud53c\uaddc\uc5b4")

    def test_visual_hints_exist_in_app_catalogs(self) -> None:
        root = Path(__file__).resolve().parent.parent
        icon_source = (root / "lib" / "config" / "app_icon_catalog.dart").read_text(encoding="utf-8")
        palette_source = (root / "lib" / "config" / "app_palette_catalog.dart").read_text(encoding="utf-8")
        icon_keys = set(re.findall(r"AppIconOption\(\s*key: '([^']+)'", icon_source, re.S))
        folder_color_hexes = {
            "0x" + value.upper()
            for value in re.findall(r"Color\(0x([0-9A-Fa-f]{8})\)", palette_source)
        }

        for visual in audit.FAMILY_VISUALS.values():
            self.assertIn(visual["icon_key"], icon_keys)
            self.assertIn(visual["color_hex"], folder_color_hexes)


if __name__ == "__main__":
    unittest.main()
