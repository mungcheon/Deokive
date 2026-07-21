from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_image_attachment_rows import import_rows


SOURCE = "https://fanding.kr/@stellive/shop/123"
IMAGE = "https://cdn.example.test/products/stellive-badge.jpg"


def _row(**overrides):
    row = {
        "catalog_index": 0,
        "name_ko": "스텔라이브 테스트 뱃지",
        "source_store": "Stellive Store",
        "source_url": "https://fanding.kr/@stellive/shop",
        "image_url": "",
    }
    row.update(overrides)
    return row


def _item(**overrides):
    item = {
        "manual_confirmed": True,
        "row_index": 0,
        "field": "image_url",
        "manual_value": IMAGE,
        "candidate_source_url": SOURCE,
        "source_store": "Stellive Store",
        "name_ko": "스텔라이브 테스트 뱃지",
    }
    item.update(overrides)
    return item


class ImportConfirmedImageAttachmentRowsTest(unittest.TestCase):
    def test_updates_image_and_replaces_generic_source_url(self) -> None:
        result = import_rows({"items": [_item()]}, [_row()])

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["seed_rows"][0]["source_url"], SOURCE)
        self.assertEqual(result["seed_rows"][0]["image_url"], IMAGE)

    def test_requires_manual_confirmation(self) -> None:
        result = import_rows({"items": [_item(manual_confirmed=False)]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_rejects_missing_candidate_source_url(self) -> None:
        result = import_rows({"items": [_item(candidate_source_url="", evidence_url="")]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "candidate_source_url_required")

    def test_rejects_generic_image_url_without_representative_flag(self) -> None:
        result = import_rows({"items": [_item(manual_value="https://cdn.example.test/og-image.jpg")]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "unsafe_source_image_pair")

    def test_rejects_existing_specific_source_conflict(self) -> None:
        result = import_rows(
            {"items": [_item(candidate_source_url="https://fanding.kr/@stellive/shop/456")]},
            [_row(source_url=SOURCE)],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "existing_source_url_conflict")

    def test_rejects_existing_image_conflict(self) -> None:
        result = import_rows({"items": [_item()]}, [_row(image_url="https://cdn.example.test/products/old.jpg")])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "existing_image_url_conflict")

    def test_rejects_row_identity_mismatch(self) -> None:
        result = import_rows({"items": [_item(name_ko="다른 상품")]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "row_index_identity_mismatch")


if __name__ == "__main__":
    unittest.main()
