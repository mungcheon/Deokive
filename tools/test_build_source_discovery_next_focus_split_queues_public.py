from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_split_queues_public as split_queues


class SourceDiscoveryNextFocusSplitQueuesPublicTest(unittest.TestCase):
    def test_splits_exact_url_and_identity_backfill_rows(self) -> None:
        payload = {
            "review_table": [
                {
                    "catalog_index": 1,
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "name_ko": "ready item",
                    "identity_review_status": "exact_page_match_review_ready",
                    "can_confirm_source_url_after_page_match": True,
                    "first_domain_limited_web_search_url": "https://www.google.com/search?q=ready",
                    "fallback_store_search_url": "https://www.animate-onlineshop.jp/sphone/products/list.php?mode=search&smt=ready",
                    "source_url_review_guidance": {
                        "rejected_source_url_patterns": ["Google search result URLs"],
                    },
                },
                {
                    "catalog_index": 2,
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "name_ko": "blocked item",
                    "identity_review_status": "variant_disambiguation_required",
                    "identity_blockers": ["missing_name_ja", "variant_or_character_not_explicit"],
                    "requires_metadata_backfill": True,
                    "requires_variant_disambiguation": True,
                    "fallback_store_search_url": "https://www.animate-onlineshop.jp/sphone/products/list.php?mode=search&smt=blocked",
                    "source_url_review_guidance": {
                        "rejected_source_url_patterns": ["Animate products/list.php search pages"],
                    },
                },
            ]
        }

        fetch_audit = {
            "items": [
                {
                    "catalog_index": 1,
                    "sample_product_detail_links": [
                        "/products/detail/123",
                        "https://www.animate-onlineshop.jp/products/detail.php?product_id=456",
                    ],
                }
            ]
        }

        exact, identity = split_queues.build_reports(
            payload,
            fetch_audit=fetch_audit,
            generated_at="2026-07-24T00:00:00Z",
        )

        self.assertEqual(exact["summary"]["queue_rows"], 1)
        self.assertEqual(exact["summary"]["blocked_identity_rows"], 1)
        self.assertEqual(exact["summary"]["primary_review_url_rows"], 1)
        self.assertEqual(exact["summary"]["candidate_detail_link_rows"], 1)
        self.assertEqual(exact["summary"]["candidate_detail_links"], 2)
        self.assertEqual(exact["summary"]["first_primary_review_url"], "https://www.google.com/search?q=ready")
        self.assertEqual(exact["summary"]["first_primary_review_url_kind"], "domain_limited_web_search")
        self.assertEqual(exact["items"][0]["next_action"], "open_search_url_confirm_exact_product_detail_page_then_fill_manual_confirmed_source_url")
        self.assertEqual(exact["items"][0]["primary_review_url"], "https://www.google.com/search?q=ready")
        self.assertEqual(exact["items"][0]["primary_review_url_kind"], "domain_limited_web_search")
        self.assertEqual(exact["items"][0]["candidate_detail_link_count"], 2)
        self.assertEqual(
            exact["items"][0]["candidate_detail_links"][0],
            "https://www.animate-onlineshop.jp/products/detail/123",
        )
        self.assertEqual(
            exact["items"][0]["first_candidate_detail_link"],
            "https://www.animate-onlineshop.jp/products/detail/123",
        )
        self.assertEqual(
            exact["items"][0]["source_url_review_guidance"]["rejected_source_url_patterns"],
            ["Google search result URLs"],
        )
        self.assertFalse(exact["automation_policy"]["auto_apply_source_url"])

        self.assertEqual(identity["summary"]["queue_rows"], 1)
        self.assertEqual(identity["summary"]["exact_url_review_ready_rows"], 1)
        self.assertEqual(identity["summary"]["metadata_backfill_required_rows"], 1)
        self.assertEqual(identity["summary"]["variant_disambiguation_required_rows"], 1)
        self.assertEqual(identity["summary"]["primary_review_url_rows"], 1)
        self.assertEqual(identity["summary"]["first_primary_review_url_kind"], "fallback_store_search")
        self.assertEqual(identity["items"][0]["identity_blockers"], ["missing_name_ja", "variant_or_character_not_explicit"])
        self.assertEqual(
            identity["items"][0]["primary_review_url"],
            "https://www.animate-onlineshop.jp/sphone/products/list.php?mode=search&smt=blocked",
        )
        self.assertEqual(
            identity["items"][0]["source_url_review_guidance"]["rejected_source_url_patterns"],
            ["Animate products/list.php search pages"],
        )
        self.assertFalse(identity["automation_policy"]["auto_apply_metadata"])


if __name__ == "__main__":
    unittest.main()
