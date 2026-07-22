from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from filter_confirmed_image_candidates import build_import_queue


class FilterConfirmedImageCandidatesTests(unittest.TestCase):
    def test_keeps_only_confirmed_rows_with_urls(self) -> None:
        result = build_import_queue(
            [
                {
                    "row_index": 3,
                    "manual_confirmed": True,
                    "source_url": "https://www.movic.jp/shop/g/g123/",
                    "image_url": "https://www.movic.jp/img/goods/1/123.jpg",
                    "name_ko": "A",
                },
                {
                    "row_index": 4,
                    "manual_confirmed": False,
                    "source_url": "https://www.movic.jp/shop/g/g456/",
                    "image_url": "https://www.movic.jp/img/goods/1/456.jpg",
                },
                {"row_index": 5, "manual_confirmed": True, "source_url": ""},
            ]
        )

        self.assertEqual(result["summary"]["ready_items"], 1)
        self.assertEqual(result["items"][0]["row_index"], 3)
        self.assertEqual(result["items"][0]["source_kind"], "licensed_retailer_exact")
        self.assertEqual(result["summary"]["skipped_items"], 2)

    def test_rejects_duplicate_row_index_after_first_ready_item(self) -> None:
        result = build_import_queue(
            [
                {
                    "row_index": 8,
                    "manual_confirmed": "confirmed",
                    "source_url": "https://www.movic.jp/shop/g/g123/",
                    "image_url": "https://www.movic.jp/img/goods/1/123.jpg",
                },
                {
                    "row_index": 8,
                    "manual_confirmed": True,
                    "source_url": "https://www.movic.jp/shop/g/g456/",
                    "image_url": "https://www.movic.jp/img/goods/1/456.jpg",
                },
            ]
        )

        self.assertEqual(result["summary"]["ready_items"], 1)
        self.assertEqual(result["skipped_sample"][0]["reason"], "duplicate_row_index")


if __name__ == "__main__":
    unittest.main()
