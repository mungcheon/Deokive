from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.build_source_detail_candidate_summary import build_summary


class SourceDetailCandidateSummaryTests(unittest.TestCase):
    def test_aggregates_reports_and_unique_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "catalog_source_detail_candidates_a.json"
            second = root / "catalog_source_detail_candidates_b.json"
            first.write_text(
                json.dumps(
                    {
                        "summary": {
                            "processed_rows": 2,
                            "exact_candidate_rows": 1,
                            "candidate_review_rows": 0,
                            "failure_count": 0,
                        },
                        "results": [
                            {
                                "row_index": 1,
                                "source_store": "Movic",
                                "status": "exact_candidate_available",
                            },
                            {
                                "row_index": 2,
                                "source_store": "Movic",
                                "status": "no_relevant_candidate",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            second.write_text(
                json.dumps(
                    {
                        "summary": {
                            "processed_rows": 2,
                            "exact_candidate_rows": 1,
                            "candidate_review_rows": 1,
                            "failure_count": 1,
                        },
                        "results": [
                            {
                                "row_index": 1,
                                "source_store": "Movic",
                                "status": "exact_candidate",
                            },
                            {
                                "row_index": 3,
                                "source_store": "코토부키야",
                                "status": "candidate_review",
                            },
                        ],
                        "failures": [{"row_index": 4, "source_store": "코토부키야"}],
                    }
                ),
                encoding="utf-8",
            )

            payload = build_summary([first, second])

        summary = payload["summary"]
        self.assertEqual(summary["report_count"], 2)
        self.assertEqual(summary["processed_rows_reported"], 4)
        self.assertEqual(summary["unique_processed_store_row_pairs"], 4)
        self.assertEqual(summary["unique_exact_candidate_store_row_pairs"], 1)
        self.assertEqual(summary["unique_review_candidate_store_row_pairs"], 1)
        stores = {row["store"]: row for row in payload["by_store"]}
        self.assertEqual(stores["Movic"]["exact_candidate_rows"], 2)
        self.assertEqual(stores["코토부키야"]["candidate_review_rows"], 1)

    def test_tracks_rate_limits_and_skips_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / "catalog_source_detail_candidates_good.json"
            bad = root / "catalog_source_detail_candidates_bad.json"
            good.write_text(
                json.dumps(
                    {
                        "summary": {
                            "time_budget_exhausted": True,
                            "rate_limit_skipped_stores": ["엔스카이"],
                        },
                        "results": [],
                    }
                ),
                encoding="utf-8",
            )
            bad.write_text("{", encoding="utf-8")

            payload = build_summary([good, bad])

        summary = payload["summary"]
        self.assertEqual(summary["report_count"], 1)
        self.assertEqual(summary["skipped_file_count"], 1)
        self.assertEqual(summary["time_budget_exhausted_reports"], 1)
        self.assertEqual(summary["rate_limit_skipped_stores"], [["엔스카이", 1]])


if __name__ == "__main__":
    unittest.main()
