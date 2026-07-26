from __future__ import annotations

import unittest

from tools.build_reused_image_deduplication_review_public import build_report


class BuildReusedImageDeduplicationReviewPublicTest(unittest.TestCase):
    def test_online_kuji_same_image_distinct_names_becomes_manual_candidate(self) -> None:
        reused = {
            "groups": [
                {
                    "risk": "medium",
                    "recommended_action": "review_possible_duplicate_or_reissue_before_keep",
                    "local_image_path": "assets/catalog_images/shared.webp",
                    "source_urls": ["https://online-kuji.chiikawamarket.jp/store/lottery/usagi"],
                    "image_urls": ["https://example.test/shared.png"],
                    "rows": [
                        {
                            "catalog_index": 660,
                            "name_ko": "D상: 마스코트 피자만",
                            "name_ja": "D賞 マスコット ピザまん",
                            "category": "마스코트",
                            "character_name": "우사기",
                            "source_store": "치이카와 온라인 쿠지",
                            "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/usagi",
                            "image_url": "https://example.test/shared.png",
                            "local_image_path": "assets/catalog_images/shared.webp",
                        },
                        {
                            "catalog_index": 11703,
                            "name_ko": "ちいかわ うさぎだらけくじ - D ピザまん",
                            "name_ja": "D ピザまん",
                            "category": "마스코트",
                            "character_name": "우사기",
                            "source_store": "치이카와 온라인 쿠지",
                            "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/usagi",
                            "image_url": "https://example.test/shared.png",
                            "local_image_path": "assets/catalog_images/shared.webp",
                        },
                    ],
                }
            ]
        }

        report = build_report(reused, generated_at="2026-07-26T00:00:00Z")

        self.assertEqual(report["summary"]["candidate_groups"], 1)
        self.assertEqual(report["summary"]["strong_manual_duplicate_candidate_groups"], 1)
        item = report["items"][0]
        self.assertEqual(item["confidence"], "strong_manual_duplicate_candidate")
        self.assertTrue(item["source_url_same"])
        self.assertTrue(item["image_same"])
        self.assertFalse(item["decision_template"]["manual_confirmed"])
        self.assertIn("same_sellable_product_keep_one", item["decision_template"]["allowed_decisions"])
        self.assertEqual(
            item["decision_template"]["evidence_urls"],
            ["https://online-kuji.chiikawamarket.jp/store/lottery/usagi"],
        )

    def test_non_online_kuji_candidates_are_skipped(self) -> None:
        reused = {
            "groups": [
                {
                    "risk": "medium",
                    "recommended_action": "review_possible_duplicate_or_reissue_before_keep",
                    "local_image_path": "assets/catalog_images/shared.webp",
                    "rows": [
                        {
                            "catalog_index": 1,
                            "name_ko": "넨도로이드",
                            "category": "피규어",
                            "character_name": "A",
                            "source_store": "굿스마일컴퍼니",
                            "source_url": "https://www.goodsmile.info/ja/product/1/",
                            "image_url": "https://example.test/shared.png",
                            "local_image_path": "assets/catalog_images/shared.webp",
                        },
                        {
                            "catalog_index": 2,
                            "name_ko": "POP UP PARADE",
                            "category": "피규어",
                            "character_name": "A",
                            "source_store": "굿스마일컴퍼니",
                            "source_url": "https://www.goodsmile.info/ja/product/1/",
                            "image_url": "https://example.test/shared.png",
                            "local_image_path": "assets/catalog_images/shared.webp",
                        },
                    ],
                }
            ]
        }

        report = build_report(reused, generated_at="2026-07-26T00:00:00Z")

        self.assertEqual(report["summary"]["candidate_groups"], 0)
        self.assertEqual(report["summary"]["skipped_reasons"], [["not_all_online_kuji_rows", 1]])


if __name__ == "__main__":
    unittest.main()
