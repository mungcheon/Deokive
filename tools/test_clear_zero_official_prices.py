from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clear_zero_official_prices import clear_zero_prices


class ClearZeroOfficialPricesTests(unittest.TestCase):
    def test_clears_zero_price_only(self) -> None:
        rows = [
            {"name_ko": "Free-looking placeholder", "official_price_jpy": 0},
            {"name_ko": "Known price", "official_price_jpy": 880},
            {"name_ko": "Unknown price", "official_price_jpy": None},
            {"name_ja": "ラストワン賞 フィギュア", "official_price_jpy": 0},
            {"name_en": "Double Chance Campaign Figure", "official_price_jpy": 0},
        ]

        changes = clear_zero_prices(rows)

        self.assertEqual(len(changes), 1)
        self.assertIsNone(rows[0]["official_price_jpy"])
        self.assertEqual(rows[1]["official_price_jpy"], 880)
        self.assertIsNone(rows[2]["official_price_jpy"])
        self.assertEqual(rows[3]["official_price_jpy"], 0)
        self.assertEqual(rows[4]["official_price_jpy"], 0)
        self.assertEqual(
            changes[0]["reason"],
            "zero_is_not_a_valid_official_price_except_last_one_or_double_chance",
        )


if __name__ == "__main__":
    unittest.main()
