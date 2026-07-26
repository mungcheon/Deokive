from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_catalog_db_sync import build_report


FIELDS = (
    "name_ko",
    "name_ja",
    "name_en",
    "category",
    "character_name",
    "affiliation",
    "series_name",
    "sub_series",
    "official_price_jpy",
    "barcode",
    "image_url",
    "source_url",
    "source_store",
    "release_date",
    "is_active",
)


def _row(**overrides):
    row = {
        "name_ko": "루피 키링",
        "name_ja": "",
        "name_en": "",
        "category": "키링",
        "character_name": "루피",
        "affiliation": "원피스",
        "series_name": "",
        "sub_series": "",
        "official_price_jpy": 770,
        "barcode": "",
        "image_url": "https://example.test/image.jpg",
        "source_url": "https://example.test/product",
        "source_store": "테스트",
        "release_date": "",
        "is_active": 1,
    }
    row.update(overrides)
    return row


def _write_seed(path: Path, rows: list[dict]) -> None:
    clean_rows = [{key: value for key, value in row.items() if key != "is_active"} for row in rows]
    path.write_text(json.dumps(clean_rows, ensure_ascii=False), encoding="utf-8")


def _write_public_seed(path: Path, rows: list[dict]) -> None:
    clean_rows = [{key: value for key, value in row.items() if key != "is_active"} for row in rows]
    path.write_text(
        json.dumps({"meta": {"row_count": len(clean_rows)}, "items": clean_rows}, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_db(path: Path, rows: list[dict]) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            create table goods_catalog (
              id integer primary key autoincrement,
              name_ko text, name_ja text, name_en text, category text,
              character_name text, affiliation text, series_name text, sub_series text,
              official_price_jpy integer, barcode text, image_url text, source_url text,
              source_store text, release_date text, is_active integer
            )
            """
        )
        placeholders = ", ".join("?" for _ in FIELDS)
        conn.executemany(
            f"insert into goods_catalog ({', '.join(FIELDS)}) values ({placeholders})",
            [tuple(row.get(field) for field in FIELDS) for row in rows],
        )
        conn.commit()
    finally:
        conn.close()


class CatalogDbSyncAuditTests(unittest.TestCase):
    def test_reports_ok_when_db_matches_seed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = root / "seed.json"
            db = root / "catalog.db"
            row = _row()
            _write_seed(seed, [row])
            _write_db(db, [row])

            report = build_report(seed, [db])

        self.assertTrue(report["ok"])
        self.assertEqual(report["databases"][0]["active_rows"], 1)
        self.assertEqual(report["databases"][0]["missing_images"], 0)

    def test_accepts_public_catalog_object_seed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = root / "catalog_public.json"
            db = root / "catalog.db"
            row = _row()
            _write_public_seed(seed, [row])
            _write_db(db, [row])

            report = build_report(seed, [db])

        self.assertTrue(report["ok"])
        self.assertEqual(report["seed_rows"], 1)

    def test_reports_stale_missing_updated_and_duplicate_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = root / "seed.json"
            db = root / "catalog.db"
            seed_row = _row()
            missing_seed_row = _row(name_ko="조로 키링", character_name="조로", source_url="https://example.test/zoro")
            stale_row = _row(name_ko="상디 키링", character_name="상디", source_url="https://example.test/sanji")
            changed_row = _row(image_url="")
            duplicate_row = _row()
            _write_seed(seed, [seed_row, missing_seed_row])
            _write_db(db, [changed_row, duplicate_row, stale_row])

            report = build_report(seed, [db])

        db_report = report["databases"][0]
        self.assertFalse(report["ok"])
        self.assertEqual(db_report["stale_active_rows"], 1)
        self.assertEqual(db_report["missing_seed_rows"], 1)
        self.assertEqual(db_report["updated_active_rows"], 1)
        self.assertEqual(db_report["duplicate_active_rows"], 1)
        self.assertEqual(db_report["missing_images"], 1)


if __name__ == "__main__":
    unittest.main()
