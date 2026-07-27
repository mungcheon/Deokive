from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_public_data_layout as target


class PublicDataLayoutAuditTests(unittest.TestCase):
    def test_current_public_data_layout_passes(self) -> None:
        summary, errors = target.run_audit()

        self.assertEqual([], errors)
        self.assertEqual("pass", summary["status"])
        self.assertGreater(summary["catalog_rows"], 0)
        self.assertIn("ichiban_kuji_campaigns.json", summary["source_lists"])

    def test_rejects_unexpected_tracked_data_root_file(self) -> None:
        errors: list[str] = []

        with patch.object(
            target,
            "git_ls_files_data",
            return_value=["data/catalog_public.json", "data/random_report_public.json"],
        ):
            target.audit_tracked_data_files(errors)

        self.assertTrue(any("Unexpected tracked data files" in error for error in errors))

    def test_allows_agent_intake_records_in_staging_dirs(self) -> None:
        self.assertTrue(target.is_allowed_data_path("data/intake/incoming/agent-run.json"))
        self.assertTrue(target.is_allowed_data_path("data/intake/processed/agent-run.json"))
        self.assertTrue(target.is_allowed_data_path("data/intake/rejected/agent-run.json"))

    def test_rejects_local_data_files_outside_single_db_layout(self) -> None:
        errors: list[str] = []

        with patch.object(
            target,
            "iter_data_filesystem_files",
            return_value=[
                "data/catalog_public.json",
                "data/intake/incoming/agent-run.json",
                "data/extra_catalog_public.json",
            ],
        ):
            summary = target.audit_data_filesystem_layout(errors)

        self.assertEqual(3, summary["data_filesystem_files"])
        self.assertTrue(any("Unexpected local data files" in error for error in errors))

    def test_rejects_invalid_incoming_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            incoming = Path(tmp)
            (incoming / "bad.json").write_text('{"schema_version": 1}', encoding="utf-8")

            with patch.object(target, "INCOMING", incoming):
                summary = target.audit_incoming_intake(errors := [])

        self.assertEqual(1, summary["incoming_files"])
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
