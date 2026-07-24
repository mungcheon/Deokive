from __future__ import annotations

import unittest

import tools.build_source_discovery_next_focus_live_source_probe_public as probe


class SourceDiscoveryNextFocusLiveSourceProbePublicTest(unittest.TestCase):
    def test_extract_candidates_keeps_only_product_detail_links(self) -> None:
        page = """
        <a href="/products/list.php?mode=search&smt=sample">search</a>
        <a href="/pn/Test Product/pd/123456/">Test Product</a>
        <a href="/products/detail.php?product_id=987654">Detail Product</a>
        <a href="/mypage/">account</a>
        """

        candidates = probe.extract_candidates(page, base_url="https://www.animate-onlineshop.jp/products/list.php")

        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            candidates[0]["source_url"],
            "https://www.animate-onlineshop.jp/pn/Test Product/pd/123456/",
        )
        self.assertEqual(candidates[1]["page_title"], "Detail Product")

    def test_extract_candidates_uses_decoded_url_title_when_anchor_text_is_empty(self) -> None:
        page = '<a href="/pn/%E3%82%B5%E3%83%B3%E3%83%97%E3%83%AB/pd/123/"><img alt=""></a>'

        candidates = probe.extract_candidates(page, base_url="https://www.animate-onlineshop.jp/")

        self.assertEqual(candidates[0]["page_title"], "サンプル")

    def test_build_report_marks_rows_without_candidates_for_alternate_research(self) -> None:
        queue = {
            "items": [
                {
                    "catalog_index": 10,
                    "name_ko": "샘플",
                    "fallback_store_search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=sample",
                    "source_url_review_guidance": {"rejected_source_url_patterns": ["Google search result URLs"]},
                }
            ]
        }

        report = probe.build_report(
            queue,
            fetcher=lambda url: (200, url, "<html>No products</html>"),
            generated_at="2026-07-24T00:00:00Z",
        )

        self.assertEqual(report["summary"]["probed_rows"], 1)
        self.assertEqual(report["summary"]["detail_candidate_rows"], 0)
        self.assertEqual(report["items"][0]["probe_status"], "no_detail_candidates_on_search_page")
        self.assertEqual(
            report["items"][0]["blocked_until"],
            "alternate_exact_source_url_research_required",
        )
        self.assertFalse(report["automation_policy"]["auto_apply_source_url"])

    def test_build_report_records_product_candidates_as_manual_review_only(self) -> None:
        queue = {
            "items": [
                {
                    "catalog_index": 20,
                    "name_ko": "샘플",
                    "fallback_store_search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=sample",
                }
            ]
        }
        page = '<a href="/pn/Exact/pd/111/">Exact title</a>'

        report = probe.build_report(
            queue,
            fetcher=lambda url: (200, url, page),
            generated_at="2026-07-24T00:00:00Z",
        )

        self.assertEqual(report["summary"]["detail_candidate_rows"], 1)
        self.assertEqual(report["summary"]["detail_candidate_total"], 1)
        self.assertEqual(report["items"][0]["probe_status"], "detail_candidates_found")
        self.assertEqual(report["items"][0]["strong_title_match_candidate_count"], 0)
        self.assertFalse(report["items"][0]["auto_apply_enabled"])
        self.assertEqual(
            report["items"][0]["candidates"][0]["source_url"],
            "https://www.animate-onlineshop.jp/pn/Exact/pd/111/",
        )


if __name__ == "__main__":
    unittest.main()
