from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_pack_fetch_audit_public as target


class SourceDiscoveryNextFocusPackFetchAuditPublicTest(unittest.TestCase):
    def test_write_report_skips_timestamp_only_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fetch_audit.json"
            report = {
                "schema_version": 1,
                "generated_at": "2026-01-01T00:00:00Z",
                "summary": {"pack_items": 1},
                "items": [],
            }
            target.write_report(report, path)
            first_mtime = path.stat().st_mtime_ns

            target.write_report({**report, "generated_at": "2026-01-01T00:01:00Z"}, path)

            self.assertEqual(path.stat().st_mtime_ns, first_mtime)

    def test_build_report_splits_ok_and_fallback_rows(self) -> None:
        pack = {
            "summary": {"focus_pack_id": "source-discovery-focus-001"},
            "items": [
                {
                    "catalog_index": 1,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "category": "Acrylic stand",
                    "name_ko": "A",
                    "name_ja": "A",
                    "official_search_url": "https://example.com/ok",
                    "web_search_url": "https://example.com/search-a",
                },
                {
                    "catalog_index": 2,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "category": "Acrylic stand",
                    "name_ko": "B",
                    "name_ja": "B",
                    "official_search_url": "https://example.com/missing",
                    "web_search_url": "https://example.com/search-b",
                },
            ],
        }

        def fake_fetch(url: str) -> dict[str, object]:
            if url.endswith("/ok"):
                return {"fetch_status": "ok", "http_status": 200, "final_url": url}
            return {"fetch_status": "http_error", "http_status": 404, "final_url": url}

        report = target.build_report(pack, fetcher=fake_fetch, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["generated_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(report["summary"]["pack_items"], 2)
        self.assertEqual(report["summary"]["official_search_ok_rows"], 1)
        self.assertEqual(report["summary"]["official_search_unavailable_rows"], 1)
        self.assertEqual(report["summary"]["store_fetch_blocked_rows"], 0)
        self.assertFalse(report["summary"]["all_unavailable_rows_are_store_fetch_blocked"])
        self.assertTrue(report["summary"]["fallback_web_search_required"])
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["items"][0]["needs_fallback_web_search"])
        self.assertTrue(report["items"][1]["needs_fallback_web_search"])
        self.assertFalse(report["items"][1]["store_fetch_blocked"])

    def test_build_report_marks_store_access_blocked_rows(self) -> None:
        pack = {
            "summary": {"focus_pack_id": "source-discovery-focus-001"},
            "items": [
                {
                    "catalog_index": 1,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "category": "Acrylic stand",
                    "name_ko": "A",
                    "name_ja": "A",
                    "official_search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=A",
                },
                {
                    "catalog_index": 2,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "category": "Acrylic stand",
                    "name_ko": "B",
                    "name_ja": "B",
                    "official_search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=B",
                },
            ],
        }

        def blocked_fetch(url: str) -> dict[str, object]:
            return {"fetch_status": "http_error", "http_status": 403, "final_url": url}

        report = target.build_report(pack, fetcher=blocked_fetch)

        self.assertEqual(report["summary"]["store_fetch_blocked_rows"], 2)
        self.assertEqual(
            report["summary"]["store_fetch_blocked_by_netloc"],
            [("www.animate-onlineshop.jp", 2)],
        )
        self.assertTrue(report["summary"]["all_unavailable_rows_are_store_fetch_blocked"])
        self.assertTrue(report["items"][0]["store_fetch_blocked"])
        self.assertEqual(
            report["items"][0]["fetch_block_reason"],
            "store_access_blocked_not_product_identity_failure",
        )
        self.assertEqual(
            report["items"][0]["recommended_next_action"],
            "use_domain_limited_search_or_legacy_store_search_for_exact_detail_url",
        )

    def test_build_report_marks_http_ok_no_results_as_fallback(self) -> None:
        pack = {
            "summary": {"focus_pack_id": "source-discovery-focus-001"},
            "items": [
                {
                    "catalog_index": 1,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "Animate",
                    "category": "Acrylic stand",
                    "name_ko": "A",
                    "name_ja": "A",
                    "official_search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=A",
                },
            ],
        }

        def no_result_fetch(url: str) -> dict[str, object]:
            return {
                "fetch_status": "ok",
                "http_status": 200,
                "final_url": url,
                "content_checked": True,
                "no_results_page": True,
                "product_detail_link_count": 0,
            }

        report = target.build_report(pack, fetcher=no_result_fetch)

        self.assertEqual(report["summary"]["official_search_ok_rows"], 0)
        self.assertEqual(report["summary"]["official_search_unavailable_rows"], 1)
        self.assertEqual(report["summary"]["official_search_no_result_rows"], 1)
        self.assertTrue(report["summary"]["fallback_web_search_required"])
        self.assertTrue(report["items"][0]["needs_fallback_web_search"])
        self.assertEqual(
            report["items"][0]["fetch_block_reason"],
            "official_search_returned_no_results",
        )

    def test_fetcher_marks_missing_url_without_network(self) -> None:
        result = target.fetch_url("")

        self.assertEqual(result["fetch_status"], "missing_url")
        self.assertIsNone(result["http_status"])


if __name__ == "__main__":
    unittest.main()
