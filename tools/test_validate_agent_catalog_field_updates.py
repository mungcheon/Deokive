from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_agent_catalog_field_updates as target


ROOT = Path(__file__).resolve().parents[1]


class AgentCatalogFieldUpdateValidationTests(unittest.TestCase):
    def valid_update(self, **overrides: object) -> dict[str, object]:
        update: dict[str, object] = {
            "catalog_index": 10,
            "field": "source_url",
            "value": "https://example.com/product",
            "evidence": [{"url": "https://example.com/product", "type": "official"}],
            "confidence": "confirmed",
        }
        update.update(overrides)
        return update

    def payload(self, *updates: dict[str, object]) -> dict[str, object]:
        return {
            "schema_version": 1,
            "agent": {
                "name": "agent",
                "run_id": "run",
                "collected_at": "2026-07-27T00:00:00+09:00",
            },
            "updates": list(updates),
        }

    def test_template_payload_is_valid(self) -> None:
        path = ROOT / "data" / "intake" / "field_updates" / "templates" / "agent_catalog_field_update.template.json"
        payload = target.load_json(path)

        errors, summary = target.validate_payload(path, payload)

        self.assertEqual([], errors)
        self.assertEqual(1, summary["updates"])

    def test_requires_source_url_value_in_evidence(self) -> None:
        payload = self.payload(
            self.valid_update(evidence=[{"url": "https://example.com/other", "type": "official"}])
        )

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("must include the source_url value" in error for error in errors))

    def test_rejects_duplicate_catalog_field_target(self) -> None:
        payload = self.payload(
            self.valid_update(catalog_index=10, field="release_date", value="2026-07"),
            self.valid_update(catalog_index=10, field="release_date", value="2026-08"),
        )

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("duplicate catalog_index/field" in error for error in errors))

    def test_validates_field_specific_values(self) -> None:
        payload = self.payload(
            self.valid_update(field="barcode", value="abc"),
            self.valid_update(field="official_price_jpy", value="1200"),
            self.valid_update(field="official_price_currency", value="EUR"),
        )

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("expected 8-14 digit barcode" in error for error in errors))
        self.assertTrue(any("expected integer for official_price_jpy" in error for error in errors))
        self.assertTrue(any("expected one of" in error for error in errors))

    def test_catalog_context_rejects_missing_or_already_filled_rows(self) -> None:
        catalog_rows = {
            10: {"catalog_index": 10, "release_date": ""},
            11: {"catalog_index": 11, "release_date": "2026-07"},
        }
        payload = self.payload(
            self.valid_update(catalog_index=11, field="release_date", value="2026-08"),
            self.valid_update(catalog_index=99, field="release_date", value="2026-08"),
        )

        errors, _summary = target.validate_payload(
            Path("sample.json"),
            payload,
            catalog_rows=catalog_rows,
        )

        self.assertTrue(any("target catalog field already has a value" in error for error in errors))
        self.assertTrue(any("not found in catalog_public.json" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
