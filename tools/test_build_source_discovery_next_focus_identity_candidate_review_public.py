from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_identity_candidate_review_public as builder


class SourceDiscoveryNextFocusIdentityCandidateReviewTests(unittest.TestCase):
    def test_build_report_keeps_candidate_identity_review_manual_only(self):
        report = builder.build_report(
            {
                "items": [
                    {
                        "catalog_index": 1082,
                        "name_ko": "죠죠의 기묘한 모험 아크릴 스탠드",
                        "source_store": "애니메이트",
                        "category": "아크릴 스탠드",
                    },
                    {
                        "catalog_index": 1123,
                        "name_ko": "신세기 에반게리온 아크릴 스탠드",
                        "source_store": "애니메이트",
                        "category": "아크릴 스탠드",
                    },
                ]
            },
            generated_at="2026-07-24T00:00:00Z",
        )

        self.assertEqual(report["summary"]["queue_rows"], 2)
        self.assertEqual(report["summary"]["items_with_candidates"], 2)
        self.assertEqual(report["summary"]["candidate_rows"], 5)
        self.assertEqual(report["summary"]["manual_confirmed_rows"], 0)
        self.assertIs(report["summary"]["auto_apply_enabled"], False)
        self.assertIs(report["automation_policy"]["auto_apply_source_url"], False)
        self.assertIs(report["automation_policy"]["requires_manual_review"], True)
        self.assertTrue(all(not item["manual_confirmed"] for item in report["items"]))
        self.assertTrue(all(not item["auto_apply_enabled"] for item in report["items"]))


if __name__ == "__main__":
    unittest.main()
