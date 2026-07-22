from __future__ import annotations

import unittest
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.export_public_catalog import (
    PUBLIC_FIELDS,
    build_meta,
    export_rows,
    validate_row_count,
)


class ExportPublicCatalogTest(unittest.TestCase):
    def test_export_rows_keeps_only_public_fields(self) -> None:
        rows = [
            {
                "name_ko": "테스트 굿즈",
                "category": "피규어",
                "source_url": " https://example.com/item ",
                "image_url": " https://example.com/image.webp ",
                "local_image_path": " assets/catalog_images/sample.webp ",
                "official_price_jpy": "1200",
                "memo": "private",
                "folder_id": "local-folder",
                "device_id": "local-device",
                "local_folder_path": "C:/Users/example/private",
            }
        ]

        exported = export_rows(rows)

        self.assertEqual(exported[0]["catalog_index"], 0)
        self.assertEqual(exported[0]["name_ko"], "테스트 굿즈")
        self.assertEqual(exported[0]["source_url"], "https://example.com/item")
        self.assertEqual(exported[0]["image_url"], "https://example.com/image.webp")
        self.assertEqual(exported[0]["local_image_path"], "assets/catalog_images/sample.webp")
        self.assertEqual(exported[0]["official_price_jpy"], 1200)
        self.assertNotIn("memo", exported[0])
        self.assertNotIn("folder_id", exported[0])
        self.assertNotIn("device_id", exported[0])
        self.assertNotIn("local_folder_path", exported[0])

    def test_build_meta_matches_public_schema(self) -> None:
        rows = export_rows(
            [
                {
                    "name_ko": "A",
                    "category": "피규어",
                    "local_image_path": "assets/catalog_images/a.webp",
                },
                {
                    "name_ko": "B",
                    "category": "피규어",
                    "image_url": "https://example.com/b.jpg",
                },
            ]
        )

        meta = build_meta(
            rows,
            source=Path("server/catalog_seed_from_local.json"),
            generated_at="2026-07-21T00:00:00Z",
        )

        self.assertEqual(meta["schema_version"], 1)
        self.assertEqual(meta["generated_at"], "2026-07-21T00:00:00Z")
        self.assertEqual(meta["row_count"], 2)
        self.assertEqual(meta["fields"], PUBLIC_FIELDS)
        self.assertEqual(meta["missing"]["image_url"], 1)
        self.assertEqual(meta["missing"]["local_image_path"], 1)
        self.assertFalse(meta["privacy"]["contains_private_memos"])
        self.assertFalse(meta["privacy"]["contains_local_folders"])

    def test_validate_row_count_rejects_unintentional_regression(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            meta = Path(raw_tmp) / "catalog_public_meta.json"
            meta.write_text('{"row_count": 3}\n', encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                validate_row_count([{"name_ko": "A"}, {"name_ko": "B"}], reference_meta=meta)

            self.assertIn("refusing to export a smaller public catalog", str(raised.exception))

    def test_validate_row_count_allows_explicit_regression(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            meta = Path(raw_tmp) / "catalog_public_meta.json"
            meta.write_text('{"row_count": 3}\n', encoding="utf-8")

            validate_row_count(
                [{"name_ko": "A"}, {"name_ko": "B"}],
                reference_meta=meta,
                allow_row_count_drop=True,
            )


if __name__ == "__main__":
    unittest.main()
