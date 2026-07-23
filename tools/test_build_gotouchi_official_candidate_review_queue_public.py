from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_gotouchi_official_candidate_review_queue_public as queue


class BuildGotouchiOfficialCandidateReviewQueuePublicTest(unittest.TestCase):
    def test_build_queue_joins_action_items_with_candidate_report(self) -> None:
        action_queue = {
            "batches": [
                {
                    "batch_id": "image-attachment-action-006",
                    "workflow": "review_gotouchi_official_candidates",
                    "items": [
                        {
                            "catalog_index": 100,
                            "source_store": "Gotouchi",
                            "name_ko": "Chiikawa keyholder",
                            "name_ja": "ちいかわ キーホルダー",
                            "category": "아크릴 키링",
                            "character_name": "치이카와",
                            "source_url": "https://www.jp-api.com/contents/NOD62/",
                            "review_lane": "representative_image_candidate_review",
                        }
                    ],
                },
                {
                    "batch_id": "ignored",
                    "workflow": "replace_generic_source_then_extract_image",
                    "items": [{"catalog_index": 200}],
                },
            ]
        }
        candidate_report = {
            "items": [
                {
                    "catalog_index": 100,
                    "candidate_status": "motif_only_type_mismatch",
                    "row_type": "acrylic_keyholder",
                    "motifs": ["雷門"],
                    "top_candidates": [
                        {
                            "page": "https://www.jp-api.com/contents/NOD62/PGE2/",
                            "image_url": "https://www.jp-api.com/images/sample.png",
                            "alt": "雷門 ぬいぐるみキーチェーン",
                            "type": "plush_keychain",
                            "row_type": "acrylic_keyholder",
                            "type_match": False,
                            "matched_motifs": ["雷門"],
                            "score": 2,
                        }
                    ],
                }
            ]
        }

        report = queue.build_queue(
            action_queue,
            candidate_report,
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-23T00:00:00Z")
        self.assertEqual(report["summary"]["review_rows"], 1)
        self.assertEqual(report["summary"]["with_candidate_options"], 1)
        self.assertEqual(report["summary"]["without_candidate_options"], 0)
        self.assertEqual(report["summary"]["by_candidate_status"], [["motif_only_type_mismatch", 1]])
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_image_url"])

        item = report["items"][0]
        self.assertEqual(item["catalog_index"], 100)
        self.assertEqual(item["candidate_status"], "motif_only_type_mismatch")
        self.assertEqual(item["top_candidate"]["image_url"], "https://www.jp-api.com/images/sample.png")
        self.assertIn("product_type_mismatch", item["review_blockers"])
        template = item["image_url_import_template"]
        self.assertEqual(template["field"], "image_url")
        self.assertEqual(template["manual_value"], "")
        self.assertEqual(template["candidate_image_url"], "https://www.jp-api.com/images/sample.png")
        self.assertTrue(template["representative_image"])
        self.assertFalse(template["manual_confirmed"])

    def test_missing_candidate_report_row_still_gets_review_item(self) -> None:
        action_queue = {
            "batches": [
                {
                    "batch_id": "image-attachment-action-006",
                    "workflow": "review_gotouchi_official_candidates",
                    "items": [{"catalog_index": 101, "category": "마스코트"}],
                }
            ]
        }

        report = queue.build_queue(action_queue, {"items": []})

        self.assertEqual(report["summary"]["review_rows"], 1)
        self.assertEqual(report["summary"]["without_candidate_options"], 1)
        self.assertEqual(report["items"][0]["candidate_status"], "missing_candidate_report")

    def test_rejected_visual_mismatch_gets_strong_blocker(self) -> None:
        action_queue = {
            "batches": [
                {
                    "batch_id": "image-attachment-action-006",
                    "workflow": "review_gotouchi_official_candidates",
                    "items": [{"catalog_index": 102, "category": "마스코트"}],
                }
            ]
        }
        candidate_report = {
            "items": [
                {
                    "catalog_index": 102,
                    "candidate_status": "rejected_visual_mismatch",
                    "top_candidates": [
                        {
                            "page": "https://www.jp-api.com/contents/NOD62/PGE1/",
                            "image_url": "https://www.jp-api.com/images/wrong.png",
                        }
                    ],
                }
            ]
        }

        report = queue.build_queue(action_queue, candidate_report)

        self.assertIn("visual_mismatch", report["items"][0]["review_blockers"])
        self.assertIn(
            "do_not_import_without_stronger_evidence",
            report["items"][0]["review_blockers"],
        )


if __name__ == "__main__":
    unittest.main()
