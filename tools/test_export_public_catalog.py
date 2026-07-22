from __future__ import annotations

import unittest
from pathlib import Path

from tools.export_public_catalog import PUBLIC_FIELDS, build_meta, export_rows


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


if __name__ == "__main__":
    unittest.main()
