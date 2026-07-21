from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_source_discovery_rows import import_rows


SOURCE = "https://www.goodsmile.info/ja/product/12345"
IMAGE = "https://images.goodsmile.info/products/12345/main.jpg"


def _row(**overrides):
    row = {
        "catalog_index": 0,
        "name_ko": "POP UP PARADE 테스트",
        "name_ja": "POP UP PARADE テスト",
        "source_store": "굿스마일컴퍼니",
        "source_url": "",
        "image_url": "",
    }
    row.update(overrides)
    return row


def _item(**overrides):
    item = {
        "manual_confirmed": True,
        "row_index": 0,
        "field": "source_url",
        "manual_value": SOURCE,
        "image_url": IMAGE,
        "allowed_source_domains": ["www.goodsmile.info"],
        "source_store": "굿스마일컴퍼니",
        "name_ko": "POP UP PARADE 테스트",
    }
    item.update(overrides)
    return item


class ImportConfirmedSourceDiscoveryRowsTest(unittest.TestCase):
    def test_updates_confirmed_product_source_and_optional_image(self) -> None:
        result = import_rows({"items": [_item()]}, [_row()])

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["seed_rows"][0]["source_url"], SOURCE)
        self.assertEqual(result["seed_rows"][0]["image_url"], IMAGE)

    def test_requires_manual_confirmation(self) -> None:
        result = import_rows({"items": [_item(manual_confirmed=False)]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_rejects_search_url_as_source(self) -> None:
        result = import_rows(
            {"items": [_item(manual_value="https://www.goodsmile.info/ja/products/search?query=test")]},
            [_row()],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "exact_product_source_url_required")

    def test_rejects_source_domain_not_allowed(self) -> None:
        result = import_rows({"items": [_item(manual_value="https://example.test/product/12345")]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "source_domain_not_allowed")

    def test_rejects_existing_source_conflict(self) -> None:
        result = import_rows({"items": [_item()]}, [_row(source_url="https://www.goodsmile.info/ja/product/99999")])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "existing_source_url_conflict")

    def test_rejects_existing_image_conflict(self) -> None:
        result = import_rows({"items": [_item()]}, [_row(image_url="https://images.goodsmile.info/products/old.jpg")])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "existing_image_url_conflict")

    def test_rejects_row_identity_mismatch(self) -> None:
        result = import_rows({"items": [_item(name_ko="다른 이름")]}, [_row()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "row_index_identity_mismatch")


if __name__ == "__main__":
    unittest.main()
