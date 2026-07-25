from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_catalog_image_review_batches as review_batches
from build_catalog_image_review_batches import build_batches


class CatalogImageReviewBatchTests(unittest.TestCase):
    def test_default_queue_uses_current_image_enrichment_queue(self):
        self.assertEqual(
            review_batches.DEFAULT_QUEUE.name,
            "catalog_image_enrichment_queue_current.json",
        )

    def test_groups_missing_images_and_adds_search_links(self):
        payload = build_batches(
            [
                {
                    "row_index": 7,
                    "name_ko": "하치와레 마스코트",
                    "name_ja": "ハチワレ マスコット",
                    "source_store": "치이카와 마켓",
                    "category": "마스코트",
                    "automation_safety": "candidate_provider_script_required",
                    "strategy": "official_search",
                },
                {
                    "name_ko": "치이카와 마스코트",
                    "source_store": "치이카와 마켓",
                    "category": "마스코트",
                    "automation_safety": "candidate_provider_script_required",
                    "strategy": "official_search",
                },
            ]
        )

        self.assertEqual(payload["missing_images"], 2)
        self.assertEqual(payload["batch_count"], 1)
        batch = payload["batches"][0]
        self.assertEqual(batch["workflow"], "provider_script_recheck")
        self.assertEqual(batch["official_search_host"], "chiikawamarket.jp")
        self.assertEqual(batch["sample_items"][0]["row_index"], 7)
        links = batch["sample_items"][0]["links"]
        self.assertIn("official_site_search", links)
        self.assertIn("official_context_search", links)
        self.assertIn("image_search", links)
        self.assertIn("context_image_search", links)
        self.assertIn("contextual_search_query", batch["sample_items"][0])

    def test_generic_storefront_requires_exact_product_page(self):
        payload = build_batches(
            [
                {
                    "name_ko": "아이리 칸나 머그컵",
                    "source_store": "Stellive Store",
                    "category": "머그컵",
                    "automation_safety": "blocked_until_exact_product_url",
                    "strategy": "source_url_generic_storefront",
                    "source_url": "https://fanding.kr/@stellive/shop",
                },
            ]
        )

        batch = payload["batches"][0]
        self.assertEqual(batch["workflow"], "find_exact_product_page")
        self.assertEqual(batch["has_source_url_count"], 1)
        self.assertIn("current_source", batch["sample_items"][0]["links"])
        self.assertIn("context_web_search", batch["sample_items"][0]["links"])

    def test_goodsmile_adds_current_and_legacy_official_hosts(self):
        payload = build_batches(
            [
                {
                    "row_index": 1408,
                    "name_ko": "POP UP PARADE 리코",
                    "name_ja": "POP UP PARADE リコ",
                    "source_store": "굿스마일컴퍼니",
                    "category": "피규어",
                    "affiliation": "메이드 인 어비스",
                    "automation_safety": "candidate_provider_script_required",
                    "strategy": "official_search",
                },
            ]
        )

        batch = payload["batches"][0]
        self.assertEqual(batch["official_search_hosts"], ["goodsmile.com", "goodsmile.info"])
        links = batch["sample_items"][0]["links"]
        self.assertIn("site%3Agoodsmile.com", links["official_site_search"])
        self.assertIn("site%3Agoodsmile.info", links["official_site_search_2"])

    def test_attaches_provider_recheck_diagnostics_to_batches(self):
        payload = build_batches(
            [
                {
                    "row_index": 921,
                    "name_ko": "치이카와 러버 스트랩 (하치와레)",
                    "name_ja": "ちいかわ ラバーストラップ (ハチワレ)",
                    "source_store": "엔스카이",
                    "category": "키링",
                    "automation_safety": "candidate_provider_script_required",
                    "strategy": "official_search",
                },
            ],
            provider_recheck={
                921: {
                    "reason": "best_candidate_rejected",
                    "rejection_reason": "failed_safety_checks",
                    "failed_checks": ["goods_type_compatible", "all_distinctive_token_match"],
                    "candidate_count": 128,
                }
            },
        )

        self.assertEqual(payload["provider_recheck_rows"], 1)
        batch = payload["batches"][0]
        self.assertEqual(batch["official_search_host"], "enskyshop.com")
        self.assertEqual(batch["provider_recheck_count"], 1)
        self.assertEqual(batch["provider_recheck_by_reason"], [("best_candidate_rejected", 1)])
        self.assertEqual(batch["provider_recheck_failed_checks"][0], ("goods_type_compatible", 1))
        self.assertEqual(
            batch["sample_items"][0]["provider_recheck"]["rejection_reason"],
            "failed_safety_checks",
        )


if __name__ == "__main__":
    unittest.main()
