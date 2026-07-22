from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_app_folder_visual_catalog as audit


class AppFolderVisualCatalogAuditTests(unittest.TestCase):
    def test_build_reports_icon_color_sections_and_animation_visual_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            icon_source = root / "icons.dart"
            palette_source = root / "palette.dart"
            animation_audit = root / "animation.json"

            icon_source.write_text(
                """
                AppIconOption(key: 'toys', icon: Icons.toys_rounded, label: 'Figure', group: 'Goods'),
                AppIconOption(key: 'badge', icon: Icons.badge_rounded, label: 'Badge', group: 'Goods'),
                """,
                encoding="utf-8",
            )
            palette_source.write_text(
                """
                // Mint
                Color(0xFF28D6C8),
                // Red
                Color(0xFFD64562),
                """,
                encoding="utf-8",
            )
            animation_audit.write_text(
                json.dumps(
                    {
                        "category_visuals": [
                            {
                                "category": "Figure",
                                "recommended_icon_key": "toys",
                                "recommended_color_hex": "0xFF28D6C8",
                            },
                            {
                                "category": "Badge",
                                "recommended_icon_key": "badge",
                                "recommended_color_hex": "0xFFD64562",
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = audit.build(icon_source, palette_source, animation_audit)

        self.assertEqual(payload["icon_count"], 2)
        self.assertEqual(payload["color_count"], 2)
        self.assertEqual(payload["palette_section_count"], 2)
        self.assertFalse(payload["palette_sorted_by_family"])
        self.assertTrue(payload["animation_visuals_covered"])
        self.assertEqual(payload["duplicate_icon_keys"], [])
        self.assertEqual(payload["duplicate_colors"], [])
        self.assertEqual(
            [item["section"] for item in payload["palette_color_families"]],
            ["Mint", "Red"],
        )
        self.assertEqual(
            [item["picker_sort_key"] for item in payload["palette_picker_order"]],
            ["99-000", "100-000"],
        )

    def test_build_flags_missing_animation_visuals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            icon_source = root / "icons.dart"
            palette_source = root / "palette.dart"
            animation_audit = root / "animation.json"

            icon_source.write_text(
                "AppIconOption(key: 'toys', icon: Icons.toys_rounded, label: 'Figure', group: 'Goods'),",
                encoding="utf-8",
            )
            palette_source.write_text("Color(0xFF28D6C8),", encoding="utf-8")
            animation_audit.write_text(
                json.dumps(
                    {
                        "category_visuals": [
                            {
                                "category": "Badge",
                                "recommended_icon_key": "badge",
                                "recommended_color_hex": "0xFFD64562",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            payload = audit.build(icon_source, palette_source, animation_audit)

        self.assertFalse(payload["animation_visuals_covered"])
        self.assertEqual(payload["missing_animation_icons"], ["badge"])
        self.assertEqual(payload["missing_animation_colors"], ["0xFFD64562"])

    def test_palette_sort_audit_accepts_color_family_sections(self) -> None:
        rows = [
            {"section": "Rose, red, pink", "color": "0xFFE11D48", "hue": 348.0, "lightness": 0.5},
            {"section": "Rose, red, pink", "color": "0xFFFF6FAE", "hue": 334.0, "lightness": 0.72},
            {"section": "Peach, orange, amber, yellow", "color": "0xFFF97316", "hue": 25.0, "lightness": 0.53},
            {"section": "Peach, orange, amber, yellow", "color": "0xFFFFD84D", "hue": 46.0, "lightness": 0.65},
            {"section": "Sand and warm neutrals", "color": "0xFFC8A978", "hue": 37.0, "lightness": 0.63},
            {"section": "Olive and green", "color": "0xFF84CC16", "hue": 83.0, "lightness": 0.44},
            {"section": "Mint, teal, cyan", "color": "0xFF28D6C8", "hue": 175.0, "lightness": 0.5},
            {"section": "Sky and blue", "color": "0xFF3B82F6", "hue": 217.0, "lightness": 0.6},
            {"section": "Indigo, violet, purple", "color": "0xFF8B5CF6", "hue": 258.0, "lightness": 0.66},
            {"section": "Neutrals", "color": "0xFFFFFFFF", "hue": 0.0, "lightness": 1.0},
            {"section": "Neutrals", "color": "0xFF1F2937", "hue": 215.0, "lightness": 0.17},
        ]

        result = audit._palette_sort_audit(rows)

        self.assertTrue(result["section_order_monotonic"])
        self.assertTrue(result["sections_locally_sorted"])

    def test_palette_picker_order_keeps_family_sections_adjacent(self) -> None:
        rows = [
            {"section": "Rose, red, pink", "color": "0xFFE11D48", "hue": 348.0, "lightness": 0.5},
            {"section": "Rose, red, pink", "color": "0xFFFF6FAE", "hue": 334.0, "lightness": 0.72},
            {"section": "Sky and blue", "color": "0xFF3B82F6", "hue": 217.0, "lightness": 0.6},
        ]

        families = audit._palette_color_families(rows)
        picker_order = audit._palette_picker_order(rows)

        self.assertEqual([item["section"] for item in families], ["Rose, red, pink", "Sky and blue"])
        self.assertEqual([item["color_count"] for item in families], [2, 1])
        self.assertEqual(
            [item["picker_sort_key"] for item in picker_order],
            ["00-000", "00-001", "05-000"],
        )


if __name__ == "__main__":
    unittest.main()
