from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_requested_focus_review_batches_public as batches


class BuildRequestedFocusReviewBatchesPublicTest(unittest.TestCase):
    def test_build_report_batches_requested_focus_rows_without_auto_apply(self) -> None:
        catalog = [
            {
                "catalog_index": 1,
                "name_ko": "단간론파 누이",
                "name_ja": "ダンガンロンパ ぬい",
                "category": "인형",
                "source_store": "Movic",
                "source_url": "",
                "image_url": "",
                "release_date": "",
                "official_price_jpy": None,
                "barcode": "",
            },
            {
                "catalog_index": 2,
                "name_ko": "마법소녀의 마녀재판 인형",
                "name_ja": "魔法少女ノ魔女裁判 ぬいぐるみ",
                "category": "인형",
                "source_store": "애니메이트",
                "source_url": "https://example.test/item",
                "image_url": "https://example.test/item.jpg",
                "release_date": "2026-01",
                "official_price_jpy": 2200,
                "barcode": "1234567890123",
            },
        ]
        requested = [
            {
                "request_label": "단간론파 누이",
                "status": "already_present",
                "matched_name_ko": "단간론파 누이",
                "has_candidate_image": False,
                "existing_count": 1,
                "review_note": "image still needs review",
            }
        ]

        report = batches.build_report(catalog, requested, batch_size=2)

        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertFalse(report["automation_policy"]["auto_apply_catalog_changes"])
        self.assertGreaterEqual(report["summary"]["batch_count"], 1)
        danganronpa_batches = [
            batch for batch in report["batches"] if batch["topic_id"] == "danganronpa"
        ]
        self.assertTrue(danganronpa_batches)
        self.assertIn(
            "source_url",
            {batch["missing_field"] for batch in danganronpa_batches},
        )
        self.assertTrue(all(batch["auto_apply_enabled"] is False for batch in report["batches"]))

    def test_requested_special_goods_matches_catalog_by_requested_name(self) -> None:
        catalog = [
            {
                "catalog_index": 10,
                "name_ko": "팝팀애픽 부쿠부 그림체 굿즈",
                "name_ja": "ポプテピピック 大川ぶくぶ 絵柄 グッズ",
                "category": "기타 굿즈",
                "source_store": "검색 추가",
                "source_url": "https://example.test/pop",
                "image_url": "https://example.test/pop.jpg",
                "release_date": "",
                "official_price_jpy": None,
                "barcode": "",
            }
        ]
        requested = [
            {
                "request_label": "팝팀애픽 부쿠부 그림체 굿즈",
                "matched_name_ko": "팝팀애픽 부쿠부 그림체 굿즈",
                "status": "already_present",
                "has_candidate_image": True,
                "existing_count": 1,
            }
        ]

        report = batches.build_report(catalog, requested, batch_size=10)
        topic = next(
            row for row in report["topic_summaries"] if row["topic_id"] == "requested_special_goods"
        )

        self.assertEqual(topic["catalog_rows"], 1)
        self.assertEqual(topic["field_missing_totals"]["release_date"], 1)


if __name__ == "__main__":
    unittest.main()
