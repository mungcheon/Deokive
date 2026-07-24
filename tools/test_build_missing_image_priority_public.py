from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_missing_image_priority_public as target


class MissingImagePriorityPublicTests(unittest.TestCase):
    def test_current_missing_image_queue_matches_public_catalog(self) -> None:
        report = target.build_report(
            target.load_json(target.CATALOG),
            target.load_json(target.WORK_QUEUE),
            generated_at="2026-01-01T00:00:00Z",
        )
        summary = report["summary"]
        catalog = target.load_json(target.CATALOG)
        expected_missing = sum(
            1
            for item in catalog.get("items", [])
            if not (item.get("image_url") or item.get("local_image_path"))
        )

        self.assertEqual(summary["missing_image_rows"], expected_missing)
        self.assertEqual(summary["work_queue_rows"], expected_missing)
        self.assertEqual(summary["queue_matched_rows"], expected_missing)
        self.assertEqual(summary["stale_queue_index_matches"], 0)
        self.assertEqual(summary["unmatched_catalog_missing_rows"], 0)
        self.assertIn("safe_existing_image_reuse_candidate_rows", summary)
        self.assertIn("source_discovery_starter_queue_groups", summary)
        self.assertEqual(
            summary["source_discovery_starter_queue_rows"],
            summary["missing_source_url_rows"],
        )
        self.assertIs(summary["auto_apply_enabled"], False)
        self.assertEqual(
            sum(row["rows"] for row in report["breakdowns"]["by_source_url_state"]),
            summary["missing_image_rows"],
        )
        self.assertEqual(
            report["next_action_queues"]["source_discovery_first"]["rows"],
            summary["missing_source_url_rows"],
        )
        self.assertGreater(len(report["focus_groups"]), 0)
        self.assertGreater(len(report["source_discovery_starter_queue"]), 0)
        self.assertGreater(len(report["breakdowns"]["by_source_store"]), 0)
        self.assertTrue(report["automation_policy"]["requires_exact_product_identity"])

        starter_queue_report = target.build_starter_queue_report(
            report,
            generated_at="2026-01-01T00:00:00Z",
        )
        starter_summary = starter_queue_report["summary"]
        self.assertEqual(
            starter_summary["starter_queue_groups"],
            summary["source_discovery_starter_queue_groups"],
        )
        self.assertEqual(
            starter_summary["starter_queue_rows"],
            summary["source_discovery_starter_queue_rows"],
        )
        self.assertTrue(starter_summary["coverage_matches_missing_source_url_rows"])
        self.assertIs(starter_summary["auto_apply_enabled"], False)
        self.assertEqual(
            starter_queue_report["source_report"],
            "data/catalog_missing_image_priority_public.json",
        )
        self.assertGreater(starter_summary["next_review_batch_rows"], 0)
        self.assertGreater(starter_summary["next_review_batch_group_count"], 0)
        self.assertTrue(starter_summary["next_review_batch_primary_source_store"])
        self.assertEqual(
            len(starter_queue_report["next_review_batch"]),
            starter_summary["next_review_batch_rows"],
        )
        self.assertIn(
            "exact official or licensed product/detail page",
            starter_queue_report["next_review_batch"][0]["review_instructions"][1],
        )
        self.assertTrue(
            starter_queue_report["automation_policy"]["requires_exact_product_source_url"]
        )

    def test_build_report_counts_focus_groups_and_priority_samples(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "샘플 A",
                    "image_url": None,
                    "source_store": "FuRyu",
                    "affiliation": "작품",
                    "category": "피규어",
                    "source_url": "https://example.com/product/a",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "샘플 B",
                    "image_url": "https://example.com/b.jpg",
                    "source_store": "FuRyu",
                    "affiliation": "작품",
                    "category": "피규어",
                },
                {
                    "catalog_index": 3,
                    "name_ko": "캐시 이미지",
                    "local_image_path": "assets/catalog_images/cached.webp",
                    "source_store": "FuRyu",
                    "affiliation": "작품",
                    "category": "피규어",
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": "FuRyu",
                    "strategy": "official_search",
                    "automation_safety": "candidate_provider_script_required",
                    "priority": 10,
                    "search_url": "https://example.com/search",
                    "source_url_is_product_detail": True,
                }
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["missing_image_rows"], 1)
        self.assertEqual(report["summary"]["queue_matched_rows"], 1)
        self.assertEqual(report["summary"]["high_priority_rows"], 1)
        self.assertEqual(report["summary"]["product_source_url_rows"], 1)
        self.assertEqual(
            report["breakdowns"]["by_source_url_state"][0],
            {"source_url_state": "product_detail_source_url", "rows": 1},
        )
        self.assertEqual(report["next_action_queues"]["image_attachment_ready"]["rows"], 1)
        self.assertEqual(report["focus_groups"][0]["rows"], 1)
        self.assertEqual(
            report["focus_groups"][0]["recommended_workflow"],
            "official_prize_provider_search_then_exact_detail_match",
        )
        self.assertEqual(report["summary"]["source_discovery_starter_queue_rows"], 0)
        self.assertEqual(report["source_discovery_starter_queue"], [])

        starter_queue_report = target.build_starter_queue_report(
            report,
            generated_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(starter_queue_report["summary"]["starter_queue_groups"], 0)
        self.assertEqual(starter_queue_report["summary"]["starter_queue_rows"], 0)
        self.assertTrue(
            starter_queue_report["summary"]["coverage_matches_missing_source_url_rows"]
        )

    def test_source_discovery_starter_queue_groups_missing_source_rows(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "Hunter Charm A",
                    "name_ja": "HUNTER チャーム A",
                    "source_store": "엔스카이",
                    "affiliation": "헌터X헌터",
                    "category": "키링",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "Hunter Charm B",
                    "name_ja": "HUNTER チャーム B",
                    "source_store": "엔스카이",
                    "affiliation": "헌터X헌터",
                    "category": "키링",
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": "엔스카이",
                    "strategy": "official_search",
                    "priority": 10,
                    "query": "HUNTER チャーム A",
                    "search_url": "https://www.enskyshop.com/search?q=HUNTER",
                },
                {
                    "row_index": 2,
                    "source_store": "엔스카이",
                    "strategy": "official_search",
                    "priority": 10,
                    "query": "HUNTER チャーム B",
                    "search_url": "https://www.enskyshop.com/search?q=HUNTER+B",
                },
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")
        starter_queue = report["source_discovery_starter_queue"]

        self.assertEqual(report["summary"]["source_discovery_starter_queue_groups"], 1)
        self.assertEqual(report["summary"]["source_discovery_starter_queue_rows"], 2)
        self.assertEqual(starter_queue[0]["rows"], 2)
        self.assertEqual(starter_queue[0]["recommended_workflow"], "official_storefront_search_then_exact_detail_match")
        self.assertEqual(starter_queue[0]["first_search_url"], "https://www.enskyshop.com/search?q=HUNTER")
        self.assertEqual(
            starter_queue[0]["search_urls"],
            [
                "https://www.enskyshop.com/search?q=HUNTER",
                "https://www.enskyshop.com/search?q=HUNTER+B",
            ],
        )
        self.assertEqual(starter_queue[0]["search_url_count"], 2)
        self.assertEqual(len(starter_queue[0]["sample_items"]), 2)
        self.assertEqual(starter_queue[0]["sample_items"][0]["search_url"], "https://www.enskyshop.com/search?q=HUNTER")

        starter_queue_report = target.build_starter_queue_report(
            report,
            generated_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(starter_queue_report["summary"]["groups_with_search_urls"], 1)
        self.assertEqual(starter_queue_report["summary"]["groups_with_fallback_web_search_urls"], 0)
        self.assertEqual(starter_queue_report["summary"]["groups_with_any_search_url"], 1)
        self.assertEqual(starter_queue_report["summary"]["next_review_batch_rows"], 2)
        self.assertEqual(starter_queue_report["summary"]["next_review_batch_group_count"], 1)
        self.assertEqual(
            starter_queue_report["summary"]["next_review_batch_primary_source_store"],
            starter_queue[0]["source_store"],
        )
        self.assertEqual(starter_queue_report["next_review_batch"][0]["group_rank"], 1)
        self.assertEqual(starter_queue_report["next_review_batch"][0]["item_rank"], 1)
        self.assertEqual(
            starter_queue_report["next_review_batch"][0]["first_group_search_url"],
            "https://www.enskyshop.com/search?q=HUNTER",
        )

    def test_source_discovery_starter_queue_adds_fallback_web_search_when_no_store_search_url(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "치이카와 중국 한정 마스코트",
                    "name_ja": "ちいかわ 中国限定マスコット",
                    "source_store": "치이카와 중국 팝업스토어",
                    "affiliation": "치이카와",
                    "category": "마스코트",
                }
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": "치이카와 중국 팝업스토어",
                    "strategy": "manual_review",
                    "priority": 50,
                    "query": "ちいかわ 中国限定マスコット",
                }
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")
        starter_group = report["source_discovery_starter_queue"][0]

        self.assertEqual(starter_group["search_urls"], [])
        self.assertIsNone(starter_group["first_search_url"])
        self.assertEqual(starter_group["fallback_web_search_url_count"], 1)
        self.assertIn("google.com/search", starter_group["first_fallback_web_search_url"])
        self.assertIn("%E3%81%A1%E3%81%84%E3%81%8B%E3%82%8F", starter_group["first_fallback_web_search_url"])

        starter_queue_report = target.build_starter_queue_report(
            report,
            generated_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(starter_queue_report["summary"]["groups_with_search_urls"], 0)
        self.assertEqual(starter_queue_report["summary"]["groups_with_fallback_web_search_urls"], 1)
        self.assertEqual(starter_queue_report["summary"]["groups_with_any_search_url"], 1)
        self.assertEqual(starter_queue_report["summary"]["next_review_batch_rows"], 1)
        self.assertIn(
            "google.com/search",
            starter_queue_report["next_review_batch"][0]["first_group_fallback_web_search_url"],
        )

    def test_reports_existing_image_reuse_candidates_for_exact_identity(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "Sample Acrylic",
                    "source_store": "Animate",
                    "affiliation": "Sample Series",
                    "category": "Acrylic Stand",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "Sample Acrylic",
                    "source_store": "Animate",
                    "affiliation": "Sample Series",
                    "category": "Acrylic Stand",
                    "image_url": "https://example.com/sample.webp",
                    "local_image_path": "assets/catalog_images/sample.webp",
                },
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": "Animate",
                    "priority": 10,
                    "source_url_is_product_detail": True,
                }
            ]
        }

        report = target.build_report(catalog, queue, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(report["summary"]["safe_existing_image_reuse_candidate_rows"], 1)
        self.assertEqual(len(report["existing_image_reuse_candidates"]), 1)
        self.assertEqual(
            report["existing_image_reuse_candidates"][0]["candidate_local_image_path"],
            "assets/catalog_images/sample.webp",
        )
        self.assertTrue(report["existing_image_reuse_candidates"][0]["review_required"])


if __name__ == "__main__":
    unittest.main()
