from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_stale_source_cleanup_queue as cleanup


class ApplyStaleSourceCleanupQueueTests(unittest.TestCase):
    def test_apply_cleanup_clears_matching_stale_source_and_image_fields(self) -> None:
        rows = [
            {
                "catalog_index": 10,
                "name_ko": "Wrong Image Row",
                "name_ja": "Wrong Image Row JA",
                "source_url": "https://example.test/wrong",
                "image_url": "https://cdn.example.test/wrong.jpg",
                "local_image_path": "assets/catalog_images/wrong.webp",
                "source_store": "Store",
            }
        ]
        queue = [
            {
                "catalog_index": 10,
                "name_ko": "Wrong Image Row",
                "name_ja": "Wrong Image Row JA",
                "current_source_url": "https://example.test/wrong",
                "current_image_url": "https://cdn.example.test/wrong.jpg",
                "identity_status": "live_title_mismatch",
                "recommended_action": "find_exact_source_url_before_image_use",
                "live_title": "Other Product",
            }
        ]

        updated, changes, skipped = cleanup.apply_cleanup(rows, queue)

        self.assertEqual(updated, 1)
        self.assertEqual(skipped, [])
        self.assertEqual(changes[0]["catalog_index"], 10)
        self.assertNotIn("source_url", rows[0])
        self.assertNotIn("image_url", rows[0])
        self.assertNotIn("local_image_path", rows[0])
        self.assertEqual(rows[0]["source_store"], "Store")

    def test_apply_cleanup_skips_when_source_url_changed(self) -> None:
        rows = [
            {
                "catalog_index": 10,
                "name_ko": "Already Fixed",
                "source_url": "https://example.test/correct",
                "image_url": "https://cdn.example.test/wrong.jpg",
            }
        ]
        queue = [
            {
                "catalog_index": 10,
                "name_ko": "Already Fixed",
                "current_source_url": "https://example.test/wrong",
                "current_image_url": "https://cdn.example.test/wrong.jpg",
                "identity_status": "live_title_mismatch",
                "recommended_action": "find_exact_source_url_before_image_use",
            }
        ]

        updated, changes, skipped = cleanup.apply_cleanup(rows, queue)

        self.assertEqual(updated, 0)
        self.assertEqual(changes, [])
        self.assertEqual(skipped[0]["reason"], "source_url_changed")
        self.assertEqual(rows[0]["source_url"], "https://example.test/correct")

    def test_apply_cleanup_skips_weak_overlap_rows(self) -> None:
        rows = [
            {
                "catalog_index": 10,
                "name_ko": "Weak Row",
                "source_url": "https://example.test/weak",
                "image_url": "https://cdn.example.test/weak.jpg",
            }
        ]
        queue = [
            {
                "catalog_index": 10,
                "current_source_url": "https://example.test/weak",
                "current_image_url": "https://cdn.example.test/weak.jpg",
                "identity_status": "weak_title_overlap",
                "recommended_action": "review_source_url_before_image_use",
            }
        ]

        updated, changes, skipped = cleanup.apply_cleanup(rows, queue)

        self.assertEqual(updated, 0)
        self.assertEqual(changes, [])
        self.assertEqual(skipped[0]["reason"], "identity_status_not_mismatch")

    def test_write_catalog_refreshes_public_missing_meta(self) -> None:
        payload = {
            "meta": {
                "fields": ["catalog_index", "source_url", "image_url", "local_image_path"],
                "missing": {"catalog_index": 0, "source_url": 0, "image_url": 0, "local_image_path": 0},
                "row_count": 1,
                "total_items": 1,
            },
            "items": [
                {
                    "catalog_index": 1,
                    "source_url": "https://example.test",
                    "image_url": "https://cdn.example.test/image.jpg",
                    "local_image_path": "assets/catalog_images/image.webp",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            rows, wrapper = cleanup.load_catalog(path)
            rows[0].pop("source_url")
            rows[0].pop("image_url")
            rows[0].pop("local_image_path")
            cleanup.write_catalog(path, rows, wrapper)

            written = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(written["meta"]["missing"]["source_url"], 1)
        self.assertEqual(written["meta"]["missing"]["image_url"], 1)
        self.assertEqual(written["meta"]["missing"]["local_image_path"], 1)
        self.assertEqual(written["meta"]["row_count"], 1)


if __name__ == "__main__":
    unittest.main()
