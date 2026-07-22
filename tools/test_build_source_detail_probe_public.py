from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_detail_probe_public as probe


class BuildSourceDetailProbePublicTest(unittest.TestCase):
    def test_build_report_summarizes_existing_candidate_reports_without_auto_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_source_detail_candidates_sample.json"
            path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "processed_rows": 3,
                            "scanned_rows": 3,
                            "result_rows": 2,
                            "failure_count": 1,
                            "exact_candidate_rows": 0,
                            "candidate_review_rows": 1,
                            "provider_temporary_unavailable_stores": [["Movic", 1]],
                            "status_counts": [["candidate_review_needed", 1], ["no_candidates", 1]],
                        },
                        "results": [
                            {
                                "row_index": 7,
                                "source_store": "Animate",
                                "name_ko": "Badge",
                                "status": "candidate_review_needed",
                                "candidate_count": 1,
                                "top_candidates": [
                                    {
                                        "candidate_source_url": "https://www.animate-onlineshop.jp/pn/test/pd/1/",
                                        "candidate_title": "Badge candidate",
                                        "candidate_image_url": "https://tc-animate.techorus-cdn.com/a.jpg",
                                        "score": 0.8,
                                        "safe_source_image_pair": True,
                                    }
                                ],
                            },
                            {
                                "row_index": 8,
                                "source_store": "Animate",
                                "name_ko": "Nope",
                                "status": "no_candidates",
                                "candidate_count": 0,
                            },
                        ],
                        "failures": [
                            {
                                "row_index": 9,
                                "source_store": "Movic",
                                "error": "provider waiting room or temporary traffic block",
                                "provider_temporary_unavailable": True,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = probe.build_report([path], generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["report_count"], 1)
        self.assertEqual(report["summary"]["candidate_review_rows"], 1)
        self.assertEqual(report["summary"]["published_candidate_rows"], 1)
        self.assertEqual(report["summary"]["candidate_yield"], 0.3333)
        self.assertEqual(report["summary"]["provider_temporary_unavailable_stores"], [["Movic", 1]])
        self.assertEqual(
            report["summary"]["store_bottleneck_counts"],
            [["fetch_or_rate_limit_failures", 1], ["candidate_review_available", 1]],
        )
        self.assertEqual(report["review_candidates"][0]["catalog_index"], 7)
        self.assertFalse(report["review_candidates"][0]["auto_apply_enabled"])
        self.assertEqual(report["candidate_rows_by_store"], [{"source_store": "Animate", "rows": 1}])
        self.assertEqual(report["store_bottlenecks"][0]["source_store"], "Movic")
        self.assertEqual(report["store_bottlenecks"][0]["provider_temporary_unavailable_failures"], 1)
        self.assertEqual(report["store_bottlenecks"][0]["bottleneck"], "fetch_or_rate_limit_failures")
        animate = next(row for row in report["store_bottlenecks"] if row["source_store"] == "Animate")
        self.assertEqual(animate["candidate_yield"], 0.5)
        self.assertEqual(animate["bottleneck"], "candidate_review_available")


if __name__ == "__main__":
    unittest.main()
