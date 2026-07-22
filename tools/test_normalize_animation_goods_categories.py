from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import normalize_animation_goods_categories as normalize


class NormalizeAnimationGoodsCategoriesTests(unittest.TestCase):
    def test_load_payload_accepts_public_catalog_shape(self) -> None:
        payload = {
            "meta": {"row_count": 1},
            "items": [
                {
                    "source_store": "애니메이트",
                    "category": "기타 굿즈",
                    "name_ko": "misc goods",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            loaded_payload, rows = normalize._load_payload(path)

        self.assertIsInstance(loaded_payload, dict)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "기타 굿즈")

    def test_write_payload_preserves_public_catalog_meta(self) -> None:
        payload = {
            "meta": {
                "generated_at": "2026-01-01T00:00:00Z",
                "row_count": 1,
                "total_items": 1,
                "fields": ["category", "sub_series"],
                "missing": {},
            },
            "items": [{"source_store": "애니메이트", "category": "액세서리", "sub_series": ""}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            normalize._write_payload(path, payload, payload["items"])
            written = json.loads(path.read_text(encoding="utf-8"))

        self.assertIsInstance(written, dict)
        self.assertEqual(written["meta"]["row_count"], 1)
        self.assertEqual(written["meta"]["total_items"], 1)
        self.assertEqual(written["meta"]["missing"]["category"], 0)
        self.assertEqual(written["meta"]["missing"]["sub_series"], 1)


if __name__ == "__main__":
    unittest.main()
