from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dedupe_catalog


def _row(index: int, **overrides):
    row = {
        "catalog_index": index,
        "name_ko": "테스트 굿즈",
        "category": "굿즈",
        "source_store": "테스트 스토어",
        "source_url": "https://example.test/product/1",
        "image_url": "",
        "local_image_path": f"assets/catalog_images/{index}.webp",
    }
    row.update(overrides)
    return row


class DedupeCatalogTests(unittest.TestCase):
    def test_process_json_accepts_public_catalog_shape_dry_run(self) -> None:
        payload = {
            "meta": {"row_count": 2, "total_items": 2, "fields": ["image_url"], "missing": {}},
            "items": [_row(1), _row(2, image_url="https://example.test/image.jpg")],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            report = Path(tmp) / "dedupe.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            rows, drops = dedupe_catalog.process_json(path, write=False, report_path=report)
            written = json.loads(path.read_text(encoding="utf-8"))
            report_payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(rows, 2)
        self.assertEqual(drops, 1)
        self.assertIsInstance(written, dict)
        self.assertEqual(len(written["items"]), 2)
        self.assertEqual(report_payload["duplicate_groups"], 1)

    def test_process_json_preserves_public_catalog_meta_on_write(self) -> None:
        payload = {
            "meta": {
                "generated_at": "2026-01-01T00:00:00Z",
                "row_count": 2,
                "total_items": 2,
                "fields": ["catalog_index", "image_url"],
                "missing": {},
            },
            "items": [_row(1), _row(2, image_url="https://example.test/image.jpg")],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            rows, drops = dedupe_catalog.process_json(path, write=True, report_path=None)
            written = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(rows, 2)
        self.assertEqual(drops, 1)
        self.assertEqual(len(written["items"]), 1)
        self.assertEqual(written["items"][0]["catalog_index"], 2)
        self.assertEqual(written["items"][0]["local_image_path"], "assets/catalog_images/2.webp")
        self.assertEqual(written["meta"]["row_count"], 1)
        self.assertEqual(written["meta"]["total_items"], 1)
        self.assertEqual(written["meta"]["missing"]["image_url"], 0)

    def test_gashapon_jan_code_keeps_distinct_source_url_rows(self) -> None:
        rows = [
            _row(
                1,
                name_ko="데스노트 코믹 참",
                source_store="가챠",
                source_url="https://gashapon.jp/products/detail.php?jan_code=4570118211446000",
            ),
            _row(
                2,
                name_ko="치이카와 메지루시",
                source_store="가챠",
                source_url="https://gashapon.jp/products/detail.php?jan_code=4570117984075000",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            report = Path(tmp) / "dedupe.json"
            path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            _, drops = dedupe_catalog.process_json(path, write=False, report_path=report)
            report_payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(drops, 0)
        self.assertEqual(report_payload["duplicate_groups"], 0)


if __name__ == "__main__":
    unittest.main()
