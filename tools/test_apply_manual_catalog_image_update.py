from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.apply_manual_catalog_image_update import (
    _replace_one_line_json_object,
    _sync_flutter_seed,
)


class ApplyManualCatalogImageUpdateTest(unittest.TestCase):
    def test_replace_one_line_json_object_updates_target_row(self) -> None:
        text = (
            '{"items":['
            '{"catalog_index":1,"name_ko":"A"},'
            '{"catalog_index":2,"name_ko":"B","image_url":null}'
            "]}\n"
        )

        updated = _replace_one_line_json_object(
            text,
            2,
            {"image_url": "https://example.test/image.jpg"},
        )

        self.assertIn('"catalog_index":2', updated)
        self.assertIn('"image_url":"https://example.test/image.jpg"', updated)
        self.assertIn('"name_ko":"A"', updated)

    def test_sync_flutter_seed_generates_seed_from_updated_public_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            catalog = root / "catalog_public.json"
            seed = root / "seed_catalog.dart"
            catalog.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "catalog_index": 7,
                                "name_ko": "테스트 굿즈",
                                "category": "피규어",
                                "character_name": "테스트",
                                "image_url": "https://example.test/image.jpg",
                                "local_image_path": "assets/catalog_images/test.webp",
                            }
                        ]
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )

            _sync_flutter_seed(catalog, seed)

            text = seed.read_text(encoding="utf-8")
            self.assertIn("const List<GoodsCatalogEntry> kSeedCatalog", text)
            self.assertIn("nameKo: '테스트 굿즈'", text)
            self.assertIn("imageUrl: 'https://example.test/image.jpg'", text)
            self.assertIn("localImagePath: 'assets/catalog_images/test.webp'", text)


if __name__ == "__main__":
    unittest.main()
