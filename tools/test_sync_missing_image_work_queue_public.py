from __future__ import annotations

import unittest

from tools.sync_missing_image_work_queue_public import sync_queue


class SyncMissingImageWorkQueuePublicTests(unittest.TestCase):
    def test_adds_missing_catalog_rows_to_queue(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "누락 이미지 A",
                    "name_ja": "Missing Image A",
                    "category": "피규어",
                    "affiliation": "작품",
                    "source_store": "FuRyu",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "이미지 있음",
                    "category": "피규어",
                    "affiliation": "작품",
                    "source_store": "FuRyu",
                    "image_url": "https://example.com/image.jpg",
                    "local_image_path": "assets/catalog_images/image.webp",
                },
            ]
        }
        result = sync_queue(catalog, {"items": []})

        self.assertEqual(result["summary"]["catalog_missing_image_rows"], 1)
        self.assertEqual(result["summary"]["added_queue_rows"], 1)
        self.assertTrue(result["summary"]["coverage_matches_catalog_missing_images"])
        item = result["queue"]["items"][0]
        self.assertEqual(item["row_index"], 1)
        self.assertEqual(item["strategy"], "official_search")
        self.assertIn("furyuprize.com/search", item["search_url"])

    def test_keeps_existing_queue_rows_and_removes_non_missing_rows(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "이미지 생김",
                    "category": "키링",
                    "affiliation": "작품",
                    "source_store": "엔스카이",
                    "image_url": "https://example.com/image.jpg",
                    "local_image_path": "assets/catalog_images/image.webp",
                },
                {
                    "catalog_index": 2,
                    "name_ko": "아직 누락",
                    "category": "키링",
                    "affiliation": "작품",
                    "source_store": "엔스카이",
                },
            ]
        }
        queue = {
            "items": [
                {"row_index": 1, "strategy": "official_search", "priority": 10},
                {"row_index": 2, "strategy": "official_search", "priority": 10},
            ]
        }
        result = sync_queue(catalog, queue)

        self.assertEqual(result["summary"]["previous_queue_rows"], 2)
        self.assertEqual(result["summary"]["synced_queue_rows"], 1)
        self.assertEqual(result["summary"]["removed_non_missing_queue_rows"], 1)
        self.assertEqual(result["queue"]["items"][0]["row_index"], 2)

    def test_unknown_store_uses_manual_review_fallback(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 3,
                    "name_ko": "수동 검색 굿즈",
                    "category": "굿즈",
                    "affiliation": "작품",
                    "source_store": "알 수 없는 스토어",
                }
            ]
        }
        result = sync_queue(catalog, {"items": []})

        item = result["queue"]["items"][0]
        self.assertEqual(item["strategy"], "manual_review")
        self.assertEqual(item["automation_safety"], "manual_research_required")
        self.assertIn("google.com/search", item["search_url"])

    def test_refreshes_official_search_url_template(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 4,
                    "name_ko": "치비누이 페른",
                    "name_ja": "ちびぬい フェルン",
                    "category": "인형",
                    "affiliation": "장송의 프리렌",
                    "source_store": "엔스카이",
                }
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 4,
                    "strategy": "official_search",
                    "provider_status": "search_only",
                    "automation_safety": "candidate_provider_script_required",
                    "priority": 10,
                    "query": "ちびぬい フェルン",
                    "search_url": "https://www.enskyshop.com/search?q=old",
                }
            ]
        }
        result = sync_queue(catalog, queue)

        item = result["queue"]["items"][0]
        self.assertIn("www.enskyshop.com/products/list?name=", item["search_url"])
        self.assertNotIn("/search?q=old", item["search_url"])


if __name__ == "__main__":
    unittest.main()
