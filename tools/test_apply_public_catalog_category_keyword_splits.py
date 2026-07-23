from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_public_catalog_category_keyword_splits as splitter


def _row(name_ja: str, *, category: str = "\uad7f\uc988", affiliation: str = "\uc8fc\uc220\ud68c\uc804") -> dict:
    return {
        "catalog_index": 1,
        "name_ko": f"\uc0d8\ud50c - {name_ja}",
        "name_ja": name_ja,
        "category": category,
        "affiliation": affiliation,
        "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
    }


class PublicCatalogCategoryKeywordSplitTests(unittest.TestCase):
    def test_splits_animation_goods_by_product_keywords(self) -> None:
        rows = [
            _row("F-1\u8cde SOFVIC\u3061\u3085 \u7dd1\u8c37\u51fa\u4e45"),
            _row("J\u8cde \u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7"),
            _row("G\u8cde \u9b54\u5c0e\u66f8\u98a8\u30ce\u30fc\u30c8"),
            _row("A\u8cde \u864e\u6756\u60a0\u4ec1\u30d3\u30b8\u30e5\u30a2\u30eb\u30af\u30ed\u30b9"),
            _row("E\u8cde \u30af\u30ea\u30a2\u30dc\u30c8\u30eb"),
        ]

        result = splitter.apply_splits(rows)

        self.assertEqual(result["updated_rows"], 5)
        self.assertEqual([row["category"] for row in rows], [
            "\ud53c\uaddc\uc5b4",
            "\ud0a4\ub9c1",
            "\ubb38\uad6c",
            "\ud0dc\ud53c\uc2a4\ud2b8\ub9ac",
            "\uc0dd\ud65c\uc7a1\ud654",
        ])

    def test_does_not_touch_non_animation_rows_by_default(self) -> None:
        rows = [
            _row(
                "F-1\u8cde SOFVIC\u3061\u3085 \u7dd1\u8c37\u51fa\u4e45",
                affiliation="\uce58\uc774\uce74\uc640",
            )
        ]
        rows[0]["source_store"] = "\uce58\uc774\uce74\uc640 \ub9c8\ucf13"

        result = splitter.apply_splits(rows)

        self.assertEqual(result["updated_rows"], 0)
        self.assertEqual(rows[0]["category"], "\uad7f\uc988")

    def test_keeps_non_matching_goods_for_manual_review(self) -> None:
        rows = [_row("G\u8cde \u30af\u30ea\u30a2\u30a2\u30a4\u30c6\u30e0\u30a2\u30bd\u30fc\u30c8")]

        result = splitter.apply_splits(rows)

        self.assertEqual(result["updated_rows"], 0)
        self.assertEqual(rows[0]["category"], "\uad7f\uc988")


if __name__ == "__main__":
    unittest.main()
