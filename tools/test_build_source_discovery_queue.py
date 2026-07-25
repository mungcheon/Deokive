from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_queue as discovery


class SourceDiscoveryQueueTests(unittest.TestCase):
    def test_default_seed_uses_public_catalog_source_of_truth(self):
        self.assertEqual(discovery.DEFAULT_SEED.name, "catalog_public.json")
        self.assertIn("data", discovery.DEFAULT_SEED.parts)

    def test_build_queue_excludes_rows_with_source_image_or_stale_index(self):
        rows = [
            {"name_ja": "A", "source_store": "애니메이트", "image_url": "", "source_url": ""},
            {"name_ja": "B", "source_store": "엔스카이", "image_url": "https://example.test/b.png", "source_url": ""},
            {"name_ja": "C", "source_store": "굿스마일컴퍼니", "image_url": "", "source_url": "https://example.test/c"},
            {"name_ja": "D", "source_store": "Movic", "image_url": "", "source_url": ""},
        ]

        payload = discovery.build_queue(rows, {3})

        self.assertEqual(payload["summary"]["source_discovery_rows"], 1)
        self.assertEqual(payload["summary"]["stale_excluded_rows"], 1)
        self.assertEqual(payload["items"][0]["row_index"], 0)
        self.assertEqual(payload["items"][0]["workflow"], "official_search_url_available")
        self.assertIn("animate-onlineshop.jp", payload["items"][0]["official_search_url"])
        source_store = payload["items"][0]["source_store"]
        self.assertEqual(
            payload["summary"]["top_store_categories"][0],
            {"source_store": source_store, "category": "", "rows": 1},
        )
        self.assertEqual(
            payload["summary"]["top_official_search_store_categories"][0],
            {"source_store": source_store, "category": "", "rows": 1},
        )

    def test_build_queue_marks_unknown_store_as_manual_research(self):
        rows = [{"name_ko": "Manual Item", "source_store": "Unknown Store"}]

        payload = discovery.build_queue(rows, set())

        self.assertEqual(payload["items"][0]["workflow"], "manual_official_research")
        self.assertIsNone(payload["items"][0]["official_search_url"])
        self.assertIn("google.com/search", payload["items"][0]["web_search_url"])

    def test_build_queue_uses_current_ensky_search_url_for_korean_store_name(self):
        rows = [
            {
                "name_ja": "ちいかわ ラバーストラップ",
                "source_store": "\uc5d4\uc2a4\uce74\uc774",
                "category": "\ud0a4\ub9c1",
                "image_url": "",
                "source_url": "",
            }
        ]

        payload = discovery.build_queue(rows, set())

        search_url = payload["items"][0]["official_search_url"]
        self.assertIn("enskyshop.com/products/list?name=", search_url)
        self.assertNotIn("list.php", search_url)

    def test_build_queue_reuses_localized_animate_query(self):
        rows = [
            {
                "source_store": "애니메이트",
                "affiliation": "강철의 연금술사",
                "category": "아크릴 스탠드",
                "name_ko": "강철의 연금술사 아크릴 스탠드 (알폰스)",
                "name_ja": "",
                "image_url": "",
                "source_url": "",
            }
        ]

        payload = discovery.build_queue(rows, set())

        item = payload["items"][0]
        self.assertEqual(item["query"], "鋼の錬金術師 アクリルスタンド アルフォンス")
        self.assertIn(
            "%E9%8B%BC%E3%81%AE%E9%8C%AC%E9%87%91%E8%A1%93%E5%B8%AB",
            item["official_search_url"],
        )

    def test_build_queue_has_official_search_for_added_public_stores(self):
        rows = [
            {"name_ko": "스텔라이브 콜라보 카페 굿즈", "source_store": "Stellive Store"},
            {"name_ko": "쿠로미 키링", "source_store": "산리오"},
            {"name_ko": "미키 마스코트", "source_store": "디즈니 스토어"},
        ]

        payload = discovery.build_queue(rows, set())
        by_store = {item["source_store"]: item for item in payload["items"]}

        self.assertEqual(
            [item["workflow"] for item in payload["items"]],
            ["official_search_url_available"] * 3,
        )
        self.assertIn("stellive.fanding.kr", by_store["Stellive Store"]["official_search_url"])
        self.assertIn("shop.sanrio.co.jp", by_store["산리오"]["official_search_url"])
        self.assertIn("store.disney.co.jp", by_store["디즈니 스토어"]["official_search_url"])

    def test_build_queue_has_official_search_for_public_store_aliases(self):
        rows = [
            {"name_ko": "(여자)아이들 포토카드", "source_store": "CUBE STORE"},
            {"name_ko": "THE BOYZ 포토카드", "source_store": "IST STORE"},
            {"name_ko": "ATEEZ 포토카드", "source_store": "KQ FELLAZ"},
            {"name_ko": "이세계아이돌 빼빼로", "source_store": "롯데웰푸드"},
            {"name_ko": "주술회전 클리어 파일", "source_store": "점프 숍"},
            {"name_ko": "이세계아이돌 아크릴 디오라마", "source_store": "이세계아이돌 공식 굿즈"},
            {"name_ko": "이세계아이돌 팝업스토어 포토카드", "source_store": "이세계아이돌 팝업스토어"},
            {"name_ko": "치이카와 중국 한정 마스코트", "source_store": "치이카와 중국 팝업스토어"},
            {"name_ko": "치이카와 용산샵 한정 에코백", "source_store": "치이카와샵 용산"},
        ]

        payload = discovery.build_queue(rows, set())
        by_store = {item["source_store"]: item for item in payload["items"]}

        self.assertEqual(
            [item["workflow"] for item in payload["items"]],
            ["official_search_url_available"] * 9,
        )
        self.assertIn("site%3Acubee.co.kr", by_store["CUBE STORE"]["official_search_url"])
        self.assertIn("site%3Ashop.weverse.io", by_store["IST STORE"]["official_search_url"])
        self.assertIn("site%3Akqshop.kr", by_store["KQ FELLAZ"]["official_search_url"])
        self.assertIn("site%3Alottewellfood.com", by_store["롯데웰푸드"]["official_search_url"])
        self.assertIn("jumpcs.shueisha.co.jp", by_store["점프 숍"]["official_search_url"])
        self.assertIn("site%3Awithmuulive.com", by_store["이세계아이돌 공식 굿즈"]["official_search_url"])
        self.assertIn("site%3Awithmuulive.com", by_store["이세계아이돌 팝업스토어"]["official_search_url"])
        self.assertIn("site%3Ax.com%2Fchiikawa_kouhou", by_store["치이카와 중국 팝업스토어"]["official_search_url"])
        self.assertIn("site%3Ax.com%2Fchiikawashop_kr", by_store["치이카와샵 용산"]["official_search_url"])

    def test_build_queue_uses_content_search_for_mixed_svc_rows(self):
        rows = [
            {"name_ko": "쿠루미 노아 콘서트 티셔츠", "source_store": "SVC 공식"},
            {"name_ko": "시라유키 히나 타올", "source_store": "SVC 공식"},
            {"name_ko": "알 수 없는 SVC 굿즈", "source_store": "SVC 공식"},
        ]

        payload = discovery.build_queue(rows, set())

        self.assertEqual(
            [item["workflow"] for item in payload["items"]],
            [
                "official_search_url_available",
                "official_search_url_available",
                "manual_official_research",
            ],
        )
        by_name = {item["name_ko"]: item for item in payload["items"]}
        self.assertIn("store.vspo.jp", by_name["쿠루미 노아 콘서트 티셔츠"]["official_search_url"])
        self.assertIn("site%3Astellive.fanding.kr", by_name["시라유키 히나 타올"]["official_search_url"])
        self.assertIsNone(by_name["알 수 없는 SVC 굿즈"]["official_search_url"])


if __name__ == "__main__":
    unittest.main()
