from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_requested_focus_source_candidates_public as candidates


class BuildRequestedFocusSourceCandidatesPublicTest(unittest.TestCase):
    def test_parse_animate_search_results_extracts_product_cards(self) -> None:
        html = """
        <li>
          <div class="item_list_thumb"><a href="/pn/%E3%83%86%E3%82%B9%E3%83%88/pd/123/">
            <img src="https://tc-animate.example/item.jpg" />
          </a></div>
          <h3><a href="/pn/%E3%83%86%E3%82%B9%E3%83%88/pd/123/" title='ダンガンロンパ 缶バッジ モノクマ'>ダンガンロンパ 缶バッジ モノクマ</a></h3>
          <div class="item_list_detail">
            <p class="price"><font class="notranslate">660</font>円(税込)</p>
            <p class="media">カテゴリ：<a href="/products/index.php?spc=1">グッズ</a></p>
            <p class="release">発売日：2026/07/24 発売</p>
          </div>
        </li>
        """

        rows = candidates.parse_animate_search_results(html)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_url"], "https://www.animate-onlineshop.jp/pn/%E3%83%86%E3%82%B9%E3%83%88/pd/123/")
        self.assertEqual(rows[0]["title"], "ダンガンロンパ 缶バッジ モノクマ")
        self.assertEqual(rows[0]["price_jpy"], 660)
        self.assertEqual(rows[0]["release_label"], "2026/07/24 発売")

    def test_build_report_keeps_candidates_manual_review_only(self) -> None:
        next_work = {
            "next_batch": {
                "batch_id": "requested-focus-action-001",
                "source_store": "애니메이트",
                "items": [
                    {
                        "catalog_index": 7,
                        "review_batch_id": "requested-focus-action-001",
                        "source_store": "애니메이트",
                        "missing_field": "source_url",
                        "name_ko": "단간론파 캔뱃지 (모노쿠마)",
                        "name_ja": "ダンガンロンパ 缶バッジ モノクマ",
                        "category": "캔뱃지",
                    }
                ],
            }
        }

        report = candidates.build_report(next_work, generated_at="2026-07-24T00:00:00Z", fetch_live=False)

        self.assertEqual(report["summary"]["target_rows"], 1)
        self.assertEqual(report["summary"]["candidate_rows"], 1)
        self.assertEqual(report["summary"]["rows_with_candidates"], 0)
        self.assertEqual(report["items"][0]["candidate_status"], "no_official_search_candidates")
        patch = report["items"][0]["confirmed_rows_template_patch"]
        self.assertFalse(patch["manual_confirmed"])
        self.assertEqual(patch["field"], "source_url")
        self.assertEqual(patch["manual_value"], "")
        self.assertEqual(patch["manual_confirmed_blocked_until"], "human_exact_product_confirmation")


if __name__ == "__main__":
    unittest.main()
