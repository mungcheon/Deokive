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

    def test_splits_remaining_ichiban_animation_goods_keywords(self) -> None:
        rows = [
            _row("F\u8cde \u9285\u50cf\u30aa\u30fc\u30eb\u30de\u30a4\u30c8 MASTERELIVE COLLECTION"),
            _row("\u30e9\u30b9\u30c8\u30ef\u30f3\u8cde \u7f36\u30b1\u30fc\u30b9\u5165\u308a\u30b9\u30da\u30b7\u30e3\u30eb\u30d0\u30c3\u30b8\u30bb\u30c3\u30c8"),
            _row("F\u8cde \u30e9\u30cf\u3099\u30fc\u30b9\u30c8\u30e9\u30c3\u30d5\u309a"),
            _row("G\u8cde \u30a2\u30af\u30ea\u30c3\u30c4"),
            _row("A\u8cde \u30b9\u30da\u30b7\u30e3\u30eb\u30b7\u30fc\u30f3\u30bb\u30ec\u30af\u30b7\u30e7\u30f3"),
            _row("C\u8cde \u89b3\u5ba2\u5e2d\u5fdc\u63f4\u30bb\u30c3\u30c8"),
            _row("A\u8cde \u30a2\u30eb\u30d0\u30e0\u59d4\u54e1\u4e00\u62bc\u3057\uff011-A\u30a2\u30eb\u30d0\u30e0"),
            _row("G\u8cde \u30af\u30ea\u30a2\u30a2\u30a4\u30c6\u30e0\u30a2\u30bd\u30fc\u30c8"),
        ]

        result = splitter.apply_splits(rows)

        self.assertEqual(result["updated_rows"], 8)
        self.assertEqual(
            [row["category"] for row in rows],
            [
                "\ud53c\uaddc\uc5b4",
                "\uce94\ubc43\uc9c0",
                "\ud0a4\ub9c1",
                "\uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                "\ud0dc\ud53c\uc2a4\ud2b8\ub9ac",
                "\uc751\uc6d0\uc6a9\ud488",
                "\ubb38\uad6c",
                "\uc561\uc138\uc11c\ub9ac",
            ],
        )

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
        rows = [_row("G\u8cde \u30df\u30b9\u30c6\u30ea\u30fc\u30bb\u30c3\u30c8")]

        result = splitter.apply_splits(rows)

        self.assertEqual(result["updated_rows"], 0)
        self.assertEqual(rows[0]["category"], "\uad7f\uc988")


if __name__ == "__main__":
    unittest.main()
