from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.build_reused_image_dedupe_confirmation_template_public import (
    build_template,
    write_markdown,
)


def _review() -> dict:
    return {
        "items": [
            {
                "group_index": 1,
                "confidence": "strong_manual_duplicate_candidate",
                "reason": "online_kuji_same_image_same_character_distinct_names",
                "source_url_same": True,
                "image_same": True,
                "category_same": True,
                "character_same": True,
                "rank_same": True,
                "source_urls": ["https://online-kuji.example/prize"],
                "image_urls": ["https://example.com/prize.jpg"],
                "rows": [
                    {
                        "catalog_index": 10,
                        "name_ko": "D상 마스코트",
                        "name_ja": "D賞 マスコット",
                        "category": "마스코트",
                        "image_url": "https://example.com/prize.jpg",
                        "source_url": "https://online-kuji.example/prize",
                    },
                    {
                        "catalog_index": 20,
                        "name_ko": "D マスコット",
                        "name_ja": "D マスコット",
                        "category": "마스코트",
                        "image_url": "https://example.com/prize.jpg",
                        "source_url": "https://online-kuji.example/prize",
                    },
                ],
                "decision_template": {
                    "manual_confirmed": False,
                    "decision": "",
                    "suggested_keep_catalog_index": 20,
                    "suggested_drop_catalog_indexes": [10],
                    "manual_keep_catalog_index": None,
                    "manual_drop_catalog_indexes": [],
                    "evidence_urls": ["https://online-kuji.example/prize"],
                },
            }
        ]
    }


class BuildReusedImageDedupeConfirmationTemplatePublicTest(unittest.TestCase):
    def test_builds_manual_only_template_with_review_urls(self) -> None:
        report = build_template(_review(), generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["template_groups"], 1)
        self.assertEqual(report["summary"]["strong_candidate_groups"], 1)
        self.assertFalse(report["summary"]["auto_delete_enabled"])
        item = report["items"][0]
        self.assertFalse(item["manual_confirmed"])
        self.assertEqual(item["decision"], "")
        self.assertEqual(item["suggested_keep_catalog_index"], 20)
        self.assertEqual(item["suggested_drop_catalog_indexes"], [10])
        self.assertEqual(item["decision_template"]["manual_confirmed"], False)
        self.assertEqual(item["decision_template"]["decision"], "")
        self.assertEqual(
            item["review_urls"],
            ["https://online-kuji.example/prize", "https://example.com/prize.jpg"],
        )

    def test_write_markdown_lists_top_items(self) -> None:
        report = build_template(_review(), generated_at="2026-01-01T00:00:00Z")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "review.md"
            write_markdown(report, output)
            text = output.read_text(encoding="utf-8")

        self.assertIn("Template groups: 1", text)
        self.assertIn("Suggested keep: 20", text)
        self.assertIn("10: D상 마스코트", text)


if __name__ == "__main__":
    unittest.main()
