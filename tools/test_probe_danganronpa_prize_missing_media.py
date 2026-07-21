from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import probe_danganronpa_prize_missing_media as probe


class DanganronpaPrizeProbeTests(unittest.TestCase):
    def test_build_report_records_exact_candidate_as_manual_review(self):
        row = {
            "catalog_index": 1467,
            "name_ko": "Desktop Cute \ubaa8\ub178\ucfe0\ub9c8",
            "name_ja": "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\u30ad\u30e5\u30fc\u30c8 \u30e2\u30ce\u30af\u30de",
            "source_store": "Taito",
        }
        candidate = {
            "candidate_title": "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\u30ad\u30e5\u30fc\u30c8 \u30e2\u30ce\u30af\u30de",
            "candidate_source_url": "https://www.taito.co.jp/prize/item/12345",
            "candidate_image_url": "https://www.taito.co.jp/Content/images/prize/monokuma.jpg",
        }
        with patch.object(probe.detail_candidates, "_taito_candidates", return_value=[candidate]):
            report = probe.build_report([row])

        self.assertEqual(report["summary"]["target_rows"], 1)
        self.assertEqual(report["summary"]["single_exact_candidate_rows"], 1)
        self.assertIs(report["summary"]["auto_apply_enabled"], False)
        self.assertIs(report["items"][0]["auto_apply_enabled"], False)
        self.assertEqual(report["items"][0]["recommended_action"], "review_single_exact_candidate_before_patch")


if __name__ == "__main__":
    unittest.main()
