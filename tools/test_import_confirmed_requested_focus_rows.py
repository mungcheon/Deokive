from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_requested_focus_rows import import_rows


SOURCE = "https://www.animate-onlineshop.jp/products/detail.php?product_id=123"


def _row(**overrides):
    row = {
        "catalog_index": 0,
        "name_ko": "단간론파 테스트 굿즈",
        "name_ja": "",
        "source_store": "애니메이트",
        "source_url": "",
        "image_url": "",
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
        "evidence_url": SOURCE,
        "candidate_source_url": SOURCE,
        "source_store": "애니메이트",
        "name_ko": "단간론파 테스트 굿즈",
        "topic_id": "danganronpa",
    }
    item.update(overrides)
    return item


class ImportConfirmedRequestedFocusRowsTest(unittest.TestCase):
    def test_updates_confirmed_source_url(self) -> None:
        result = import_rows({"items": [_item("source_url", SOURCE)]}, [_row()])

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["seed_rows"][0]["source_url"], SOURCE)

    def test_updates_confirmed_release_date(self) -> None:
        result = import_rows({"items": [_item("release_date", "2026-07")]}, [_row()])

        self.assertEqual(result["seed_rows"][0]["release_date"], "2026-07")

    def test_updates_confirmed_price(self) -> None:
        result = import_rows({"items": [_item("official_price_jpy", "880")]}, [_row()])

        self.assertEqual(result["seed_rows"][0]["official_price_jpy"], 880)

    def test_updates_confirmed_name_ja_without_evidence_requirement(self) -> None:
        result = import_rows({"items": [_item("name_ja", "ダンガンロンパ テストグッズ", evidence_url="", candidate_source_url="")]}, [_row()])

        self.assertEqual(result["seed_rows"][0]["name_ja"], "ダンガンロンパ テストグッズ")

    def test_requires_manual_confirmation(self) -> None:
        result = import_rows({"items": [_item("source_url", SOURCE, manual_confirmed=False)]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_rejects_generic_source_url(self) -> None:
        result = import_rows({"items": [_item("source_url", "https://www.animate-onlineshop.jp/search?q=test")]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "generic_source_url")

    def test_requires_evidence_for_metadata_fields(self) -> None:
        result = import_rows({"items": [_item("official_price_jpy", "880", evidence_url="", candidate_source_url="")]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "evidence_url_required")

    def test_rejects_existing_conflict_by_default(self) -> None:
        result = import_rows({"items": [_item("official_price_jpy", "880")]}, [_row(official_price_jpy=990)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "existing_field_conflict")

    def test_can_overwrite_existing_conflict_when_enabled(self) -> None:
        result = import_rows(
            {"items": [_item("official_price_jpy", "880")]},
            [_row(official_price_jpy=990)],
            allow_existing_overwrite=True,
        )

        self.assertEqual(result["seed_rows"][0]["official_price_jpy"], 880)


if __name__ == "__main__":
    unittest.main()
