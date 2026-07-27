from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_catalog_report_consistency as audit


class CatalogReportConsistencyAuditTests(unittest.TestCase):
    def test_default_field_artifacts_use_current_reports(self) -> None:
        self.assertEqual(audit.DEFAULT_FIELD_QUEUE.name, "catalog_field_enrichment_queue_current.json")
        self.assertEqual(audit.DEFAULT_FIELD_BATCHES.name, "catalog_field_review_batches_current.json")
        self.assertEqual(audit.DEFAULT_IMAGE_QUEUE.name, "catalog_image_enrichment_queue_current.json")
        self.assertEqual(audit.DEFAULT_FIELD_UPDATE_WORK_PACKS.parent.name, "field_update_work_packs")
        self.assertEqual(audit.DEFAULT_WORK_PACK_COVERAGE_AUDIT.name, "catalog_work_pack_coverage_audit.json")

    def test_build_report_accepts_matching_counts(self) -> None:
        report = audit.build_report(
            {"rows": 2, "missing_enrichment": {"image_url": 2, "source_url": 3}},
            {"missing_total": 5, "by_field": [["image_url", 2], ["source_url", 3]]},
            {"queue_rows": 5},
            {
                "missing_images": 2,
                "items": [
                    {"row_index": 10, "source_url": ""},
                    {"row_index": 11, "source_url": "https://example.test/product"},
                    {"row_index": 12, "source_url": ""},
                ],
            },
            {"missing_images": 2},
            {"missing_images": 2},
            {"missing_images": 2},
            {"summary": {"source_discovery_rows": 1}},
            {"items": [{"row_index": 12}]},
            {
                "summary": {
                    "input_items": 3,
                    "ready_items": 1,
                    "rejected_items": 2,
                    "rejected_reasons": [["image_already_present", 1], ["unsafe_source_image_pair", 1]],
                },
                "items": [{"row_index": 20}],
            },
            {
                "summary": {
                    "input_items": 4,
                    "ready_items": 0,
                    "rejected_items": 4,
                    "rejected_reasons": [["image_already_present", 4]],
                },
                "items": [],
            },
            {
                "seed_rows": 2,
                "seed_keys": 2,
                "db_count": 1,
                "databases": [{"ok": True, "active_rows": 2, "missing_images": 2}],
            },
            image_update_work_packs={
                "pack_count": 1,
                "target_rows": 2,
                "packs": [{"rows": 2}],
            },
            field_update_work_packs={
                "pack_count": 2,
                "target_rows": 3,
                "packs": [{"rows": 1, "field": "source_url"}, {"rows": 2, "field": "source_url"}],
            },
            work_pack_coverage_audit={
                "missing_enrichment": {"image_url": 2, "source_url": 3},
                "image_coverage": {"missing": 2},
                "image_work_packs": {"pack_count": 1, "target_rows": 2},
                "field_update_work_packs": {
                    "pack_count": 2,
                    "target_rows": 3,
                    "by_field": {"source_url": 3},
                },
                "field_coverage": {"source_url": {"missing": 3}},
            },
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["failure_count"], 0)

    def test_build_report_checks_image_update_work_pack_manifest(self) -> None:
        report = audit.build_report(
            {"rows": 2, "missing_enrichment": {"image_url": 2}},
            {"missing_total": 2, "by_field": {"image_url": 2}},
            {"queue_rows": 2},
            {"missing_images": 2, "items": []},
            {"missing_images": 2},
            image_update_work_packs={
                "pack_count": 2,
                "target_rows": 3,
                "packs": [{"rows": 2}],
            },
        )

        self.assertFalse(report["ok"])
        names = {item["name"]: item["delta"] for item in report["failures"]}
        self.assertEqual(names["image_update_work_pack_count_matches_manifest"], -1)
        self.assertEqual(names["image_update_work_pack_rows_match_manifest"], -1)

    def test_build_report_checks_field_update_work_pack_manifest(self) -> None:
        report = audit.build_report(
            {"rows": 5, "missing_enrichment": {"source_url": 5}},
            {"missing_total": 5, "by_field": {"source_url": 5}},
            {"queue_rows": 5},
            {"missing_images": 0, "items": []},
            {"missing_images": 0},
            field_update_work_packs={
                "pack_count": 3,
                "target_rows": 4,
                "packs": [{"rows": 1, "field": "source_url"}, {"rows": 2, "field": "source_url"}],
            },
        )

        self.assertFalse(report["ok"])
        names = {item["name"]: item["delta"] for item in report["failures"]}
        self.assertEqual(names["field_update_work_pack_count_matches_manifest"], -1)
        self.assertEqual(names["field_update_work_pack_rows_match_manifest"], -1)

    def test_build_report_checks_work_pack_coverage_audit(self) -> None:
        report = audit.build_report(
            {"rows": 5, "missing_enrichment": {"image_url": 2, "source_url": 3}},
            {"missing_total": 5, "by_field": {"image_url": 2, "source_url": 3}},
            {"queue_rows": 5},
            {"missing_images": 2, "items": []},
            {"missing_images": 2},
            image_update_work_packs={"pack_count": 1, "target_rows": 2, "packs": [{"rows": 2}]},
            field_update_work_packs={
                "pack_count": 1,
                "target_rows": 3,
                "packs": [{"rows": 3, "field": "source_url"}],
            },
            work_pack_coverage_audit={
                "missing_enrichment": {"image_url": 1, "source_url": 2},
                "image_coverage": {"missing": 1},
                "image_work_packs": {"pack_count": 2, "target_rows": 1},
                "field_update_work_packs": {
                    "pack_count": 2,
                    "target_rows": 2,
                    "by_field": {"source_url": 2},
                },
                "field_coverage": {"source_url": {"missing": 2}},
            },
        )

        self.assertFalse(report["ok"])
        names = {item["name"]: item["delta"] for item in report["failures"]}
        self.assertEqual(names["work_pack_coverage_missing_matches_quality:image_url"], -1)
        self.assertEqual(names["work_pack_coverage_image_pack_count_matches_manifest"], 1)
        self.assertEqual(names["work_pack_coverage_field_target_rows_matches_manifest"], -1)
        self.assertEqual(names["work_pack_coverage_field_by_field_matches_packs:source_url"], -1)

    def test_build_report_reports_mismatch_delta(self) -> None:
        report = audit.build_report(
            {"rows": 2, "missing_enrichment": {"image_url": 2, "source_url": 3}},
            {"missing_total": 4, "by_field": {"image_url": 1, "source_url": 3}},
            {"queue_rows": 4},
            {"missing_images": 2, "items": [{"row_index": 10, "source_url": ""}]},
            {"missing_images": 5},
            {"missing_images": 6},
            {"missing_images": 7},
            {"summary": {"source_discovery_rows": 3}},
            {"items": []},
            {
                "summary": {
                    "input_items": 5,
                    "ready_items": 2,
                    "rejected_items": 2,
                    "rejected_reasons": [["image_already_present", 1]],
                },
                "items": [{"row_index": 20}],
            },
            {
                "summary": {
                    "input_items": 7,
                    "ready_items": 1,
                    "rejected_items": 5,
                    "rejected_reasons": [["image_already_present", 4]],
                },
                "items": [],
            },
            {
                "seed_rows": 1,
                "seed_keys": 2,
                "db_count": 2,
                "databases": [{"ok": True, "active_rows": 3, "missing_images": 4}],
            },
        )

        self.assertFalse(report["ok"])
        names = {item["name"]: item["delta"] for item in report["failures"]}
        self.assertEqual(names["field_queue_missing_total_matches_quality"], -1)
        self.assertEqual(names["image_batches_match_image_queue"], 3)
        self.assertEqual(names["image_batch_plan_matches_image_queue"], 4)
        self.assertEqual(names["image_provider_coverage_matches_image_queue"], 5)
        self.assertEqual(names["source_discovery_matches_no_source_image_queue"], 2)
        self.assertEqual(names["field_queue_by_field_matches_quality:image_url"], -1)
        self.assertEqual(names["agent_image_candidates_ready_items_match_items"], -1)
        self.assertEqual(names["agent_image_candidates_input_items_match_ready_plus_rejected"], -1)
        self.assertEqual(names["agent_image_candidates_rejected_reasons_match_rejected_items"], -1)
        self.assertEqual(names["agent_image_candidates_broad_ready_items_match_items"], -1)
        self.assertEqual(names["agent_image_candidates_broad_input_items_match_ready_plus_rejected"], -1)
        self.assertEqual(names["agent_image_candidates_broad_rejected_reasons_match_rejected_items"], -1)
        self.assertEqual(names["db_sync_seed_rows_match_quality"], -1)
        self.assertEqual(names["db_sync_all_databases_ok"], -1)
        self.assertEqual(names["db_sync_active_rows_match_seed:0"], 1)
        self.assertEqual(names["db_sync_missing_images_match_quality:0"], 2)

    def test_build_report_checks_current_applicability_reports(self) -> None:
        field_queue = {
            "missing_total": 8,
            "by_field": {
                "barcode": 2,
                "release_date": 2,
                "official_price_jpy": 1,
                "source_url": 1,
                "image_url": 2,
            },
            "queue": [
                {
                    "field": "barcode",
                    "actionable_now": True,
                    "source_group": "shop",
                    "applicability": "provider_supported",
                },
                {
                    "field": "barcode",
                    "actionable_now": False,
                    "source_group": "kuji",
                    "applicability": "not_publicly_available",
                },
                {
                    "field": "release_date",
                    "actionable_now": True,
                    "automation_candidate": True,
                },
                {
                    "field": "release_date",
                    "actionable_now": False,
                    "automation_candidate": False,
                },
                {
                    "field": "official_price_jpy",
                    "actionable_now": True,
                    "automation_candidate": False,
                },
                {
                    "field": "source_url",
                    "actionable_now": True,
                    "automation_candidate": True,
                    "search_url": "https://example.test/search",
                },
                {
                    "field": "image_url",
                    "actionable_now": True,
                    "automation_candidate": True,
                    "source_url": "https://example.test/item",
                },
                {
                    "field": "image_url",
                    "actionable_now": False,
                    "automation_candidate": False,
                },
            ],
        }
        barcode = {
            "barcode_missing_rows": 2,
            "actionable_barcode_rows": 1,
            "non_actionable_barcode_rows": 1,
            "kuji_not_public_barcode_rows": 1,
            "manual_only_or_not_public_rows": 0,
        }
        metadata = {
            "metadata_missing_rows": 3,
            "metadata_actionable_rows": 2,
            "metadata_automation_candidate_rows": 1,
            "fields": {
                "release_date": {
                    "missing_rows": 2,
                    "actionable_rows": 1,
                    "non_actionable_rows": 1,
                    "automation_candidate_rows": 1,
                },
                "official_price_jpy": {
                    "missing_rows": 1,
                    "actionable_rows": 1,
                    "non_actionable_rows": 0,
                    "automation_candidate_rows": 0,
                },
            },
        }
        source_image = {
            "source_image_missing_rows": 3,
            "source_image_actionable_rows": 2,
            "source_image_automation_candidate_rows": 2,
            "missing_image_and_source_url": 1,
            "has_image_but_missing_source_url": 2,
            "image_provider_candidate_items": 2,
            "image_manual_or_blocked_items": 1,
            "image_missing_with_exact_source_url": 0,
            "image_missing_with_generic_source_url": 1,
            "fields": {
                "source_url": {
                    "missing_rows": 1,
                    "actionable_rows": 1,
                    "automation_candidate_rows": 1,
                    "evidence_url_rows": 1,
                    "manual_or_no_evidence_rows": 0,
                },
                "image_url": {
                    "missing_rows": 2,
                    "actionable_rows": 1,
                    "automation_candidate_rows": 1,
                    "evidence_url_rows": 1,
                    "manual_or_no_evidence_rows": 1,
                },
            },
        }
        report = audit.build_report(
            {
                "rows": 20,
                "missing_enrichment": {
                    "barcode": 2,
                    "release_date": 2,
                    "official_price_jpy": 1,
                    "source_url": 1,
                    "image_url": 2,
                },
            },
            field_queue,
            {"queue_rows": 8},
            {"missing_images": 2, "items": []},
            {"missing_images": 2},
            barcode_applicability=barcode,
            metadata_applicability=metadata,
            source_image_applicability=source_image,
            image_remaining_audit={
                "provider_candidate_items": 2,
                "manual_or_blocked_items": 1,
                "missing_with_exact_source_url": 0,
                "missing_with_generic_source_url": 1,
            },
            source_bottlenecks={"missing_image_and_source_url": 1, "has_image_but_missing_source_url": 2},
            prize_provider_fallback={
                "summary": {"searched_rows": 2, "fallback_candidate_rows": 1, "unresolved_rows": 1},
                "items": [{"row_index": 1}],
            },
            focus_missing_images={
                "focus_count": 2,
                "focus_rows": 5,
                "focus_missing_image_rows": 3,
                "focus_missing_source_rows": 2,
                "focus_missing_image_and_source_rows": 1,
                "focus_summaries": [
                    {"focus_key": "danganronpa", "missing_image_rows": 2, "missing_source_rows": 1},
                    {"focus_key": "frieren", "missing_image_rows": 1, "missing_source_rows": 1},
                ],
                "items": [{"row_index": 1}, {"row_index": 2}, {"row_index": 3}],
            },
            focus_image_template={
                "items": [
                    {"row_index": 1, "manual_confirmed": False},
                    {"row_index": 2, "manual_confirmed": False},
                    {"row_index": 3, "manual_confirmed": False},
                ]
            },
            confirmed_import={
                "workflows": [
                    {
                        "name": "focus_image",
                        "template_items": 3,
                        "manual_confirmed_true": 0,
                    }
                ]
            },
            ichiban_history_status={
                "campaign_count": 4,
                "seeded_campaign_url_count": 3,
                "campaign_gap_count": 1,
                "audited_gap_count": 1,
                "prize_rows": 12,
                "missing_sub_series_rows": 0,
                "metadata": {
                    "urls_with_missing_metadata": 2,
                    "rows_missing_release_date": 1,
                    "rows_missing_official_price_jpy": 3,
                    "safe_release_url_count": 0,
                    "safe_price_url_count": 1,
                    "blocked_rows": 4,
                    "safe_update_url_count": 1,
                },
            },
            ichiban_metadata={
                "urls_with_missing_metadata": 2,
                "rows_missing_release_date": 1,
                "rows_missing_official_price_jpy": 3,
                "safe_release_url_count": 0,
                "safe_price_url_count": 1,
            },
            ichiban_campaign_gap={
                "campaign_count": 4,
                "seeded_campaign_url_count": 3,
                "campaign_gap_count": 1,
                "audited_gap_count": 1,
            },
            ichiban_prize_structure={
                "campaign_count": 4,
                "seeded_campaign_url_count": 3,
                "prize_rows": 12,
                "missing_sub_series_rows": 0,
            },
            goal_status={
                "missing_enrichment": {
                    "barcode": 2,
                    "release_date": 2,
                    "official_price_jpy": 1,
                    "source_url": 1,
                    "image_url": 2,
                },
                "barcode_applicability": barcode,
                "metadata_applicability": {
                    "metadata_missing_rows": 3,
                    "metadata_actionable_rows": 2,
                    "metadata_automation_candidate_rows": 1,
                },
                "source_image_applicability": {
                    "source_image_missing_rows": 3,
                    "source_image_actionable_rows": 2,
                    "source_image_automation_candidate_rows": 2,
                    "missing_image_and_source_url": 1,
                    "has_image_but_missing_source_url": 2,
                    "image_provider_candidate_items": 2,
                    "image_manual_or_blocked_items": 1,
                },
                "prize_provider_fallback_images": {
                    "summary": {"searched_rows": 2, "fallback_candidate_rows": 1, "unresolved_rows": 1}
                },
                "focus_missing_images": {
                    "focus_count": 2,
                    "focus_rows": 5,
                    "focus_missing_image_rows": 3,
                    "focus_missing_source_rows": 2,
                    "focus_missing_image_and_source_rows": 1,
                },
                "ichiban_metadata": {
                    "urls_with_missing_metadata": 2,
                    "rows_missing_release_date": 1,
                    "rows_missing_official_price_jpy": 3,
                    "safe_release_url_count": 0,
                    "safe_price_url_count": 1,
                },
                "ichiban_campaign_gaps": {
                    "campaign_count": 4,
                    "seeded_campaign_url_count": 3,
                    "campaign_gap_count": 1,
                    "audited_gap_count": 1,
                },
                "ichiban_prize_structure": {
                    "campaign_count": 4,
                    "seeded_campaign_url_count": 3,
                    "prize_rows": 12,
                    "missing_sub_series_rows": 0,
                },
            },
        )

        self.assertTrue(report["ok"], report["failures"])

    def test_build_report_reports_applicability_mismatches(self) -> None:
        report = audit.build_report(
            {"rows": 1, "missing_enrichment": {"barcode": 1, "image_url": 1}},
            {
                "missing_total": 2,
                "by_field": {"barcode": 1, "image_url": 1},
                "queue": [
                    {
                        "field": "barcode",
                        "actionable_now": False,
                        "source_group": "kuji",
                        "applicability": "not_publicly_available",
                    },
                    {"field": "image_url", "actionable_now": True, "automation_candidate": True},
                ],
            },
            {"queue_rows": 2},
            {"missing_images": 1, "items": []},
            {"missing_images": 1},
            barcode_applicability={"barcode_missing_rows": 0, "actionable_barcode_rows": 1},
            source_image_applicability={
                "source_image_missing_rows": 0,
                "source_image_actionable_rows": 0,
                "source_image_automation_candidate_rows": 0,
                "fields": {
                    "image_url": {
                        "missing_rows": 0,
                        "actionable_rows": 0,
                        "automation_candidate_rows": 0,
                        "evidence_url_rows": 1,
                        "manual_or_no_evidence_rows": 0,
                    }
                },
            },
            prize_provider_fallback={
                "summary": {"searched_rows": 2, "fallback_candidate_rows": 2, "unresolved_rows": 1},
                "items": [{"row_index": 1}],
            },
            focus_missing_images={
                "focus_count": 2,
                "focus_rows": 5,
                "focus_missing_image_rows": 3,
                "focus_missing_source_rows": 4,
                "focus_missing_image_and_source_rows": 1,
                "focus_summaries": [
                    {"focus_key": "danganronpa", "missing_image_rows": 2, "missing_source_rows": 1},
                ],
                "items": [{"row_index": 1}],
            },
            focus_image_template={
                "items": [
                    {"row_index": 1, "manual_confirmed": True},
                    {"row_index": 2, "manual_confirmed": False},
                ]
            },
            confirmed_import={
                "workflows": [
                    {
                        "name": "focus_image",
                        "template_items": 2,
                        "manual_confirmed_true": 1,
                    }
                ]
            },
            ichiban_history_status={
                "campaign_count": 4,
                "seeded_campaign_url_count": 3,
                "campaign_gap_count": 1,
                "audited_gap_count": 1,
                "prize_rows": 12,
                "missing_sub_series_rows": 0,
                "metadata": {
                    "urls_with_missing_metadata": 2,
                    "rows_missing_release_date": 1,
                    "rows_missing_official_price_jpy": 3,
                    "safe_release_url_count": 0,
                    "safe_price_url_count": 1,
                    "blocked_rows": 4,
                    "safe_update_url_count": 1,
                },
            },
            ichiban_metadata={
                "urls_with_missing_metadata": 4,
                "rows_missing_release_date": 1,
                "rows_missing_official_price_jpy": 2,
                "safe_release_url_count": 0,
                "safe_price_url_count": 0,
            },
            ichiban_campaign_gap={
                "campaign_count": 5,
                "seeded_campaign_url_count": 3,
                "campaign_gap_count": 2,
                "audited_gap_count": 1,
            },
            ichiban_prize_structure={
                "campaign_count": 4,
                "seeded_campaign_url_count": 2,
                "prize_rows": 10,
                "missing_sub_series_rows": 1,
            },
            goal_status={
                "missing_enrichment": {"barcode": 0, "image_url": 1},
                "focus_missing_images": {
                    "focus_count": 1,
                    "focus_rows": 5,
                    "focus_missing_image_rows": 2,
                    "focus_missing_source_rows": 4,
                    "focus_missing_image_and_source_rows": 1,
                },
                "ichiban_metadata": {
                    "urls_with_missing_metadata": 1,
                    "rows_missing_release_date": 1,
                    "rows_missing_official_price_jpy": 2,
                    "safe_release_url_count": 0,
                    "safe_price_url_count": 0,
                },
                "ichiban_campaign_gaps": {
                    "campaign_count": 4,
                    "seeded_campaign_url_count": 3,
                    "campaign_gap_count": 2,
                    "audited_gap_count": 1,
                },
                "ichiban_prize_structure": {
                    "campaign_count": 4,
                    "seeded_campaign_url_count": 2,
                    "prize_rows": 9,
                    "missing_sub_series_rows": 1,
                },
            },
        )

        self.assertFalse(report["ok"])
        names = {item["name"]: item["delta"] for item in report["failures"]}
        self.assertEqual(names["barcode_applicability_missing_matches_field_queue"], -1)
        self.assertEqual(names["barcode_applicability_actionable_matches_field_queue"], 1)
        self.assertEqual(names["source_image_applicability_missing_matches_field_queue:image_url"], -1)
        self.assertEqual(names["source_image_applicability_evidence_matches_field_queue:image_url"], 1)
        self.assertEqual(names["prize_provider_fallback_items_match_summary"], 1)
        self.assertEqual(names["goal_status_prize_provider_fallback_matches_audit:searched_rows"], -2)
        self.assertEqual(names["focus_missing_image_items_match_summary"], 2)
        self.assertEqual(names["focus_missing_image_summary_matches_focuses"], 1)
        self.assertEqual(names["focus_missing_source_summary_matches_focuses"], 3)
        self.assertEqual(names["focus_image_template_items_match_focus_missing_images"], -1)
        self.assertEqual(names["focus_image_template_manual_confirmed_false"], 1)
        self.assertEqual(names["confirmed_import_focus_template_items_match_focus_missing_images"], -1)
        self.assertEqual(names["confirmed_import_focus_manual_confirmed_matches_workflow"], 1)
        self.assertEqual(names["ichiban_history_status_matches_campaign_gap:campaign_count"], -1)
        self.assertEqual(names["ichiban_history_status_matches_campaign_gap:campaign_gap_count"], -1)
        self.assertEqual(names["ichiban_history_status_matches_prize_structure:seeded_campaign_url_count"], 1)
        self.assertEqual(names["ichiban_history_status_matches_prize_structure:prize_rows"], 2)
        self.assertEqual(names["ichiban_history_status_matches_metadata:urls_with_missing_metadata"], -2)
        self.assertEqual(names["ichiban_history_status_matches_metadata:rows_missing_official_price_jpy"], 1)
        self.assertEqual(names["ichiban_history_status_matches_metadata:safe_price_url_count"], 1)
        self.assertEqual(names["ichiban_history_status_metadata_blocked_rows_match_missing_fields"], 1)
        self.assertEqual(names["ichiban_history_status_metadata_safe_updates_match_safe_urls"], 1)
        self.assertEqual(names["ichiban_campaign_gap_matches_prize_structure:campaign_count"], -1)
        self.assertEqual(names["ichiban_campaign_gap_matches_prize_structure:seeded_campaign_url_count"], -1)
        self.assertEqual(names["goal_status_focus_missing_images_matches_audit:focus_count"], -1)
        self.assertEqual(names["goal_status_focus_missing_images_matches_audit:focus_missing_image_rows"], -1)
        self.assertEqual(names["goal_status_missing_enrichment_matches_quality:barcode"], -1)
        self.assertEqual(names["goal_status_ichiban_metadata_matches_audit:urls_with_missing_metadata"], -3)
        self.assertEqual(names["goal_status_ichiban_campaign_gap_matches_audit:campaign_count"], -1)
        self.assertEqual(names["goal_status_ichiban_prize_structure_matches_audit:prize_rows"], -1)


if __name__ == "__main__":
    unittest.main()
