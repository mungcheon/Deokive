from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.normalize_catalog_characters_and_ichiban import _normalize_frieren_aliases


class NormalizeCatalogCharactersAndIchibanTest(unittest.TestCase):
    def test_normalizes_frieren_aliases_only_inside_frieren_scope(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "OSHI WORKS Fern",
                "name_ja": "OSHI WORKS フェルン",
                "character_name": "Pern",
                "affiliation": "장송의 후리렌",
            },
            {
                "catalog_index": 2,
                "name_ko": "후루츠 펀치",
                "character_name": "펀",
                "affiliation": "치이카와",
            },
        ]

        changes = _normalize_frieren_aliases(rows, write=True)

        self.assertEqual(len(changes), 1)
        self.assertEqual(rows[0]["name_ko"], "OSHI WORKS 페른")
        self.assertEqual(rows[0]["character_name"], "페른")
        self.assertEqual(rows[0]["affiliation"], "장송의 프리렌")
        self.assertEqual(rows[1]["name_ko"], "후루츠 펀치")
        self.assertEqual(rows[1]["character_name"], "펀")


if __name__ == "__main__":
    unittest.main()
