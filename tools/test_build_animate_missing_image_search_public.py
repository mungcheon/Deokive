from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_animate_missing_image_search_public as target


class AnimateMissingImageSearchPublicTests(unittest.TestCase):
    def test_build_report_keeps_search_rows_review_only(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "sample",
                    "name_ja": "sample ja",
                    "source_store": target.ANIMATE_STORE,
                    "category": "badge",
                    "affiliation": "series",
                    "image_url": None,
                },
                {
                    "catalog_index": 2,
                    "name_ko": "has image",
                    "source_store": target.ANIMATE_STORE,
                    "image_url": "https://example.com/2.jpg",
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": target.ANIMATE_STORE,
                    "query": "sample ja",
                    "search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=sample",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                }
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["missing_animate_image_rows"], 1)
        self.assertEqual(report["summary"]["matched_queue_rows"], 1)
        self.assertEqual(report["summary"]["official_search_url_rows"], 1)
        self.assertEqual(report["summary"]["reviewable_search_url_rows"], 1)
        self.assertEqual(report["summary"]["source_research_required_rows"], 0)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])
        self.assertEqual(report["items"][0]["import_template"]["blocked_until"], "exact_animate_product_page_confirmed")
        self.assertTrue(report["items"][0]["manual_review_required"])
        self.assertEqual(report["items"][0]["candidate_review_risk"], "medium")
        self.assertEqual(report["items"][0]["research_status"], "reviewable_search_url")
        self.assertIn("by_candidate_review_risk", report["breakdowns"])
        self.assertIn("by_research_status", report["breakdowns"])

    def test_marks_hangul_or_blind_pack_queries_as_high_risk(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 10,
                    "name_ko": "\uc6d0\ud53c\uc2a4 \uce94\ubc43\uc9c0 (\ub79c\ub364 1\ud329)",
                    "name_ja": None,
                    "source_store": target.ANIMATE_STORE,
                    "category": "\uce94\ubc43\uc9c0",
                    "affiliation": "\uc6d0\ud53c\uc2a4",
                    "image_url": None,
                }
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 10,
                    "source_store": target.ANIMATE_STORE,
                    "query": "\uc6d0\ud53c\uc2a4 \uce94\ubc43\uc9c0 \ub79c\ub364",
                    "search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=test",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                }
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["items"][0]["candidate_review_risk"], "high")
        self.assertEqual(report["items"][0]["research_status"], "needs_official_language_name")
        self.assertIn("missing_official_language_name", report["items"][0]["candidate_review_reasons"])
        self.assertIn("hangul_search_query_needs_japanese_rewrite", report["items"][0]["candidate_review_reasons"])
        self.assertEqual(report["breakdowns"]["by_candidate_review_risk"][0]["rows"], 1)
        self.assertEqual(report["summary"]["source_research_required_rows"], 1)
        self.assertEqual(report["source_research_required"]["row_count"], 1)
        self.assertEqual(
            report["source_research_required"]["items"][0]["research_next_action"],
            "add_japanese_or_official_product_name_before_search",
        )

    def test_marks_hangul_query_with_official_name_as_query_rewrite(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 20,
                    "name_ko": "sample",
                    "name_ja": "\u864e\u6756\u60a0\u4ec1 \u30a2\u30af\u30ea\u30eb\u30b9\u30bf\u30f3\u30c9",
                    "source_store": target.ANIMATE_STORE,
                    "category": "\uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                    "affiliation": "\uc8fc\uc220\ud68c\uc804",
                    "image_url": None,
                }
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 20,
                    "source_store": target.ANIMATE_STORE,
                    "query": "\uc8fc\uc220\ud68c\uc804 \uc544\ud06c\ub9b4",
                    "search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=test",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                }
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["items"][0]["research_status"], "needs_query_rewrite")
        self.assertEqual(report["source_research_required"]["row_count"], 1)


if __name__ == "__main__":
    unittest.main()
