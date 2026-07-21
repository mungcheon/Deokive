from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_catalog_execution_plan_public as plan


class BuildCatalogExecutionPlanPublicTest(unittest.TestCase):
    def test_plan_prefers_manual_confirmation_before_import(self) -> None:
        payloads = {
            "catalog_operations_public.json": {
                "summary": {"open_review_queues": {"image_missing_rows": 10}}
            },
            "catalog_image_enrichment_batches_public.json": {
                "summary": {"missing_image_rows": 10, "source_url_ready_rows": 0, "needs_source_discovery_rows": 10}
            },
            "catalog_image_attachment_action_queue_public.json": {
                "summary": {
                    "actionable_image_rows": 2,
                    "queued_image_rows": 2,
                    "action_batch_count": 1,
                    "excluded_workflow_rows": [["find_source_then_extract_image", 8]],
                }
            },
            "source_discovery_review_batches_public.json": {
                "summary": {"source_discovery_rows": 10, "batch_count": 2}
            },
            "catalog_metadata_review_batches_public.json": {
                "summary": {"missing_cell_count": 20, "batch_count": 2, "field_missing_totals": {"barcode": 20}}
            },
            "requested_focus_review_batches_public.json": {
                "summary": {
                    "review_row_count": 5,
                    "batch_count": 1,
                    "field_patch_template_count": 5,
                    "field_patch_template_counts": [
                        ["barcode", 3],
                        ["source_url", 1],
                        ["image_url", 1],
                    ],
                }
            },
            "requested_focus_action_queue_public.json": {
                "summary": {
                    "actionable_template_rows": 2,
                    "queued_action_rows": 2,
                    "action_batch_count": 1,
                    "barcode_template_rows_excluded": 3,
                    "field_counts": [["source_url", 1], ["image_url", 1]],
                }
            },
            "catalog_deduplication_review_batches_public.json": {
                "summary": {"source_groups": 1, "batch_count": 1}
            },
            "catalog_deduplication_action_queue_public.json": {
                "summary": {
                    "actionable_groups": 2,
                    "queued_groups": 2,
                    "action_batch_count": 1,
                    "by_review_confidence": [["high_review_confidence", 2]],
                    "excluded_review_confidence": [["variant_caution", 1]],
                }
            },
            "ichiban_kuji_metadata_review_batches_public.json": {
                "summary": {"catalog_item_rows": 0}
            },
            "animation_category_review_batches_public.json": {
                "summary": {"source_rows": 0}
            },
            "catalog_confirmed_import_readiness_public.json": {
                "summary": {
                    "template_items": 3,
                    "ready_or_pending_import_rows": 0,
                    "blocked_confirmed_rows": 0,
                }
            },
        }

        with patch.object(plan, "_load", side_effect=lambda name: payloads.get(name, {})):
            report = plan.build_plan()

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        first = report["actions"][0]
        self.assertEqual(first["workstream"], "confirmed_import_readiness")
        self.assertEqual(first["status"], "needs_manual_confirmation")
        self.assertIn("manual_confirmed=true", first["blocker"])
        requested = next(
            action
            for action in report["actions"]
            if action["workstream"] == "requested_focus_review_batches"
        )
        self.assertEqual(report["summary"]["requested_focus_actionable_template_rows"], 2)
        self.assertEqual(report["summary"]["requested_focus_barcode_template_rows"], 3)
        self.assertEqual(requested["evidence"]["actionable_non_barcode_template_rows"], 2)
        self.assertEqual(requested["evidence"]["barcode_template_rows"], 3)
        action_queue = next(
            action
            for action in report["actions"]
            if action["workstream"] == "requested_focus_action_queue"
        )
        self.assertEqual(action_queue["priority"], 11)
        self.assertEqual(action_queue["rows"], 2)
        self.assertEqual(action_queue["evidence"]["barcode_template_rows_excluded"], 3)
        image = next(action for action in report["actions"] if action["workstream"] == "image_url_attachment")
        self.assertEqual(image["status"], "blocked")
        image_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "image_attachment_action_queue"
        )
        self.assertEqual(image_action["priority"], 31)
        self.assertEqual(image_action["rows"], 2)
        self.assertEqual(image_action["evidence"]["actionable_image_rows"], 2)
        dedupe_action = next(
            action
            for action in report["actions"]
            if action["workstream"] == "deduplication_action_queue"
        )
        self.assertEqual(dedupe_action["rows"], 2)
        self.assertEqual(dedupe_action["evidence"]["actionable_groups"], 2)

    def test_pending_import_rows_are_prioritized(self) -> None:
        payloads = {
            "catalog_operations_public.json": {"summary": {"open_review_queues": {}}},
            "catalog_confirmed_import_readiness_public.json": {
                "summary": {
                    "template_items": 0,
                    "ready_or_pending_import_rows": 2,
                    "blocked_confirmed_rows": 0,
                }
            },
        }

        with patch.object(plan, "_load", side_effect=lambda name: payloads.get(name, {})):
            report = plan.build_plan()

        self.assertEqual(report["actions"][0]["status"], "pending_import")
        self.assertIsNone(report["actions"][0]["blocker"])
        self.assertEqual(report["summary"]["pending_import_action_count"], 1)


if __name__ == "__main__":
    unittest.main()
