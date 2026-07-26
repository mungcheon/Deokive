from __future__ import annotations

import unittest

from tools.import_confirmed_reused_image_deduplication_rows import import_confirmed


def _review_item(manual_confirmed: bool = False, decision: str = "") -> dict:
    return {
        "group_index": 1,
        "confidence": "strong_manual_duplicate_candidate",
        "source_url_same": True,
        "image_same": True,
        "category_same": True,
        "character_same": True,
        "rank_same": True,
        "source_urls": ["https://online-kuji.chiikawamarket.jp/store/lottery/usagi"],
        "decision_template": {
            "manual_confirmed": manual_confirmed,
            "decision": decision,
            "suggested_keep_catalog_index": 11703,
            "suggested_drop_catalog_indexes": [660],
            "manual_keep_catalog_index": None,
            "manual_drop_catalog_indexes": [],
            "evidence_urls": ["https://online-kuji.chiikawamarket.jp/store/lottery/usagi"],
            "manual_note": "confirmed same prize",
        },
    }


class ImportConfirmedReusedImageDeduplicationRowsTest(unittest.TestCase):
    def test_unconfirmed_items_are_skipped(self) -> None:
        catalog = {
            "items": [
                {"catalog_index": 660, "name_ko": "old"},
                {"catalog_index": 11703, "name_ko": "new"},
            ]
        }

        result = import_confirmed({"items": [_review_item()]}, catalog)

        self.assertEqual(result["summary"]["updated_rows"], 0)
        self.assertEqual(result["summary"]["output_rows"], 2)
        self.assertEqual(result["summary"]["skip_reason_counts"], [["manual_confirmed_false", 1]])

    def test_confirmed_keep_one_drops_selected_rows(self) -> None:
        catalog = {
            "items": [
                {"catalog_index": 660, "name_ko": "D상: 마스코트 피자만"},
                {"catalog_index": 11703, "name_ko": "ちいかわ うさぎだらけくじ - D ピザまん"},
                {"catalog_index": 42, "name_ko": "other"},
            ]
        }

        result = import_confirmed(
            {"items": [_review_item(True, "same_sellable_product_keep_one")]},
            catalog,
        )

        self.assertEqual(result["summary"]["updated_rows"], 1)
        self.assertEqual(result["summary"]["ready_groups"], 1)
        self.assertEqual(result["summary"]["output_rows"], 2)
        remaining = [row["catalog_index"] for row in result["catalog"]["items"]]
        self.assertEqual(remaining, [11703, 42])
        self.assertEqual(result["updated"][0]["drop_catalog_index"], 660)
        self.assertEqual(result["updated"][0]["keep_catalog_index"], 11703)

    def test_identity_flags_must_all_be_true(self) -> None:
        item = _review_item(True, "same_sellable_product_keep_one")
        item["image_same"] = False
        catalog = {
            "items": [
                {"catalog_index": 660, "name_ko": "old"},
                {"catalog_index": 11703, "name_ko": "new"},
            ]
        }

        result = import_confirmed({"items": [item]}, catalog)

        self.assertEqual(result["summary"]["updated_rows"], 0)
        self.assertEqual(result["summary"]["skip_reason_counts"], [["identity_flags_not_all_true", 1]])


if __name__ == "__main__":
    unittest.main()
