from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import catalog_quality_report as quality


class CatalogQualityReportTests(unittest.TestCase):
    def test_load_catalog_rows_accepts_public_catalog_object(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog_public.json"
            path.write_text(
                json.dumps({"items": [{"name_ko": "A"}, {"name_ko": "B"}]}),
                encoding="utf-8",
            )

            rows = quality.load_catalog_rows(path)

        self.assertEqual([row["name_ko"] for row in rows], ["A", "B"])

    def test_default_input_stays_local_seed_for_local_quality_report(self) -> None:
        self.assertEqual(quality.DEFAULT_INPUT.name, "catalog_seed_from_local.json")


if __name__ == "__main__":
    unittest.main()
