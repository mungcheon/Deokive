from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_deduplication_fast_review_public import build_report


class DeduplicationFastReviewTests(unittest.TestCase):
    def test_build_report_keeps_only_high_confidence_barcode_groups(self):
        action_queue = {
            "batches": [
                {
                    "groups": [
                        {
                            "key_type": "barcode",
                            "key": "111",
                            "review_confidence": "high_review_confidence",
                            "review_risk": "strong_identity_review",
                            "keep_catalog_index": 1,
                            "drop_catalog_indexes": [2],
                            "stores": ["store a", "store b"],
                            "categories": ["badge"],
                            "evidence": ["barcode", "same_barcode", "same_source_url"],
                            "dedupe_decision_template": {"key": "111"},
                            "rows": [
                                {
                                    "catalog_index": 1,
                                    "name_ko": "치이카와 양말 (하치와레/블루)",
                                    "source_store": "store a",
                                    "source_url": "https://example.test/item",
                                    "image_url": "https://example.test/a.jpg",
                                    "richness": 12,
                                },
                                {
                                    "catalog_index": 2,
                                    "name_ko": "치이카와 양말 (가르마 / 블루)",
                                    "source_store": "store b",
                                    "source_url": "https://example.test/item",
                                    "image_url": "https://example.test/b.jpg",
                                    "richness": 10,
                                },
                            ],
                        },
                        {
                            "key_type": "barcode",
                            "key": "333",
                            "review_confidence": "high_review_confidence",
                            "review_risk": "strong_identity_review",
                            "keep_catalog_index": 7,
                            "drop_catalog_indexes": [8],
                            "stores": ["store a", "store b"],
                            "categories": ["badge"],
                            "evidence": ["barcode", "same_barcode", "same_source_url"],
                            "dedupe_decision_template": {"key": "333"},
                            "rows": [
                                {
                                    "catalog_index": 7,
                                    "name_ko": "치이카와 양말 (시사/오렌지)",
                                    "source_store": "store a",
                                    "source_url": "https://example.test/same",
                                    "image_url": "https://example.test/same-a.jpg",
                                    "richness": 12,
                                },
                                {
                                    "catalog_index": 8,
                                    "name_ko": "치이카와 양말 (시사 / 오렌지)",
                                    "source_store": "store b",
                                    "source_url": "https://example.test/same",
                                    "image_url": "https://example.test/same-b.jpg",
                                    "richness": 10,
                                },
                            ],
                        },
                        {
                            "key_type": "source_url",
                            "key": "https://example.test/a",
                            "review_confidence": "high_review_confidence",
                            "drop_catalog_indexes": [4],
                        },
                        {
                            "key_type": "barcode",
                            "key": "222",
                            "review_confidence": "medium_review_confidence",
                            "drop_catalog_indexes": [6],
                        },
                    ]
                }
            ]
        }

        report = build_report(action_queue, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["summary"]["fast_review_groups"], 2)
        self.assertEqual(report["summary"]["held_for_later_groups"], 2)
        self.assertEqual(report["summary"]["same_barcode_groups"], 2)
        self.assertEqual(report["summary"]["same_source_url_groups"], 2)
        self.assertEqual(report["summary"]["same_image_url_groups"], 0)
        self.assertEqual(report["summary"]["name_delta_groups"], 1)
        self.assertEqual(report["summary"]["image_delta_groups"], 2)
        self.assertEqual(report["summary"]["image_url_only_same_identity_groups"], 1)
        self.assertEqual(report["summary"]["variant_warning_groups"], 2)
        self.assertEqual(report["summary"]["next_fast_review_batch_groups"], 2)
        self.assertEqual(report["summary"]["next_fast_review_batch_drop_candidate_rows"], 2)
        self.assertEqual(report["summary"]["next_fast_review_batch_primary_review_url_groups"], 2)
        self.assertEqual(
            report["summary"]["next_fast_review_batch_image_url_only_same_identity_groups"],
            1,
        )
        self.assertEqual(
            report["summary"]["next_fast_review_batch_warning_counts"],
            [["image_delta_requires_visual_check", 1], ["name_delta_requires_variant_check", 1]],
        )
        self.assertEqual(report["summary"]["primary_review_url_groups"], 2)
        self.assertEqual(report["summary"]["first_primary_review_url"], "https://example.test/item")
        self.assertIs(report["summary"]["auto_delete_enabled"], False)
        self.assertIs(report["items"][0]["dedupe_decision_template"]["manual_confirmed"], False)
        self.assertEqual(
            report["items"][0]["dedupe_decision_template"]["fast_review_lane"],
            "same_barcode_and_source_url",
        )
        self.assertEqual(report["items"][0]["fast_review_lane"], "same_barcode_and_source_url")
        self.assertEqual(report["items"][0]["fast_review_warning"], "name_delta_requires_variant_check")
        self.assertEqual(report["items"][0]["primary_review_url"], "https://example.test/item")
        self.assertEqual(report["items"][0]["primary_review_url_kind"], "keep_source_url")
        self.assertEqual(report["items"][0]["review_url_count"], 3)
        self.assertEqual(report["items"][0]["keep_reason"], "keeps_richest_catalog_row")
        self.assertTrue(report["items"][0]["identity_delta"]["name_differs"])
        self.assertFalse(report["items"][0]["identity_delta"]["source_url_differs"])
        self.assertTrue(report["items"][0]["identity_delta"]["image_url_differs"])
        self.assertEqual(report["items"][0]["identity_delta"]["store_count"], 2)
        self.assertEqual(
            report["breakdowns"]["by_fast_review_lane"],
            [{"fast_review_lane": "same_barcode_and_source_url", "groups": 2}],
        )
        self.assertEqual(
            report["breakdowns"]["by_fast_review_warning"],
            [
                {"fast_review_warning": "name_delta_requires_variant_check", "groups": 1},
                {"fast_review_warning": "image_delta_requires_visual_check", "groups": 1},
            ],
        )
        self.assertEqual(
            report["breakdowns"]["by_primary_review_url_kind"],
            [{"primary_review_url_kind": "keep_source_url", "groups": 2}],
        )
        self.assertEqual(report["next_fast_review_batch"][0]["key"], "333")
        self.assertTrue(report["next_fast_review_batch"][0]["image_url_only_same_identity"])
        self.assertEqual(
            report["next_fast_review_batch"][0]["suggested_review_order"],
            "image_url_only_same_identity_first",
        )
        self.assertFalse(report["next_fast_review_batch"][0]["manual_confirmed"])
        self.assertFalse(report["next_fast_review_batch"][0]["auto_merge_enabled"])
        self.assertEqual(
            report["next_fast_review_batch"][0]["primary_review_url"],
            "https://example.test/same",
        )
        self.assertIn(
            "same sellable item",
            report["next_fast_review_batch"][0]["operator_checklist"][1],
        )
        self.assertIn(
            "same_sellable_product_confirmed",
            report["next_fast_review_batch"][0]["manual_value_fields_to_fill"],
        )
        self.assertEqual(report["automation_policy"]["import_tool"], "tools/import_confirmed_dedupe_decisions.py")


if __name__ == "__main__":
    unittest.main()
