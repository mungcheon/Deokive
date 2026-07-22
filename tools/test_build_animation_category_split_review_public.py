from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_animation_category_split_review_public as split_review


class BuildAnimationCategorySplitReviewPublicTest(unittest.TestCase):
    def test_build_report_creates_name_level_templates(self) -> None:
        payload = {
            "batches": [
                {
                    "categories": [
                        {
                            "category": "굿즈",
                            "rows": 12,
                            "requires_name_level_split_review": True,
                            "suggested_category": "기타 굿즈",
                            "review_reason": "Broad category needs split.",
                            "sample_names": [
                                "一番くじ 僕のヒーローアカデミア - A賞 緑谷出久 MASTERLISE",
                                "一番くじ 僕のヒーローアカデミア - H賞 キャンバス風ボード",
                                "一番くじ 僕のヒーローアカデミア - J賞 ステーショナリーコレクション",
                                "분류 안 되는 샘플",
                            ],
                        },
                        {
                            "category": "캔뱃지",
                            "rows": 5,
                            "requires_name_level_split_review": False,
                            "sample_names": ["缶バッジ"],
                        },
                    ]
                }
            ]
        }

        report = split_review.build_report(payload)

        self.assertEqual(report["summary"]["split_review_categories"], 1)
        self.assertEqual(report["summary"]["affected_catalog_rows"], 12)
        self.assertEqual(report["summary"]["candidate_split_rules"], 3)
        self.assertEqual(report["summary"]["matched_sample_names"], 3)
        self.assertEqual(report["summary"]["unmatched_sample_names"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_rows"], 0)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_category_changes"])
        self.assertFalse(report["automation_policy"]["auto_create_folders"])

        item = report["review_items"][0]
        self.assertEqual(item["source_category"], "굿즈")
        self.assertEqual(item["manual_confirmation_template"], "server/animation_category_name_split_confirmed_rows.template.json")
        self.assertEqual(item["confirmed_queue"], "server/animation_category_name_split_confirmed_rows.json")
        self.assertEqual(item["unblocks_when"], "name_level_split_manually_confirmed")
        targets = {candidate["target_category"] for candidate in item["split_candidates"]}
        self.assertEqual(targets, {"피규어", "보드", "문구"})
        figure = next(candidate for candidate in item["split_candidates"] if candidate["rule_id"] == "figure")
        template = figure["name_level_split_template"]
        self.assertFalse(template["manual_confirmed"])
        self.assertEqual(template["target_category"], "피규어")
        self.assertEqual(template["folder_icon_key"], "toys")
        self.assertEqual(template["blocked_until"], "name_level_split_manually_confirmed")
        self.assertEqual(item["unmatched_sample_names"], ["분류 안 되는 샘플"])


if __name__ == "__main__":
    unittest.main()
