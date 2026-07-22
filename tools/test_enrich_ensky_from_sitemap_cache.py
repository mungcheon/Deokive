from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enrich_ensky_from_sitemap_cache as ensky


class EnskySitemapCacheTests(unittest.TestCase):
    def test_safe_match_accepts_exact_numbered_variant(self):
        self.assertTrue(
            ensky._safe_match(
                "\u546a\u8853\u5efb\u6226 \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 (\u864e\u6756\u60a0\u4ec1)",
                "TV\u30a2\u30cb\u30e1\u300e\u546a\u8853\u5efb\u6226\u300f \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c95 /(1)\u864e\u6756\u60a0\u4ec1",
            )
        )

    def test_safe_match_rejects_group_variant_for_single_character_query(self):
        self.assertFalse(
            ensky._safe_match(
                "\u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3 \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 (\u30d5\u30ea\u30fc\u30ec\u30f3)",
                "TV\u30a2\u30cb\u30e1\u300c\u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3\u300d \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 /(5)\u30d5\u30ea\u30fc\u30ec\u30f3\u4e00\u884c",
            )
        )

    def test_enrich_reports_scanned_no_match_rows(self):
        rows = [
            {
                "catalog_index": 922,
                "name_ko": "\uce58\uc774\uce74\uc640 \ub7ec\ubc84 \uc2a4\ud2b8\ub7a9",
                "name_ja": "\u3061\u3044\u304b\u308f \u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7",
                "source_store": "\uc5d4\uc2a4\uce74\uc774",
                "image_url": None,
                "source_url": None,
            }
        ]
        result = ensky.enrich(rows, [])

        self.assertEqual(result["scanned_rows"], 1)
        self.assertEqual(result["updated_rows"], 0)
        self.assertEqual(result["no_matches"][0]["row_index"], 922)
        self.assertEqual(result["no_matches"][0]["name_ko"], "\uce58\uc774\uce74\uc640 \ub7ec\ubc84 \uc2a4\ud2b8\ub7a9")

    def test_enrich_reports_catalog_index_for_changes(self):
        rows = [
            {
                "catalog_index": "1392",
                "name_ko": "\uc8fc\uc220\ud68c\uc804 \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                "name_ja": "\u546a\u8853\u5efb\u6226 \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 (\u864e\u6756\u60a0\u4ec1)",
                "source_store": "\uc5d4\uc2a4\uce74\uc774",
                "image_url": None,
                "source_url": None,
            }
        ]
        products = [
            {
                "title": "TV\u30a2\u30cb\u30e1\u300e\u546a\u8853\u5efb\u6226\u300f \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c95 /(1)\u864e\u6756\u60a0\u4ec1",
                "image_url": "https://example.com/yuji.webp",
                "source_url": "https://example.com/yuji",
            }
        ]

        result = ensky.enrich(rows, products)

        self.assertEqual(result["updated_rows"], 1)
        self.assertEqual(result["changes"][0]["row_index"], 1392)
        self.assertEqual(rows[0]["image_url"], "https://example.com/yuji.webp")

    def test_row_identifier_falls_back_to_enumeration_index(self):
        self.assertEqual(ensky.row_identifier({}, 7), 7)


if __name__ == "__main__":
    unittest.main()
