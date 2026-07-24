from __future__ import annotations

import sys
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enrich_movic_detail_fields_public as movic


HTML = """
<html>
  <head>
    <meta property="og:title" content="ダンガンロンパ 希望の学園と絶望の高校生 アクリルスタンド／苗木誠: アクリルスタンド／フィギュア｜ムービック（movic）">
    <meta property="og:image" content="https://www.movic.jp/img/goods/L/02330-00350-00624-l.jpg">
  </head>
  <body>
    <h1>ダンガンロンパ 希望の学園と絶望の高校生 アクリルスタンド／苗木誠</h1>
    <p>1,650円</p>
    <dl>
      <dt>発売日</dt><dd>2026/04/25</dd>
      <dt>商品コード</dt><dd>02330-00350-00624</dd>
    </dl>
    <p>JANコード：4550621606502</p>
  </body>
</html>
"""


class EnrichMovicDetailFieldsPublicTest(unittest.TestCase):
    def test_parse_movic_detail_extracts_labeled_fields(self) -> None:
        page = movic.parse_movic_detail(HTML)

        self.assertIn("苗木誠", page["title"])
        self.assertEqual(page["release_date"], "2026-04-25")
        self.assertEqual(page["official_price_jpy"], 1650)
        self.assertEqual(page["barcode"], "4550621606502")
        self.assertEqual(page["product_code"], "02330-00350-00624")

    def test_enrich_fills_missing_fields_and_reports_price_conflict(self) -> None:
        row = {
            "catalog_index": 1639,
            "name_ko": "단간론파 아크릴 스탠드 (나에기 마코토)",
            "name_ja": "ダンガンロンパ アクリルスタンド (苗木誠)",
            "source_store": "Movic",
            "source_url": "https://www.movic.jp/shop/g/g02330-00350-00624/",
            "image_url": "https://www.movic.jp/img/goods/S/02330-00350-00624-s.jpg",
            "official_price_jpy": 1320,
        }
        original_fetch = movic._fetch
        movic._fetch = lambda _url: HTML
        try:
            result = movic.enrich([row])
        finally:
            movic._fetch = original_fetch

        self.assertEqual(row["release_date"], "2026-04-25")
        self.assertEqual(row["barcode"], "4550621606502")
        self.assertEqual(row["official_price_jpy"], 1320)
        self.assertEqual(result["changes"][0]["fields"]["release_date"], "2026-04-25")
        self.assertEqual(result["price_conflicts"][0]["page_official_price_jpy"], 1650)

    def test_rejects_page_when_product_code_mismatches_url(self) -> None:
        row = {
            "catalog_index": 1,
            "name_ja": "ダンガンロンパ アクリルスタンド (苗木誠)",
            "source_store": "Movic",
            "source_url": "https://www.movic.jp/shop/g/g02330-00350-99999/",
            "image_url": "https://www.movic.jp/img/goods/S/02330-00350-99999-s.jpg",
        }
        original_fetch = movic._fetch
        movic._fetch = lambda _url: HTML
        try:
            result = movic.enrich([row])
        finally:
            movic._fetch = original_fetch

        self.assertEqual(result["changes"], [])
        self.assertEqual(result["rejected"][0]["reason"], "product_code_mismatch")

    def test_classifies_movic_503_as_waiting_room_or_block(self) -> None:
        row = {
            "catalog_index": 1639,
            "name_ja": "ダンガンロンパ アクリルスタンド (苗木誠)",
            "source_store": "Movic",
            "source_url": "https://www.movic.jp/shop/g/g02330-00350-00624/",
            "image_url": "https://www.movic.jp/img/goods/S/02330-00350-00624-s.jpg",
        }

        def raise_503(_url: str) -> str:
            raise urllib.error.HTTPError(_url, 503, "OK", {}, None)

        original_fetch = movic._fetch
        movic._fetch = raise_503
        try:
            result = movic.enrich([row])
        finally:
            movic._fetch = original_fetch

        self.assertEqual(result["changes"], [])
        self.assertEqual(result["rejected"][0]["reason"], "movic_http_503_blocked_or_waiting_room")


if __name__ == "__main__":
    unittest.main()
