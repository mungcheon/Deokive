from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_metadata_rows import import_rows


def _row(**overrides):
    row = {
        "catalog_index": 0,
        "name_ko": "테스트 굿즈",
        "name_ja": "",
        "source_store": "테스트 스토어",
        "release_date": "",
        "official_price_jpy": "",
    }
    row.update(overrides)
    return row


def _item(field: str, manual_value, **overrides):
    item = {
        "manual_confirmed": True,
        "row_index": 0,
        "field": field,
        "manual_value": manual_value,
        "source_store": "테스트 스토어",
        "name_ko": "테스트 굿즈",
    }
    item.update(overrides)
    return item


class ImportConfirmedMetadataRowsTest(unittest.TestCase):
    def test_updates_release_date(self) -> None:
        result = import_rows({"items": [_item("release_date", "2026-07")]}, [_row()])

        self.assertEqual(result["seed_rows"][0]["release_date"], "2026-07")

    def test_updates_price(self) -> None:
        result = import_rows({"items": [_item("official_price_jpy", "1,320")]}, [_row()])

        self.assertEqual(result["seed_rows"][0]["official_price_jpy"], 1320)

    def test_updates_name_ja(self) -> None:
        result = import_rows({"items": [_item("name_ja", "テスト グッズ")]}, [_row()])

        self.assertEqual(result["seed_rows"][0]["name_ja"], "テスト グッズ")

    def test_requires_manual_confirmation(self) -> None:
        result = import_rows({"items": [_item("release_date", "2026-07", manual_confirmed=False)]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_rejects_invalid_release_date(self) -> None:
        result = import_rows({"items": [_item("release_date", "2026-99-99")]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "invalid_release_date")

    def test_rejects_unsupported_field(self) -> None:
        result = import_rows({"items": [_item("barcode", "4901234567890")]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "unsupported_field")

    def test_rejects_existing_conflict_by_default(self) -> None:
        result = import_rows({"items": [_item("official_price_jpy", "1320")]}, [_row(official_price_jpy=990)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "existing_field_conflict")

    def test_can_overwrite_existing_conflict_when_enabled(self) -> None:
        result = import_rows(
            {"items": [_item("official_price_jpy", "1320")]},
            [_row(official_price_jpy=990)],
            allow_existing_overwrite=True,
        )

        self.assertEqual(result["seed_rows"][0]["official_price_jpy"], 1320)


if __name__ == "__main__":
    unittest.main()
