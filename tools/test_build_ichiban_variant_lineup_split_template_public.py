from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_ichiban_variant_lineup_split_template_public import build_template


class BuildIchibanVariantLineupSplitTemplatePublicTest(unittest.TestCase):
    def test_builds_manual_confirmation_template_from_matched_probe_rows(self) -> None:
        probe = {
            "candidates": [
                {
                    "catalog_index": 10,
                    "status": "matched",
                    "source_url": "https://1kuji.com/products/test",
                    "official_name": "H\u8cde \u30b9\u30c6\u30c3\u30ab\u30fc\u30a2\u30bd\u30fc\u30c8",
                    "official_detail": "\u25a0\u51683\u7a2e",
                    "expected_variant_count": 3,
                    "choice_policy": "blind",
                },
                {
                    "catalog_index": 11,
                    "status": "official_item_not_matched",
                    "source_url": "https://1kuji.com/products/special",
                },
            ]
        }

        template = build_template(probe)

        self.assertEqual(template["summary"]["template_rows"], 1)
        item = template["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertFalse(item["representative_image_ok"])
        self.assertEqual(item["source_catalog_index"], 10)
        self.assertEqual(item["expected_variant_count"], 3)
        self.assertEqual(len(item["variants"]), 3)
        self.assertEqual(item["variants"][0]["character_name"], "\uae30\ud0c0")


if __name__ == "__main__":
    unittest.main()
