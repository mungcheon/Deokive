from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prune_public_ichiban_duplicate_image_rows as target


class PrunePublicIchibanDuplicateImageRowsTest(unittest.TestCase):
    def test_prunes_root_kuji_row_when_official_product_row_shares_image(self) -> None:
        catalog = {
            "meta": {"row_count": 2},
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "legacy",
                    "source_url": "https://1kuji.com/",
                    "image_url": "https://assets.1kuji.com/item.webp",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "official",
                    "name_ja": "A prize official",
                    "source_url": "https://1kuji.com/products/demo",
                    "image_url": "https://assets.1kuji.com/item.webp",
                },
            ],
        }

        report = target.prune_duplicate_image_rows(catalog, write=True)

        self.assertEqual(report["summary"]["pruned_rows"], 1)
        self.assertEqual(catalog["meta"]["row_count"], 1)
        self.assertEqual(catalog["items"][0]["catalog_index"], 2)
        self.assertEqual(report["pruned_rows"][0]["official_keep"]["catalog_index"], 2)

    def test_keeps_root_row_without_official_image_match(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "legacy",
                    "source_url": "https://1kuji.com/",
                    "image_url": "https://assets.1kuji.com/item.webp",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "other official",
                    "source_url": "https://1kuji.com/products/demo",
                    "image_url": "https://assets.1kuji.com/other.webp",
                },
            ],
        }

        report = target.prune_duplicate_image_rows(catalog, write=True)

        self.assertEqual(report["summary"]["pruned_rows"], 0)
        self.assertEqual(len(catalog["items"]), 2)


if __name__ == "__main__":
    unittest.main()
