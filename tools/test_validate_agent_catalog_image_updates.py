from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_agent_catalog_image_updates as target


ROOT = Path(__file__).resolve().parents[1]


class AgentCatalogImageUpdateValidationTests(unittest.TestCase):
    def valid_update(self, **overrides: object) -> dict[str, object]:
        update: dict[str, object] = {
            "catalog_index": 10,
            "image_url": "https://example.com/product.jpg",
            "source_url": "https://example.com/product",
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
        path = ROOT / "data" / "intake" / "image_updates" / "templates" / "agent_catalog_image_update.template.json"
        payload = target.load_json(path)

        errors, summary = target.validate_payload(path, payload)

        self.assertEqual([], errors)
        self.assertEqual(1, summary["updates"])

    def test_requires_evidence_for_source_url(self) -> None:
        payload = self.payload(
            self.valid_update(evidence=[{"url": "https://example.com/other", "type": "official"}])
        )

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("evidence: must include source_url" in error for error in errors))

    def test_rejects_duplicate_catalog_index_in_one_file(self) -> None:
        payload = self.payload(
            self.valid_update(catalog_index=10),
            self.valid_update(catalog_index=10),
        )

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("duplicate catalog_index" in error for error in errors))

    def test_rejects_unknown_fields(self) -> None:
        update = self.valid_update()
        update["random"] = "nope"
        payload = self.payload(update)
        payload["extra"] = True

        errors, _summary = target.validate_payload(Path("sample.json"), payload)

        self.assertTrue(any("sample.json: unknown field(s): extra" in error for error in errors))
        self.assertTrue(any("updates[0]: unknown field(s): random" in error for error in errors))

    def test_catalog_context_rejects_missing_or_already_imaged_rows(self) -> None:
        catalog_rows = {
            10: {"catalog_index": 10, "image_url": None},
            11: {"catalog_index": 11, "image_url": "https://example.com/existing.jpg"},
        }
        payload = self.payload(
            self.valid_update(catalog_index=11),
            self.valid_update(catalog_index=99, image_url="https://example.com/other.jpg"),
        )

        errors, _summary = target.validate_payload(
            Path("sample.json"),
            payload,
            catalog_rows=catalog_rows,
        )

        self.assertTrue(any("target catalog row already has an image" in error for error in errors))
        self.assertTrue(any("not found in catalog_public.json" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
