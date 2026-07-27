from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_animation_enrichment_priority_queue as target
from build_animation_enrichment_priority_queue import build, build_image_update_template, write_csv, write_html


class AnimationEnrichmentPriorityQueueTests(unittest.TestCase):
    def test_default_seed_uses_public_catalog(self) -> None:
        self.assertEqual(target.DEFAULT_SEED.name, "catalog_public.json")

    def test_catalog_rows_accepts_public_catalog_object(self) -> None:
        rows = target._catalog_rows({"items": [{"catalog_index": 1}, "skip"]}, Path("catalog.json"))

        self.assertEqual(rows, [{"catalog_index": 1}])

    def test_prioritizes_missing_source_group_and_summarizes_affiliations(self) -> None:
        rows = [
            {
                "source_store": "Animate",
                "category": "figure",
                "affiliation": "Danganronpa",
                "name_ko": "Monokuma figure",
                "name_ja": "モノクマ フィギュア",
                "image_url": "",
                "source_url": "",
            },
            {
                "source_store": "Animate",
                "category": "figure",
                "affiliation": "Danganronpa",
                "name_ko": "Nagito figure",
                "name_ja": "狛枝凪斗 フィギュア",
                "image_url": "",
                "source_url": "",
            },
            {
                "source_store": "Animate",
                "category": "figure",
                "affiliation": "Frieren",
                "name_ko": "Frieren figure",
                "name_ja": "フリーレン フィギュア",
                "image_url": "",
                "source_url": "",
            },
            {
                "source_store": "Other Store",
                "category": "figure",
                "affiliation": "Ignored",
                "name_ko": "Non animation row",
                "image_url": "",
                "source_url": "",
            },
        ]
        audit = {
            "missing_image_by_category": [{"category": "figure", "rows": 3}],
            "missing_source_url_by_category": [{"category": "figure", "rows": 3}],
        }

        payload = build(rows, audit)

        self.assertEqual(payload["animation_rows"], 3)
        self.assertEqual(payload["queue_rows"], 3)
        self.assertEqual(payload["items"][0]["workflow"], "find_exact_source_url")
        self.assertEqual(
            payload["items"][0]["top_affiliations"],
            [
                {"affiliation": "Danganronpa", "rows": 2},
                {"affiliation": "Frieren", "rows": 1},
            ],
        )
        self.assertIn("official_search", payload["items"][0]["sample_items"][0]["links"])

    def test_write_outputs_include_top_affiliations_and_links(self) -> None:
        payload = {
            "animation_rows": 1,
            "queue_groups": 1,
            "queue_rows": 1,
            "missing_image_rows": 1,
            "missing_source_rows": 1,
            "items": [
                {
                    "priority": 1,
                    "workflow": "find_exact_source_url",
                    "category": "figure",
                    "source_store": "Good Smile",
                    "rows": 1,
                    "missing_image_url": 1,
                    "missing_source_url": 1,
                    "top_affiliations": [{"affiliation": "Vocaloid", "rows": 1}],
                    "sample_items": [
                        {
                            "name_ko": "Test figure",
                            "affiliation": "Vocaloid",
                            "sub_series": "HELLO! GOOD SMILE",
                            "links": {"official_search": "https://example.com/search"},
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            html_path = root / "queue.html"
            csv_path = root / "queue.csv"
            write_html(html_path, payload)
            write_csv(csv_path, payload["items"])
            html_text = html_path.read_text(encoding="utf-8")
            csv_text = csv_path.read_text(encoding="utf-8-sig")

        self.assertIn("Vocaloid: 1", html_text)
        self.assertIn("https://example.com/search", html_text)
        self.assertIn("top_affiliations", csv_text)
        self.assertIn("Vocaloid: 1", csv_text)

    def test_build_image_update_template_uses_next_batch_samples(self) -> None:
        payload = {
            "items": [
                {
                    "workflow": "find_exact_source_url",
                    "category": "figure",
                    "source_store": "Good Smile",
                    "sample_items": [
                        {
                            "row_index": 7,
                            "name_ko": "Test figure",
                            "name_ja": "テストフィギュア",
                            "affiliation": "Vocaloid",
                        }
                    ],
                }
            ]
        }

        template = build_image_update_template(payload)

        self.assertEqual(template["schema_version"], 1)
        self.assertEqual(template["agent"]["name"], "animation-enrichment-reviewer")
        self.assertEqual(template["updates"][0]["catalog_index"], 7)
        self.assertEqual(template["updates"][0]["confidence"], "needs_review")
        self.assertEqual(template["updates"][0]["image_url"], "https://example.com/TODO_EXACT_IMAGE_URL")
        self.assertEqual(template["updates"][0]["source_url"], "https://example.com/TODO_EXACT_PRODUCT_DETAIL_URL")
        self.assertEqual(template["updates"][0]["evidence"][0]["type"], "official")
        self.assertIn("Good Smile", template["updates"][0]["notes"])


if __name__ == "__main__":
    unittest.main()
