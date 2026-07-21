from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_animation_category_action_queue_public as action


class BuildAnimationCategoryActionQueuePublicTest(unittest.TestCase):
    def test_build_queue_creates_manual_mapping_templates(self) -> None:
        payload = {
            "batches": [
                {
                    "categories": [
                        {
                            "category": "Acrylic",
                            "rows": 97,
                            "review_priority": 20,
                            "suggested_family": "acrylic",
                            "suggested_category": "Acrylic Stand",
                            "suggested_color_group": "blue",
                            "suggested_color_hint": "sky",
                            "suggested_color_hex": "0xFF7DB7FF",
                            "suggested_color_sort_order": 220,
                            "suggested_primary_icon_key": "view_carousel",
                            "suggested_icon_options": ["view_carousel", "standee"],
                            "review_reason": "Split broad acrylic rows first.",
                            "sample_names": ["Big acrylic stand"],
                            "folder_template": {
                                "folder_name": "Acrylic Stand",
                                "family": "acrylic",
                                "color_hex": "0xFF7DB7FF",
                                "color_hint": "sky",
                                "color_group": "blue",
                                "color_sort_order": 220,
                                "primary_icon_key": "view_carousel",
                                "icon_options": ["view_carousel", "standee"],
                            },
                        },
                        {
                            "category": "Charm",
                            "rows": 12,
                            "review_priority": 30,
                            "suggested_family": "keyring",
                            "suggested_category": "Keyring",
                            "suggested_color_group": "yellow",
                            "suggested_color_hint": "amber",
                            "suggested_primary_icon_key": "local_offer",
                        },
                    ]
                }
            ]
        }

        report = action.build_queue(payload, max_categories=1, batch_size=1)

        self.assertEqual(report["summary"]["actionable_categories"], 2)
        self.assertEqual(report["summary"]["queued_categories"], 1)
        self.assertEqual(report["summary"]["queued_catalog_rows"], 97)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_category_changes"])
        self.assertFalse(report["automation_policy"]["auto_create_folders"])
        batch = report["batches"][0]
        self.assertEqual(batch["review_state"], "manual_category_mapping_confirmation_required")
        self.assertEqual(batch["next_machine_step"], "fill_confirmed_animation_category_mapping_templates")
        template = batch["categories"][0]["category_mapping_template"]
        self.assertFalse(template["manual_confirmed"])
        self.assertEqual(template["source_category"], "Acrylic")
        self.assertEqual(template["target_category"], "Acrylic Stand")
        self.assertEqual(template["folder_icon_key"], "view_carousel")
        self.assertEqual(template["blocked_until"], "category_mapping_manually_confirmed")


if __name__ == "__main__":
    unittest.main()
