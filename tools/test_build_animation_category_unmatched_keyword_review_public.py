from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_animation_category_unmatched_keyword_review_public as keyword_review


class BuildAnimationCategoryUnmatchedKeywordReviewPublicTest(unittest.TestCase):
    def test_build_report_groups_unmatched_keyword_candidates(self) -> None:
        split_payload = {
            "review_items": [
                {
                    "source_category": "굿즈",
                    "split_candidates": [
                        {"match_keywords": ["피규어", "MASTERLISE"]},
                    ],
                }
            ]
        }
        catalog_payload = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "나히아 MASTERLISE 피규어",
                    "category": "굿즈",
                    "series_name": "이치방쿠지",
                    "sub_series": "A상",
                    "source_store": "이치방쿠지",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "치이카와 카메라 토이",
                    "category": "굿즈",
                    "series_name": "치이카와 마켓",
                    "sub_series": "카메라",
                    "source_store": "치이카와 마켓",
                },
                {
                    "catalog_index": 3,
                    "name_ko": "치이카와 카메라 케이스",
                    "category": "굿즈",
                    "series_name": "치이카와 마켓",
                    "sub_series": "카메라",
                    "source_store": "치이카와 마켓",
                },
            ]
        }

        report = keyword_review.build_report(split_payload, catalog_payload, limit=5)

        self.assertEqual(report["summary"]["source_categories"], 1)
        self.assertEqual(report["summary"]["source_category_rows"], 3)
        self.assertEqual(report["summary"]["unmatched_rows"], 2)
        self.assertGreater(report["summary"]["token_candidate_count"], 0)
        self.assertGreater(report["summary"]["product_type_candidate_count"], 0)
        self.assertEqual(
            report["summary"]["top_product_type_candidate_count"],
            len(report["top_product_type_candidates"]),
        )
        self.assertGreaterEqual(report["summary"]["noise_candidate_count"], 0)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        item = report["review_items"][0]
        self.assertEqual(item["source_category"], "굿즈")
        self.assertEqual(item["unmatched_rows"], 2)
        self.assertFalse(item["automation_policy"]["auto_apply_keywords"])
        self.assertEqual(item["top_sub_series"][0]["sub_series"], "카메라")
        tokens = {row["token"] for row in item["top_token_candidates"]}
        self.assertIn("카메라", tokens)
        camera = next(row for row in item["top_token_candidates"] if row["token"] == "카메라")
        self.assertEqual(camera["review_kind"], "product_type_like")
        self.assertTrue(camera["product_type_hint"])
        self.assertGreater(camera["review_score"], 80)
        self.assertEqual(
            camera["recommended_manual_action"],
            "review_samples_then_add_name_level_split_rule_if_consistent",
        )
        self.assertEqual(item["next_review_action"], "review_promotable_product_type_candidates")
        self.assertGreater(item["highest_review_score"], 0)
        self.assertIn(
            "product_type_like",
            {row["review_kind"] for row in item["review_kind_counts"]},
        )
        self.assertEqual(item["promotable_token_candidates"][0]["token"], "카메라")
        self.assertEqual(report["top_product_type_candidates"][0]["source_category"], "굿즈")
        self.assertEqual(report["top_product_type_candidates"][0]["token"], "카메라")
        self.assertEqual(item["sample_unmatched_rows"][0]["catalog_index"], 2)

    def test_unicode_stationery_and_tableware_keywords_are_promotable(self) -> None:
        split_payload = {
            "review_items": [
                {
                    "source_category": "굿즈",
                    "split_candidates": [],
                }
            ]
        }
        catalog_payload = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "치이카와 색지 컬렉션",
                    "name_ja": "ちいかわ 色紙コレクション",
                    "category": "굿즈",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "치이카와 식기 세트",
                    "name_ja": "ちいかわ 食器コレクション",
                    "category": "굿즈",
                },
            ]
        }

        report = keyword_review.build_report(split_payload, catalog_payload, limit=10)
        candidates = {
            row["token"]: row
            for item in report["review_items"]
            for row in item["top_token_candidates"]
        }

        self.assertEqual(candidates["色紙"]["suggested_target_category"], "색지")
        self.assertEqual(candidates["色紙"]["suggested_target_family"], "stationery")
        self.assertEqual(candidates["食器"]["suggested_target_category"], "생활잡화")
        self.assertEqual(candidates["食器"]["suggested_target_family"], "daily_goods")
        self.assertNotIn("コレクション", {row["token"] for row in report["top_product_type_candidates"]})


if __name__ == "__main__":
    unittest.main()
