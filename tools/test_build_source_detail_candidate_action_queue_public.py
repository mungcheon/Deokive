from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_detail_candidate_action_queue_public as queue


class BuildSourceDetailCandidateActionQueuePublicTest(unittest.TestCase):
    def test_build_report_publishes_manual_review_templates(self) -> None:
        source_detail = {
            "review_candidates": [
                {
                    "catalog_index": 7,
                    "source_store": "Animate",
                    "name_ko": "Badge",
                    "candidate_status": "candidate_review_needed",
                    "status": "candidate_review_needed",
                    "candidate_count": 1,
                    "candidate_source_url": "https://www.animate-onlineshop.jp/pn/test/pd/1/",
                    "candidate_image_url": "https://tc-animate.techorus-cdn.com/a.jpg",
                    "candidate_title": "Badge candidate",
                    "score": 0.8,
                    "safe_source_image_pair": True,
                }
            ]
        }

        catalog_rows = [
            {
                "catalog_index": 7,
                "source_store": "Animate",
                "name_ko": "Badge",
                "name_ja": None,
                "image_url": "",
                "local_image_path": "",
                "source_url": "https://old.example/item",
            }
        ]

        report = queue.build_report(source_detail, catalog_rows, generated_at="2026-07-22T00:00:00Z", batch_size=10)

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["candidate_action_rows"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_true"], 0)
        self.assertEqual(report["summary"]["safe_source_image_pair_rows"], 1)
        self.assertEqual(report["summary"]["identity_safe_source_image_pair_rows"], 1)
        self.assertEqual(report["summary"]["identity_blocked_source_image_pair_rows"], 0)
        self.assertEqual(report["summary"]["manual_confirmation_shortlist_rows"], 1)
        self.assertEqual(report["summary"]["priority_manual_review_candidate_rows"], 1)
        self.assertEqual(
            report["summary"]["by_manual_confirmation_shortlist"],
            [["ready_for_priority_manual_confirmation", 1], ["requires_deeper_identity_review", 0]],
        )
        self.assertEqual(
            report["summary"]["by_priority_manual_review_candidate"],
            [["safe_unflagged_missing_display_candidate", 1], ["not_priority_manual_review_candidate", 0]],
        )
        self.assertEqual(report["summary"]["identity_warning_rows"], 0)
        self.assertEqual(report["summary"]["identity_warning_missing_display_image_rows"], 0)
        self.assertEqual(report["summary"]["unflagged_missing_display_image_candidate_rows"], 1)
        self.assertEqual(report["summary"]["current_catalog_matched_rows"], 1)
        self.assertEqual(report["summary"]["current_catalog_missing_display_image_rows"], 1)
        self.assertEqual(report["summary"]["current_catalog_already_has_display_image_rows"], 0)
        self.assertEqual(report["summary"]["stale_candidate_rows"], 0)
        self.assertEqual(report["summary"]["identity_matched_candidate_rows"], 1)
        self.assertEqual(report["summary"]["near_or_better_candidate_rows"], 1)
        self.assertEqual(report["summary"]["ambiguous_or_weaker_candidate_rows"], 0)
        self.assertEqual(report["summary"]["by_candidate_count_bucket"], [["single_candidate", 1]])
        item = report["batches"][0]["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["candidate_count_bucket"], "single_candidate")
        self.assertEqual(item["candidate_score"], 0.8)
        self.assertEqual(item["candidate_identity_flags"], [])
        self.assertTrue(item["manual_confirmation_shortlist"])
        self.assertTrue(item["priority_manual_review_candidate"])
        self.assertTrue(item["identity_safe_source_image_pair"])
        self.assertEqual(item["review_priority"], 20)
        self.assertEqual(item["recommended_action"], "priority_manual_confirm_source_and_image_patch")
        self.assertEqual(report["priority_manual_review_candidates"][0]["catalog_index"], 7)
        self.assertEqual(
            report["priority_manual_review_candidates"][0]["recommended_action"],
            "priority_manual_confirm_source_and_image_patch",
        )
        self.assertEqual(report["batches"][0]["safe_source_image_pair_rows"], 1)
        self.assertEqual(report["batches"][0]["identity_safe_source_image_pair_rows"], 1)
        self.assertEqual(report["batches"][0]["identity_blocked_source_image_pair_rows"], 0)
        self.assertEqual(report["batches"][0]["manual_confirmation_shortlist_rows"], 1)
        self.assertEqual(report["batches"][0]["priority_manual_review_candidate_rows"], 1)
        self.assertEqual(item["current_catalog_state"]["catalog_match_found"], True)
        self.assertEqual(item["current_catalog_state"]["catalog_has_display_image"], False)
        self.assertEqual(item["current_catalog_state"]["catalog_identity_matches"], True)
        self.assertEqual(item["source_patch_template"]["field"], "source_url")
        self.assertEqual(item["image_patch_template"]["field"], "image_url")
        self.assertFalse(item["source_patch_template"]["manual_confirmed"])
        self.assertIn("exact product", item["acceptance_criteria"][1])

    def test_build_report_marks_stale_or_already_imaged_candidates(self) -> None:
        source_detail = {
            "review_candidates": [
                {
                    "catalog_index": 1,
                    "source_store": "Animate",
                    "name_ko": "Old Name",
                    "name_ja": "古い",
                    "status": "candidate_review_needed",
                    "candidate_count": 4,
                    "candidate_source_url": "https://www.animate-onlineshop.jp/pn/old/pd/1/",
                    "candidate_image_url": "https://tc-animate.techorus-cdn.com/old.jpg",
                    "score": 0.5,
                    "safe_source_image_pair": True,
                },
                {
                    "catalog_index": 2,
                    "source_store": "Animate",
                    "name_ko": "Solved",
                    "name_ja": "解決",
                    "status": "candidate_review_needed",
                    "candidate_count": 1,
                    "candidate_source_url": "https://www.animate-onlineshop.jp/pn/solved/pd/2/",
                    "candidate_image_url": "https://tc-animate.techorus-cdn.com/solved.jpg",
                    "score": 0.8,
                    "safe_source_image_pair": True,
                },
            ]
        }
        catalog_rows = [
            {"catalog_index": 1, "source_store": "Animate", "name_ko": "New Name", "name_ja": "新しい"},
            {"catalog_index": 2, "source_store": "Animate", "name_ko": "Solved", "name_ja": "解決", "image_url": "https://example/img.jpg"},
        ]

        report = queue.build_report(source_detail, catalog_rows, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["summary"]["current_catalog_matched_rows"], 2)
        self.assertEqual(report["summary"]["current_catalog_missing_display_image_rows"], 1)
        self.assertEqual(report["summary"]["current_catalog_already_has_display_image_rows"], 1)
        self.assertEqual(report["summary"]["stale_candidate_rows"], 1)
        actions = {item["catalog_index"]: item["recommended_action"] for batch in report["batches"] for item in batch["items"]}
        self.assertEqual(actions[1], "refresh_candidate_before_manual_review")
        self.assertEqual(actions[2], "skip_current_catalog_row_already_has_display_image")

    def test_build_report_flags_risky_title_identity_matches(self) -> None:
        source_detail = {
            "review_candidates": [
                {
                    "catalog_index": 3,
                    "source_store": "Good Smile",
                    "name_ko": "POP UP PARADE Monokuma",
                    "name_ja": "POP UP PARADE Monokuma",
                    "status": "candidate_review_needed",
                    "candidate_count": 1,
                    "candidate_source_url": "https://example.test/product/3",
                    "candidate_image_url": "https://example.test/product/3.jpg",
                    "candidate_title": "POP UP PARADE Junko Enoshima",
                    "score": 0.75,
                    "shared_tokens": ["pop", "up", "parade"],
                    "safe_source_image_pair": True,
                },
                {
                    "catalog_index": 4,
                    "source_store": "Animate",
                    "name_ko": "Crayon pouch (Shinchan)",
                    "name_ja": "Crayon pouch",
                    "status": "candidate_review_needed",
                    "candidate_count": 2,
                    "candidate_source_url": "https://example.test/product/4",
                    "candidate_image_url": "https://example.test/product/4.jpg",
                    "candidate_title": "TXT | Crayon earphone pouch",
                    "score": 0.8,
                    "shared_tokens": ["pouch"],
                    "safe_source_image_pair": True,
                },
            ]
        }
        catalog_rows = [
            {"catalog_index": 3, "source_store": "Good Smile", "name_ko": "POP UP PARADE Monokuma", "name_ja": "POP UP PARADE Monokuma"},
            {"catalog_index": 4, "source_store": "Animate", "name_ko": "Crayon pouch (Shinchan)", "name_ja": "Crayon pouch"},
        ]

        report = queue.build_report(source_detail, catalog_rows, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["summary"]["identity_warning_rows"], 2)
        self.assertEqual(report["summary"]["identity_safe_source_image_pair_rows"], 0)
        self.assertEqual(report["summary"]["identity_blocked_source_image_pair_rows"], 2)
        self.assertEqual(report["summary"]["manual_confirmation_shortlist_rows"], 0)
        self.assertEqual(report["summary"]["priority_manual_review_candidate_rows"], 0)
        self.assertEqual(report["priority_manual_review_candidates"], [])
        self.assertEqual(report["summary"]["identity_warning_missing_display_image_rows"], 2)
        self.assertEqual(report["summary"]["unflagged_missing_display_image_candidate_rows"], 0)
        self.assertEqual(
            report["summary"]["by_candidate_identity_flag"],
            [
                ["only_generic_shared_tokens", 2],
                ["candidate_title_mentions_crossover", 1],
                ["candidate_title_missing_catalog_variant_hint", 1],
            ],
        )
        items = {item["catalog_index"]: item for batch in report["batches"] for item in batch["items"]}
        self.assertEqual(items[3]["candidate_identity_flags"], ["only_generic_shared_tokens"])
        self.assertFalse(items[3]["identity_safe_source_image_pair"])
        self.assertEqual(items[3]["review_priority"], 35)
        self.assertEqual(items[3]["recommended_action"], "recheck_candidate_identity_before_source_or_image_patch")
        self.assertEqual(
            items[4]["candidate_identity_flags"],
            [
                "only_generic_shared_tokens",
                "candidate_title_mentions_crossover",
                "candidate_title_missing_catalog_variant_hint",
            ],
        )
        self.assertEqual(items[4]["review_priority"], 35)
        self.assertFalse(items[4]["identity_safe_source_image_pair"])
        self.assertEqual(items[4]["recommended_action"], "recheck_candidate_identity_before_source_or_image_patch")

    def test_build_report_flags_product_type_and_bundle_mismatches(self) -> None:
        source_detail = {
            "review_candidates": [
                {
                    "catalog_index": 5,
                    "source_store": "Good Smile",
                    "name_ko": "Nendoroid Mahito",
                    "name_ja": "ねんどろいど 真人",
                    "status": "candidate_review_needed",
                    "candidate_count": 1,
                    "candidate_source_url": "https://example.test/product/5",
                    "candidate_image_url": "https://example.test/product/5.jpg",
                    "candidate_title": "呪術廻戦 ねんどろいどぷらす アクリルキーチェーン 宿儺/真人/七海建人",
                    "score": 0.8,
                    "shared_tokens": ["真人"],
                    "safe_source_image_pair": True,
                }
            ]
        }
        catalog_rows = [
            {
                "catalog_index": 5,
                "source_store": "Good Smile",
                "name_ko": "Nendoroid Mahito",
                "name_ja": "ねんどろいど 真人",
            }
        ]

        report = queue.build_report(source_detail, catalog_rows, generated_at="2026-07-22T00:00:00Z")

        item = report["batches"][0]["items"][0]
        self.assertEqual(report["summary"]["manual_confirmation_shortlist_rows"], 0)
        self.assertEqual(report["summary"]["identity_safe_source_image_pair_rows"], 0)
        self.assertEqual(report["summary"]["identity_blocked_source_image_pair_rows"], 1)
        self.assertFalse(item["identity_safe_source_image_pair"])
        self.assertIn("candidate_title_product_type_mismatch", item["candidate_identity_flags"])
        self.assertIn("candidate_title_multi_variant_or_bundle", item["candidate_identity_flags"])
        self.assertEqual(item["review_priority"], 35)
        self.assertEqual(item["recommended_action"], "recheck_candidate_identity_before_source_or_image_patch")

    def test_priority_manual_review_surfaces_high_score_large_candidate_set(self) -> None:
        source_detail = {
            "review_candidates": [
                {
                    "catalog_index": 6,
                    "source_store": "Animate",
                    "name_ko": "Unflagged shirt",
                    "name_ja": "Unflagged shirt",
                    "status": "candidate_review_needed",
                    "candidate_count": 23,
                    "candidate_source_url": "https://www.animate-onlineshop.jp/pn/shirt/pd/6/",
                    "candidate_image_url": "https://tc-animate.techorus-cdn.com/shirt.jpg",
                    "candidate_title": "Unflagged shirt",
                    "score": 1.0,
                    "shared_tokens": ["Unflagged"],
                    "safe_source_image_pair": True,
                }
            ]
        }
        catalog_rows = [
            {
                "catalog_index": 6,
                "source_store": "Animate",
                "name_ko": "Unflagged shirt",
                "name_ja": "Unflagged shirt",
                "image_url": "",
                "local_image_path": "",
            }
        ]

        report = queue.build_report(source_detail, catalog_rows, generated_at="2026-07-22T00:00:00Z")

        item = report["batches"][0]["items"][0]
        self.assertEqual(item["candidate_count_bucket"], "large_candidate_set")
        self.assertFalse(item["manual_confirmation_shortlist"])
        self.assertTrue(item["candidate_count_review_required"])
        self.assertTrue(item["priority_manual_review_candidate"])
        self.assertTrue(item["identity_safe_source_image_pair"])
        self.assertEqual(item["recommended_action"], "review_large_candidate_set_before_source_or_image_patch")
        self.assertEqual(report["summary"]["manual_confirmation_shortlist_rows"], 0)
        self.assertEqual(report["summary"]["identity_safe_source_image_pair_rows"], 1)
        self.assertEqual(report["summary"]["identity_blocked_source_image_pair_rows"], 0)
        self.assertEqual(report["summary"]["candidate_count_review_required_rows"], 1)
        self.assertEqual(report["summary"]["priority_manual_review_candidate_rows"], 1)
        self.assertEqual(report["priority_manual_review_candidates"][0]["catalog_index"], 6)
        self.assertTrue(report["priority_manual_review_candidates"][0]["candidate_count_review_required"])
        self.assertEqual(report["batches"][0]["candidate_count_review_required_rows"], 1)


if __name__ == "__main__":
    unittest.main()
