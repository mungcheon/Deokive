from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_catalog_naming_public as audit


class AuditCatalogNamingPublicTest(unittest.TestCase):
    def test_report_passes_valid_fern_and_ichiban_rows(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "\ub137\ub3c4\ub85c\uc774\ub4dc \ud398\ub978",
                "name_ja": "\u306d\u3093\u3069\u308d\u3044\u3069 \u30d5\u30a7\u30eb\u30f3",
                "character_name": "\ud398\ub978",
            },
            {
                "catalog_index": 2,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u3061\u3044\u304b\u308f / A\u8cde / \u3061\u3044\u304b\u308f \u306c\u3044\u3050\u308b\u307f / \uce58\uc774\uce74\uc640",
                "name_ja": "A\u8cde \u3061\u3044\u304b\u308f \u306c\u3044\u3050\u308b\u307f",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                "sub_series": "A\u8cde",
                "character_name": "\uce58\uc774\uce74\uc640",
                "official_price_jpy": 750,
            },
            {
                "catalog_index": 3,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u3061\u3044\u304b\u308f / \u30e9\u30b9\u30c8\u30ef\u30f3\u8cde / \u30e9\u30b0\u30de\u30c3\u30c8 / \uce58\uc774\uce74\uc640",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                "sub_series": "\u30e9\u30b9\u30c8\u30ef\u30f3\u8cde",
                "character_name": "\uce58\uc774\uce74\uc640",
                "official_price_jpy": 0,
            },
        ]

        report = audit.build_report(rows, generated_at="2026-07-27T00:00:00Z")

        self.assertEqual(report["summary"]["status"], "pass")
        self.assertEqual(report["summary"]["ichiban_rows"], 2)
        self.assertEqual(report["summary"]["total_issue_rows"], 0)

    def test_report_flags_fern_typo_and_ichiban_shape_errors(self) -> None:
        rows = [
            {
                "catalog_index": 4,
                "name_ko": "\ub137\ub3c4\ub85c\uc774\ub4dc \ud380",
                "name_ja": "\u306d\u3093\u3069\u308d\u3044\u3069 \u30d5\u30a7\u30eb\u30f3",
                "character_name": "\ud380",
            },
            {
                "catalog_index": 5,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u3061\u3044\u304b\u308f / A\u8cde / \u306c\u3044\u3050\u308b\u307f",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                "sub_series": "B\u8cde",
                "character_name": "\ud558\uce58\uc640\ub808",
                "official_price_jpy": 750,
            },
            {
                "catalog_index": 6,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u3061\u3044\u304b\u308f / \u30e9\u30b9\u30c8\u30ef\u30f3\u8cde / \u30e9\u30b0\u30de\u30c3\u30c8 / \uce58\uc774\uce74\uc640",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                "sub_series": "\u30e9\u30b9\u30c8\u30ef\u30f3\u8cde",
                "character_name": "\uce58\uc774\uce74\uc640",
                "official_price_jpy": 750,
            },
        ]

        report = audit.build_report(rows, generated_at="2026-07-27T00:00:00Z")
        reasons = dict(report["summary"]["by_reason"])

        self.assertEqual(report["summary"]["status"], "needs_review")
        self.assertEqual(reasons["fern_korean_name_should_be_페른"], 1)
        self.assertEqual(reasons["fern_japanese_name_character_mismatch"], 1)
        self.assertEqual(reasons["ichiban_name_missing_release_prize_item_character_parts"], 1)
        self.assertEqual(reasons["ichiban_last_one_or_double_chance_price_should_be_zero"], 1)


if __name__ == "__main__":
    unittest.main()
