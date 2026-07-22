from __future__ import annotations

import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_ichiban_metadata_rows import import_rows
from import_confirmed_ichiban_metadata_rows import _write_seed_payload


URL = "https://1kuji.com/products/test-kuji"


def _row(catalog_index: int, **overrides):
    row = {
        "catalog_index": catalog_index,
        "name_ko": f"이치방쿠지 테스트 {catalog_index}",
        "source_url": URL,
        "release_date": "",
        "official_price_jpy": "",
    }
    row.update(overrides)
    return row


def _item(field: str, manual_value, **overrides):
    item = {
        "manual_confirmed": True,
        "official_evidence_confirmed": True,
        "field": field,
        "manual_value": manual_value,
        "evidence_url": URL,
        "campaign_slug": "test-kuji",
        "campaign_title": "一番くじ テスト",
        "target_catalog_item_rows": 2,
    }
    item.update(overrides)
    return item


class ImportConfirmedIchibanMetadataRowsTest(unittest.TestCase):
    def test_updates_all_rows_for_confirmed_campaign_release_date(self) -> None:
        result = import_rows({"items": [_item("release_date", "2026-07-22")]}, [_row(1), _row(2)])

        self.assertEqual(len(result["updated"]), 2)
        self.assertEqual(result["seed_rows"][0]["release_date"], "2026-07-22")
        self.assertEqual(result["seed_rows"][1]["release_date"], "2026-07-22")

    def test_updates_all_rows_for_confirmed_campaign_price(self) -> None:
        result = import_rows({"items": [_item("official_price_jpy", "850")]}, [_row(1), _row(2)])

        self.assertEqual(len(result["updated"]), 2)
        self.assertEqual(result["seed_rows"][0]["official_price_jpy"], 850)

    def test_requires_manual_confirmation(self) -> None:
        result = import_rows({"items": [_item("release_date", "2026-07", manual_confirmed=False)]}, [_row(1), _row(2)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_requires_official_evidence_confirmation(self) -> None:
        result = import_rows(
            {"items": [_item("release_date", "2026-07", official_evidence_confirmed=False)]},
            [_row(1), _row(2)],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "official_evidence_not_confirmed")

    def test_rejects_non_1kuji_evidence_url(self) -> None:
        result = import_rows(
            {"items": [_item("official_price_jpy", "850", evidence_url="https://example.test/products/test-kuji")]},
            [_row(1), _row(2)],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "official_1kuji_evidence_url_required")

    def test_rejects_count_mismatch(self) -> None:
        result = import_rows({"items": [_item("release_date", "2026-07", target_catalog_item_rows=3)]}, [_row(1), _row(2)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "target_catalog_item_rows_mismatch")

    def test_rejects_existing_value_conflict_by_default(self) -> None:
        result = import_rows({"items": [_item("release_date", "2026-07")]}, [_row(1, release_date="2026-06"), _row(2)])

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["skipped"][0]["reason"], "existing_field_conflict")

    def test_can_overwrite_existing_value_when_enabled(self) -> None:
        result = import_rows(
            {"items": [_item("release_date", "2026-07")]},
            [_row(1, release_date="2026-06"), _row(2)],
            allow_existing_overwrite=True,
        )

        self.assertEqual(len(result["updated"]), 2)
        self.assertEqual(result["seed_rows"][0]["release_date"], "2026-07")

    def test_write_seed_payload_preserves_public_catalog_shape_and_updates_meta(self) -> None:
        payload = {
            "meta": {
                "generated_at": "2026-01-01T00:00:00Z",
                "row_count": 1,
                "total_items": 1,
                "fields": ["catalog_index", "release_date", "official_price_jpy"],
                "missing": {},
            },
            "items": [_row(1, release_date="", official_price_jpy=850)],
        }
        result = import_rows({"items": [_item("release_date", "2026-07-22", target_catalog_item_rows=1)]}, payload["items"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            _write_seed_payload(path, payload, result["seed_rows"])
            written = json.loads(path.read_text(encoding="utf-8"))

        self.assertIsInstance(written, dict)
        self.assertEqual(len(written["items"]), 1)
        self.assertEqual(written["items"][0]["release_date"], "2026-07-22")
        self.assertEqual(written["meta"]["row_count"], 1)
        self.assertEqual(written["meta"]["total_items"], 1)
        self.assertEqual(written["meta"]["missing"]["release_date"], 0)
        self.assertEqual(written["meta"]["missing"]["official_price_jpy"], 0)


if __name__ == "__main__":
    unittest.main()
