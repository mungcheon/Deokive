from __future__ import annotations

import sys
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enrich_images_from_source_url as enrich


class EnrichImagesFromSourceUrlTests(unittest.TestCase):
    def test_load_and_write_catalog_object_preserves_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            path.write_text(
                '{"meta":{"row_count":1},"items":[{"catalog_index":7,"name_ko":"테스트"}]}',
                encoding="utf-8",
            )

            rows, wrapper = enrich.load_catalog(path)
            self.assertEqual(rows, [{"catalog_index": 7, "name_ko": "테스트"}])
            self.assertIsNotNone(wrapper)

            rows[0]["image_url"] = "https://example.com/item.jpg"
            enrich.write_catalog(path, rows, wrapper)

            written_rows, written_wrapper = enrich.load_catalog(path)
            self.assertEqual(written_rows[0]["image_url"], "https://example.com/item.jpg")
            self.assertEqual(written_wrapper["meta"]["row_count"], 1)

    def test_main_reports_unfilled_public_catalog_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog = Path(tmp) / "catalog_public.json"
            report = Path(tmp) / "report.json"
            catalog.write_text(
                json.dumps(
                    {
                        "meta": {"row_count": 1},
                        "items": [
                            {
                                "catalog_index": 3,
                                "name_ko": "후보",
                                "source_store": "공식",
                                "source_url": "https://example.com/products/item",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(enrich, "fetch_image", return_value=None):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "enrich_images_from_source_url.py",
                        "--input",
                        str(catalog),
                        "--report",
                        str(report),
                        "--allow-non-product-source",
                    ],
                ):
                    enrich.main()

            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["candidates"], 1)
            self.assertEqual(payload["filled"], 0)
            self.assertEqual(payload["unfilled"], 1)
            self.assertEqual(payload["attempted"][0]["catalog_index"], 3)
            self.assertEqual(payload["attempted"][0]["status"], "no_safe_image_found")

    def test_non_product_source_requires_explicit_option(self) -> None:
        html = '<meta property="og:image" content="https://example.com/images/collab-keyvisual.jpg">'
        response = Mock()
        response.headers.get_content_charset.return_value = "utf-8"
        response.read.return_value = html.encode("utf-8")
        response.__enter__ = lambda item: item
        response.__exit__ = lambda *args: None

        with patch.object(enrich.urllib.request, "urlopen", return_value=response):
            self.assertIsNone(enrich.fetch_image("https://example.com/news/collab"))

        with patch.object(enrich.urllib.request, "urlopen", return_value=response):
            self.assertEqual(
                enrich.fetch_image("https://example.com/news/collab", allow_non_product_source=True),
                "https://example.com/images/collab-keyvisual.jpg",
            )


if __name__ == "__main__":
    unittest.main()
