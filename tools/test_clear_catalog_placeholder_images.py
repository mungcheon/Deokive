from __future__ import annotations

import json
import unittest

from tools.clear_catalog_placeholder_images import clear_placeholder_images


class ClearCatalogPlaceholderImagesTest(unittest.TestCase):
    def test_clears_only_placeholder_image_rows(self) -> None:
        placeholder = "https://online-kuji.chiikawamarket.jp/assets/images/ogp.png"
        keep = "https://example.com/product.jpg"
        payload = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "placeholder row",
                    "image_url": placeholder,
                    "local_image_path": "assets/catalog_images/placeholder.webp",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "real row",
                    "image_url": keep,
                    "local_image_path": "assets/catalog_images/real.webp",
                },
            ]
        }
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        updated, cleared = clear_placeholder_images(text, {placeholder})

        updated_payload = json.loads(updated)
        self.assertEqual([row["catalog_index"] for row in cleared], [1])
        self.assertIsNone(updated_payload["items"][0]["image_url"])
        self.assertIsNone(updated_payload["items"][0]["local_image_path"])
        self.assertEqual(updated_payload["items"][1]["image_url"], keep)
        self.assertEqual(updated_payload["items"][1]["local_image_path"], "assets/catalog_images/real.webp")


if __name__ == "__main__":
    unittest.main()
