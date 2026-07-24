from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ensky_cache_candidate_action_queue_public as queue


class BuildEnskyCacheCandidateActionQueuePublicTest(unittest.TestCase):
    def test_build_report_publishes_broad_candidates_as_manual_only_actions(self) -> None:
        cache_coverage = {
            "items": [
                {
                    "catalog_index": 2,
                    "name_ko": "Badge",
                    "name_ja": "缶バッジ",
                    "source_store": "엔스카이",
                    "affiliation": "Series",
                    "category": "캔뱃지",
                    "status": "broad_cache_candidate",
                    "candidate_count": 1,
                    "top_candidates": [
                        {
                            "title": "Badge candidate",
                            "source_url": "https://www.enskyshop.com/products/detail/1",
                            "image_url": "https://www.enskyshop.com/html/upload/save_image/a.jpg",
                            "safe_exact_match": False,
                            "score": 20,
                            "matched_tokens": ["badge"],
                        }
                    ],
                },
                {
                    "catalog_index": 1,
                    "source_store": "엔스카이",
                    "status": "no_cache_candidate",
                    "candidate_count": 0,
                    "top_candidates": [],
                },
            ]
        }

        report = queue.build_report(cache_coverage, generated_at="2026-07-22T00:00:00Z", batch_size=10)

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["candidate_action_rows"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_true"], 0)
        self.assertEqual(report["summary"]["candidate_source_url_ready_rows"], 1)
        self.assertEqual(report["summary"]["candidate_image_url_ready_rows"], 1)
        self.assertEqual(report["summary"]["can_import_now_rows"], 0)
        self.assertEqual(report["summary"]["blocked_manual_review_rows"], 1)
        self.assertEqual(report["import_readiness"]["candidate_rows"], 1)
        self.assertEqual(report["import_readiness"]["can_import_now_rows"], 0)
        item = report["batches"][0]["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertTrue(item["top_candidate_has_source_url"])
        self.assertTrue(item["top_candidate_has_image_url"])
        self.assertFalse(item["import_readiness"]["can_import_now"])
        self.assertEqual(item["source_patch_template"]["field"], "source_url")
        self.assertEqual(item["image_patch_template"]["field"], "image_url")
        self.assertFalse(item["source_patch_template"]["manual_confirmed"])
        self.assertEqual(item["top_candidates"][0]["candidate_source_url"], "https://www.enskyshop.com/products/detail/1")
        self.assertIn("exact product", item["acceptance_criteria"][0])

    def test_build_report_flags_product_type_and_box_candidates(self) -> None:
        cache_coverage = {
            "items": [
                {
                    "catalog_index": 3,
                    "name_ko": "Chiikawa acrylic stand",
                    "name_ja": "ちいかわ アクリルスタンド (ちいかわ)",
                    "source_store": "엔스카이",
                    "affiliation": "ちいかわ",
                    "category": "アクリルスタンド",
                    "status": "broad_cache_candidate",
                    "candidate_count": 1,
                    "top_candidates": [
                        {
                            "title": "ちいかわ mitamemoチケットファイル2【1BOX 14個入り】",
                            "source_url": "https://www.enskyshop.com/products/detail/28997",
                            "image_url": "https://www.enskyshop.com/html/upload/save_image/a.jpg",
                            "safe_exact_match": False,
                            "score": 20,
                            "matched_tokens": ["ちいかわ"],
                        }
                    ],
                }
            ]
        }

        report = queue.build_report(cache_coverage, generated_at="2026-07-22T00:00:00Z", batch_size=10)

        item = report["batches"][0]["items"][0]
        self.assertEqual(report["summary"]["identity_warning_rows"], 1)
        self.assertEqual(report["summary"]["safe_exact_top_candidate_rows"], 0)
        self.assertEqual(report["batches"][0]["identity_warning_rows"], 1)
        self.assertEqual(report["batches"][0]["can_import_now_rows"], 0)
        self.assertEqual(
            dict(report["summary"]["by_candidate_identity_flag"]),
            {
                "candidate_title_product_type_mismatch": 1,
                "candidate_title_box_or_assortment": 1,
            },
        )
        self.assertEqual(
            item["recommended_action"],
            "recheck_ensky_candidate_identity_before_source_or_image_patch",
        )
        self.assertEqual(
            item["import_readiness"]["blocked_reason"],
            "candidate_identity_warning_requires_review",
        )
        self.assertEqual(
            item["top_candidates"][0]["candidate_identity_flags"],
            [
                "candidate_title_product_type_mismatch",
                "candidate_title_box_or_assortment",
            ],
        )


if __name__ == "__main__":
    unittest.main()
