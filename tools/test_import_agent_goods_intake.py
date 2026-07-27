from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_agent_goods_intake as target


def intake_payload(*items: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "agent": {
            "name": "agent",
            "run_id": "run",
            "collected_at": "2026-07-27T00:00:00+09:00",
        },
        "items": list(items),
    }


class ImportAgentGoodsIntakeTests(unittest.TestCase):
    def test_import_adds_validated_item_with_jpy_price(self) -> None:
        catalog = {
            "meta": {"generated_at": "2026-07-27T00:00:00Z"},
            "items": [
                {
                    "catalog_index": 0,
                    "name_ko": "Existing",
                    "category": "figure",
                    "character_name": "A",
                    "affiliation": "Series",
                    "series_name": "Series",
                    "sub_series": "",
                    "source_store": "Official",
                    "source_url": "https://example.com/existing",
                    "barcode": "11111111",
                }
            ],
            "total_items": 1,
        }
        payload = intake_payload(
            {
                "external_id": "sku-2",
                "display_name": "New Figure",
                "name_ja": "新しいフィギュア",
                "category": "figure",
                "series_name": "Sample Series",
                "character_name": "Character",
                "source_store": "Official",
                "source_url": "https://example.com/new",
                "image_url": "https://example.com/new.jpg",
                "official_price": 1800,
                "official_price_currency": "JPY",
                "official_price_jpy": 1800,
                "confidence": "confirmed",
            }
        )

        result = target.import_payloads(catalog, [(Path("intake.json"), payload)])

        self.assertEqual(1, len(result["added_rows"]))
        added = result["added_rows"][0]
        self.assertEqual(1, added["catalog_index"])
        self.assertEqual("New Figure", added["name_ko"])
        self.assertEqual(1800, added["official_price_jpy"])
        self.assertIsNone(added["official_price_krw"])
        self.assertEqual(2, result["catalog"]["total_items"])

    def test_import_skips_source_url_duplicate(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 0,
                    "name_ko": "Existing",
                    "category": "figure",
                    "character_name": "A",
                    "affiliation": "Series",
                    "series_name": "Series",
                    "sub_series": "",
                    "source_store": "Official",
                    "source_url": "https://example.com/existing",
                }
            ]
        }
        payload = intake_payload(
            {
                "external_id": "sku-duplicate",
                "display_name": "Existing Reimport",
                "category": "figure",
                "series_name": "Series",
                "source_store": "Official",
                "source_url": "https://example.com/existing/",
                "confidence": "confirmed",
            }
        )

        result = target.import_payloads(catalog, [(Path("intake.json"), payload)])

        self.assertEqual([], result["added_rows"])
        self.assertEqual("source_url_duplicate", result["skipped_rows"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
