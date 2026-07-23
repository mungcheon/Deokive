from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_source_discovery_next_focus_detail_candidates_public as builder
from enrich_catalog_images import ProductImage


class BuildSourceDiscoveryNextFocusDetailCandidatesPublicTest(unittest.TestCase):
    def test_build_report_publishes_review_only_detail_candidates(self) -> None:
        source = {
            "summary": {
                "focus_pack_id": "source-discovery-focus-001",
                "source_store": "애니메이트",
                "target_category": "아크릴 스탠드",
            },
            "items": [
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "catalog_index": 1,
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "name_ko": "최애의 아이 아크릴 스탠드 (호시노 아이)",
                    "name_ja": "推しの子 アクリルスタンド (星野アイ)",
                    "search_query": "推しの子 アクリルスタンド (星野アイ)",
                    "official_search_url": "https://animate.example/search",
                    "source_patch_template": {"catalog_index": 1},
                },
                {
                    "focus_pack_id": "source-discovery-focus-001",
                    "catalog_index": 2,
                    "source_store": "애니메이트",
                    "category": "아크릴 스탠드",
                    "name_ko": "후보 없음",
                    "search_query": "후보 없음",
                },
            ],
        }

        def search(item):
            if item["catalog_index"] == 1:
                return [
                    ProductImage(
                        title="【グッズ-スタンドポップ】【推しの子】 アクリルスタンド 星野アイ",
                        image_url="https://tc-animate.techorus-cdn.com/resize_image/resize_image.php?image=4550000000000_1.jpg&width=400&height=400&square=1",
                        source_url="https://www.animate-onlineshop.jp/pn/test/pd/1234567/",
                    )
                ]
            return []

        report = builder.build_report(
            source,
            search_fn=search,
            generated_at="2026-07-23T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-23T00:00:00Z")
        self.assertEqual(report["summary"]["focus_pack_id"], "source-discovery-focus-001")
        self.assertEqual(report["summary"]["pack_items"], 2)
        self.assertEqual(report["summary"]["items_with_candidates"], 1)
        self.assertEqual(report["summary"]["candidate_rows"], 1)
        self.assertEqual(report["summary"]["exact_candidate_review_rows"], 1)
        self.assertEqual(report["summary"]["no_candidate_items"], 1)
        first = report["items"][0]
        self.assertEqual(first["manual_review_status"], "not_started")
        self.assertEqual(first["manual_confirmed_source_url"], "")
        self.assertEqual(first["candidates"][0]["review_status"], "exact_candidate_review")
        self.assertEqual(first["source_patch_template"]["catalog_index"], 1)
        self.assertFalse(report["automation_policy"]["auto_apply_source_url"])


if __name__ == "__main__":
    unittest.main()
