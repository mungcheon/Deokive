from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ensky_cache_candidate_action_queue_public as queue


class BuildEnskyCacheCandidateActionQueuePublicTest(unittest.TestCase):
    def test_build_report_publishes_broad_candidates_as_manual_only_actions(self) -> None:
        cache_coverage = {
            "items": [
                {
                    "catalog_index": 2,
                    "name_ko": "Badge",
                    "name_ja": "缶バッジ",
                    "source_store": "엔스카이",
                    "affiliation": "Series",
                    "category": "캔뱃지",
                    "status": "broad_cache_candidate",
                    "candidate_count": 1,
                    "top_candidates": [
                        {
                            "title": "Badge candidate",
                            "source_url": "https://www.enskyshop.com/products/detail/1",
                            "image_url": "https://www.enskyshop.com/html/upload/save_image/a.jpg",
                            "safe_exact_match": False,
                            "score": 20,
                            "matched_tokens": ["badge"],
                        }
                    ],
                },
                {
                    "catalog_index": 1,
                    "source_store": "엔스카이",
                    "status": "no_cache_candidate",
                    "candidate_count": 0,
                    "top_candidates": [],
                },
            ]
        }

        report = queue.build_report(cache_coverage, generated_at="2026-07-22T00:00:00Z", batch_size=10)

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["candidate_action_rows"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_true"], 0)
        item = report["batches"][0]["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["source_patch_template"]["field"], "source_url")
        self.assertEqual(item["image_patch_template"]["field"], "image_url")
        self.assertFalse(item["source_patch_template"]["manual_confirmed"])
        self.assertEqual(item["top_candidates"][0]["candidate_source_url"], "https://www.enskyshop.com/products/detail/1")
        self.assertIn("exact product", item["acceptance_criteria"][0])


if __name__ == "__main__":
    unittest.main()
