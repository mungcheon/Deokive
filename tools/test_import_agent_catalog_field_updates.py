from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_agent_catalog_field_updates as target


def payload(*updates: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "agent": {
            "name": "agent",
            "run_id": "run",
            "collected_at": "2026-07-27T00:00:00+09:00",
        },
        "updates": list(updates),
    }


class ImportAgentCatalogFieldUpdatesTests(unittest.TestCase):
    def test_import_updates_missing_fields_only(self) -> None:
        catalog = {
            "meta": {"generated_at": "2026-07-27T00:00:00Z"},
            "items": [
                {"catalog_index": 1, "name_ko": "Missing Source", "source_url": ""},
                {"catalog_index": 2, "name_ko": "Has Source", "source_url": "https://example.com/existing"},
            ],
        }
        updates = payload(
            {
                "catalog_index": 1,
                "field": "source_url",
                "value": "https://example.com/product",
                "evidence": [{"url": "https://example.com/product", "type": "official"}],
                "confidence": "confirmed",
            },
            {
                "catalog_index": 2,
                "field": "source_url",
                "value": "https://example.com/new",
                "evidence": [{"url": "https://example.com/new", "type": "official"}],
                "confidence": "confirmed",
            },
        )

        result = target.import_payloads(catalog, [(Path("updates.json"), updates)])

        self.assertEqual(1, len(result["updated_rows"]))
        self.assertEqual(1, len(result["skipped_rows"]))
        self.assertEqual("field_already_present", result["skipped_rows"][0]["reason"])
        self.assertEqual("https://example.com/product", result["catalog"]["items"][0]["source_url"])
        self.assertEqual("https://example.com/existing", result["catalog"]["items"][1]["source_url"])

    def test_import_skips_non_confirmed_updates(self) -> None:
        catalog = {"items": [{"catalog_index": 1, "name_ko": "Sample", "release_date": ""}]}
        updates = payload(
            {
                "catalog_index": 1,
                "field": "release_date",
                "value": "2026-07",
                "evidence": [{"url": "https://example.com/product", "type": "official"}],
                "confidence": "candidate",
            }
        )

        result = target.import_payloads(catalog, [(Path("updates.json"), updates)])

        self.assertEqual([], result["updated_rows"])
        self.assertEqual("confidence_not_confirmed", result["skipped_rows"][0]["reason"])
        self.assertEqual("", result["catalog"]["items"][0]["release_date"])

    def test_validated_payloads_reject_existing_field_with_catalog_context(self) -> None:
        catalog = {"items": [{"catalog_index": 1, "name_ko": "Sample", "release_date": "2026-01"}]}
        updates = payload(
            {
                "catalog_index": 1,
                "field": "release_date",
                "value": "2026-07",
                "evidence": [{"url": "https://example.com/product", "type": "official"}],
                "confidence": "confirmed",
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            update_path = Path(temp_dir) / "agent-20260727-fields.json"
            update_path.write_text(target.json.dumps(updates, ensure_ascii=False), encoding="utf-8")

            payloads, errors = target.load_validated_payloads([update_path], catalog=catalog)

        self.assertEqual([], payloads)
        self.assertTrue(any("target catalog field already has a value" in error for error in errors))

    def test_write_path_updates_catalog_meta_and_moves_processed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            incoming = root / "data" / "intake" / "field_updates" / "incoming"
            processed = root / "data" / "intake" / "field_updates" / "processed"
            incoming.mkdir(parents=True)
            catalog_path = root / "data" / "catalog_public.json"
            meta_path = root / "data" / "catalog_public_meta.json"
            report_path = root / "server" / "agent_catalog_field_update_import_report.json"
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            catalog_path.write_text(
                target.json.dumps(
                    {
                        "meta": {
                            "generated_at": "2026-07-27T00:00:00Z",
                            "fields": ["catalog_index", "release_date"],
                        },
                        "items": [{"catalog_index": 1, "name_ko": "Sample", "release_date": ""}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            update_path = incoming / "agent-20260727-release-date.json"
            update_path.write_text(
                target.json.dumps(
                    payload(
                        {
                            "catalog_index": 1,
                            "field": "release_date",
                            "value": "2026-07",
                            "evidence": [{"url": "https://example.com/product", "type": "official"}],
                            "confidence": "confirmed",
                        }
                    ),
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            catalog = target.load_catalog(catalog_path)
            payloads, errors = target.load_validated_payloads([incoming], catalog=catalog)
            self.assertEqual([], errors)
            result = target.import_payloads(catalog, payloads)
            target.write_json(catalog_path, result["catalog"], compact=True)
            target.write_json(meta_path, target.build_meta(result["catalog"]))
            with patch.object(target, "DEFAULT_INCOMING", incoming):
                moved = target.move_processed([update_path], processed)
            target.write_json(report_path, {"updated_rows": len(result["updated_rows"]), "processed_files": moved})

            catalog = target.load_json(catalog_path)
            meta = target.load_json(meta_path)

            self.assertFalse(update_path.exists())
            self.assertTrue((processed / "agent-20260727-release-date.json").exists())
            self.assertEqual("2026-07", catalog["items"][0]["release_date"])
            self.assertEqual(0, meta["missing"]["release_date"])
            self.assertEqual(1, target.load_json(report_path)["updated_rows"])


if __name__ == "__main__":
    unittest.main()
