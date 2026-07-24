from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_exact_url_candidate_audit_public as target


class SourceDiscoveryNextFocusExactUrlCandidateAuditPublicTest(unittest.TestCase):
    def test_broad_store_search_is_not_auto_apply_ready(self) -> None:
        queue = {
            "items": [
                {
                    "catalog_index": 1,
                    "source_store": "Ensky",
                    "name_ja": "ちいかわ ラバーストラップ (うさぎ)",
                    "fallback_store_search_url": "https://www.enskyshop.com/products/list?name=x",
                }
            ]
        }
        links = "".join(
            f'<a href="/products/detail/{10000 + index}">Other product {index}</a>'
            for index in range(target.BROAD_RESULT_LINK_THRESHOLD + 1)
        )

        report = target.build_report(queue, generated_at="2026-01-01T00:00:00Z", fetcher=lambda _: links)

        self.assertEqual(report["summary"]["queue_rows"], 1)
        self.assertEqual(report["summary"]["store_search_broad_result_rows"], 1)
        self.assertEqual(report["summary"]["auto_apply_ready_rows"], 0)
        self.assertTrue(report["items"][0]["broad_result_page"])
        self.assertEqual(report["items"][0]["candidate_source_urls"], [])
        self.assertEqual(report["items"][0]["recommended_next_action"], "use_domain_limited_web_search_url")

    def test_exact_title_candidate_is_manual_review_only(self) -> None:
        queue = {
            "items": [
                {
                    "catalog_index": 2,
                    "source_store": "Ensky",
                    "name_ja": "五条悟 ラバーストラップ",
                    "fallback_store_search_url": "https://www.enskyshop.com/products/list?name=y",
                }
            ]
        }
        html = """
        <div class="ec-shelfGrid__item">
          <a href="/products/detail/12345">五条悟 ラバーストラップ</a>
        </div>
        """

        report = target.build_report(queue, generated_at="2026-01-01T00:00:00Z", fetcher=lambda _: html)

        self.assertEqual(report["summary"]["exact_title_candidate_rows"], 1)
        self.assertEqual(report["summary"]["manual_review_candidate_rows"], 1)
        self.assertEqual(report["summary"]["auto_apply_ready_rows"], 0)
        self.assertFalse(report["items"][0]["broad_result_page"])
        self.assertEqual(
            report["items"][0]["candidate_source_urls"],
            ["https://www.enskyshop.com/products/detail/12345"],
        )
        self.assertEqual(
            report["items"][0]["recommended_next_action"],
            "review_exact_title_candidate_source_urls",
        )


if __name__ == "__main__":
    unittest.main()
