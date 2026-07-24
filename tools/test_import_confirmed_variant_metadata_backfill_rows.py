from __future__ import annotations

import unittest

import tools.import_confirmed_variant_metadata_backfill_rows as importer


class ImportConfirmedVariantMetadataBackfillRowsTest(unittest.TestCase):
    def test_skips_unconfirmed_template(self) -> None:
        result = importer.import_rows(
            {
                "items": [
                    {
                        "catalog_index": 1,
                        "metadata_backfill_template": {
                            "catalog_index": 1,
                            "manual_confirmed": False,
                            "manual_confirmed_name_ja": "商品名",
                        },
                    }
                ]
            },
            [{"catalog_index": 1, "name_ko": "테스트"}],
        )

        self.assertEqual(result["summary"]["would_update_rows"], 0)
        self.assertEqual(result["summary"]["skipped_rows"], 1)
        self.assertEqual(result["skipped_sample"][0]["reason"], "manual_confirmed_false")

    def test_blocks_confirmed_row_without_exact_evidence_url(self) -> None:
        result = importer.import_rows(
            {
                "items": [
                    {
                        "catalog_index": 1,
                        "metadata_backfill_template": {
                            "catalog_index": 1,
                            "manual_confirmed": True,
                            "manual_confirmed_name_ja": "商品名",
                            "manual_evidence_url": "https://example.com/search?q=item",
                        },
                    }
                ]
            },
            [{"catalog_index": 1, "name_ko": "테스트"}],
        )

        self.assertEqual(result["summary"]["would_update_rows"], 0)
        self.assertEqual(result["summary"]["blocked_rows"], 1)
        self.assertEqual(result["blocked_sample"][0]["reason"], "exact_evidence_url_required")

    def test_reports_dry_run_updates_for_empty_fields(self) -> None:
        result = importer.import_rows(
            {
                "items": [
                    {
                        "catalog_index": 7,
                        "name_ko": "카드캡터 체리 아크릴 스탠드",
                        "source_store": "애니메이트",
                        "metadata_backfill_template": {
                            "catalog_index": 7,
                            "manual_confirmed": True,
                            "manual_confirmed_name_ja": "カードキャプターさくら アクリルスタンド",
                            "manual_confirmed_sub_series": "クリアカード編",
                            "manual_evidence_url": "https://www.animate-onlineshop.jp/pn/sample/pd/3478244/",
                        },
                    }
                ]
            },
            [
                {
                    "catalog_index": 7,
                    "name_ko": "카드캡터 체리 아크릴 스탠드",
                    "source_store": "애니메이트",
                }
            ],
        )

        self.assertEqual(result["summary"]["would_update_rows"], 1)
        self.assertEqual(result["summary"]["updated_rows"], 0)
        self.assertEqual(result["updated"][0]["fields"]["sub_series"], "クリアカード編")

    def test_blocks_existing_value_conflict(self) -> None:
        result = importer.import_rows(
            {
                "items": [
                    {
                        "catalog_index": 9,
                        "metadata_backfill_template": {
                            "catalog_index": 9,
                            "manual_confirmed": True,
                            "manual_confirmed_category": "캘린더",
                            "manual_evidence_url": "https://www.animate-onlineshop.jp/pn/sample/pd/3480000/",
                        },
                    }
                ]
            },
            [{"catalog_index": 9, "name_ko": "세일러문", "category": "아크릴 스탠드"}],
        )

        self.assertEqual(result["summary"]["would_update_rows"], 0)
        self.assertEqual(result["summary"]["blocked_rows"], 1)
        self.assertEqual(result["blocked_sample"][0]["reason"], "existing_field_conflict")


if __name__ == "__main__":
    unittest.main()
