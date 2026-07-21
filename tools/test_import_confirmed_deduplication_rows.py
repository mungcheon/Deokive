from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_deduplication_rows import import_rows


def _row(catalog_index: int, barcode: str = "4901234567890", **overrides):
    row = {
        "catalog_index": catalog_index,
        "name_ko": f"테스트 굿즈 {catalog_index}",
        "category": "피규어",
        "barcode": barcode,
        "source_url": f"https://example.test/products/{catalog_index}",
        "image_url": f"https://example.test/images/{catalog_index}.jpg",
    }
    row.update(overrides)
    return row


def _decision(**overrides):
    item = {
        "manual_confirmed": True,
        "same_sellable_product_confirmed": True,
        "decision": "drop_duplicates",
        "key_type": "barcode",
        "key": "4901234567890",
        "keep_catalog_index": 2,
        "drop_catalog_indexes": [1],
        "manual_note": "same item after image/title review",
    }
    item.update(overrides)
    return item


class ImportConfirmedDeduplicationRowsTest(unittest.TestCase):
    def test_drops_confirmed_duplicate_rows(self) -> None:
        result = import_rows({"items": [_decision()]}, [_row(1), _row(2), _row(3, barcode="1111111111111")])

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["updated"][0]["drop_catalog_index"], 1)
        self.assertEqual([row["catalog_index"] for row in result["seed_rows"]], [2, 3])

    def test_requires_manual_confirmation(self) -> None:
        result = import_rows({"items": [_decision(manual_confirmed=False)]}, [_row(1), _row(2)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_requires_same_sellable_product_confirmation(self) -> None:
        result = import_rows({"items": [_decision(same_sellable_product_confirmed=False)]}, [_row(1), _row(2)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "same_sellable_product_not_confirmed")

    def test_rejects_unsupported_decision(self) -> None:
        result = import_rows({"items": [_decision(decision="review_required")]}, [_row(1), _row(2)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "unsupported_decision")

    def test_rejects_dedupe_key_mismatch(self) -> None:
        result = import_rows({"items": [_decision()]}, [_row(1, barcode="9999999999999"), _row(2)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "dedupe_key_mismatch")

    def test_rejects_keep_in_drop_indexes(self) -> None:
        result = import_rows({"items": [_decision(drop_catalog_indexes=[1, 2])]}, [_row(1), _row(2)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "keep_catalog_index_in_drop_indexes")

    def test_rejects_overlapping_drop_decisions(self) -> None:
        result = import_rows(
            {"items": [_decision(), _decision(keep_catalog_index=3, drop_catalog_indexes=[1])]},
            [_row(1), _row(2), _row(3)],
        )

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["skipped"][0]["reason"], "catalog_index_used_by_prior_decision")


if __name__ == "__main__":
    unittest.main()
