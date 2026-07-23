from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_animation_category_action_queue_public as action


class BuildAnimationCategoryActionQueuePublicTest(unittest.TestCase):
    def test_build_queue_creates_manual_mapping_templates(self) -> None:
        payload = {
            "app_folder_visual_catalog": {
                "color_count": 188,
                "icon_count": 211,
                "icon_group_count": 9,
                "palette_section_count": 8,
                "palette_sorted_by_family": True,
                "animation_visuals_covered": True,
            },
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
                            "sample_names": [
                                "Big acrylic stand",
                                "Acrylic keyring",
                                "Clear file set",
                            ],
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

        unmatched_keyword_review = {
            "summary": {
                "unmatched_rows": 42,
                "token_candidate_count": 7,
                "product_type_candidate_count": 2,
            },
            "top_product_type_candidates": [
                {"source_category": "Goods", "token": "stand", "row_count": 6},
            ],
        }

        report = action.build_queue(
            payload,
            max_categories=1,
            batch_size=1,
            unmatched_keyword_review=unmatched_keyword_review,
        )

        self.assertEqual(report["summary"]["actionable_categories"], 2)
        self.assertEqual(report["summary"]["queued_categories"], 1)
        self.assertEqual(report["summary"]["queued_catalog_rows"], 97)
        self.assertEqual(report["summary"]["split_review_categories"], 1)
        self.assertEqual(report["summary"]["direct_mapping_categories"], 1)
        self.assertEqual(report["summary"]["work_order_steps"], 2)
        self.assertEqual(
            report["summary"]["work_order_lanes"],
            ["name_level_split_review", "unmatched_keyword_review"],
        )
        self.assertEqual(report["summary"]["split_first_blocked_categories"], ["Acrylic"])
        self.assertEqual(report["summary"]["unmatched_keyword_review_rows"], 42)
        self.assertEqual(report["summary"]["unmatched_keyword_candidate_count"], 7)
        self.assertEqual(report["summary"]["unmatched_keyword_product_type_candidate_count"], 2)
        self.assertEqual(report["summary"]["app_folder_color_count"], 188)
        self.assertEqual(report["summary"]["app_folder_icon_option_count"], 211)
        self.assertTrue(report["summary"]["app_folder_palette_sorted_by_family"])
        self.assertTrue(report["summary"]["app_animation_visuals_covered"])
        self.assertEqual(report["app_folder_visual_catalog"]["icon_group_count"], 9)
        self.assertEqual(
            report["summary"]["by_mapping_mode"],
            [("name_level_split_review_required", 1), ("direct_category_mapping_review", 1)],
        )
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_category_changes"])
        self.assertFalse(report["automation_policy"]["auto_create_folders"])
        self.assertEqual(len(report["work_order"]), 2)
        self.assertEqual(report["work_order"][0]["lane"], "name_level_split_review")
        self.assertEqual(report["work_order"][0]["category_count"], 1)
        self.assertEqual(report["work_order"][0]["affected_catalog_rows"], 97)
        self.assertEqual(
            report["work_order"][0]["next_step"],
            "confirm_animation_category_name_split_templates",
        )
        self.assertEqual(
            report["work_order"][0]["blocked_direct_mapping_categories"],
            ["Acrylic"],
        )
        self.assertTrue(report["work_order"][0]["manual_confirmation_required"])
        self.assertFalse(report["work_order"][0]["auto_apply_enabled"])
        self.assertEqual(report["work_order"][1]["lane"], "unmatched_keyword_review")
        self.assertEqual(report["work_order"][1]["affected_catalog_rows"], 42)
        self.assertEqual(report["work_order"][1]["token_candidate_count"], 7)
        self.assertEqual(report["work_order"][1]["product_type_candidate_count"], 2)
        self.assertEqual(report["work_order"][1]["top_product_type_candidate_count"], 1)
        self.assertEqual(report["work_order"][1]["top_product_type_candidates"][0]["token"], "stand")
        self.assertEqual(
            report["work_order"][1]["next_step"],
            "review_unmatched_animation_keyword_candidates",
        )
        self.assertTrue(report["work_order"][1]["manual_confirmation_required"])
        self.assertFalse(report["work_order"][1]["auto_apply_enabled"])
        batch = report["batches"][0]
        self.assertEqual(batch["review_state"], "manual_category_mapping_confirmation_required")
        self.assertEqual(batch["next_machine_step"], "fill_confirmed_animation_category_mapping_templates")
        self.assertEqual(batch["manual_confirmation_template"], "server/animation_category_confirmed_rows.template.json")
        self.assertEqual(batch["import_tool"], "tools/import_confirmed_animation_category_rows.py")
        self.assertEqual(batch["unblocks_when"], "category_mapping_manually_confirmed")
        self.assertEqual(batch["categories"][0]["mapping_mode"], "name_level_split_review_required")
        self.assertTrue(batch["categories"][0]["requires_name_level_split_review"])
        self.assertEqual(batch["categories"][0]["confirmed_queue"], "server/animation_category_confirmed_rows.json")
        self.assertEqual(
            batch["categories"][0]["review_summary"]["recommended_review_path"],
            "review_name_split_hints_before_category_mapping",
        )
        self.assertEqual(batch["categories"][0]["review_summary"]["name_split_hint_count"], 3)
        hint_keys = {
            hint["hint_key"]
            for hint in batch["categories"][0]["name_split_hints"]
        }
        self.assertEqual(hint_keys, {"acrylic_stand", "acrylic_keyring", "clear_file"})
        template = batch["categories"][0]["category_mapping_template"]
        self.assertFalse(template["manual_confirmed"])
        self.assertEqual(template["mapping_mode"], "name_level_split_review_required")
        self.assertTrue(template["requires_name_level_split_review"])
        self.assertEqual(template["source_category"], "Acrylic")
        self.assertEqual(template["target_category"], "Acrylic Stand")
        self.assertEqual(template["folder_icon_key"], "view_carousel")
        self.assertEqual(template["blocked_until"], "category_mapping_manually_confirmed")
        self.assertEqual(
            report["automation_policy"]["manual_confirmation_template"],
            "server/animation_category_confirmed_rows.template.json",
        )


if __name__ == "__main__":
    unittest.main()
