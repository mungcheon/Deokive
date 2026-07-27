from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.import_confirmed_ichiban_variant_lineup_splits_public import import_splits


def _catalog() -> dict[str, object]:
    return {
        "meta": {
            "fields": [
                "catalog_index",
                "name_ko",
                "name_ja",
                "category",
                "character_name",
                "affiliation",
                "series_name",
                "sub_series",
                "image_url",
                "source_url",
            ]
        },
        "total_items": 1,
        "items": [
            {
                "catalog_index": 10,
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST / H\u8cde / \u30b9\u30c6\u30c3\u30ab\u30fc\u30a2\u30bd\u30fc\u30c8 / \uae30\ud0c0",
                "name_ja": "H\u8cde \u30b9\u30c6\u30c3\u30ab\u30fc\u30a2\u30bd\u30fc\u30c8",
                "category": "\uc2a4\ud2f0\ucee4",
                "character_name": "\uae30\ud0c0",
                "affiliation": "TEST",
                "series_name": "\u4e00\u756a\u304f\u3058 TEST",
                "sub_series": "H\u8cde",
                "image_url": "https://assets.1kuji.com/test.jpg",
                "source_url": "https://1kuji.com/products/test",
            }
        ],
    }


class ImportConfirmedIchibanVariantLineupSplitsPublicTest(unittest.TestCase):
    def test_skips_unconfirmed_items(self) -> None:
        catalog = _catalog()
        queue = {"items": [{"manual_confirmed": False, "source_catalog_index": 10}]}

        report = import_splits(catalog, queue, write=True)

        self.assertEqual(report["summary"]["applied_items"], 0)
        self.assertEqual(report["skipped"][0]["reason"], "manual_confirmed_false")
        self.assertEqual(len(catalog["items"]), 1)

    def test_splits_confirmed_variants_and_refreshes_meta(self) -> None:
        catalog = _catalog()
        queue = {
            "items": [
                {
                    "manual_confirmed": True,
                    "source_catalog_index": 10,
                    "source_url": "https://1kuji.com/products/test",
                    "expected_variant_count": 3,
                    "representative_image_ok": True,
                    "variants": [
                        {"variant_name": "\u30c7\u30b6\u30a4\u30f3A", "character_name": "\u30ad\u30e3\u30e9A"},
                        {"variant_name": "\u30c7\u30b6\u30a4\u30f3B", "character_name": "\u30ad\u30e3\u30e9B"},
                        {"variant_name": "\u30c7\u30b6\u30a4\u30f3C", "character_name": "\u30ad\u30e3\u30e9C"},
                    ],
                }
            ]
        }

        report = import_splits(catalog, queue, write=True)

        self.assertEqual(report["summary"]["applied_items"], 1)
        self.assertEqual(report["summary"]["created_or_updated_rows"], 3)
        self.assertEqual(len(catalog["items"]), 3)
        self.assertEqual(catalog["items"][0]["catalog_index"], 10)
        self.assertEqual(catalog["items"][1]["catalog_index"], 11)
        self.assertEqual(catalog["items"][2]["catalog_index"], 12)
        self.assertEqual(
            catalog["items"][0]["name_ko"],
            "\u4e00\u756a\u304f\u3058 TEST / H\u8cde / \u30c7\u30b6\u30a4\u30f3A / \u30ad\u30e3\u30e9A",
        )
        self.assertEqual(catalog["meta"]["row_count"], 3)
        self.assertEqual(catalog["total_items"], 3)

    def test_allows_same_variant_name_when_character_names_differ(self) -> None:
        catalog = _catalog()
        queue = {
            "items": [
                {
                    "manual_confirmed": True,
                    "source_catalog_index": 10,
                    "expected_variant_count": 2,
                    "representative_image_ok": True,
                    "variants": [
                        {"variant_name": "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9", "character_name": "\u30ad\u30e3\u30e9A"},
                        {"variant_name": "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9", "character_name": "\u30ad\u30e3\u30e9B"},
                    ],
                }
            ]
        }

        report = import_splits(catalog, queue, write=True)

        self.assertEqual(report["summary"]["applied_items"], 1)
        self.assertEqual(
            catalog["items"][0]["name_ko"],
            "\u4e00\u756a\u304f\u3058 TEST / H\u8cde / \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 / \u30ad\u30e3\u30e9A",
        )
        self.assertEqual(
            catalog["items"][1]["name_ko"],
            "\u4e00\u756a\u304f\u3058 TEST / H\u8cde / \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 / \u30ad\u30e3\u30e9B",
        )

    def test_rejects_duplicate_variant_name_character_pairs(self) -> None:
        catalog = _catalog()
        queue = {
            "items": [
                {
                    "manual_confirmed": True,
                    "source_catalog_index": 10,
                    "expected_variant_count": 2,
                    "representative_image_ok": True,
                    "variants": [
                        {"variant_name": "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9", "character_name": "\u30ad\u30e3\u30e9A"},
                        {"variant_name": "\u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9", "character_name": "\u30ad\u30e3\u30e9A"},
                    ],
                }
            ]
        }

        report = import_splits(catalog, queue, write=True)

        self.assertEqual(report["summary"]["applied_items"], 0)
        self.assertEqual(report["skipped"][0]["reason"], "duplicate_variant_name_character_pair")

    def test_requires_all_variant_images_unless_representative_image_is_confirmed(self) -> None:
        catalog = _catalog()
        queue = {
            "items": [
                {
                    "manual_confirmed": True,
                    "source_catalog_index": 10,
                    "expected_variant_count": 1,
                    "representative_image_ok": False,
                    "variants": [{"variant_name": "\u30c7\u30b6\u30a4\u30f3A", "character_name": "\u30ad\u30e3\u30e9A"}],
                }
            ]
        }

        report = import_splits(catalog, queue, write=True)

        self.assertEqual(report["summary"]["applied_items"], 0)
        self.assertEqual(report["skipped"][0]["reason"], "variant_image_missing_without_representative_image_ok")


if __name__ == "__main__":
    unittest.main()
