from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import probe_danganronpa_goodsmile_missing_media as probe


class DanganronpaGoodsmileProbeTests(unittest.TestCase):
    def test_build_report_keeps_probe_manual_review_only(self):
        rows = [
            {
                "catalog_index": 1447,
                "name_ko": "\ub125\ub3c4\ub85c\uc774\ub4dc \ud1a0\uac00\ubbf8 \ubcfc\uc57c",
                "name_ja": "\u306d\u3093\u3069\u308d\u3044\u3069 \u5341\u795e\u767d\u591c",
                "affiliation": "\ub2e8\uac04\ub860\ud30c",
                "source_store": "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
                "image_url": None,
                "source_url": None,
            }
        ]
        fake_result = {
            "changes": [],
            "review": [
                {
                    "row_index": 0,
                    "name_ko": rows[0]["name_ko"],
                    "name_ja": rows[0]["name_ja"],
                    "reason": "no_exact_title_match",
                    "safe_match_count": 0,
                    "top_candidates": [{"title": "other", "source_url": "https://www.goodsmile.com/ja/product/1"}],
                }
            ],
        }
        with patch.object(probe.goodsmile, "enrich", return_value=fake_result), patch.object(
            probe.goodsmile_info, "enrich", return_value={"changes": [], "review": fake_result["review"]}
        ):
            report = probe.build_report(rows)

        self.assertEqual(report["summary"]["target_rows"], 1)
        self.assertEqual(report["summary"]["goodsmile_com_review_rows"], 1)
        self.assertIs(report["summary"]["auto_apply_enabled"], False)
        self.assertIs(report["items"][0]["auto_apply_enabled"], False)
        self.assertEqual(report["items"][0]["recommended_action"], "manual_identity_review_required")


if __name__ == "__main__":
    unittest.main()
