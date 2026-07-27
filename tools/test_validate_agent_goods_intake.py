from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_agent_goods_intake as target


ROOT = Path(__file__).resolve().parents[1]


class AgentGoodsIntakeValidationTests(unittest.TestCase):
    def valid_item(self, **overrides: object) -> dict[str, object]:
        item: dict[str, object] = {
            "external_id": "sku-1",
            "display_name": "Sample",
            "category": "figure",
            "series_name": "Sample Series",
            "source_store": "Official Store",
            "source_url": "https://example.com/product",
            "evidence": [{"url": "https://example.com/product", "type": "official"}],
            "confidence": "confirmed",
        }
        item.update(overrides)
        return item

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
                self.valid_item(official_price=1200)
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
                self.valid_item(
                    official_price=1200,
                    official_price_currency="JPY",
                    official_price_jpy=1500,
                )
            ],
        }

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(
            any("official_price_jpy: must match official_price" in error for error in errors)
        )

    def test_rejects_unknown_fields_so_agents_share_one_shape(self) -> None:
        payload = {
            "schema_version": 1,
            "agent": {
                "name": "agent",
                "run_id": "run",
                "collected_at": "2026-07-27T00:00:00+09:00",
                "extra_agent_field": "nope",
            },
            "items": [
                {
                    "external_id": "sku-1",
                    "display_name": "Sample",
                    "category": "figure",
                    "series_name": "Sample Series",
                    "source_store": "Official Store",
                    "source_url": "https://example.com/product",
                    "confidence": "confirmed",
                    "random_price_hint": 1200,
                    "evidence": [
                        {
                            "url": "https://example.com/product",
                            "type": "official",
                            "extra_evidence_field": "nope",
                        }
                    ],
                }
            ],
            "random_top_level": True,
        }

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("sample.json: unknown field(s): random_top_level" in error for error in errors))
        self.assertTrue(any("agent: unknown field(s): extra_agent_field" in error for error in errors))
        self.assertTrue(any("items[0]: unknown field(s): random_price_hint" in error for error in errors))
        self.assertTrue(
            any("items[0].evidence[0]: unknown field(s): extra_evidence_field" in error for error in errors)
        )

    def test_rejects_non_iso_collected_at(self) -> None:
        payload = {
            "schema_version": 1,
            "agent": {
                "name": "agent",
                "run_id": "run",
                "collected_at": "today",
            },
            "items": [
                {
                    "external_id": "sku-1",
                    "display_name": "Sample",
                    "category": "figure",
                    "series_name": "Sample Series",
                    "source_store": "Official Store",
                    "source_url": "https://example.com/product",
                    "evidence": [{"url": "https://example.com/product", "type": "official"}],
                    "confidence": "confirmed",
                }
            ],
        }

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("agent.collected_at: expected ISO-8601 timestamp" in error for error in errors))

    def test_jpy_currency_requires_explicit_jpy_price(self) -> None:
        payload = {
            "schema_version": 1,
            "agent": {
                "name": "agent",
                "run_id": "run",
                "collected_at": "2026-07-27T00:00:00+09:00",
            },
            "items": [
                self.valid_item(official_price=1200, official_price_currency="JPY")
            ],
        }

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("official_price_jpy: required" in error for error in errors))

    def test_evidence_must_include_source_url(self) -> None:
        payload = {
            "schema_version": 1,
            "agent": {
                "name": "agent",
                "run_id": "run",
                "collected_at": "2026-07-27T00:00:00+09:00",
            },
            "items": [
                self.valid_item(evidence=[{"url": "https://example.com/other", "type": "official"}])
            ],
        }

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("evidence: must include the source_url" in error for error in errors))

    def test_ichiban_display_name_requires_four_part_identity(self) -> None:
        payload = {
            "schema_version": 1,
            "agent": {
                "name": "agent",
                "run_id": "run",
                "collected_at": "2026-07-27T00:00:00+09:00",
            },
            "items": [
                self.valid_item(
                    display_name="Ichiban Kuji Frieren / A Prize / Figure",
                    series_name="Ichiban Kuji Frieren",
                )
            ],
        }

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("Ichiban Kuji items must use" in error for error in errors))

    def test_ichiban_character_field_matches_display_name_character_segment(self) -> None:
        payload = {
            "schema_version": 1,
            "agent": {
                "name": "agent",
                "run_id": "run",
                "collected_at": "2026-07-27T00:00:00+09:00",
            },
            "items": [
                self.valid_item(
                    display_name="Ichiban Kuji Frieren / A Prize / Figure / Fern",
                    series_name="Ichiban Kuji Frieren",
                    character_name="Frieren",
                )
            ],
        }

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("character_name: must match" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
