from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.audit_catalog_character_names import audit, main


class AuditCatalogCharacterNamesTest(unittest.TestCase):
    def test_passes_for_valid_ichiban_and_frieren_character_names(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3 / C\u8cde / \u63cf\u304d\u304a\u308d\u3057\u30d5\u30a7\u30eb\u30f3\u306e\u30d6\u30e9\u30f3\u30b1\u30c3\u30c8 / \ud398\ub978",
                "series_name": "\u4e00\u756a\u304f\u3058 \u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3",
                "sub_series": "C\u8cde",
                "character_name": "\ud398\ub978",
                "official_price_jpy": 860,
            },
            {
                "catalog_index": 2,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u3061\u3044\u304b\u308f / \u30e9\u30b9\u30c8\u30ef\u30f3\u8cde / \u30e9\u30b9\u30c8\u30ef\u30f3\u5546\u54c1 / \uce58\uc774\uce74\uc640",
                "series_name": "\u4e00\u756a\u304f\u3058 \u3061\u3044\u304b\u308f",
                "sub_series": "\u30e9\u30b9\u30c8\u30ef\u30f3\u8cde",
                "character_name": "\uce58\uc774\uce74\uc640",
                "official_price_jpy": 0,
            },
            {
                "catalog_index": 3,
                "name_ko": "\u4e00\u756a\u304f\u3058 NARUTO -THE HISTORY- / 1\u7b49 / \u5fcd\u5177\u30dd\u30fc\u30c1 / \uae30\ud0c0",
                "series_name": "\u4e00\u756a\u304f\u3058 NARUTO -THE HISTORY-",
                "sub_series": "1\u7b49",
                "character_name": "\uae30\ud0c0",
                "official_price_jpy": 700,
            },
            {
                "catalog_index": 4,
                "name_ko": "\u6a5f\u52d5\u6226\u58eb\u30ac\u30f3\u30c0\u30e0 30th ANNIVERSARY \u4e00\u756a\u304f\u3058 / \u95a2\u9023\u5546\u54c1 / \u95a2\u9023\u5546\u54c1 / \uae30\ud0c0",
                "series_name": "\u6a5f\u52d5\u6226\u58eb\u30ac\u30f3\u30c0\u30e0 30th ANNIVERSARY \u4e00\u756a\u304f\u3058",
                "sub_series": "\u95a2\u9023\u5546\u54c1",
                "character_name": "\uae30\ud0c0",
                "official_price_jpy": None,
            },
            {
                "catalog_index": 5,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u30ef\u30f3\u30d4\u30fc\u30b9 / \u306c\u3044\u3050\u308b\u307f / \u30c1\u30e7\u30c3\u30d1\u30fc\u306c\u3044\u3050\u308b\u307f / \ud1a0\ub2c8\ud1a0\ub2c8 \ucd78\ud30c",
                "series_name": "\u4e00\u756a\u304f\u3058 \u30ef\u30f3\u30d4\u30fc\u30b9",
                "sub_series": "\u306c\u3044\u3050\u308b\u307f",
                "character_name": "\ud1a0\ub2c8\ud1a0\ub2c8 \ucd78\ud30c",
                "official_price_jpy": None,
            },
        ]

        result = audit(rows)

        self.assertEqual(result["summary"]["status"], "pass")
        self.assertEqual(result["summary"]["findings"], 0)
        self.assertEqual(result["summary"]["ichiban_product_character_violations"], 0)
        self.assertEqual(result["summary"]["ichiban_display_character_mismatches"], 0)

    def test_reports_character_alias_display_name_and_zero_price_violations(self) -> None:
        rows = [
            {
                "catalog_index": 3,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3 C\u8cde \ud6c4\ub9ac\ub80c \ud38c \ube14\ub7ad\ud0b7",
                "series_name": "\u4e00\u756a\u304f\u3058 \u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3",
                "sub_series": "\u30e9\u30b9\u30c8\u30ef\u30f3\u8cde",
                "character_name": "\ud38c",
                "affiliation": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
                "official_price_jpy": 860,
            }
        ]

        result = audit(rows)

        self.assertEqual(result["summary"]["status"], "needs_review")
        self.assertEqual(result["summary"]["character_alias_violations"], 3)
        self.assertEqual(result["summary"]["ichiban_display_name_violations"], 1)
        self.assertEqual(result["summary"]["ichiban_display_character_mismatches"], 0)
        self.assertEqual(result["summary"]["ichiban_product_character_violations"], 1)
        self.assertEqual(result["summary"]["zero_price_violations"], 1)

    def test_reports_frieren_pun_typo_and_display_character_mismatch(self) -> None:
        rows = [
            {
                "catalog_index": 4,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3 / C\u8cde / \u63cf\u304d\u304a\u308d\u3057\u30d5\u30a7\u30eb\u30f3\u306e\u30d6\u30e9\u30f3\u30b1\u30c3\u30c8 / \ud38c",
                "series_name": "\u4e00\u756a\u304f\u3058 \u846c\u9001\u306e\u30d5\u30ea\u30fc\u30ec\u30f3",
                "sub_series": "C\u8cde",
                "character_name": "\ud398\ub978",
                "affiliation": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
                "official_price_jpy": 860,
            },
            {
                "catalog_index": 5,
                "name_ko": "\ud380 \uad7f\uc988",
                "character_name": "\ud380",
                "affiliation": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
            },
        ]

        result = audit(rows)

        self.assertEqual(result["summary"]["status"], "needs_review")
        self.assertEqual(result["summary"]["character_alias_violations"], 3)
        self.assertEqual(result["summary"]["ichiban_display_character_mismatches"], 1)
        self.assertEqual(
            result["ichiban_display_character_mismatches"][0]["display_character_name"],
            "\ud38c",
        )

    def test_reports_ichiban_product_character_mismatch_with_longest_token_priority(self) -> None:
        rows = [
            {
                "catalog_index": 20,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u30ef\u30f3\u30d4\u30fc\u30b9 / C\u8cde / \u30c1\u30e7\u30c3\u30d1\u30fc\u30d5\u30a3\u30ae\u30e5\u30a2 / \ud2b8\ub77c\ud314\uac00 \ub85c",
                "series_name": "\u4e00\u756a\u304f\u3058 \u30ef\u30f3\u30d4\u30fc\u30b9",
                "sub_series": "C\u8cde",
                "character_name": "\ud2b8\ub77c\ud314\uac00 \ub85c",
                "official_price_jpy": 600,
            }
        ]

        result = audit(rows)

        self.assertEqual(result["summary"]["status"], "needs_review")
        self.assertEqual(result["summary"]["ichiban_product_character_violations"], 1)
        self.assertEqual(
            result["ichiban_product_character_violations"][0]["expected"],
            "\ud1a0\ub2c8\ud1a0\ub2c8 \ucd78\ud30c",
        )

    def test_katakana_character_tokens_do_not_match_inside_longer_words(self) -> None:
        rows = [
            {
                "catalog_index": 21,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u30ef\u30f3\u30d4\u30fc\u30b9 / C\u8cde / \u30da\u30ed\u30fc\u30ca\u30d5\u30a3\u30ae\u30e5\u30a2 / \ud398\ub85c\ub098",
                "series_name": "\u4e00\u756a\u304f\u3058 \u30ef\u30f3\u30d4\u30fc\u30b9",
                "sub_series": "C\u8cde",
                "character_name": "\ud398\ub85c\ub098",
                "official_price_jpy": 600,
            }
        ]

        result = audit(rows)

        self.assertEqual(result["summary"]["status"], "pass")
        self.assertEqual(result["summary"]["ichiban_product_character_violations"], 0)
        self.assertEqual(
            result["summary"]["ichiban_multi_character_product_review_candidates"],
            0,
        )

    def test_reports_multi_character_ichiban_product_review_candidates(self) -> None:
        rows = [
            {
                "catalog_index": 22,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u9b3c\u6ec5\u306e\u5203 / A\u8cde / \u7ac8\u9580\u70ad\u6cbb\u90ce&\u7ac8\u9580\u79b0\u8c46\u5b50 ArtScale Memoria / \uae30\ud0c0",
                "series_name": "\u4e00\u756a\u304f\u3058 \u9b3c\u6ec5\u306e\u5203",
                "sub_series": "A\u8cde",
                "character_name": "\uae30\ud0c0",
                "official_price_jpy": 790,
            }
        ]

        result = audit(rows)

        self.assertEqual(result["summary"]["status"], "pass")
        self.assertEqual(
            result["summary"]["ichiban_multi_character_product_review_candidates"],
            1,
        )
        self.assertEqual(
            result["ichiban_multi_character_product_review_candidates"][0]["matched_characters"],
            ["\uce74\ub9c8\ub3c4 \ub124\uc988\ucf54", "\uce74\ub9c8\ub3c4 \ud0c4\uc9c0\ub85c"],
        )

    def test_character_alias_rules_are_scoped_to_frieren(self) -> None:
        rows = [
            {
                "catalog_index": 10,
                "name_ko": "\ud38c \uae30\ud0c0 \uad7f\uc988",
                "character_name": "\ud38c",
                "affiliation": "\uae30\ud0c0",
            }
        ]

        result = audit(rows)

        self.assertEqual(result["summary"]["character_alias_violations"], 0)

    def test_main_only_fails_on_findings_when_requested(self) -> None:
        with mock.patch(
            "sys.argv",
            [
                "audit_catalog_character_names.py",
                "--catalog",
                str(Path(__file__).resolve().parent.parent / "data" / "catalog_public.json"),
            ],
        ):
            self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
