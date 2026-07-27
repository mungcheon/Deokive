from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_agent_goods_intake as target


ROOT = Path(__file__).resolve().parents[1]


class AgentGoodsIntakeValidationTests(unittest.TestCase):
    def test_template_payload_is_valid(self) -> None:
        path = ROOT / "data" / "intake" / "templates" / "agent_goods_intake.template.json"
        payload = target.load_json(path)

        errors, summary = target.validate_payload(path, payload)

        self.assertEqual([], errors)
        self.assertEqual(1, summary["items"])

    def test_official_price_requires_currency(self) -> None:
        payload = {
            "schema_version": 1,
            "agent": {
                "name": "agent",
                "run_id": "run",
                "collected_at": "2026-07-27T00:00:00+09:00",
            },
            "items": [
                {
                    "external_id": "sku-1",
                    "display_name": "Sample",
                    "category": "figure",
                    "series_name": "Sample Series",
                    "source_store": "Official Store",
                    "source_url": "https://example.com/product",
                    "official_price": 1200,
                    "confidence": "confirmed",
                }
            ],
        }

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(
            any("official_price_currency: required" in error for error in errors)
        )

    def test_jpy_price_alias_must_match_explicit_jpy_price(self) -> None:
        payload = {
            "schema_version": 1,
            "agent": {
                "name": "agent",
                "run_id": "run",
                "collected_at": "2026-07-27T00:00:00+09:00",
            },
            "items": [
                {
                    "external_id": "sku-1",
                    "display_name": "Sample",
                    "category": "figure",
                    "series_name": "Sample Series",
                    "source_store": "Official Store",
                    "source_url": "https://example.com/product",
                    "official_price": 1200,
                    "official_price_currency": "JPY",
                    "official_price_jpy": 1500,
                    "confidence": "confirmed",
                }
            ],
        }

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(
            any("official_price_jpy: must match official_price" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
