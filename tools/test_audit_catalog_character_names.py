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
                "name_ko": "一番くじ 葬送のフリーレン / C賞 / ちょこのっこフィギュア フェルン / 페른",
                "series_name": "一番くじ 葬送のフリーレン",
                "sub_series": "C賞",
                "character_name": "페른",
                "official_price_jpy": 860,
            },
            {
                "catalog_index": 2,
                "name_ko": "一番くじ ちいかわ / ラストワン賞 / ラグマット / 치이카와",
                "series_name": "一番くじ ちいかわ",
                "sub_series": "ラストワン賞",
                "character_name": "치이카와",
                "official_price_jpy": 0,
            },
        ]

        result = audit(rows)

        self.assertEqual(result["summary"]["status"], "pass")
        self.assertEqual(result["summary"]["findings"], 0)

    def test_reports_character_alias_display_name_and_zero_price_violations(self) -> None:
        rows = [
            {
                "catalog_index": 3,
                "name_ko": "一番くじ 葬送のフリーレン C賞 ちょこのっこフィギュア フェルン",
                "series_name": "一番くじ 葬送のフリーレン",
                "sub_series": "ラストワン賞",
                "character_name": "펀",
                "official_price_jpy": 860,
            }
        ]

        result = audit(rows)

        self.assertEqual(result["summary"]["status"], "needs_review")
        self.assertEqual(result["summary"]["character_alias_violations"], 1)
        self.assertEqual(result["summary"]["ichiban_display_name_violations"], 1)
        self.assertEqual(result["summary"]["zero_price_violations"], 1)

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
