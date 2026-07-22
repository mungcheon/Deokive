from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enrich_chiikawa_market_name_ja_public as target


class ChiikawaMarketNameJaPublicEnrichmentTest(unittest.TestCase):
    def test_enriches_name_ja_by_exact_barcode_identity(self) -> None:
        catalog = {
            "meta": {"missing": {"name_ja": 1}},
            "items": [
                {
                    "catalog_index": 7,
                    "name_ko": "치이카와 테스트 상품",
                    "source_store": "치이카와 마켓",
                    "barcode": "4970381532567",
                    "source_url": "https://chiikawamarket.jp/ko/products/4970381532567",
                }
            ],
        }
        products = [
            {
                "title": "ちいかわ テスト商品",
                "handle": "4970381532567",
                "variants": [{"barcode": "4970381532567"}],
            }
        ]

        report = target.enrich_catalog(catalog, products, "2026-01-01T00:00:00Z")

        self.assertEqual(catalog["items"][0]["name_ja"], "ちいかわ テスト商品")
        self.assertEqual(report["summary"]["updated_rows"], 1)
        self.assertEqual(report["summary"]["market_missing_name_ja_after"], 0)
        self.assertEqual(catalog["meta"]["missing"]["name_ja"], 0)

    def test_does_not_translate_or_guess_without_exact_identity(self) -> None:
        catalog = {
            "meta": {"missing": {"name_ja": 1}},
            "items": [
                {
                    "catalog_index": 9,
                    "name_ko": "치이카와 이름만 있는 상품",
                    "source_store": "치이카와 마켓",
                }
            ],
        }

        report = target.enrich_catalog(catalog, [], "2026-01-01T00:00:00Z")

        self.assertNotIn("name_ja", catalog["items"][0])
        self.assertEqual(report["summary"]["updated_rows"], 0)
        self.assertEqual(report["summary"]["market_missing_name_ja_after"], 1)

    def test_uses_source_handle_when_barcode_is_blank(self) -> None:
        catalog = {
            "meta": {},
            "items": [
                {
                    "catalog_index": 11,
                    "name_ko": "치이카와 핸들 매칭 상품",
                    "source_store": "치이카와 마켓",
                    "source_url": "https://chiikawamarket.jp/ko/products/4570189203968",
                }
            ],
        }
        products = [
            {
                "title": "ちいかわ ハンドル一致商品",
                "handle": "4570189203968",
                "variants": [{"sku": "4570189203968"}],
            }
        ]

        report = target.enrich_catalog(catalog, products, "2026-01-01T00:00:00Z")

        self.assertEqual(catalog["items"][0]["name_ja"], "ちいかわ ハンドル一致商品")
        self.assertEqual(report["summary"]["matched_rows"], 1)


if __name__ == "__main__":
    unittest.main()
