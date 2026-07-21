from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_animation_category_review_batches_public as batches


class BuildAnimationCategoryReviewBatchesPublicTest(unittest.TestCase):
    def test_build_report_keeps_taxonomy_manual_and_exposes_folder_ui_tokens(self) -> None:
        source = {
            "folder_color_palette": [
                {"color_hint": "yellow", "color_hex": "0xFFFFD84D", "sort_order": 40, "color_group": "warm"},
                {"color_hint": "blue", "color_hex": "0xFF5BA7F7", "sort_order": 90, "color_group": "cool"},
            ],
            "folder_visual_tokens": [
                {
                    "category": "Keyring",
                    "family": "keyring",
                    "color_sort_order": 40,
                    "primary_icon_key": "local_offer",
                    "icon_options": ["local_offer", "vpn_key", "sell", "loyalty"],
                },
                {
                    "category": "Acrylic Stand",
                    "family": "acrylic",
                    "color_sort_order": 90,
                    "primary_icon_key": "view_carousel",
                    "icon_options": ["view_carousel", "layers", "photo_library", "filter_frames"],
                },
            ],
        }
        queue = [
            {
                "category": "Charm",
                "rows": 23,
                "review_priority": 30,
                "suggested_family": "keyring",
                "suggested_category": "Keyring",
                "suggested_color_hint": "yellow",
                "suggested_color_hex": "0xFFFFD84D",
                "suggested_color_group": "warm",
                "suggested_color_sort_order": 40,
                "suggested_primary_icon_key": "local_offer",
                "suggested_icon_options": ["local_offer", "vpn_key", "sell", "loyalty"],
                "review_reason": "Charm items usually behave like keyrings.",
                "sample_names": ["Sample charm"],
            },
            {
                "category": "Acrylic",
                "rows": 97,
                "review_priority": 20,
                "suggested_family": "acrylic",
                "suggested_category": "Acrylic Stand",
                "suggested_color_hint": "blue",
                "suggested_color_hex": "0xFF5BA7F7",
                "suggested_color_group": "cool",
                "suggested_color_sort_order": 90,
                "suggested_primary_icon_key": "view_carousel",
                "suggested_icon_options": ["view_carousel", "layers", "photo_library", "filter_frames"],
                "review_reason": "Most acrylic goods should be split after name review.",
                "sample_names": ["Sample acrylic stand"],
            },
        ]

        report = batches.build_report(source, queue, batch_size=1)

        self.assertEqual(report["summary"]["source_categories"], 2)
        self.assertEqual(report["summary"]["source_rows"], 120)
        self.assertEqual(report["summary"]["batch_count"], 2)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["folder_template_count"], 2)
        self.assertEqual(report["summary"]["by_suggested_color_group"], [("cool", 1), ("warm", 1)])
        self.assertEqual(report["summary"]["folder_icon_family_count"], 2)
        self.assertFalse(report["automation_policy"]["auto_apply_category_changes"])
        self.assertFalse(report["automation_policy"]["auto_apply_folder_visuals"])
        self.assertEqual(
            report["batches"][0]["folder_creation_blocked_until"],
            "category_mapping_manually_confirmed",
        )
        self.assertEqual(
            report["batches"][0]["categories"][0]["folder_template"]["primary_icon_key"],
            "view_carousel",
        )
        self.assertEqual(report["batches"][1]["folder_templates"][0]["color_sort_order"], 40)
        self.assertEqual(report["batches"][1]["folder_templates"][0]["color_group"], "warm")
        self.assertEqual(report["batches"][0]["categories"][0]["category"], "Acrylic")
        self.assertEqual(report["batches"][1]["categories"][0]["suggested_color_hint"], "yellow")
        self.assertEqual(report["folder_color_palette"][0]["color_group"], "warm")
        self.assertGreaterEqual(report["folder_icon_catalog"][0]["icon_count"], 4)


if __name__ == "__main__":
    unittest.main()
