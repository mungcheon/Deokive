from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.generate_seed_catalog_dart import generate, validate_row_count


class GenerateSeedCatalogDartTest(unittest.TestCase):
    def test_generate_keeps_basic_catalog_fields(self) -> None:
        dart = generate(
            [
                {
                    "name_ko": "Sample goods",
                    "category": "figure",
                    "character_name": "Sample",
                    "image_url": "https://example.test/image.jpg",
                    "official_price_jpy": "1200",
                }
            ]
        )

        self.assertIn("const List<GoodsCatalogEntry> kSeedCatalog", dart)
        self.assertIn("nameKo: 'Sample goods'", dart)
        self.assertIn("officialPriceJpy: 1200", dart)
        self.assertIn("imageUrl: 'https://example.test/image.jpg'", dart)

    def test_validate_row_count_rejects_unintentional_regression(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            meta = Path(raw_tmp) / "catalog_public_meta.json"
            meta.write_text('{"row_count": 3}\n', encoding="utf-8")

            with self.assertRaises(SystemExit) as raised:
                validate_row_count([{"name_ko": "A"}, {"name_ko": "B"}], reference_meta=meta)

            self.assertIn("refusing to generate a smaller seed catalog", str(raised.exception))

    def test_validate_row_count_allows_explicit_regression(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            meta = Path(raw_tmp) / "catalog_public_meta.json"
            meta.write_text('{"row_count": 3}\n', encoding="utf-8")

            validate_row_count(
                [{"name_ko": "A"}, {"name_ko": "B"}],
                reference_meta=meta,
                allow_row_count_drop=True,
            )


if __name__ == "__main__":
    unittest.main()
