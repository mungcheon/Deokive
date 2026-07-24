from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_detail_candidates_public as builder
from enrich_catalog_images import ProductImage


class BuildSourceDiscoveryNextFocusDetailCandidatesPublicTest(unittest.TestCase):
    def test_build_report_publishes_review_only_detail_candidates(self) -> None:
        source = {
            "summary": {
                "focus_pack_id": "source-discovery-focus-001",
                "source_store": "애니메이트",
                "target_category": "아크릴 스탠드",
            },
            "items": [
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "catalog_index": 1,
                    "source_store": "애니메이트",
                    "affiliation": "Series A",
                    "category": "아크릴 스탠드",
                    "name_ko": "최애의 아이 아크릴 스탠드 (호시노 아이)",
                    "name_ja": "推しの子 アクリルスタンド (星野アイ)",
                    "search_query": "推しの子 アクリルスタンド (星野アイ)",
                    "official_search_url": "https://animate.example/search",
                    "source_patch_template": {"catalog_index": 1},
                },
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "catalog_index": 2,
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "name_ko": "후보 없음",
                    "search_query": "후보 없음",
                },
            ],
        }

        def search(item):
            if item["catalog_index"] == 1:
                return [
                    ProductImage(
                        title="【グッズ-スタンドポップ】【推しの子】 アクリルスタンド 星野アイ",
                        image_url="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550000000000_1.jpg&width=400&height=400&square=1",
                        source_url="https://www.animate-onlineshop.jp/pn/test/pd/1234567/",
                    )
                ]
            return []

        report = builder.build_report(
            source,
            search_fn=search,
            fetch_audit={
                "items": [
                    {
                        "catalog_index": 1,
                        "no_results_page": True,
                        "needs_fallback_web_search": True,
                        "product_detail_link_count": 0,
                        "fetch_block_reason": "official_search_returned_no_results",
                    },
                    {
                        "catalog_index": 2,
                        "no_results_page": False,
                        "needs_fallback_web_search": False,
                        "product_detail_link_count": 1,
                    },
                ]
            },
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-23T00:00:00Z")
        self.assertEqual(report["summary"]["focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(report["summary"]["pack_items"], 2)
        self.assertEqual(report["summary"]["items_with_candidates"], 1)
        self.assertEqual(report["summary"]["items_with_candidates_from_official_no_results"], 1)
        self.assertEqual(report["summary"]["candidate_rows_from_fallback_search"], 1)
        self.assertEqual(report["summary"]["candidate_rows"], 1)
        self.assertEqual(report["summary"]["exact_candidate_review_rows"], 1)
        self.assertEqual(report["summary"]["no_candidate_items"], 1)
        self.assertEqual(report["summary"]["candidate_confirmation_template_rows"], 1)
        self.assertEqual(report["summary"]["exact_candidate_confirmation_shortlist_rows"], 1)
        self.assertEqual(report["summary"]["candidate_confirmation_exact_review_rows"], 1)
        self.assertEqual(report["summary"]["candidate_confirmation_manual_confirmed_rows"], 0)
        self.assertEqual(report["summary"]["completion_readiness_status"], "exact_candidate_confirmation_ready")
        self.assertEqual(report["summary"]["auto_apply_ready_rows"], 0)
        self.assertEqual(report["summary"]["fallback_bridge_rows"], 0)
        self.assertEqual(
            report["summary"]["review_bucket_counts"],
            [["exact_candidate_shortlist_review", 1], ["no_candidate_manual_source_research", 1]],
        )
        self.assertEqual(
            report["summary"]["review_decision_counts"],
            [["exact_candidate_confirmation_ready", 1], ["manual_source_research_required", 1]],
        )
        self.assertEqual(report["summary"]["next_action_lane_count"], 2)
        self.assertEqual(
            report["summary"]["next_action_lanes"],
            [["confirm_exact_candidate_identity", 1], ["manual_source_research", 1]],
        )
        self.assertEqual(report["summary"]["variant_detail_required_rows"], 0)
        self.assertEqual(report["summary"]["exact_candidate_confirmation_ready_items"], 1)
        self.assertEqual(report["completion_readiness"]["status"], "exact_candidate_confirmation_ready")
        self.assertEqual(report["completion_readiness"]["next_safe_phase"], "confirm_exact_candidate_identity")
        self.assertEqual(report["completion_readiness"]["auto_apply_ready_rows"], 0)
        self.assertIn("review-only", report["completion_readiness"]["safety_note"])
        first = report["items"][0]
        self.assertEqual(first["manual_review_status"], "not_started")
        self.assertEqual(first["review_bucket"], "exact_candidate_shortlist_review")
        self.assertEqual(first["review_decision"]["decision"], "exact_candidate_confirmation_ready")
        self.assertEqual(first["manual_confirmed_source_url"], "")
        self.assertEqual(first["affiliation"], "Series A")
        self.assertEqual(first["official_search_audit_status"], "official_search_no_results")
        self.assertTrue(first["official_search_no_results"])
        self.assertTrue(first["needs_fallback_web_search"])
        self.assertEqual(first["official_search_fetch_block_reason"], "official_search_returned_no_results")
        self.assertEqual(first["candidates"][0]["review_status"], "exact_candidate_review")
        self.assertTrue(first["candidates"][0]["exact_candidate_gate_passed"])
        self.assertEqual(first["candidates"][0]["exact_candidate_blockers"], [])
        self.assertEqual(first["source_patch_template"]["catalog_index"], 1)
        template_row = report["candidate_confirmation_template"][0]
        self.assertFalse(template_row["manual_confirmed"])
        self.assertEqual(template_row["catalog_index"], 1)
        self.assertEqual(template_row["affiliation"], "Series A")
        self.assertEqual(template_row["candidate_rank"], 1)
        self.assertEqual(template_row["candidate_review_status"], "exact_candidate_review")
        self.assertEqual(
            template_row["candidate_source_url"],
            "https://www.animate-onlineshop.jp/pn/test/pd/1234567/",
        )
        self.assertEqual(template_row["manual_confirmed_source_url"], "")
        shortlist_row = report["exact_candidate_confirmation_shortlist"][0]
        self.assertEqual(shortlist_row["catalog_index"], 1)
        self.assertEqual(shortlist_row["candidate_review_status"], "exact_candidate_review")
        self.assertEqual(shortlist_row["shortlist_reason"], "exact_candidate_gate_passed")
        self.assertIn("recommended_next_step", shortlist_row)
        self.assertEqual(report["candidate_review_work_order"][0]["catalog_index"], 1)
        self.assertEqual(
            report["candidate_review_work_order"][0]["recommended_next_step"],
            "confirm_exact_candidate_identity",
        )
        self.assertEqual(
            report["candidate_review_work_order"][0]["review_decision"]["decision"],
            "exact_candidate_confirmation_ready",
        )
        self.assertEqual(report["next_action_lanes"][0]["lane"], "confirm_exact_candidate_identity")
        self.assertEqual(report["next_action_lanes"][0]["row_count"], 1)
        self.assertEqual(report["next_action_lanes"][0]["candidate_rows"], 1)
        self.assertEqual(report["next_action_lanes"][0]["next_catalog_index"], 1)
        self.assertEqual(
            report["next_action_lanes"][0]["sample_items"][0]["decision"],
            "exact_candidate_confirmation_ready",
        )
        self.assertEqual(report["next_action_lanes"][1]["lane"], "manual_source_research")
        self.assertFalse(report["automation_policy"]["auto_apply_source_url"])

    def test_build_report_bridges_no_candidate_fallback_rows(self) -> None:
        source = {
            "summary": {
                "focus_pack_id": "source-discovery-focus-001",
                "source_store": "애니메이트",
                "target_category": "아크릴 스탠드",
            },
            "items": [
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "catalog_index": 9,
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "name_ko": "후보 없음",
                    "name_ja": "候補なし アクリルスタンド",
                    "search_query": "候補なし アクリルスタンド",
                }
            ],
        }

        report = builder.build_report(
            source,
            search_fn=lambda _item: [],
            fetch_audit={
                "items": [
                    {
                        "catalog_index": 9,
                        "no_results_page": True,
                        "needs_fallback_web_search": True,
                    }
                ]
            },
            fallback_queue={
                "items": [
                    {
                        "catalog_index": 9,
                        "domain_limited_web_search_urls": [
                            "https://google.example/search-exact",
                            "https://google.example/search-title",
                        ],
                        "fallback_store_search_url": "https://animate.example/sphone/search",
                        "fallback_search_queries": ["exact title", "ko title"],
                        "fallback_search_terms": ["exact title"],
                        "allowed_source_domains": ["www.animate-onlineshop.jp"],
                    }
                ]
            },
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["summary"]["fallback_bridge_rows"], 1)
        self.assertEqual(report["summary"]["next_action_lanes"], [["fallback_source_search", 1]])
        self.assertEqual(report["summary"]["completion_readiness_status"], "fallback_search_required")
        self.assertEqual(report["summary"]["no_candidate_items"], 1)
        self.assertEqual(report["summary"]["review_bucket_counts"], [["fallback_search_required", 1]])
        self.assertEqual(report["summary"]["review_decision_counts"], [["fallback_search_required", 1]])
        self.assertEqual(report["items"][0]["review_decision"]["decision"], "fallback_search_required")
        self.assertEqual(report["fallback_bridge_items"][0]["catalog_index"], 9)
        self.assertEqual(
            report["fallback_bridge_items"][0]["domain_limited_web_search_url_count"],
            2,
        )
        self.assertEqual(
            report["fallback_bridge_items"][0]["first_domain_limited_web_search_url"],
            "https://google.example/search-exact",
        )
        self.assertEqual(
            report["fallback_bridge_items"][0]["fallback_store_search_url"],
            "https://animate.example/sphone/search",
        )
        self.assertEqual(
            report["fallback_bridge_items"][0]["fallback_queue_report"],
            "data/source_discovery_next_focus_fallback_queue_public.json",
        )
        self.assertEqual(
            report["candidate_review_work_order"][0]["recommended_next_step"],
            "use_fallback_queue_to_find_exact_source_url",
        )
        self.assertEqual(
            report["candidate_review_work_order"][0]["review_decision"]["decision"],
            "fallback_search_required",
        )
        self.assertEqual(report["next_action_lanes"][0]["lane"], "fallback_source_search")
        self.assertEqual(report["next_action_lanes"][0]["row_count"], 1)
        self.assertEqual(report["next_action_lanes"][0]["fallback_search_url_count"], 2)
        self.assertEqual(
            report["next_action_lanes"][0]["sample_items"][0][
                "first_domain_limited_web_search_url"
            ],
            "https://google.example/search-exact",
        )
        self.assertEqual(report["completion_readiness"]["status"], "fallback_search_required")
        self.assertEqual(
            report["completion_readiness"]["next_safe_phase"],
            "use_fallback_queue_to_find_exact_source_url",
        )
        self.assertIn("fallback_search_required", report["completion_readiness"]["blocked_reasons"])

    def test_build_report_marks_broad_variant_rows_before_import(self) -> None:
        source = {
            "summary": {
                "focus_pack_id": "source-discovery-focus-001",
                "source_store": "animate",
                "target_category": "acrylic stand",
            },
            "items": [
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "catalog_index": 10,
                    "source_store": "animate",
                    "category": "acrylic stand",
                    "name_ko": "acrylic stand",
                    "search_query": "acrylic stand",
                }
            ],
        }

        report = builder.build_report(
            source,
            search_fn=lambda _item: [
                ProductImage(
                    title="JoJo acrylic stand Iggy",
                    image_url="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550000000000_1.jpg&width=400&height=400&square=1",
                    source_url="https://www.animate-onlineshop.jp/pn/test/pd/7654321/",
                ),
                ProductImage(
                    title="JoJo acrylic stand Jotaro",
                    image_url="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550000000001_1.jpg&width=400&height=400&square=1",
                    source_url="https://www.animate-onlineshop.jp/pn/test/pd/7654322/",
                )
            ],
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(
            report["summary"]["review_decision_counts"],
            [["catalog_variant_detail_required_before_import", 1]],
        )
        self.assertEqual(report["summary"]["variant_detail_required_rows"], 1)
        self.assertEqual(report["summary"]["metadata_enrichment_template_rows"], 1)
        self.assertEqual(report["summary"]["metadata_field_import_template_rows"], 3)
        self.assertEqual(report["summary"]["metadata_field_import_supported_rows"], 3)
        self.assertEqual(report["summary"]["next_action_lanes"], [["catalog_variant_metadata_enrichment", 1]])
        self.assertEqual(report["summary"]["completion_readiness_status"], "variant_detail_required")
        self.assertEqual(report["summary"]["exact_candidate_confirmation_ready_items"], 0)
        decision = report["items"][0]["review_decision"]
        self.assertEqual(decision["decision"], "catalog_variant_detail_required_before_import")
        self.assertIn("catalog_row_is_too_broad_for_single_product_image", decision["reasons"])
        self.assertEqual(report["completion_readiness"]["status"], "variant_detail_required")
        self.assertIn(
            "catalog_variant_detail_required_before_import",
            report["completion_readiness"]["blocked_reasons"],
        )
        metadata_row = report["metadata_enrichment_template"][0]
        self.assertFalse(metadata_row["manual_confirmed"])
        self.assertEqual(metadata_row["catalog_index"], 10)
        self.assertEqual(metadata_row["current_name_ko"], "acrylic stand")
        self.assertEqual(metadata_row["top_candidate_title"], "JoJo acrylic stand Iggy")
        self.assertEqual(
            metadata_row["top_candidate_source_url"],
            "https://www.animate-onlineshop.jp/pn/test/pd/7654321/",
        )
        self.assertEqual(len(metadata_row["candidate_options"]), 2)
        self.assertEqual(metadata_row["suggested_name_ja"], "")
        self.assertEqual(metadata_row["suggested_sub_series"], "")
        self.assertIn("exact_variant_or_character_name", metadata_row["required_evidence"])
        field_rows = report["metadata_field_import_template"]
        self.assertEqual([row["field"] for row in field_rows], ["sub_series", "name_ja", "character_name"])
        self.assertEqual(field_rows[0]["catalog_index"], 10)
        self.assertEqual(field_rows[0]["manual_value"], "")
        self.assertFalse(field_rows[0]["manual_confirmed"])
        self.assertTrue(field_rows[0]["import_supported"])
        self.assertEqual(
            field_rows[0]["import_tool"],
            "tools/import_confirmed_catalog_field_rows.py",
        )
        self.assertTrue(field_rows[1]["import_supported"])
        self.assertEqual(
            field_rows[1]["import_tool"],
            "tools/import_confirmed_catalog_field_rows.py",
        )
        self.assertTrue(field_rows[2]["import_supported"])
        self.assertIn(
            "metadata_field_import_template",
            report["automation_policy"],
        )
        self.assertEqual(
            report["automation_policy"]["metadata_field_import_supported_fields"],
            ["sub_series", "name_ja", "character_name"],
        )

    def test_build_report_uses_localized_animate_query_for_korean_only_rows(self) -> None:
        source = {
            "summary": {
                "focus_pack_id": "source-discovery-focus-001",
                "source_store": "애니메이트",
                "target_category": "아크릴 스탠드",
            },
            "items": [
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "catalog_index": 3,
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "name_ko": "카드캡터 체리 아크릴 스탠드 (사쿠라)",
                    "name_ja": "",
                    "search_query": "카드캡터 체리 아크릴 스탠드 (사쿠라)",
                    "catalog_field_import_template": {
                        "affiliation": "카드캡터 체리",
                        "category": "아크릴 스탠드",
                        "name_ko": "카드캡터 체리 아크릴 스탠드 (사쿠라)",
                        "name_ja": "",
                        "source_store": "애니메이트",
                    },
                }
            ],
        }
        seen_queries: list[str] = []

        def search(item):
            seen_queries.append(builder._query_for_item(item))
            return []

        report = builder.build_report(
            source,
            search_fn=search,
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(seen_queries, ["カードキャプターさくら アクリルスタンド 木之本桜"])
        self.assertEqual(
            report["items"][0]["search_query"],
            "カードキャプターさくら アクリルスタンド 木之本桜",
        )
        self.assertEqual(report["items"][0]["affiliation"], "카드캡터 체리")

    def test_candidate_row_explains_manual_review_blockers(self) -> None:
        row = builder._candidate_row(
            "Oshi no Ko acrylic stand (Ruby)",
            ProductImage(
                title="Oshi no Ko acrylic stand Ai",
                image_url="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550000000000_1.jpg&width=400&height=400&square=1",
                source_url="https://www.animate-onlineshop.jp/pn/test/pd/1234567/",
            ),
            1,
        )

        self.assertEqual(row["review_status"], "manual_candidate_review")
        self.assertFalse(row["exact_candidate_gate_passed"])
        self.assertIn("distinctive_tokens_missing", row["exact_candidate_blockers"])
        self.assertIn("parenthetical_terms_missing", row["exact_candidate_blockers"])

    def test_candidate_row_accepts_tensura_title_alias(self) -> None:
        row = builder._candidate_row(
            "転スラ アクリルスタンド (リムル)",
            ProductImage(
                title="転生したらスライムだった件 アクリルスタンド リムル",
                image_url="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550000000000_1.jpg&width=400&height=400&square=1",
                source_url="https://www.animate-onlineshop.jp/pn/test/pd/1234567/",
            ),
            1,
        )

        self.assertEqual(row["review_status"], "exact_candidate_review")
        self.assertTrue(row["exact_candidate_gate_passed"])
        self.assertEqual(row["exact_candidate_blockers"], [])

    def test_candidate_row_keeps_broad_queries_in_manual_review(self) -> None:
        row = builder._candidate_row(
            "ジョジョの奇妙な冒険 アクリルスタンド",
            ProductImage(
                title="ジョジョの奇妙な冒険 オラオラオーバードライブ アクリルスタンド イギー",
                image_url="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550000000000_1.jpg&width=400&height=400&square=1",
                source_url="https://www.animate-onlineshop.jp/pn/test/pd/1234567/",
            ),
            1,
        )

        self.assertEqual(row["review_status"], "manual_candidate_review")
        self.assertFalse(row["exact_candidate_gate_passed"])
        self.assertIn("broad_query_without_variant", row["exact_candidate_blockers"])


if __name__ == "__main__":
    unittest.main()
