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
