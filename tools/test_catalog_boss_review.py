from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.build_catalog_boss_review_batch import build_batch, write_batch
from tools.import_catalog_boss_review_decisions import (
    build_approved_catalog,
    merge_ledger,
)


class CatalogBossReviewTest(unittest.TestCase):
    def test_builds_first_unreviewed_ten_item_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "catalog.json"
            ledger = root / "ledger.json"
            out_json = root / "current.json"
            out_html = root / "current.html"
            catalog.write_text(
                json.dumps(
                    {
                        "items": [
                            {"catalog_index": index, "name_ko": f"상품 {index}", "image_url": "https://example.com/a.jpg"}
                            for index in range(12)
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ledger.write_text(
                json.dumps({"decisions": [{"row_index": 0, "status": "pass"}]}, ensure_ascii=False),
                encoding="utf-8",
            )

            batch = build_batch(catalog_path=catalog, ledger_path=ledger, batch_size=10)
            write_batch(batch, out_json, out_html)

            self.assertEqual(batch["meta"]["selected_items"], 10)
            self.assertEqual(batch["items"][0]["row_index"], 1)
            self.assertEqual(batch["items"][-1]["row_index"], 10)
            self.assertTrue(out_json.exists())
            html = out_html.read_text(encoding="utf-8")
            self.assertIn("사장님 DB 검수실", html)
            self.assertIn('`../../${path}`', html)
            self.assertIn("^https?:", html)

    def test_approved_catalog_includes_only_pass_and_fixed_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "meta": {"version": 1},
                        "items": [
                            {"catalog_index": 0, "name_ko": "통과"},
                            {"catalog_index": 1, "name_ko": "사진오류"},
                            {"catalog_index": 2, "name_ko": "수정후통과"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ledger = merge_ledger(
                root / "missing-ledger.json",
                [
                    {"row_index": 0, "status": "pass", "status_label": "통과"},
                    {"row_index": 1, "status": "image_error", "status_label": "사진오류"},
                    {"row_index": 2, "status": "fixed_pass", "status_label": "수정후통과"},
                ],
            )

            approved = build_approved_catalog(catalog, ledger)

            self.assertEqual(approved["total_items"], 2)
            self.assertEqual([item["catalog_index"] for item in approved["items"]], [0, 2])
            self.assertEqual(approved["items"][0]["boss_review"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
