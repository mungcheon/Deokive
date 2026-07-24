from __future__ import annotations

import unittest

import tools.build_source_discovery_next_focus_variant_metadata_confirmed_template_public as builder


class SourceDiscoveryNextFocusVariantMetadataConfirmedTemplatePublicTest(unittest.TestCase):
    def test_build_template_uses_catalog_current_values(self) -> None:
        queue = {
            "items": [
                {
                    "catalog_index": 1117,
                    "name_ko": "broken display name",
                    "category": "broken category",
                    "source_store": "broken store",
                    "variant_risk_flags": ["letter_or_version_variant"],
                    "recommended_metadata_fields": ["name_ja", "sub_series", "name_ko"],
                    "review_url": "https://www.animate-onlineshop.jp/search",
                    "candidate_samples": [
                        {
                            "source_url": "https://www.animate-onlineshop.jp/pn/sample/pd/3478244/",
                            "page_title": "Sample title",
                        }
                    ],
                }
            ]
        }
        catalog = {
            "items": [
                {
                    "catalog_index": 1117,
                    "name_ko": "카드캡터 체리 아크릴 스탠드 (사쿠라)",
                    "category": "아크릴 스탠드",
                    "source_store": "애니메이트",
                    "character_name": "키노모토 사쿠라",
                    "affiliation": "카드캡터 체리",
                }
            ]
        }

        template = builder.build_template(queue, catalog, generated_at="2026-07-24T00:00:00Z")

        self.assertEqual(template["summary"]["template_rows"], 1)
        item = template["items"][0]
        self.assertEqual(item["current"]["name_ko"], "카드캡터 체리 아크릴 스탠드 (사쿠라)")
        self.assertEqual(item["current"]["source_store"], "애니메이트")
        self.assertEqual(
            item["metadata_backfill_template"]["manual_evidence_url"],
            "https://www.animate-onlineshop.jp/pn/sample/pd/3478244/",
        )
        self.assertFalse(item["metadata_backfill_template"]["manual_confirmed"])

    def test_build_template_reports_missing_catalog_rows(self) -> None:
        template = builder.build_template(
            {"items": [{"catalog_index": 9999}]},
            {"items": [{"catalog_index": 1, "name_ko": "Existing"}]},
            generated_at="2026-07-24T00:00:00Z",
        )

        self.assertEqual(template["summary"]["template_rows"], 1)
        self.assertEqual(template["summary"]["missing_catalog_rows"], 1)
        self.assertEqual(template["summary"]["missing_catalog_indexes"], [9999])


if __name__ == "__main__":
    unittest.main()
