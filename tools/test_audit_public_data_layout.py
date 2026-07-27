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
        self.assertEqual(1, summary["public_database_files"])
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

    def test_requires_exactly_one_public_database_file(self) -> None:
        errors: list[str] = []

        with patch.object(
            target,
            "git_ls_files_data",
            return_value=["data/catalog_public_meta.json", "data/site_status_public.json"],
        ):
            target.audit_tracked_data_files(errors)

        self.assertTrue(any("exactly one database file" in error for error in errors))

    def test_allows_agent_intake_records_in_staging_dirs(self) -> None:
        self.assertTrue(target.is_allowed_data_path("data/intake/incoming/agent-run.json"))
        self.assertTrue(target.is_allowed_data_path("data/intake/processed/agent-run.json"))
        self.assertTrue(target.is_allowed_data_path("data/intake/rejected/agent-run.json"))

    def test_rejects_tracked_server_artifacts(self) -> None:
        errors: list[str] = []

        with patch.object(
            target,
            "git_ls_files",
            return_value=["server/catalog_report.json", "server/review.html"],
        ):
            target.audit_tracked_server_artifacts(errors)

        self.assertTrue(any("Unexpected tracked server/local artifacts" in error for error in errors))

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
                summary = target.audit_goods_intake_records(errors := [])

        self.assertEqual(1, summary["incoming_files"])
        self.assertTrue(errors)

    def test_rejects_invalid_field_update_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            incoming = Path(tmp)
            (incoming / "agent-20260727-source-url.json").write_text(
                '{"schema_version": 1, "updates": []}',
                encoding="utf-8",
            )

            with patch.object(target, "FIELD_UPDATES_INCOMING", incoming):
                summary = target.audit_field_update_records(errors := [])

        self.assertEqual(1, summary["field_update_incoming_files"])
        self.assertTrue(errors)

    def test_rejects_invalid_processed_field_update_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "incoming").mkdir()
            (root / "rejected").mkdir()
            processed = root / "processed"
            processed.mkdir()
            (processed / "agent-20260727-source-url.json").write_text(
                '{"schema_version": 1, "updates": [{"catalog_index": 1}]}',
                encoding="utf-8",
            )

            with patch.object(target, "FIELD_UPDATES_INCOMING", root / "incoming"), patch.object(
                target, "FIELD_UPDATES_PROCESSED", processed
            ), patch.object(target, "FIELD_UPDATES_REJECTED", root / "rejected"):
                summary = target.audit_field_update_records(errors := [])

        self.assertEqual(1, summary["field_update_processed_files"])
        self.assertTrue(errors)

    def test_rejects_untraceable_incoming_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            incoming = Path(tmp)
            (incoming / "random.json").write_text(
                """{
                  "schema_version": 1,
                  "agent": {
                    "name": "agent",
                    "run_id": "20260727-topic",
                    "collected_at": "2026-07-27T00:00:00+09:00"
                  },
                  "items": [
                    {
                      "external_id": "sku-1",
                      "display_name": "Sample",
                      "category": "figure",
                      "series_name": "Series",
                      "source_store": "Official",
                      "source_url": "https://example.com/product",
                      "confidence": "confirmed"
                    }
                  ]
                }""",
                encoding="utf-8",
            )

            with patch.object(target, "INCOMING", incoming):
                summary = target.audit_goods_intake_records(errors := [])

        self.assertEqual(1, summary["incoming_files"])
        self.assertTrue(any("intake filename must be" in error for error in errors))

    def test_accepts_traceable_incoming_filename(self) -> None:
        self.assertTrue(target.is_valid_intake_record_name(Path("agent-20260727-ichiban-kuji.json")))
        self.assertFalse(target.is_valid_intake_record_name(Path("agent-run.json")))


if __name__ == "__main__":
    unittest.main()
