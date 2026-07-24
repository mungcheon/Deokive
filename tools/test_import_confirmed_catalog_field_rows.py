from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_catalog_field_rows import import_rows


def _seed_row(**overrides):
    row = {
        "source_store": "FuRyu",
        "name_ko": "Test Goods",
        "name_ja": "Test Goods JP",
        "source_url": "",
        "image_url": "",
        "release_date": "",
        "barcode": "",
        "official_price_jpy": "",
    }
    row.update(overrides)
    return row


def _item(field, manual_value, **overrides):
    item = {
        "manual_confirmed": True,
        "row_index": 0,
        "field": field,
        "manual_value": manual_value,
        "evidence_url": "https://furyuprize.com/item/12345/",
        "source_store": "FuRyu",
        "name_ko": "Test Goods",
        "name_ja": "Test Goods JP",
        "category": "",
        "affiliation": "",
    }
    item.update(overrides)
    return item


class ConfirmedCatalogFieldImportTests(unittest.TestCase):
    def test_rejects_impossible_calendar_release_dates(self):
        result = import_rows(
            {"items": [_item("release_date", "2026-99-99")]},
            [_seed_row()],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "invalid_release_date")

    def test_accepts_valid_month_release_date_from_exact_store_evidence(self):
        result = import_rows(
            {"items": [_item("release_date", "2026-07")]},
            [_seed_row()],
        )

        self.assertEqual(result["updated"][0]["field"], "release_date")
        self.assertEqual(result["seed_rows"][0]["release_date"], "2026-07")

    def test_rejects_exact_product_url_from_wrong_store_domain(self):
        result = import_rows(
            {
                "items": [
                    _item(
                        "source_url",
                        "https://www.animate-onlineshop.jp/products/detail.php?product_id=123",
                        evidence_url="https://www.animate-onlineshop.jp/products/detail.php?product_id=123",
                    )
                ]
            },
            [_seed_row()],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "source_store_mismatch")

    def test_rejects_barcode_without_exact_evidence_url(self):
        result = import_rows(
            {"items": [_item("barcode", "4901234567890", evidence_url="https://furyuprize.com/")]},
            [_seed_row()],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "exact_evidence_url_required")

    def test_rejects_existing_non_generic_field_conflicts(self):
        result = import_rows(
            {"items": [_item("barcode", "4901234567890")]},
            [_seed_row(barcode="4900000000000")],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "existing_field_conflict")

    def test_allows_existing_field_overwrite_when_explicitly_enabled(self):
        result = import_rows(
            {"items": [_item("official_price_jpy", "1980")]},
            [_seed_row(official_price_jpy=2200)],
            allow_existing_overwrite=True,
        )

        self.assertEqual(result["updated"][0]["field"], "official_price_jpy")
        self.assertEqual(result["seed_rows"][0]["official_price_jpy"], 1980)

    def test_accepts_image_url_with_candidate_source_url_evidence(self):
        result = import_rows(
            {
                "items": [
                    _item(
                        "image_url",
                        "https://cdn.example.test/products/test-goods.jpg",
                        evidence_url="",
                        candidate_source_url="https://furyuprize.com/item/12345/",
                    )
                ]
            },
            [_seed_row()],
        )

        self.assertEqual(result["updated"][0]["field"], "image_url")
        self.assertEqual(result["seed_rows"][0]["image_url"], "https://cdn.example.test/products/test-goods.jpg")

    def test_accepts_manually_confirmed_representative_image(self):
        result = import_rows(
            {
                "items": [
                    _item(
                        "image_url",
                        "https://example.com/og-image.jpg",
                        evidence_url="https://example.com/collab/",
                        representative_image=True,
                        source_store="Collab Store",
                    )
                ]
            },
            [_seed_row(source_store="Collab Store", source_url="https://example.com/collab/")],
        )

        self.assertEqual(result["updated"][0]["field"], "image_url")
        self.assertEqual(result["seed_rows"][0]["image_url"], "https://example.com/og-image.jpg")

    def test_rejects_generic_image_without_representative_flag(self):
        result = import_rows(
            {
                "items": [
                    _item(
                        "image_url",
                        "https://example.com/og-image.jpg",
                        evidence_url="https://example.com/collab/",
                        source_store="Collab Store",
                    )
                ]
            },
            [_seed_row(source_store="Collab Store", source_url="https://example.com/collab/")],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "generic_image_url")

    def test_accepts_ichiban_sub_series_with_exact_campaign_evidence(self):
        source_url = "https://1kuji.com/products/test-kuji"
        result = import_rows(
            {
                "items": [
                    _item(
                        "sub_series",
                        "A賞",
                        evidence_url=source_url,
                        source_store="이치방쿠지",
                        name_ko="Ichiban Prize",
                        name_ja="A賞 フィギュア",
                    )
                ]
            },
            [
                _seed_row(
                    source_store="이치방쿠지",
                    name_ko="Ichiban Prize",
                    name_ja="A賞 フィギュア",
                    source_url=source_url,
                    sub_series="",
                )
            ],
        )

        self.assertEqual(result["updated"][0]["field"], "sub_series")
        self.assertEqual(result["seed_rows"][0]["sub_series"], "A賞")

    def test_rejects_ichiban_sub_series_with_wrong_evidence_url(self):
        result = import_rows(
            {
                "items": [
                    _item(
                        "sub_series",
                        "A賞",
                        evidence_url="https://1kuji.com/products/other-kuji",
                        source_store="이치방쿠지",
                        name_ko="Ichiban Prize",
                        name_ja="A賞 フィギュア",
                    )
                ]
            },
            [
                _seed_row(
                    source_store="이치방쿠지",
                    name_ko="Ichiban Prize",
                    name_ja="A賞 フィギュア",
                    source_url="https://1kuji.com/products/test-kuji",
                    sub_series="",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "evidence_source_mismatch")

    def test_accepts_name_ja_and_character_name_from_exact_evidence(self):
        evidence_url = "https://furyuprize.com/item/12345/"
        result = import_rows(
            {
                "items": [
                    _item("name_ja", "テストグッズ", name_ja="", evidence_url=evidence_url),
                    _item("character_name", "ミク", name_ja="", evidence_url=evidence_url),
                ]
            },
            [_seed_row(name_ja="", character_name="", source_url=evidence_url)],
        )

        self.assertEqual([row["field"] for row in result["updated"]], ["name_ja", "character_name"])
        self.assertEqual(result["seed_rows"][0]["name_ja"], "テストグッズ")
        self.assertEqual(result["seed_rows"][0]["character_name"], "ミク")

    def test_rejects_name_ja_without_exact_evidence(self):
        result = import_rows(
            {
                "items": [
                    _item(
                        "name_ja",
                        "テストグッズ",
                        name_ja="",
                        evidence_url="https://furyuprize.com/",
                    )
                ]
            },
            [_seed_row(name_ja="", source_url="")],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "exact_evidence_url_required")

    def test_rejects_character_name_url_values(self):
        result = import_rows(
            {"items": [_item("character_name", "https://example.com/name", name_ja="")]},
            [_seed_row(name_ja="", character_name="")],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "invalid_character_name")


if __name__ == "__main__":
    unittest.main()
