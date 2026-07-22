from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import update_public_catalog_reports as reports


class PublicCatalogReportTests(unittest.TestCase):
    def test_public_report_generation_keeps_site_data_safe_and_consistent(self):
        result = reports.update_reports(write=False)

        self.assertFalse(result["write"])
        self.assertGreater(result["rows"], 0)
        self.assertIn("source_url", result["missing"])
        self.assertIn("image_url", result["missing"])
        updated_files = {Path(path).as_posix() for path in result["updated_files"]}
        self.assertIn("data/catalog_operations_public.json", updated_files)
        self.assertIn("data/catalog_agent_work_queue_public.json", updated_files)
        self.assertIn("data/requested_focus_enrichment_public.json", updated_files)
        self.assertIn("data/requested_focus_review_batches_public.json", updated_files)
        self.assertIn("data/catalog_confirmed_import_readiness_public.json", updated_files)
        self.assertIn("data/catalog_execution_plan_public.json", updated_files)
        self.assertIn("data/animation_category_action_queue_public.json", updated_files)
        self.assertIn("data/danganronpa_missing_media_public.json", updated_files)

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
        self.assertGreater(len(animation_agent_batches), 0)
        self.assertTrue(
            all(
                "split_review_categories" in batch.get("review_summary", {})
                for batch in animation_agent_batches
            )
        )


if __name__ == "__main__":
    unittest.main()
