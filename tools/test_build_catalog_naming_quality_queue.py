from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_catalog_naming_quality_queue as target


class BuildCatalogNamingQualityQueueTests(unittest.TestCase):
    def test_build_queue_uses_character_and_ichiban_quality_sections(self) -> None:
        quality_report = {
            "character_name_quality": {
                "known_alias_rows": 1,
                "ja_token_mismatch_rows": 1,
                "single_character_name_review_rows": 1,
                "samples": {
                    "known_alias_rows": [
                        {
                            "catalog_index": 1,
                            "name_ko": "Frieren Fern Badge",
                            "character_name": "펀",
                            "expected_character_name": "페른",
                            "reason": "known_alias",
                        }
                    ],
                    "ja_token_mismatch_rows": [
                        {
                            "catalog_index": 2,
                            "name_ja": "フェルン アクリルスタンド",
                            "character_name": "다른표기",
                            "expected_character_name": "페른",
                            "reason": "name_ja_contains_フェルン",
                        }
                    ],
                    "single_character_name_review_rows": [
                        {
                            "catalog_index": 3,
                            "name_ko": "Short Name",
                            "character_name": "나",
                            "reason": "single_character_name_needs_review",
                        }
                    ],
                },
            },
            "ichiban_kuji": {
                "naming_convention_review_rows": 1,
                "naming_convention_review_sample": [
                    {
                        "catalog_index": 4,
                        "name_ko": "Bad Ichiban Name",
                        "character_name": "페른",
                        "reason": "second_part_should_be_prize_rank",
                        "display_parts": ["release", "not rank", "prize", "페른"],
                    }
                ],
            },
        }

        queue = target.build_queue(quality_report)

        self.assertEqual(4, queue["summary"]["queue_rows"])
        self.assertEqual(1, queue["summary"]["known_alias_rows"])
        self.assertEqual(1, queue["summary"]["ja_token_mismatch_rows"])
        self.assertEqual(1, queue["summary"]["single_character_name_review_rows"])
        self.assertEqual(1, queue["summary"]["ichiban_naming_convention_review_rows"])
        self.assertEqual(
            [
                "character_alias_normalization",
                "character_ja_token_mismatch",
                "ichiban_display_name_convention",
                "single_character_name_review",
            ],
            [item["workflow"] for item in queue["items"]],
        )

    def test_write_csv_serializes_display_parts(self) -> None:
        queue = {
            "items": [
                {
                    "workflow": "ichiban_display_name_convention",
                    "priority": 20,
                    "display_parts": ["release", "rank", "prize", "character"],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "queue.csv"
            target.write_csv(queue, path)
            text = path.read_text(encoding="utf-8-sig")

        self.assertIn("release | rank | prize | character", text)


if __name__ == "__main__":
    unittest.main()
