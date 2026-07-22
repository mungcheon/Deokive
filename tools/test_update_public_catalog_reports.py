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
        self.assertIn("data/catalog_image_asset_audit_public.json", updated_files)
        self.assertIn("data/catalog_missing_image_priority_public.json", updated_files)
        self.assertIn("data/animate_missing_image_search_public.json", updated_files)
        self.assertIn("data/goodsmile_missing_image_search_public.json", updated_files)
        self.assertIn("data/kotobukiya_movic_missing_image_search_public.json", updated_files)
        self.assertIn("data/jump_furyu_taito_missing_image_search_public.json", updated_files)
        self.assertIn("data/secondary_official_missing_image_search_public.json", updated_files)
        self.assertIn("data/manual_missing_image_source_discovery_public.json", updated_files)
        self.assertIn("data/generic_storefront_missing_image_source_public.json", updated_files)
        self.assertIn("data/catalog_missing_image_report_coverage_public.json", updated_files)
        self.assertIn("data/ensky_missing_image_cache_coverage_public.json", updated_files)
        self.assertIn("data/ensky_cache_candidate_action_queue_public.json", updated_files)
        self.assertIn("data/ensky_search_page_probe_public.json", updated_files)
        self.assertIn("data/stellive_fanding_candidates_public.json", updated_files)
        self.assertIn("data/requested_focus_enrichment_public.json", updated_files)
        self.assertIn("data/requested_focus_review_batches_public.json", updated_files)
        self.assertIn("data/catalog_confirmed_import_readiness_public.json", updated_files)
        self.assertIn("data/catalog_execution_plan_public.json", updated_files)
        self.assertIn("data/source_discovery_store_bottlenecks_public.json", updated_files)
        self.assertIn("data/catalog_metadata_review_batches_public.json", updated_files)
        self.assertIn("data/catalog_metadata_action_queue_public.json", updated_files)
        self.assertIn("data/animation_category_action_queue_public.json", updated_files)
        self.assertIn("data/danganronpa_missing_media_public.json", updated_files)
        self.assertIn("data/gotouchi_representative_image_attachment_public.json", updated_files)
        self.assertIn("data/catalog_image_source_url_confirmed_template_public.json", updated_files)
        self.assertIn("data/source_discovery_next_focus_pack_public.json", updated_files)
        self.assertIn("data/source_discovery_next_focus_pack_import_dry_run_public.json", updated_files)
        self.assertIn("data/source_discovery_next_focus_pack_fetch_audit_public.json", updated_files)
        self.assertIn("data/catalog_missing_image_actionability_public.json", updated_files)
        self.assertIn("data/catalog_deduplication_fast_review_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_metadata_fast_review_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_prize_policy_audit_public.json", updated_files)
        self.assertIn("data/ichiban_kuji_prize_name_image_review_public.json", updated_files)
        self.assertIn("data/animation_category_split_review_public.json", updated_files)
        self.assertIn("data/animation_category_unmatched_keyword_review_public.json", updated_files)
        self.assertIn("data/source_detail_probe_public.json", updated_files)
        self.assertIn("data/source_detail_candidate_action_queue_public.json", updated_files)

        quality = reports.load_json(reports.QUALITY)
        self.assertEqual(quality["missing_image_priority"]["missing_image_rows"], result["missing"]["image_url"])
        if reports.ANIMATE_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["animate_missing_image_search"]["missing_animate_image_rows"], 148)
            self.assertIs(quality["animate_missing_image_search"]["auto_apply_enabled"], False)
        if reports.GOODSMILE_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["goodsmile_missing_image_search"]["missing_goodsmile_image_rows"], 57)
            self.assertIs(quality["goodsmile_missing_image_search"]["auto_apply_enabled"], False)
        if reports.KOTOBUKIYA_MOVIC_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["kotobukiya_movic_missing_image_search"]["missing_target_image_rows"], 80)
            self.assertIs(quality["kotobukiya_movic_missing_image_search"]["auto_apply_enabled"], False)
        if reports.JUMP_FURYU_TAITO_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["jump_furyu_taito_missing_image_search"]["missing_target_image_rows"], 59)
            self.assertIs(quality["jump_furyu_taito_missing_image_search"]["auto_apply_enabled"], False)
        if reports.SECONDARY_OFFICIAL_MISSING_IMAGE_SEARCH.exists():
            self.assertEqual(quality["secondary_official_missing_image_search"]["missing_target_image_rows"], 49)
            self.assertIs(quality["secondary_official_missing_image_search"]["auto_apply_enabled"], False)
        if reports.MANUAL_MISSING_IMAGE_SOURCE_DISCOVERY.exists():
            self.assertEqual(quality["manual_missing_image_source_discovery"]["manual_source_discovery_rows"], 112)
            self.assertIs(quality["manual_missing_image_source_discovery"]["auto_apply_enabled"], False)
        if reports.GENERIC_STOREFRONT_MISSING_IMAGE_SOURCE.exists():
            self.assertEqual(quality["generic_storefront_missing_image_source"]["generic_storefront_rows"], 5)
            self.assertIs(quality["generic_storefront_missing_image_source"]["auto_apply_enabled"], False)
        if reports.MISSING_IMAGE_REPORT_COVERAGE.exists():
            self.assertEqual(quality["missing_image_report_coverage"]["missing_image_rows"], result["missing"]["image_url"])
            self.assertEqual(quality["missing_image_report_coverage"]["unassigned_missing_image_rows"], 0)
            self.assertIs(quality["missing_image_report_coverage"]["auto_apply_enabled"], False)
        if reports.MISSING_IMAGE_ACTIONABILITY.exists():
            self.assertEqual(quality["missing_image_actionability"]["missing_image_rows"], result["missing"]["image_url"])
            self.assertEqual(quality["missing_image_actionability"]["unclassified_rows"], 0)
            self.assertIs(quality["missing_image_actionability"]["auto_apply_enabled"], False)
        self.assertEqual(
            quality["image_source_url_confirmed_template"]["template_items"],
            quality["image_attachment_action_queue"]["source_url_update_template_rows"],
        )
        self.assertIs(quality["image_source_url_confirmed_template"]["auto_apply_enabled"], False)
        self.assertEqual(quality["source_discovery_next_focus_pack"]["pack_items"], 20)
        self.assertEqual(quality["source_discovery_next_focus_pack"]["focus_pack_id"], "source-discovery-focus-001")
        self.assertIs(quality["source_discovery_next_focus_pack"]["auto_apply_enabled"], False)
        self.assertEqual(quality["source_discovery_next_focus_pack_import_dry_run"]["updated_rows"], 0)
        self.assertEqual(quality["source_discovery_next_focus_pack_import_dry_run"]["skipped_rows"], 20)
        self.assertIs(quality["source_discovery_next_focus_pack_import_dry_run"]["write"], False)
        if reports.SOURCE_DISCOVERY_NEXT_FOCUS_PACK_FETCH_AUDIT.exists():
            self.assertEqual(
                quality["source_discovery_next_focus_pack_fetch_audit"]["pack_items"],
                quality["source_discovery_next_focus_pack"]["pack_items"],
            )
            self.assertIs(
                quality["source_discovery_next_focus_pack_fetch_audit"]["auto_apply_enabled"],
                False,
            )
        self.assertEqual(quality["ensky_cache_coverage"]["missing_ensky_image_rows"], 142)
        self.assertIs(quality["ensky_cache_coverage"]["auto_apply_enabled"], False)
        if reports.ENSKY_SEARCH_PAGE_PROBE.exists():
            self.assertEqual(quality["ensky_search_page_probe"]["processed_rows"], 30)
            self.assertIs(quality["ensky_search_page_probe"]["auto_apply_enabled"], False)
        if reports.STELLIVE_FANDING_CANDIDATES.exists():
            self.assertGreater(quality["stellive_fanding_candidates"]["missing_image_candidate_rows"], 0)
            self.assertIs(quality["stellive_fanding_candidates"]["auto_apply_enabled"], False)
        if reports.SOURCE_DISCOVERY_STORE_BOTTLENECKS.exists():
            self.assertEqual(
                quality["source_discovery_store_bottlenecks"]["queued_source_rows"],
                quality["source_discovery_action_queue"]["queued_source_rows"],
            )
            self.assertGreater(quality["source_discovery_store_bottlenecks"]["store_count"], 0)
            self.assertIs(quality["source_discovery_store_bottlenecks"]["auto_apply_enabled"], False)
        if reports.SOURCE_DETAIL.exists():
            self.assertEqual(
                quality["source_detail_candidate_probe"]["candidate_review_rows"],
                reports.load_json(reports.SOURCE_DETAIL)["summary"]["candidate_review_rows"],
            )
            self.assertIs(quality["source_detail_candidate_probe"]["auto_apply_enabled"], False)
        if reports.SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.exists():
            source_detail_action = reports.load_json(reports.SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE)
            self.assertEqual(
                quality["source_detail_candidate_action_queue"]["candidate_action_rows"],
                source_detail_action["summary"]["candidate_action_rows"],
            )
            self.assertEqual(
                quality["source_detail_candidate_action_queue"]["manual_confirmation_shortlist_rows"],
                source_detail_action["summary"]["manual_confirmation_shortlist_rows"],
            )
            self.assertEqual(quality["source_detail_candidate_action_queue"]["manual_confirmed_true"], 0)
            self.assertIs(quality["source_detail_candidate_action_queue"]["auto_apply_enabled"], False)
        if reports.GOTOUCHI_REPRESENTATIVE_IMAGE_ATTACHMENT.exists():
            gotouchi_attachment = reports.load_json(reports.GOTOUCHI_REPRESENTATIVE_IMAGE_ATTACHMENT)
            self.assertEqual(
                quality["gotouchi_representative_image_attachment"]["representative_attachment_rows"],
                gotouchi_attachment["summary"]["representative_attachment_rows"],
            )
            self.assertEqual(quality["gotouchi_representative_image_attachment"]["manual_confirmed_true"], 0)
            self.assertIs(quality["gotouchi_representative_image_attachment"]["auto_apply_enabled"], False)
        if reports.DEDUPLICATION_FAST_REVIEW.exists():
            self.assertEqual(quality["deduplication_fast_review"]["fast_review_groups"], 42)
            self.assertEqual(quality["deduplication_fast_review"]["manual_confirmed_true"], 0)
            self.assertIs(quality["deduplication_fast_review"]["auto_delete_enabled"], False)
        if reports.DEDUPLICATION_CONFIRMED_TEMPLATE.exists():
            dedupe_template = reports.load_json(reports.DEDUPLICATION_CONFIRMED_TEMPLATE)
            self.assertEqual(
                quality["deduplication_confirmed_template"]["template_items"],
                dedupe_template["summary"]["template_items"],
            )
            self.assertEqual(quality["deduplication_confirmed_template"]["manual_confirmed_rows"], 0)
            self.assertIs(quality["deduplication_confirmed_template"]["auto_delete_enabled"], False)
        if reports.DEDUPLICATION_TEMPLATE_IMPORT_DRY_RUN.exists():
            self.assertEqual(quality["deduplication_template_import_dry_run"]["updated_rows"], 0)
            self.assertEqual(quality["deduplication_template_import_dry_run"]["skipped_rows"], 42)
            self.assertIs(quality["deduplication_template_import_dry_run"]["write"], False)
        if reports.ICHIIBAN_KUJI_METADATA_FAST_REVIEW.exists():
            self.assertEqual(quality["ichiban_kuji_metadata_fast_review"]["fast_review_campaigns"], 20)
            self.assertEqual(quality["ichiban_kuji_metadata_fast_review"]["manual_confirmed_true"], 0)
            self.assertIs(quality["ichiban_kuji_metadata_fast_review"]["auto_apply_enabled"], False)
        if reports.ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.exists():
            prize_audit = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT)
            self.assertEqual(
                quality["ichiban_kuji_prize_policy_audit"]["last_one_nonzero_price_rows"],
                prize_audit["summary"]["last_one_nonzero_price_rows"],
            )
            self.assertEqual(quality["ichiban_kuji_prize_policy_audit"]["double_chance_nonzero_price_rows"], 0)
            self.assertEqual(
                quality["ichiban_kuji_prize_policy_audit"]["incomplete_numbered_variant_prize_label_groups"],
                prize_audit["summary"]["incomplete_numbered_variant_prize_label_groups"],
            )
            self.assertIs(
                quality["ichiban_kuji_prize_policy_audit"]["numbered_variant_coverage_policy_pass"],
                prize_audit["summary"]["numbered_variant_coverage_policy_pass"],
            )
            self.assertEqual(
                quality["ichiban_kuji_prize_policy_audit"]["prize_policy_review_batch_count"],
                prize_audit["summary"]["prize_policy_review_batch_count"],
            )
            self.assertIs(quality["ichiban_kuji_prize_policy_audit"]["zero_price_exception_policy_pass"], True)
            self.assertIs(quality["ichiban_kuji_prize_policy_audit"]["auto_apply_enabled"], False)
        if reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.exists():
            prize_name_image = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW)
            prize_name_image_summary = prize_name_image.get("summary", {})
            self.assertEqual(
                quality["ichiban_kuji_prize_name_image_review"]["review_rows"],
                prize_name_image_summary.get("review_rows"),
            )
            self.assertEqual(
                quality["ichiban_kuji_prize_name_image_review"]["multi_item_prize_rank_groups"],
                prize_name_image_summary.get("multi_item_prize_rank_groups"),
            )
            self.assertIs(quality["ichiban_kuji_prize_name_image_review"]["auto_apply_enabled"], False)

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

    def test_execution_plan_open_queues_match_operations(self):
        operations = reports.load_json(reports.OPERATIONS_REPORT)
        execution_plan = reports.load_json(reports.EXECUTION_PLAN)

        self.assertEqual(
            execution_plan.get("summary", {}).get("open_review_queues"),
            operations.get("summary", {}).get("open_review_queues"),
        )

    def test_public_meta_counts_match_catalog(self):
        catalog = reports.load_json(reports.PUBLIC_CATALOG)
        public_meta = reports.load_json(reports.PUBLIC_META)
        rows = len(catalog.get("items", []))

        self.assertEqual(public_meta.get("row_count"), rows)
        self.assertEqual(public_meta.get("total_items"), rows)
        self.assertEqual(public_meta.get("generated_at"), catalog.get("meta", {}).get("generated_at"))

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
        quality = reports.load_json(reports.QUALITY)
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
        image_asset = reports.load_json(reports.IMAGE_ASSET_AUDIT)
        image_asset_summary = image_asset.get("summary", {})
        image_asset_gate = next(
            row
            for row in operations.get("quality_gates", [])
            if row.get("key") == "local_image_asset_coverage"
        )
        image_asset_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "local_image_asset_audit"
        )
        source_action = reports.load_json(reports.SOURCE_DISCOVERY_ACTION_QUEUE)
        source_action_summary = source_action.get("summary", {})
        source_focus_template = reports.load_json(reports.SOURCE_DISCOVERY_FOCUS_TEMPLATE)
        source_focus_template_summary = source_focus_template.get("summary", {})
        source_focus_template_import = reports.load_json(reports.SOURCE_DISCOVERY_FOCUS_TEMPLATE_IMPORT)
        ensky_cache_action = reports.load_json(reports.ENSKY_CACHE_CANDIDATE_ACTION_QUEUE)
        ensky_cache_action_summary = ensky_cache_action.get("summary", {})
        source_detail_action = reports.load_json(reports.SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE)
        source_detail_action_summary = source_detail_action.get("summary", {})
        source_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_discovery_action_queue"
        )
        source_focus_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_discovery_focus_template"
        )
        source_detail_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "source_detail_candidate_action_queue"
        )
        source_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_discovery_action_queue"
        )
        source_focus_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_discovery_focus_template"
        )
        ensky_cache_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ensky_cache_candidate_action_queue"
        )
        source_detail_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "source_detail_candidate_action_queue"
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
        ichiban_prize_audit = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT)
        ichiban_prize_audit_summary = ichiban_prize_audit.get("summary", {})
        ichiban_prize_name_image = reports.load_json(reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW)
        ichiban_prize_name_image_summary = ichiban_prize_name_image.get("summary", {})
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
        ichiban_prize_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ichiban_kuji_prize_policy_audit"
        )
        ichiban_prize_name_image_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "ichiban_kuji_prize_name_image_review"
        )
        ichiban_prize_name_image_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "ichiban_kuji_prize_name_image_review"
        )
        animation_action = reports.load_json(reports.ANIMATION_CATEGORY_ACTION_QUEUE)
        animation_action_summary = animation_action.get("summary", {})
        animation_split = reports.load_json(reports.ANIMATION_CATEGORY_SPLIT_REVIEW)
        animation_split_summary = animation_split.get("summary", {})
        animation_keyword = reports.load_json(reports.ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW)
        animation_keyword_summary = animation_keyword.get("summary", {})
        animation_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "animation_category_action_queue"
        )
        animation_split_scorecard = next(
            row
            for row in operations.get("workstream_scorecard", [])
            if row.get("workstream") == "animation_category_split_review"
        )
        animation_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "animation_category_action_queue"
        )
        animation_split_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "animation_category_split_review"
        )
        animation_keyword_next_action = next(
            row
            for row in operations.get("next_actions", [])
            if row.get("workstream") == "animation_category_unmatched_keyword_review"
        )
        animation_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "animation_category_action_queue"
        ]
        animation_split_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "animation_category_split_review"
        ]
        animation_keyword_agent_batches = [
            batch
            for batch in agent_queue.get("batches", [])
            if batch.get("workstream") == "animation_category_unmatched_keyword_review"
        ]
        self.assertIn(f"data/{reports.IMAGE_ENRICHMENT_BATCHES.name}", scorecard_reports)
        self.assertIn(f"data/{reports.REQUESTED_FOCUS.name}", scorecard_reports)
        self.assertIn(f"data/{reports.DANGANRONPA_MISSING_MEDIA.name}", scorecard_reports)
        self.assertIn(f"data/{reports.AGENT_WORK_QUEUE.name}", next_action_reports)
        self.assertIn(f"data/{reports.EXECUTION_PLAN.name}", next_action_reports)
        self.assertIn(f"data/{reports.CONFIRMED_IMPORT_READINESS.name}", report_links)
        self.assertIn(f"data/{reports.IMAGE_ASSET_AUDIT.name}", report_links)
        self.assertIn(f"data/{reports.SOURCE_DETAIL_CANDIDATE_ACTION_QUEUE.name}", report_links)
        self.assertIn(f"data/{reports.SOURCE_DISCOVERY_FOCUS_TEMPLATE.name}", report_links)
        self.assertIn(f"data/{reports.ANIMATION_CATEGORY_ACTION_QUEUE.name}", report_links)
        self.assertIn(f"data/{reports.ANIMATION_CATEGORY_SPLIT_REVIEW.name}", report_links)
        self.assertIn(f"data/{reports.ANIMATION_CATEGORY_UNMATCHED_KEYWORD_REVIEW.name}", report_links)
        self.assertIn(f"data/{reports.ICHIIBAN_KUJI_PRIZE_POLICY_AUDIT.name}", report_links)
        self.assertIn(f"data/{reports.ICHIIBAN_KUJI_PRIZE_NAME_IMAGE_REVIEW.name}", report_links)
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
        self.assertEqual(image_asset_gate.get("status"), "pass")
        self.assertEqual(image_asset_gate.get("image_url_without_local_path_rows"), 0)
        self.assertEqual(image_asset_gate.get("missing_local_image_files"), 0)
        self.assertEqual(image_asset_gate.get("image_url_rows"), image_asset_summary.get("image_url_rows"))
        self.assertEqual(
            image_asset_next_action.get("local_asset_coverage"),
            image_asset_summary.get("local_asset_coverage"),
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
        expected_source_workstreams = [
            {
                "source_store": row.get("source_store"),
                "priority": row.get("priority"),
                "queued_source_rows": row.get("queued_source_rows"),
                "batch_count": row.get("batch_count", 0),
                "next_batch_id": row.get("next_batch_id"),
                "batch_ids": row.get("batch_ids", []),
                "allowed_source_domains": row.get("allowed_source_domains", []),
                "official_search_url_count": row.get("official_search_url_count", 0),
                "workflow_rows": row.get("workflow_rows", []),
                "review_state_rows": row.get("review_state_rows", []),
                "category_rows": row.get("category_rows", []),
                "recommended_next_step": row.get("recommended_next_step"),
                "auto_apply_enabled": row.get("auto_apply_enabled", False),
            }
            for row in source_action.get("source_store_workstreams", [])[:8]
        ]
        self.assertEqual(
            source_scorecard.get("top_source_store_workstreams"),
            expected_source_workstreams,
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
            source_next_action.get("top_source_store_workstreams"),
            expected_source_workstreams,
        )
        self.assertEqual(
            open_queues.get("source_discovery_focus_template_rows"),
            source_focus_template_summary.get("template_items"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_focus_template_work_order_packs"),
            source_focus_template_summary.get("work_order_pack_count"),
        )
        self.assertEqual(
            open_queues.get("source_discovery_focus_template_dry_run_skipped_rows"),
            source_focus_template_import.get("skipped_rows"),
        )
        for field in (
            "next_focus_pack_id",
            "next_source_store",
            "next_target_category",
            "next_focus_pack_rows",
            "next_official_search_url",
            "work_order_pack_count",
        ):
            self.assertEqual(source_focus_scorecard.get(field), source_focus_template_summary.get(field))
            self.assertEqual(source_focus_next_action.get(field), source_focus_template_summary.get(field))
        self.assertEqual(
            source_focus_scorecard.get("dry_run_skipped_rows"),
            source_focus_template_import.get("skipped_rows"),
        )
        self.assertFalse(source_focus_scorecard.get("auto_apply_enabled"))
        self.assertEqual(
            quality["source_discovery_action_queue"].get("top_source_store_workstreams"),
            expected_source_workstreams,
        )
        self.assertEqual(
            open_queues.get("ensky_cache_candidate_action_rows"),
            ensky_cache_action_summary.get("candidate_action_rows"),
        )
        self.assertEqual(
            open_queues.get("ensky_cache_candidate_manual_confirmed_rows"),
            ensky_cache_action_summary.get("manual_confirmed_true"),
        )
        self.assertEqual(
            ensky_cache_next_action.get("candidate_action_rows"),
            ensky_cache_action_summary.get("candidate_action_rows"),
        )
        self.assertEqual(
            quality["ensky_cache_candidate_action_queue"].get("candidate_action_rows"),
            ensky_cache_action_summary.get("candidate_action_rows"),
        )
        self.assertFalse(quality["ensky_cache_candidate_action_queue"].get("auto_apply_enabled"))
        self.assertEqual(
            open_queues.get("source_detail_candidate_action_rows"),
            source_detail_action_summary.get("candidate_action_rows"),
        )
        self.assertEqual(
            open_queues.get("source_detail_candidate_manual_confirmed_rows"),
            source_detail_action_summary.get("manual_confirmed_true"),
        )
        self.assertEqual(
            source_detail_scorecard.get("open_rows"),
            source_detail_action_summary.get("candidate_action_rows"),
        )
        self.assertEqual(
            source_detail_scorecard.get("by_review_risk"),
            source_detail_action_summary.get("by_review_risk"),
        )
        self.assertEqual(
            source_detail_next_action.get("candidate_action_rows"),
            source_detail_action_summary.get("candidate_action_rows"),
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
            image_next_action.get("source_url_update_template_rows"),
            image_action_summary.get("source_url_update_template_rows"),
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
            ichiban_prize_next_action.get("last_one_nonzero_price_rows"),
            ichiban_prize_audit_summary.get("last_one_nonzero_price_rows"),
        )
        self.assertEqual(
            ichiban_prize_next_action.get("double_chance_nonzero_price_rows"),
            ichiban_prize_audit_summary.get("double_chance_nonzero_price_rows"),
        )
        self.assertEqual(
            ichiban_prize_next_action.get("multi_item_prize_label_review_batch_count"),
            ichiban_prize_audit_summary.get("multi_item_prize_label_review_batch_count"),
        )
        self.assertEqual(
            ichiban_prize_next_action.get("repeated_name_different_source_review_batch_count"),
            ichiban_prize_audit_summary.get("repeated_name_different_source_review_batch_count"),
        )
        self.assertEqual(
            ichiban_prize_next_action.get("prize_policy_review_batch_count"),
            ichiban_prize_audit_summary.get("prize_policy_review_batch_count"),
        )
        self.assertIs(ichiban_prize_next_action.get("zero_price_exception_policy_pass"), True)
        self.assertEqual(
            open_queues.get("ichiban_prize_name_image_review_rows"),
            ichiban_prize_name_image_summary.get("review_rows"),
        )
        self.assertEqual(
            open_queues.get("ichiban_prize_multi_item_rank_groups"),
            ichiban_prize_name_image_summary.get("multi_item_prize_rank_groups"),
        )
        self.assertEqual(
            ichiban_prize_name_image_scorecard.get("open_rows"),
            ichiban_prize_name_image_summary.get("review_rows"),
        )
        self.assertEqual(
            ichiban_prize_name_image_scorecard.get("multi_item_prize_rank_groups"),
            ichiban_prize_name_image_summary.get("multi_item_prize_rank_groups"),
        )
        self.assertEqual(
            ichiban_prize_name_image_next_action.get("name_structure_review_rows"),
            ichiban_prize_name_image_summary.get("name_structure_review_rows"),
        )
        self.assertEqual(
            ichiban_prize_name_image_next_action.get("image_identity_review_rows"),
            ichiban_prize_name_image_summary.get("image_identity_review_rows"),
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
            open_queues.get("animation_category_name_split_rows"),
            animation_split_summary.get("affected_catalog_rows"),
        )
        self.assertEqual(
            open_queues.get("animation_category_name_split_candidates"),
            animation_split_summary.get("candidate_split_rules"),
        )
        self.assertEqual(
            open_queues.get("animation_category_name_split_unmatched_catalog_rows"),
            animation_split_summary.get("unmatched_catalog_rows"),
        )
        self.assertEqual(
            open_queues.get("animation_category_unmatched_keyword_rows"),
            animation_keyword_summary.get("unmatched_rows"),
        )
        self.assertEqual(
            open_queues.get("animation_category_unmatched_keyword_candidates"),
            animation_keyword_summary.get("token_candidate_count"),
        )
        self.assertEqual(
            open_queues.get("animation_category_unmatched_keyword_product_type_candidates"),
            animation_keyword_summary.get("product_type_candidate_count"),
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
        animation_visual_catalog = animation_action.get("app_folder_visual_catalog") or {}
        self.assertEqual(len(animation_visual_catalog.get("palette_color_families") or []), 8)
        self.assertEqual(len(animation_visual_catalog.get("palette_picker_order") or []), 188)
        self.assertEqual(
            animation_scorecard.get("app_folder_color_count"),
            animation_action_summary.get("app_folder_color_count"),
        )
        self.assertEqual(
            animation_next_action.get("app_folder_icon_option_count"),
            animation_action_summary.get("app_folder_icon_option_count"),
        )
        self.assertEqual(
            animation_split_scorecard.get("candidate_split_rules"),
            animation_split_summary.get("candidate_split_rules"),
        )
        self.assertEqual(
            animation_split_next_action.get("matched_sample_names"),
            animation_split_summary.get("matched_sample_names"),
        )
        self.assertEqual(
            animation_split_scorecard.get("matched_catalog_rows"),
            animation_split_summary.get("matched_catalog_rows"),
        )
        self.assertEqual(
            animation_split_next_action.get("unmatched_catalog_rows"),
            animation_split_summary.get("unmatched_catalog_rows"),
        )
        self.assertFalse(animation_split_summary.get("auto_apply_enabled"))
        self.assertEqual(
            animation_keyword_next_action.get("token_candidate_count"),
            animation_keyword_summary.get("token_candidate_count"),
        )
        self.assertEqual(
            animation_keyword_next_action.get("product_type_candidate_count"),
            animation_keyword_summary.get("product_type_candidate_count"),
        )
        self.assertFalse(animation_keyword_summary.get("auto_apply_enabled"))
        self.assertGreater(len(animation_agent_batches), 0)
        self.assertGreater(len(animation_split_agent_batches), 0)
        self.assertGreater(len(animation_keyword_agent_batches), 0)
        self.assertTrue(
            all(
                "split_review_categories" in batch.get("review_summary", {})
                for batch in animation_agent_batches
            )
        )
        self.assertTrue(
            all(
                "split_candidate_count" in batch.get("review_summary", {})
                for batch in animation_split_agent_batches
            )
        )
        self.assertTrue(
            all(
                "token_candidate_count" in batch.get("review_summary", {})
                for batch in animation_keyword_agent_batches
            )
        )


if __name__ == "__main__":
    unittest.main()
