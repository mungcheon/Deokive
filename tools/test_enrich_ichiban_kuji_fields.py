from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enrich_ichiban_kuji_fields as enrich


class EnrichIchibanKujiFieldsTests(unittest.TestCase):
    def test_zero_price_is_present(self) -> None:
        self.assertTrue(enrich._present(0))

    def test_none_and_empty_string_are_missing(self) -> None:
        self.assertFalse(enrich._present(None))
        self.assertFalse(enrich._present(""))


if __name__ == "__main__":
    unittest.main()
