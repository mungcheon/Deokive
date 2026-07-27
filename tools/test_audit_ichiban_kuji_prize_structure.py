from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class IchibanKujiPrizeStructureAuditTests(unittest.TestCase):
    def test_archive_urls_count_as_represented_campaign_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            seed = temp / "seed.json"
            campaigns = temp / "campaigns.json"
            archive = temp / "archive.json"
            report = temp / "report.json"
            markdown = temp / "report.md"
            seed.write_text(
                json.dumps(
                    [
                        {
                            "name_ko": "A prize",
                            "name_ja": "A賞 Prize",
                            "source_url": "https://1kuji.com/products/a/",
                            "sub_series": "A賞",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            campaigns.write_text(
                json.dumps(
                    [
                        {"url": "https://1kuji.com/products/a/"},
                        {"url": "https://1kuji.com/products/b/"},
                    ]
                ),
                encoding="utf-8",
            )
            archive.write_text(
                json.dumps(
                    [
                        {
                            "row": {
                                "source_url": "https://1kuji.com/products/b/",
                            }
                        }
                    ]
                ),
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "audit_ichiban_kuji_prize_structure.py"),
                    "--seed",
                    str(seed),
                    "--campaigns",
                    str(campaigns),
                    "--archive",
                    str(archive),
                    "--json-report",
                    str(report),
                    "--md-report",
                    str(markdown),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )

            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(payload["seeded_campaign_url_count"], 2)
        self.assertEqual(payload["campaign_without_seed_rows_count"], 0)

    def test_reports_single_generic_variant_rows_as_character_split_review_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            seed = temp / "seed.json"
            campaigns = temp / "campaigns.json"
            archive = temp / "archive.json"
            report = temp / "report.json"
            markdown = temp / "report.md"
            seed.write_text(
                json.dumps(
                    [
                        {
                            "catalog_index": 10,
                            "name_ko": (
                                "\u4e00\u756a\u304f\u3058 TEST / D\u8cde / "
                                "\u30c8\u30ec\u30fc\u30c7\u30a3\u30f3\u30b0\u7f36\u30d0\u30c3\u30b8 "
                                "\u51683\u7a2e / \uae30\ud0c0"
                            ),
                            "name_ja": "D\u8cde \u30c8\u30ec\u30fc\u30c7\u30a3\u30f3\u30b0\u7f36\u30d0\u30c3\u30b8 \u51683\u7a2e",
                            "source_url": "https://1kuji.com/products/test",
                            "sub_series": "D\u8cde",
                            "character_name": "\uae30\ud0c0",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            campaigns.write_text(json.dumps([{"url": "https://1kuji.com/products/test"}]), encoding="utf-8")
            archive.write_text(json.dumps([]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "audit_ichiban_kuji_prize_structure.py"),
                    "--seed",
                    str(seed),
                    "--campaigns",
                    str(campaigns),
                    "--archive",
                    str(archive),
                    "--json-report",
                    str(report),
                    "--md-report",
                    str(markdown),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )

            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(payload["under_split_prize_review_candidate_rows"], 1)
        self.assertEqual(
            payload["under_split_prize_review_candidates"][0]["reason"],
            "single_generic_variant_row_may_need_one_row_per_character",
        )

    def test_reads_public_catalog_items_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            catalog = temp / "catalog_public.json"
            campaigns = temp / "campaigns.json"
            archive = temp / "archive.json"
            report = temp / "report.json"
            markdown = temp / "report.md"
            catalog.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "catalog_index": 12,
                                "name_ko": (
                                    "\u4e00\u756a\u304f\u3058 TEST / E\u8cde / "
                                    "\u30b9\u30c6\u30c3\u30ab\u30fc\u30b3\u30ec\u30af\u30b7\u30e7\u30f3 / "
                                    "\uae30\ud0c0"
                                ),
                                "name_ja": "E\u8cde \u30b9\u30c6\u30c3\u30ab\u30fc\u30b3\u30ec\u30af\u30b7\u30e7\u30f3",
                                "source_url": "https://1kuji.com/products/test",
                                "sub_series": "E\u8cde",
                                "character_name": "\uae30\ud0c0",
                            }
                        ],
                        "total_items": 1,
                    }
                ),
                encoding="utf-8",
            )
            campaigns.write_text(json.dumps([{"url": "https://1kuji.com/products/test"}]), encoding="utf-8")
            archive.write_text(json.dumps([]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "audit_ichiban_kuji_prize_structure.py"),
                    "--catalog",
                    str(catalog),
                    "--campaigns",
                    str(campaigns),
                    "--archive",
                    str(archive),
                    "--json-report",
                    str(report),
                    "--md-report",
                    str(markdown),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )

            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(payload["catalog"], str(catalog))
        self.assertEqual(payload["prize_rows"], 1)
        self.assertEqual(payload["under_split_prize_review_candidate_rows"], 1)

    def test_does_not_report_character_specific_single_rows_as_split_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            seed = temp / "seed.json"
            campaigns = temp / "campaigns.json"
            archive = temp / "archive.json"
            report = temp / "report.json"
            markdown = temp / "report.md"
            seed.write_text(
                json.dumps(
                    [
                        {
                            "catalog_index": 11,
                            "name_ko": (
                                "\u4e00\u756a\u304f\u3058 TEST / A\u8cde / "
                                "\u864e\u6756\u60a0\u4ec1\u30d5\u30a3\u30ae\u30e5\u30a2 / "
                                "\uc774\ud0c0\ub3c4\ub9ac \uc720\uc9c0"
                            ),
                            "name_ja": "A\u8cde \u864e\u6756\u60a0\u4ec1\u30d5\u30a3\u30ae\u30e5\u30a2",
                            "source_url": "https://1kuji.com/products/test",
                            "sub_series": "A\u8cde",
                            "character_name": "\uc774\ud0c0\ub3c4\ub9ac \uc720\uc9c0",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            campaigns.write_text(json.dumps([{"url": "https://1kuji.com/products/test"}]), encoding="utf-8")
            archive.write_text(json.dumps([]), encoding="utf-8")

            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "audit_ichiban_kuji_prize_structure.py"),
                    "--seed",
                    str(seed),
                    "--campaigns",
                    str(campaigns),
                    "--archive",
                    str(archive),
                    "--json-report",
                    str(report),
                    "--md-report",
                    str(markdown),
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )

            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(payload["under_split_prize_review_candidate_rows"], 0)


if __name__ == "__main__":
    unittest.main()
