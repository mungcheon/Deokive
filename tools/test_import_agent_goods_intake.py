from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_write_path_updates_catalog_meta_and_moves_processed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            incoming = root / "data" / "intake" / "incoming"
            processed = root / "data" / "intake" / "processed"
            incoming.mkdir(parents=True)
            catalog_path = root / "data" / "catalog_public.json"
            meta_path = root / "data" / "catalog_public_meta.json"
            report_path = root / "server" / "agent_goods_intake_import_report.json"
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            catalog_path.write_text(
                '{"meta": {"generated_at": "2026-07-27T00:00:00Z"}, "items": [], "total_items": 0}\n',
                encoding="utf-8",
            )
            intake_path = incoming / "agent-run.json"
            intake_path.write_text(
                target.json.dumps(
                    intake_payload(
                        {
                            "external_id": "sku-1",
                            "display_name": "Write Import Item",
                            "category": "badge",
                            "series_name": "Series",
                            "source_store": "Official",
                            "source_url": "https://example.com/write-import",
                            "evidence": [
                                {"url": "https://example.com/write-import", "type": "official"}
                            ],
                            "official_price": 1200,
                            "official_price_currency": "JPY",
                            "official_price_jpy": 1200,
                            "confidence": "confirmed",
                        }
                    ),
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payloads, errors = target.load_validated_payloads([incoming])
            self.assertEqual([], errors)
            result = target.import_payloads(target.load_catalog(catalog_path), payloads)
            target.write_json(catalog_path, result["catalog"])
            target.write_json(meta_path, target.build_meta(result["catalog"]))
            with patch.object(target, "DEFAULT_INCOMING", incoming):
                moved = target.move_processed([intake_path], processed)
            target.write_json(
                report_path,
                {"added_rows": len(result["added_rows"]), "processed_files": moved},
            )

            catalog = target.load_json(catalog_path)
            meta = target.load_json(meta_path)

            self.assertFalse(intake_path.exists())
            self.assertTrue((processed / "agent-run.json").exists())
            self.assertEqual(1, catalog["total_items"])
            self.assertEqual(1, meta["row_count"])
            self.assertEqual(1, meta["missing"]["image_url"])
            self.assertEqual(1, target.load_json(report_path)["added_rows"])


if __name__ == "__main__":
    unittest.main()
