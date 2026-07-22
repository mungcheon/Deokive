from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_auto_promotable_image_candidates import build_candidates


def _seed_row(**overrides):
    row = {
        "name_ko": "오버로드 트레이딩 캔뱃지",
        "name_ja": "オーバーロード トレーディング缶バッジ",
        "affiliation": "오버로드",
        "image_url": "",
    }
    row.update(overrides)
    return row


def _unresolved(**overrides):
    item = {
        "row_index": 0,
        "name_ko": "오버로드 트레이딩 캔뱃지",
        "query": "オーバーロード トレーディング缶バッジ",
        "source_store": "애니메이트",
        "reason": "best_candidate_rejected",
        "top_candidates": [
            {
                "title": "【グッズ-バッチ】オーバーロード トレーディング缶バッジ",
                "source_url": "https://www.animate-onlineshop.jp/pn/test/pd/2895287/",
                "image_url": "https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550451238683_2_1718273107.jpg&width=400&height=400&square=1",
            }
        ],
    }
    item.update(overrides)
    return item


class BuildAutoPromotableImageCandidatesTests(unittest.TestCase):
    def test_promotes_safe_title_subsuming_top_candidate(self) -> None:
        payload = build_candidates(
            [Path("report.json")],
            [_seed_row()],
        )
        self.assertEqual(payload["items"], [])

        report_payload = {"unresolved": [_unresolved()]}
        original_read_report = __import__("build_auto_promotable_image_candidates")._read_report
        try:
            __import__("build_auto_promotable_image_candidates")._read_report = lambda _path: report_payload
            payload = build_candidates([Path("report.json")], [_seed_row()])
        finally:
            __import__("build_auto_promotable_image_candidates")._read_report = original_read_report

        self.assertEqual(payload["summary"]["candidate_items"], 1)
        self.assertEqual(payload["items"][0]["confidence"], 0.92)
        self.assertTrue(payload["items"][0]["manual_confirmed"])

    def test_skips_rows_that_already_have_images(self) -> None:
        report_payload = {"unresolved": [_unresolved()]}
        module = __import__("build_auto_promotable_image_candidates")
        original_read_report = module._read_report
        try:
            module._read_report = lambda _path: report_payload
            payload = build_candidates([Path("report.json")], [_seed_row(image_url="https://example.test/existing.jpg")])
        finally:
            module._read_report = original_read_report

        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["skipped_sample"][0]["reason"], "already_has_image")

    def test_skips_stale_row_index_when_candidate_name_differs_from_current_seed(self) -> None:
        report_payload = {
            "unresolved": [
                _unresolved(
                    name_ko="stale candidate row",
                    name_ja="stale candidate row ja",
                    query="stale candidate query",
                )
            ]
        }
        module = __import__("build_auto_promotable_image_candidates")
        original_read_report = module._read_report
        try:
            module._read_report = lambda _path: report_payload
            payload = build_candidates([Path("report.json")], [_seed_row()])
        finally:
            module._read_report = original_read_report

        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["summary"]["candidate_items"], 0)
        self.assertEqual(payload["skipped_sample"][0]["reason"], "candidate_row_name_mismatch")
        self.assertEqual(payload["skipped_sample"][0]["candidate_name_ko"], "stale candidate row")

    def test_rejects_generic_or_non_product_candidates(self) -> None:
        report_payload = {
            "unresolved": [
                _unresolved(
                    top_candidates=[
                        {
                            "title": "オーバーロード トレーディング缶バッジ",
                            "source_url": "https://example.com/search?q=x",
                            "image_url": "https://example.com/image.jpg",
                        }
                    ]
                )
            ]
        }
        module = __import__("build_auto_promotable_image_candidates")
        original_read_report = module._read_report
        try:
            module._read_report = lambda _path: report_payload
            payload = build_candidates([Path("report.json")], [_seed_row()])
        finally:
            module._read_report = original_read_report

        self.assertEqual(payload["items"], [])

    def test_promotes_provider_flag_character_specific_candidate(self) -> None:
        report_payload = {
            "unresolved": [
                _unresolved(
                    query="呪術廻戦 キーホルダー (真人)",
                    top_candidates=[
                        {
                            "title": "【グッズ-キーホルダー】呪術廻戦 アクリルキーチェーン 真人",
                            "source_url": "https://www.animate-onlineshop.jp/pn/test/pd/2019616/",
                            "image_url": "https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4580590148253_1.jpg&width=400&height=400&square=1",
                            "score_similarity": 1.0,
                            "goods_type_compatible": True,
                            "distinctive_token_match": True,
                            "all_distinctive_token_match": True,
                            "parenthetical_terms_match": True,
                            "source_url_is_product_detail": True,
                            "safe_source_image_pair": True,
                        }
                    ],
                )
            ]
        }
        module = __import__("build_auto_promotable_image_candidates")
        original_read_report = module._read_report
        try:
            module._read_report = lambda _path: report_payload
            payload = build_candidates(
                [Path("report.json")],
                [
                    _seed_row(
                        name_ko="주술회전 키링 (마히토)",
                        name_ja="呪術廻戦 キーホルダー (真人)",
                        source_store="애니메이트",
                    )
                ],
            )
        finally:
            module._read_report = original_read_report

        self.assertEqual(payload["summary"]["candidate_items"], 1)

    def test_provider_flag_candidate_rejects_unrequested_collab(self) -> None:
        report_payload = {
            "unresolved": [
                _unresolved(
                    query="クレヨンしんちゃん 缶バッジ (しんのすけ)",
                    top_candidates=[
                        {
                            "title": "【グッズ-バッチ】ハローキティ×クレヨンしんちゃん 缶バッジ しんのすけ",
                            "source_url": "https://www.animate-onlineshop.jp/pn/test/pd/1616865/",
                            "image_url": "https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4580560313926_1.jpg&width=400&height=400&square=1",
                            "score_similarity": 1.0,
                            "goods_type_compatible": True,
                            "distinctive_token_match": True,
                            "all_distinctive_token_match": True,
                            "parenthetical_terms_match": True,
                            "source_url_is_product_detail": True,
                            "safe_source_image_pair": True,
                        }
                    ],
                )
            ]
        }
        module = __import__("build_auto_promotable_image_candidates")
        original_read_report = module._read_report
        try:
            module._read_report = lambda _path: report_payload
            payload = build_candidates(
                [Path("report.json")],
                [
                    _seed_row(
                        name_ko="짱구는 못말려 캔뱃지 (신노스케)",
                        name_ja="クレヨンしんちゃん 缶バッジ (しんのすけ)",
                        source_store="애니메이트",
                    )
                ],
            )
        finally:
            module._read_report = original_read_report

        self.assertEqual(payload["items"], [])


if __name__ == "__main__":
    unittest.main()
