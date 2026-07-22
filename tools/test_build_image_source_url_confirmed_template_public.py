from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_image_source_url_confirmed_template_public as template


class BuildImageSourceUrlConfirmedTemplatePublicTest(unittest.TestCase):
    def test_build_template_keeps_only_source_url_update_items(self) -> None:
        action_queue = {
            "batches": [
                {
                    "batch_id": "image-attachment-action-001",
                    "source_store": "Stellive Store",
                    "items": [
                        {
                            "catalog_index": 10,
                            "workflow": "replace_generic_source_then_extract_image",
                            "source_store": "Stellive Store",
                            "name_ko": "Badge",
                            "category": "Can Badge",
                            "source_url": "https://fanding.kr/@stellive/shop",
                            "official_search_url": "https://stellive.fanding.kr/search?keyword=Badge",
                            "required_before_image_import": [
                                "confirm_exact_product_source_url",
                                "replace_generic_source_url",
                            ],
                            "source_url_import_template": {
                                "row_index": 10,
                                "field": "source_url",
                                "current_source_url": "https://fanding.kr/@stellive/shop",
                            },
                        },
                        {
                            "catalog_index": 11,
                            "workflow": "review_gotouchi_official_candidates",
                            "source_store": "Gotouchi",
                            "name_ko": "Charm",
                        },
                    ],
                }
            ]
        }

        candidate_report = {
            "queue": [
                {
                    "row_index": 10,
                    "candidate_status": "weak_manual_review_candidate",
                    "top_candidates": [
                        {
                            "product_no": 100,
                            "title": "Badge exact-ish",
                            "source_url": "https://fanding.kr/@stellive/shop/100",
                            "image_url": "https://example.test/badge.webp",
                            "score": 0.81,
                            "shared_tokens": ["Badge"],
                            "query_overlap": 0.5,
                            "title_overlap": 0.75,
                        }
                    ],
                }
            ]
        }

        report = template.build_template(
            action_queue,
            candidate_report,
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(report["summary"]["template_items"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_rows"], 0)
        self.assertEqual(report["summary"]["by_source_store"], [["Stellive Store", 1]])
        self.assertEqual(report["summary"]["candidate_prefilled_rows"], 1)
        self.assertEqual(report["summary"]["by_candidate_status"], [["weak_manual_review_candidate", 1]])
        self.assertEqual(report["summary"]["by_source_url_review_lane"], [["weak_candidate_review", 1]])
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        item = report["items"][0]
        self.assertEqual(item["field"], "source_url")
        self.assertEqual(item["row_index"], 10)
        self.assertEqual(item["manual_value"], "")
        self.assertEqual(item["candidate_source_url"], "https://fanding.kr/@stellive/shop/100")
        self.assertEqual(item["candidate_image_url"], "https://example.test/badge.webp")
        self.assertEqual(item["candidate_title"], "Badge exact-ish")
        self.assertEqual(item["candidate_status"], "weak_manual_review_candidate")
        self.assertEqual(item["source_url_review_lane"], "weak_candidate_review")
        self.assertIn("weak_candidate_only", item["source_url_review_blockers"])
        self.assertIn("manual_confirmed=true", item["manual_confirmation_requirements"][-1])
        self.assertEqual(item["candidate_options"][0]["product_no"], 100)
        self.assertEqual(item["current_source_url"], "https://fanding.kr/@stellive/shop")
        self.assertEqual(item["next_after_confirmed_source_url"], "extract_or_confirm_product_page_image_url")
        self.assertFalse(item["auto_apply_enabled"])


if __name__ == "__main__":
    unittest.main()
