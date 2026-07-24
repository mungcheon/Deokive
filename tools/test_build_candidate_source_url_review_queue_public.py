from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_candidate_source_url_review_queue_public as queue


class BuildCandidateSourceUrlReviewQueuePublicTest(unittest.TestCase):
    def test_build_queue_keeps_only_low_and_weak_candidate_rows(self) -> None:
        template = {
            "items": [
                {
                    "row_index": 1,
                    "catalog_index": 1,
                    "source_store": "Stellive Store",
                    "name_ko": "Target badge",
                    "category": "캔뱃지",
                    "current_source_url": "https://fanding.kr/@stellive/shop",
                    "source_url_review_lane": "low_confidence_candidate_review",
                    "candidate_status": "low_confidence_candidate",
                    "candidate_score": 0.23,
                    "source_url_review_blockers": ["candidate_score_too_low"],
                    "store_search_hints": {
                        "storefront_url": "https://fanding.kr/@stellive/shop",
                        "store_search_url": "https://stellive.fanding.kr/search?keyword=Target",
                        "site_query": "site:fanding.kr/@stellive/shop",
                    },
                    "candidate_options": [
                        {
                            "product_no": 100,
                            "title": "Related badge",
                            "source_url": "https://fanding.kr/@stellive/shop/100",
                            "image_url": "https://example.test/badge.webp",
                            "score": 0.23,
                        }
                    ],
                },
                {
                    "row_index": 2,
                    "catalog_index": 2,
                    "source_store": "Stellive Store",
                    "name_ko": "Exact-ish stand",
                    "category": "아크릴 스탠드",
                    "source_url_review_lane": "weak_candidate_review",
                    "candidate_status": "weak_manual_review_candidate",
                    "candidate_score": 0.63,
                    "candidate_options": [],
                },
                {
                    "row_index": 3,
                    "catalog_index": 3,
                    "source_store": "Stellive Store",
                    "name_ko": "Manual item",
                    "category": "인형",
                    "source_url_review_lane": "manual_search_required",
                },
            ]
        }

        report = queue.build_queue(template, generated_at="2026-07-23T00:00:00Z")

        self.assertEqual(report["generated_at"], "2026-07-23T00:00:00Z")
        self.assertEqual(report["summary"]["candidate_review_rows"], 2)
        self.assertEqual(report["summary"]["workstream_count"], 2)
        self.assertEqual(
            report["summary"]["by_source_url_review_lane"],
            [["low_confidence_candidate_review", 1], ["weak_candidate_review", 1]],
        )
        self.assertEqual(report["summary"]["with_candidate_options"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(
            report["review_readiness"]["status"],
            "manual_candidate_review_required",
        )
        self.assertEqual(report["review_readiness"]["auto_apply_ready_rows"], 0)
        self.assertEqual(report["review_readiness"]["manual_review_rows"], 2)
        self.assertEqual(report["review_readiness"]["rows_with_candidate_options"], 1)
        self.assertEqual(report["review_readiness"]["single_candidate_option_rows"], 1)
        self.assertEqual(
            report["review_readiness"]["next_review_row"]["catalog_index"],
            1,
        )
        self.assertEqual(
            report["review_readiness"]["blocked_until"],
            "manual_exact_product_source_url_confirmation",
        )
        self.assertFalse(report["automation_policy"]["auto_apply_source_url"])
        self.assertEqual(
            report["automation_policy"]["import_tool"],
            "tools/import_confirmed_source_urls.py",
        )
        self.assertIn(
            "tools/import_confirmed_source_urls.py",
            report["instructions"][3],
        )

        item = report["items"][0]
        self.assertEqual(item["catalog_index"], 1)
        self.assertEqual(item["top_candidate"]["product_no"], 100)
        self.assertEqual(item["source_url_import_template"]["field"], "source_url")
        self.assertEqual(item["source_url_import_template"]["manual_value"], "")
        self.assertEqual(item["source_url_import_template"]["candidate_source_url"], "")
        self.assertFalse(item["source_url_import_template"]["manual_confirmed"])
        self.assertIn("candidate_score_too_low", item["review_blockers"])

    def test_empty_template_builds_empty_candidate_queue(self) -> None:
        report = queue.build_queue({"items": []})

        self.assertEqual(report["summary"]["candidate_review_rows"], 0)
        self.assertEqual(report["review_readiness"]["status"], "empty")
        self.assertEqual(report["review_readiness"]["manual_review_rows"], 0)
        self.assertEqual(report["workstreams"], [])
        self.assertEqual(report["items"], [])


if __name__ == "__main__":
    unittest.main()
