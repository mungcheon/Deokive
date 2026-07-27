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
            {
                "catalog_index": 4,
                "name_ko": "FIGURE SPIRITS KUJI \u6a5f\u52d5\u6226\u58eb\u30ac\u30f3\u30c0\u30e0 / A\u8cde / MASTERLISE MECHANICS \u30ac\u30f3\u30c0\u30e0 / \uae30\ud0c0",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                "sub_series": "A\u8cde",
                "character_name": "\uae30\ud0c0",
                "official_price_jpy": 8500,
            },
            {
                "catalog_index": 5,
                "name_ko": "\u4e00\u756a\u304f\u3058 NARUTO -THE HISTORY- / 1\u7b49 / \u8907\u88fd\u8272\u7d19 / \uae30\ud0c0",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                "sub_series": "1\u7b49",
                "character_name": "\uae30\ud0c0",
                "official_price_jpy": 520,
            },
        ]

        report = audit.build_report(rows, generated_at="2026-07-27T00:00:00Z")

        self.assertEqual(report["summary"]["status"], "pass")
        self.assertEqual(report["summary"]["ichiban_rows"], 4)
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
        self.assertEqual(reasons["fern_korean_name_should_be_peoreun"], 1)
        self.assertEqual(reasons["fern_japanese_name_character_mismatch"], 1)
        self.assertEqual(reasons["ichiban_name_missing_release_prize_item_character_parts"], 1)
        self.assertEqual(reasons["ichiban_last_one_or_double_chance_price_should_be_zero"], 1)

    def test_report_flags_frieren_aliases_and_non_exact_ichiban_separator(self) -> None:
        rows = [
            {
                "catalog_index": 7,
                "name_ko": "\ud504\ub80c \uad7f\uc988",
                "character_name": "\ud504\ub80c",
                "affiliation": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c",
            },
            {
                "catalog_index": 8,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u3061\u3044\u304b\u308f/A\u8cde/\u3061\u3044\u304b\u308f \u306c\u3044\u3050\u308b\u307f/\uce58\uc774\uce74\uc640",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                "sub_series": "A\u8cde",
                "character_name": "\uce58\uc774\uce74\uc640",
                "official_price_jpy": 750,
            },
        ]

        report = audit.build_report(rows, generated_at="2026-07-27T00:00:00Z")
        reasons = dict(report["summary"]["by_reason"])

        self.assertEqual(report["summary"]["status"], "needs_review")
        self.assertEqual(reasons["fern_korean_name_should_be_peoreun"], 1)
        self.assertEqual(reasons["ichiban_name_missing_release_prize_item_character_parts"], 1)

    def test_report_queues_ichiban_exact_display_duplicates_without_blocking(self) -> None:
        rows = [
            {
                "catalog_index": 10,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u9b3c\u6ec5\u306e\u5203 / A\u8cde / \u7ac8\u9580\u70ad\u6cbb\u90ce \u30d5\u30a3\u30ae\u30e5\u30a2 / \uce74\ub9c8\ub3c4 \ud0c4\uc9c0\ub85c",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                "source_url": "https://1kuji.com/products/kimetsu",
                "sub_series": "A\u8cde",
                "character_name": "\uce74\ub9c8\ub3c4 \ud0c4\uc9c0\ub85c",
                "official_price_jpy": 680,
            },
            {
                "catalog_index": 11,
                "name_ko": "\u4e00\u756a\u304f\u3058 \u9b3c\u6ec5\u306e\u5203 / A\u8cde / \u7ac8\u9580\u70ad\u6cbb\u90ce \u30d5\u30a3\u30ae\u30e5\u30a2 / \uce74\ub9c8\ub3c4 \ud0c4\uc9c0\ub85c",
                "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                "source_url": "https://1kuji.com/products/kimetsu2",
                "sub_series": "A\u8cde",
                "character_name": "\uce74\ub9c8\ub3c4 \ud0c4\uc9c0\ub85c",
                "official_price_jpy": 680,
            },
        ]

        report = audit.build_report(rows, generated_at="2026-07-27T00:00:00Z")

        self.assertEqual(report["summary"]["status"], "pass")
        self.assertEqual(report["summary"]["total_issue_rows"], 0)
        self.assertEqual(report["summary"]["ichiban_exact_display_duplicate_review_groups"], 1)
        self.assertEqual(report["summary"]["ichiban_exact_display_duplicate_review_rows"], 2)
        self.assertEqual(
            report["ichiban_exact_display_duplicate_review"][0]["catalog_indexes"],
            [10, 11],
        )
        self.assertEqual(
            report["ichiban_exact_display_duplicate_review"][0]["review_lane"],
            "same_slug_family_reissue_review",
        )
        self.assertEqual(
            report["summary"]["ichiban_exact_display_duplicate_review_by_lane"],
            [["same_slug_family_reissue_review", 1]],
        )

    def test_duplicate_review_classifies_same_source_and_cross_campaign_groups(self) -> None:
        base = {
            "name_ko": "\u4e00\u756a\u304f\u3058 TEST / A\u8cde / \u30d5\u30a3\u30ae\u30e5\u30a2 / \uae30\ud0c0",
            "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
            "sub_series": "A\u8cde",
            "character_name": "\uae30\ud0c0",
            "official_price_jpy": 700,
            "image_url": "https://assets.1kuji.com/a.jpg",
            "local_image_path": "assets/catalog_images/a.webp",
        }
        same_source_rows = [
            {**base, "catalog_index": 20, "source_url": "https://1kuji.com/products/test"},
            {**base, "catalog_index": 21, "source_url": "https://1kuji.com/products/test"},
        ]
        cross_campaign_rows = [
            {
                **base,
                "catalog_index": 30,
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST2 / A\u8cde / \u30d5\u30a3\u30ae\u30e5\u30a2 / \uae30\ud0c0",
                "source_url": "https://1kuji.com/products/alpha",
            },
            {
                **base,
                "catalog_index": 31,
                "name_ko": "\u4e00\u756a\u304f\u3058 TEST2 / A\u8cde / \u30d5\u30a3\u30ae\u30e5\u30a2 / \uae30\ud0c0",
                "source_url": "https://1kuji.com/products/beta",
            },
        ]

        report = audit.build_report(same_source_rows + cross_campaign_rows, generated_at="2026-07-27T00:00:00Z")
        lanes = {group["catalog_indexes"][0]: group for group in report["ichiban_exact_display_duplicate_review"]}

        self.assertEqual(lanes[20]["review_lane"], "same_source_url_exact_duplicate_review")
        self.assertTrue(lanes[20]["same_source_url"])
        self.assertTrue(lanes[20]["same_image_url"])
        self.assertEqual(lanes[30]["review_lane"], "cross_campaign_exact_display_review")
        self.assertFalse(lanes[30]["same_slug_family"])
        self.assertEqual(len(lanes[20]["rows"]), 2)


if __name__ == "__main__":
    unittest.main()
