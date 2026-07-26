from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_top_missing_image_manual_fix_queue_public import build_candidate_context, build_queue


class BuildTopMissingImageManualFixQueuePublicTest(unittest.TestCase):
    def test_build_queue_exports_top_missing_rows_with_safe_command(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "Already done",
                "image_url": "https://example.test/done.jpg",
                "local_image_path": "assets/catalog_images/done.webp",
            },
            {
                "catalog_index": 2,
                "name_ja": "A Prize",
                "category": "Figure",
                "source_store": "Official Store",
                "source_url": "https://example.test/product/2",
            },
            {
                "catalog_index": 3,
                "name_ko": "Needs image",
                "category": "Badge",
                "source_store": "Other Store",
            },
        ]

        report = build_queue(rows, limit=2, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(report["summary"]["catalog_rows"], 3)
        self.assertEqual(report["summary"]["missing_image_rows"], 2)
        self.assertEqual(report["summary"]["queue_rows"], 2)
        self.assertEqual(report["summary"]["manual_confirmed_rows"], 0)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        first = report["items"][0]
        self.assertEqual(first["row_index"], 1)
        self.assertEqual(first["catalog_index"], 2)
        self.assertEqual(first["review_lane"], "open_existing_source_url")
        self.assertEqual(first["manual_image_url"], "")
        self.assertIn("apply_manual_catalog_image_update.py 2", first["safe_apply_command"])
        self.assertIn("--expect-name \"A Prize\"", first["safe_apply_command"])

    def test_root_online_kuji_source_uses_campaign_identity_review_lane(self) -> None:
        rows = [
            {
                "catalog_index": 10,
                "name_ko": "Kuji prize",
                "source_store": "chiikawa online kuji",
                "source_url": "https://online-kuji.chiikawamarket.jp/",
            }
        ]

        report = build_queue(rows, limit=10, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["items"][0]["review_lane"], "official_campaign_identity_review")

    def test_build_queue_merges_candidate_context_for_manual_review(self) -> None:
        rows = [
            {
                "catalog_index": 20,
                "name_ja": "Gotouchi item",
                "source_store": "ご当地ちいかわ 공식(API)",
                "source_url": "https://www.jp-api.com/contents/NOD62/",
            },
            {
                "catalog_index": 30,
                "name_ja": "Kuji item",
                "source_store": "치이카와 온라인 쿠지",
                "source_url": "https://online-kuji.chiikawamarket.jp/store/lottery/sample",
            },
        ]
        context = build_candidate_context(
            gotouchi_queue={
                "items": [
                    {
                        "catalog_index": 20,
                        "candidate_status": "motif_only_type_mismatch",
                        "candidate_count": 0,
                        "rejected_candidate_count": 1,
                        "rejected_candidate_options": [
                            {"image_url": "https://example.test/wrong.png", "alt": "Wrong type"}
                        ],
                        "review_blockers": ["product_type_confirmation_required"],
                        "manual_confirmation_requirements": ["Confirm the product type."],
                    }
                ]
            },
            online_kuji_repair={
                "skipped": [
                    {
                        "catalog_index": 30,
                        "reason": "no_unique_safe_candidate",
                        "candidate_count": 2,
                    }
                ]
            },
        )

        report = build_queue(
            rows,
            limit=10,
            candidate_context=context,
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["summary"]["candidate_context_rows"], 2)
        self.assertEqual(report["summary"]["rejected_candidate_option_rows"], 1)
        gotouchi = report["items"][0]
        self.assertEqual(gotouchi["candidate_status"], "motif_only_type_mismatch")
        self.assertEqual(gotouchi["rejected_candidate_count"], 1)
        self.assertIn("Confirm the product type.", gotouchi["confirmation_checklist"])
        kuji = report["items"][1]
        self.assertEqual(kuji["candidate_status"], "blocked")
        self.assertEqual(kuji["repair_skip_reason"], "no_unique_safe_candidate")


if __name__ == "__main__":
    unittest.main()
