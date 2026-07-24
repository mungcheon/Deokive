from __future__ import annotations

import unittest

import tools.build_source_discovery_next_focus_variant_metadata_backfill_public as builder


class SourceDiscoveryNextFocusVariantMetadataBackfillPublicTest(unittest.TestCase):
    def test_build_report_queues_risky_strong_candidates(self) -> None:
        live_probe = {
            "items": [
                {
                    "catalog_index": 1117,
                    "name_ko": "카드캡터 체리 아크릴 스탠드 (사쿠라)",
                    "search_term": "カードキャプターさくら アクリルスタンド 木之本桜",
                    "category": "아크릴 스탠드",
                    "source_store": "애니메이트",
                    "strong_title_match_candidate_count": 1,
                    "strong_title_match_candidates": [
                        {
                            "source_url": "https://www.animate-onlineshop.jp/pn/sample/pd/1/",
                            "page_title": "カードキャプターさくら 木之本 桜 BIGアクリルスタンド ver.A",
                            "title_match": {"best_field_score": 1.0},
                            "variant_risk": {
                                "flags": ["oversized_variant", "letter_or_version_variant"],
                                "blocks_auto_apply": True,
                            },
                        }
                    ],
                }
            ]
        }

        report = builder.build_report(live_probe, generated_at="2026-07-24T00:00:00Z")

        self.assertEqual(report["summary"]["queue_rows"], 1)
        self.assertEqual(report["summary"]["risky_strong_candidate_total"], 1)
        item = report["items"][0]
        self.assertTrue(item["manual_backfill_required"])
        self.assertFalse(item["auto_apply_enabled"])
        self.assertIn("name_ja", item["recommended_metadata_fields"])
        self.assertIn("sub_series", item["recommended_metadata_fields"])
        self.assertIn("name_ko", item["recommended_metadata_fields"])
        self.assertEqual(
            item["blocked_until"],
            "exact_variant_metadata_backfilled_or_candidate_rejected",
        )

    def test_build_report_skips_non_risky_candidates(self) -> None:
        live_probe = {
            "items": [
                {
                    "catalog_index": 1,
                    "strong_title_match_candidates": [
                        {
                            "source_url": "https://example.test/pn/sample/pd/1/",
                            "page_title": "Sample",
                            "variant_risk": {
                                "flags": [],
                                "blocks_auto_apply": False,
                            },
                        }
                    ],
                }
            ]
        }

        report = builder.build_report(live_probe, generated_at="2026-07-24T00:00:00Z")

        self.assertEqual(report["summary"]["queue_rows"], 0)
        self.assertEqual(report["items"], [])


if __name__ == "__main__":
    unittest.main()
