from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_stellive_fanding_candidates_public as target


class StelliveFandingCandidatesPublicTests(unittest.TestCase):
    def test_build_report_keeps_candidates_review_only(self) -> None:
        fake_summary = {
            "products_fetched": 2,
            "candidate_rows": 1,
            "review_candidate_rows": 1,
            "missing_image_candidate_rows": 1,
            "missing_image_review_candidate_rows": 1,
        }
        fake_queue = [
            {
                "row_index": 10,
                "name_ko": "sample",
                "missing_image_url": True,
                "candidate_status": "weak_manual_review_candidate",
                "candidate_review_lane": "weak_candidate_review",
                "top_candidates": [
                    {
                        "source_url": "https://fanding.kr/@stellive/shop/1",
                        "image_url": "https://example.com/1.webp",
                        "score": 0.8,
                    }
                ],
            }
        ]
        with patch.object(target.fanding, "enrich", return_value=(0, [], [], fake_summary, fake_queue)):
            report = target.build_report({"items": [{"catalog_index": 10}]}, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["queue_rows"], 1)
        self.assertEqual(report["summary"]["missing_image_queue_rows"], 1)
        self.assertEqual(report["summary"]["missing_image_review_queue_rows"], 1)
        self.assertEqual(
            report["summary"]["candidate_review_lane_counts"],
            {"weak_candidate_review": 1},
        )
        self.assertEqual(
            report["summary"]["missing_image_candidate_review_lane_counts"],
            {"weak_candidate_review": 1},
        )
        self.assertEqual(
            report["summary"]["missing_image_resolution_readiness"],
            {
                "exact_source_image_ready_rows": 0,
                "manual_search_required_rows": 0,
                "candidate_review_required_rows": 1,
                "weak_candidate_review_rows": 1,
                "low_confidence_candidate_review_rows": 0,
                "blocking_reason": (
                    "No missing-image Stellive/Fanding row has a unique exact "
                    "product identity match. Confirm exact product detail pages "
                    "before importing images."
                ),
                "next_safe_step": (
                    "Resolve the 0 manual-search rows first, then review the 1 "
                    "candidate rows before image attachment."
                ),
            },
        )
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])
        self.assertEqual(len(report["missing_image_review_queue"]), 1)


if __name__ == "__main__":
    unittest.main()
