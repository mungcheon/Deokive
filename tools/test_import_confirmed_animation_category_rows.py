from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_animation_category_rows import import_rows


def _row(category: str, **overrides):
    row = {
        "catalog_index": 1,
        "name_ko": "테스트 굿즈",
        "name_ja": "テストグッズ",
        "category": category,
        "series_name": "테스트",
    }
    row.update(overrides)
    return row


def _mapping(**overrides):
    item = {
        "manual_confirmed": True,
        "source_category": "아크릴",
        "target_category": "아크릴 스탠드",
        "target_family": "acrylic",
        "folder_name": "아크릴 스탠드",
        "folder_color_hex": "0xFF7DB7FF",
        "folder_icon_key": "view_carousel",
        "affected_catalog_rows": 2,
    }
    item.update(overrides)
    return item


class ImportConfirmedAnimationCategoryRowsTest(unittest.TestCase):
    def test_updates_all_rows_for_confirmed_category_mapping(self) -> None:
        result = import_rows(
            {"items": [_mapping()]},
            [_row("아크릴", catalog_index=1), _row("아크릴", catalog_index=2), _row("인형", catalog_index=3)],
        )

        self.assertEqual(len(result["updated"]), 2)
        self.assertEqual(result["seed_rows"][0]["category"], "아크릴 스탠드")
        self.assertEqual(result["seed_rows"][1]["category"], "아크릴 스탠드")
        self.assertEqual(result["seed_rows"][2]["category"], "인형")
        self.assertEqual(result["updated"][0]["folder_icon_key"], "view_carousel")

    def test_skips_unconfirmed_mapping(self) -> None:
        result = import_rows({"items": [_mapping(manual_confirmed=False)]}, [_row("아크릴"), _row("아크릴")])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_rejects_count_mismatch_by_default(self) -> None:
        result = import_rows({"items": [_mapping(affected_catalog_rows=3)]}, [_row("아크릴"), _row("아크릴")])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "affected_catalog_rows_mismatch")

    def test_can_allow_count_mismatch_explicitly(self) -> None:
        result = import_rows(
            {"items": [_mapping(affected_catalog_rows=3)]},
            [_row("아크릴"), _row("아크릴")],
            allow_count_mismatch=True,
        )

        self.assertEqual(len(result["updated"]), 2)

    def test_rejects_duplicate_source_mapping(self) -> None:
        result = import_rows(
            {"items": [_mapping(), _mapping(target_category="아크릴 키링")]},
            [_row("아크릴"), _row("아크릴")],
        )

        self.assertEqual(len(result["updated"]), 2)
        self.assertEqual(result["skipped"][0]["reason"], "duplicate_source_mapping")

    def test_rejects_url_like_target_category(self) -> None:
        result = import_rows(
            {"items": [_mapping(target_category="https://example.com/category")]},
            [_row("아크릴"), _row("아크릴")],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "category_contains_url")


if __name__ == "__main__":
    unittest.main()
