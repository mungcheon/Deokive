import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_current_image_candidate_reconciliation import _catalog_rows, build_reconciliation


class BuildCurrentImageCandidateReconciliationTest(unittest.TestCase):
    def test_reads_public_catalog_items_payload(self) -> None:
        payload = {"items": [{"name_ko": "A"}, {"name_ko": "B"}]}
        self.assertEqual([row["name_ko"] for row in _catalog_rows(payload)], ["A", "B"])

    def test_reconciles_exact_current_japanese_title(self) -> None:
        rows = [
            {
                "name_ko": "치이카와 러버 스트랩 (하치와레)",
                "name_ja": "ちいかわ ラバーストラップ (ハチワレ)",
                "image_url": "",
                "source_store": "엔스카이",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "candidate.json"
            candidate.write_text(
                """{
                  "items": [{
                    "name_ja": "ちいかわ ラバーストラップ (ハチワレ)",
                    "candidate_title": "ちいかわ ラバーストラップ (ハチワレ)",
                    "source_url": "https://www.enskyshop.com/products/detail/29520",
                    "image_url": "https://www.enskyshop.com/html/upload/save_image/0827104242_68ae629247650.jpg"
                  }]
                }""",
                encoding="utf-8",
            )
            report = build_reconciliation(rows, [candidate])
        self.assertEqual(report["summary"]["importable_rows"], 1)
        self.assertEqual(report["items"][0]["source_store"], "엔스카이")

    def test_rejects_candidate_title_for_different_current_row(self) -> None:
        rows = [
            {
                "name_ko": "치비누이 Vol.2 키리시마 에이지로",
                "name_ja": "ちびぬいマスコット Vol.2 切島鋭児郎",
                "image_url": "",
                "source_store": "엔스카이",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "candidate.json"
            candidate.write_text(
                """{
                  "items": [{
                    "name_ja": "ちびぬいマスコット Vol.2 切島鋭児郎",
                    "candidate_title": "『僕のヒーローアカデミア』 Chibiぬいマスコット 轟焦凍 Vol.2",
                    "source_url": "https://shop.asobistore.jp/products/detail/204493-hero_04_v2-00-00",
                    "image_url": "https://shop.asobistore.jp/simages/product_image_large/4582698665731.jpg"
                  }]
                }""",
                encoding="utf-8",
            )
            report = build_reconciliation(rows, [candidate])
        self.assertEqual(report["summary"]["importable_rows"], 0)
        self.assertEqual(report["risky_sample"][0]["reason"], "candidate_title_not_exact_current_name_ja")

    def test_rejects_rows_without_japanese_name(self) -> None:
        rows = [{"name_ko": "디즈니 봉제 인형 (미키 마우스)", "image_url": "", "source_store": "디즈니 스토어"}]
        with tempfile.TemporaryDirectory() as temp:
            candidate = Path(temp) / "candidate.json"
            candidate.write_text(
                """{
                  "items": [{
                    "name_ko": "디즈니 봉제 인형 (미키 마우스)",
                    "candidate_title": "디즈니 봉제 인형 (미키 마우스)",
                    "source_url": "https://www.pokemoncenter-online.com/4904790177286.html",
                    "image_url": "https://www.pokemoncenter-online.com/a/img/item/4904790177286/M/sample.jpg"
                  }]
                }""",
                encoding="utf-8",
            )
            report = build_reconciliation(rows, [candidate])
        self.assertEqual(report["summary"]["importable_rows"], 0)
        self.assertEqual(report["risky_sample"][0]["reason"], "current_row_missing_name_ja")


if __name__ == "__main__":
    unittest.main()
