from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_catalog_field_review_batches as field_batches
from build_catalog_field_review_batches import build_batches


class CatalogFieldReviewBatchTests(unittest.TestCase):
    def test_default_queue_uses_current_field_enrichment_queue(self):
        self.assertEqual(
            field_batches.DEFAULT_QUEUE.name,
            "catalog_field_enrichment_queue_current.json",
        )
        self.assertEqual(
            field_batches.DEFAULT_JSON.name,
            "catalog_field_review_batches_current.json",
        )

    def test_groups_actionable_items_by_store_category_and_field(self):
        payload = build_batches(
            [
                {
                    "field": "source_url",
                    "source_group": "chiikawa_official",
                    "source_store": "치이카와 마켓",
                    "category": "마스코트",
                    "workstream": "chiikawa_official_shop_lookup",
                    "applicability": "actionable",
                    "risk": "medium",
                    "automation_candidate": True,
                    "actionable_now": True,
                    "search_url": "https://example.test/search",
                    "row_index": 1,
                    "name_ko": "A",
                },
                {
                    "field": "source_url",
                    "source_group": "chiikawa_official",
                    "source_store": "치이카와 마켓",
                    "category": "마스코트",
                    "workstream": "chiikawa_official_shop_lookup",
                    "applicability": "actionable",
                    "risk": "medium",
                    "automation_candidate": True,
                    "actionable_now": True,
                    "search_url": "https://example.test/search",
                    "row_index": 2,
                    "name_ko": "B",
                },
            ]
        )

        self.assertEqual(payload["batch_count"], 1)
        self.assertEqual(payload["actionable_rows"], 2)
        batch = payload["batches"][0]
        self.assertEqual(batch["row_count"], 2)
        self.assertEqual(batch["workflow"], "exact_url_or_image_lookup")

    def test_missing_evidence_url_gets_manual_source_discovery_workflow(self):
        payload = build_batches(
            [
                {
                    "field": "source_url",
                    "source_group": "chiikawa_official",
                    "source_store": "치이카와 중국 팝업스토어",
                    "category": "마스코트",
                    "workstream": "chiikawa_official_shop_lookup",
                    "applicability": "actionable",
                    "risk": "medium",
                    "automation_candidate": True,
                    "actionable_now": True,
                    "row_index": 1,
                    "name_ko": "A",
                },
            ]
        )

        self.assertEqual(payload["batches"][0]["workflow"], "manual_source_discovery")
        self.assertEqual(payload["batches"][0]["no_evidence_url_count"], 1)


if __name__ == "__main__":
    unittest.main()
