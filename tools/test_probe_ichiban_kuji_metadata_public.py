from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import probe_ichiban_kuji_metadata_public as probe


class ProbeIchibanKujiMetadataPublicTest(unittest.TestCase):
    def test_build_report_extracts_safe_labeled_release_and_price(self) -> None:
        rows = [
            {
                "catalog_index": 1,
                "name_ko": "一番くじ テスト - A賞",
                "source_url": "https://1kuji.com/products/test",
                "release_date": None,
                "official_price_jpy": None,
            }
        ]
        html = """
        <html><body>
          <section>■発売日：2024年7月20日(土)より順次発売予定</section>
          <section>■メーカー希望小売価格：1回750円(税10％込)</section>
        </body></html>
        """
        report = probe.build_report(rows, fetch_text=lambda url: html, sleep_seconds=0)

        self.assertEqual(report["summary"]["urls_with_missing_metadata"], 1)
        self.assertEqual(report["summary"]["safe_release_url_count"], 1)
        self.assertEqual(report["summary"]["safe_price_url_count"], 1)
        self.assertEqual(report["summary"]["safe_release_row_count"], 1)
        self.assertEqual(report["summary"]["safe_price_row_count"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])
        self.assertEqual(report["pages"][0]["safe_release_date"], "2024-07-20")
        self.assertEqual(report["pages"][0]["safe_price_jpy"], 750)
        self.assertFalse(report["pages"][0]["auto_apply_enabled"])

    def test_double_chance_date_does_not_become_release_candidate(self) -> None:
        rows = [
            {
                "catalog_index": 2,
                "name_ko": "一番くじ テスト - B賞",
                "source_url": "https://1kuji.com/products/test2",
                "release_date": None,
                "official_price_jpy": 700,
            }
        ]
        html = """
        <html><body>
          <section>ダブルチャンスキャンペーン 2024年8月31日まで</section>
        </body></html>
        """
        report = probe.build_report(rows, fetch_text=lambda url: html, sleep_seconds=0)

        self.assertEqual(report["summary"]["safe_release_url_count"], 0)
        self.assertEqual(report["summary"]["safe_release_row_count"], 0)
        self.assertEqual(report["summary"]["rows_missing_release_date"], 1)
        self.assertTrue(report["pages"][0]["ambiguous"])

    def test_following_double_chance_field_does_not_hide_safe_price(self) -> None:
        rows = [
            {
                "catalog_index": 3,
                "name_ko": "一番くじ テスト - C賞",
                "source_url": "https://1kuji.com/products/test3",
                "release_date": None,
                "official_price_jpy": None,
            }
        ]
        html = """
        <html><body>
          <section>
            ■発売日：<br />未定
            ■メーカー希望小売価格：1回650円(税10％込)
            ■ダブルチャンスキャンペーン期間：発売日～2021年11月末日
          </section>
        </body></html>
        """
        report = probe.build_report(rows, fetch_text=lambda url: html, sleep_seconds=0)

        self.assertEqual(report["summary"]["safe_price_url_count"], 1)
        self.assertEqual(report["summary"]["safe_price_row_count"], 1)
        self.assertEqual(report["pages"][0]["safe_price_jpy"], 650)
        self.assertIsNone(report["pages"][0]["safe_release_date"])
        self.assertEqual(
            report["pages"][0]["safe_release_reason"],
            "release label says undecided",
        )

    def test_unlabeled_yen_amount_is_unsafe_manual_candidate_only(self) -> None:
        rows = [
            {
                "catalog_index": 4,
                "name_ko": "一番くじ テスト - D賞",
                "source_url": "https://1kuji.com/products/test4",
                "release_date": "2008-05",
                "official_price_jpy": None,
            }
        ]
        html = """
        <html><body>
          <section>参考情報 500円</section>
        </body></html>
        """
        report = probe.build_report(rows, fetch_text=lambda url: html, sleep_seconds=0)

        self.assertEqual(report["summary"]["safe_price_url_count"], 0)
        self.assertEqual(report["summary"]["unsafe_price_candidate_url_count"], 1)
        self.assertEqual(report["summary"]["unsafe_price_candidate_row_count"], 1)
        self.assertEqual(
            dict(report["summary"]["unsafe_price_candidate_reasons"]),
            {"unlabeled_yen_amount_requires_manual_review": 1},
        )
        self.assertIsNone(report["pages"][0]["safe_price_jpy"])
        self.assertEqual(
            report["pages"][0]["unsafe_price_candidates"][0]["reason"],
            "unlabeled_yen_amount_requires_manual_review",
        )
        self.assertTrue(
            report["pages"][0]["unsafe_price_candidates"][0]["manual_review_required"]
        )


if __name__ == "__main__":
    unittest.main()
