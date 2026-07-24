from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_fallback_queue_public as target


class SourceDiscoveryNextFocusFallbackQueuePublicTest(unittest.TestCase):
    def test_write_report_skips_timestamp_only_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fallback_queue.json"
            report = {
                "schema_version": 1,
                "generated_at": "2026-01-01T00:00:00Z",
                "summary": {"queue_rows": 1},
                "items": [],
            }
            target.write_report(report, path)
            first_mtime = path.stat().st_mtime_ns

            target.write_report({**report, "generated_at": "2026-01-01T00:01:00Z"}, path)

            self.assertEqual(path.stat().st_mtime_ns, first_mtime)

    def test_build_report_keeps_only_fallback_required_rows(self) -> None:
        next_pack = {
            "summary": {"focus_pack_id": "source-discovery-focus-001"},
            "items": [
                {
                    "catalog_index": 1,
                    "focus_pack_id": "source-discovery-focus-001",
                    "pack_sequence": 1,
                    "source_store": "Animate",
                    "category": "Acrylic stand",
                    "name_ko": "A",
                    "name_ja": "A",
                    "search_query": "A acrylic",
                    "review_state": "official_search_review_required",
                    "workflow": "official_search_url_available",
                    "official_search_url": "https://animate.example/products/list.php?mode=search&smt=A",
                    "web_search_url": "https://google.example/search?q=A",
                    "allowed_source_domains": ["www.animate-onlineshop.jp"],
                    "manual_review_checklist": ["Confirm exact product page"],
                    "acceptance_rule": "exact match",
                    "source_patch_template": {"catalog_index": 1, "source_url": "<exact>"},
                    "catalog_field_import_template": {"row_index": 1, "field": "source_url"},
                },
                {
                    "catalog_index": 2,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "category": "Badge",
                    "name_ko": "B",
                    "official_search_url": "https://animate.example/products/list.php?mode=search&smt=B",
                },
            ],
        }
        fetch_audit = {
            "items": [
                {
                    "catalog_index": 1,
                    "needs_fallback_web_search": True,
                    "fetch_status": "http_error",
                    "http_status": 404,
                },
                {
                    "catalog_index": 2,
                    "needs_fallback_web_search": False,
                    "fetch_status": "ok",
                    "http_status": 200,
                },
            ]
        }

        report = target.build_report(next_pack, fetch_audit, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["queue_rows"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_rows"], 0)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_source_url"])
        self.assertEqual(
            report["automation_policy"]["import_tool"],
            "tools/import_confirmed_source_discovery_rows.py",
        )
        self.assertEqual(report["summary"]["by_http_status"], [("404", 1)])
        self.assertEqual(report["summary"]["fallback_query_count"], 3)
        self.assertEqual(report["summary"]["domain_limited_web_search_url_count"], 3)
        self.assertEqual(report["summary"]["work_order_steps"], 3)
        self.assertEqual(
            report["summary"]["work_order_lanes"],
            [
                "domain_limited_exact_title_search",
                "legacy_mobile_store_search",
                "evidence_fill_and_dry_run",
            ],
        )
        self.assertIn(
            "site%3Awww.animate-onlineshop.jp",
            report["summary"]["first_domain_limited_web_search_url"],
        )
        self.assertIn(
            "sphone/products/list.php",
            report["summary"]["first_fallback_store_search_url"],
        )
        self.assertEqual(
            report["summary"]["first_primary_review_url_kind"],
            "domain_limited_web_search",
        )
        self.assertIn(
            "site%3Awww.animate-onlineshop.jp",
            report["summary"]["first_primary_review_url"],
        )
        self.assertEqual(
            [step["lane"] for step in report["work_order"]],
            [
                "domain_limited_exact_title_search",
                "legacy_mobile_store_search",
                "evidence_fill_and_dry_run",
            ],
        )
        self.assertEqual(report["work_order"][0]["query_count"], 1)
        item = report["items"][0]
        self.assertEqual(item["catalog_index"], 1)
        self.assertEqual(item["manual_review_status"], "fallback_not_started")
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["search_query"], "A acrylic")
        self.assertEqual(item["review_state"], "official_search_review_required")
        self.assertEqual(item["workflow"], "official_search_url_available")
        self.assertEqual(item["manual_review_checklist"], ["Confirm exact product page"])
        self.assertIn("sphone/products/list.php", item["fallback_store_search_url"])
        self.assertEqual(item["primary_review_url_kind"], "domain_limited_web_search")
        self.assertEqual(item["primary_review_url"], item["domain_limited_web_search_urls"][0])
        self.assertEqual(item["fallback_search_terms"], ["A"])
        self.assertEqual(len(item["fallback_search_queries"]), 3)
        self.assertTrue(
            item["fallback_search_queries"][0]["query"].startswith(
                'site:www.animate-onlineshop.jp/pn/ "A"'
            )
        )
        self.assertIn("site%3Awww.animate-onlineshop.jp", item["domain_limited_web_search_urls"][0])
        self.assertEqual(item["source_patch_template"]["catalog_index"], 1)
        self.assertEqual(item["catalog_field_import_template"]["field"], "source_url")
        review_row = report["review_table"][0]
        self.assertEqual(review_row["review_priority"], 1)
        self.assertEqual(review_row["primary_review_url"], item["primary_review_url"])
        self.assertEqual(review_row["primary_review_url_kind"], "domain_limited_web_search")
        self.assertIn(
            "Google search result URLs",
            review_row["source_url_review_guidance"]["rejected_source_url_patterns"],
        )
        self.assertIn(
            "https://www.animate-onlineshop.jp/pn/.../pd/...",
            report["manual_entry_template"]["source_url_review_guidance"][
                "accepted_source_url_patterns"
            ],
        )

    def test_fallback_terms_prefer_localized_animate_query(self) -> None:
        next_pack = {
            "summary": {"focus_pack_id": "source-discovery-focus-001"},
            "items": [
                {
                    "catalog_index": 10,
                    "focus_pack_id": "source-discovery-focus-001",
                    "pack_sequence": 1,
                    "source_store": "애니메이트",
                    "affiliation": "슬램덩크",
                    "category": "아크릴 스탠드",
                    "name_ko": "슬램덩크 아크릴 스탠드 (서태웅)",
                    "name_ja": None,
                    "search_query": "슬램덩크 아크릴 스탠드 (서태웅)",
                    "official_search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=old",
                    "allowed_source_domains": ["www.animate-onlineshop.jp"],
                }
            ],
        }
        fetch_audit = {
            "items": [
                {
                    "catalog_index": 10,
                    "needs_fallback_web_search": True,
                    "fetch_status": "ok",
                    "http_status": 200,
                }
            ]
        }

        report = target.build_report(next_pack, fetch_audit, generated_at="2026-01-01T00:00:00Z")

        item = report["items"][0]
        self.assertEqual(item["fallback_search_terms"][0], "SLAM DUNK アクリルスタンド 流川楓")
        self.assertIn("SLAM+DUNK", item["fallback_store_search_url"])
        self.assertIn("SLAM+DUNK", item["domain_limited_web_search_urls"][0])

    def test_ensky_focus_uses_ensky_detail_guidance(self) -> None:
        next_pack = {
            "summary": {"focus_pack_id": "source-discovery-focus-001"},
            "items": [
                {
                    "catalog_index": 20,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Ensky",
                    "category": "Keychain",
                    "name_ko": "Chiikawa rubber strap",
                    "name_ja": "ちいかわ ラバーストラップ",
                    "official_search_url": "https://www.enskyshop.com/products/list?name=chiikawa",
                    "allowed_source_domains": ["www.enskyshop.com", "www.ensky.co.jp"],
                }
            ],
        }
        fetch_audit = {
            "items": [
                {
                    "catalog_index": 20,
                    "needs_fallback_web_search": True,
                    "fetch_status": "ok_200_broad_result_set",
                    "http_status": 200,
                }
            ]
        }

        report = target.build_report(next_pack, fetch_audit, generated_at="2026-01-01T00:00:00Z")

        item = report["items"][0]
        review_row = report["review_table"][0]
        self.assertIn("site%3Awww.enskyshop.com%2Fproducts%2Fdetail", item["domain_limited_web_search_urls"][0])
        self.assertIn(
            "https://www.enskyshop.com/products/detail/...",
            review_row["source_url_review_guidance"]["accepted_source_url_patterns"],
        )
        self.assertNotIn(
            "https://www.animate-onlineshop.jp/pn/.../pd/...",
            review_row["source_url_review_guidance"]["accepted_source_url_patterns"],
        )
        self.assertIn("Ensky products/list search pages", review_row["source_url_review_guidance"]["rejected_source_url_patterns"])

    def test_character_title_without_parentheses_can_move_to_exact_review(self) -> None:
        next_pack = {
            "summary": {"focus_pack_id": "source-discovery-focus-001"},
            "items": [
                {
                    "catalog_index": 30,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Ensky",
                    "category": "Keychain",
                    "name_ko": "고죠 사토루 러버 스트랩",
                    "name_ja": "五条悟 ラバーストラップ",
                    "official_search_url": "https://www.enskyshop.com/products/list?name=gojo",
                    "allowed_source_domains": ["www.enskyshop.com"],
                }
            ],
        }
        fetch_audit = {
            "items": [
                {
                    "catalog_index": 30,
                    "needs_fallback_web_search": True,
                    "fetch_status": "ok_200_broad_result_set",
                    "http_status": 200,
                }
            ]
        }

        report = target.build_report(next_pack, fetch_audit, generated_at="2026-01-01T00:00:00Z")

        review_row = report["review_table"][0]
        self.assertEqual(review_row["identity_review_status"], "exact_page_match_review_ready")
        self.assertEqual(review_row["identity_blockers"], [])
        self.assertTrue(review_row["can_confirm_source_url_after_page_match"])


if __name__ == "__main__":
    unittest.main()
