from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_public_catalog_category_corrections as corrections


def _row(name: str, *, category: str = "아크릴 스탠드") -> dict:
    return {
        "catalog_index": 1,
        "name_ko": name,
        "name_ja": name,
        "category": category,
        "source_store": "애니메이트",
    }


class PublicCatalogCategoryCorrectionTests(unittest.TestCase):
    def test_corrects_acrylic_keyholder_and_mascot(self) -> None:
        rows = [
            _row("葬送のフリーレン トレーディングアクリルキーホルダー"),
            _row("呪術廻戦 デフォルメアクリルマスコット"),
        ]

        result = corrections.apply_corrections(rows)

        self.assertEqual(result["updated_rows"], 2)
        self.assertEqual(rows[0]["category"], "아크릴 키링")
        self.assertEqual(rows[1]["category"], "마스코트")

    def test_keeps_real_acrylic_stands(self) -> None:
        rows = [_row("推しの子 アクリルスタンド 星野アイ")]

        result = corrections.apply_corrections(rows)

        self.assertEqual(result["updated_rows"], 0)
        self.assertEqual(rows[0]["category"], "아크릴 스탠드")

    def test_does_not_rewrite_non_source_categories(self) -> None:
        rows = [_row("葬送のフリーレン トレーディングアクリルキーホルダー", category="키링")]

        result = corrections.apply_corrections(rows)

        self.assertEqual(result["updated_rows"], 0)
        self.assertEqual(rows[0]["category"], "키링")


if __name__ == "__main__":
    unittest.main()
