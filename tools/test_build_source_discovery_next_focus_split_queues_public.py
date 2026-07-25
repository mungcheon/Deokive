from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_split_queues_public as split_queues


class SourceDiscoveryNextFocusSplitQueueTests(unittest.TestCase):
    def test_exact_url_queue_exposes_manual_patch_template(self):
        payload = {
            "review_table": [
                {
                    "catalog_index": 922,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "엔스카이",
                    "category": "키링",
                    "name_ko": "치이카와 러버 스트랩 (우사기)",
                    "name_ja": "ちいかわ ラバーストラップ (うさぎ)",
                    "primary_review_url": "https://www.google.com/search?q=example",
                    "primary_review_url_kind": "domain_limited_web_search",
                    "fallback_store_search_url": "https://www.enskyshop.com/products/list?name=example",
                    "can_confirm_source_url_after_page_match": True,
                    "acceptance_rule": "exact product only",
                    "source_url_review_guidance": {
                        "allowed_source_domains": ["www.enskyshop.com"],
                        "accepted_source_url_patterns": [
                            "https://www.enskyshop.com/products/detail/..."
                        ],
                        "rejected_source_url_patterns": ["Google search result URLs"],
                        "confirmation_checks": ["title matches"],
                    },
                    "identity_review_status": "exact_page_match_review_ready",
                }
            ]
        }
        fetch_audit = {
            "items": [
                {
                    "catalog_index": 922,
                    "broad_result_page": True,
                    "sample_product_detail_links": [
                        "https://www.enskyshop.com/products/detail/30883"
                    ],
                }
            ]
        }

        exact_report, identity_report = split_queues.build_reports(
            payload,
            fetch_audit=fetch_audit,
            generated_at="2026-07-25T00:00:00Z",
        )

        self.assertEqual(identity_report["summary"]["queue_rows"], 0)
        template = exact_report["source_url_confirmation_patch_template"]
        self.assertEqual(
            template["status"], "manual_exact_source_url_confirmation_required"
        )
        self.assertEqual(template["template_rows"], 1)
        self.assertEqual(template["ready_to_import_rows"], 0)
        self.assertEqual(template["blocked_rows"], 1)
        self.assertEqual(template["candidate_detail_link_rows"], 1)
        self.assertIs(template["auto_apply_enabled"], False)
        row = template["rows"][0]
        self.assertEqual(row["catalog_index"], 922)
        self.assertEqual(row["manual_confirmed_source_url"], "")
        self.assertEqual(
            row["candidate_detail_links"],
            ["https://www.enskyshop.com/products/detail/30883"],
        )
        self.assertEqual(row["allowed_source_domains"], ["www.enskyshop.com"])
        self.assertIn("exact product detail page", row["ready_condition"])


if __name__ == "__main__":
    unittest.main()
