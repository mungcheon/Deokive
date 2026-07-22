from __future__ import annotations

import unittest

from build_gotouchi_representative_image_attachment_public import build_report


class GotouchiRepresentativeImageAttachmentTests(unittest.TestCase):
    def test_build_report_exports_manual_confirmed_templates_only_for_representative_rows(self):
        payload = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "치이카와 마스코트",
                    "name_ja": "ちいかわ マスコット",
                    "category": "마스코트",
                    "character_name": "치이카와",
                    "candidate_status": "attached_representative_official_image",
                    "row_type": "plush_keychain",
                    "top_candidates": [
                        {
                            "page": "https://www.jp-api.com/contents/NOD62/",
                            "image_url": "https://www.jp-api.com/images/sample.png",
                            "type": "plush_keychain",
                            "matched_motifs": ["sample"],
                        }
                    ],
                },
                {
                    "catalog_index": 2,
                    "candidate_status": "motif_only_type_mismatch",
                    "top_candidates": [
                        {
                            "page": "https://www.jp-api.com/contents/NOD62/",
                            "image_url": "https://www.jp-api.com/images/wrong.png",
                        }
                    ],
                },
            ]
        }

        report = build_report(payload, generated_at="2026-07-22T00:00:00Z")

        self.assertEqual(report["summary"]["representative_attachment_rows"], 1)
        self.assertEqual(report["summary"]["manual_confirmed_true"], 0)
        self.assertIs(report["summary"]["auto_apply_enabled"], False)
        item = report["items"][0]
        self.assertEqual(item["catalog_index"], 1)
        self.assertEqual(item["field"], "image_url")
        self.assertIs(item["manual_confirmed"], False)
        self.assertTrue(item["representative_image"])
        self.assertEqual(item["manual_value"], "https://www.jp-api.com/images/sample.png")


if __name__ == "__main__":
    unittest.main()
