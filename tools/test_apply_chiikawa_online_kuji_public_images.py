from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.apply_chiikawa_online_kuji_public_images import repair, row_matches_candidate


class ApplyChiikawaOnlineKujiPublicImagesTest(unittest.TestCase):
    def test_matches_same_tier_and_character_token(self) -> None:
        row = {"name_ja": "A賞 BIGクレープな抱っこぬいぐるみ ちいかわ"}
        candidate = {"name_ja": "A ちいかわ", "image_url": "https://example.com/a.jpg"}

        self.assertTrue(row_matches_candidate(row, candidate))

    def test_rejects_different_tier(self) -> None:
        row = {"name_ja": "B賞 クレープ屋さんなぬいぐるみS ちいかわ"}
        candidate = {"name_ja": "A ちいかわ", "image_url": "https://example.com/a.jpg"}

        self.assertFalse(row_matches_candidate(row, candidate))

    def test_repairs_only_unique_safe_match(self) -> None:
        rows = [
            {
                "catalog_index": 10,
                "name_ja": "A賞 BIGクレープな抱っこぬいぐるみ ちいかわ",
                "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/sample",
            },
            {
                "catalog_index": 11,
                "name_ja": "B賞 名前が合わない",
                "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/sample",
            },
        ]

        with patch(
            "tools.apply_chiikawa_online_kuji_public_images.extract_campaign",
            return_value=[
                {"name_ja": "A ちいかわ", "image_url": "https://example.com/a.jpg"},
                {"name_ja": "B ハチワレ", "image_url": "https://example.com/b.jpg"},
            ],
        ):
            report = repair(rows, write=True)

        self.assertEqual(report["summary"]["repaired_rows"], 1)
        self.assertEqual(report["summary"]["skipped_rows"], 1)
        self.assertEqual(rows[0]["image_url"], "https://example.com/a.jpg")
        self.assertNotIn("image_url", rows[1])


if __name__ == "__main__":
    unittest.main()
