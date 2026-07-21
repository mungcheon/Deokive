from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_confirmed_import_readiness_public as readiness


def _write_json(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class BuildConfirmedImportReadinessPublicTest(unittest.TestCase):
    def test_default_workflows_include_source_discovery_import_path(self) -> None:
        self.assertIn("source_discovery", readiness.WORKFLOWS)
        workflow = readiness.WORKFLOWS["source_discovery"]

        self.assertEqual(workflow["confirmed"].name, "source_discovery_confirmed_rows.json")
        self.assertEqual(workflow["template"].name, "source_discovery_confirmed_rows.template.json")
        self.assertEqual(workflow["report"].name, "source_discovery_confirmed_import_report.json")
        self.assertEqual(workflow["public_workstream"], "source_discovery_source_urls")

    def test_default_workflows_include_public_action_only_metadata_paths(self) -> None:
        self.assertIn("ichiban_metadata", readiness.WORKFLOWS)
        self.assertIn("animation_category", readiness.WORKFLOWS)

        ichiban = readiness.WORKFLOWS["ichiban_metadata"]
        self.assertEqual(ichiban["public_action_queue"].name, "ichiban_kuji_metadata_action_queue_public.json")
        self.assertEqual(ichiban["public_action_rows_key"], "queued_catalog_item_rows")
        self.assertEqual(ichiban["public_action_next_step"], "fill_confirmed_ichiban_campaign_patch_templates")

        animation = readiness.WORKFLOWS["animation_category"]
        self.assertEqual(animation["public_action_queue"].name, "animation_category_action_queue_public.json")
        self.assertEqual(animation["public_action_rows_key"], "queued_catalog_rows")
        self.assertEqual(animation["public_action_next_step"], "fill_confirmed_animation_category_mapping_templates")

    def test_template_candidates_are_public_without_row_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = {
                "focus_image": {
                    "confirmed": root / "focus_confirmed.json",
                    "template": _write_json(
                        root / "focus.template.json",
                        {
                            "items": [
                                {"row_index": 1, "name_ko": "private detail", "manual_confirmed": False},
                                {"row_index": 2, "name_ko": "private detail 2", "manual_confirmed": False},
                            ]
                        },
                    ),
                    "report": root / "focus_report.json",
                    "public_workstream": "requested_focus_image_urls",
                }
            }

            report = readiness.build_report(workflows)

        self.assertEqual(report["summary"]["template_items"], 2)
        self.assertEqual(report["workflows"][0]["status"], "template_ready_for_manual_confirmation")
        self.assertNotIn("items", report["workflows"][0])
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(
            report["automation_policy"]["row_level_candidate_details"],
            "omitted_from_public_report",
        )

    def test_public_action_queue_counts_are_summarized_without_row_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = {
                "catalog_field": {
                    "confirmed": root / "metadata_confirmed.json",
                    "template": root / "metadata.template.json",
                    "report": root / "metadata_report.json",
                    "public_workstream": "metadata_field_values",
                    "public_action_queue": _write_json(
                        root / "metadata_action.json",
                        {
                            "summary": {
                                "queued_missing_cells": 12,
                                "action_batch_count": 2,
                            },
                            "batches": [
                                {
                                    "batch_id": "private-row-details",
                                    "groups": [{"catalog_indexes": [1, 2, 3]}],
                                }
                            ],
                        },
                    ),
                    "public_action_rows_key": "queued_missing_cells",
                    "public_action_batches_key": "action_batch_count",
                    "public_action_next_step": "fill_confirmed_metadata_patch_templates",
                }
            }

            report = readiness.build_report(workflows)

        workflow = report["workflows"][0]
        self.assertEqual(workflow["status"], "public_action_queue_ready_for_confirmation")
        self.assertEqual(workflow["public_action_rows"], 12)
        self.assertEqual(workflow["public_action_batches"], 2)
        self.assertEqual(report["summary"]["public_action_queue_rows"], 12)
        self.assertEqual(report["summary"]["public_action_queue_batches"], 2)
        self.assertNotIn("batches", workflow)
        self.assertNotIn("groups", workflow)

    def test_confirmed_blocked_rows_summarize_skip_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = {
                "catalog_image": {
                    "confirmed": _write_json(
                        root / "image_confirmed.json",
                        {
                            "items": [
                                {"row_index": 5, "manual_confirmed": True},
                                {"row_index": 6, "manual_confirmed": "confirmed"},
                            ]
                        },
                    ),
                    "template": _write_json(root / "image.template.json", {"items": []}),
                    "report": _write_json(
                        root / "image_report.json",
                        {
                            "updated_rows": 0,
                            "skipped_sample": [
                                {"row_index": 5, "reason": "image_url_already_present"},
                                {"row_index": 6, "reason": "image_url_already_present"},
                            ],
                        },
                    ),
                    "public_workstream": "exact_image_urls",
                }
            }

            report = readiness.build_report(workflows)

        workflow = report["workflows"][0]
        self.assertEqual(workflow["status"], "confirmed_rows_blocked")
        self.assertEqual(report["summary"]["blocked_confirmed_rows"], 2)
        self.assertEqual(workflow["skip_reason_counts"], [("image_url_already_present", 2)])


if __name__ == "__main__":
    unittest.main()
