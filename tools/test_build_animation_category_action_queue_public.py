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
            normalization_review={
                "folder_visual_tokens": [
                    {
                        "category": "Stationery",
                        "family": "stationery",
                        "color_hint": "mint",
                        "color_hex": "0xFF7DD3C7",
                        "color_group": "mint",
                        "color_sort_order": 130,
                        "primary_icon_key": "sticky_note_2",
                        "icon_options": ["sticky_note_2", "edit_note"],
                    }
                ],
                "normalization_review_queue": [
                    {
                        "review_id": "animation-category-normalization-001",
                        "category": "Clear File",
                        "suggested_category": "Stationery",
                        "affected_catalog_rows": 8,
                        "review_reason": "Subtype-like category may work better as sub_series.",
                        "sample_names": ["Prize F clear file set"],
                        "category_mapping_template": {
                            "manual_confirmed": False,
                            "source_category": "Clear File",
                            "target_category": "Stationery",
                            "preserve_source_category_as_sub_series": True,
                            "affected_catalog_rows": 8,
                            "manual_note": "",
                        },
                    }
                ]
            },
        )

        self.assertEqual(report["summary"]["actionable_categories"], 2)
        self.assertEqual(report["summary"]["queued_categories"], 1)
        self.assertEqual(report["summary"]["queued_catalog_rows"], 97)
        self.assertEqual(report["summary"]["split_review_categories"], 1)
        self.assertEqual(report["summary"]["direct_mapping_categories"], 1)
        self.assertEqual(report["summary"]["work_order_steps"], 3)
        self.assertEqual(
            report["summary"]["work_order_lanes"],
            [
                "name_level_split_review",
                "canonical_category_normalization_review",
                "unmatched_keyword_review",
            ],
        )
        self.assertEqual(report["summary"]["split_first_blocked_categories"], ["Acrylic"])
        self.assertEqual(report["summary"]["unmatched_keyword_review_rows"], 42)
        self.assertEqual(report["summary"]["unmatched_keyword_candidate_count"], 7)
        self.assertEqual(report["summary"]["unmatched_keyword_product_type_candidate_count"], 2)
        self.assertEqual(report["summary"]["normalization_review_categories"], 1)
        self.assertEqual(report["summary"]["normalization_review_rows"], 8)
        self.assertEqual(report["summary"]["normalization_review_target_categories"], [("Stationery", 1)])
        self.assertEqual(report["summary"]["next_normalization_review_batch_rows"], 1)
        self.assertEqual(report["summary"]["next_normalization_review_batch_catalog_rows"], 8)
        self.assertEqual(
            report["summary"]["next_normalization_review_batch_target_categories"],
            [("Stationery", 1)],
        )
        self.assertEqual(report["summary"]["next_normalization_review_batch_preserve_sub_series_rows"], 1)
        self.assertEqual(report["summary"]["target_visual_token_rows"], 2)
        self.assertEqual(report["summary"]["target_visual_token_catalog_rows"], 105)
        self.assertEqual(report["summary"]["target_visual_color_groups"], [("mint", 1), ("blue", 1)])
        self.assertEqual(
            report["summary"]["target_visual_primary_icon_keys"],
            [("sticky_note_2", 1), ("view_carousel", 1)],
        )
        self.assertTrue(report["summary"]["target_visual_palette_ordered"])
        self.assertEqual(report["summary"]["app_folder_color_count"], 188)
        self.assertEqual(report["summary"]["app_folder_icon_option_count"], 211)
        self.assertTrue(report["summary"]["app_folder_palette_sorted_by_family"])
        self.assertTrue(report["summary"]["app_animation_visuals_covered"])
        self.assertEqual(report["app_folder_visual_catalog"]["icon_group_count"], 9)
        self.assertEqual(report["target_visual_token_summary"]["visual_token_rows"], 2)
        self.assertEqual(
            [
                token["color_sort_order"]
                for token in report["target_visual_token_summary"]["tokens"]
            ],
            [130, 220],
        )
        self.assertEqual(
            report["summary"]["by_mapping_mode"],
            [("name_level_split_review_required", 1), ("direct_category_mapping_review", 1)],
        )
        self.assertEqual(
            report["summary"]["by_blocked_reason"],
            [
                ("broad_source_category_requires_name_level_split", 1),
                ("direct_category_mapping_requires_sample_review", 1),
            ],
        )
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_category_changes"])
        self.assertFalse(report["automation_policy"]["auto_create_folders"])
        self.assertEqual(
            report["automation_policy"]["blocked_until_default"],
            "category_mapping_or_split_rules_manually_confirmed",
        )
        self.assertIn(
            "broad_categories_split_before_mapping",
            report["automation_policy"]["required_evidence"],
        )
        self.assertEqual(len(report["work_order"]), 3)
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
        self.assertEqual(
            report["work_order"][0]["blocked_reason"],
            "broad_source_category_requires_name_level_split",
        )
        self.assertIn(
            "confirmed_split_target_category_for_each_rule",
            report["work_order"][0]["required_evidence"],
        )
        self.assertEqual(report["work_order"][1]["lane"], "canonical_category_normalization_review")
        self.assertEqual(report["work_order"][1]["affected_catalog_rows"], 8)
        self.assertEqual(report["work_order"][1]["categories"], ["Clear File"])
        self.assertEqual(report["work_order"][1]["target_categories"], ["Stationery"])
        self.assertEqual(
            report["work_order"][1]["target_category_visual_tokens"][0]["primary_icon_key"],
            "sticky_note_2",
        )
        self.assertEqual(
            report["work_order"][1]["target_visual_token_summary"]["color_group_counts"],
            [("mint", 1)],
        )
        self.assertEqual(
            report["work_order"][1]["blocked_reason"],
            "subtype_category_may_need_sub_series_preservation",
        )
        self.assertEqual(report["work_order"][2]["lane"], "unmatched_keyword_review")
        self.assertEqual(report["work_order"][2]["affected_catalog_rows"], 42)
        self.assertEqual(report["work_order"][2]["token_candidate_count"], 7)
        self.assertEqual(report["work_order"][2]["product_type_candidate_count"], 2)
        self.assertEqual(report["work_order"][2]["top_product_type_candidate_count"], 1)
        self.assertEqual(report["work_order"][2]["top_product_type_candidates"][0]["token"], "stand")
        self.assertEqual(
            report["work_order"][2]["next_step"],
            "review_unmatched_animation_keyword_candidates",
        )
        self.assertTrue(report["work_order"][2]["manual_confirmation_required"])
        self.assertFalse(report["work_order"][2]["auto_apply_enabled"])
        self.assertEqual(
            report["work_order"][2]["blocked_reason"],
            "unmatched_product_type_keywords_need_review",
        )
        batch = report["batches"][0]
        self.assertEqual(batch["review_state"], "manual_category_mapping_confirmation_required")
        self.assertEqual(batch["target_visual_token_summary"]["color_group_counts"], [("blue", 1)])
        self.assertEqual(
            batch["target_visual_token_summary"]["tokens"][0]["primary_icon_key"],
            "view_carousel",
        )
        self.assertEqual(batch["next_machine_step"], "fill_confirmed_animation_category_mapping_templates")
        self.assertEqual(batch["manual_confirmation_template"], "server/animation_category_confirmed_rows.template.json")
        self.assertEqual(batch["import_tool"], "tools/import_confirmed_animation_category_rows.py")
        self.assertEqual(batch["unblocks_when"], "category_mapping_manually_confirmed")
        self.assertEqual(batch["categories"][0]["mapping_mode"], "name_level_split_review_required")
        self.assertTrue(batch["categories"][0]["requires_name_level_split_review"])
        self.assertEqual(batch["categories"][0]["confirmed_queue"], "server/animation_category_confirmed_rows.json")
        self.assertEqual(
            batch["categories"][0]["blocked_until"],
            "name_level_split_rules_manually_confirmed",
        )
        self.assertIn(
            "broad_category_not_mapped_to_single_folder",
            batch["categories"][0]["required_evidence"],
        )
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
        self.assertEqual(template["blocked_until"], "name_level_split_rules_manually_confirmed")
        self.assertEqual(template["blocked_reason"], "broad_source_category_requires_name_level_split")
        self.assertEqual(
            report["automation_policy"]["manual_confirmation_template"],
            "server/animation_category_confirmed_rows.template.json",
        )
        normalization_batch = report["batches"][1]
        normalization_row = normalization_batch["categories"][0]
        self.assertEqual(normalization_row["target_category_visual_token"]["color_hex"], "0xFF7DD3C7")
        self.assertEqual(normalization_row["suggested_primary_icon_key"], "sticky_note_2")
        self.assertEqual(
            normalization_row["category_mapping_template"]["folder_color_group"],
            "mint",
        )
        self.assertEqual(
            normalization_row["category_mapping_template"]["folder_icon_options"],
            ["sticky_note_2", "edit_note"],
        )
        self.assertEqual(
            normalization_row["normalization_decision_guidance"]["recommended_decision"],
            "normalize_to_target_category_preserve_source_sub_series",
        )
        self.assertEqual(
            normalization_row["normalization_decision_guidance"]["suggested_sub_series_value"],
            "Clear File",
        )
        self.assertIn(
            "source category remains useful as a subtype/search label",
            normalization_row["normalization_decision_guidance"]["required_evidence"],
        )
        self.assertEqual(
            normalization_batch["target_visual_token_summary"]["tokens"][0]["color_sort_order"],
            130,
        )
        next_normalization = report["next_normalization_review_batch"][0]
        self.assertFalse(next_normalization["manual_confirmed"])
        self.assertEqual(next_normalization["source_category"], "Clear File")
        self.assertEqual(next_normalization["target_category"], "Stationery")
        self.assertEqual(next_normalization["affected_catalog_rows"], 8)
        self.assertTrue(next_normalization["preserve_source_category_as_sub_series"])
        self.assertEqual(next_normalization["folder_color_group"], "mint")
        self.assertEqual(next_normalization["folder_icon_key"], "sticky_note_2")
        self.assertEqual(
            next_normalization["normalization_decision_guidance"]["target_category"],
            "Stationery",
        )
        self.assertEqual(
            next_normalization["normalization_decision_guidance"]["suggested_sub_series_value"],
            "Clear File",
        )
        self.assertEqual(
            next_normalization["category_mapping_template"]["target_category"],
            "Stationery",
        )
        self.assertIn(
            "manual_note",
            next_normalization["manual_value_fields_to_fill"],
        )
        self.assertIn(
            "Confirm sample names belong under the target canonical category.",
            next_normalization["operator_checklist"],
        )
        self.assertFalse(next_normalization["auto_apply_enabled"])


if __name__ == "__main__":
    unittest.main()
