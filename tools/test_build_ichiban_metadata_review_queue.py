from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_ichiban_metadata_review_queue import build_queue


class BuildIchibanMetadataReviewQueueTest(unittest.TestCase):
    def test_builds_manual_review_item_when_no_safe_values_exist(self) -> None:
        payload = {
            "pages": [
                {
                    "url": "https://1kuji.com/products/example",
                    "title": "一番くじ Example",
                    "rows": 7,
                    "missing_release_rows": 1,
                    "missing_price_rows": 7,
                    "safe_release_date": None,
                    "safe_price_jpy": None,
                    "safe_release_reason": "double-chance dates are unsafe",
                    "safe_price_reason": "no labeled yen price",
                    "all_dates": ["2024-01-01"],
                    "double_chance_dates": ["2024-01-01"],
                    "ambiguous": True,
                }
            ]
        }

        queue = build_queue(
            payload,
            seed_rows=[
                {
                    "source_url": "https://1kuji.com/products/example",
                    "name_ko": "Example A prize",
                    "release_date": "",
                    "official_price_jpy": None,
                }
            ],
        )

        self.assertEqual(queue["summary"]["review_items"], 1)
        self.assertEqual(queue["summary"]["missing_release_rows"], 1)
        self.assertEqual(queue["summary"]["missing_price_rows"], 7)
        self.assertEqual(queue["items"][0]["workflow"], "manual_release_and_price_review")
        self.assertEqual(queue["items"][0]["date_candidates"], ["2024-01-01 (double chance)"])
        self.assertEqual(queue["items"][0]["row_sample_count"], 1)
        self.assertEqual(queue["items"][0]["row_samples"][0]["row_index"], 0)
        self.assertEqual(
            queue["items"][0]["needs_evidence"],
            ["labeled_official_release_date", "labeled_official_price_jpy"],
        )

    def test_skips_pages_with_safe_values_because_importer_handles_them(self) -> None:
        payload = {
            "pages": [
                {
                    "url": "https://1kuji.com/products/safe",
                    "missing_release_rows": 1,
                    "missing_price_rows": 0,
                    "safe_release_date": "2024-01-20",
                    "safe_price_jpy": None,
                }
            ]
        }

        queue = build_queue(payload)

        self.assertEqual(queue["summary"]["review_items"], 0)
        self.assertEqual(queue["items"], [])

    def test_keeps_price_review_when_only_release_has_safe_value(self) -> None:
        payload = {
            "pages": [
                {
                    "url": "https://1kuji.com/products/price",
                    "missing_release_rows": 0,
                    "missing_price_rows": 7,
                    "safe_release_date": "2008-06",
                    "safe_price_jpy": None,
                }
            ]
        }

        queue = build_queue(payload)

        self.assertEqual(queue["summary"]["review_items"], 1)
        self.assertEqual(queue["summary"]["missing_release_rows"], 0)
        self.assertEqual(queue["summary"]["missing_price_rows"], 7)
        self.assertEqual(queue["items"][0]["workflow"], "manual_price_review")

    def test_summary_records_custom_source_audit_path(self) -> None:
        queue = build_queue({"pages": []}, source_audit=Path("server/custom_metadata_audit.json"))

        self.assertEqual(queue["summary"]["source_audit"], "server\\custom_metadata_audit.json")

    def test_zero_price_is_not_marked_missing_in_row_sample(self) -> None:
        payload = {
            "pages": [
                {
                    "url": "https://1kuji.com/products/last-one",
                    "missing_release_rows": 1,
                    "missing_price_rows": 0,
                    "safe_release_date": None,
                    "safe_price_jpy": None,
                    "safe_release_reason": "no exact release-date label",
                    "safe_price_reason": "not needed",
                }
            ]
        }

        queue = build_queue(
            payload,
            seed_rows=[
                {
                    "source_url": "https://1kuji.com/products/last-one",
                    "name_ko": "Example - ラストワン賞 Prize",
                    "release_date": "",
                    "official_price_jpy": 0,
                }
            ],
        )

        self.assertEqual(queue["items"][0]["row_samples"][0]["missing_official_price_jpy"], False)


if __name__ == "__main__":
    unittest.main()
