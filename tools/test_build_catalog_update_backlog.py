import unittest
import tempfile
from pathlib import Path

from tools import build_catalog_update_backlog as backlog


class BuildCatalogUpdateBacklogTest(unittest.TestCase):
    def test_default_queues_use_current_generated_reports(self):
        self.assertEqual(backlog.DEFAULT_QUEUE.name, "catalog_image_enrichment_queue_current.json")
        self.assertEqual(backlog.DEFAULT_FIELD_QUEUE.name, "catalog_field_enrichment_queue_current.json")
        self.assertEqual(backlog.DEFAULT_ICHIBAN_QUALITY_QUEUE.name, "ichiban_public_quality_queue.json")
        self.assertEqual(
            backlog.DEFAULT_ANIMATION_ENRICHMENT_PRIORITY_QUEUE.name,
            "animation_enrichment_priority_queue.json",
        )
        self.assertEqual(
            backlog.DEFAULT_ANIMATION_IMAGE_UPDATE_TEMPLATE.name,
            "animation_next_batch_image_update.template.json",
        )

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
                    "actionable_now": True,
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
                "ichiban_display_name_convention_review_rows": 1,
                "ichiban_non_prize_related_item_review_rows": 2,
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
                "display_name_convention_review_rows": 1,
                "non_prize_related_item_review_rows": 1,
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
        image_asset_audit = {
            "summary": {
                "missing_image_url_rows": 3,
                "missing_image_with_source_url_rows": 1,
                "missing_image_without_source_url_rows": 2,
                "rows_ready_for_source_page_image_review": 1,
                "rows_requiring_source_url_before_image_review": 2,
            },
            "missing_image_evidence_priority": {
                "with_source_url_rows": 1,
                "without_source_url_rows": 2,
                "with_source_url_by_source_store": [["Store A", 1]],
                "without_source_url_by_source_store": [["Store B", 2]],
                "source_url_ready_sample_rows": [
                    {
                        "catalog_index": 30,
                        "name_ko": "image ready",
                        "source_store": "Store A",
                        "source_url": "https://example.test/source",
                    }
                ],
                "source_discovery_required_sample_rows": [
                    {"catalog_index": 31, "name_ko": "source needed", "source_store": "Store B"}
                ],
            },
        }
        animation_enrichment_priority = {
            "animation_rows": 12,
            "queue_groups": 2,
            "queue_rows": 9,
            "missing_image_rows": 7,
            "missing_source_rows": 8,
            "by_workflow": [["find_exact_source_url", 5], ["attach_image_from_exact_source", 4]],
            "items": [
                {
                    "workflow": "find_exact_source_url",
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "rows": 5,
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
            image_asset_audit,
            animation_enrichment_priority,
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
        self.assertEqual(1, len(result["field_update_work_packs"]))
        self.assertEqual("data/intake/field_updates/incoming", result["field_update_work_packs"][0]["intake_dir"])
        self.assertEqual("tools/import_agent_catalog_field_updates.py", result["field_update_work_packs"][0]["import_tool"])
        self.assertEqual(result["priority_goods_summary"]["danganronpa"]["incomplete_rows"], 1)
        self.assertEqual(result["priority_goods_incomplete_samples"][0]["focus"], "danganronpa")
        self.assertEqual(result["naming_quality"]["queue_rows"], 6)
        self.assertEqual(result["naming_quality"]["known_alias_rows"], 1)
        self.assertEqual(result["naming_quality"]["ichiban_display_name_convention_review_rows"], 1)
        self.assertEqual(result["naming_quality"]["ichiban_non_prize_related_item_review_rows"], 2)
        self.assertEqual(
            result["naming_quality"]["by_workflow"],
            [("character_alias_normalization", 1), ("ichiban_display_name_convention", 1)],
        )
        self.assertEqual(result["ichiban_quality"]["queue_rows"], 4)
        self.assertEqual(result["ichiban_quality"]["artifact"], "server/ichiban_public_quality_queue.html")
        self.assertEqual(result["ichiban_quality"]["campaign_gap_queue_rows"], 1)
        self.assertEqual(result["ichiban_quality"]["display_name_convention_review_rows"], 1)
        self.assertEqual(result["ichiban_quality"]["non_prize_related_item_review_rows"], 1)
        self.assertEqual(
            result["ichiban_quality"]["by_workflow"],
            [("campaign_gap_research", 1), ("non_prize_related_item_classification", 1)],
        )
        self.assertEqual(result["ichiban_quality"]["work_packs"][0]["group_key"], "sample")
        self.assertEqual(result["ichiban_quality"]["work_pack_rows"], 1)
        self.assertEqual(result["animation_enrichment_priority"]["queue_rows"], 9)
        self.assertEqual(
            result["animation_enrichment_priority"]["image_update_template"],
            "server/animation_next_batch_image_update.template.json",
        )
        self.assertEqual(
            result["animation_enrichment_priority"]["by_workflow"],
            [["find_exact_source_url", 5], ["attach_image_from_exact_source", 4]],
        )
        self.assertEqual(result["image_evidence_split"]["missing_image_url_rows"], 3)
        self.assertEqual(result["image_evidence_split"]["with_source_url_rows"], 1)
        self.assertEqual(result["image_evidence_split"]["without_source_url_rows"], 2)
        self.assertEqual(
            result["image_evidence_split"]["source_url_ready_sample_rows"][0]["catalog_index"],
            30,
        )
        self.assertEqual(result["operator_next_actions"][0]["lane"], "image_from_known_source")
        self.assertEqual(result["operator_next_actions"][0]["rows"], 1)
        self.assertEqual(result["operator_next_actions"][1]["lane"], "source_before_image")
        self.assertIn(
            "animation_enrichment",
            {item["lane"] for item in result["operator_next_actions"]},
        )

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

    def test_field_update_work_packs_balances_fields_when_limited(self):
        items = [
            {
                "workstream": "metadata",
                "source_store": "스토어",
                "category": f"소스 {index}",
                "field": "source_url",
                "actionable_now": True,
            }
            for index in range(6)
        ]
        items.extend(
            [
                {
                    "workstream": "metadata",
                    "source_store": "스토어",
                    "category": "발매일",
                    "field": "release_date",
                    "actionable_now": True,
                },
                {
                    "workstream": "metadata",
                    "source_store": "스토어",
                    "category": "가격",
                    "field": "official_price_jpy",
                    "actionable_now": True,
                },
                {
                    "workstream": "metadata",
                    "source_store": "스토어",
                    "category": "바코드",
                    "field": "barcode",
                    "actionable_now": True,
                },
            ]
        )

        packs = backlog._field_update_work_packs(items, limit=4)

        self.assertEqual(4, len(packs))
        self.assertEqual(
            {"source_url", "release_date", "official_price_jpy", "barcode"},
            {pack["field"] for pack in packs},
        )

    def test_markdown_includes_image_evidence_split(self):
        payload = {
            "rows": 10,
            "missing_images": 3,
            "source_discovery_rows": 2,
            "field_queue_missing_total": 5,
            "missing_enrichment": {"image_url": 3},
            "image_evidence_split": {
                "missing_image_url_rows": 3,
                "with_source_url_rows": 1,
                "without_source_url_rows": 2,
                "rows_ready_for_source_page_image_review": 1,
                "rows_requiring_source_url_before_image_review": 2,
                "with_source_url_by_source_store": [["Store A", 1]],
                "without_source_url_by_source_store": [["Store B", 2]],
                "source_url_ready_sample_rows": [
                    {
                        "catalog_index": 30,
                        "source_store": "Store A",
                        "name_ko": "image ready",
                        "source_url": "https://example.test/source",
                    }
                ],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "backlog.md"
            backlog.write_markdown(payload, path)

            text = path.read_text(encoding="utf-8-sig")

        self.assertIn("## Operator Next Actions", text)
        self.assertIn("No immediate operator action queue is loaded.", text)
        self.assertIn("## Image Evidence Split", text)
        self.assertIn("With source_url: `1`", text)
        self.assertIn("Store A", text)

    def test_markdown_includes_operator_next_actions(self):
        payload = {
            "rows": 10,
            "missing_images": 3,
            "source_discovery_rows": 2,
            "field_queue_missing_total": 5,
            "missing_enrichment": {"image_url": 3},
            "operator_next_actions": [
                {
                    "lane": "image_from_known_source",
                    "label": "출처가 있는 사진부터 검수",
                    "rows": 2,
                    "source_store": "Store A",
                    "category": "Figure",
                    "next_action": "confirm exact image",
                    "artifact": "server/example.json",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "backlog.md"
            backlog.write_markdown(payload, path)

            text = path.read_text(encoding="utf-8-sig")

        self.assertIn("## Operator Next Actions", text)
        self.assertIn("출처가 있는 사진부터 검수", text)
        self.assertIn("server/example.json", text)


if __name__ == "__main__":
    unittest.main()
