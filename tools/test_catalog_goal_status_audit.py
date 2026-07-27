from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_catalog_goal_status as goal_status
from audit_catalog_goal_status import build


def _write_json(path: Path, payload) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _make_db(path: Path) -> Path:
    with sqlite3.connect(path) as conn:
        conn.execute("create table goods_catalog (id integer primary key, is_active integer)")
        conn.executemany(
            "insert into goods_catalog (is_active) values (?)",
            [(1,), (1,), (0,)],
        )
    return path


class CatalogGoalStatusAuditTests(unittest.TestCase):
    def test_default_inputs_use_public_catalog_and_current_queues(self):
        self.assertEqual(goal_status.DEFAULT_SEED.name, "catalog_public.json")
        self.assertEqual(goal_status.DEFAULT_FIELD_QUEUE.name, "catalog_field_enrichment_queue_current.json")
        self.assertEqual(goal_status.DEFAULT_FIELD_BATCHES.name, "catalog_field_review_batches_current.json")
        self.assertEqual(goal_status.DEFAULT_IMAGE_QUEUE.name, "catalog_image_enrichment_queue_current.json")

    def test_build_accepts_public_catalog_object_seed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = argparse.Namespace(
                seed=_write_json(root / "catalog_public.json", {"items": [{"source_store": "A", "category": "B"}]}),
                quality=_write_json(root / "quality.json", {"missing_enrichment": {"image_url": 1}}),
                field_queue=_write_json(root / "field_queue.json", {}),
                field_batches=_write_json(root / "field_batches.json", {}),
                image_queue=_write_json(root / "image_queue.json", {}),
                official_detail_queue=_write_json(root / "official_detail.json", {}),
                official_detail_batches=_write_json(root / "official_detail_batches.json", {}),
                storefront_queue=_write_json(root / "storefront.json", {}),
                storefront_batches=_write_json(root / "storefront_batches.json", {}),
                ichiban_ocr_queue=_write_json(root / "ichiban_ocr.json", {}),
                discovery=_write_json(root / "discovery.json", {}),
                metadata_audit=_write_json(root / "metadata.json", {}),
                ichiban_campaign_gap_audit=_write_json(root / "gap.json", {}),
                ichiban_prize_structure_audit=_write_json(root / "structure.json", {}),
                animation_category_audit=_write_json(root / "animation.json", {}),
                animation_enrichment_priority=_write_json(root / "animation_priority.json", {}),
                barcode_applicability_audit=_write_json(root / "barcode.json", {}),
                metadata_applicability_audit=_write_json(root / "metadata_applicability.json", {}),
                source_image_applicability_audit=_write_json(root / "source_image.json", {}),
                prize_provider_fallback_audit=_write_json(root / "prize_provider.json", {}),
                focus_missing_image_queue=_write_json(root / "focus.json", {}),
                confirmed_import_audit=_write_json(root / "confirmed_import.json", {}),
                confirmed_archive_report=_write_json(root / "archive.json", {}),
                store_source_netloc_audit=_write_json(root / "netloc.json", {}),
                boss_review_ledger=_write_json(root / "boss_ledger.json", {}),
                boss_review_batch=_write_json(root / "boss_batch.json", {}),
                db=root / "missing.db",
            )

            payload = build(args)

        self.assertEqual(payload["rows"], 1)
        self.assertEqual(payload["boss_review"]["pending_items"], 1)
        self.assertEqual(payload["boss_review"]["remaining_batches"], 1)
        self.assertIn("boss review gate", [action["area"] for action in payload["next_actions"]])

    def test_build_includes_ichiban_and_animation_workstream_summaries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            args = argparse.Namespace(
                seed=_write_json(
                    root / "seed.json",
                    [
                        {
                            "source_store": "Animate",
                            "name_ko": "A",
                            "name_ja": "A",
                            "category": "Badge",
                            "affiliation": "Series",
                        },
                        {
                            "source_store": "Animate",
                            "name_ko": "B",
                            "name_ja": "B",
                            "category": "Badge",
                            "affiliation": "Series",
                        },
                    ],
                ),
                quality=_write_json(root / "quality.json", {"missing_enrichment": {"image_url": 2, "barcode": 3}}),
                field_queue=_write_json(
                    root / "field_queue.json",
                    {
                        "missing_total": 5,
                        "actionable_missing_total": 4,
                        "non_actionable_missing_total": 1,
                        "by_field": [["barcode", 3]],
                        "by_strategy": [["manual_review", 3]],
                    },
                ),
                field_batches=_write_json(
                    root / "field_batches.json",
                    {
                        "queue_rows": 5,
                        "actionable_rows": 4,
                        "non_actionable_rows": 1,
                        "batch_count": 2,
                        "by_field": [["barcode", 3]],
                        "by_workflow": [["manual_barcode_evidence", 1]],
                        "by_applicability": [["actionable", 4]],
                    },
                ),
                image_queue=_write_json(
                    root / "image_queue.json",
                    {
                        "missing_images": 2,
                        "by_strategy": [["official_search", 2]],
                        "top_strategy_stores": [],
                    },
                ),
                official_detail_queue=_write_json(
                    root / "official.json",
                    {
                        "target_items": 10,
                        "candidate_rows": 20,
                        "by_status": [["needs_manual_title_review", 4]],
                    },
                ),
                official_detail_batches=_write_json(
                    root / "official_batches.json",
                    {
                        "reviewable_seed_rows": 2,
                        "reviewable_candidate_rows": 5,
                        "by_workflow": {"manual_small_set_review": 2},
                    },
                ),
                storefront_queue=_write_json(
                    root / "storefront.json",
                    {
                        "generic_queue_rows": 1,
                        "fanding_queue_rows": 0,
                        "reviewable_candidates": 6,
                        "image_reviewable_candidates": 4,
                        "image_reviewable_seed_rows": 2,
                        "manual_only_rows": 1,
                    },
                ),
                storefront_batches=_write_json(
                    root / "storefront_batches.json",
                    {
                        "reviewable_seed_rows": 2,
                        "reviewable_candidate_rows": 4,
                        "by_workflow": {"manual_image_review": 2},
                    },
                ),
                ichiban_ocr_queue=_write_json(root / "ocr.json", {"rows": 0, "primary_review_rows": 0}),
                discovery=_write_json(root / "discovery.json", {"existing_rows": 1, "discovered_new_rows": 0}),
                metadata_audit=_write_json(
                    root / "metadata.json",
                    {
                        "urls_with_missing_metadata": 3,
                        "audited_urls": 3,
                        "failures": [],
                        "rows_missing_release_date": 1,
                        "rows_missing_official_price_jpy": 2,
                        "safe_release_url_count": 0,
                        "safe_price_url_count": 0,
                    },
                ),
                ichiban_campaign_gap_audit=_write_json(
                    root / "gaps.json",
                    {
                        "campaign_count": 10,
                        "seeded_campaign_url_count": 8,
                        "campaign_gap_count": 2,
                        "audited_gap_count": 2,
                        "by_status": [["http_error", 2]],
                        "by_classification": [["official_online_archive_404", 2]],
                    },
                ),
                ichiban_prize_structure_audit=_write_json(
                    root / "structure.json",
                    {
                        "campaign_count": 10,
                        "seeded_campaign_url_count": 8,
                        "campaign_without_seed_rows_count": 2,
                        "prize_rows": 100,
                        "missing_sub_series_rows": 7,
                        "fillable_sub_series_rows": 0,
                    },
                ),
                animation_category_audit=_write_json(
                    root / "animation.json",
                    {
                        "rows": 12,
                        "category_count": 3,
                        "normalization_suggestions": [],
                        "unknown_categories": [],
                        "category_families": [{"family": "figure", "rows": 5}],
                    },
                ),
                animation_enrichment_priority=_write_json(
                    root / "animation_priority.json",
                    {
                        "queue_groups": 2,
                        "queue_rows": 9,
                        "missing_image_rows": 7,
                        "missing_source_rows": 9,
                        "by_workflow": [["find_exact_source_url", 9]],
                        "items": [
                            {
                                "priority": 1,
                                "workflow": "find_exact_source_url",
                                "category": "피규어",
                                "source_store": "굿스마일컴퍼니",
                                "rows": 5,
                            }
                        ],
                    },
                ),
                barcode_applicability_audit=_write_json(
                    root / "barcode.json",
                    {
                        "barcode_missing_rows": 3,
                        "actionable_barcode_rows": 1,
                        "non_actionable_barcode_rows": 2,
                        "kuji_not_public_barcode_rows": 2,
                        "manual_only_or_not_public_rows": 0,
                        "by_applicability": [
                            {"value": "not_publicly_available", "rows": 2},
                            {"value": "actionable", "rows": 1},
                        ],
                        "actionable_top_source_stores": [{"value": "Animate", "rows": 1}],
                    },
                ),
                metadata_applicability_audit=_write_json(
                    root / "metadata_applicability.json",
                    {
                        "metadata_missing_rows": 4,
                        "metadata_actionable_rows": 3,
                        "metadata_automation_candidate_rows": 2,
                        "fields": {
                            "release_date": {
                                "missing_rows": 3,
                                "actionable_rows": 3,
                                "automation_candidate_rows": 2,
                            },
                            "official_price_jpy": {
                                "missing_rows": 1,
                                "actionable_rows": 0,
                                "automation_candidate_rows": 0,
                            },
                        },
                    },
                ),
                source_image_applicability_audit=_write_json(
                    root / "source_image_applicability.json",
                    {
                        "source_image_missing_rows": 5,
                        "source_image_actionable_rows": 5,
                        "source_image_automation_candidate_rows": 4,
                        "missing_image_and_source_url": 2,
                        "has_image_but_missing_source_url": 1,
                        "image_provider_candidate_items": 3,
                        "image_manual_or_blocked_items": 2,
                        "fields": {
                            "source_url": {
                                "missing_rows": 3,
                                "actionable_rows": 3,
                                "automation_candidate_rows": 2,
                            },
                            "image_url": {
                                "missing_rows": 2,
                                "actionable_rows": 2,
                                "automation_candidate_rows": 2,
                            },
                        },
                    },
                ),
                prize_provider_fallback_audit=_write_json(
                    root / "fallback.json",
                    {
                        "summary": {
                            "target_stores": ["FuRyu", "Taito"],
                            "searched_rows": 6,
                            "fallback_candidate_rows": 4,
                            "unresolved_rows": 2,
                        },
                        "items": [],
                    },
                ),
                focus_missing_image_queue=_write_json(
                    root / "focus_missing.json",
                    {
                        "focus_count": 3,
                        "focus_rows": 20,
                        "focus_missing_image_rows": 7,
                        "focus_missing_source_rows": 6,
                        "focus_missing_image_and_source_rows": 5,
                        "focus_summaries": [
                            {
                                "focus_key": "danganronpa",
                                "focus_label": "단간론파",
                                "rows": 9,
                                "missing_image_rows": 4,
                                "missing_source_rows": 3,
                            }
                        ],
                    },
                ),
                confirmed_import_audit=_write_json(
                    root / "confirmed.json",
                    {
                        "summary": {
                            "workflow_count": 1,
                            "confirmed_files": 0,
                            "manual_confirmed_true": 0,
                            "template_items": 2,
                            "updated_rows": 0,
                            "skipped_rows": 0,
                            "duplicates": 0,
                        },
                        "workflows": [
                            {
                                "name": "storefront",
                                "status": "template_ready_no_confirmed_file",
                                "manual_confirmed_true": 0,
                                "template_items": 2,
                                "next_action": "Review template.",
                            }
                        ],
                    },
                ),
                confirmed_archive_report=_write_json(
                    root / "archive.json",
                    {
                        "summary": {
                            "queued_items": 2,
                            "archivable_items": 2,
                            "remaining_items": 0,
                            "archived_items": 0,
                            "archive_items": 2,
                        },
                        "workflows": [],
                    },
                ),
                store_source_netloc_audit=_write_json(
                    root / "store_source.json",
                    {"mismatch_count": 2, "by_severity": [["external_evidence_source", 2]]},
                ),
                boss_review_ledger=_write_json(
                    root / "boss_ledger.json",
                    {
                        "meta": {"approved_statuses": ["fixed_pass", "pass"]},
                        "decisions": [
                            {"row_index": 0, "status": "pass"},
                            {"row_index": 1, "status": "image_error"},
                        ],
                    },
                ),
                boss_review_batch=_write_json(
                    root / "boss_batch.json",
                    {
                        "meta": {
                            "selected_items": 10,
                            "first_row_index": 2,
                            "last_row_index": 11,
                            "batch_number": 2,
                        }
                    },
                ),
                db=_make_db(root / "test.db"),
            )

            payload = build(args)

        self.assertEqual(payload["db"]["active_rows"], 2)
        self.assertEqual(payload["field_batches"]["batch_count"], 2)
        self.assertEqual(payload["boss_review"]["reviewed_items"], 2)
        self.assertEqual(payload["boss_review"]["pending_items"], 0)
        self.assertEqual(payload["boss_review"]["approved_items"], 1)
        self.assertEqual(payload["boss_review"]["blocked_items"], 1)
        self.assertEqual(payload["boss_review"]["current_batch_number"], 2)
        self.assertEqual(payload["ichiban_metadata"]["safe_price_url_count"], 0)
        self.assertEqual(payload["ichiban_campaign_gaps"]["campaign_gap_count"], 2)
        self.assertEqual(payload["ichiban_prize_structure"]["missing_sub_series_rows"], 7)
        self.assertEqual(payload["animation_goods_categories"]["unknown_categories"], 0)
        self.assertEqual(payload["animation_enrichment_priority"]["queue_rows"], 9)
        self.assertEqual(payload["barcode_applicability"]["actionable_barcode_rows"], 1)
        self.assertEqual(payload["barcode_applicability"]["kuji_not_public_barcode_rows"], 2)
        self.assertEqual(payload["metadata_applicability"]["metadata_automation_candidate_rows"], 2)
        self.assertEqual(payload["metadata_applicability"]["fields"]["release_date"]["actionable_rows"], 3)
        self.assertEqual(payload["source_image_applicability"]["source_image_automation_candidate_rows"], 4)
        self.assertEqual(payload["source_image_applicability"]["missing_image_and_source_url"], 2)
        self.assertEqual(payload["prize_provider_fallback_images"]["summary"]["fallback_candidate_rows"], 4)
        self.assertEqual(payload["focus_missing_images"]["focus_missing_image_rows"], 7)
        self.assertEqual(payload["animation_enrichment_priority"]["items"][0]["category"], "피규어")
        self.assertEqual(payload["confirmed_import_queues"]["summary"]["template_items"], 2)
        self.assertEqual(payload["confirmed_archive"]["summary"]["archivable_items"], 2)
        self.assertEqual(payload["store_source_netloc_audit"]["mismatch_count"], 2)
        areas = [action["area"] for action in payload["next_actions"]]
        self.assertNotIn("boss review gate", areas)
        self.assertIn("storefront images", areas)
        self.assertIn("official detail images", areas)
        self.assertIn("Ichiban Kuji campaign gaps", areas)
        self.assertIn("Ichiban Kuji metadata", areas)
        self.assertIn("barcodes", areas)
        barcode_action = next(action for action in payload["next_actions"] if action["area"] == "barcodes")
        self.assertIn("1 actionable", barcode_action["evidence"])
        self.assertIn("2 kuji rows", barcode_action["evidence"])
        self.assertIn("field review batches", areas)
        self.assertIn("animation goods exact sources", areas)
        self.assertIn("prize image fallback review", areas)
        self.assertIn("focus missing image queue", areas)
        fallback_action = next(action for action in payload["next_actions"] if action["area"] == "prize image fallback review")
        self.assertIn("4 review-only", fallback_action["evidence"])
        focus_action = next(action for action in payload["next_actions"] if action["area"] == "focus missing image queue")
        self.assertIn("7 focus rows", focus_action["evidence"])
        animation_action = next(action for action in payload["next_actions"] if action["area"] == "animation goods exact sources")
        self.assertIn("animation_enrichment_priority_queue.html", animation_action["action"])
        self.assertIn("confirmed queue: storefront", areas)
        self.assertIn("confirmed queue archive", areas)
        self.assertIn("external evidence sources", areas)


if __name__ == "__main__":
    unittest.main()
