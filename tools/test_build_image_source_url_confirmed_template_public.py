from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_image_source_url_confirmed_template_public as template


class BuildImageSourceUrlConfirmedTemplatePublicTest(unittest.TestCase):
    def test_build_template_keeps_only_source_url_update_items(self) -> None:
        action_queue = {
            "batches": [
                {
                    "batch_id": "image-attachment-action-001",
                    "source_store": "Stellive Store",
                    "items": [
                        {
                            "catalog_index": 10,
                            "workflow": "replace_generic_source_then_extract_image",
                            "source_store": "Stellive Store",
                            "name_ko": "Badge",
                            "category": "Can Badge",
                            "source_url": "https://fanding.kr/@stellive/shop",
                            "official_search_url": "https://stellive.fanding.kr/search?keyword=Badge",
                            "required_before_image_import": [
                                "confirm_exact_product_source_url",
                                "replace_generic_source_url",
                            ],
                            "source_url_import_template": {
                                "row_index": 10,
                                "field": "source_url",
                                "current_source_url": "https://fanding.kr/@stellive/shop",
                            },
                        },
                        {
                            "catalog_index": 11,
                            "workflow": "replace_generic_source_then_extract_image",
                            "source_store": "Weverse Shop",
                            "name_ko": "SEVENTEEN 포토카드 (랜덤)",
                            "name_ja": "SEVENTEEN フォトカード（ランダム）",
                            "series_name": "SEVENTEEN",
                            "category": "포토카드",
                            "source_url": "https://shop.weverse.io/home",
                            "source_url_import_template": {
                                "row_index": 11,
                                "field": "source_url",
                                "current_source_url": "https://shop.weverse.io/home",
                            },
                        },
                        {
                            "catalog_index": 12,
                            "workflow": "review_gotouchi_official_candidates",
                            "source_store": "Gotouchi",
                            "name_ko": "Charm",
                        },
                    ],
                }
            ]
        }

        candidate_report = {
            "queue": [
                {
                    "row_index": 99,
                    "catalog_index": 10,
                    "candidate_status": "weak_manual_review_candidate",
                    "candidate_review_lane": "weak_candidate_review",
                    "match_diagnostics": {
                        "diagnosis": "candidate_requires_exact_identity_confirmation",
                        "query_tokens": ["badge"],
                    },
                    "fallback_search_queries": [
                        "site:fanding.kr/@stellive/shop Badge",
                    ],
                    "top_candidates": [
                        {
                            "product_no": 100,
                            "title": "Badge exact-ish",
                            "source_url": "https://fanding.kr/@stellive/shop/100",
                            "image_url": "https://example.test/badge.webp",
                            "score": 0.81,
                            "shared_tokens": ["Badge"],
                            "query_overlap": 0.5,
                            "title_overlap": 0.75,
                        }
                    ],
                }
            ]
        }

        report = template.build_template(
            action_queue,
            candidate_report,
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(report["summary"]["template_items"], 2)
        self.assertEqual(report["summary"]["manual_confirmed_rows"], 0)
        self.assertEqual(
            report["summary"]["by_source_store"],
            [["Stellive Store", 1], ["Weverse Shop", 1]],
        )
        self.assertEqual(report["summary"]["candidate_prefilled_rows"], 0)
        self.assertEqual(
            report["summary"]["by_candidate_status"],
            [["weak_manual_review_candidate", 1], ["no_candidate_report", 1]],
        )
        self.assertEqual(
            report["summary"]["by_source_url_review_lane"],
            [["weak_candidate_review", 1], ["candidate_provider_missing", 1]],
        )
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        item = report["items"][0]
        self.assertEqual(item["field"], "source_url")
        self.assertEqual(item["row_index"], 10)
        self.assertEqual(item["manual_value"], "")
        self.assertEqual(item["candidate_source_url"], "")
        self.assertEqual(item["candidate_image_url"], "")
        self.assertEqual(item["candidate_title"], "")
        self.assertEqual(item["candidate_status"], "weak_manual_review_candidate")
        self.assertEqual(item["candidate_review_lane"], "weak_candidate_review")
        self.assertEqual(
            item["match_diagnostics"]["diagnosis"],
            "candidate_requires_exact_identity_confirmation",
        )
        self.assertEqual(
            item["fallback_search_queries"],
            ["site:fanding.kr/@stellive/shop Badge"],
        )
        self.assertEqual(item["source_url_review_lane"], "weak_candidate_review")
        self.assertIn("weak_candidate_only", item["source_url_review_blockers"])
        self.assertIn("manual_confirmed=true", item["manual_confirmation_requirements"][-1])
        self.assertEqual(item["candidate_options"][0]["product_no"], 100)
        self.assertEqual(item["current_source_url"], "https://fanding.kr/@stellive/shop")
        self.assertEqual(
            item["store_search_hints"]["store_search_url"],
            "https://stellive.fanding.kr/search?keyword=Badge",
        )
        self.assertEqual(item["store_search_hints"]["site_query"], "site:fanding.kr/@stellive/shop")
        self.assertEqual(item["next_after_confirmed_source_url"], "extract_or_confirm_product_page_image_url")
        self.assertFalse(item["auto_apply_enabled"])

        missing_provider_item = report["items"][1]
        self.assertEqual(missing_provider_item["row_index"], 11)
        self.assertEqual(missing_provider_item["candidate_status"], "no_candidate_report")
        self.assertEqual(missing_provider_item["candidate_review_lane"], "candidate_provider_missing")
        self.assertEqual(
            missing_provider_item["source_url_review_lane"],
            "candidate_provider_missing",
        )
        self.assertIn(
            'site:shop.weverse.io "SEVENTEEN フォトカード（ランダム） SEVENTEEN 포토카드"',
            missing_provider_item["fallback_search_queries"],
        )
        self.assertEqual(
            missing_provider_item["store_search_hints"]["store_search_url"],
            "https://shop.weverse.io/search?keyword=SEVENTEEN+%E3%83%95%E3%82%A9%E3%83%88%E3%82%AB%E3%83%BC%E3%83%89%EF%BC%88%E3%83%A9%E3%83%B3%E3%83%80%E3%83%A0%EF%BC%89",
        )
        self.assertEqual(
            missing_provider_item["match_diagnostics"]["diagnosis"],
            "no_store_specific_candidate_report",
        )

    def test_low_confidence_candidate_is_not_prefilled(self) -> None:
        action_queue = {
            "batches": [
                {
                    "batch_id": "image-attachment-action-001",
                    "source_store": "Stellive Store",
                    "items": [
                        {
                            "catalog_index": 10,
                            "source_store": "Stellive Store",
                            "name_ko": "Badge",
                            "category": "Can Badge",
                            "source_url": "https://fanding.kr/@stellive/shop",
                            "source_url_import_template": {
                                "row_index": 10,
                                "field": "source_url",
                                "current_source_url": "https://fanding.kr/@stellive/shop",
                            },
                        },
                    ],
                }
            ]
        }
        candidate_report = {
            "queue": [
                {
                    "catalog_index": 10,
                    "candidate_status": "low_confidence_candidate",
                    "candidate_review_lane": "low_confidence_candidate_review",
                    "top_candidates": [
                        {
                            "product_no": 100,
                            "title": "Wrong-ish badge",
                            "source_url": "https://fanding.kr/@stellive/shop/100",
                            "image_url": "https://example.test/badge.webp",
                            "score": 0.27,
                        }
                    ],
                }
            ]
        }

        report = template.build_template(action_queue, candidate_report)
        item = report["items"][0]

        self.assertEqual(report["summary"]["candidate_prefilled_rows"], 0)
        self.assertEqual(item["candidate_source_url"], "")
        self.assertEqual(item["candidate_image_url"], "")
        self.assertEqual(item["candidate_title"], "")
        self.assertEqual(item["evidence_url"], "")
        self.assertEqual(item["candidate_options"][0]["product_no"], 100)
        self.assertIn("candidate_score_too_low", item["source_url_review_blockers"])

    def test_candidate_name_mismatch_is_not_attached(self) -> None:
        action_queue = {
            "batches": [
                {
                    "batch_id": "image-attachment-action-001",
                    "source_store": "Stellive Store",
                    "items": [
                        {
                            "catalog_index": 10,
                            "source_store": "Stellive Store",
                            "name_ko": "Correct Badge",
                            "category": "Can Badge",
                            "source_url": "https://fanding.kr/@stellive/shop",
                            "source_url_import_template": {
                                "row_index": 10,
                                "field": "source_url",
                                "current_source_url": "https://fanding.kr/@stellive/shop",
                            },
                        },
                    ],
                }
            ]
        }
        candidate_report = {
            "queue": [
                {
                    "catalog_index": 10,
                    "name_ko": "Different Badge",
                    "candidate_status": "weak_manual_review_candidate",
                    "candidate_review_lane": "weak_candidate_review",
                    "top_candidates": [
                        {
                            "product_no": 100,
                            "title": "Different Badge",
                            "source_url": "https://fanding.kr/@stellive/shop/100",
                            "score": 0.9,
                        }
                    ],
                }
            ]
        }

        report = template.build_template(action_queue, candidate_report)
        item = report["items"][0]

        self.assertEqual(item["candidate_status"], "no_candidate_report")
        self.assertEqual(item["candidate_source_url"], "")
        self.assertEqual(item["candidate_options"], [])
        self.assertEqual(item["source_url_review_lane"], "candidate_provider_missing")

    def test_stellive_rows_generate_official_store_search_hints(self) -> None:
        action_queue = {
            "batches": [
                {
                    "batch_id": "image-attachment-action-001",
                    "source_store": "Stellive Store",
                    "items": [
                        {
                            "catalog_index": 10,
                            "source_store": "Stellive Store",
                            "name_ko": "Mascot plush",
                            "category": "Plush",
                            "source_url": "https://fanding.kr/@stellive/shop",
                            "source_url_import_template": {
                                "row_index": 10,
                                "field": "source_url",
                                "current_source_url": "https://fanding.kr/@stellive/shop",
                            },
                        },
                    ],
                }
            ]
        }

        report = template.build_template(action_queue, None)
        item = report["items"][0]

        self.assertEqual(item["store_search_hints"]["storefront_url"], "https://fanding.kr/@stellive/shop")
        self.assertEqual(item["store_search_hints"]["site_query"], "site:fanding.kr/@stellive/shop")
        self.assertEqual(
            item["store_search_hints"]["store_search_url"],
            "https://stellive.fanding.kr/search?keyword=Mascot+plush",
        )
        self.assertIn(
            'site:fanding.kr/@stellive/shop "Mascot plush Plush"',
            item["fallback_search_queries"],
        )


if __name__ == "__main__":
    unittest.main()
