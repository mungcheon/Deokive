from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_fallback_confirmed_template as template_builder


class SourceDiscoveryNextFocusFallbackConfirmedTemplateTest(unittest.TestCase):
    def test_build_template_from_review_table(self) -> None:
        payload = {
            "review_table": [
                {
                    "catalog_index": 1072,
                    "focus_pack_id": "source-discovery-focus-001",
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "name_ko": "최애의 아이 아크릴 스탠드 (호시노 아이)",
                    "name_ja": "推しの子 アクリルスタンド (星野アイ)",
                    "search_term": "推しの子 アクリルスタンド (星野アイ)",
                    "first_domain_limited_web_search_url": "https://www.google.com/search?q=example",
                    "fallback_store_search_url": "https://www.animate-onlineshop.jp/sphone/products/list.php",
                    "acceptance_rule": "exact match required",
                },
                {
                    "catalog_index": 1072,
                    "name_ko": "duplicate row should be ignored",
                },
            ]
        }

        report = template_builder.build_template(payload, generated_at="2026-07-24T00:00:00Z")

        self.assertEqual(report["summary"]["template_items"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_true"], 0)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["summary"]["focus_pack_ids"], ["source-discovery-focus-001"])
        self.assertEqual(report["automation_policy"]["confirmed_file"], "server/source_discovery_confirmed_rows.json")

        item = report["items"][0]
        self.assertEqual(item["catalog_index"], 1072)
        self.assertEqual(item["field"], "source_url")
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["manual_confirmed_source_url"], "")
        self.assertEqual(item["manual_confirmed_image_url"], "")
        self.assertEqual(item["manual_evidence_url"], "https://www.google.com/search?q=example")


if __name__ == "__main__":
    unittest.main()
