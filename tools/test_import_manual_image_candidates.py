from __future__ import annotations

import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from image_enrichment_safety import is_product_specific_source_url, is_safe_source_image_pair
from import_manual_image_candidates import _load_seed, _write_seed, import_candidates


def _row(**overrides):
    row = {
        "source_store": "Banpresto",
        "name_ko": "Test Prize",
        "name_ja": "Test Prize JP",
        "image_url": "",
        "source_url": "",
    }
    row.update(overrides)
    return row


def _candidate(**overrides):
    item = {
        "row_index": 0,
        "source_url": "https://bsp-prize.jp/item/12345/",
        "image_url": "https://bsp-prize.jp/files_thumbnail/item/test.jpg",
        "confidence": "high",
        "source_kind": "official_manufacturer",
    }
    item.update(overrides)
    return item


class ManualImageCandidateImportTests(unittest.TestCase):
    def test_accepts_safe_official_candidate(self):
        result = import_candidates([_row()], [_candidate()])

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["seed_rows"][0]["image_url"], "https://bsp-prize.jp/files_thumbnail/item/test.jpg")

    def test_load_and_write_preserves_public_catalog_wrapper(self):
        with tempfile.TemporaryDirectory() as raw_tmp:
            path = Path(raw_tmp) / "catalog_public.json"
            path.write_text(
                json.dumps(
                    {
                        "meta": {
                            "schema_version": 1,
                            "row_count": 1,
                            "total_items": 1,
                            "fields": ["catalog_index", "name_ko", "image_url", "source_url"],
                            "missing": {"name_ko": 0, "image_url": 1, "source_url": 1},
                        },
                        "items": [
                            {
                                "catalog_index": 7,
                                "source_store": "Banpresto",
                                "name_ko": "Test Prize",
                                "name_ja": "Test Prize JP",
                                "image_url": "",
                                "source_url": "",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            rows, wrapper = _load_seed(path)
            result = import_candidates(rows, [_candidate()])
            _write_seed(path, result["seed_rows"], wrapper)

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["meta"]["schema_version"], 1)
            self.assertEqual(payload["meta"]["row_count"], 1)
            self.assertEqual(payload["meta"]["total_items"], 1)
            self.assertEqual(payload["meta"]["missing"]["image_url"], 0)
            self.assertEqual(payload["items"][0]["catalog_index"], 7)
            self.assertEqual(payload["items"][0]["image_url"], "https://bsp-prize.jp/files_thumbnail/item/test.jpg")

    def test_rejects_unsupported_source_kind(self):
        result = import_candidates([_row()], [_candidate(source_kind="retailer_candidate")])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "unsupported_source_kind")

    def test_rejects_low_confidence_candidate(self):
        result = import_candidates([_row()], [_candidate(confidence=0.5)])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "confidence_below_threshold")

    def test_require_manual_confirmed_skips_unconfirmed_candidate(self):
        result = import_candidates([_row()], [_candidate(manual_confirmed=False)], require_manual_confirmed=True)

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "manual_confirmed_false")

    def test_require_manual_confirmed_accepts_confirmed_candidate(self):
        result = import_candidates([_row()], [_candidate(manual_confirmed=True)], require_manual_confirmed=True)

        self.assertEqual(len(result["updated"]), 1)

    def test_later_valid_duplicate_can_update_after_first_candidate_rejected(self):
        result = import_candidates(
            [_row()],
            [
                _candidate(confidence=0.5),
                _candidate(
                    source_url="https://bsp-prize.jp/item/67890/",
                    image_url="https://bsp-prize.jp/files_thumbnail/item/better.jpg",
                    confidence="high",
                ),
            ],
        )

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["seed_rows"][0]["source_url"], "https://bsp-prize.jp/item/67890/")

    def test_rejects_generic_or_unknown_source_urls(self):
        result = import_candidates([_row()], [_candidate(source_url="https://example.com/search?q=test")])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "unsafe_source_image_pair")

    def test_rejects_known_store_netloc_mismatch(self):
        result = import_candidates(
            [
                _row(
                    source_store="\ub514\uc988\ub2c8 \uc2a4\ud1a0\uc5b4",
                    name_ko="\ub514\uc988\ub2c8 \ubd09\uc81c \uc778\ud615",
                )
            ],
            [
                _candidate(
                    source_kind="licensed_retailer_exact",
                    source_url="https://www.pokemoncenter-online.com/4904790177286.html",
                    image_url="https://www.pokemoncenter-online.com/a/img/item/4904790177286/M/example.jpg",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "source_netloc_mismatch")

    def test_accepts_licensed_retailer_when_candidate_store_matches_netloc_and_change_allowed(self):
        result = import_candidates(
            [_row(source_store="FuRyu", name_ko="누들 스토퍼 피규어 벚꽃 미쿠 2022", name_ja="ぬーどるストッパーフィギュア 桜ミク 2022")],
            [
                _candidate(
                    source_store="AmiAmi",
                    source_kind="licensed_retailer_exact",
                    source_url="https://www.amiami.jp/top/detail/detail?gcode=FIGURE-138695-R",
                    image_url="https://img.amiami.jp/images/product/thumb300/222/FIGURE-138695.jpg",
                    candidate_title="ぬーどるストッパーフィギュア 桜ミク 2022",
                )
            ],
            allow_source_store_change=True,
        )

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["seed_rows"][0]["source_store"], "AmiAmi")

    def test_accepts_hobby_search_when_candidate_store_matches_netloc_and_change_allowed(self):
        result = import_candidates(
            [_row(source_store="엔스카이", name_ko="장송의 프리렌 펀 우치와", name_ja="葬送のフリーレン フェルン うちわ")],
            [
                _candidate(
                    source_store="Hobby Search",
                    source_kind="licensed_retailer_exact",
                    source_url="https://www.1999.co.jp/11426949",
                    image_url="https://www.1999.co.jp/itbig142/11426949b.jpg",
                    candidate_title="葬送のフリーレン 応援うちわ/フェルン",
                )
            ],
            allow_source_store_change=True,
        )

        self.assertEqual(len(result["updated"]), 1)
        self.assertEqual(result["seed_rows"][0]["source_store"], "Hobby Search")

    def test_rejects_licensed_retailer_store_change_without_explicit_option(self):
        result = import_candidates(
            [_row(source_store="FuRyu", name_ko="누들 스토퍼 피규어 벚꽃 미쿠 2022", name_ja="ぬーどるストッパーフィギュア 桜ミク 2022")],
            [
                _candidate(
                    source_store="AmiAmi",
                    source_kind="licensed_retailer_exact",
                    source_url="https://www.amiami.jp/top/detail/detail?gcode=FIGURE-138695-R",
                    image_url="https://img.amiami.jp/images/product/thumb300/222/FIGURE-138695.jpg",
                    candidate_title="ぬーどるストッパーフィギュア 桜ミク 2022",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "source_store_change_not_enabled")

    def test_rejects_existing_image_conflict_by_default(self):
        result = import_candidates([_row(image_url="https://example.test/existing.jpg")], [_candidate()])

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "existing_image_url_conflict")

    def test_rejects_candidate_title_that_does_not_match_row(self):
        result = import_candidates(
            [_row(name_ko="단간론파 빅 아크릴 스탠드", name_ja="ダンガンロンパ ビッグアクリルスタンド")],
            [_candidate(candidate_title="劇場版チェンソーマン ジグソーパズル")],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "candidate_title_mismatch")

    def test_rejects_title_match_with_only_generic_goods_type_overlap(self):
        result = import_candidates(
            [
                _row(
                    source_store="Stellive Store",
                    name_ko="\ucfe0\ub8e8\ubbf8 \ub178\uc544 \ub370\ube44 \uae30\ub150 \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                    source_url="",
                )
            ],
            [
                _candidate(
                    source_store="Stellive Store",
                    source_kind="official_licensed",
                    source_url="https://fanding.kr/@stellive/shop/1354/",
                    image_url="https://uploads.cdn.fanding.com/upload/image/product_thumbnail/2025/05/16/sample.webp",
                    candidate_title="<\uc2a4\ud154\ub77c\uc774\ube0c \ud074\ub9ac\uc170 1\uc8fc\ub144> \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc (\ub2e8\ud488)",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "candidate_title_mismatch")

    def test_rejects_pop_up_parade_candidate_when_only_line_name_matches(self):
        result = import_candidates(
            [
                _row(
                    source_store="\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
                    name_ko="POP UP PARADE \uce74\uc774\uc800",
                    name_ja="POP UP PARADE \u30df\u30d2\u30e3\u30a8\u30eb\u30fb\u30ab\u30a4\u30b6\u30fc",
                    source_url="",
                )
            ],
            [
                _candidate(
                    source_store="\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
                    source_kind="official_manufacturer_page",
                    source_url="https://www.goodsmile.com/ja/product/10987",
                    image_url="https://www.goodsmile.com/example.jpg",
                    candidate_title="POP UP PARADE \u30ed\u30a4\u30c9\u30fb\u30d5\u30a9\u30fc\u30b8\u30e3\u30fc",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "candidate_title_mismatch")

    def test_rejects_character_only_candidate_title_when_row_has_goods_type(self):
        result = import_candidates(
            [
                _row(
                    source_store="\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
                    name_ko="\uce74\uac00\ubbf8\ub124 \ub9b0 \uba38\uadf8\ucef5",
                    name_ja="\u93e1\u97f3\u30ea\u30f3 \u30de\u30b0\u30ab\u30c3\u30d7",
                    source_url="",
                )
            ],
            [
                _candidate(
                    source_store="\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
                    source_kind="official_manufacturer_page",
                    source_url="https://www.goodsmile.com/ja/product/405",
                    image_url="https://www.goodsmile.com/example.jpg",
                    candidate_title="\u93e1\u97f3\u30ea\u30f3",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "candidate_title_mismatch")

    def test_rejects_candidate_title_with_different_goods_type(self):
        result = import_candidates(
            [
                _row(
                    source_store="\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
                    name_ko="\ud558\uce20\ub124 \ubbf8\ucfe0 \ud074\ub9ac\uc5b4 \ud30c\uc77c A4",
                    name_ja="\u521d\u97f3\u30df\u30af \u30af\u30ea\u30a2\u30d5\u30a1\u30a4\u30ebA4",
                    source_url="",
                )
            ],
            [
                _candidate(
                    source_store="\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
                    source_kind="official_manufacturer_page",
                    source_url="https://www.goodsmile.com/ja/product/60606",
                    image_url="https://www.goodsmile.com/example.jpg",
                    candidate_title="\u306d\u3093\u3069\u308d\u3044\u3069 \u521d\u97f3\u30df\u30af",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "candidate_title_mismatch")

    def test_rejects_korean_near_name_mismatch(self):
        result = import_candidates(
            [
                _row(
                    source_store="Stellive Store",
                    name_ko="\ube44\ube44 \uc544\ud06c\ub9b4 \ud0a4\ub9c1",
                    source_url="",
                )
            ],
            [
                _candidate(
                    source_store="Stellive Store",
                    source_kind="official_licensed",
                    source_url="https://fanding.kr/@stellive/shop/50/",
                    image_url="https://uploads.cdn.fanding.com/upload/image/funding/2023/09/06/sample.webp",
                    candidate_title="2023 \ud0c0\ube44 \uc544\ud06c\ub9b4 \ud0a4\ub9c1",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "candidate_title_mismatch")

    def test_rejects_candidate_when_stored_row_name_no_longer_matches_seed(self):
        result = import_candidates(
            [_row(name_ko="Current Name", name_ja="Current Name JP")],
            [
                _candidate(
                    name_ko="Old Candidate Name",
                    name_ja="Old Candidate Name JP",
                    candidate_title="Current Name",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "candidate_row_name_mismatch")

    def test_accepts_korean_distinctive_name_overlap(self):
        result = import_candidates(
            [
                _row(
                    source_store="Stellive Store",
                    name_ko="\uc544\uce74\ub124 \ub9ac\uc81c \ub370\ube44 \uae30\ub150 \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                    source_url="",
                )
            ],
            [
                _candidate(
                    source_store="Stellive Store",
                    source_kind="official_licensed",
                    source_url="https://fanding.kr/@stellive/shop/55/",
                    image_url="https://uploads.cdn.fanding.com/upload/image/funding/2023/09/27/sample.webp",
                    candidate_title="2023 \ub9ac\uc81c \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                )
            ],
        )

        self.assertEqual(len(result["updated"]), 1)

    def test_rejects_match_with_only_anniversary_and_goods_type_overlap(self):
        result = import_candidates(
            [
                _row(
                    source_store="Stellive Store",
                    name_ko="\ucfe0\ub8e8\ubbf8 \ub178\uc544 \ub370\ube44 1\uc8fc\ub144 \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc",
                    source_url="",
                )
            ],
            [
                _candidate(
                    source_store="Stellive Store",
                    source_kind="official_licensed",
                    source_url="https://fanding.kr/@stellive/shop/1354/",
                    image_url="https://uploads.cdn.fanding.com/upload/image/product_thumbnail/2025/05/16/sample.webp",
                    candidate_title="<\uc2a4\ud154\ub77c\uc774\ube0c \ud074\ub9ac\uc170 1\uc8fc\ub144> \uc544\ud06c\ub9b4 \uc2a4\ud0e0\ub4dc (\ub2e8\ud488)",
                )
            ],
        )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "candidate_title_mismatch")

    def test_require_live_title_exact_rejects_stale_candidate_title(self):
        with patch(
            "import_manual_image_candidates._page_title",
            return_value="ちいかわ マシュマロ風シール /(2)ハチワレおおめセット",
        ):
            result = import_candidates(
                [
                    _row(
                        source_store="\uc5d4\uc2a4\uce74\uc774",
                        name_ko="\uce58\uc774\uce74\uc640 \ub7ec\ubc84 \uc2a4\ud2b8\ub7a9 (\ud558\uce58\uc640\ub808)",
                        name_ja="ちいかわ ラバーストラップ (ハチワレ)",
                    )
                ],
                [
                    _candidate(
                        source_store="\uc5d4\uc2a4\uce74\uc774",
                        source_kind="licensed_retailer_exact",
                        source_url="https://www.enskyshop.com/products/detail/29520",
                        image_url="https://www.enskyshop.com/html/upload/save_image/0827104242_68ae629247650.jpg",
                        candidate_title="ちいかわ ラバーストラップ (ハチワレ)",
                        manual_confirmed=True,
                    )
                ],
                require_live_title_exact=True,
                trust_manual_confirmed_title=True,
            )

        self.assertEqual(result["updated"], [])
        self.assertEqual(result["skipped"][0]["reason"], "live_title_exact_mismatch")

    def test_require_live_title_exact_accepts_current_seed_title(self):
        with patch(
            "import_manual_image_candidates._page_title",
            return_value="ちいかわ ラバーストラップ (ハチワレ) | エンスカイショップ",
        ):
            result = import_candidates(
                [
                    _row(
                        source_store="\uc5d4\uc2a4\uce74\uc774",
                        name_ko="\uce58\uc774\uce74\uc640 \ub7ec\ubc84 \uc2a4\ud2b8\ub7a9 (\ud558\uce58\uc640\ub808)",
                        name_ja="ちいかわ ラバーストラップ (ハチワレ)",
                    )
                ],
                [
                    _candidate(
                        source_store="\uc5d4\uc2a4\uce74\uc774",
                        source_kind="licensed_retailer_exact",
                        source_url="https://www.enskyshop.com/products/detail/29520",
                        image_url="https://www.enskyshop.com/html/upload/save_image/0827104242_68ae629247650.jpg",
                        candidate_title="ちいかわ ラバーストラップ (ハチワレ)",
                    )
                ],
                require_live_title_exact=True,
            )

        self.assertEqual(len(result["updated"]), 1)

    def test_accepts_kana_spelling_variant_in_official_title(self):
        result = import_candidates(
            [
                _row(
                    source_store="FuRyu",
                    name_ko="Noodle Stopper Frieren",
                    name_ja="?????????????? ?????",
                )
            ],
            [
                _candidate(
                    source_store="FuRyu",
                    source_kind="official_anime",
                    source_url="https://frieren-anime.jp/goods/prize/1759/",
                    image_url="https://frieren-anime.jp/wp-content/themes/frieren_2023/assets/img/goods/goodsimages/20240122_80.jpg",
                    candidate_title="?????????????????????",
                )
            ],
        )

        self.assertEqual(len(result["updated"]), 1)

    def test_tracks_known_new_product_detail_patterns(self):
        urls = [
            "https://www.kotobukiya.co.jp/product/detail/p4934054033799/",
            "https://www.goodsmile.info/ja/product/4143/test.html",
            "https://www.taito.co.jp/prize/0478044210",
            "https://www.furyu.jp/news/2026/01/tirol-hatsune_miku/",
            "https://file-origin.charahiroba.com/prize/item/detail?id=15823",
            "https://info.miku.sega.jp/14389",
            "https://blog.piapro.net/2020/10/w201029-2.html",
            "https://blog.piapro.net/2025/07/b2507141.html",
            "https://animota.net/products/animota-e-pre8688",
            "https://bc-onlinestore.com/c/corabo/4970381618711",
            "https://frieren-anime.jp/goods/sundries/728/",
            "https://www.nbcuni.co.jp/anime/danganronpa3/goods/index00810000.html",
            "https://store.jp.square-enix.com/item/ME10681.html",
            "https://eu.store.square-enix-games.com/final-fantasy-xiv-starlight-mug",
            "https://apac.store.square-enix.com/products/final-fantasy-xiv-laptop-case-amaurot",
            "https://anime-store.jp/zh-hant/products/4988601273534",
            "https://anime-store.jp/products/4988601267472-202507",
            "https://www.nin-nin-game.com/en/other-goods/35063-dragon-quest-metallic-monsters-gallery-zoma-goods-.html",
            "https://ninoma.com/products/dragon-quest-metallic-monsters-gallery-zoma-robe-of-darkness-ver",
            "https://jujutsukaisen.jp/goods/goods2893.php",
            "https://one-piece.com/news/76413/index.html",
            "https://www.daiso-sangyo.co.jp/item/24515",
            "https://shop.weverse.io/en/shop/USD/artists/50/sales/14167",
        ]

        self.assertTrue(all(is_product_specific_source_url(url) for url in urls))

    def test_accepts_square_enix_product_images_with_cover_in_filename(self):
        self.assertTrue(
            is_safe_source_image_pair(
                "https://eu.store.square-enix-games.com/final-fantasy-xiv-starlight-cushion-cover",
                "https://cdn11.bigcommerce.com/s-uak4l72xa0/products/3430/images/17403/001_e-STORE_FF14_Starlight_Cushion_cover_20251024__42335.1768344843.386.513.jpg?c=1",
            )
        )

    def test_accepts_piapro_blog_product_images(self):
        self.assertTrue(
            is_safe_source_image_pair(
                "https://blog.piapro.net/2020/10/w201029-2.html",
                "https://blog.piapro.net/wp-content/uploads/2020/10/w201029_img2.jpg",
            )
        )
        self.assertTrue(
            is_safe_source_image_pair(
                "https://blog.piapro.net/2025/07/b2507141.html",
                "https://blog.piapro.net/wp-content/uploads/2025/06/b2507141.jpg",
            )
        )

    def test_accepts_sega_miku_blog_product_images(self):
        self.assertTrue(
            is_safe_source_image_pair(
                "https://info.miku.sega.jp/14389",
                "https://info.miku.sega.jp/wp-content/uploads/2019/04/D101951_001.jpg",
            )
        )

    def test_accepts_official_jujutsu_goods_images(self):
        self.assertTrue(
            is_safe_source_image_pair(
                "https://jujutsukaisen.jp/goods/goods2893.php",
                "https://jujutsukaisen.jp/goods/images/g2893.jpg",
            )
        )


if __name__ == "__main__":
    unittest.main()
