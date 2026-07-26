from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_catalog_image_attachment_review_board_public as board_builder


class CatalogImageAttachmentReviewBoardTest(unittest.TestCase):
    def test_build_board_summarizes_and_sorts_review_lanes(self) -> None:
        template = {
            "generated_at": "2026-07-25T12:00:00Z",
            "items": [
                {
                    "catalog_index": 2,
                    "name_ko": "대표 이미지 확인",
                    "source_store": "B store",
                    "review_lane": "representative_image_candidate_review",
                    "image_import_blockers": ["representative_image_may_not_match_exact_variant"],
                },
                {
                    "catalog_index": 1,
                    "name_ko": "이미지 URL 확인",
                    "source_store": "A store",
                    "review_lane": "image_url_review_ready",
                    "current_source_url": "https://example.com/item",
                    "manual_value": "https://example.com/item.jpg",
                    "manual_confirmed": True,
                    "image_import_blockers": ["manual_image_url_confirmation"],
                },
            ],
        }

        board = board_builder.build_board(
            template,
            generated_at="2026-07-26T00:00:00Z",
        )

        self.assertEqual(board["generated_at"], "2026-07-26T00:00:00Z")
        self.assertEqual(board["summary"]["review_rows"], 2)
        self.assertEqual(board["summary"]["image_url_review_ready_rows"], 1)
        self.assertEqual(board["summary"]["representative_image_review_rows"], 1)
        self.assertEqual(board["summary"]["manual_confirmed_rows"], 1)
        self.assertEqual(board["summary"]["manual_value_rows"], 1)
        self.assertEqual(board["summary"]["gate_status"], "blocked_until_manual_image_confirmation")
        self.assertEqual(board["items"][0]["catalog_index"], 1)
        self.assertEqual(board["items"][0]["review_url"], "https://example.com/item")


if __name__ == "__main__":
    unittest.main()
