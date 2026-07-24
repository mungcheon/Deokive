from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_confirmed_import_queues as audit
import import_confirmed_animation_category_rows
import import_confirmed_dedupe_decisions
import import_confirmed_ichiban_metadata_rows
import import_confirmed_image_attachment_rows
import import_confirmed_metadata_rows
import import_confirmed_requested_focus_rows
import import_confirmed_source_discovery_rows
import import_confirmed_variant_metadata_backfill_rows


def _write_json(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


class ConfirmedImportQueueAuditTests(unittest.TestCase):
    def test_template_without_confirmed_file_is_actionable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = {
                "storefront": {
                    "confirmed": root / "storefront_confirmed.json",
                    "template": _write_json(
                        root / "storefront.template.json",
                        {"items": [{"manual_confirmed": False}, {"manual_confirmed": False}]},
                    ),
                    "report": _write_json(
                        root / "storefront_report.json",
                        {"updated_rows": 0, "skipped_rows": 0, "note": "No confirmed queue found."},
                    ),
                    "artifact": root / "storefront.html",
                    "description": "storefront candidates",
                    "dry_run_command": "python dry-run.py",
                    "write_command": "python write.py --write",
                }
            }

            with patch.object(audit, "WORKFLOWS", config):
                payload = audit.build()

        workflow = payload["workflows"][0]
        self.assertEqual(workflow["status"], "template_ready_no_confirmed_file")
        self.assertEqual(workflow["template_items"], 2)
        self.assertEqual(workflow["dry_run_command"], "python dry-run.py")
        self.assertIn("python write.py --write", workflow["next_action"])
        self.assertEqual(payload["summary"]["template_items"], 2)

    def test_confirmed_rows_with_skip_reasons_are_summarized(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = {
                "official_detail": {
                    "confirmed": _write_json(
                        root / "official_confirmed.json",
                        {
                            "items": [
                                {"manual_confirmed": True, "name_ko": "A"},
                                {"manual_confirmed": True, "name_ko": "B"},
                            ]
                        },
                    ),
                    "template": _write_json(root / "official.template.json", {"items": []}),
                    "report": _write_json(
                        root / "official_report.json",
                        {
                            "updated_rows": 0,
                            "skipped_rows": 2,
                            "skipped_sample": [
                                {"name_ko": "A", "reason": "no_empty_fields"},
                                {"name_ko": "B", "reason": "no_empty_fields"},
                            ],
                        },
                    ),
                    "artifact": root / "official.html",
                    "description": "official candidates",
                    "dry_run_command": "python dry.py",
                    "write_command": "python write.py --write",
                }
            }

            with patch.object(audit, "WORKFLOWS", config):
                payload = audit.build()

        workflow = payload["workflows"][0]
        self.assertEqual(workflow["status"], "confirmed_rows_all_skipped")
        self.assertEqual(workflow["manual_confirmed_true"], 2)
        self.assertEqual(workflow["import_report"]["skip_reason_counts"], [("no_empty_fields", 2)])
        self.assertEqual(payload["summary"]["skipped_rows"], 2)

    def test_default_workflows_match_current_readiness_scope(self):
        self.assertEqual(len(audit.WORKFLOWS), 12)
        for name in (
            "source_discovery",
            "catalog_image",
            "focus_image",
            "variant_metadata",
            "ichiban_metadata",
            "animation_category",
            "deduplication",
        ):
            self.assertIn(name, audit.WORKFLOWS)

    def test_current_importer_workflows_use_importer_default_paths(self):
        expected = {
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
            workflow = audit.WORKFLOWS[workflow_name]
            self.assertEqual(workflow["confirmed"], importer.DEFAULT_QUEUE, workflow_name)
            self.assertEqual(workflow["template"], importer.FALLBACK_QUEUE, workflow_name)
            self.assertEqual(workflow["report"], importer.DEFAULT_REPORT, workflow_name)

    def test_focus_image_workflow_exposes_current_import_command(self):
        workflow = audit.audit_workflow("focus_image", audit.WORKFLOWS["focus_image"])

        self.assertIn("import_confirmed_requested_focus_rows.py", workflow["dry_run_command"])
        self.assertIn("requested_focus_confirmed_rows.json", workflow["write_command"])

    def test_variant_metadata_workflow_exposes_public_template_import_command(self):
        workflow = audit.audit_workflow("variant_metadata", audit.WORKFLOWS["variant_metadata"])

        self.assertIn("import_confirmed_variant_metadata_backfill_rows.py", workflow["dry_run_command"])
        self.assertEqual(
            audit.WORKFLOWS["variant_metadata"]["artifact"].name,
            "source_discovery_next_focus_variant_metadata_confirmed_rows.template.json",
        )


if __name__ == "__main__":
    unittest.main()
