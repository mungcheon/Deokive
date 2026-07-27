from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import catalog_quality_report as quality


class CatalogQualityReportIchibanNamingTests(unittest.TestCase):
    def test_prize_rank_display_name_has_no_naming_issue(self) -> None:
        row = {
            "name_ko": "一番くじ Demo / B賞 / 石仮面ぬいぐるみ / 기타",
            "character_name": "기타",
            "sub_series": "B賞",
        }

        self.assertIsNone(quality._ichiban_naming_issue(row))

    def test_classified_non_prize_related_label_has_no_naming_issue(self) -> None:
        row = {
            "name_ko": "一番くじ Demo / 関連商品 / 菓子商品 Demo / 기타",
            "character_name": "기타",
            "sub_series": "関連商品",
        }

        self.assertIsNone(quality._ichiban_naming_issue(row))

    def test_unclassified_non_prize_related_label_still_needs_review(self) -> None:
        row = {
            "name_ko": "一番くじ Demo / 関連商品 / 菓子商品 Demo / 기타",
            "character_name": "기타",
            "sub_series": "",
        }

        self.assertEqual(
            quality._ichiban_naming_issue(row),
            "non_prize_or_related_item_needs_classification",
        )


if __name__ == "__main__":
    unittest.main()
