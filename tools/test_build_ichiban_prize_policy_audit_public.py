from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_ichiban_prize_policy_audit_public as audit


class BuildIchibanPrizePolicyAuditPublicTest(unittest.TestCase):
    def test_last_one_price_policy_flags_nonzero_rows(self) -> None:
        report = audit.build_report(
            {
                "items": [
                    {
                        "catalog_index": 1,
                        "name_ko": "一番くじ sample - ラストワン賞 prize",
                        "sub_series": "ラストワン賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 2,
                        "name_ko": "一番くじ sample - A賞 prize one",
                        "sub_series": "A賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 3,
                        "name_ko": "一番くじ sample - A賞 prize two",
                        "sub_series": "A賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 4,
                        "name_ko": "一番くじ sample - B賞 アクリル（1/3）",
                        "name_ja": "B賞 アクリル（1/3）",
                        "sub_series": "B賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 5,
                        "name_ko": "一番くじ sample - B賞 アクリル（3/3）",
                        "name_ja": "B賞 アクリル（3/3）",
                        "sub_series": "B賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample",
                    },
                    {
                        "catalog_index": 6,
                        "name_ko": "一番くじ sample（再販売） - A賞 prize one",
                        "sub_series": "A賞",
                        "official_price_jpy": 650,
                        "source_url": "https://1kuji.com/products/sample-2",
                    },
                ]
            },
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(report["summary"]["kuji_rows"], 6)
        self.assertEqual(report["summary"]["last_one_rows"], 1)
        self.assertEqual(report["summary"]["last_one_nonzero_price_rows"], 1)
        self.assertFalse(report["summary"]["zero_price_exception_policy_pass"])
        self.assertEqual(report["summary"]["multi_item_prize_label_groups"], 2)
        self.assertEqual(report["summary"]["numbered_variant_prize_label_groups"], 1)
        self.assertEqual(report["summary"]["incomplete_numbered_variant_prize_label_groups"], 1)
        self.assertFalse(report["summary"]["numbered_variant_coverage_policy_pass"])
        self.assertEqual(
            report["incomplete_numbered_variant_prize_label_groups"][0]["missing_variant_numbers"],
            [2],
        )
        self.assertEqual(report["summary"]["probable_reissue_review_groups"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])


if __name__ == "__main__":
    unittest.main()
