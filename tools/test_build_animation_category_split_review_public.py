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
                                "장송의 프리렌 × 오오카와 부쿠부 콜라보 굿즈",
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

        catalog_payload = {
            "items": [
                {
                    "catalog_index": 101,
                    "name_ko": "나히아 MASTERLISE 피규어",
                    "name_ja": "僕のヒーローアカデミア MASTERLISE",
                    "category": "굿즈",
                    "affiliation": "나의 히어로 아카데미아",
                    "series_name": "이치방쿠지",
                    "sub_series": "A상",
                    "source_store": "이치방쿠지",
                },
                {
                    "catalog_index": 102,
                    "name_ko": "장송의 프리렌 × 오오카와 부쿠부 콜라보 굿즈",
                    "name_ja": "葬送のフリーレン×大川ぶくぶ グッズ",
                    "category": "굿즈",
                    "affiliation": "장송의 프리렌",
                    "series_name": "부쿠부 콜라보",
                    "sub_series": "콜라보 굿즈",
                    "source_store": "애니메이트",
                },
                {
                    "catalog_index": 103,
                    "name_ko": "분류 안 되는 샘플",
                    "category": "굿즈",
                    "affiliation": "테스트",
                    "series_name": "테스트",
                    "source_store": "테스트",
                },
            ]
        }

        report = split_review.build_report(payload, catalog_payload)

        self.assertEqual(report["summary"]["split_review_categories"], 1)
        self.assertEqual(report["summary"]["affected_catalog_rows"], 12)
        self.assertEqual(report["summary"]["candidate_split_rules"], 4)
        self.assertEqual(report["summary"]["matched_sample_names"], 4)
        self.assertEqual(report["summary"]["unmatched_sample_names"], 1)
        self.assertTrue(report["summary"]["catalog_scan_enabled"])
        self.assertEqual(report["summary"]["catalog_source_category_rows"], 3)
        self.assertEqual(report["summary"]["matched_catalog_rule_hits"], 2)
        self.assertEqual(report["summary"]["matched_catalog_rows"], 2)
        self.assertEqual(report["summary"]["unmatched_catalog_rows"], 1)
        self.assertEqual(report["summary"]["candidate_priority_rows"], 4)
        self.assertEqual(report["summary"]["starter_confirmed_queue_rows"], 4)
        self.assertEqual(report["summary"]["top_candidate_expected_update_rows"], 1)
        self.assertEqual(report["summary"]["top_candidate_source_category"], "굿즈")
        self.assertEqual(report["summary"]["manual_confirmed_rows"], 0)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_category_changes"])
        self.assertFalse(report["automation_policy"]["auto_create_folders"])

        item = report["review_items"][0]
        self.assertEqual(item["source_category"], "굿즈")
        self.assertEqual(item["manual_confirmation_template"], "server/animation_category_name_split_confirmed_rows.template.json")
        self.assertEqual(item["confirmed_queue"], "server/animation_category_name_split_confirmed_rows.json")
        self.assertEqual(item["unblocks_when"], "name_level_split_manually_confirmed")
        self.assertEqual(item["catalog_category_rows"], 3)
        self.assertEqual(item["matched_catalog_rule_hit_count"], 2)
        self.assertEqual(item["matched_catalog_row_count"], 2)
        self.assertEqual(item["unmatched_catalog_row_count"], 1)
        targets = {candidate["target_category"] for candidate in item["split_candidates"]}
        self.assertEqual(targets, {"피규어", "보드", "문구", "콜라보 굿즈"})
        figure = next(candidate for candidate in item["split_candidates"] if candidate["rule_id"] == "figure")
        template = figure["name_level_split_template"]
        self.assertFalse(template["manual_confirmed"])
        self.assertEqual(template["target_category"], "피규어")
        self.assertEqual(template["folder_icon_key"], "toys")
        self.assertEqual(template["blocked_until"], "name_level_split_manually_confirmed")
        collab = next(candidate for candidate in item["split_candidates"] if candidate["rule_id"] == "collab_goods")
        self.assertEqual(collab["target_category"], "콜라보 굿즈")
        self.assertEqual(collab["matched_catalog_row_count"], 1)
        self.assertEqual(collab["matched_catalog_samples"][0]["catalog_index"], 102)
        self.assertEqual(collab["name_level_split_template"]["folder_icon_key"], "diversity_3")
        self.assertEqual(item["unmatched_sample_names"], ["분류 안 되는 샘플"])
        self.assertEqual(item["unmatched_catalog_samples"][0]["catalog_index"], 103)
        priority = report["candidate_priority_queue"][0]
        self.assertEqual(priority["source_category"], "굿즈")
        self.assertEqual(priority["expected_update_rows"], 1)
        self.assertFalse(priority["auto_apply_enabled"])
        self.assertEqual(
            priority["manual_confirmation_template"]["blocked_until"],
            "name_level_split_manually_confirmed",
        )
        starter = report["starter_confirmed_queue"]
        self.assertEqual(starter["target_queue"], "server/animation_category_name_split_confirmed_rows.json")
        self.assertEqual(starter["import_tool"], "tools/import_confirmed_animation_category_rows.py")
        self.assertFalse(starter["manual_confirmed_default"])
        self.assertEqual(starter["items"][0]["manual_confirmed"], False)
        self.assertEqual(starter["items"][0]["source_category"], priority["source_category"])
        self.assertEqual(starter["items"][0]["target_category"], priority["target_category"])

    def test_unicode_stationery_and_tableware_split_rules_are_available(self) -> None:
        rules = {rule["rule_id"]: rule for rule in split_review.SPLIT_RULES}

        self.assertEqual(rules["shikishi_board"]["target_category"], "색지")
        self.assertIn("色紙", rules["shikishi_board"]["match_keywords"])
        self.assertEqual(rules["sticker"]["target_category"], "스티커")
        self.assertIn("ステッカー", rules["sticker"]["match_keywords"])
        self.assertEqual(rules["card_bromide"]["target_category"], "카드/브로마이드")
        self.assertIn("ブロマイド", rules["card_bromide"]["match_keywords"])
        self.assertEqual(rules["clear_file"]["target_category"], "클리어 파일")
        self.assertIn("クリアファイル", rules["clear_file"]["match_keywords"])
        self.assertEqual(rules["tableware_daily_goods"]["target_category"], "생활잡화")
        self.assertIn("食器", rules["tableware_daily_goods"]["match_keywords"])


if __name__ == "__main__":
    unittest.main()
