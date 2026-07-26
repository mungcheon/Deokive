from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_ichiban_variant_lineup_official_probe_public import (
    build_probe,
    extract_item_blocks,
    extract_special_popup_blocks,
)


class BuildIchibanVariantLineupOfficialProbePublicTest(unittest.TestCase):
    def test_extracts_official_item_detail_count_and_choice_policy(self) -> None:
        source = """
        <html><head><title>一番くじ TEST｜一番くじ倶楽部</title></head>
        <body><section>
          <div class="itemColList">
            <h4 class="name sp">H賞 名場面ステッカーアソート</h4>
            <div class="itemColGallery">
              <a href="https://assets.1kuji.com/uploads/product_item/image/1/test.jpg">
                <img src="https://assets.1kuji.com/uploads/product_item/image/1/test.jpg">
              </a>
            </div>
            <p class="detail">名場面を切り取ったステッカーアソートです。<br>■全9種（3枚セット）<br>※選べません</p>
          </div>
        </section></body></html>
        """

        items = extract_item_blocks(source, "https://1kuji.com/products/test")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["official_name"], "H賞 名場面ステッカーアソート")
        self.assertEqual(items[0]["expected_variant_count"], 9)
        self.assertEqual(items[0]["choice_policy"], "blind")

    def test_build_probe_matches_review_row_by_image_url(self) -> None:
        review = {
            "review_rows": [
                {
                    "catalog_index": 10,
                    "source_url": "https://1kuji.com/products/test",
                    "image_url": "https://assets.1kuji.com/uploads/product_item/image/1/test.jpg",
                    "prize_rank": "H賞",
                    "product_name": "名場面ステッカーアソート",
                    "character_name": "기타",
                }
            ]
        }
        source = """
        <html><head><title>一番くじ TEST｜一番くじ倶楽部</title></head>
        <body><section>
          <div class="itemColList">
            <h4 class="name sp">H賞 名場面ステッカーアソート</h4>
            <a href="https://assets.1kuji.com/uploads/product_item/image/1/test.jpg">
              <img src="https://assets.1kuji.com/uploads/product_item/image/1/test.jpg">
            </a>
            <p class="detail">■全9種<br>※選べません</p>
          </div>
        </section></body></html>
        """

        with mock.patch(
            "tools.build_ichiban_variant_lineup_official_probe_public.fetch_page",
            return_value=(source, "https://1kuji.com/products/test"),
        ):
            report = build_probe(review, sleep=0)

        self.assertEqual(report["summary"]["candidate_rows"], 1)
        self.assertEqual(report["summary"]["rows_with_official_expected_variant_count"], 1)
        candidate = report["candidates"][0]
        self.assertEqual(candidate["status"], "matched")
        self.assertEqual(candidate["recommended_action"], "review_before_variant_split")
        self.assertEqual(candidate["expected_variant_count"], 9)
        self.assertEqual(
            candidate["proposed_display_name_ko"],
            "一番くじ TEST / H賞 / 名場面ステッカーアソート / 기타",
        )

    def test_extracts_special_popup_items(self) -> None:
        source = """
        <html><head><title>一番くじ ドラゴンボールDAIMA｜一番くじ倶楽部</title></head>
        <body>
          <li class="prizeSub">
            <a href="#popup_prizeH"><img src="images/lineup/img_h.jpg?v01" alt="H賞 ラバーアソート"></a>
            <div class="popupCol" id="popup_prizeH">
              <div class="popupColInner popupH">
                <div class="popupTitCol">
                  <img src="images/popup/tit_prizeH.png?v01" alt="H賞 ラバーアソート" class="popupTitImg">
                  <h3 class="popupTit">ラバーアソート</h3>
                </div>
                <div class="popupSliderCol">
                  <ul class="swiper-wrapper">
                    <li class="swiper-slide"><img src="images/popup/prizeH_01.jpg?v01" alt="H賞 ラバーアソート"></li>
                    <li class="swiper-slide"><img src="images/popup/prizeH_02.jpg?v01" alt="H賞 ラバーアソート"></li>
                  </ul>
                </div>
                <div class="popupDetailCol">
                  <div class="popupDetailBox">
                    <ul class="popupDetailList">
                      <li class="popupDetailListItem"><span>全4種</span></li>
                      <li class="popupDetailListItem"><span>選べる全4種！</span></li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </li>
        </body></html>
        """

        items = extract_special_popup_blocks(source, "https://sf.1kuji.com/1kuji_db/db_d/")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["official_name"], "H賞 ラバーアソート")
        self.assertEqual(items[0]["expected_variant_count"], 4)
        self.assertEqual(items[0]["choice_policy"], "selectable")
        self.assertTrue(items[0]["official_images"][0].endswith("/images/popup/prizeH_01.jpg?v01"))


if __name__ == "__main__":
    unittest.main()
