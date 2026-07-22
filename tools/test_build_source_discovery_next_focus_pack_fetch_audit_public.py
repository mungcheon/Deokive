from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_pack_fetch_audit_public as target


class SourceDiscoveryNextFocusPackFetchAuditPublicTest(unittest.TestCase):
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
        self.assertTrue(report["summary"]["fallback_web_search_required"])
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["items"][0]["needs_fallback_web_search"])
        self.assertTrue(report["items"][1]["needs_fallback_web_search"])

    def test_fetcher_marks_missing_url_without_network(self) -> None:
        result = target.fetch_url("")

        self.assertEqual(result["fetch_status"], "missing_url")
        self.assertIsNone(result["http_status"])


if __name__ == "__main__":
    unittest.main()
