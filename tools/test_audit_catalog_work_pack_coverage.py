from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_catalog_work_pack_coverage as target


class CatalogWorkPackCoverageAuditTests(unittest.TestCase):
    def test_audit_summarizes_missing_rows_against_work_packs(self) -> None:
        quality = {
            "rows": 10,
            "missing_enrichment": {
                "image_url": 4,
                "source_url": 3,
                "release_date": 2,
                "barcode": 5,
                "official_price_jpy": 1,
            },
        }
        backlog = {
            "field_update_work_packs": [{"field": "source_url"}],
            "image_work_packs": [{"strategy": "official_search"}],
            "ichiban_quality": {"work_pack_rows": 2},
        }
        image_manifest = {
            "pack_count": 1,
            "target_rows": 3,
            "packs": [{"rows": 3, "source_store": "Store", "strategy": "official_search"}],
        }
        field_manifest = {
            "pack_count": 2,
            "target_rows": 3,
            "packs": [
                {"rows": 2, "field": "source_url", "source_store": "Store", "risk": "medium"},
                {"rows": 1, "field": "release_date", "source_store": "Store", "risk": "medium"},
            ],
        }
        ichiban_queue = {
            "summary": {
                "queue_rows": 4,
                "campaign_gap_queue_rows": 2,
                "exact_display_duplicate_queue_rows": 1,
                "naming_convention_queue_rows": 1,
                "work_pack_rows": 4,
            }
        }

        report, errors = target.audit(quality, backlog, image_manifest, field_manifest, ichiban_queue)

        self.assertEqual([], errors)
        self.assertEqual("pass", report["status"])
        self.assertEqual(4, report["image_coverage"]["missing"])
        self.assertEqual(3, report["image_coverage"]["work_pack_target_rows"])
        self.assertEqual(1, report["image_coverage"]["uncovered_or_deferred_rows"])
        self.assertEqual(2, report["field_coverage"]["source_url"]["work_pack_target_rows"])
        self.assertEqual(1, report["field_coverage"]["release_date"]["work_pack_target_rows"])
        self.assertEqual(0, report["field_coverage"]["official_price_jpy"]["work_pack_target_rows"])
        self.assertEqual(4, report["ichiban_quality"]["queue_rows"])
        self.assertEqual("barcode", report["next_focus"][0]["workstream"])

    def test_audit_fails_when_manifest_overclaims_missing_rows(self) -> None:
        quality = {"missing_enrichment": {"image_url": 1, "source_url": 1}}
        backlog = {"field_update_work_packs": [], "image_work_packs": []}
        image_manifest = {"pack_count": 1, "target_rows": 2, "packs": []}
        field_manifest = {
            "pack_count": 1,
            "target_rows": 2,
            "packs": [{"rows": 2, "field": "source_url"}],
        }

        report, errors = target.audit(quality, backlog, image_manifest, field_manifest, {})

        self.assertEqual("fail", report["status"])
        self.assertTrue(any("image work-pack target rows exceed" in error for error in errors))
        self.assertTrue(any("source_url work-pack target rows exceed" in error for error in errors))

    def test_run_audit_reports_missing_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report, errors = target.run_audit(
                root / "quality.json",
                root / "backlog.json",
                root / "image.json",
                root / "field.json",
                root / "ichiban.json",
            )

        self.assertEqual("fail", report["status"])
        self.assertEqual(5, len(errors))


if __name__ == "__main__":
    unittest.main()
