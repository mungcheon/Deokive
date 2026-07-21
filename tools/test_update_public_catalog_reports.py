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
        self.assertIn("data/danganronpa_missing_media_public.json", updated_files)

    def test_published_reports_keep_manual_review_guards(self):
        operations = reports.load_json(reports.OPERATIONS_REPORT)
        source_discovery = reports.load_json(reports.SOURCE_DISCOVERY)
        generic_candidates = reports.load_json(reports.GENERIC_SOURCE_PATCH_CANDIDATES)

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
        self.assertIs(danganronpa_summary.get("auto_apply_enabled"), False)
        self.assertEqual(danganronpa_summary.get("missing_media_rows"), len(danganronpa_items))
        self.assertTrue(all(item.get("auto_apply_enabled") is False for item in danganronpa_items))

    def test_published_reports_expose_home_catalog_work_blocks(self):
        operations = reports.load_json(reports.OPERATIONS_REPORT)
        image_batches = reports.load_json(reports.IMAGE_ENRICHMENT_BATCHES)
        agent_queue = reports.load_json(reports.AGENT_WORK_QUEUE)

        blocker_rows = sum(int(row.get("rows") or 0) for row in image_batches.get("blocker_summary", []))
        self.assertEqual(blocker_rows, image_batches["summary"]["missing_image_rows"])

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
        self.assertIn(f"data/{reports.IMAGE_ENRICHMENT_BATCHES.name}", scorecard_reports)
        self.assertIn(f"data/{reports.REQUESTED_FOCUS.name}", scorecard_reports)
        self.assertIn(f"data/{reports.DANGANRONPA_MISSING_MEDIA.name}", scorecard_reports)
        self.assertIn(f"data/{reports.AGENT_WORK_QUEUE.name}", next_action_reports)


if __name__ == "__main__":
    unittest.main()
