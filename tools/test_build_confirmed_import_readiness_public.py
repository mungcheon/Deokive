from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_confirmed_import_readiness_public as readiness
import import_confirmed_animation_category_rows
import import_confirmed_dedupe_decisions
import import_confirmed_ichiban_metadata_rows
import import_confirmed_image_attachment_rows
import import_confirmed_metadata_rows
import import_confirmed_official_detail_matches
import import_confirmed_requested_focus_rows
import import_confirmed_source_discovery_rows
import import_confirmed_variant_metadata_backfill_rows


def _write_json(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class BuildConfirmedImportReadinessPublicTest(unittest.TestCase):
    def test_default_workflows_include_source_discovery_import_path(self) -> None:
        self.assertIn("source_discovery", readiness.WORKFLOWS)
        self.assertIn("source_discovery_next_focus_fallback", readiness.WORKFLOWS)
        metadata = readiness.WORKFLOWS["catalog_field"]
        self.assertEqual(metadata["public_action_queue"].name, "catalog_metadata_action_queue_public.json")
        self.assertEqual(metadata["public_action_rows_key"], "queued_missing_cells")
        self.assertEqual(
            metadata["public_action_next_step"],
            "fill_confirmed_metadata_patch_templates_then_run_import_confirmed_metadata_rows",
        )

        workflow = readiness.WORKFLOWS["source_discovery"]

        official = readiness.WORKFLOWS["official_detail"]
        self.assertEqual(official["public_action_queue"].name, "official_detail_review_batches_public.json")
        self.assertEqual(official["public_action_rows_key"], "reviewable_seed_rows")
        self.assertEqual(
            official["public_action_next_step"],
            "confirm_official_detail_candidates_then_run_import_confirmed_official_detail_matches",
        )

        self.assertEqual(workflow["confirmed"].name, "source_discovery_confirmed_rows.json")
        self.assertEqual(workflow["template"].name, "source_discovery_confirmed_rows.template.json")
        self.assertEqual(workflow["report"].name, "source_discovery_confirmed_import_report.json")
        self.assertEqual(workflow["public_workstream"], "source_discovery_source_urls")
        self.assertEqual(
            workflow["public_action_next_step"],
            "confirm_source_url_templates_then_run_import_confirmed_source_discovery_rows",
        )

        focused = readiness.WORKFLOWS["source_discovery_next_focus_fallback"]
        self.assertEqual(focused["confirmed"].name, "source_discovery_confirmed_rows.json")
        self.assertEqual(
            focused["template"].name,
            "source_discovery_next_focus_fallback_confirmed_rows.template.json",
        )
        self.assertEqual(
            focused["report"].name,
            "source_discovery_next_focus_fallback_confirmed_import_dryrun.json",
        )
        self.assertEqual(focused["public_action_queue"].name, "source_discovery_next_focus_fallback_queue_public.json")
        self.assertEqual(focused["public_action_rows_key"], "queue_rows")
        self.assertEqual(
            focused["public_action_next_step"],
            "confirm_focused_fallback_source_urls_then_run_import_confirmed_source_discovery_rows",
        )

        variant_metadata = readiness.WORKFLOWS["variant_metadata"]
        self.assertEqual(
            variant_metadata["public_workstream"],
            "catalog_variant_metadata_enrichment",
        )
        self.assertEqual(
            variant_metadata["public_action_next_step"],
            "fill_variant_metadata_confirmed_rows_then_run_import_confirmed_variant_metadata_backfill_rows",
        )

        image = readiness.WORKFLOWS["catalog_image"]
        self.assertEqual(image["confirmed"].name, "catalog_image_attachment_confirmed_rows.json")
        self.assertEqual(image["template"].name, "catalog_image_attachment_confirmed_rows.template.json")
        self.assertEqual(image["report"].name, "catalog_image_attachment_confirmed_import_report.json")
        self.assertEqual(image["public_action_queue"].name, "catalog_image_attachment_action_queue_public.json")
        self.assertEqual(image["public_action_rows_key"], "queued_image_rows")
        self.assertEqual(
            image["public_action_next_step"],
            "confirm_exact_image_url_templates_then_run_import_confirmed_image_attachment_rows",
        )

        focus = readiness.WORKFLOWS["focus_image"]
        self.assertEqual(focus["confirmed"].name, "requested_focus_confirmed_rows.json")
        self.assertEqual(focus["template"].name, "requested_focus_confirmed_rows.template.json")
        self.assertEqual(focus["report"].name, "requested_focus_confirmed_import_report.json")
        self.assertEqual(focus["public_action_queue"].name, "requested_focus_action_queue_public.json")
        self.assertEqual(focus["public_action_rows_key"], "queued_action_rows")
        self.assertEqual(
            focus["public_action_next_step"],
            "confirm_requested_focus_templates_then_run_import_confirmed_requested_focus_rows",
        )

    def test_default_workflows_include_public_action_only_metadata_paths(self) -> None:
        self.assertIn("ichiban_metadata", readiness.WORKFLOWS)
        self.assertIn("animation_category", readiness.WORKFLOWS)
        self.assertIn("deduplication", readiness.WORKFLOWS)

        ichiban = readiness.WORKFLOWS["ichiban_metadata"]
        self.assertEqual(ichiban["public_action_queue"].name, "ichiban_kuji_metadata_action_queue_public.json")
        self.assertEqual(ichiban["public_action_rows_key"], "queued_catalog_item_rows")
        self.assertEqual(
            ichiban["public_action_next_step"],
            "fill_confirmed_ichiban_campaign_patch_templates_then_run_import_confirmed_ichiban_metadata_rows",
        )

        animation = readiness.WORKFLOWS["animation_category"]
        self.assertEqual(animation["public_action_queue"].name, "animation_category_action_queue_public.json")
        self.assertEqual(animation["public_action_rows_key"], "queued_catalog_rows")
        self.assertEqual(
            animation["public_action_next_step"],
            "fill_confirmed_animation_category_mapping_templates_then_run_import_confirmed_animation_category_rows",
        )

        dedupe = readiness.WORKFLOWS["deduplication"]
        self.assertEqual(dedupe["public_action_queue"].name, "catalog_deduplication_action_queue_public.json")
        self.assertEqual(dedupe["public_action_rows_key"], "queued_groups")
        self.assertEqual(
            dedupe["public_action_next_step"],
            "fill_confirmed_deduplication_decisions_then_run_import_confirmed_dedupe_decisions",
        )

    def test_public_action_next_steps_reference_existing_importers(self) -> None:
        tools_dir = Path(__file__).resolve().parent
        for workflow_name, workflow in readiness.WORKFLOWS.items():
            next_step = workflow.get("public_action_next_step")
            if not next_step:
                continue
            marker = "then_run_"
            self.assertIn(marker, next_step, workflow_name)
            importer_name = next_step.split(marker, 1)[1]
            self.assertTrue((tools_dir / f"{importer_name}.py").exists(), workflow_name)

    def test_readiness_paths_match_importer_defaults(self) -> None:
        expected = {
            "official_detail": import_confirmed_official_detail_matches,
            "catalog_field": import_confirmed_metadata_rows,
            "source_discovery": import_confirmed_source_discovery_rows,
            "catalog_image": import_confirmed_image_attachment_rows,
            "focus_image": import_confirmed_requested_focus_rows,
            "variant_metadata": import_confirmed_variant_metadata_backfill_rows,
            "ichiban_metadata": import_confirmed_ichiban_metadata_rows,
            "animation_category": import_confirmed_animation_category_rows,
            "deduplication": import_confirmed_dedupe_decisions,
        }

        for workflow_name, importer in expected.items():
            workflow = readiness.WORKFLOWS[workflow_name]
            self.assertEqual(workflow["confirmed"], importer.DEFAULT_QUEUE, workflow_name)
            self.assertEqual(workflow["template"], importer.FALLBACK_QUEUE, workflow_name)
            self.assertEqual(workflow["report"], importer.DEFAULT_REPORT, workflow_name)

        focused = readiness.WORKFLOWS["source_discovery_next_focus_fallback"]
        self.assertEqual(focused["confirmed"], import_confirmed_source_discovery_rows.DEFAULT_QUEUE)
        self.assertNotEqual(focused["template"], import_confirmed_source_discovery_rows.FALLBACK_QUEUE)
        self.assertNotEqual(focused["report"], import_confirmed_source_discovery_rows.DEFAULT_REPORT)

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

    def test_variant_metadata_summary_counts_are_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = {
                "variant_metadata": {
                    "confirmed": _write_json(
                        root / "variant.template.json",
                        {
                            "items": [
                                {"manual_confirmed": False},
                                {"manual_confirmed": False},
                            ]
                        },
                    ),
                    "template": root / "variant.template.json",
                    "report": _write_json(
                        root / "variant_report.json",
                        {"updated_rows": 0, "skipped_rows": 2},
                    ),
                    "public_workstream": "catalog_variant_metadata_enrichment",
                }
            }

            report = readiness.build_report(workflows)

        self.assertEqual(report["summary"]["variant_metadata_template_rows"], 2)
        self.assertEqual(report["summary"]["variant_metadata_manual_confirmed_rows"], 0)
        self.assertEqual(report["summary"]["variant_metadata_skipped_rows"], 2)

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
        self.assertEqual(report["summary"]["manual_confirmation_backlog_rows"], 12)
        self.assertEqual(report["summary"]["work_order_lanes"], 1)
        self.assertEqual(report["summary"]["top_work_order_lane"], "convert_public_action_queue_to_confirmed_rows")
        self.assertEqual(report["summary"]["top_work_order_workflow"], "catalog_field")
        self.assertEqual(report["work_order"][0]["row_count"], 12)
        self.assertEqual(report["work_order"][0]["batch_count"], 2)
        self.assertNotIn("batches", workflow)
        self.assertNotIn("groups", workflow)
        self.assertNotIn("batches", report["work_order"][0])
        self.assertNotIn("groups", report["work_order"][0])

    def test_work_order_prioritizes_importable_and_blocked_rows_before_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = {
                "catalog_image": {
                    "confirmed": _write_json(
                        root / "image_confirmed.json",
                        {"items": [{"manual_confirmed": True}, {"manual_confirmed": True}]},
                    ),
                    "template": _write_json(root / "image.template.json", {"items": []}),
                    "report": _write_json(root / "image_report.json", {"updated_rows": 0, "skipped_rows": 2}),
                    "public_workstream": "exact_image_urls",
                },
                "source_discovery": {
                    "confirmed": _write_json(
                        root / "source_confirmed.json",
                        {"items": [{"manual_confirmed": True}]},
                    ),
                    "template": _write_json(root / "source.template.json", {"items": []}),
                    "report": root / "source_report.json",
                    "public_workstream": "source_discovery_source_urls",
                },
                "catalog_field": {
                    "confirmed": root / "metadata_confirmed.json",
                    "template": _write_json(
                        root / "metadata.template.json",
                        {"items": [{"manual_confirmed": False}, {"manual_confirmed": False}]},
                    ),
                    "report": root / "metadata_report.json",
                    "public_workstream": "metadata_field_values",
                    "public_action_queue": _write_json(
                        root / "metadata_action.json",
                        {"summary": {"queued_missing_cells": 99, "action_batch_count": 4}},
                    ),
                    "public_action_rows_key": "queued_missing_cells",
                    "public_action_batches_key": "action_batch_count",
                    "public_action_next_step": "fill_confirmed_metadata_patch_templates_then_run_import_confirmed_metadata_rows",
                },
            }

            report = readiness.build_report(workflows)

        lanes = [(row["lane"], row["workflow"], row["row_count"]) for row in report["work_order"]]
        self.assertEqual(lanes[0], ("run_guarded_confirmed_import", "source_discovery", 1))
        self.assertEqual(lanes[1], ("resolve_blocked_confirmed_rows", "catalog_image", 2))
        self.assertEqual(lanes[2], ("confirm_template_rows", "catalog_field", 2))
        self.assertEqual(lanes[3], ("convert_public_action_queue_to_confirmed_rows", "catalog_field", 99))
        self.assertEqual(report["summary"]["manual_confirmation_backlog_rows"], 101)

    def test_public_action_queue_takes_priority_over_empty_confirmed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflows = {
                "official_detail": {
                    "confirmed": _write_json(root / "official_confirmed.json", {"items": []}),
                    "template": root / "official.template.json",
                    "report": root / "official_report.json",
                    "public_workstream": "official_detail_source_image",
                    "public_action_queue": _write_json(
                        root / "official_action.json",
                        {"summary": {"reviewable_seed_rows": 3}},
                    ),
                    "public_action_rows_key": "reviewable_seed_rows",
                    "public_action_next_step": "confirm_official_detail_candidates_then_run_import_confirmed_official_detail_matches",
                }
            }

            report = readiness.build_report(workflows)

        workflow = report["workflows"][0]
        self.assertEqual(workflow["status"], "public_action_queue_ready_for_confirmation")
        self.assertTrue(workflow["confirmed_file_exists"])
        self.assertEqual(workflow["public_action_rows"], 3)

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
