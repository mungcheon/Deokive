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
        self.assertEqual(report["summary"]["fallback_bridge_rows"], 0)
        self.assertEqual(
            report["summary"]["review_bucket_counts"],
            [["exact_candidate_shortlist_review", 1], ["no_candidate_manual_source_research", 1]],
        )
        first = report["items"][0]
        self.assertEqual(first["manual_review_status"], "not_started")
        self.assertEqual(first["review_bucket"], "exact_candidate_shortlist_review")
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
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["summary"]["fallback_bridge_rows"], 1)
        self.assertEqual(report["summary"]["no_candidate_items"], 1)
        self.assertEqual(report["summary"]["review_bucket_counts"], [["fallback_search_required", 1]])
        self.assertEqual(report["fallback_bridge_items"][0]["catalog_index"], 9)
        self.assertEqual(
            report["fallback_bridge_items"][0]["fallback_queue_report"],
            "data/source_discovery_next_focus_fallback_queue_public.json",
        )
        self.assertEqual(
            report["candidate_review_work_order"][0]["recommended_next_step"],
            "use_fallback_queue_to_find_exact_source_url",
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
