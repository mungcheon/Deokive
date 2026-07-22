from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enrich_fanding_store_from_shop_api as fanding


class FandingStoreEnrichmentTests(unittest.TestCase):
    def test_clean_korean_member_token_mismatch_rejects_candidate(self) -> None:
        product = {"aTitle": {"ko": "2025 비비 아크릴 스탠드"}, "iProductNo": 50}

        self.assertIsNone(fanding._rank_product_candidate("린 데뷔 기념 아크릴 스탠드", product))

    def test_clean_korean_member_and_product_type_match_keeps_candidate(self) -> None:
        product = {"aTitle": {"ko": "2025 린 아크릴 스탠드"}, "iProductNo": 51}
        candidate = fanding._rank_product_candidate("린 데뷔 기념 아크릴 스탠드", product)

        self.assertIsNotNone(candidate)
        self.assertIn("린", candidate["shared_tokens"])

    def test_clean_korean_product_type_mismatch_rejects_candidate(self) -> None:
        product = {"aTitle": {"ko": "강지 응원봉"}, "iProductNo": 52}

        self.assertIsNone(fanding._rank_product_candidate("강지 마스코트 인형", product))

    def test_clean_korean_goods_box_does_not_match_voice_only_product(self) -> None:
        product = {"aTitle": {"ko": "2025 히나 생일 보이스팩"}, "iProductNo": 982}

        self.assertIsNone(fanding._rank_product_candidate("시라유키 히나 생일 굿즈 박스 2025", product))

    def test_korean_member_token_mismatch_rejects_candidate(self) -> None:
        product = {"aTitle": {"ko": "2025 비비 아크릴 스탠드"}, "iProductNo": 50}

        self.assertIsNone(fanding._rank_product_candidate("린 데뷔 기념 아크릴 스탠드", product))

    def test_korean_member_and_product_type_match_keeps_candidate(self) -> None:
        product = {"aTitle": {"ko": "2025 린 아크릴 스탠드"}, "iProductNo": 51}
        candidate = fanding._rank_product_candidate("린 데뷔 기념 아크릴 스탠드", product)

        self.assertIsNotNone(candidate)
        self.assertIn("린", candidate["shared_tokens"])

    def test_korean_product_type_mismatch_rejects_candidate(self) -> None:
        product = {"aTitle": {"ko": "강지 응원봉"}, "iProductNo": 52}

        self.assertIsNone(fanding._rank_product_candidate("강지 마스코트 인형", product))

    def test_member_token_mismatch_rejects_candidate(self) -> None:
        product = {"aTitle": {"ko": "2023 타비 아크릴 키링"}, "iProductNo": 50}

        self.assertIsNone(fanding._rank_product_candidate("비비 아크릴 키링", product))

    def test_member_specific_query_rejects_generic_group_product(self) -> None:
        product = {"aTitle": {"ko": "<스텔라이브 클리셰 1주년> 아크릴 스탠드 (단품)"}, "iProductNo": 1354}

        self.assertIsNone(fanding._rank_product_candidate("비비 데뷔 기념 아크릴 스탠드", product))

    def test_member_token_match_keeps_candidate(self) -> None:
        product = {"aTitle": {"ko": "2023 리제 아크릴 스탠드"}, "iProductNo": 55}
        candidate = fanding._rank_product_candidate("아카네 리제 데뷔 2주년 아크릴 스탠드", product)

        self.assertIsNotNone(candidate)
        self.assertIn("리제", candidate["shared_tokens"])

    def test_product_type_mismatch_rejects_candidate(self) -> None:
        product = {"aTitle": {"ko": "강지 응원봉"}, "iProductNo": 2007}

        self.assertIsNone(fanding._rank_product_candidate("강지 마스코트 인형", product))

    def test_tote_bag_does_not_match_keycap(self) -> None:
        product = {"aTitle": {"ko": "스텔라이브 아티산 키캡 - 아카네 리제"}, "iProductNo": 676}

        self.assertIsNone(fanding._rank_product_candidate("아카네 리제 토트백", product))

    def test_goods_box_does_not_match_voice_only_product(self) -> None:
        product = {"aTitle": {"ko": "2025 히나 생일 보이스"}, "iProductNo": 982}

        self.assertIsNone(fanding._rank_product_candidate("시라유키 히나 생일 굿즈 박스 2025", product))

    def test_strong_candidate_can_update_existing_same_image_row(self) -> None:
        row = {
            "source_url": fanding.FANDING_SHOP_URL,
            "image_url": "https://dcjnmis8jxmbl.cloudfront.net/upload/image/product_thumbnail/2025/09/18/WFKCqAQ5kEUHp1ig.webp",
        }
        candidate = {
            "source_url": "https://fanding.kr/@stellive/shop/1288",
            "image_url": "https://uploads.cdn.fanding.com/upload/image/product_thumbnail/2025/09/18/WFKCqAQ5kEUHp1ig.webp",
            "score": 0.948,
            "shared_tokens": ["생일", "스탠드", "아크릴"],
        }

        self.assertTrue(fanding._can_auto_update_existing_image_row(row, candidate))

    def test_strong_candidate_does_not_update_missing_image_row(self) -> None:
        row = {"source_url": fanding.FANDING_SHOP_URL, "image_url": ""}
        candidate = {
            "source_url": "https://fanding.kr/@stellive/shop/1288",
            "image_url": "https://uploads.cdn.fanding.com/upload/image/product_thumbnail/2025/09/18/WFKCqAQ5kEUHp1ig.webp",
            "score": 0.948,
            "shared_tokens": ["생일", "스탠드", "아크릴"],
        }

        self.assertFalse(fanding._can_auto_update_existing_image_row(row, candidate))

    def test_strong_candidate_requires_same_image_file(self) -> None:
        row = {
            "source_url": fanding.FANDING_SHOP_URL,
            "image_url": "https://dcjnmis8jxmbl.cloudfront.net/upload/image/product_thumbnail/2025/09/18/other.webp",
        }
        candidate = {
            "source_url": "https://fanding.kr/@stellive/shop/1288",
            "image_url": "https://uploads.cdn.fanding.com/upload/image/product_thumbnail/2025/09/18/WFKCqAQ5kEUHp1ig.webp",
            "score": 0.948,
            "shared_tokens": ["생일", "스탠드", "아크릴"],
        }

        self.assertFalse(fanding._can_auto_update_existing_image_row(row, candidate))

    def test_debut_query_does_not_match_birthday_product(self) -> None:
        product = {"aTitle": {"ko": "2025 린 생일 회전목마 아크릴 스탠드"}, "iProductNo": 1288}

        self.assertIsNone(fanding._rank_product_candidate("린 데뷔 기념 아크릴 스탠드", product))

    def test_birthday_query_does_not_match_debut_product(self) -> None:
        product = {"aTitle": {"ko": "2025 린 데뷔 기념 아크릴 스탠드"}, "iProductNo": 1289}

        self.assertIsNone(fanding._rank_product_candidate("린 생일 기념 아크릴 스탠드", product))

    def test_anniversary_number_must_match(self) -> None:
        product = {"aTitle": {"ko": "아카네 리제 데뷔 1주년 아크릴 스탠드"}, "iProductNo": 1290}

        self.assertIsNone(fanding._rank_product_candidate("아카네 리제 데뷔 2주년 아크릴 스탠드", product))

    def test_status_counts_groups_candidate_statuses(self) -> None:
        counts = fanding._status_counts(
            [
                {"candidate_status": "weak_manual_review_candidate"},
                {"candidate_status": "weak_manual_review_candidate"},
                {"candidate_status": "no_candidate"},
            ]
        )

        self.assertEqual(
            counts,
            {
                "no_candidate": 1,
                "weak_manual_review_candidate": 2,
            },
        )

    def test_no_candidate_gets_manual_search_diagnostics(self) -> None:
        row = {
            "name_ko": "강지 마스코트 인형",
            "category": "인형",
            "affiliation": "스텔라이브",
        }
        queries = fanding._fallback_search_queries(row, row["name_ko"])

        self.assertEqual(
            fanding._candidate_review_lane("no_candidate", []),
            "manual_search_required",
        )
        self.assertIn("site:fanding.kr/@stellive/shop 강지 마스코트 인형", queries)
        self.assertEqual(
            fanding._match_diagnostics(row["name_ko"], [])["diagnosis"],
            "no_product_matched_member_and_product_type_filters",
        )


if __name__ == "__main__":
    unittest.main()
