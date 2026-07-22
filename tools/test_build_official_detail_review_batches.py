from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_official_detail_review_batches as batches


class OfficialDetailReviewBatchesTest(unittest.TestCase):
    def test_load_rows_reads_reviewable_summary_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "merged.json"
            path.write_text(
                json.dumps(
                    {
                        "reviewable": [
                            {
                                "source_store": "애니메이트",
                                "name_ko": "도라에몽 봉제 인형",
                                "name_ja": None,
                                "category": "인형",
                                "affiliation": "도라에몽",
                                "review_status": "needs_manual_title_review",
                                "candidate_source_url": "https://www.animate-onlineshop.jp/pn/x/pd/1/",
                                "candidate_image_url": "https://tc-animate.techorus-cdn.com/resize_image/x.jpg",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            rows = batches._load_rows([path])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name_ko"], "도라에몽 봉제 인형")
        self.assertEqual(rows[0]["review_status"], "needs_manual_title_review")

    def test_write_template_keeps_review_items_unconfirmed(self) -> None:
        payload = {
            "items": [
                {
                    "row_index": 1115,
                    "source_store": "애니메이트",
                    "name_ko": "도라에몽 봉제 인형",
                    "name_ja": None,
                    "category": "인형",
                    "affiliation": "도라에몽",
                    "candidate_count": 1,
                    "candidates": [
                        {
                            "review_status": "needs_manual_title_review",
                            "candidate_title": "ドラえもん ぬいぐるみ Mサイズ",
                            "candidate_source_url": "https://www.animate-onlineshop.jp/pn/x/pd/1/",
                            "candidate_image_url": "https://tc-animate.techorus-cdn.com/resize_image/x.jpg",
                            "token_overlap": 2,
                            "similarity": 1.0,
                        }
                    ],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "template.json"
            batches._write_template(path, payload)
            template = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(template["reviewable_items"], 1)
        self.assertEqual(template["manual_confirmed_true"], 0)
        self.assertFalse(template["items"][0]["manual_confirmed"])
        self.assertEqual(template["items"][0]["row_index"], 1115)

    def test_build_batches_exposes_public_summary(self) -> None:
        payload = batches.build_batches(
            [
                {
                    "source_store": "애니메이트",
                    "name_ko": "도라에몽 봉제 인형",
                    "name_ja": None,
                    "category": "인형",
                    "affiliation": "도라에몽",
                    "review_status": "needs_manual_title_review",
                    "candidate_source_url": "https://www.animate-onlineshop.jp/pn/x/pd/1/",
                    "candidate_image_url": "https://tc-animate.techorus-cdn.com/resize_image/x.jpg",
                    "token_overlap": 2,
                    "similarity": 1.0,
                }
            ],
            seed_index_by_key={("애니메이트", "도라에몽 봉제 인형", None, "인형", "도라에몽"): 1115},
        )

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["summary"]["reviewable_seed_rows"], 1)
        self.assertEqual(payload["summary"]["reviewable_candidate_rows"], 1)
        self.assertEqual(payload["summary"]["manual_confirmed_true"], 0)
        self.assertFalse(payload["summary"]["auto_apply_enabled"])
        self.assertEqual(payload["summary"]["by_store"], [["애니메이트", 1]])


if __name__ == "__main__":
    unittest.main()
