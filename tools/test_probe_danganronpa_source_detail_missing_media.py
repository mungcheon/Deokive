from __future__ import annotations

import unittest
from unittest.mock import patch

import probe_danganronpa_source_detail_missing_media as probe


class ProbeDanganronpaSourceDetailMissingMediaTest(unittest.TestCase):
    def test_build_report_wraps_source_detail_candidates_without_auto_apply(self) -> None:
        rows = [
            {
                "catalog_index": 1700,
                "name_ko": "\ub2e8\uac04\ub860\ud30c \uba54\ud0c8\ub9ad \uce94\ubc43\uc9c0 \ubaa8\ub178\ucfe0\ub9c8",
                "name_ja": "\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1 \u30e1\u30bf\u30ea\u30c3\u30af\u7f36\u30d0\u30c3\u30b8 \u30e2\u30ce\u30af\u30de",
                "source_store": "Movic",
                "source_kind": "official_manufacturer",
                "category": "\uce94\ubc43\uc9c0",
            }
        ]
        candidate_payload = {
            "summary": {
                "source_queue_rows": 1,
                "supported_provider_rows": 1,
                "unsupported_provider_rows": 0,
                "scanned_rows": 1,
                "processed_rows": 1,
                "result_rows": 1,
                "failure_count": 0,
                "status_counts": [("exact_candidate_available", 1)],
                "exact_candidate_rows": 1,
                "candidate_review_rows": 0,
                "no_relevant_candidate_rows": 0,
            },
            "results": [
                {
                    "row_index": 1700,
                    "status": "exact_candidate_available",
                    "candidate_count": 1,
                    "top_candidates": [
                        {
                            "candidate_title": "\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1 \u30e1\u30bf\u30ea\u30c3\u30af\u7f36\u30d0\u30c3\u30b8 \u30e2\u30ce\u30af\u30de",
                            "candidate_source_url": "https://www.movic.jp/shop/g/g00000/",
                            "candidate_image_url": "https://www.movic.jp/img/goods/L/00000.jpg",
                            "safe_source_image_pair": True,
                        }
                    ],
                }
            ],
            "failures": [],
        }
        with patch.object(probe.detail_candidates, "build_candidates", return_value=candidate_payload) as build:
            report = probe.build_report(rows)

        build.assert_called_once()
        self.assertEqual(report["summary"]["target_rows"], 1)
        self.assertEqual(report["summary"]["official_search_url_rows"], 1)
        self.assertEqual(report["summary"]["exact_candidate_rows"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["items"][0]["auto_apply_enabled"])
        self.assertIn("movic.jp", report["items"][0]["official_search_url"])
        self.assertEqual(report["items"][0]["recommended_action"], "manual_review_exact_candidate_before_patch")


if __name__ == "__main__":
    unittest.main()
