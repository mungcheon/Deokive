from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_detail_candidates as detail_candidates


class SourceDetailCandidatesTests(unittest.TestCase):
    def test_cospa_candidates_extracts_detail_title_and_image(self):
        source_html = """
        <div class="item_tn">
          <div class="itembox">
            <a href="https://www.cospa.com/cospa/detail/id/00000147001" title="鬼滅の刃 我妻善逸 マイクロファイバータオル" class="item-tn">
              <img src="https://www.cospa.com/images/items/pc/202607/zenitsu.jpg" class="item-tn" />
            </a>
          </div>
          <h3><a href="https://www.cospa.com/cospa/detail/id/00000147001" title="鬼滅の刃 我妻善逸 マイクロファイバータオル">title</a></h3>
        </div>
        """

        candidates = detail_candidates._cospa_candidates(source_html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_title"], "鬼滅の刃 我妻善逸 マイクロファイバータオル")
        self.assertEqual(candidates[0]["candidate_source_url"], "https://www.cospa.com/cospa/detail/id/00000147001")
        self.assertEqual(candidates[0]["candidate_image_url"], "https://www.cospa.com/images/items/pc/202607/zenitsu.jpg")

    def test_token_score_prefers_exact_overlap(self):
        score, shared = detail_candidates._token_score(
            "鬼滅の刃 我妻善逸 マイクロファイバータオル",
            "鬼滅の刃 我妻善逸 マイクロファイバータオル",
        )

        self.assertEqual(score, 1.0)
        self.assertIn("我妻善逸", shared)

    def test_token_score_ignores_generic_goods_type_only_overlap(self):
        score, shared = detail_candidates._token_score(
            "\u304a\u307e\u3093\u3058\u3085\u3046\u306b\u304e\u306b\u304e\u30de\u30b9\u30b3\u30c3\u30c8 \u30ca\u30ca\u30c1",
            "Thunderbolt Fantasy Project \u304a\u307e\u3093\u3058\u3085\u3046\u306b\u304e\u306b\u304e\u30de\u30b9\u30b3\u30c3\u30c8 \u30da\u30a2",
        )

        self.assertEqual(score, 0.0)
        self.assertEqual(shared, [])

    def test_goods_type_compatibility_rejects_character_only_match(self):
        self.assertFalse(
            detail_candidates._goods_type_compatible(
                "\u837c\u6bd8 \u30e1\u30bf\u30ea\u30c3\u30af\u30e9\u30d0\u30fc\u30b9\u30c8\u30e9\u30c3\u30d7",
                "\u30a2\u30cb\u30e1\u300e\u50d5\u306e\u30d2\u30fc\u30ed\u30fc\u30a2\u30ab\u30c7\u30df\u30a2\u300f \u3061\u307f\u3051\u3082\u307e\u3059\u3053\u3063\u3068 /(5)\u837c\u6bd8",
            )
        )

    def test_ensky_candidates_extracts_detail_title_and_image(self):
        source_html = """
        <div class="tabBox_item clearfix">
          <a href="https://www.enskyshop.com/products/detail/32395">
            <picture>
              <source srcset="/html/upload/save_image/0717130700_6a59aa64a90b4.jpg" media="(min-width:1160px)">
              <img src="" alt="名探偵プリキュア! キラキラトレーディングコレクション2 ガムつき【1BOX 20パック入り】">
            </picture>
          </a>
          <a href="https://www.enskyshop.com/products/detail/32395"><span>名探偵プリキュア! キラキラトレーディングコレクション2 ガムつき【1BOX 20パック入り】</span></a>
        </div>
        """

        candidates = detail_candidates._ensky_candidates(source_html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_source_url"], "https://www.enskyshop.com/products/detail/32395")
        self.assertEqual(candidates[0]["candidate_image_url"], "https://www.enskyshop.com/html/upload/save_image/0717130700_6a59aa64a90b4.jpg")
        self.assertIn("名探偵プリキュア", candidates[0]["candidate_title"])

    def test_animate_candidates_extracts_detail_title_and_image(self):
        source_html = """
        <div class="item_list_class">
          <div class="item_list_thumb"><a href="/pn/%E3%80%90%E3%82%B0%E3%83%83%E3%82%BA-%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%83%9D%E3%83%83%E3%83%97%E3%80%91%E3%83%81%E3%82%A7%E3%83%B3%E3%82%BD%E3%83%BC%E3%83%9E%E3%83%B3+%E3%82%A2%E3%82%AF%E3%83%AA%E3%83%AB%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89+%E3%83%91%E3%83%AF%E3%83%BC/pd/3167771/"><img src="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550432284210_1_1750997103.jpg&amp;width=400&amp;height=400&square=1" width="178" height="178" title='【グッズ-スタンドポップ】チェンソーマン アクリルスタンド パワー' /></a></div>
          <h3><a href="/pn/%E3%80%90%E3%82%B0%E3%83%83%E3%82%BA-%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%83%9D%E3%83%83%E3%83%97%E3%80%91%E3%83%81%E3%82%A7%E3%83%B3%E3%82%BD%E3%83%BC%E3%83%9E%E3%83%B3+%E3%82%A2%E3%82%AF%E3%83%AA%E3%83%AB%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89+%E3%83%91%E3%83%AF%E3%83%BC/pd/3167771/" title='【グッズ-スタンドポップ】チェンソーマン アクリルスタンド パワー'>【グッズ-スタンドポップ】チェンソーマン アクリルスタンド パワー</a></h3>
        </div>
        """

        candidates = detail_candidates._animate_candidates(source_html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]["candidate_source_url"],
            "https://www.animate-onlineshop.jp/pn/%E3%80%90%E3%82%B0%E3%83%83%E3%82%BA-%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89%E3%83%9D%E3%83%83%E3%83%97%E3%80%91%E3%83%81%E3%82%A7%E3%83%B3%E3%82%BD%E3%83%BC%E3%83%9E%E3%83%B3+%E3%82%A2%E3%82%AF%E3%83%AA%E3%83%AB%E3%82%B9%E3%82%BF%E3%83%B3%E3%83%89+%E3%83%91%E3%83%AF%E3%83%BC/pd/3167771/",
        )
        self.assertEqual(
            candidates[0]["candidate_image_url"],
            "https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550432284210_1_1750997103.jpg&width=400&height=400&square=1",
        )
        self.assertEqual(candidates[0]["candidate_title"], "【グッズ-スタンドポップ】チェンソーマン アクリルスタンド パワー")

    def test_goodsmile_info_candidates_extracts_detail_title_and_image(self):
        source_html = """
        <div class="hitItem">
          <div class="hitBox">
            <a href="/ja/product/11254/">
              <img data-original="//images.goodsmile.info/cgm/images/product/20210524/11254/85060/thumb/monokuma.jpg" class="itemImg" alt="" />
              <span class="hitTtl"><span>POP UP PARADE モノクマ</span></span>
            </a>
          </div>
        </div>
        """

        candidates = detail_candidates._goodsmile_info_candidates(source_html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_source_url"], "https://www.goodsmile.info/ja/product/11254/")
        self.assertEqual(
            candidates[0]["candidate_image_url"],
            "https://images.goodsmile.info/cgm/images/product/20210524/11254/85060/thumb/monokuma.jpg",
        )
        self.assertEqual(candidates[0]["candidate_title"], "POP UP PARADE モノクマ")

    def test_furyu_candidates_extracts_api_detail_title_and_image(self):
        original_fetch_json = detail_candidates._fetch_json

        def payload(_url: str) -> dict:
            return {
                "items": [
                    {
                        "code": "12345",
                        "name_item": "ちょこのせプレミアムフィギュア 爆豪勝己",
                        "img_item_main": "/item/sample.jpg",
                    }
                ]
            }

        try:
            detail_candidates._fetch_json = payload
            candidates = detail_candidates._furyu_candidates("ちょこのせプレミアムフィギュア 爆豪勝己")
        finally:
            detail_candidates._fetch_json = original_fetch_json

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_source_url"], "https://furyuprize.com/item/12345")
        self.assertEqual(candidates[0]["candidate_image_url"], "https://furyuprize.com/files/images/item/sample.jpg")
        self.assertEqual(candidates[0]["candidate_title"], "ちょこのせプレミアムフィギュア 爆豪勝己")

    def test_taito_candidates_extracts_api_detail_title_and_image(self):
        original_fetch_taito_json = detail_candidates._fetch_taito_json

        def payload(_url: str) -> dict:
            return {
                "data": {
                    "ProductList": [
                        {
                            "ProductID": "98765",
                            "ProductName": "Desktop Cuteフィギュア トガヒミコ",
                            "ImagePath": "/Content/images/prize/",
                            "ImageName01": "toga.jpg",
                        }
                    ]
                }
            }

        try:
            detail_candidates._fetch_taito_json = payload
            candidates = detail_candidates._taito_candidates("Desktop Cuteフィギュア トガヒミコ")
        finally:
            detail_candidates._fetch_taito_json = original_fetch_taito_json

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_source_url"], "https://www.taito.co.jp/prize/item/98765")
        self.assertEqual(candidates[0]["candidate_image_url"], "https://www.taito.co.jp/Content/images/prize/toga.jpg")
        self.assertEqual(candidates[0]["candidate_title"], "Desktop Cuteフィギュア トガヒミコ")

    def test_rement_candidates_extracts_detail_title_and_image(self):
        source_html = """
        <a href="r12345/">
          <img data-original="https://www.re-ment.co.jp/product/images/r12345/main.jpg">
          <p class="name">リーメント SPY×FAMILY デスクコレクション</p>
        </a>
        """

        candidates = detail_candidates._rement_candidates(source_html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_source_url"], "https://www.re-ment.co.jp/product/r12345/")
        self.assertEqual(candidates[0]["candidate_image_url"], "https://www.re-ment.co.jp/product/images/r12345/main.jpg")
        self.assertEqual(candidates[0]["candidate_title"], "リーメント SPY×FAMILY デスクコレクション")

    def test_rement_catalog_candidates_fetches_once(self):
        original_fetch = detail_candidates._fetch_text
        original_cache = detail_candidates._REMENT_CATALOG_CACHE
        calls = []

        def page(url: str) -> str:
            calls.append(url)
            return """
            <a href="r12345/">
              <img data-original="https://www.re-ment.co.jp/product/images/r12345/main.jpg">
              <p class="name">リーメント SPY×FAMILY デスクコレクション</p>
            </a>
            """

        try:
            detail_candidates._REMENT_CATALOG_CACHE = None
            detail_candidates._fetch_text = page
            first = detail_candidates._rement_catalog_candidates()
            second = detail_candidates._rement_catalog_candidates()
        finally:
            detail_candidates._fetch_text = original_fetch
            detail_candidates._REMENT_CATALOG_CACHE = original_cache

        self.assertEqual(len(first), 1)
        self.assertEqual(second, first)
        self.assertEqual(calls, [detail_candidates.REMENT_CATALOG_URL])

    def test_amiami_candidates_extracts_detail_title_and_image(self):
        source_html = """
        <div class="product_box">
          <a href="https://www.amiami.jp/top/detail/detail?gcode=GOODS-1-R">
            <img data-src="https://img.amiami.jp/images/product/thumb80/001/GOODS-1.jpg">
            <div class="product_name_inner">鬼滅の刃 イラストカードコレクション 冨岡</div>
          </a>
        </div>
        """

        candidates = detail_candidates._amiami_candidates(source_html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_source_url"], "https://www.amiami.jp/top/detail/detail?gcode=GOODS-1-R")
        self.assertEqual(candidates[0]["candidate_image_url"], "https://img.amiami.jp/images/product/thumb300/001/GOODS-1.jpg")
        self.assertEqual(candidates[0]["candidate_title"], "鬼滅の刃 イラストカードコレクション 冨岡")

    def test_goods_search_candidates_extracts_detail_title_and_image(self):
        source_html = """
        <li class="block-goods">
          <a href="/shop/g/g02330-00350-00630/">
            <img src="/client_info/MOVIC/itemimage/02330-00350-00630.jpg" alt="HUNTER×HUNTER ぬいぐるみ ヒソカ">
          </a>
        </li>
        """

        candidates = detail_candidates._goods_search_candidates(source_html, "https://www.movic.jp")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_source_url"], "https://www.movic.jp/shop/g/g02330-00350-00630/")
        self.assertEqual(
            candidates[0]["candidate_image_url"],
            "https://www.movic.jp/client_info/MOVIC/itemimage/02330-00350-00630.jpg",
        )
        self.assertEqual(candidates[0]["candidate_title"], "HUNTER×HUNTER ぬいぐるみ ヒソカ")

    def test_build_candidates_keeps_multiple_high_score_matches_in_review(self):
        original_fetch = detail_candidates._fetch_text
        source_html = """
        <div class="item_list_class">
          <div class="item_list_thumb"><a href="/pn/a/pd/1/"><img src="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=a.jpg" title='【グッズ-クリアファイル】オーバーロード クリアファイル パープル' /></a></div>
          <h3><a href="/pn/a/pd/1/" title='【グッズ-クリアファイル】オーバーロード クリアファイル パープル'>【グッズ-クリアファイル】オーバーロード クリアファイル パープル</a></h3>
        </div>
        <div class="item_list_class">
          <div class="item_list_thumb"><a href="/pn/b/pd/2/"><img src="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=b.jpg" title='【グッズ-クリアファイル】オーバーロード クリアファイル ブラック' /></a></div>
          <h3><a href="/pn/b/pd/2/" title='【グッズ-クリアファイル】オーバーロード クリアファイル ブラック'>【グッズ-クリアファイル】オーバーロード クリアファイル ブラック</a></h3>
        </div>
        """

        def page(_url: str) -> str:
            return source_html

        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": "\uc560\ub2c8\uba54\uc774\ud2b8",
                    "query": "オーバーロード クリアファイル",
                    "official_search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=test",
                }
            ]
        }
        try:
            detail_candidates._fetch_text = page
            payload = detail_candidates.build_candidates(queue, source_store="\uc560\ub2c8\uba54\uc774\ud2b8")
        finally:
            detail_candidates._fetch_text = original_fetch

        self.assertEqual(payload["results"][0]["status"], "candidate_review_needed")
        self.assertEqual(payload["summary"]["exact_candidate_rows"], 0)
        self.assertEqual(payload["summary"]["candidate_review_rows"], 1)

    def test_build_candidates_uses_focus_pack_search_query(self):
        original_fetch = detail_candidates._fetch_text
        source_html = """
        <div class="item_list_class">
          <div class="item_list_thumb"><a href="/pn/oshi-ai-acrylic-stand/pd/1/"><img src="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=ai.jpg" title='oshi ai acrylic stand' /></a></div>
          <h3><a href="/pn/oshi-ai-acrylic-stand/pd/1/" title='oshi ai acrylic stand'>oshi ai acrylic stand</a></h3>
        </div>
        """

        def page(_url: str) -> str:
            return source_html

        queue = {
            "items": [
                {
                    "row_index": 1072,
                    "source_store": "\uc560\ub2c8\uba54\uc774\ud2b8",
                    "search_query": "oshi ai acrylic stand",
                    "official_search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=oshi",
                }
            ]
        }
        try:
            detail_candidates._fetch_text = page
            payload = detail_candidates.build_candidates(queue, source_store="\uc560\ub2c8\uba54\uc774\ud2b8")
        finally:
            detail_candidates._fetch_text = original_fetch

        self.assertEqual(payload["results"][0]["query"], "oshi ai acrylic stand")
        self.assertEqual(payload["results"][0]["status"], "exact_candidate_available")
        self.assertEqual(payload["summary"]["exact_candidate_rows"], 1)

    def test_build_candidates_rejects_line_only_pop_up_parade_match(self):
        original_fetch = detail_candidates._fetch_text
        source_html = """
        <div class="hitItem">
          <div class="hitBox">
            <a href="/ja/product/11254/POP+UP+PARADE+%E6%B1%9F%E3%83%8E%E5%B3%B6%E7%9B%BE%E5%AD%90.html">
              <img data-original="https://images.goodsmile.info/cgm/images/product/20210524/11254/85060/thumb/junko.jpg" class="itemImg">
              <span class="hitTtl"><span>POP UP PARADE 江ノ島盾子</span></span>
            </a>
          </div>
        </div>
        """

        def page(_url: str) -> str:
            return source_html

        queue = {
            "items": [
                {
                    "row_index": 1455,
                    "source_store": "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
                    "query": "POP UP PARADE \u30e2\u30ce\u30af\u30de",
                    "official_search_url": "https://www.goodsmile.info/ja/products/search?search%5Bquery%5D=test",
                }
            ]
        }
        try:
            detail_candidates._fetch_text = page
            payload = detail_candidates.build_candidates(queue, source_store="\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8")
        finally:
            detail_candidates._fetch_text = original_fetch

        self.assertEqual(payload["results"][0]["status"], "no_relevant_candidates")
        self.assertEqual(payload["summary"]["candidate_review_rows"], 0)

    def test_build_candidates_stops_after_consecutive_rate_limits(self):
        original_fetch = detail_candidates._fetch_text

        def rate_limited(_url: str) -> str:
            raise detail_candidates.RateLimitError("HTTP Error 429: Too Many Requests")

        queue = {
            "items": [
                {
                    "row_index": index,
                    "source_store": "\uc5d4\uc2a4\uce74\uc774",
                    "query": "query",
                    "official_search_url": f"https://www.enskyshop.com/products/list.php?mode=search&smt={index}",
                }
                for index in range(5)
            ]
        }
        try:
            detail_candidates._fetch_text = rate_limited
            payload = detail_candidates.build_candidates(
                queue,
                source_store="\uc5d4\uc2a4\uce74\uc774",
                max_consecutive_rate_limits=2,
            )
        finally:
            detail_candidates._fetch_text = original_fetch

        self.assertTrue(payload["summary"]["rate_limit_stopped"])
        self.assertEqual(payload["summary"]["failure_count"], 2)
        self.assertEqual(payload["summary"]["rate_limit_failures"], 2)
        self.assertEqual(payload["summary"]["result_rows"], 0)

    def test_build_candidates_can_resume_from_start_index(self):
        original_fetch = detail_candidates._fetch_text

        def empty_page(_url: str) -> str:
            return ""

        queue = {
            "items": [
                {
                    "row_index": index,
                    "source_store": "Cospa",
                    "query": f"query {index}",
                    "official_search_url": f"https://www.cospa.com/cospa/itemlist/keyword/{index}",
                }
                for index in range(5)
            ]
        }
        try:
            detail_candidates._fetch_text = empty_page
            payload = detail_candidates.build_candidates(queue, source_store="Cospa", start_index=2, max_rows=2)
        finally:
            detail_candidates._fetch_text = original_fetch

        self.assertEqual(payload["summary"]["start_index"], 2)
        self.assertEqual(payload["summary"]["scanned_rows"], 2)
        self.assertEqual(payload["summary"]["processed_rows"], 2)
        self.assertEqual([item["row_index"] for item in payload["results"]], [2, 3])

    def test_build_candidates_stops_on_time_budget(self):
        original_fetch = detail_candidates._fetch_text
        calls = []

        def empty_page(url: str) -> str:
            calls.append(url)
            return ""

        queue = {
            "items": [
                {
                    "row_index": index,
                    "source_store": "Cospa",
                    "query": f"query {index}",
                    "official_search_url": f"https://www.cospa.com/cospa/itemlist/keyword/{index}",
                }
                for index in range(5)
            ]
        }
        try:
            detail_candidates._fetch_text = empty_page
            payload = detail_candidates.build_candidates(
                queue,
                source_store="Cospa",
                sleep_seconds=0.02,
                time_budget_seconds=0.01,
            )
        finally:
            detail_candidates._fetch_text = original_fetch

        self.assertTrue(payload["summary"]["time_budget_exhausted"])
        self.assertEqual(payload["summary"]["result_rows"], 1)
        self.assertEqual(payload["summary"]["processed_rows"], 1)
        self.assertEqual(len(calls), 1)

    def test_build_candidates_without_store_scans_supported_provider_stores_only(self):
        original_fetch = detail_candidates._fetch_text
        original_fetch_json = detail_candidates._fetch_json
        original_fetch_taito_json = detail_candidates._fetch_taito_json

        def empty_page(_url: str) -> str:
            return ""

        queue = {
            "items": [
                {
                    "row_index": 1,
                    "source_store": "Cospa",
                    "query": "cospa",
                    "official_search_url": "https://www.cospa.com/cospa/itemlist/keyword/cospa",
                },
                {
                    "row_index": 2,
                    "source_store": "\uc5d4\uc2a4\uce74\uc774",
                    "query": "ensky",
                    "official_search_url": "https://www.enskyshop.com/products/list.php?mode=search&smt=ensky",
                },
                {
                    "row_index": 3,
                    "source_store": "\uc560\ub2c8\uba54\uc774\ud2b8",
                    "query": "animate",
                    "official_search_url": "https://www.animate-onlineshop.jp/products/list.php?mode=search&smt=animate",
                },
                {
                    "row_index": 4,
                    "source_store": "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
                    "query": "goodsmile",
                    "official_search_url": "https://www.goodsmile.info/ja/products/search?search%5Bquery%5D=goodsmile",
                },
                {
                    "row_index": 5,
                    "source_store": "FuRyu",
                    "query": "furyu",
                    "official_search_url": "https://furyuprize.com/search?keyword=furyu",
                },
                {
                    "row_index": 6,
                    "source_store": "Taito",
                    "query": "taito",
                    "official_search_url": "https://www.taito.co.jp/prize?keyword=taito",
                },
                {
                    "row_index": 7,
                    "source_store": "Re-ment",
                    "query": "rement",
                    "official_search_url": "https://www.re-ment.co.jp/?s=rement",
                },
                {
                    "row_index": 8,
                    "source_store": "AmiAmi",
                    "query": "amiami",
                    "official_search_url": "https://www.amiami.jp/top/search/list?s_keywords=amiami",
                },
                {
                    "row_index": 9,
                    "source_store": "Movic",
                    "query": "movic",
                    "official_search_url": "https://www.movic.jp/shop/goods/search.aspx?search=x&keyword=movic",
                },
                {
                    "row_index": 10,
                    "source_store": "\ucf54\ud1a0\ubd80\ud0a4\uc57c",
                    "query": "kotobukiya",
                    "official_search_url": "https://shop.kotobukiya.co.jp/shop/goods/search.aspx?search=x&keyword=kotobukiya",
                },
                {
                    "row_index": 11,
                    "source_store": "Unsupported",
                    "query": "unsupported",
                    "official_search_url": "https://example.test/search",
                },
            ]
        }
        try:
            detail_candidates._fetch_text = empty_page
            detail_candidates._fetch_json = lambda _url: {}
            detail_candidates._fetch_taito_json = lambda _url: {}
            payload = detail_candidates.build_candidates(queue, source_store=None)
        finally:
            detail_candidates._fetch_text = original_fetch
            detail_candidates._fetch_json = original_fetch_json
            detail_candidates._fetch_taito_json = original_fetch_taito_json

        self.assertEqual(payload["summary"]["scanned_rows"], 10)
        self.assertEqual(payload["summary"]["processed_rows"], 10)
        self.assertEqual(payload["summary"]["source_queue_rows"], 11)
        self.assertEqual(payload["summary"]["supported_provider_rows"], 10)
        self.assertEqual(payload["summary"]["unsupported_provider_rows"], 1)
        self.assertEqual(
            payload["summary"]["top_unsupported_provider_stores"],
            [{"source_store": "Unsupported", "rows": 1}],
        )
        self.assertEqual(payload["summary"]["result_rows"], 10)
        self.assertEqual([item["row_index"] for item in payload["results"]], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    def test_build_candidates_marks_movic_waiting_room_as_temporary_failure(self):
        original_fetch = detail_candidates._fetch_text

        def waiting_room(_url: str) -> str:
            return """
            <html>
              <title>ただいま大変混みあっております ｜ムービック（movic）</title>
              <body>待ち人数：<span>確認中</span> 想定待ち時間：<span>確認中</span></body>
            </html>
            """

        queue = {
            "items": [
                {
                    "row_index": 1730,
                    "source_store": "Movic",
                    "query": "鬼滅の刃 BIG缶バッジ 炭治郎",
                    "official_search_url": "https://www.movic.jp/shop/goods/search.aspx?keyword=test",
                }
            ]
        }
        try:
            detail_candidates._fetch_text = waiting_room
            payload = detail_candidates.build_candidates(queue, source_store="Movic")
        finally:
            detail_candidates._fetch_text = original_fetch

        self.assertEqual(payload["summary"]["result_rows"], 0)
        self.assertEqual(payload["summary"]["failure_count"], 1)
        self.assertEqual(payload["summary"]["provider_temporary_unavailable_failures"], 1)
        self.assertTrue(payload["failures"][0]["provider_temporary_unavailable"])

    def test_taito_candidates_initializes_session_before_api_request(self):
        class FakeResponse:
            def __init__(self, payload=None):
                self.status_code = 200
                self._payload = payload or {}

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        class FakeSession:
            def __init__(self):
                self.headers = {}
                self.calls = []

            def get(self, url, timeout, headers=None):
                self.calls.append((url, headers))
                if url == "https://www.taito.co.jp/prize":
                    return FakeResponse()
                return FakeResponse(
                    {
                        "ProductList": [
                            {
                                "ProductID": "000001",
                                "ProductName": "Taito Prize Miku Figure",
                                "ImagePath": "/prize/",
                                "ImageName01": "miku.jpg",
                            }
                        ]
                    }
                )

        fake_session = FakeSession()
        original_session = detail_candidates._TAITO_SESSION
        try:
            detail_candidates._TAITO_SESSION = None
            with mock.patch.object(detail_candidates.requests, "Session", return_value=fake_session):
                candidates = detail_candidates._taito_candidates("miku")
        finally:
            detail_candidates._TAITO_SESSION = original_session

        self.assertEqual(fake_session.calls[0][0], "https://www.taito.co.jp/prize")
        self.assertIn("api/Prize", fake_session.calls[1][0])
        self.assertEqual(fake_session.calls[1][1]["X-Requested-With"], "XMLHttpRequest")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["candidate_source_url"], "https://www.taito.co.jp/prize/item/000001")

    def test_cli_forwards_sleep_seconds(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with mock.patch.object(
                detail_candidates,
                "build_candidates",
                return_value={
                    "summary": {
                        "source_queue_rows": 0,
                        "supported_provider_rows": 0,
                        "unsupported_provider_rows": 0,
                        "top_unsupported_provider_stores": [],
                        "scanned_rows": 0,
                        "exact_candidate_rows": 0,
                        "candidate_review_rows": 0,
                        "failure_count": 0,
                        "status_counts": [],
                    },
                    "results": [],
                    "failures": [],
                },
            ) as build_mock:
                with mock.patch.object(
                    sys,
                    "argv",
                    [
                        "build_source_detail_candidates.py",
                        "--queue",
                        "server/catalog_source_discovery_queue.json",
                        "--json-output",
                        str(tmp_path / "source_detail_candidates.json"),
                        "--markdown-output",
                        str(tmp_path / "source_detail_candidates.md"),
                        "--sleep-seconds",
                        "0.5",
                        "--max-consecutive-rate-limits",
                        "4",
                    ],
                ):
                    detail_candidates.main()

        self.assertEqual(build_mock.call_args.kwargs["sleep_seconds"], 0.5)
        self.assertEqual(build_mock.call_args.kwargs["max_consecutive_rate_limits"], 4)


if __name__ == "__main__":
    unittest.main()
