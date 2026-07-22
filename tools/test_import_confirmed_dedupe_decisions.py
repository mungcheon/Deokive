from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_dedupe_decisions import import_decisions


def _row(catalog_index: int, **overrides):
    row = {
        "catalog_index": catalog_index,
        "name_ko": f"Goods {catalog_index}",
        "is_active": True,
    }
    row.update(overrides)
    return row


def _item(**overrides):
    item = {
        "manual_confirmed": True,
        "decision": "keep_drop_confirmed",
        "key_type": "barcode",
        "key": "123",
        "keep_catalog_index": 10,
        "drop_catalog_indexes": [11],
        "manual_note": "same sellable product",
    }
    item.update(overrides)
    return item


class ImportConfirmedDedupeDecisionsTest(unittest.TestCase):
    def test_deactivates_confirmed_drop_rows_and_keeps_winner(self) -> None:
        result = import_decisions({"items": [_item()]}, [_row(10), _row(11)])

        self.assertEqual(len(result["updated"]), 1)
        self.assertTrue(result["seed_rows"][0]["is_active"])
        self.assertFalse(result["seed_rows"][1]["is_active"])
        self.assertEqual(result["seed_rows"][1]["dedupe_keep_catalog_index"], 10)
        self.assertEqual(result["seed_rows"][1]["dedupe_manual_note"], "same sellable product")

    def test_requires_manual_confirmation(self) -> None:
        result = import_decisions({"items": [_item(manual_confirmed=False)]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_rejects_review_required_decision(self) -> None:
        result = import_decisions({"items": [_item(decision="review_required")]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "unsupported_decision")

    def test_rejects_missing_keep_row(self) -> None:
        result = import_decisions({"items": [_item(keep_catalog_index=99)]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "keep_catalog_index_not_found")

    def test_rejects_keep_in_drop_list(self) -> None:
        result = import_decisions({"items": [_item(drop_catalog_indexes=[10, 11])]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "keep_catalog_index_in_drop_list")

    def test_uses_row_position_when_catalog_index_is_missing(self) -> None:
        result = import_decisions(
            {"items": [_item(keep_catalog_index=0, drop_catalog_indexes=[1])]},
            [{"name_ko": "Keep"}, {"name_ko": "Drop"}],
        )

        self.assertEqual(len(result["updated"]), 1)
        self.assertFalse(result["seed_rows"][1]["is_active"])


if __name__ == "__main__":
    unittest.main()
