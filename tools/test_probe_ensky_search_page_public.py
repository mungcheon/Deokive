from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import probe_ensky_search_page_public as target
from enrich_catalog_images import ProductImage


class FakeProvider:
    def __init__(self) -> None:
        self.results = {
            "exact": [ProductImage(title="exact title", image_url="https://example.com/exact.jpg", source_url="https://example.com/exact")],
            "rejected": [
                ProductImage(
                    title="wrong title",
                    image_url="https://example.com/wrong.jpg",
                    source_url="https://example.com/wrong",
                )
            ],
            "empty": [],
        }

    def search_images(self, query: str) -> list[ProductImage]:
        return self.results[query]

    def match(self, query: str) -> ProductImage | None:
        if query == "exact":
            return self.results[query][0]
        return None


class ProbeEnskySearchPagePublicTests(unittest.TestCase):
    def test_build_probe_report_splits_safe_rejected_and_empty_results(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ja": "exact",
                    "name_ko": "safe",
                    "source_store": "엔스카이",
                    "affiliation": "sample",
                    "category": "sample",
                    "image_url": None,
                },
                {
                    "catalog_index": 2,
                    "name_ja": "rejected",
                    "name_ko": "rejected",
                    "source_store": "엔스카이",
                    "affiliation": "sample",
                    "category": "sample",
                    "image_url": None,
                },
                {
                    "catalog_index": 3,
                    "name_ja": "empty",
                    "name_ko": "empty",
                    "source_store": "엔스카이",
                    "affiliation": "sample",
                    "category": "sample",
                    "image_url": None,
                },
            ]
        }

        report = target.build_probe_report(catalog, FakeProvider(), generated_at="2026-01-01T00:00:00Z")
        statuses = {item["catalog_index"]: item["status"] for item in report["items"]}

        self.assertEqual(report["summary"]["processed_rows"], 3)
        self.assertEqual(report["summary"]["safe_match_rows"], 1)
        self.assertEqual(report["summary"]["rejected_search_result_rows"], 1)
        self.assertEqual(report["summary"]["no_search_result_rows"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(statuses[1], "safe_match")
        self.assertEqual(statuses[2], "rejected_search_results")
        self.assertEqual(statuses[3], "no_search_results")
        self.assertTrue(all(item["manual_review_required"] for item in report["items"]))


if __name__ == "__main__":
    unittest.main()
