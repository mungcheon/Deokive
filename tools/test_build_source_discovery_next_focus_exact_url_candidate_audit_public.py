from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_exact_url_candidate_audit_public as audit


class SourceDiscoveryExactUrlCandidateAuditTests(unittest.TestCase):
    def test_broad_result_sample_links_include_cached_page_titles(self):
        calls: list[str] = []

        def fetcher(url: str) -> str:
            calls.append(url)
            if "products/list" in url:
                links = "".join(
                    f'<a href="/products/detail/{index}">item</a>'
                    for index in range(100, 135)
                )
                return f"<html><body>{links}</body></html>"
            return (
                "<html><head><title>Wrong Pretty Cure Product ｜ "
                "エンスカイショップ</title></head>"
                "<body><h1>Wrong Pretty Cure Product</h1></body></html>"
            )

        queue = {
            "items": [
                {
                    "catalog_index": 922,
                    "source_store": "엔스카이",
                    "category": "키링",
                    "name_ja": "ちいかわ ラバーストラップ (うさぎ)",
                    "fallback_store_search_url": "https://www.enskyshop.com/products/list?name=sample",
                },
                {
                    "catalog_index": 923,
                    "source_store": "엔스카이",
                    "category": "키링",
                    "name_ja": "ちいかわ ラバーストラップ (ハチワレ)",
                    "fallback_store_search_url": "https://www.enskyshop.com/products/list?name=sample",
                },
            ]
        }

        report = audit.build_report(
            queue,
            generated_at="2026-07-25T00:00:00Z",
            fetcher=fetcher,
            cache_coverage={
                "items": [
                    {
                        "catalog_index": 922,
                        "status": "broad_cache_candidate",
                        "candidate_count": 2,
                        "safe_exact_match": False,
                        "candidates": [
                            {
                                "title": "Wrong Chiikawa Rubber Strap",
                                "source_url": "https://www.enskyshop.com/products/detail/100",
                                "image_url": "https://www.enskyshop.com/image.jpg",
                            }
                        ],
                    },
                    {
                        "catalog_index": 923,
                        "status": "no_cache_candidate",
                        "candidate_count": 0,
                        "safe_exact_match": False,
                    },
                ]
            },
        )

        self.assertEqual(report["summary"]["queue_rows"], 2)
        self.assertEqual(report["summary"]["store_search_broad_result_rows"], 2)
        self.assertEqual(report["summary"]["sample_product_detail_link_snapshot_rows"], 10)
        self.assertEqual(report["summary"]["unique_sample_product_detail_link_snapshots"], 5)
        self.assertEqual(report["summary"]["sample_product_detail_link_title_mismatch_rows"], 10)
        self.assertEqual(
            report["summary"]["sample_product_detail_link_title_match_counts"],
            [("title_mismatch", 10)],
        )
        self.assertEqual(report["summary"]["ensky_cache_cross_checked_rows"], 2)
        self.assertEqual(report["summary"]["ensky_cache_safe_exact_match_rows"], 0)
        self.assertEqual(report["summary"]["ensky_cache_broad_candidate_rows"], 1)
        self.assertEqual(report["summary"]["ensky_cache_no_candidate_rows"], 1)
        self.assertEqual(
            report["summary"]["ensky_cache_status_counts"],
            [("broad_cache_candidate", 1), ("no_cache_candidate", 1)],
        )
        self.assertEqual(
            report["items"][0]["ensky_cache_coverage"]["top_candidate_source_url"],
            "https://www.enskyshop.com/products/detail/100",
        )
        first = report["items"][0]["sample_product_detail_link_snapshots"][0]
        self.assertEqual(first["fetch_status"], "ok")
        self.assertEqual(first["title_match_status"], "title_mismatch")
        self.assertEqual(first["title"], "Wrong Pretty Cure Product ｜ エンスカイショップ")
        self.assertEqual(first["h1"], "Wrong Pretty Cure Product")
        self.assertEqual(calls.count("https://www.enskyshop.com/products/detail/100"), 1)


if __name__ == "__main__":
    unittest.main()
