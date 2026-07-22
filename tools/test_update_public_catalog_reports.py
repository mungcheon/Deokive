from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import update_public_catalog_reports as reports
from build_metadata_action_queue_public import build_report as build_metadata_action_queue_report


class PublicCatalogReportTests(unittest.TestCase):
    def test_public_report_generation_keeps_site_data_safe_and_consistent(self):
        result = reports.update_reports(write=False)

        self.assertFalse(result["write"])
        self.assertGreater(result["rows"], 0)
        self.assertIn("source_url", result["missing"])
        self.assertIn("image_url", result["missing"])
        self.assertEqual(result["public_validation"]["status"], "pass")
        self.assertGreaterEqual(result["public_validation"]["checked_files"], 30)
        updated_files = {Path(path).as_posix() for path in result["updated_files"]}
        self.assertIn("data/catalog_operations_public.json", updated_files)
        self.assertIn("data/catalog_agent_work_queue_public.json", updated_files)
        self.assertIn("data/requested_focus_enrichment_public.json", updated_files)
        self.assertIn("data/requested_focus_review_batches_public.json", updated_files)
        self.assertIn("data/catalog_confirmed_import_readiness_public.json", updated_files)
        self.assertIn("data/catalog_execution_plan_public.json", updated_files)
        self.assertIn("data/catalog_metadata_review_batches_public.json", updated_files)
        self.assertIn("data/catalog_metadata_action_queue_public.json", updated_files)
        self.assertIn("data/animation_category_action_queue_public.json", updated_files)
        self.assertIn("data/danganronpa_missing_media_public.json", updated_files)

    def test_all_public_json_files_are_parseable_and_safe_for_pages(self):
        public_files = reports.discover_public_json_files()
        self.assertGreaterEqual(len(public_files), 30)
        self.assertIn(reports.PUBLIC_CATALOG, public_files)
        self.assertIn(reports.OPERATIONS_REPORT, public_files)

        validation = reports.validate_all_public_json_files()
        self.assertEqual(validation["status"], "pass", validation["findings"])
        self.assertEqual(validation["checked_files"], len(public_files))

    def test_catalog_currency_invariants_reject_jpy_price_with_krw_purchase(self):
        findings = reports.catalog_currency_invariant_findings(
            {
                "items": [
                    {
                        "catalog_index": 7,
                        "name_ko": "sample",
                        "official_price_jpy": 1980,
                        "default_purchase": {
                            "price": 1980,
                            "currency": "KRW",
                        },
                    }
                ]
            }
        )

        self.assertEqual(
            findings,
            ["catalog row 7 has official_price_jpy but default_purchase.currency=KRW"],
        )

    def test_catalog_currency_invariants_accept_jpy_price_with_jpy_purchase(self):
        findings = reports.catalog_currency_invariant_findings(
            {
                "items": [
                    {
                        "catalog_index": 8,
                        "name_ko": "sample",
                        "official_price_jpy": 1980,
                        "default_purchase": {
                            "price": 1980,
                            "currency": "JPY",
                        },
                    }
                ]
            }
        )

        self.assertEqual(findings, [])

    def test_published_reports_keep_manual_review_guards(self):
        operations = reports.load_json(reports.OPERATIONS_REPORT)
        source_discovery = reports.load_json(reports.SOURCE_DISCOVERY)
        generic_candidates = reports.load_json(reports.GENERIC_SOURCE_PATCH_CANDIDATES)
        deduplication = reports.load_json(reports.DEDUPLICATION)

        scorecard = operations.get("workstream_scorecard", [])
        self.assertGreater(len(scorecard), 0)
        self.assertTrue(all(row.get("auto_apply_enabled") is False for row in scorecard))

        source_items = source_discovery.get("items", [])
        self.assertGreater(len(source_items), 0)
        self.assertTrue(all(item.get("auto_apply_enabled") is False for item in source_items))
        self.assertTrue(all("evidence_required" in item for item in source_items))
        self.assertTrue(all("acceptance_rule" in item for item in source_items))

        generic_summary = generic_candidates.get("summary", {})
        generic_items = generic_candidates.get("items", [])
        self.assertIs(generic_summary.get("auto_apply_enabled"), False)
        self.assertEqual(generic_summary.get("candidate_rows"), len(generic_items))

        requested_focus = reports.load_json(reports.REQUESTED_FOCUS)
        focus_summary = requested_focus.get("summary", {})
        focus_topics = requested_focus.get("topics", [])
        self.assertIs(focus_summary.get("auto_apply_enabled"), False)
        self.assertEqual(focus_summary.get("topic_count"), len(focus_topics))
        self.assertTrue(all(topic.get("auto_apply_enabled") is False for topic in focus_topics))

        danganronpa_media = reports.load_json(reports.DANGANRONPA_MISSING_MEDIA)
        danganronpa_summary = danganronpa_media.get("summary", {})
        danganronpa_items = danganronpa_media.get("items", [])
        danganronpa_batches = danganronpa_media.get("review_batches", [])
        self.assertIs(danganronpa_summary.get("auto_apply_enabled"), False)
        self.assertEqual(danganronpa_summary.get("missing_media_rows"), len(danganronpa_items))
        self.assertEqual(danganronpa_summary.get("review_batch_count"), len(danganronpa_batches))
        self.assertEqual(
            danganronpa_summary.get("missing_media_rows"),
            sum(int(batch.get("rows") or 0) for batch in danganronpa_batches),
        )
        self.assertTrue(all(item.get("auto_apply_enabled") is False for item in danganronpa_items))
        self.assertTrue(all(batch.get("auto_apply_enabled") is False for batch in danganronpa_batches))

        dedupe_summary = deduplication.get("summary", {})
        source_url_exclusions = dedupe_summary.get("source_url_exclusions", {})
        self.assertGreater(source_url_exclusions.get("shared_source_url_value_groups", 0), 0)
        self.assertGreater(source_url_exclusions.get("excluded_shared_source_url_value_groups", 0), 0)
        self.assertLess(
            source_url_exclusions.get("source_url_name_matched_review_groups", 0),
            source_url_exclusions.get("shared_source_url_value_groups", 0),
        )
        self.assertIs(deduplication.get("automation_policy", {}).get("auto_delete"), False)
        self.assertIn(
            "broad same-source-url matches",
            deduplication.get("automation_policy", {}).get("excluded", ""),
        )

    def test_shared_campaign_urls_do_not_become_dedupe_groups(self):
        items = [
            {
                "catalog_index": 1,
                "name_ko": "이치방쿠지 샘플 A상 피규어",
                "category": "피규어",
                "source_url": "https://1kuji.com/products/sample",
                "image_url": "https://example.com/a.jpg",
            },
            {
                "catalog_index": 2,
                "name_ko": "이치방쿠지 샘플 B상 쿠션",
                "category": "생활잡화",
                "source_url": "https://1kuji.com/products/sample",
                "image_url": "https://example.com/b.jpg",
            },
        ]

        dedupe = reports.build_deduplication_public(items)
        self.assertEqual(dedupe["summary"]["duplicate_groups"], 0)
        self.assertEqual(
            dedupe["summary"]["source_url_exclusions"]["shared_source_url_value_groups"],
            1,
        )
        self.assertEqual(
            dedupe["summary"]["source_url_exclusions"]["excluded_shared_source_url_value_groups"],
            1,
        )

    def test_image_actionable_groups_publish_enough_samples_for_action_queue(self):
        items = [
            {
                "catalog_index": index,
                "name_ko": f"스텔라이브 샘플 {index}",
                "category": "캔뱃지",
                "source_store": "Stellive Store",
                "source_url": "https://fanding.kr/@stellive/shop",
                "image_url": None,
            }
            for index in range(12)
        ]

        image_batches = reports.build_image_enrichment_batches_public(items)
        group = image_batches["groups"][0]

        self.assertEqual(group["workflow"], "replace_generic_source_then_extract_image")
        self.assertEqual(group["missing_image_rows"], 12)
        self.assertEqual(len(group["sample_items"]), 12)
        self.assertEqual(
            image_batches["summary"]["sample_image_import_template_count"],
            image_batches["summary"]["generic_source_url_rows"],
        )

    def test_published_reports_expose_home_catalog_work_blocks(self):
        operations = reports.load_json(reports.OPERATIONS_REPORT)
        image_batches = reports.load_json(reports.IMAGE_ENRICHMENT_BATCHES)
        agent_queue = reports.load_json(reports.AGENT_WORK_QUEUE)

        blocker_rows = sum(int(row.get("rows") or 0) for row in image_batches.get("blocker_summary", []))
        self.assertEqual(blocker_rows, image_batches["summary"]["missing_image_rows"])
        image_review_batches = image_batches.get("review_batches", [])
        self.assertEqual(image_batches["summary"]["review_batch_count"], len(image_review_batches))
        self.assertEqual(
            sum(int(batch.get("missing_image_rows") or 0) for batch in image_review_batches),
            sum(int(group.get("missing_image_rows") or 0) for group in image_batches.get("groups", [])),
        )
        self.assertTrue(all(batch.get("auto_apply_enabled") is False for batch in image_review_batches))
        self.assertGreater(image_batches["summary"].get("sample_image_import_template_count", 0), 0)
        self.assertTrue(
            all(
                len({group.get("workflow") for group in batch.get("groups", []) if isinstance(group, dict)}) <= 1
                for batch in image_review_batches
            )
        )
        sample_templates = [
            item.get("catalog_field_import_template")
            for group in image_batches.get("groups", [])
            for item in group.get("sample_items", [])
            if isinstance(item, dict)
        ]
        self.assertGreater(len(sample_templates), 0)
        self.assertTrue(all(isinstance(template, dict) for template in sample_templates))
        self.assertTrue(all(template.get("field") == "image_url" for template in sample_templates))
        self.assertTrue(all(template.get("manual_confirmed") is False for template in sample_templates))
        self.assertTrue(
            any(template.get("blocked_until") == "exact_product_source_url_confirmed" for template in sample_templates)
        )

        batches = agent_queue.get("batches", [])
        top_batches = agent_queue.get("top_next_batches", [])
        self.assertGreater(len(batches), 0)
        self.assertEqual(agent_queue["summary"]["top_next_batch_count"], len(top_batches))
        self.assertEqual(
            [batch["batch_id"] for batch in top_batches],
            [batch["batch_id"] for batch in batches[: len(top_batches)]],
        )

        scorecard_reports = {row.get("primary_report") for row in operations.get("workstream_scorecard", [])}
        next_action_reports = {row.get("public_report") for row in operations.get("next_actions", [])}
        report_links = {row.get("public_report") for row in operations.get("reports", [])}
        open_queues = operations.get("summary", {}).get("open_review_queues", {})
        confirmed_readiness = reports.load_json(reports.CONFIRMED_IMPORT_READINESS)
        readiness_summary = confirmed_readiness.get("summary", {})
        requested_focus_action = reports.load_json(reports.REQUESTED_FOCUS_ACTION_QUEUE)
        requested_focus_action_summary = requested_focus_action.get("summary", {})
        requested_focus_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "requested_focus_action_queue"
        )
        requested_focus_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "requested_focus_action_queue"
        )
        image_action = reports.load_json(reports.IMAGE_ATTACHMENT_ACTION_QUEUE)
        image_action_summary = image_action.get("summary", {})
        source_action = reports.load_json(reports.SOURCE_DISCOVERY_ACTION_QUEUE)
        source_action_summary = source_action.get("summary", {})
        source_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_discovery_action_queue"
        )
        source_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_discovery_action_queue"
        )
        metadata_action = reports.load_json(reports.METADATA_ACTION_QUEUE)
        metadata_action_summary = metadata_action.get("summary", {})
        metadata_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "metadata_action_queue"
        )
        metadata_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "metadata_action_queue"
        )
        image_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "image_attachment_action_queue"
        )
        image_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "image_attachment_action_queue"
        )
        dedupe_action = reports.load_json(reports.DEDUPLICATION_ACTION_QUEUE)
        dedupe_action_summary = dedupe_action.get("summary", {})
        dedupe_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "deduplication_action_queue"
        )
        dedupe_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "deduplication_action_queue"
        )
        ichiban_action = reports.load_json(reports.ICHIIBAN_KUJI_METADATA_ACTION_QUEUE)
        ichiban_action_summary = ichiban_action.get("summary", {})
        ichiban_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "ichiban_kuji_metadata_action_queue"
        )
        ichiban_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ichiban_kuji_metadata_action_queue"
        )
        animation_action = reports.load_json(reports.ANIMATION_CATEGORY_ACTION_QUEUE)
        animation_action_summary = animation_action.get("summary", {})
        animation_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "animation_category_action_queue"
        )
        animation_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "animation_category_action_queue"
        )
        animation_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "animation_category_action_queue"
        ]
        self.assertIn(f"data/{reports.IMAGE_ENRICHMENT_BATCHES.name}", scorecard_reports)
        self.assertIn(f"data/{reports.REQUESTED_FOCUS.name}", scorecard_reports)
        self.assertIn(f"data/{reports.DANGANRONPA_MISSING_MEDIA.name}", scorecard_reports)
        self.assertIn(f"data/{reports.AGENT_WORK_QUEUE.name}", next_action_reports)
        self.assertIn(f"data/{reports.EXECUTION_PLAN.name}", next_action_reports)
        self.assertIn(f"data/{reports.CONFIRMED_IMPORT_READINESS.name}", report_links)
        self.assertIn(f"data/{reports.ANIMATION_CATEGORY_ACTION_QUEUE.name}", report_links)
        self.assertEqual(
            open_queues.get("confirmed_import_action_queue_rows"),
            readiness_summary.get("public_action_queue_rows"),
        )
        self.assertEqual(
            open_queues.get("requested_focus_action_rows"),
            requested_focus_action_summary.get("queued_action_rows"),
        )
        self.assertEqual(
            open_queues.get("requested_focus_actionable_rows"),
            requested_focus_action_summary.get("actionable_template_rows"),
        )
        self.assertEqual(
            open_queues.get("requested_focus_unqueued_actionable_rows"),
            requested_focus_action_summary.get("unqueued_actionable_rows"),
        )
        self.assertEqual(
            open_queues.get("requested_focus_barcode_template_rows_excluded"),
            requested_focus_action_summary.get("barcode_template_rows_excluded"),
        )
        self.assertEqual(
            requested_focus_scorecard.get("queue_coverage"),
            requested_focus_action_summary.get("queue_coverage"),
        )
        self.assertEqual(
            requested_focus_next_action.get("non_barcode_template_share"),
            requested_focus_action_summary.get("non_barcode_template_share"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_action_rows"),
            image_action_summary.get("queued_image_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_action_rows"),
            source_action_summary.get("queued_source_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_actionable_rows"),
            source_action_summary.get("actionable_source_rows"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_unqueued_actionable_rows"),
            source_action_summary.get("unqueued_actionable_source_rows"),
        )
        self.assertEqual(
            source_scorecard.get("queue_coverage"),
            source_action_summary.get("queue_coverage"),
        )
        self.assertEqual(
            source_scorecard.get("by_review_state"),
            source_action_summary.get("by_review_state"),
        )
        self.assertEqual(
            source_scorecard.get("by_source_store"),
            source_action_summary.get("by_source_store"),
        )
        self.assertEqual(
            source_next_action.get("unqueued_actionable_source_rows"),
            source_action_summary.get("unqueued_actionable_source_rows"),
        )
        self.assertEqual(
            source_next_action.get("excluded_review_state_rows"),
            source_action_summary.get("excluded_review_state_rows"),
        )
        self.assertEqual(
            open_queues.get("metadata_action_missing_cells"),
            metadata_action_summary.get("queued_missing_cells"),
        )
        self.assertEqual(
            open_queues.get("metadata_actionable_groups"),
            metadata_action_summary.get("actionable_group_count"),
        )
        self.assertEqual(
            open_queues.get("metadata_unqueued_actionable_groups"),
            metadata_action_summary.get("unqueued_actionable_group_count"),
        )
        self.assertEqual(
            open_queues.get("metadata_actionable_missing_cells"),
            metadata_action_summary.get("actionable_missing_cells"),
        )
        self.assertEqual(
            open_queues.get("metadata_unqueued_actionable_missing_cells"),
            metadata_action_summary.get("unqueued_actionable_missing_cells"),
        )
        self.assertEqual(
            metadata_scorecard.get("missing_cell_queue_coverage"),
            metadata_action_summary.get("missing_cell_queue_coverage"),
        )
        self.assertEqual(
            metadata_scorecard.get("missing_cells_by_field"),
            metadata_action_summary.get("missing_cells_by_field"),
        )
        self.assertEqual(
            metadata_scorecard.get("top_action_groups"),
            metadata_action_summary.get("top_action_groups"),
        )
        catalog_items = reports.load_json(reports.PUBLIC_CATALOG).get("items", [])
        metadata_review = reports.build_metadata_review_batches_public(catalog_items, "2026-01-01T00:00:00Z")
        rebuilt_metadata_action = build_metadata_action_queue_report(metadata_review)
        rebuilt_field_cells = [
            list(row) for row in rebuilt_metadata_action.get("summary", {}).get("missing_cells_by_field", [])
        ]
        self.assertEqual(
            rebuilt_field_cells,
            metadata_action_summary.get("missing_cells_by_field"),
        )
        self.assertEqual(
            metadata_next_action.get("unqueued_actionable_missing_cells"),
            metadata_action_summary.get("unqueued_actionable_missing_cells"),
        )
        self.assertEqual(
            metadata_next_action.get("missing_cells_by_source_store"),
            metadata_action_summary.get("missing_cells_by_source_store"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_actionable_rows"),
            image_action_summary.get("actionable_image_rows"),
        )
        self.assertEqual(
            open_queues.get("image_attachment_unqueued_actionable_rows"),
            image_action_summary.get("unqueued_actionable_image_rows"),
        )
        self.assertEqual(
            image_scorecard.get("unqueued_actionable_image_rows"),
            image_action_summary.get("unqueued_actionable_image_rows"),
        )
        self.assertEqual(
            image_scorecard.get("by_workflow"),
            image_action_summary.get("by_workflow"),
        )
        self.assertEqual(
            image_scorecard.get("excluded_workflow_rows"),
            image_action_summary.get("excluded_workflow_rows"),
        )
        self.assertEqual(
            image_next_action.get("sample_queue_coverage"),
            image_action_summary.get("sample_queue_coverage"),
        )
        self.assertEqual(
            image_next_action.get("by_source_store"),
            image_action_summary.get("by_source_store"),
        )
        self.assertEqual(
            open_queues.get("dedupe_action_groups"),
            dedupe_action_summary.get("queued_groups"),
        )
        self.assertEqual(
            open_queues.get("dedupe_actionable_groups"),
            dedupe_action_summary.get("actionable_groups"),
        )
        self.assertEqual(
            open_queues.get("dedupe_unqueued_actionable_groups"),
            dedupe_action_summary.get("unqueued_actionable_groups"),
        )
        self.assertEqual(
            dedupe_scorecard.get("queue_coverage"),
            dedupe_action_summary.get("queue_coverage"),
        )
        self.assertEqual(
            dedupe_next_action.get("unqueued_actionable_groups"),
            dedupe_action_summary.get("unqueued_actionable_groups"),
        )
        self.assertEqual(
            open_queues.get("ichiban_metadata_action_campaigns"),
            ichiban_action_summary.get("queued_action_campaigns"),
        )
        self.assertEqual(
            open_queues.get("ichiban_metadata_actionable_campaigns"),
            ichiban_action_summary.get("actionable_campaigns"),
        )
        self.assertEqual(
            open_queues.get("ichiban_metadata_unqueued_action_campaigns"),
            ichiban_action_summary.get("unqueued_action_campaigns"),
        )
        self.assertEqual(
            open_queues.get("ichiban_metadata_queued_catalog_item_rows"),
            ichiban_action_summary.get("queued_catalog_item_rows"),
        )
        self.assertEqual(
            ichiban_scorecard.get("campaign_queue_coverage"),
            ichiban_action_summary.get("campaign_queue_coverage"),
        )
        self.assertEqual(
            ichiban_next_action.get("field_patch_template_counts"),
            ichiban_action_summary.get("field_patch_template_counts"),
        )
        self.assertEqual(
            open_queues.get("animation_category_action_rows"),
            animation_action_summary.get("queued_catalog_rows"),
        )
        self.assertEqual(
            open_queues.get("animation_category_split_review_categories"),
            animation_action_summary.get("split_review_categories"),
        )
        self.assertEqual(
            open_queues.get("animation_category_direct_mapping_categories"),
            animation_action_summary.get("direct_mapping_categories"),
        )
        self.assertEqual(
            animation_scorecard.get("split_review_categories"),
            animation_action_summary.get("split_review_categories"),
        )
        self.assertEqual(
            animation_next_action.get("direct_mapping_categories"),
            animation_action_summary.get("direct_mapping_categories"),
        )
        self.assertEqual(animation_action_summary.get("app_folder_color_count"), 188)
        self.assertEqual(animation_action_summary.get("app_folder_icon_option_count"), 211)
        self.assertTrue(animation_action_summary.get("app_folder_palette_sorted_by_family"))
        self.assertEqual(
            animation_scorecard.get("app_folder_color_count"),
            animation_action_summary.get("app_folder_color_count"),
        )
        self.assertEqual(
            animation_next_action.get("app_folder_icon_option_count"),
            animation_action_summary.get("app_folder_icon_option_count"),
        )
        self.assertGreater(len(animation_agent_batches), 0)
        self.assertTrue(
            all(
                "split_review_categories" in batch.get("review_summary", {})
                for batch in animation_agent_batches
            )
        )


if __name__ == "__main__":
    unittest.main()
