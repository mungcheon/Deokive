from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_remaining_image_enrichment as audit


class RemainingImageEnrichmentAuditTests(unittest.TestCase):
    def test_provider_blockers_include_smoke_matrix_and_candidate_review_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / "seed.json"
            queue = root / "queue.json"
            smoke = root / "smoke.json"
            candidates = root / "candidates.json"

            seed.write_text(
                json.dumps(
                    [
                        {"name_ko": "A", "source_store": "Animate", "image_url": ""},
                        {"name_ko": "B", "source_store": "Ensky", "image_url": ""},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            queue.write_text(
                json.dumps(
                    {
                        "queue": [
                            {"name_ko": "A", "source_store": "Animate", "strategy": "official_search"},
                            {"name_ko": "B", "source_store": "Ensky", "strategy": "manual_review"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            smoke.write_text(
                json.dumps(
                    {
                        "rows": [
                            {
                                "source_store": "Animate",
                                "latest_processed_rows": 20,
                                "latest_image_filled": 0,
                                "latest_current_image_filled": 0,
                                "latest_image_fill_rate": 0.0,
                                "recommendation": "Improve parser.",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            candidates.write_text(
                json.dumps(
                    {
                        "summary": {
                            "candidate_files": 3,
                            "input_items": 10,
                            "preflight_passed_items": 2,
                            "ready_items": 0,
                            "fallback_candidate_rows": 3,
                            "rejected_items": 10,
                            "rejected_reasons": [
                                ["image_already_present", 6],
                                ["current_name_mismatch", 4],
                            ],
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = audit.build(seed, queue, smoke, [candidates])

        self.assertEqual(payload["provider_candidate_items"], 1)
        self.assertEqual(payload["manual_or_blocked_items"], 1)
        self.assertEqual(payload["provider_blockers"][0]["source_store"], "Animate")
        self.assertEqual(payload["provider_blockers"][0]["recommendation"], "Improve parser.")
        self.assertEqual(payload["provider_blockers"][0]["latest_processed_rows"], 20)
        self.assertEqual(payload["candidate_reviews"]["ready_items"], 0)
        self.assertEqual(payload["candidate_reviews"]["preflight_passed_items"], 2)
        self.assertEqual(payload["candidate_reviews"]["candidate_items"], 3)
        self.assertEqual(payload["candidate_reviews"]["totals"]["fallback_candidate_rows"], 3)
        self.assertEqual(payload["candidate_reviews"]["totals"]["input_items"], 10)
        self.assertEqual(payload["candidate_reviews"]["rejected_reasons"][0], ("image_already_present", 6))

    def test_public_catalog_items_shape_reports_unqueued_missing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "catalog_public.json"
            queue = root / "queue.json"
            smoke = root / "smoke.json"

            catalog.write_text(
                json.dumps(
                    {
                        "items": [
                            {"catalog_index": 10, "name_ko": "Queued", "image_url": ""},
                            {"catalog_index": 11, "name_ko": "Unqueued", "image_url": ""},
                            {"catalog_index": 12, "name_ko": "Done", "image_url": "https://example.test/a.jpg"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            queue.write_text(
                json.dumps(
                    {
                        "queue": [
                            {
                                "row_index": 0,
                                "catalog_index": 10,
                                "name_ko": "Queued",
                                "source_store": "Store",
                                "strategy": "official_search",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            smoke.write_text(json.dumps({"rows": []}), encoding="utf-8")

            payload = audit.build(catalog, queue, smoke, [])

        self.assertEqual(payload["rows"], 3)
        self.assertEqual(payload["missing_images"], 2)
        self.assertEqual(payload["queued_missing_image_rows"], 1)
        self.assertEqual(payload["unqueued_missing_image_rows"], 1)
        self.assertEqual(payload["unqueued_missing_image_samples"][0]["name_ko"], "Unqueued")


if __name__ == "__main__":
    unittest.main()
