from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_agent_catalog_image_updates as target


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


class ImportAgentCatalogImageUpdatesTests(unittest.TestCase):
    def test_import_updates_missing_image_only(self) -> None:
        catalog = {
            "meta": {"generated_at": "2026-07-27T00:00:00Z"},
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "Missing Image",
                    "image_url": None,
                    "source_url": None,
                },
                {
                    "catalog_index": 2,
                    "name_ko": "Already Has Image",
                    "image_url": "https://example.com/existing.jpg",
                    "source_url": "https://example.com/existing",
                },
            ],
        }
        updates = payload(
            {
                "catalog_index": 1,
                "image_url": "https://example.com/image.jpg",
                "source_url": "https://example.com/detail",
                "evidence": [{"url": "https://example.com/detail", "type": "official"}],
                "confidence": "confirmed",
            },
            {
                "catalog_index": 2,
                "image_url": "https://example.com/new.jpg",
                "source_url": "https://example.com/new",
                "evidence": [{"url": "https://example.com/new", "type": "official"}],
                "confidence": "confirmed",
            },
        )

        result = target.import_payloads(catalog, [(Path("updates.json"), updates)])

        self.assertEqual(1, len(result["updated_rows"]))
        self.assertEqual(1, len(result["skipped_rows"]))
        self.assertEqual("image_url_already_present", result["skipped_rows"][0]["reason"])
        self.assertEqual("https://example.com/image.jpg", result["catalog"]["items"][0]["image_url"])
        self.assertEqual("https://example.com/detail", result["catalog"]["items"][0]["source_url"])
        self.assertEqual(
            target.local_path_for_image_url("https://example.com/image.jpg"),
            result["catalog"]["items"][0]["local_image_path"],
        )

    def test_import_can_download_asset_files_for_known_image_url(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "Missing Image",
                    "image_url": None,
                    "source_url": None,
                }
            ],
        }
        updates = payload(
            {
                "catalog_index": 1,
                "image_url": "https://example.com/image.jpg",
                "source_url": "https://example.com/detail",
                "evidence": [{"url": "https://example.com/detail", "type": "official"}],
                "confidence": "confirmed",
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            with patch.object(target, "ROOT", temp_root), patch.object(
                target,
                "download_image",
                return_value=(b"image-bytes", "image/jpeg"),
            ):
                result = target.import_payloads(
                    catalog,
                    [(Path("updates.json"), updates)],
                    download_assets=True,
                )

                local_path = result["catalog"]["items"][0]["local_image_path"]
                self.assertTrue(str(local_path).startswith("assets/catalog_images/"))
                self.assertTrue((temp_root / str(local_path)).is_file())
                self.assertTrue((temp_root / "assets" / str(local_path)).is_file())

    def test_write_path_updates_catalog_meta_and_moves_processed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            incoming = root / "data" / "intake" / "image_updates" / "incoming"
            processed = root / "data" / "intake" / "image_updates" / "processed"
            incoming.mkdir(parents=True)
            catalog_path = root / "data" / "catalog_public.json"
            meta_path = root / "data" / "catalog_public_meta.json"
            report_path = root / "server" / "agent_catalog_image_update_import_report.json"
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            catalog_path.write_text(
                target.json.dumps(
                    {
                        "meta": {"generated_at": "2026-07-27T00:00:00Z", "fields": ["catalog_index", "image_url"]},
                        "items": [{"catalog_index": 1, "name_ko": "Sample", "image_url": None}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            update_path = incoming / "agent-run.json"
            update_path.write_text(
                target.json.dumps(
                    payload(
                        {
                            "catalog_index": 1,
                            "image_url": "https://example.com/image.jpg",
                            "source_url": "https://example.com/detail",
                            "evidence": [{"url": "https://example.com/detail", "type": "official"}],
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
            target.write_json(catalog_path, result["catalog"], compact=True)
            target.write_json(meta_path, target.build_meta(result["catalog"]))
            with patch.object(target, "DEFAULT_INCOMING", incoming):
                moved = target.move_processed([update_path], processed)
            target.write_json(report_path, {"updated_rows": len(result["updated_rows"]), "processed_files": moved})

            catalog = target.load_json(catalog_path)
            meta = target.load_json(meta_path)

            self.assertFalse(update_path.exists())
            self.assertTrue((processed / "agent-run.json").exists())
            self.assertEqual("https://example.com/image.jpg", catalog["items"][0]["image_url"])
            self.assertEqual(0, meta["missing"]["image_url"])
            self.assertEqual(1, target.load_json(report_path)["updated_rows"])


if __name__ == "__main__":
    unittest.main()
