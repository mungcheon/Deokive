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
                ]
            },
            generated_at="2026-07-22T00:00:00Z",
        )

        self.assertEqual(report["generated_at"], "2026-07-22T00:00:00Z")
        self.assertEqual(report["summary"]["kuji_rows"], 3)
        self.assertEqual(report["summary"]["last_one_rows"], 1)
        self.assertEqual(report["summary"]["last_one_nonzero_price_rows"], 1)
        self.assertFalse(report["summary"]["zero_price_exception_policy_pass"])
        self.assertEqual(report["summary"]["multi_item_prize_label_groups"], 1)
        self.assertFalse(report["summary"]["auto_apply_enabled"])


if __name__ == "__main__":
    unittest.main()
