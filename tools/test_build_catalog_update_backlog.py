import unittest

from tools import build_catalog_update_backlog as backlog


class BuildCatalogUpdateBacklogTest(unittest.TestCase):
    def test_default_queues_use_current_generated_reports(self):
        self.assertEqual(backlog.DEFAULT_QUEUE.name, "catalog_image_enrichment_queue_current.json")
        self.assertEqual(backlog.DEFAULT_FIELD_QUEUE.name, "catalog_field_enrichment_queue_current.json")
        self.assertEqual(backlog.DEFAULT_ICHIBAN_QUALITY_QUEUE.name, "ichiban_public_quality_queue.json")

    def test_build_backlog_summarizes_image_and_field_work(self):
        image_queue = {
            "missing_images": 3,
            "queue": [
                {
                    "source_store": "애니메이트",
                    "strategy": "official_search",
                    "provider_status": "search_only",
                    "automation_safety": "candidate_provider_script_required",
                    "category": "아크릴 스탠드",
                    "name_ko": "샘플 A",
                    "query": "sample a",
                    "search_url": "https://example.test/search/a",
                },
                {
                    "source_store": "애니메이트",
                    "strategy": "official_search",
                    "provider_status": "search_only",
                    "automation_safety": "candidate_provider_script_required",
                    "category": "아크릴 스탠드",
                    "name_ko": "샘플 B",
                    "query": "sample b",
                    "search_url": "https://example.test/search/b",
                },
                {
                    "source_store": "굿스마일컴퍼니",
                    "strategy": "manual_review",
                    "provider_status": "manual_only",
                    "automation_safety": "manual_research_required",
                    "category": "피규어",
                    "name_ko": "샘플 C",
                },
            ],
            "by_category": [["아크릴 스탠드", 2], ["피규어", 1]],
            "top_strategy_stores": [
                {"strategy": "official_search", "source_store": "애니메이트", "missing_images": 2}
            ],
            "top_store_categories": [
                {"source_store": "애니메이트", "category": "아크릴 스탠드", "missing_images": 2}
            ],
        }
        field_queue = {
            "missing_total": 2,
            "by_field": [["source_url", 1], ["release_date", 1]],
            "queue": [
                {
                    "batch_key": "animation|애니메이트|source_url",
                    "source_group": "animation_goods",
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "field": "source_url",
                    "strategy": "official_search",
                    "workstream": "source_discovery",
                    "field_action": "find_exact_source_url",
                    "risk": "medium",
                    "automation_candidate": True,
                    "name_ko": "샘플 A",
                    "acceptance_criteria": "exact product page",
                }
            ],
            "top_store_fields": [],
            "top_strategy_store_fields": [],
            "top_store_category_fields": [],
            "top_batch_keys": [],
            "animation_goods_category_fields": [],
            "animation_goods_store_category_fields": [],
        }
        quality = {
            "rows": 10,
            "missing_enrichment": {"image_url": 3, "source_url": 1},
        }
        source_discovery = {
            "summary": {
                "source_discovery_rows": 2,
                "top_store_categories": [
                    {"source_store": "Store A", "category": "Figure", "rows": 2}
                ],
            },
            "items": [
                {"workflow": "official_search_url_available", "source_store": "Store A"},
                {"workflow": "manual_official_research", "source_store": "Store B"},
            ],
        }
        priority_goods = {
            "summaries": {
                "danganronpa": {
                    "rows": 2,
                    "complete_rows": 1,
                    "incomplete_rows": 1,
                    "missing_fields": {"image_url": 1},
                }
            },
            "items": [
                {
                    "focus": "danganronpa",
                    "name_ko": "sample",
                    "missing_fields": ["image_url"],
                }
            ],
        }
        naming_queue = {
            "summary": {
                "known_alias_rows": 1,
                "ja_token_mismatch_rows": 0,
                "single_character_name_review_rows": 2,
                "ichiban_naming_convention_review_rows": 3,
                "queue_rows": 6,
            },
            "items": [
                {
                    "workflow": "character_alias_normalization",
                    "display_name": "sample alias",
                    "reason": "known_alias",
                },
                {
                    "workflow": "ichiban_display_name_convention",
                    "display_name": "sample ichiban",
                    "reason": "second_part_should_be_prize_rank",
                },
            ],
        }
        ichiban_quality = {
            "summary": {
                "queue_rows": 4,
                "campaign_gap_queue_rows": 1,
                "exact_display_duplicate_queue_rows": 1,
                "zero_price_policy_queue_rows": 0,
                "naming_convention_queue_rows": 2,
                "campaign_count": 10,
                "seeded_campaign_url_count": 9,
                "work_pack_rows": 1,
            },
            "items": [
                {
                    "workflow": "campaign_gap_research",
                    "display_name": "Ichiban sample A",
                    "source_url": "https://example.test/a",
                    "reason": "missing_seed_url",
                },
                {
                    "workflow": "non_prize_related_item_classification",
                    "display_name": "Ichiban sample B",
                    "source_url": "https://example.test/b",
                    "reason": "non_prize_or_related_item_needs_classification",
                },
            ],
            "work_packs": [
                {
                    "workflow": "campaign_gap_research",
                    "group_key": "sample",
                    "rows": 1,
                    "next_action": "Find evidence.",
                }
            ],
        }

        result = backlog.build_backlog(
            image_queue,
            quality,
            field_queue,
            {},
            source_discovery,
            {},
            priority_goods,
            naming_queue,
            ichiban_quality,
        )

        self.assertEqual(result["rows"], 10)
        self.assertEqual(result["missing_images"], 3)
        self.assertEqual(result["source_discovery_rows"], 2)
        self.assertEqual(
            result["source_discovery_by_workflow"],
            [("official_search_url_available", 1), ("manual_official_research", 1)],
        )
        self.assertEqual(result["source_discovery_top_stores"][0], {"source_store": "Store A", "rows": 1})
        self.assertEqual(
            result["source_discovery_top_store_categories"][0],
            {"source_store": "Store A", "category": "Figure", "rows": 2},
        )
        self.assertEqual(result["field_queue_missing_total"], 2)
        self.assertEqual(
            result["store_completion_focus"][0]["source_store"],
            field_queue["queue"][0]["source_store"],
        )
        self.assertEqual(result["store_completion_focus"][0]["source_url_missing"], 1)
        self.assertEqual(result["store_completion_focus"][0]["next_action"], "find_exact_source_urls_first")
        self.assertEqual(result["image_queue_by_strategy"], [("official_search", 2), ("manual_review", 1)])
        self.assertEqual(result["image_queue_by_provider_status"], [("search_only", 2), ("manual_only", 1)])
        self.assertEqual(
            result["image_queue_by_automation_safety"],
            [("candidate_provider_script_required", 2), ("manual_research_required", 1)],
        )
        self.assertEqual(
            result["top_image_safety_store_backlog"][0],
            {
                "automation_safety": "candidate_provider_script_required",
                "source_store": "애니메이트",
                "missing_images": 2,
            },
        )
        self.assertEqual(result["image_work_packs"][0]["source_store"], "애니메이트")
        self.assertEqual(result["image_work_packs"][0]["missing_images"], 2)
        self.assertEqual(
            result["image_work_packs"][0]["next_action"],
            "run_verified_provider_search_then_confirm_exact_detail_matches",
        )
        self.assertEqual(result["image_work_packs"][0]["samples"][0]["query"], "sample a")
        self.assertEqual(result["top_image_backlog"][0]["source_store"], "애니메이트")
        self.assertEqual(result["top_image_backlog"][0]["next_action"], "official_search_provider_or_manual_review")
        self.assertEqual(result["field_focus_packs"][0]["batch_key"], "animation|애니메이트|source_url")
        self.assertTrue(result["field_focus_packs"][0]["automation_candidate"])
        self.assertEqual(1, len(result["field_focus_packs"]))
        self.assertEqual(1, sum(1 for item in result["field_focus_packs"] if item["automation_candidate"]))
        self.assertEqual(result["priority_goods_summary"]["danganronpa"]["incomplete_rows"], 1)
        self.assertEqual(result["priority_goods_incomplete_samples"][0]["focus"], "danganronpa")
        self.assertEqual(result["naming_quality"]["queue_rows"], 6)
        self.assertEqual(result["naming_quality"]["known_alias_rows"], 1)
        self.assertEqual(
            result["naming_quality"]["by_workflow"],
            [("character_alias_normalization", 1), ("ichiban_display_name_convention", 1)],
        )
        self.assertEqual(result["ichiban_quality"]["queue_rows"], 4)
        self.assertEqual(result["ichiban_quality"]["campaign_gap_queue_rows"], 1)
        self.assertEqual(
            result["ichiban_quality"]["by_workflow"],
            [("campaign_gap_research", 1), ("non_prize_related_item_classification", 1)],
        )
        self.assertEqual(result["ichiban_quality"]["work_packs"][0]["group_key"], "sample")
        self.assertEqual(result["ichiban_quality"]["work_pack_rows"], 1)

    def test_field_focus_packs_groups_missing_rows_by_batch_key(self):
        items = [
            {
                "batch_key": "store|category|source_url",
                "source_group": "animation_goods",
                "source_store": "스토어",
                "category": "피규어",
                "field": "source_url",
                "automation_candidate": True,
            },
            {
                "batch_key": "store|category|source_url",
                "source_group": "animation_goods",
                "source_store": "스토어",
                "category": "피규어",
                "field": "source_url",
                "automation_candidate": True,
            },
        ]

        packs = backlog._field_focus_packs(items)

        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0]["missing"], 2)
        self.assertEqual(packs[0]["batch_key"], "store|category|source_url")


if __name__ == "__main__":
    unittest.main()
