from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_public_catalog_safety as audit


class AuditPublicCatalogSafetyTest(unittest.TestCase):
    def test_public_catalog_comparison_reports_missing_image_delta(self) -> None:
        seed_rows = [
            {"name_ko": "A", "category": "figure", "character_name": "A", "image_url": ""},
            {"name_ko": "B", "category": "figure", "character_name": "B", "image_url": ""},
        ]
        public_rows = [
            {"name_ko": "A", "category": "figure", "character_name": "A", "image_url": "https://example.com/a.jpg"},
            {"name_ko": "B", "category": "figure", "character_name": "B", "image_url": ""},
            {"name_ko": "C", "category": "figure", "character_name": "C", "image_url": "https://example.com/c.jpg"},
        ]

        with tempfile.TemporaryDirectory() as tmp:
            public_path = Path(tmp) / "catalog_public.json"
            public_path.write_text(json.dumps({"items": public_rows}), encoding="utf-8")

            seed_summary = audit.summarize_seed(seed_rows)
            public_summary = audit.summarize_public_catalog(public_path)
            comparison = audit.compare_public_catalog(public_summary, seed_summary)

        self.assertEqual(seed_summary["missing_enrichment"]["image_url"], 2)
        self.assertEqual(public_summary["missing_enrichment"]["image_url"], 1)
        self.assertEqual(comparison["row_delta"], 1)
        self.assertEqual(comparison["image_missing_delta"], -1)
        self.assertEqual(comparison["public_image_missing_rows"], 1)
        self.assertEqual(comparison["seed_image_missing_rows"], 2)
        self.assertFalse(comparison["same_row_count"])

    def test_ichiban_prize_rows_with_different_characters_are_not_duplicates(self) -> None:
        rows = [
            {
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST / P\u8cde / \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 / \u30ad\u30e3\u30e9A",
                "name_ja": "P\u8cde \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9",
                "category": "\u30a2\u30af\u30ea\u30eb",
                "character_name": "\u30ad\u30e3\u30e9A",
                "source_url": "https://1kuji.com/products/test",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
            },
            {
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST / P\u8cde / \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9 / \u30ad\u30e3\u30e9B",
                "name_ja": "P\u8cde \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9",
                "category": "\u30a2\u30af\u30ea\u30eb",
                "character_name": "\u30ad\u30e3\u30e9B",
                "source_url": "https://1kuji.com/products/test",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
            },
        ]

        summary = audit.summarize_seed(rows)

        self.assertEqual(summary["duplicate_groups"], 0)


if __name__ == "__main__":
    unittest.main()
