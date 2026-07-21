from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_animation_category_review_batches_public as batches


class BuildAnimationCategoryReviewBatchesPublicTest(unittest.TestCase):
    def test_build_report_keeps_taxonomy_manual_and_sorts_color_tokens(self) -> None:
        source = {
            "folder_color_palette": [
                {"color_hint": "yellow", "color_hex": "0xFFFFD84D", "sort_order": 40},
                {"color_hint": "blue", "color_hex": "0xFF5BA7F7", "sort_order": 90},
            ],
            "folder_visual_tokens": [
                {"category": "키링", "color_sort_order": 40, "primary_icon_key": "local_offer"},
                {"category": "아크릴 스탠드", "color_sort_order": 90, "primary_icon_key": "view_carousel"},
            ],
        }
        queue = [
            {
                "category": "참",
                "rows": 23,
                "review_priority": 30,
                "suggested_family": "keyring",
                "suggested_category": "키링",
                "suggested_color_hint": "yellow",
                "suggested_color_hex": "0xFFFFD84D",
                "suggested_color_sort_order": 40,
                "suggested_primary_icon_key": "local_offer",
                "suggested_icon_options": ["local_offer", "vpn_key"],
                "review_reason": "Charm items usually behave like keyrings.",
                "sample_names": ["ラバーチャーム"],
            },
            {
                "category": "아크릴",
                "rows": 97,
                "review_priority": 20,
                "suggested_family": "acrylic",
                "suggested_category": "아크릴 스탠드",
                "suggested_color_hint": "blue",
                "suggested_color_hex": "0xFF5BA7F7",
                "suggested_color_sort_order": 90,
                "suggested_primary_icon_key": "view_carousel",
                "suggested_icon_options": ["view_carousel", "layers"],
                "review_reason": "Most acrylic goods should be split after name review.",
                "sample_names": ["アクリルスタンド"],
            },
        ]

        report = batches.build_report(source, queue, batch_size=1)

        self.assertEqual(report["summary"]["source_categories"], 2)
        self.assertEqual(report["summary"]["source_rows"], 120)
        self.assertEqual(report["summary"]["batch_count"], 2)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["folder_template_count"], 2)
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
        self.assertEqual(report["batches"][0]["categories"][0]["category"], "아크릴")
        self.assertEqual(report["batches"][1]["categories"][0]["suggested_color_hint"], "yellow")


if __name__ == "__main__":
    unittest.main()
