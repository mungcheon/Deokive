from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from enrich_detail_page_fields import (
    _extract_fields,
    _fetch_text,
    _row_contains,
    _safe_title_match,
    enrich,
    load_catalog,
    write_catalog,
)


class DetailPageFieldEnrichmentSafetyTest(unittest.TestCase):
    def test_rejects_chiikawa_card_page_for_rubber_strap(self) -> None:
        row = {
            "name_ko": "\uce58\uc774\uce74\uc640 \ub7ec\ubc84 \uc2a4\ud2b8\ub7a9 (\uce58\uc774\uce74\uc640)",
            "name_ja": "\u3061\u3044\u304b\u308f \u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7 (\u3061\u3044\u304b\u308f)",
        }
        title = (
            "\u3061\u3044\u304b\u308f \u30d0\u30e9\u30a8\u30c6\u30a3\u30ab\u30fc\u30c9 "
            "\u30ac\u30e0\u3064\u304d\u30101BOX 16\u30d1\u30c3\u30af\u5165\u308a\u3011"
            " \uff5c \u30a8\u30f3\u30b9\u30ab\u30a4\u30b7\u30e7\u30c3\u30d7"
        )
        self.assertFalse(_safe_title_match(row, title))

    def test_rejects_korean_only_mug_for_japanese_magnet(self) -> None:
        row = {"name_ko": "\uadc0\uba78\uc758 \uce7c\ub0a0 \ubbf8\uce20\ub9ac \uba38\uadf8\ucef5"}
        title = (
            "\u3010\u30b0\u30c3\u30ba-\u30de\u30b0\u30cd\u30c3\u30c8\u3011"
            "\u9b3c\u6ec5\u306e\u5203 \u30ac\u30e9\u30b9\u30de\u30b0\u30cd\u30c3\u30c8vol.6 "
            "\u7518\u9732\u5bfa\u871c\u7483\u3010\u518d\u8ca9\u3011 | \u30a2\u30cb\u30e1\u30a4\u30c8"
        )
        self.assertFalse(_safe_title_match(row, title))

    def test_accepts_exact_japanese_product_name_in_title(self) -> None:
        name = (
            "TV\u30a2\u30cb\u30e1\u300e\u546a\u8853\u5efb\u6226\u300f "
            "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c95 /(1)\u864e\u6756\u60a0\u4ec1"
        )
        row = {"name_ko": "\uc8fc\uc220\ud68c\uc804 \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc (\uc774\ud0c0\ub3c4\ub9ac)", "name_ja": name}
        title = f"{name} \uff5c \u30a8\u30f3\u30b9\u30ab\u30a4\u30b7\u30e7\u30c3\u30d7"
        self.assertTrue(_safe_title_match(row, title))

    def test_accepts_distinctive_substring_japanese_product_name(self) -> None:
        row = {
            "name_ko": "\ub2e8\uac04\ub860\ud30c \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc (\ucf54\ub9c8\uc5d0\ub2e4 \ub098\uae30\ud1a0)",
            "name_ja": "\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1 \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 (\u72db\u679d\u51ea\u6597)",
        }
        title = (
            "\u3010\u30b0\u30c3\u30ba-\u30b9\u30bf\u30f3\u30c9\u30dd\u30c3\u30d7\u3011"
            "\u30b9\u30fc\u30d1\u30fc\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d12 "
            "\u3055\u3088\u306a\u3089\u7d76\u671b\u5b66\u5712 "
            "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9\uff0f\u72db\u679d\u51ea\u6597 | \u30a2\u30cb\u30e1\u30a4\u30c8"
        )

        self.assertTrue(_safe_title_match(row, title))

    def test_extracts_kotobukiya_detail_fields(self) -> None:
        source = """
        <html><body>
        <section>
          <p>\u767a\u58f2\u6708 2026\u5e7411\u6708</p>
          <p>\u4fa1\u683c 35,860 \u5186\uff08\u7a0e\u8fbc\uff09 32,600 \u5186\uff08\u7a0e\u629c\uff09</p>
          <p>\u521d\u56de\u767a\u58f2\u6708 2026\u5e7411\u6708</p>
        </section>
        </body></html>
        """
        fields = _extract_fields(
            "\ucf54\ud1a0\ubd80\ud0a4\uc57c",
            source,
            "https://www.kotobukiya.co.jp/product/detail/p4934054077151/",
        )
        self.assertEqual(fields["barcode"], "4934054077151")
        self.assertEqual(fields["release_date"], "2026-11")
        self.assertEqual(fields["official_price_jpy"], 35860)

    def test_row_contains_filters_priority_text(self) -> None:
        row = {
            "name_ko": "\ub2e8\uac04\ub860\ud30c \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
            "source_store": "Movic",
        }

        self.assertTrue(_row_contains(row, ["\ub2e8\uac04\ub860\ud30c"]))
        self.assertFalse(_row_contains(row, ["\ub9c8\ub140\uc7ac\ud310"]))

    def test_load_and_write_catalog_object_refreshes_missing_meta(self) -> None:
        import json
        import tempfile

        payload = {
            "meta": {
                "fields": ["name_ko", "release_date"],
                "missing": {"name_ko": 0, "release_date": 1},
                "row_count": 1,
                "total_items": 1,
            },
            "items": [{"name_ko": "\uc0c1\ud488", "release_date": None}],
            "total_items": 1,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            rows, wrapper = load_catalog(path)
            rows[0]["release_date"] = "2026-04"
            write_catalog(path, rows, wrapper)

            written = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(written["meta"]["missing"]["release_date"], 0)
        self.assertEqual(written["meta"]["row_count"], 1)
        self.assertEqual(written["total_items"], 1)

    def test_fetch_text_classifies_http_errors(self) -> None:
        import urllib.error
        from unittest.mock import patch

        def raise_429(_request, timeout):
            raise urllib.error.HTTPError("https://example.com", 429, "Too Many Requests", {}, None)

        with patch("urllib.request.urlopen", side_effect=raise_429):
            source, reason = _fetch_text("https://example.com")

        self.assertIsNone(source)
        self.assertEqual(reason, "http_error_429")

    def test_enrich_offset_skips_processable_rows_before_fetching(self) -> None:
        rows = [
            {
                "name_ko": "first",
                "name_ja": "TVアニメ『呪術廻戦』 アクリルスタンド5 /(1)虎杖悠仁",
                "source_store": "엔스카이",
                "source_url": "https://www.enskyshop.com/products/detail/31157",
            },
            {
                "name_ko": "second",
                "name_ja": "TVアニメ『呪術廻戦』 アクリルスタンド5 /(2)伏黒恵",
                "source_store": "엔스카이",
                "source_url": "https://www.enskyshop.com/products/detail/31158",
            },
        ]
        fetched: list[str] = []

        def fake_fetch(url: str):
            fetched.append(url)
            return (
                "<html><title>TVアニメ『呪術廻戦』 アクリルスタンド5 /(2)伏黒恵 ｜ エンスカイショップ</title>"
                "商品コード 4970381922535 初回出荷開始日 2026年6月</html>",
                None,
            )

        from unittest.mock import patch

        with patch("enrich_detail_page_fields._fetch_text", side_effect=fake_fetch):
            updated, changes, rejected = enrich(rows, max_rows=1, offset=1)

        self.assertEqual(fetched, ["https://www.enskyshop.com/products/detail/31158"])
        self.assertEqual(updated, 1)
        self.assertEqual(changes[0]["name_ko"], "second")
        self.assertEqual(rejected, [])


if __name__ == "__main__":
    unittest.main()
