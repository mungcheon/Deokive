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
            "source_discovery_review_batches_public.json": {
                "summary": {"source_discovery_rows": 10, "batch_count": 2}
            },
            "catalog_metadata_review_batches_public.json": {
                "summary": {"missing_cell_count": 20, "batch_count": 2, "field_missing_totals": {"barcode": 20}}
            },
            "requested_focus_review_batches_public.json": {
                "summary": {"review_row_count": 5, "batch_count": 1}
            },
            "catalog_deduplication_review_batches_public.json": {
                "summary": {"source_groups": 1, "batch_count": 1}
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
        image = next(action for action in report["actions"] if action["workstream"] == "image_url_attachment")
        self.assertEqual(image["status"], "blocked")

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
