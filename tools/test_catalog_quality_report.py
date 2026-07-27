from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import catalog_quality_report as quality


class CatalogQualityReportTests(unittest.TestCase):
    def test_load_catalog_rows_accepts_public_catalog_object(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog_public.json"
            path.write_text(
                json.dumps({"items": [{"name_ko": "A"}, {"name_ko": "B"}]}),
                encoding="utf-8",
            )

            rows = quality.load_catalog_rows(path)

        self.assertEqual([row["name_ko"] for row in rows], ["A", "B"])

    def test_default_input_uses_public_catalog_for_single_db_layout(self) -> None:
        self.assertEqual(quality.DEFAULT_INPUT.as_posix().split("/")[-2:], ["data", "catalog_public.json"])

    def test_ichiban_summary_tracks_campaign_gaps_duplicates_and_zero_price_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            campaign_path = Path(temp) / "ichiban_kuji_campaigns.json"
            campaign_path.write_text(
                json.dumps(
                    [
                        {"url": "https://1kuji.com/products/a"},
                        {"url": "https://1kuji.com/products/missing"},
                    ]
                ),
                encoding="utf-8",
            )
            rows = [
                {
                    "catalog_index": 1,
                    "source_store": "이치방쿠지",
                    "source_url": "https://1kuji.com/products/a",
                    "name_ko": "一番くじ A / A賞 / Prize / Character",
                    "official_price_jpy": 790,
                },
                {
                    "catalog_index": 2,
                    "source_store": "이치방쿠지",
                    "source_url": "https://1kuji.com/products/b",
                    "name_ko": "一番くじ A / A賞 / Prize / Character",
                    "official_price_jpy": 790,
                },
                {
                    "catalog_index": 3,
                    "source_store": "이치방쿠지",
                    "source_url": "https://1kuji.com/products/a",
                    "name_ko": "一番くじ A / ラストワン賞 / ラストワン / Character",
                    "official_price_jpy": 0,
                },
                {
                    "catalog_index": 4,
                    "source_store": "이치방쿠지",
                    "source_url": "https://1kuji.com/products/a",
                    "name_ko": "一番くじ A / B賞 / Normal Zero / Character",
                    "official_price_jpy": 0,
                },
            ]

            summary = quality.build_ichiban_summary(rows, campaign_path)

        self.assertEqual(4, summary["rows"])
        self.assertEqual(2, summary["campaign_count"])
        self.assertEqual(1, summary["seeded_campaign_url_count"])
        self.assertEqual(1, summary["campaign_gap_count"])
        self.assertEqual(["https://1kuji.com/products/missing"], summary["campaign_gap_urls"])
        self.assertEqual(1, summary["exact_display_duplicate_review_groups"])
        self.assertEqual(2, summary["exact_display_duplicate_review_rows"])
        self.assertEqual(1, len(summary["exact_display_duplicate_review"]))
        self.assertEqual(1, summary["zero_price_exception_rows"])
        self.assertEqual(1, summary["zero_price_non_exception_rows"])


if __name__ == "__main__":
    unittest.main()
