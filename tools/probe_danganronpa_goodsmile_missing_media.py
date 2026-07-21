from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import enrich_goodsmile_info_official as goodsmile_info
import enrich_goodsmile_official as goodsmile


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_REPORT = ROOT / "data" / "danganronpa_goodsmile_probe_public.json"
STORE_NAME = "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8"
DANGANRONPA_TERMS = ("\ub2e8\uac04\ub860\ud30c", "\u30c0\u30f3\u30ac\u30f3\u30ed\u30f3\u30d1", "danganronpa")


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _catalog_items(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [item for item in payload["items"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise ValueError(f"{path} must contain a catalog item list")


def _matches_danganronpa(item: dict[str, Any]) -> bool:
    haystack = json.dumps(item, ensure_ascii=False).lower()
    return any(term.lower() in haystack for term in DANGANRONPA_TERMS)


def _target_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if _matches_danganronpa(item)
        and str(item.get("source_store") or "") == STORE_NAME
        and not item.get("image_url")
    ]


def _compact_review(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_index": row.get("row_index"),
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "reason": row.get("reason"),
        "safe_match_count": row.get("safe_match_count"),
        "top_candidates": [
            {
                "title": candidate.get("title"),
                "source_url": candidate.get("source_url"),
                "image_url": candidate.get("image_url"),
            }
            for candidate in row.get("top_candidates", [])[:8]
            if isinstance(candidate, dict)
        ],
    }


def build_report(items: list[dict[str, Any]], *, max_rows: int | None = None) -> dict[str, Any]:
    targets = [dict(item) for item in _target_rows(items)]
    if max_rows is not None:
        targets = targets[:max_rows]

    goodsmile_result = goodsmile.enrich([dict(item) for item in targets])
    info_result = goodsmile_info.enrich([dict(item) for item in targets], max_rows=max_rows)

    rows = []
    by_index = {
        int(item.get("catalog_index") or -1): item
        for item in targets
    }
    goodsmile_review = {int(row.get("row_index") or -1): row for row in goodsmile_result.get("review", [])}
    goodsmile_changes = {int(row.get("row_index") or -1): row for row in goodsmile_result.get("changes", [])}
    info_review = {int(row.get("row_index") or -1): row for row in info_result.get("review", [])}
    info_changes = {int(row.get("row_index") or -1): row for row in info_result.get("changes", [])}

    for offset, item in enumerate(targets):
        catalog_index = int(item.get("catalog_index") or -1)
        row = {
            "catalog_index": catalog_index,
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
            "source_store": item.get("source_store"),
            "current_source_url": item.get("source_url"),
            "current_image_url": item.get("image_url"),
            "goodsmile_com_change": goodsmile_changes.get(offset),
            "goodsmile_info_change": info_changes.get(offset),
            "goodsmile_com_review": _compact_review(goodsmile_review.get(offset, {})),
            "goodsmile_info_review": _compact_review(info_review.get(offset, {})),
            "recommended_action": "manual_identity_review_required",
            "auto_apply_enabled": False,
        }
        if row["goodsmile_com_change"] or row["goodsmile_info_change"]:
            row["recommended_action"] = "review_probe_change_before_catalog_patch"
        rows.append(row)

    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "danganronpa_goodsmile_missing_media_probe",
        "summary": {
            "target_rows": len(targets),
            "goodsmile_com_updated_rows": len(goodsmile_result.get("changes", [])),
            "goodsmile_com_review_rows": len(goodsmile_result.get("review", [])),
            "goodsmile_info_updated_rows": len(info_result.get("changes", [])),
            "goodsmile_info_review_rows": len(info_result.get("review", [])),
            "auto_apply_enabled": False,
        },
        "items": rows,
        "instructions": [
            "This probe records official Good Smile search behavior for Danganronpa rows missing media.",
            "Do not apply probe changes automatically; exact product identity must be reviewed first.",
            "Rows with no unique safe match should remain in manual source discovery or be corrected if the seed identity is invalid.",
        ],
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--max-rows", type=int)
    args = parser.parse_args()

    report = build_report(_catalog_items(args.catalog), max_rows=args.max_rows)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
