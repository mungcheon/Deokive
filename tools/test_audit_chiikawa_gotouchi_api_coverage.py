from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_chiikawa_gotouchi_api_coverage as audit
from enrich_chiikawa_gotouchi_jp_api_images import OfficialImage


class ChiikawaGotouchiApiCoverageAuditTests(unittest.TestCase):
    def test_build_audit_classifies_current_api_coverage(self):
        rows = [
            {
                "catalog_index": 936,
                "source_store": "ご当地ちいかわ 공식(API)",
                "source_url": "https://www.jp-api.com/contents/NOD62/",
                "name_ko": "치이카와 ご当地 마스코트 (후지산)",
                "category": "마스코트",
                "image_url": "",
            },
            {
                "source_store": "치이카와 마켓",
                "name_ko": "치이카와 ご当地 마스코트 (오사카 타코야키)",
                "category": "마스코트",
                "image_url": "",
            },
            {
                "source_store": "치이카와 마켓",
                "name_ko": "치이카와 ご当地 캔뱃지 (교토 마이코)",
                "category": "캔뱃지",
                "image_url": "",
            },
            {
                "source_store": "치이카와 마켓",
                "name_ko": "치이카와 ご当地 마스코트 (알수없음)",
                "category": "마스코트",
                "image_url": "",
            },
        ]
        images = [
            OfficialImage("富士山 ぬいぐるみキーチェーン", "https://www.jp-api.com/images/tphoto_1_0_b.png"),
            OfficialImage("舞妓はん 巾着", "https://www.jp-api.com/images/tphoto_2_0_b.png"),
        ]

        with patch.object(audit, "fetch_official_images", return_value=images):
            report = audit.build_audit(rows, "https://example.test/")

        self.assertEqual(report["target_rows"], 4)
        self.assertEqual(report["official_image_count"], 2)
        self.assertEqual(report["status_counts"]["official_pair_available"], 1)
        self.assertEqual(report["status_counts"]["theme_not_in_current_official_api"], 1)
        self.assertEqual(report["status_counts"]["theme_available_type_missing"], 1)
        self.assertEqual(report["status_counts"]["theme_unclassified"], 1)
        self.assertEqual(report["rows"][0]["catalog_index"], 936)
        self.assertEqual(report["rows"][0]["source_store"], "ご当地ちいかわ 공식(API)")
        self.assertEqual(report["rows"][0]["source_url"], "https://www.jp-api.com/contents/NOD62/")


if __name__ == "__main__":
    unittest.main()
