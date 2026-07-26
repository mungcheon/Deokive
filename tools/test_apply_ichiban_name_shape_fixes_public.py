from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_ichiban_name_shape_fixes_public as fixer


class ApplyIchibanNameShapeFixesPublicTest(unittest.TestCase):
    def test_apply_fixes_inserts_missing_item_part(self) -> None:
        payload = {
            "items": [
                {
                    "catalog_index": 1,
                    "name_ko": "\u4e00\u756a\u304a\u307f\u304f\u3058 \u30cf\u30a4\u30ad\u30e5\u30fc!! / \u7f36\u30d0\u30c3\u30b8 / \uae30\ud0c0",
                    "name_ja": "\u7f36\u30d0\u30c3\u30b8",
                    "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                    "sub_series": "\u7f36\u30d0\u30c3\u30b8",
                    "character_name": "\uae30\ud0c0",
                }
            ]
        }

        report = fixer.apply_fixes(payload)

        self.assertEqual(report["summary"]["updated_rows"], 1)
        self.assertEqual(
            payload["items"][0]["name_ko"],
            "\u4e00\u756a\u304a\u307f\u304f\u3058 \u30cf\u30a4\u30ad\u30e5\u30fc!! / \u7f36\u30d0\u30c3\u30b8 / \u7f36\u30d0\u30c3\u30b8 / \uae30\ud0c0",
        )

    def test_apply_fixes_skips_character_mismatch(self) -> None:
        payload = {
            "items": [
                {
                    "catalog_index": 2,
                    "name_ko": "\u4e00\u756a\u304a\u307f\u304f\u3058 \u30cf\u30a4\u30ad\u30e5\u30fc!! / \u7f36\u30d0\u30c3\u30b8 / \uae30\ud0c0",
                    "name_ja": "\u7f36\u30d0\u30c3\u30b8",
                    "source_store": "\uc774\uce58\ubc29\ucfe0\uc9c0",
                    "sub_series": "\u7f36\u30d0\u30c3\u30b8",
                    "character_name": "\ub2e4\ub978 \uce90\ub9ad\ud130",
                }
            ]
        }

        report = fixer.apply_fixes(payload)

        self.assertEqual(report["summary"]["updated_rows"], 0)


if __name__ == "__main__":
    unittest.main()
