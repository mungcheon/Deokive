from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_public_quality_queue as target


class BuildIchibanPublicQualityQueueTests(unittest.TestCase):
    def test_build_queue_uses_quality_summary_for_action_rows(self) -> None:
        quality_report = {
            "ichiban_kuji": {
                "rows": 4,
                "campaign_count": 2,
                "seeded_campaign_url_count": 1,
                "campaign_gap_count": 1,
                "campaign_gap_urls": [
                    "https://1kuji.com/products/missing",
                    "https://1kuji.com/products/missing-2",
                ],
                "campaign_gap_sample": ["https://1kuji.com/products/sample-only"],
                "exact_display_duplicate_review_groups": 1,
                "exact_display_duplicate_review_rows": 2,
                "exact_display_duplicate_review": [
                    {
                        "display_name": "Same Name",
                        "rows": 2,
                        "source_urls": [
                            "https://1kuji.com/products/a",
                            "https://1kuji.com/products/b",
                        ],
                        "catalog_indexes": [1, 2],
                    }
                ],
                "exact_display_duplicate_review_sample": [],
                "zero_price_exception_rows": 1,
                "zero_price_non_exception_rows": 1,
                "zero_price_non_exception_sample": [
                    {
                        "catalog_index": 4,
                        "name_ko": "Unexpected Zero",
                        "source_url": "https://1kuji.com/products/a",
                    }
                ],
                "naming_convention_review_rows": 2,
                "display_name_convention_review_rows": 1,
                "non_prize_related_item_review_rows": 1,
                "naming_convention_review_sample": [
                    {
                        "catalog_index": 5,
                        "name_ko": "Bad Display",
                        "source_url": "https://1kuji.com/products/a",
                        "reason": "second_part_should_be_prize_rank",
                        "display_parts": ["release", "bad rank", "prize", "character"],
                    },
                    {
                        "catalog_index": 6,
                        "name_ko": "Related Item",
                        "source_url": "https://1kuji.com/products/b",
                        "reason": "non_prize_or_related_item_needs_classification",
                        "display_parts": ["release", "関連商品", "item", "character"],
                    },
                ],
            }
        }

        queue = target.build_queue(quality_report)

        self.assertEqual(6, queue["summary"]["queue_rows"])
        self.assertEqual(2, queue["summary"]["campaign_gap_queue_rows"])
        self.assertEqual(1, queue["summary"]["exact_display_duplicate_queue_rows"])
        self.assertEqual(1, queue["summary"]["zero_price_policy_queue_rows"])
        self.assertEqual(1, queue["summary"]["display_name_convention_review_rows"])
        self.assertEqual(1, queue["summary"]["non_prize_related_item_review_rows"])
        self.assertEqual(2, queue["summary"]["naming_convention_queue_rows"])
        self.assertEqual(6, queue["summary"]["work_pack_rows"])
        self.assertEqual(
            [
                "zero_price_policy_review",
                "campaign_gap_research",
                "campaign_gap_research",
                "exact_display_duplicate_reissue_review",
                "display_name_convention_review",
                "non_prize_related_item_classification",
            ],
            [item["workflow"] for item in queue["items"]],
        )
        self.assertEqual(
            [
                "zero_price_policy_review",
                "campaign_gap_research",
                "campaign_gap_research",
                "exact_display_duplicate_reissue_review",
                "display_name_convention_review",
                "non_prize_related_item_classification",
            ],
            [item["workflow"] for item in queue["work_packs"]],
        )
        self.assertEqual(1, queue["work_packs"][1]["rows"])
        self.assertEqual("missing", queue["work_packs"][1]["group_key"])
        self.assertEqual("missing-2", queue["work_packs"][2]["group_key"])
        self.assertEqual("release / bad rank", queue["work_packs"][4]["group_key"])
        self.assertFalse(queue["automation_policy"]["auto_merge_duplicates"])
        self.assertIn("research_links", queue["items"][1])
        self.assertEqual(
            "possible_reissue_or_separate_campaign",
            queue["items"][3]["duplicate_review_kind"],
        )
        self.assertIn(
            "keep_rows_as_separate_reissues_with_distinguishing_metadata",
            queue["items"][3]["decision_options"],
        )
        self.assertEqual(
            "Ichiban Kuji release name / prize rank / prize name / character name",
            queue["items"][4]["expected_display_format"],
        )
        self.assertFalse(queue["work_packs"][0]["auto_apply_enabled"])
        self.assertIn("acceptance_criteria", queue["work_packs"][0])

    def test_write_html_renders_review_cards_and_links(self) -> None:
        queue = {
            "summary": {
                "ichiban_rows": 2,
                "campaign_gap_queue_rows": 1,
                "exact_display_duplicate_queue_rows": 1,
                "naming_convention_queue_rows": 0,
                "queue_rows": 2,
                "work_pack_rows": 2,
            },
            "items": [
                {
                    "workflow": "campaign_gap_research",
                    "priority": 10,
                    "status": "needs_official_or_archive_evidence",
                    "source_url": "https://1kuji.com/products/sample",
                    "research_links": {
                        "wayback_calendar": "https://web.archive.org/web/*/sample",
                        "domain_search": "https://www.google.com/search?q=sample",
                    },
                    "recommended_action": "Find evidence.",
                    "decision_options": ["add_missing_campaign_rows_only_after_official_or_archive_evidence"],
                    "acceptance_criteria": ["Campaign URL must resolve."],
                },
                {
                    "workflow": "exact_display_duplicate_reissue_review",
                    "priority": 20,
                    "status": "needs_reissue_or_duplicate_decision",
                    "display_name": "Same Prize",
                    "duplicate_review_kind": "possible_reissue_or_separate_campaign",
                    "catalog_indexes": [1, 2],
                    "source_urls": ["https://1kuji.com/products/a", "https://1kuji.com/products/b"],
                    "recommended_action": "Confirm reissue.",
                    "decision_options": ["keep_rows_as_separate_reissues_with_distinguishing_metadata"],
                    "acceptance_criteria": ["Keep both rows only with separate campaigns."],
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "ichiban.html"
            target.write_html(queue, output)
            html = output.read_text(encoding="utf-8")

        self.assertIn("Ichiban Kuji Quality Queue", html)
        self.assertIn("Campaign gaps", html)
        self.assertIn("Same Prize", html)
        self.assertIn("Wayback", html)
        self.assertIn("Source 2", html)


if __name__ == "__main__":
    unittest.main()
