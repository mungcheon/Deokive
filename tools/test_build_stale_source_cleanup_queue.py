from __future__ import annotations

import sys
import unittest
from pathlib import Path
import json
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_stale_source_cleanup_queue as stale_queue


class StaleSourceCleanupQueueTests(unittest.TestCase):
    def test_build_queue_includes_only_mismatch_rows(self):
        audit = {
            "results": [
                {
                    "source_url": "https://example.test/products/1",
                    "source_store": "Test Store",
                    "row_count": 2,
                    "live_title": "Other Product",
                    "status": "live_title_mismatch",
                    "rows": [
                        {
                            "row_index": 0,
                            "name_ko": "Seed Wrong",
                            "name_ja": "Seed Wrong JA",
                            "status": "live_title_mismatch",
                            "shared_tokens": [],
                        },
                        {
                            "row_index": 1,
                            "name_ko": "Other Product",
                            "name_ja": "Other Product",
                            "status": "title_overlap_ok",
                            "shared_tokens": ["Other"],
                        },
                    ],
                }
            ]
        }
        seed_rows = [
            {
                "catalog_index": 101,
                "name_ko": "Seed Wrong",
                "name_ja": "Seed Wrong JA",
                "source_store": "Seed Store",
                "source_url": "https://example.test/products/1",
                "image_url": "https://cdn.example.test/wrong.png",
            },
            {
                "name_ko": "Other Product",
                "name_ja": "Other Product",
                "source_store": "Seed Store",
                "source_url": "https://example.test/products/1",
                "image_url": "",
            },
        ]

        payload = stale_queue.build_queue(audit, seed_rows)

        self.assertEqual(payload["summary"]["review_rows"], 1)
        self.assertEqual(payload["summary"]["mismatch_rows"], 1)
        self.assertEqual(payload["summary"]["weak_overlap_rows"], 0)
        self.assertEqual(payload["summary"]["mismatch_urls"], 1)
        self.assertEqual(payload["items"][0]["row_index"], 0)
        self.assertEqual(payload["items"][0]["catalog_index"], 101)
        self.assertEqual(payload["items"][0]["name_ko"], "Seed Wrong")
        self.assertEqual(payload["items"][0]["current_image_url"], "https://cdn.example.test/wrong.png")
        self.assertEqual(payload["items"][0]["identity_status"], "live_title_mismatch")
        self.assertEqual(payload["items"][0]["recommended_action"], "find_exact_source_url_before_image_use")

    def test_build_queue_includes_weak_overlap_rows_as_review_only(self):
        audit = {
            "results": [
                {
                    "source_url": "https://example.test/products/weak",
                    "source_store": "Test Store",
                    "row_count": 1,
                    "live_title": "ちいかわ マシュマロ風シール",
                    "status": "weak_title_overlap",
                    "rows": [
                        {
                            "row_index": 0,
                            "name_ko": "치이카와 러버 스트랩",
                            "name_ja": "ちいかわ ラバーストラップ",
                            "status": "weak_title_overlap",
                            "shared_tokens": ["ちいかわ"],
                        }
                    ],
                }
            ]
        }
        seed_rows = [
            {
                "name_ko": "치이카와 러버 스트랩",
                "name_ja": "ちいかわ ラバーストラップ",
                "source_store": "Test Store",
                "source_url": "https://example.test/products/weak",
                "image_url": "",
            }
        ]

        payload = stale_queue.build_queue(audit, seed_rows)

        self.assertEqual(payload["summary"]["review_rows"], 1)
        self.assertEqual(payload["summary"]["mismatch_rows"], 0)
        self.assertEqual(payload["summary"]["weak_overlap_rows"], 1)
        self.assertEqual(payload["summary"]["weak_overlap_urls"], 1)
        self.assertEqual(payload["items"][0]["risk"], "weak_source_identity_overlap")
        self.assertEqual(payload["items"][0]["recommended_action"], "review_source_url_before_image_import")

    def test_build_queue_skips_stale_audit_row_indexes(self):
        audit = {
            "results": [
                {
                    "source_url": "https://example.test/products/1",
                    "source_store": "Test Store",
                    "row_count": 1,
                    "live_title": "Other Product",
                    "status": "live_title_mismatch",
                    "rows": [
                        {
                            "row_index": 0,
                            "name_ko": "Old Row Name",
                            "name_ja": "Old Row Name JA",
                            "status": "live_title_mismatch",
                            "shared_tokens": [],
                        }
                    ],
                }
            ]
        }
        seed_rows = [
            {
                "name_ko": "Current Different Row",
                "name_ja": "Current Different Row JA",
                "source_store": "Seed Store",
                "source_url": "https://example.test/products/1",
                "image_url": "",
            }
        ]

        payload = stale_queue.build_queue(audit, seed_rows)

        self.assertEqual(payload["summary"]["review_rows"], 0)
        self.assertEqual(payload["summary"]["mismatch_rows"], 0)
        self.assertEqual(payload["summary"]["skipped_rows"], 1)
        self.assertEqual(payload["summary"]["skipped_by_reason"], [("audit_row_name_mismatch", 1)])
        self.assertEqual(payload["skipped_sample"][0]["current_name_ko"], "Current Different Row")

    def test_build_queue_recovers_shifted_rows_by_name_and_source_url(self):
        audit = {
            "results": [
                {
                    "source_url": "https://example.test/products/1",
                    "source_store": "Test Store",
                    "row_count": 1,
                    "live_title": "Other Product",
                    "status": "live_title_mismatch",
                    "rows": [
                        {
                            "row_index": 0,
                            "name_ko": "Moved Row",
                            "name_ja": "Moved Row JA",
                            "status": "live_title_mismatch",
                            "shared_tokens": [],
                        }
                    ],
                }
            ]
        }
        seed_rows = [
            {
                "catalog_index": 1,
                "name_ko": "Different Row",
                "name_ja": "Different Row JA",
                "source_url": "https://example.test/products/1",
            },
            {
                "catalog_index": 9,
                "name_ko": "Moved Row",
                "name_ja": "Moved Row JA",
                "source_store": "Seed Store",
                "source_url": "https://example.test/products/1",
                "image_url": "https://cdn.example.test/moved.png",
            },
        ]

        payload = stale_queue.build_queue(audit, seed_rows)

        self.assertEqual(payload["summary"]["review_rows"], 1)
        self.assertEqual(payload["summary"]["skipped_rows"], 0)
        self.assertEqual(payload["items"][0]["catalog_index"], 9)
        self.assertEqual(payload["items"][0]["match_method"], "name_source_url")
        self.assertEqual(payload["items"][0]["name_ko"], "Moved Row")

    def test_load_seed_rows_accepts_public_catalog_object(self):
        payload = {
            "meta": {"row_count": 1},
            "items": [
                {
                    "catalog_index": 7,
                    "name_ko": "Public Row",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog_public.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            rows = stale_queue._load_seed_rows(path)

        self.assertEqual(rows, [{"catalog_index": 7, "name_ko": "Public Row"}])


if __name__ == "__main__":
    unittest.main()
