from __future__ import annotations

import unittest

from tools import sync_missing_image_work_queue_public as target
from tools.sync_missing_image_work_queue_public import sync_queue


class SyncMissingImageWorkQueuePublicTests(unittest.TestCase):
    def test_default_queue_is_local_server_artifact(self) -> None:
        self.assertEqual(
            target.DEFAULT_QUEUE.as_posix().split("/")[-2:],
            ["server", "catalog_missing_image_work_queue_current.json"],
        )
        self.assertEqual(target.DEFAULT_CSV.suffix, ".csv")

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

    def test_korean_store_names_use_official_search_lanes(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 11,
                    "name_ko": "샘플 아크릴 스탠드",
                    "name_ja": "サンプル アクリルスタンド",
                    "category": "아크릴 스탠드",
                    "affiliation": "샘플",
                    "source_store": "애니메이트",
                },
                {
                    "catalog_index": 12,
                    "name_ko": "샘플 키링",
                    "name_ja": "サンプル キーホルダー",
                    "category": "키링",
                    "affiliation": "샘플",
                    "source_store": "엔스카이",
                },
                {
                    "catalog_index": 13,
                    "name_ko": "샘플 피규어",
                    "name_ja": "サンプル フィギュア",
                    "category": "피규어",
                    "affiliation": "샘플",
                    "source_store": "굿스마일컴퍼니",
                },
            ]
        }

        result = sync_queue(catalog, {"items": []})

        by_store = {item["source_store"]: item for item in result["queue"]["items"]}
        self.assertEqual("official_search", by_store["애니메이트"]["strategy"])
        self.assertIn("animate-onlineshop.jp", by_store["애니메이트"]["search_url"])
        self.assertEqual("official_search", by_store["엔스카이"]["strategy"])
        self.assertIn("enskyshop.com", by_store["엔스카이"]["search_url"])
        self.assertEqual("official_search", by_store["굿스마일컴퍼니"]["strategy"])
        self.assertIn("goodsmile.info", by_store["굿스마일컴퍼니"]["search_url"])

    def test_review_only_korean_store_names_use_manual_official_search_lanes(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 21,
                    "name_ko": "샘플 굿즈",
                    "category": "굿즈",
                    "affiliation": "샘플",
                    "source_store": "무기와라스토어",
                },
                {
                    "catalog_index": 22,
                    "name_ko": "샘플 굿즈",
                    "category": "굿즈",
                    "affiliation": "샘플",
                    "source_store": "산리오",
                },
                {
                    "catalog_index": 23,
                    "name_ko": "샘플 굿즈",
                    "category": "굿즈",
                    "affiliation": "샘플",
                    "source_store": "디즈니 스토어",
                },
                {
                    "catalog_index": 24,
                    "name_ko": "샘플 굿즈",
                    "category": "굿즈",
                    "affiliation": "샘플",
                    "source_store": "Bandai Premium",
                },
            ]
        }

        result = sync_queue(catalog, {"items": []})

        for item in result["queue"]["items"]:
            self.assertEqual("manual_official_search_review", item["strategy"])
            self.assertEqual("manual_confirmation_required", item["automation_safety"])
            self.assertNotIn("google.com/search?q=%EC%83%98%ED%94%8C", item["search_url"])

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

    def test_refreshes_stale_query_from_current_catalog_name(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 6,
                    "name_ko": "\uccb4\uc778\uc18c\ub9e8 \ubaa8\uc790\uc774\ud06c \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                    "category": "\uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                    "affiliation": "\uccb4\uc778\uc18c\ub9e8",
                    "source_store": "\uc5d4\uc2a4\uce74\uc774",
                }
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 6,
                    "strategy": "official_search",
                    "provider_status": "search_only",
                    "automation_safety": "candidate_provider_script_required",
                    "priority": 10,
                    "query": "\uccb4\uc778\uc18c \ub9e8 \ubaa8\uc790\uc774\ud06c \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                }
            ]
        }

        result = sync_queue(catalog, queue)

        item = result["queue"]["items"][0]
        self.assertEqual(item["query"], "\uccb4\uc778\uc18c\ub9e8 \ubaa8\uc790\uc774\ud06c \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc")
        self.assertNotIn("%20%EB%A7%A8", item["search_url"])

    def test_promotes_existing_manual_review_when_store_gets_official_search_lane(self) -> None:
        catalog = {
            "items": [
                {
                    "catalog_index": 5,
                    "name_ko": "원피스 피규어",
                    "name_ja": "ONE PIECE フィギュア",
                    "category": "피규어",
                    "affiliation": "원피스",
                    "source_store": "메가하우스",
                }
            ]
        }
        queue = {
            "items": [
                {
                    "row_index": 5,
                    "strategy": "manual_review",
                    "provider_status": "manual_only",
                    "automation_safety": "manual_research_required",
                    "priority": 50,
                    "query": "ONE PIECE フィギュア",
                    "search_url": "https://www.google.com/search?q=old",
                }
            ]
        }

        result = sync_queue(catalog, queue)

        item = result["queue"]["items"][0]
        self.assertEqual(item["strategy"], "manual_official_search_review")
        self.assertEqual(item["provider_status"], "search_only_manual")
        self.assertEqual(item["automation_safety"], "manual_confirmation_required")
        self.assertEqual(item["priority"], 20)
        self.assertIn("megahobby.jp/products/?s=", item["search_url"])


if __name__ == "__main__":
    unittest.main()
