from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_image_enrichment_batch_plan as plan


class BuildImageEnrichmentBatchPlanTests(unittest.TestCase):
    def test_groups_character_rows_into_workstream_and_batches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = root / "seed.json"
            queue = root / "queue.json"
            seed.write_text(
                json.dumps(
                    [
                        {
                            "name_ko": "A acrylic stand alpha",
                            "category": "acrylic stand",
                            "character_name": "Alpha",
                        },
                        {
                            "name_ko": "A acrylic stand beta",
                            "category": "acrylic stand",
                            "character_name": "Beta",
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            queue.write_text(
                json.dumps(
                    {
                        "queue": [
                            {
                                "row_index": 0,
                                "name_ko": "A acrylic stand alpha",
                                "category": "acrylic stand",
                                "affiliation": "Series A",
                                "source_store": "Store A",
                                "strategy": "official_search",
                            },
                            {
                                "row_index": 1,
                                "name_ko": "A acrylic stand beta",
                                "category": "acrylic stand",
                                "affiliation": "Series A",
                                "source_store": "Store A",
                                "strategy": "official_search",
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = plan.build(seed, queue)

        self.assertEqual(payload["missing_images"], 2)
        self.assertEqual(payload["workstream_count"], 1)
        self.assertEqual(payload["workstreams"][0]["missing_images"], 2)
        self.assertEqual(payload["workstreams"][0]["batch_type"], "official_provider_matcher")
        self.assertEqual(payload["workstreams"][0]["image_granularity"], "individual_character_image_required")

    def test_marks_generic_source_as_exact_product_url_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = root / "seed.json"
            queue = root / "queue.json"
            seed.write_text(json.dumps([{"name_ko": "BTS random photo"}]), encoding="utf-8")
            queue.write_text(
                json.dumps(
                    {
                        "queue": [
                            {
                                "row_index": 0,
                                "name_ko": "BTS random photo",
                                "category": "photo card",
                                "affiliation": "BTS",
                                "source_store": "Weverse Shop",
                                "strategy": "source_url_generic_storefront",
                                "source_url": "https://shop.weverse.io/home",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            payload = plan.build(seed, queue)

        self.assertEqual(payload["workstreams"][0]["batch_type"], "exact_product_url_required")
        self.assertIn("exact product URLs", payload["workstreams"][0]["recommended_next_action"])
        self.assertEqual(
            payload["workstreams"][0]["manual_confirmation_template"],
            "server/source_discovery_confirmed_rows.template.json",
        )
        self.assertEqual(
            payload["workstreams"][0]["import_tool"],
            "tools/import_confirmed_source_discovery_rows.py",
        )
        self.assertEqual(
            payload["batches"][0]["unblocks_when"],
            "exact_product_source_url_confirmed",
        )

    def test_routes_exact_detail_extraction_to_image_candidate_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seed = root / "seed.json"
            queue = root / "queue.json"
            seed.write_text(json.dumps([{"name_ko": "Exact item"}]), encoding="utf-8")
            queue.write_text(
                json.dumps(
                    {
                        "queue": [
                            {
                                "row_index": 0,
                                "name_ko": "Exact item",
                                "source_store": "Store A",
                                "strategy": "source_url_product_detail_lookup",
                                "source_url": "https://example.test/product/1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            payload = plan.build(seed, queue)

        self.assertEqual(payload["workstreams"][0]["batch_type"], "exact_detail_image_extraction")
        self.assertEqual(
            payload["workstreams"][0]["manual_confirmation_template"],
            "server/catalog_image_candidate_import_queue.template.json",
        )
        self.assertEqual(payload["workstreams"][0]["import_tool"], "tools/import_manual_image_candidates.py")
        self.assertEqual(payload["items"][0]["unblocks_when"], "same_product_page_image_url_confirmed")


if __name__ == "__main__":
    unittest.main()
