from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ensky_cache_coverage_public as target


class EnskyCacheCoveragePublicTests(unittest.TestCase):
    def test_build_report_separates_exact_broad_and_missing_candidates(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "주술회전 아크릴 스탠드",
                    "name_ja": "呪術廻戦 アクリルスタンド (虎杖悠仁)",
                    "source_store": "엔스카이",
                    "affiliation": "주술회전",
                    "category": "아크릴 스탠드",
                    "image_url": None,
                },
                {
                    "catalog_index": 2,
                    "name_ko": "장송의 프리렌 아크릴 스탠드",
                    "name_ja": "葬送のフリーレン アクリルスタンド (フリーレン)",
                    "source_store": "엔스카이",
                    "affiliation": "장송의 프리렌",
                    "category": "아크릴 스탠드",
                    "image_url": None,
                },
                {
                    "catalog_index": 3,
                    "name_ko": "치이카와 러버 스트랩",
                    "name_ja": "ちいかわ ラバーストラップ (うさぎ)",
                    "source_store": "엔스카이",
                    "affiliation": "치이카와",
                    "category": "키링",
                    "image_url": None,
                },
            ]
        }
        products = [
            {
                "title": "TVアニメ『呪術廻戦』 アクリルスタンド5 /(1)虎杖悠仁",
                "image_url": "https://example.com/yuji.jpg",
                "source_url": "https://example.com/yuji",
            },
            {
                "title": "TVアニメ「葬送のフリーレン」 アクリルスタンド /(5)フリーレン一行",
                "image_url": "https://example.com/frieren.jpg",
                "source_url": "https://example.com/frieren",
            },
        ]

        report = target.build_report(catalog, products, generated_at="2026-01-01T00:00:00Z")
        statuses = {item["catalog_index"]: item["status"] for item in report["items"]}

        self.assertEqual(report["summary"]["missing_ensky_image_rows"], 3)
        self.assertEqual(report["summary"]["exact_safe_match_rows"], 1)
        self.assertEqual(report["summary"]["broad_cache_candidate_rows"], 1)
        self.assertEqual(report["summary"]["weak_cache_candidate_rows"], 0)
        self.assertEqual(report["summary"]["no_cache_candidate_rows"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(statuses[1], "exact_safe_match")
        self.assertEqual(statuses[2], "broad_cache_candidate")
        self.assertEqual(statuses[3], "no_cache_candidate")
        self.assertTrue(all(item["manual_review_required"] for item in report["items"]))

    def test_current_public_report_has_no_auto_apply(self) -> None:
        if not target.CACHE.exists():
            self.skipTest("Local Ensky sitemap cache is not available")

        report = target.build_report(
            target.load_json(target.CATALOG),
            target.load_json(target.CACHE),
            generated_at="2026-01-01T00:00:00Z",
        )

        expected_missing = len(target.missing_ensky_rows(target.catalog_items(target.load_json(target.CATALOG))))
        self.assertEqual(report["summary"]["missing_ensky_image_rows"], expected_missing)
        self.assertEqual(report["summary"]["cache_products"], 3153)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(len(report["items"]), expected_missing)

    def test_wrong_product_type_broad_candidate_is_filtered(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 10,
                    "name_ko": "치이카와 카라비너 러버 스트랩 (치이카와)",
                    "name_ja": "ちいかわ カラビナ付きラバーストラップ (ちいかわ)",
                    "source_store": "엔스카이",
                    "affiliation": "치이카와",
                    "category": "키링",
                    "image_url": None,
                }
            ]
        }
        products = [
            {
                "title": "ちいかわ mitamemoチケットファイル2【1BOX 14個入り】",
                "image_url": "https://example.com/ticket-file.jpg",
                "source_url": "https://www.enskyshop.com/products/detail/28997",
            }
        ]

        report = target.build_report(catalog, products, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["broad_cache_candidate_rows"], 0)
        self.assertEqual(report["summary"]["no_cache_candidate_rows"], 1)
        self.assertEqual(report["items"][0]["top_candidates"], [])

    def test_capsule_standy_candidate_is_not_acrylic_stand_match(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 11,
                    "name_ko": "원피스 아크릴 스탠드 (몽키 D 루피)",
                    "name_ja": "ONE PIECE アクリルスタンド (モンキー・D・ルフィ)",
                    "source_store": "엔스카이",
                    "affiliation": "원피스",
                    "category": "아크릴 스탠드",
                    "image_url": None,
                }
            ]
        }
        products = [
            {
                "title": "ワンピース カブセルスタンディ / モンキー・D・ルフィ(エルバフ) CC-ST050",
                "image_url": "https://www.enskyshop.com/html/upload/save_image/luffy.jpg",
                "source_url": "https://www.enskyshop.com/products/detail/32268",
            }
        ]

        report = target.build_report(catalog, products, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["broad_cache_candidate_rows"], 0)
        self.assertEqual(report["summary"]["no_cache_candidate_rows"], 1)
        self.assertEqual(report["items"][0]["top_candidates"], [])

    def test_affiliation_only_candidate_is_weak(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 20,
                    "name_ko": "치이카와 러버 스트랩 (치이카와)",
                    "name_ja": "ちいかわ ラバーストラップ (ちいかわ)",
                    "source_store": "엔스카이",
                    "affiliation": "치이카와",
                    "category": "키링",
                    "image_url": None,
                }
            ]
        }
        products = [
            {
                "title": "ちいかわ お絵かきボードセット",
                "image_url": "https://example.com/board.jpg",
                "source_url": "https://www.enskyshop.com/products/detail/26056",
            }
        ]

        report = target.build_report(catalog, products, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["broad_cache_candidate_rows"], 0)
        self.assertEqual(report["summary"]["weak_cache_candidate_rows"], 1)
        self.assertEqual(report["summary"]["no_cache_candidate_rows"], 0)
        self.assertEqual(report["items"][0]["status"], "weak_cache_candidate")
        self.assertTrue(report["items"][0]["top_candidates"][0]["weak_broad_match"])


if __name__ == "__main__":
    unittest.main()
