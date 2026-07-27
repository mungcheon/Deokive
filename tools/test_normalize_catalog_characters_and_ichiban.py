from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.normalize_catalog_characters_and_ichiban import (  # noqa: E402
    _ichiban_display_name,
    _normalize_ichiban_direct_character_rules,
    _normalize_frieren_aliases,
    _normalize_last_one_prices,
)


class NormalizeCatalogCharactersAndIchibanTest(unittest.TestCase):
    def test_normalizes_frieren_aliases_only_inside_frieren_scope(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "OSHI WORKS Fern",
                "name_ja": "OSHI WORKS フェルン",
                "character_name": "Pern",
                "affiliation": "장송의 프리렌",
            },
            {
                "catalog_index": 2,
                "name_ko": "프렌즈 펀치 키링",
                "character_name": "펀",
                "affiliation": "치이카와",
            },
        ]

        changes = _normalize_frieren_aliases(rows, write=True)

        self.assertEqual(len(changes), 1)
        self.assertEqual(rows[0]["name_ko"], "OSHI WORKS 페른")
        self.assertEqual(rows[0]["character_name"], "페른")
        self.assertEqual(rows[0]["affiliation"], "장송의 프리렌")
        self.assertEqual(rows[1]["name_ko"], "프렌즈 펀치 키링")
        self.assertEqual(rows[1]["character_name"], "펀")

    def test_ichiban_display_name_uses_release_tier_item_and_character(self) -> None:
        row = {
            "series_name": "一番くじ 葬送のフリーレン",
            "sub_series": "C賞",
            "name_ja": "C賞 ちょこのっこフィギュア フェルン",
            "character_name": "페른",
        }

        self.assertEqual(
            _ichiban_display_name(row),
            "一番くじ 葬送のフリーレン / C賞 / ちょこのっこフィギュア フェルン / 페른",
        )

    def test_last_one_and_double_chance_prices_are_zero(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "series_name": "一番くじ 葬送のフリーレン",
                "sub_series": "ラストワン賞",
                "name_ja": "ラストワン賞 フリーレン アートスケールフィギュア",
                "official_price_jpy": 850,
            },
            {
                "catalog_index": 2,
                "series_name": "一番くじ 葬送のフリーレン",
                "sub_series": "A賞",
                "name_ja": "A賞 フリーレン フィギュア",
                "official_price_jpy": 850,
            },
        ]

        changes = _normalize_last_one_prices(rows, write=True)

        self.assertEqual(len(changes), 1)
        self.assertEqual(rows[0]["official_price_jpy"], 0)
        self.assertEqual(rows[1]["official_price_jpy"], 850)

    def test_direct_character_rules_skip_vs_and_absorption_forms(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "series_name": "一番くじ ドラゴンボール",
                "sub_series": "C賞",
                "name_ja": "C賞 ベジータVSセル Revible Moment",
                "character_name": "기타",
                "affiliation": "드래곤볼",
                "source_url": "https://1kuji.com/products/db-test",
            },
            {
                "catalog_index": 2,
                "series_name": "一番くじ ドラゴンボール",
                "sub_series": "D賞",
                "name_ja": "D賞 魔人ブウ：孫悟飯吸収 MASTERLISE",
                "character_name": "기타",
                "affiliation": "드래곤볼",
                "source_url": "https://1kuji.com/products/db-test",
            },
            {
                "catalog_index": 3,
                "series_name": "一番くじ ドラゴンボール",
                "sub_series": "D賞",
                "name_ja": "D賞 ザマス（孫悟空） フィギュア",
                "character_name": "기타",
                "affiliation": "드래곤볼",
                "source_url": "https://1kuji.com/products/db-test",
            },
            {
                "catalog_index": 4,
                "series_name": "一番くじ ドラゴンボール",
                "sub_series": "A賞",
                "name_ja": "A賞 孫悟空 MASTERLISE",
                "character_name": "기타",
                "affiliation": "드래곤볼",
                "source_url": "https://1kuji.com/products/db-test",
            },
        ]

        changes = _normalize_ichiban_direct_character_rules(rows, write=True)

        self.assertEqual([change["catalog_index"] for change in changes], [4])
        self.assertEqual(rows[0]["character_name"], "기타")
        self.assertEqual(rows[1]["character_name"], "기타")
        self.assertEqual(rows[2]["character_name"], "기타")
        self.assertEqual(rows[3]["character_name"], "손오공")


if __name__ == "__main__":
    unittest.main()
