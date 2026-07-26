from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class IchibanVariantCompletenessAuditTests(unittest.TestCase):
    def test_reports_missing_numbered_variant_rows(self) -> None:
        rows = [
            _row(1, "G賞 タオル（1/3）"),
            _row(2, "G賞 タオル（3/3）"),
        ]
        payload = _run_audit(rows)

        self.assertEqual(payload["incomplete_fraction_groups_count"], 1)
        group = payload["incomplete_fraction_groups"][0]
        self.assertEqual(group["expected_variant_count"], 3)
        self.assertEqual(group["present_variant_numbers"], [1, 3])
        self.assertEqual(group["missing_variant_numbers"], [2])

    def test_accepts_complete_numbered_variant_rows(self) -> None:
        rows = [
            _row(1, "H賞 アクリルチャーム（1/3）", tier="H賞"),
            _row(2, "H賞 アクリルチャーム（2/3）", tier="H賞"),
            _row(3, "H賞 アクリルチャーム（3/3）", tier="H賞"),
        ]
        payload = _run_audit(rows)

        self.assertEqual(payload["complete_fraction_groups"], 1)
        self.assertEqual(payload["incomplete_fraction_groups_count"], 0)

    def test_reports_assort_count_marker_without_enough_rows(self) -> None:
        rows = [_row(1, "I賞 ステーショナリーアソート 全4種", tier="I賞")]
        payload = _run_audit(rows)

        self.assertEqual(payload["count_marker_review_groups_count"], 1)
        group = payload["count_marker_review_groups"][0]
        self.assertEqual(group["expected_variant_count"], 4)
        self.assertEqual(group["present_row_count"], 1)


def _row(index: int, name_ja: str, *, tier: str = "G賞") -> dict[str, object]:
    return {
        "catalog_index": index,
        "name_ko": f"一番くじ テスト / {tier} / {name_ja} / 기타",
        "name_ja": name_ja,
        "character_name": "기타",
        "series_name": "一番くじ テスト",
        "sub_series": tier,
        "source_url": "https://1kuji.com/products/test",
    }


def _run_audit(rows: list[dict[str, object]]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        catalog = temp / "catalog.json"
        report = temp / "report.json"
        markdown = temp / "report.md"
        catalog.write_text(json.dumps({"items": rows}, ensure_ascii=False), encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "audit_ichiban_variant_completeness.py"),
                "--catalog",
                str(catalog),
                "--json-report",
                str(report),
                "--md-report",
                str(markdown),
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return json.loads(report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
