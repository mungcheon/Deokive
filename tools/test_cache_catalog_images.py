from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.cache_catalog_images import cache_images


class CacheCatalogImagesTest(unittest.TestCase):
    def test_row_indexes_limit_cache_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            cache_dir = Path(raw_tmp)
            rows = [
                {"catalog_index": 1, "image_url": "https://example.com/a.jpg"},
                {"catalog_index": 2, "image_url": "https://example.com/b.jpg"},
            ]

            def fake_download(url: str, target: Path, max_size: int, quality: int) -> tuple[bool, str | None]:
                target.write_bytes(b"image")
                return True, None

            with patch("tools.cache_catalog_images._download_image", side_effect=fake_download):
                result = cache_images(
                    rows,
                    cache_dir,
                    max_rows=None,
                    dry_run=False,
                    delay_seconds=0,
                    max_size=640,
                    quality=78,
                    row_indexes={2},
                )

            self.assertEqual(result["checked_with_image_url"], 1)
            self.assertNotIn("local_image_path", rows[0])
            self.assertTrue(rows[1]["local_image_path"].startswith("assets/catalog_images/"))


if __name__ == "__main__":
    unittest.main()
