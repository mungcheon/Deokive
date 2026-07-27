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
