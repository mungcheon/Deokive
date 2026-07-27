from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.advance_catalog_boss_review import advance_review
from tools.build_catalog_boss_review_batch import build_batch, write_batch
from tools.catalog_boss_review_status import build_status
from tools.import_catalog_boss_review_decisions import (
    build_approved_catalog,
    build_rework_queue,
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
            self.assertEqual(len(batch["review_items"]), 12)
            self.assertTrue(out_json.exists())
            html = out_html.read_text(encoding="utf-8")
            self.assertIn("사장님 DB 검수실", html)
            self.assertIn("다음 배치 검토하기", html)
            self.assertIn("수정 담당", html)
            self.assertIn("공개 반영 담당", html)
            self.assertIn("deokive-boss-review-ledger-v3", html)
            self.assertIn("statuses.includes", html)

    def test_approved_catalog_includes_only_pass(self) -> None:
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
                            {"catalog_index": 2, "name_ko": "내용오류"},
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
                    {"row_index": 1, "statuses": ["image_error"], "status_label": "사진오류"},
                    {"row_index": 2, "statuses": ["content_error"], "status_label": "내용오류"},
                ],
            )

            approved = build_approved_catalog(catalog, ledger)

            self.assertEqual(approved["total_items"], 1)
            self.assertEqual([item["catalog_index"] for item in approved["items"]], [0])
            self.assertEqual(approved["items"][0]["boss_review"]["status"], "pass")

    def test_rework_queue_routes_multi_status_rows_to_combined_intake_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "items": [
                            {"catalog_index": 0, "name_ko": "사진 내용 둘 다 수정 필요"},
                            {"catalog_index": 1, "name_ko": "내용 수정 필요"},
                            {"catalog_index": 2, "name_ko": "통과"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ledger = merge_ledger(
                root / "missing-ledger.json",
                [
                    {
                        "row_index": 0,
                        "statuses": ["image_error", "content_error"],
                        "status_label": "사진오류 + 내용오류",
                        "note": "wrong photo and name",
                    },
                    {"row_index": 1, "statuses": ["content_error"], "status_label": "내용오류", "note": "wrong name"},
                    {"row_index": 2, "status": "pass", "status_label": "통과"},
                ],
            )

            queue = build_rework_queue(catalog, ledger)

            self.assertEqual(queue["meta"]["blocked_items"], 2)
            self.assertEqual(queue["items"][0]["rework_type"], "image_and_field_update")
            self.assertEqual(queue["items"][0]["statuses"], ["image_error", "content_error"])
            self.assertIn("image and field", queue["items"][0]["next_step"])
            self.assertEqual(queue["items"][1]["rework_type"], "field_update")

    def test_advance_review_imports_decisions_and_builds_next_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "catalog.json"
            decisions = root / "decisions.json"
            ledger = root / "ledger.json"
            approved = root / "approved.json"
            rework = root / "rework.json"
            next_json = root / "next.json"
            next_html = root / "next.html"
            catalog.write_text(
                json.dumps(
                    {
                        "items": [
                            {"catalog_index": index, "name_ko": f"상품 {index}", "image_url": "https://example.com/a.jpg"}
                            for index in range(15)
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            decisions.write_text(
                json.dumps(
                    {
                        "decisions": [
                            {
                                "row_index": index,
                                "catalog_index": index,
                                "display_name": f"상품 {index}",
                                "status": "pass",
                                "status_label": "통과",
                            }
                            for index in range(10)
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = advance_review(
                decisions,
                catalog_path=catalog,
                ledger_path=ledger,
                approved_path=approved,
                rework_path=rework,
                batch_json_path=next_json,
                batch_html_path=next_html,
                batch_size=10,
            )

            self.assertEqual(result["reviewed_items"], 10)
            self.assertEqual(result["approved_items"], 10)
            self.assertEqual(result["next_selected_items"], 5)
            self.assertEqual(result["next_first_row_index"], 10)
            self.assertEqual(result["next_last_row_index"], 14)
            self.assertTrue(next_html.exists())

    def test_status_reports_progress_and_next_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "catalog.json"
            ledger = root / "ledger.json"
            catalog.write_text(
                json.dumps(
                    {
                        "items": [
                            {"catalog_index": index, "name_ko": f"상품 {index}"}
                            for index in range(25)
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            ledger.write_text(
                json.dumps(
                    {
                        "decisions": [
                            {"row_index": 0, "status": "pass"},
                            {"row_index": 1, "statuses": ["image_error", "content_error"]},
                            {"row_index": 2, "status": "image_error"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            status = build_status(catalog_path=catalog, ledger_path=ledger, batch_size=10)

            self.assertEqual(status["total_items"], 25)
            self.assertEqual(status["reviewed_items"], 3)
            self.assertEqual(status["approved_items"], 1)
            self.assertEqual(status["blocked_items"], 2)
            self.assertEqual(status["status_counts"]["content_error"], 1)
            self.assertEqual(status["status_counts"]["image_error"], 2)
            self.assertEqual(status["remaining_batches"], 3)
            self.assertEqual(status["next_batch"]["first_row_index"], 3)
            self.assertEqual(status["next_batch"]["last_row_index"], 12)


if __name__ == "__main__":
    unittest.main()
