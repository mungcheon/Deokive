from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_confirmed_dedupe_decisions import import_decisions


def _row(catalog_index: int, **overrides):
    row = {
        "catalog_index": catalog_index,
        "name_ko": f"Goods {catalog_index}",
        "is_active": True,
    }
    row.update(overrides)
    return row


def _item(**overrides):
    item = {
        "manual_confirmed": True,
        "decision": "keep_drop_confirmed",
        "key_type": "barcode",
        "key": "123",
        "keep_catalog_index": 10,
        "drop_catalog_indexes": [11],
        "manual_note": "same sellable product",
    }
    item.update(overrides)
    return item


class ImportConfirmedDedupeDecisionsTest(unittest.TestCase):
    def test_deactivates_confirmed_drop_rows_and_keeps_winner(self) -> None:
        result = import_decisions({"items": [_item()]}, [_row(10), _row(11)])

        self.assertEqual(len(result["updated"]), 1)
        self.assertTrue(result["seed_rows"][0]["is_active"])
        self.assertFalse(result["seed_rows"][1]["is_active"])
        self.assertEqual(result["seed_rows"][1]["dedupe_keep_catalog_index"], 10)
        self.assertEqual(result["seed_rows"][1]["dedupe_manual_note"], "same sellable product")

    def test_requires_manual_confirmation(self) -> None:
        result = import_decisions({"items": [_item(manual_confirmed=False)]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_rejects_review_required_decision(self) -> None:
        result = import_decisions({"items": [_item(decision="review_required")]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "unsupported_decision")

    def test_campaign_level_review_never_deactivates_seed_rows(self) -> None:
        campaign_item = _item(
            patch_row_id="ichiban-campaign-reissue-review-001",
            campaign_work_order_id="campaign-onep6-onep8",
            decision="campaign_pair_reissue_keep_all_separate",
            recommended_decision="campaign_pair_reissue_keep_all_separate",
            evidence_url="https://1kuji.com/products/onep6",
            source_urls=[
                "https://1kuji.com/products/onep6",
                "https://1kuji.com/products/onep8",
            ],
            manual_note="official campaign pages are different waves",
        )

        result = import_decisions({"items": [campaign_item]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertTrue(result["seed_rows"][1]["is_active"])
        self.assertEqual(
            result["skipped"][0]["reason"],
            "campaign_level_review_not_importable_as_keep_drop",
        )

    def test_campaign_level_review_requires_evidence_url(self) -> None:
        campaign_item = _item(
            patch_row_id="ichiban-campaign-reissue-review-001",
            decision="campaign_pair_reissue_keep_all_separate",
            evidence_url="",
            manual_note="checked",
            source_urls=[
                "https://1kuji.com/products/onep6",
                "https://1kuji.com/products/onep8",
            ],
        )

        result = import_decisions({"items": [campaign_item]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "campaign_evidence_url_missing")

    def test_rejects_missing_keep_row(self) -> None:
        result = import_decisions({"items": [_item(keep_catalog_index=99)]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "keep_catalog_index_not_found")

    def test_rejects_keep_in_drop_list(self) -> None:
        result = import_decisions({"items": [_item(drop_catalog_indexes=[10, 11])]}, [_row(10), _row(11)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "keep_catalog_index_in_drop_list")

    def test_uses_row_position_when_catalog_index_is_missing(self) -> None:
        result = import_decisions(
            {"items": [_item(keep_catalog_index=0, drop_catalog_indexes=[1])]},
            [{"name_ko": "Keep"}, {"name_ko": "Drop"}],
        )

        self.assertEqual(len(result["updated"]), 1)
        self.assertFalse(result["seed_rows"][1]["is_active"])


if __name__ == "__main__":
    unittest.main()
