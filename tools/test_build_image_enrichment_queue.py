from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_image_enrichment_queue as queue


class ImageEnrichmentQueueTests(unittest.TestCase):
    def test_row_identifier_prefers_catalog_index_for_public_catalog_rows(self) -> None:
        self.assertEqual(queue.row_identifier({"catalog_index": 17613}, 17452), 17613)
        self.assertEqual(queue.row_identifier({"catalog_index": "17622"}, 17461), 17622)
        self.assertEqual(queue.row_identifier({"name_ko": "sample"}, 12), 12)

    def test_chiikawa_market_prefers_japanese_name_for_shopify_matching(self) -> None:
        row = {
            "source_store": queue.CHIIKAWA_MARKET_STORE,
            "affiliation": "\u30c1\u30a4\u30ab\u30ef",
            "category": "\u30de\u30b9\u30b3\u30c3\u30c8",
            "name_ko": "\uce58\uc774\uce74\uc640 \uace0\ud1a0\uce58 \ub9c8\uc2a4\ucf54\ud2b8",
            "name_ja": "\u3061\u3044\u304b\u308f \u3054\u5f53\u5730\u30de\u30b9\u30b3\u30c3\u30c8",
        }

        self.assertEqual(queue.preferred_query(row), "\u3061\u3044\u304b\u308f \u3054\u5f53\u5730\u30de\u30b9\u30b3\u30c3\u30c8")
        self.assertIn("%E3%81%A1%E3%81%84%E3%81%8B%E3%82%8F", queue.search_url(row) or "")


if __name__ == "__main__":
    unittest.main()
