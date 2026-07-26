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
        self.assertEqual(report["summary"]["low_risk_review_rows"], 1)
        self.assertEqual(report["summary"]["can_import_now_rows"], 0)
        self.assertEqual(report["summary"]["blocked_manual_review_rows"], 1)
        self.assertEqual(report["import_readiness"]["candidate_rows"], 1)
        self.assertEqual(report["import_readiness"]["can_import_now_rows"], 0)
        item = report["batches"][0]["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertTrue(item["top_candidate_has_source_url"])
        self.assertTrue(item["top_candidate_has_image_url"])
        self.assertFalse(item["import_readiness"]["can_import_now"])
        self.assertEqual(item["candidate_review_risk"], "low")
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
        self.assertEqual(report["summary"]["high_risk_review_rows"], 1)
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
        self.assertEqual(item["candidate_review_risk"], "high")
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

    def test_build_report_treats_capsule_standy_as_stand_type(self) -> None:
        flags = queue.candidate_identity_flags(
            {
                "name_ja": "\u9b3c\u6ec5\u306e\u5203 \u7f36\u30d0\u30c3\u30b8 \u7ac8\u9580\u70ad\u6cbb\u90ce",
                "category": "\u7f36\u30d0\u30c3\u30b8",
            },
            {
                "title": "\u9b3c\u6ec5\u306e\u5203 \u30ab\u30d6\u30bb\u30eb\u30b9\u30bf\u30f3\u30c7\u30a3 / \u7ac8\u9580\u70ad\u6cbb\u90ce",
            },
        )

        self.assertIn("candidate_title_product_type_mismatch", flags)

    def test_build_report_rejects_capsule_standy_for_acrylic_stand_rows(self) -> None:
        flags = queue.candidate_identity_flags(
            {
                "affiliation": "\uc6d0\ud53c\uc2a4",
                "name_ja": "ONE PIECE \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 (\u30e2\u30f3\u30ad\u30fc\u30fbD\u30fb\u30eb\u30d5\u30a3)",
                "category": "\uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
            },
            {
                "title": "\u30ef\u30f3\u30d4\u30fc\u30b9 \u30ab\u30d6\u30bb\u30eb\u30b9\u30bf\u30f3\u30c7\u30a3 / \u30e2\u30f3\u30ad\u30fc\u30fbD\u30fb\u30eb\u30d5\u30a3(\u30a8\u30eb\u30d0\u30d5)",
            },
        )

        self.assertIn("candidate_title_product_type_mismatch", flags)

    def test_build_report_treats_chibigumi_as_plush_type(self) -> None:
        flags = queue.candidate_identity_flags(
            {
                "affiliation": "\u30ef\u30f3\u30d4\u30fc\u30b9",
                "name_ja": "\u3061\u3073\u3050\u308b\u307f \u30e2\u30f3\u30ad\u30fc\u30fbD\u30fb\u30eb\u30d5\u30a3",
                "category": "\u4eba\u5f62",
            },
            {
                "title": "\u30ef\u30f3\u30d4\u30fc\u30b9 \u30ab\u30d6\u30bb\u30eb\u30b9\u30bf\u30f3\u30c7\u30a3 / \u30e2\u30f3\u30ad\u30fc\u30fbD\u30fb\u30eb\u30d5\u30a3",
            },
        )

        self.assertIn("candidate_title_product_type_mismatch", flags)

    def test_build_report_flags_affiliation_mismatch(self) -> None:
        flags = queue.candidate_identity_flags(
            {
                "affiliation": "\ub2e8\uac04\ub860\ud30c",
                "name_ja": "\u304a\u307e\u3093\u3058\u3085\u3046 \u30de\u30b9\u30b3\u30c3\u30c8 \u30e2\u30ce\u30af\u30de",
                "category": "\u30de\u30b9\u30b3\u30c3\u30c8",
            },
            {
                "title": "TV\u30a2\u30cb\u30e1\u300eFate/strange Fake\u300f \u304a\u307e\u3093\u3058\u3085\u3046\u306b\u304e\u306b\u304e\u30de\u30b9\u30b3\u30c3\u30c8",
            },
        )

        self.assertIn("candidate_title_affiliation_mismatch", flags)

    def test_chainsaw_man_canonical_affiliation_matches_ensky_title_hint(self) -> None:
        flags = queue.candidate_identity_flags(
            {
                "affiliation": "\uccb4\uc778\uc18c\ub9e8",
                "name_ja": "\u30c1\u30a7\u30f3\u30bd\u30fc\u30de\u30f3 \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 (\u30d1\u30ef\u30fc)",
                "category": "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9",
            },
            {
                "title": "\u30c1\u30a7\u30f3\u30bd\u30fc\u30de\u30f3 \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 / \u30d1\u30ef\u30fc",
            },
        )

        self.assertNotIn("candidate_title_affiliation_mismatch", flags)

    def test_build_report_prioritizes_lower_identity_risk_candidates(self) -> None:
        cache_coverage = {
            "items": [
                {
                    "catalog_index": 10,
                    "name_ko": "Danganronpa mascot",
                    "name_ja": "\u304a\u307e\u3093\u3058\u3085\u3046 \u30de\u30b9\u30b3\u30c3\u30c8 \u30e2\u30ce\u30af\u30de",
                    "source_store": queue.ENSKY_STORE,
                    "affiliation": "Danganronpa",
                    "category": "\u30de\u30b9\u30b3\u30c3\u30c8",
                    "status": "broad_cache_candidate",
                    "candidate_count": 9,
                    "top_candidates": [
                        {
                            "title": "Fate rubber strap 1BOX",
                            "source_url": "https://www.enskyshop.com/products/detail/10",
                            "image_url": "https://www.enskyshop.com/html/upload/save_image/10.jpg",
                        }
                    ],
                },
                {
                    "catalog_index": 11,
                    "name_ko": "Jujutsu rubber strap",
                    "name_ja": "\u864e\u6756\u60a0\u4ec1 \u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7",
                    "source_store": queue.ENSKY_STORE,
                    "affiliation": "Jujutsu Kaisen",
                    "category": "\u30ad\u30fc\u30ea\u30f3\u30b0",
                    "status": "broad_cache_candidate",
                    "candidate_count": 1,
                    "top_candidates": [
                        {
                            "title": "\u546a\u8853\u5efb\u6226 \u864e\u6756\u60a0\u4ec1 \u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7",
                            "source_url": "https://www.enskyshop.com/products/detail/11",
                            "image_url": "https://www.enskyshop.com/html/upload/save_image/11.jpg",
                        }
                    ],
                },
            ]
        }

        report = queue.build_report(cache_coverage, generated_at="2026-07-22T00:00:00Z", batch_size=10)

        first_item = report["batches"][0]["items"][0]
        self.assertEqual(first_item["catalog_index"], 11)
        self.assertEqual(first_item["candidate_review_risk"], "low")
        self.assertLessEqual(
            len(first_item["candidate_identity_flags"]),
            len(report["batches"][0]["items"][1]["candidate_identity_flags"]),
        )

    def test_review_risk_only_multi_variant_flag_is_low(self) -> None:
        self.assertEqual(
            queue.candidate_review_risk(["candidate_title_multi_variant_or_lineup"]),
            "low",
        )
        self.assertEqual(
            queue.candidate_review_risk(["candidate_title_box_or_assortment"]),
            "medium",
        )
        self.assertEqual(
            queue.candidate_review_risk(["candidate_title_product_type_mismatch"]),
            "high",
        )


if __name__ == "__main__":
    unittest.main()
