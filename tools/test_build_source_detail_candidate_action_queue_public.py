from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_detail_candidate_action_queue_public as queue


class BuildSourceDetailCandidateActionQueuePublicTest(unittest.TestCase):
    def test_build_report_publishes_manual_review_templates(self) -> None:
        source_detail = {
            "review_candidates": [
                {
                    "catalog_index": 7,
                    "source_store": "Animate",
                    "name_ko": "Badge",
                    "candidate_status": "candidate_review_needed",
                    "status": "candidate_review_needed",
                    "candidate_count": 1,
                    "candidate_source_url": "https://www.animate-onlineshop.jp/pn/test/pd/1/",
                    "candidate_image_url": "https://tc-animate.techorus-cdn.com/a.jpg",
                    "candidate_title": "Badge candidate",
                    "score": 0.8,
                    "safe_source_image_pair": True,
                }
            ]
        }

        report = queue.build_report(source_detail, generated_at="2026-07-22T00:00:00Z", batch_size=10)

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["candidate_action_rows"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_true"], 0)
        self.assertEqual(report["summary"]["safe_source_image_pair_rows"], 1)
        self.assertEqual(report["summary"]["near_or_better_candidate_rows"], 1)
        self.assertEqual(report["summary"]["ambiguous_or_weaker_candidate_rows"], 0)
        self.assertEqual(report["summary"]["by_candidate_count_bucket"], [["single_candidate", 1]])
        item = report["batches"][0]["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["candidate_count_bucket"], "single_candidate")
        self.assertEqual(item["review_priority"], 20)
        self.assertEqual(report["batches"][0]["safe_source_image_pair_rows"], 1)
        self.assertEqual(item["source_patch_template"]["field"], "source_url")
        self.assertEqual(item["image_patch_template"]["field"], "image_url")
        self.assertFalse(item["source_patch_template"]["manual_confirmed"])
        self.assertIn("exact product", item["acceptance_criteria"][1])


if __name__ == "__main__":
    unittest.main()
