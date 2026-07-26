from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.audit_flutter_seed_matches_public import audit, expected_seed_text


class AuditFlutterSeedMatchesPublicTest(unittest.TestCase):
    def test_audit_passes_when_seed_matches_public_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            catalog = root / "catalog_public.json"
            seed = root / "seed_catalog.dart"
            catalog.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "catalog_index": 1,
                                "name_ko": "샘플 굿즈",
                                "category": "피규어",
                                "character_name": "샘플",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            seed.write_text(expected_seed_text(catalog), encoding="utf-8")

            result = audit(catalog, seed)

            self.assertTrue(result["matches"])
            self.assertEqual(result["catalog_rows"], 1)
            self.assertEqual(result["seed_entries"], 1)

    def test_audit_reports_first_diff_when_seed_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            catalog = root / "catalog_public.json"
            seed = root / "seed_catalog.dart"
            catalog.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "catalog_index": 1,
                                "name_ko": "새 이름",
                                "category": "피규어",
                                "character_name": "샘플",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            seed.write_text(
                expected_seed_text(catalog).replace("새 이름", "옛 이름"),
                encoding="utf-8",
            )

            result = audit(catalog, seed)

            self.assertFalse(result["matches"])
            self.assertIsNotNone(result["first_diff_line"])


if __name__ == "__main__":
    unittest.main()
