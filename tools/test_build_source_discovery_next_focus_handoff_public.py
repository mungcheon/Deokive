from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_source_discovery_next_focus_handoff_public import build_handoff


class BuildSourceDiscoveryNextFocusHandoffPublicTest(unittest.TestCase):
    def test_build_handoff_compacts_next_focus_pack(self) -> None:
        report = build_handoff(
            focus_pack={
                "summary": {
                    "recommended_active_focus_pack_id": "source-discovery-focus-002",
                    "source_store": "엔스카이",
                    "target_category": "키링",
                    "focus_pack_progress_remaining_rows": 741,
                    "current_focus_resolution_status": "manual_source_search_required",
                }
            },
            fallback_queue={
                "summary": {
                    "focus_pack_id": "source-discovery-focus-002",
                    "queue_rows": 1,
                    "fallback_query_count": 6,
                    "recommended_next_action": "review exact URLs",
                },
                "items": [
                    {
                        "catalog_index": 1549,
                        "name_ko": "이타도리 유지 러버 스트랩",
                        "name_ja": "虎杖悠仁 ラバーストラップ",
                        "source_store": "엔스카이",
                        "affiliation": "주술회전",
                        "category": "키링",
                        "domain_limited_web_search_urls": ["https://example.test/search"],
                    }
                ],
            },
            detail_candidates={"summary": {"candidate_rows": 0, "exact_candidate_review_rows": 0}},
            live_probe={"summary": {"detail_candidate_rows": 0}},
            variant_backfill={"summary": {"queue_rows": 0}},
            generated_at="2026-07-26T00:00:00Z",
        )

        self.assertEqual(report["summary"]["recommended_active_focus_pack_id"], "source-discovery-focus-002")
        self.assertEqual(report["summary"]["auto_apply_ready_rows"], 0)
        self.assertEqual(len(report["items"]), 1)
        self.assertEqual(report["items"][0]["catalog_index"], 1549)
        self.assertIn("exact product/detail URL", report["items"][0]["required_evidence"][0])


if __name__ == "__main__":
    unittest.main()
