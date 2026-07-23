from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "ichiban_kuji_reissue_deduplication_public.json"
DEFAULT_OUTPUT = DEFAULT_INPUT


def _compact(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _removed_rows(group: dict[str, Any]) -> list[dict[str, Any]]:
    removed = group.get("removed")
    if not isinstance(removed, list):
        return []
    return [row for row in removed if isinstance(row, dict)]


def _differs_from_kept(group: dict[str, Any], field: str) -> bool:
    kept = group.get("kept")
    if not isinstance(kept, dict):
        return False
    kept_value = _compact(kept.get(field))
    return any(_compact(row.get(field)) != kept_value for row in _removed_rows(group))


def _count_missing_local_files(groups: list[dict[str, Any]], asset_root: Path) -> int:
    missing = 0
    for group in groups:
        rows: list[dict[str, Any]] = []
        kept = group.get("kept")
        if isinstance(kept, dict):
            rows.append(kept)
        rows.extend(_removed_rows(group))
        for row in rows:
            local_path = _compact(row.get("local_image_path"))
            if not local_path:
                continue
            if not (asset_root / local_path).exists():
                missing += 1
    return missing


def build_summary(report: dict[str, Any], *, asset_root: Path | None = None) -> dict[str, Any]:
    raw_groups = report.get("groups")
    groups = [group for group in raw_groups if isinstance(group, dict)] if isinstance(raw_groups, list) else []
    removed_rows = sum(len(_removed_rows(group)) for group in groups)
    reason_counts = Counter(_compact(group.get("reason")) or "unknown" for group in groups)

    summary: dict[str, Any] = {
        "reissue_duplicate_groups": len(groups),
        "kept_rows": len(groups),
        "removed_rows": removed_rows,
        "reason_counts": [[reason, count] for reason, count in sorted(reason_counts.items())],
        "release_date_mismatch_groups": sum(_differs_from_kept(group, "release_date") for group in groups),
        "source_url_mismatch_groups": sum(_differs_from_kept(group, "source_url") for group in groups),
        "image_url_mismatch_groups": sum(_differs_from_kept(group, "image_url") for group in groups),
        "local_image_path_mismatch_groups": sum(_differs_from_kept(group, "local_image_path") for group in groups),
        "official_price_jpy_mismatch_groups": sum(
            _differs_from_kept(group, "official_price_jpy") for group in groups
        ),
        "top_level_duplicate_groups_removed": int(report.get("duplicate_groups_removed") or 0),
        "top_level_duplicate_rows_removed": int(report.get("duplicate_rows_removed") or 0),
        "top_level_price_zero_updates": int(report.get("price_zero_updates") or 0),
        "summary_matches_top_level_counts": (
            int(report.get("duplicate_groups_removed") or 0) == len(groups)
            and int(report.get("duplicate_rows_removed") or 0) == removed_rows
        ),
        "automation_policy": {
            "auto_delete_enabled": False,
            "auto_merge_enabled": False,
            "manual_review_required_before_mutation": True,
        },
    }
    if asset_root is not None:
        summary["missing_local_image_files"] = _count_missing_local_files(groups, asset_root)
    return summary


def build_report(report: dict[str, Any], *, asset_root: Path | None = None) -> dict[str, Any]:
    out = dict(report)
    out["summary"] = build_summary(out, asset_root=asset_root)
    out["summary_generated_at"] = (
        dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--asset-root", type=Path, default=ROOT)
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(report, dict):
        raise SystemExit(f"{args.input} must contain a JSON object")

    updated = build_report(report, asset_root=args.asset_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "output": str(args.output),
                "reissue_duplicate_groups": updated["summary"]["reissue_duplicate_groups"],
                "removed_rows": updated["summary"]["removed_rows"],
                "missing_local_image_files": updated["summary"].get("missing_local_image_files"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
