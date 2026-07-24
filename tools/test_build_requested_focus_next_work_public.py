from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_requested_focus_next_work_public as next_work


class BuildRequestedFocusNextWorkPublicTest(unittest.TestCase):
    def test_build_report_publishes_next_batch_and_preview(self) -> None:
        action_queue = {
            "summary": {
                "actionable_template_rows": 3,
                "queued_action_rows": 3,
                "action_batch_count": 2,
            },
            "batches": [
                {
                    "batch_id": "requested-focus-action-001",
                    "priority": 10,
                    "topic_id": "danganronpa",
                    "missing_field": "source_url",
                    "source_store": "애니메이트",
                    "row_count": 2,
                    "review_state": "manual_evidence_review_required",
                    "next_machine_step": "find_exact_source",
                    "recommended_action": "Find source",
                    "blocked_until": "exact_product_source_url_confirmed",
                    "blocked_reason": "missing_exact_source_url_for_requested_focus",
                    "required_evidence": ["exact_official_or_trusted_product_source_url"],
                    "first_primary_review_url": "https://example.com/search",
                    "first_primary_review_url_kind": "domain_limited_web_search",
                    "items": [
                        {
                            "catalog_index": 1,
                            "topic_id": "danganronpa",
                            "missing_field": "source_url",
                            "source_store": "애니메이트",
                            "name_ko": "단간론파 클리어 파일",
                            "name_ja": "ダンガンロンパ クリアファイル",
                            "category": "문구",
                            "primary_review_url": "https://example.com/search",
                            "primary_review_url_kind": "domain_limited_web_search",
                            "blocked_until": "exact_product_source_url_confirmed",
                            "blocked_reason": "missing_exact_source_url_for_requested_focus",
                            "required_evidence": ["exact_official_or_trusted_product_source_url"],
                            "catalog_field_import_template": {
                                "field": "source_url",
                                "manual_value": "",
                                "evidence_url": "",
                                "manual_confirmed": False,
                            },
                        },
                        {
                            "catalog_index": 2,
                            "topic_id": "danganronpa",
                            "missing_field": "source_url",
                            "source_store": "애니메이트",
                            "name_ko": "단간론파 캔뱃지",
                            "category": "캔뱃지",
                            "primary_review_url": "https://example.com/search",
                            "primary_review_url_kind": "domain_limited_web_search",
                            "catalog_field_import_template": {"field": "source_url"},
                        },
                    ],
                },
                {
                    "batch_id": "requested-focus-action-002",
                    "priority": 20,
                    "topic_id": "danganronpa",
                    "missing_field": "image_url",
                    "source_store": "Movic",
                    "row_count": 1,
                    "items": [
                        {
                            "catalog_index": 3,
                            "topic_id": "danganronpa",
                            "missing_field": "image_url",
                            "source_store": "Movic",
                            "name_ko": "단간론파 누이",
                            "category": "마스코트",
                            "catalog_field_import_template": {"field": "image_url"},
                        }
                    ],
                },
            ],
        }

        report = next_work.build_report(action_queue, preview_batches=2, generated_at="2026-07-24T00:00:00Z")

        self.assertEqual(report["summary"]["next_batch_id"], "requested-focus-action-001")
        self.assertEqual(report["summary"]["next_topic_id"], "danganronpa")
        self.assertEqual(report["summary"]["next_missing_field"], "source_url")
        self.assertEqual(report["summary"]["next_source_store"], "애니메이트")
        self.assertEqual(report["summary"]["next_row_count"], 2)
        self.assertEqual(report["summary"]["preview_batch_count"], 2)
        self.assertEqual(report["summary"]["preview_row_count"], 3)
        self.assertEqual(dict(report["summary"]["preview_field_counts"]), {"source_url": 2, "image_url": 1})
        self.assertEqual(dict(report["summary"]["preview_topic_counts"]), {"danganronpa": 3})
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["next_batch"]["items"][0]["topic_id"], "danganronpa")
        self.assertEqual(report["next_batch"]["items"][0]["manual_value_field"], "source_url")
        self.assertFalse(report["next_batch"]["items"][0]["manual_confirmed"])
        self.assertEqual(report["next_batch"]["first_primary_review_url"], "https://example.com/search")
        template = report["confirmed_rows_template"]
        self.assertEqual(template["target_confirmed_queue"], "server/catalog_field_confirmed_rows.json")
        self.assertEqual(len(template["items"]), 2)
        self.assertEqual(template["items"][0]["field"], "source_url")
        self.assertEqual(template["items"][0]["row_index"], 1)
        self.assertEqual(template["items"][0]["source_store"], "애니메이트")
        self.assertEqual(template["items"][0]["name_ko"], "단간론파 클리어 파일")
        self.assertEqual(template["items"][0]["manual_value"], "")
        self.assertEqual(template["items"][0]["evidence_url"], "")
        self.assertFalse(template["items"][0]["manual_confirmed"])
        self.assertEqual(template["items"][0]["review_batch_id"], "requested-focus-action-001")
        self.assertEqual(report["summary"]["confirmed_rows_template_rows"], 2)
        self.assertEqual(report["summary"]["confirmed_rows_manual_confirmed_rows"], 0)
        self.assertEqual(len(report["preview_batches"]), 2)


if __name__ == "__main__":
    unittest.main()
