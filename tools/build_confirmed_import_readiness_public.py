from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"
DATA = ROOT / "data"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_confirmed_import_readiness_public.json"

WORKFLOWS = {
    "official_detail": {
        "confirmed": SERVER / "official_detail_match_confirmed_rows.json",
        "template": SERVER / "official_detail_match_confirmed_rows.template.json",
        "report": SERVER / "official_detail_match_import_report.json",
        "public_workstream": "official_detail_source_image",
    },
    "storefront": {
        "confirmed": SERVER / "storefront_match_confirmed_rows.json",
        "template": SERVER / "storefront_match_confirmed_rows.template.json",
        "report": SERVER / "storefront_match_import_report.json",
        "public_workstream": "storefront_source_image",
    },
    "catalog_field": {
        "confirmed": SERVER / "catalog_field_confirmed_rows.json",
        "template": SERVER / "catalog_field_confirmed_rows.template.json",
        "report": SERVER / "catalog_field_confirmed_import_report.json",
        "public_workstream": "metadata_field_values",
        "public_action_queue": DATA / "catalog_metadata_action_queue_public.json",
        "public_action_rows_key": "queued_missing_cells",
        "public_action_batches_key": "action_batch_count",
        "public_action_next_step": "fill_confirmed_metadata_patch_templates",
    },
    "source_discovery": {
        "confirmed": SERVER / "source_discovery_confirmed_rows.json",
        "template": SERVER / "source_discovery_confirmed_rows.template.json",
        "report": SERVER / "source_discovery_confirmed_import_report.json",
        "public_workstream": "source_discovery_source_urls",
        "public_action_queue": DATA / "source_discovery_action_queue_public.json",
        "public_action_rows_key": "queued_source_rows",
        "public_action_batches_key": "action_batch_count",
        "public_action_next_step": "confirm_source_url_templates",
    },
    "catalog_image": {
        "confirmed": SERVER / "catalog_image_confirmed_rows.json",
        "template": SERVER / "catalog_image_confirmed_rows.template.json",
        "report": SERVER / "catalog_image_confirmed_import_report.json",
        "public_workstream": "exact_image_urls",
        "public_action_queue": DATA / "catalog_image_attachment_action_queue_public.json",
        "public_action_rows_key": "queued_image_rows",
        "public_action_batches_key": "action_batch_count",
        "public_action_next_step": "confirm_exact_image_url_templates",
    },
    "focus_image": {
        "confirmed": SERVER / "focus_image_confirmed_rows.json",
        "template": SERVER / "focus_image_confirmed_rows.template.json",
        "report": SERVER / "focus_image_confirmed_import_report.json",
        "public_workstream": "requested_focus_image_urls",
        "public_action_queue": DATA / "requested_focus_action_queue_public.json",
        "public_action_rows_key": "queued_action_rows",
        "public_action_batches_key": "action_batch_count",
        "public_action_next_step": "confirm_requested_focus_templates",
    },
    "ichiban_ocr": {
        "confirmed": SERVER / "ichiban_kuji_ocr_confirmed_rows.json",
        "template": SERVER / "ichiban_kuji_ocr_confirmed_rows.template.json",
        "report": SERVER / "ichiban_kuji_ocr_import_report.json",
        "public_workstream": "ichiban_kuji_ocr_rows",
    },
    "ichiban_sub_series": {
        "confirmed": SERVER / "ichiban_kuji_sub_series_confirmed_rows.json",
        "template": SERVER / "ichiban_kuji_sub_series_confirmed_rows.template.json",
        "report": SERVER / "ichiban_kuji_sub_series_confirmed_import_report.json",
        "public_workstream": "ichiban_kuji_sub_series",
    },
    "ichiban_metadata": {
        "confirmed": SERVER / "ichiban_kuji_metadata_confirmed_rows.json",
        "template": SERVER / "ichiban_kuji_metadata_confirmed_rows.template.json",
        "report": SERVER / "ichiban_kuji_metadata_confirmed_import_report.json",
        "public_workstream": "ichiban_kuji_metadata",
        "public_action_queue": DATA / "ichiban_kuji_metadata_action_queue_public.json",
        "public_action_rows_key": "queued_catalog_item_rows",
        "public_action_batches_key": "action_batch_count",
        "public_action_next_step": "fill_confirmed_ichiban_campaign_patch_templates_then_run_import_confirmed_ichiban_metadata_rows",
    },
    "animation_category": {
        "confirmed": SERVER / "animation_category_confirmed_rows.json",
        "template": SERVER / "animation_category_confirmed_rows.template.json",
        "report": SERVER / "animation_category_confirmed_import_report.json",
        "public_workstream": "animation_category_mapping",
        "public_action_queue": DATA / "animation_category_action_queue_public.json",
        "public_action_rows_key": "queued_catalog_rows",
        "public_action_batches_key": "action_batch_count",
        "public_action_next_step": "fill_confirmed_animation_category_mapping_templates_then_run_import_confirmed_animation_category_rows",
    },
    "deduplication": {
        "confirmed": SERVER / "catalog_deduplication_confirmed_rows.json",
        "template": SERVER / "catalog_deduplication_confirmed_rows.template.json",
        "report": SERVER / "catalog_deduplication_confirmed_import_report.json",
        "public_workstream": "catalog_deduplication",
        "public_action_queue": DATA / "catalog_deduplication_action_queue_public.json",
        "public_action_rows_key": "queued_groups",
        "public_action_batches_key": "action_batch_count",
        "public_action_next_step": "fill_confirmed_deduplication_decisions_then_run_import_confirmed_deduplication_rows",
    },
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        raw = payload.get("items")
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
    return []


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "confirmed", "확인", "확정"}


def _report_count(report: Any, *keys: str) -> int:
    if not isinstance(report, dict):
        return 0
    for key in keys:
        value = report.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, list):
            return len(value)
    return 0


def _summary_count(summary: Any, key: str | None) -> int:
    if not key or not isinstance(summary, dict):
        return 0
    value = summary.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _skip_reason_counts(report: Any) -> list[tuple[str, int]]:
    if not isinstance(report, dict):
        return []
    samples: list[Any] = []
    for key in ("skipped_sample", "skipped", "duplicate_sample"):
        value = report.get(key)
        if isinstance(value, list):
            samples.extend(value)
    counter: Counter[str] = Counter()
    for item in samples:
        if isinstance(item, dict):
            counter[str(item.get("reason") or "unspecified")] += 1
    return counter.most_common(8)


def _status(
    *,
    confirmed_exists: bool,
    confirmed_true: int,
    template_items: int,
    public_action_rows: int,
    updated_rows: int,
    skipped_rows: int,
    duplicates: int,
) -> str:
    if confirmed_true and updated_rows:
        return "imported"
    if confirmed_true and (skipped_rows or duplicates):
        return "confirmed_rows_blocked"
    if confirmed_true:
        return "confirmed_rows_pending_import"
    if confirmed_exists:
        return "confirmed_file_empty"
    if template_items:
        return "template_ready_for_manual_confirmation"
    if public_action_rows:
        return "public_action_queue_ready_for_confirmation"
    return "no_current_candidates"


def build_report(workflows: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    workflows = workflows or WORKFLOWS
    rows: list[dict[str, Any]] = []
    for name, config in workflows.items():
        confirmed_path = Path(config["confirmed"])
        template_path = Path(config["template"])
        report_path = Path(config["report"])
        action_queue_path = Path(config["public_action_queue"]) if config.get("public_action_queue") else None
        confirmed_items = _items(_read_json(confirmed_path))
        template_items = _items(_read_json(template_path))
        report = _read_json(report_path)
        action_queue = _read_json(action_queue_path) if action_queue_path else None
        action_summary = action_queue.get("summary", {}) if isinstance(action_queue, dict) else {}
        public_action_rows = _summary_count(action_summary, config.get("public_action_rows_key"))
        public_action_batches = _summary_count(action_summary, config.get("public_action_batches_key"))
        confirmed_true = sum(1 for item in confirmed_items if _confirmed(item.get("manual_confirmed")))
        template_confirmed_true = sum(1 for item in template_items if _confirmed(item.get("manual_confirmed")))
        updated_rows = _report_count(report, "updated_rows", "updated", "created_rows")
        skipped_rows = _report_count(report, "skipped_rows", "skipped", "skipped_sample")
        duplicates = _report_count(report, "duplicates", "duplicate_sample")
        status = _status(
            confirmed_exists=confirmed_path.exists(),
            confirmed_true=confirmed_true,
            template_items=len(template_items),
            public_action_rows=public_action_rows,
            updated_rows=updated_rows,
            skipped_rows=skipped_rows,
            duplicates=duplicates,
        )
        rows.append(
            {
                "workflow": name,
                "public_workstream": config.get("public_workstream") or name,
                "status": status,
                "confirmed_file_exists": confirmed_path.exists(),
                "template_file_exists": template_path.exists(),
                "import_report_exists": report_path.exists(),
                "confirmed_items": len(confirmed_items),
                "manual_confirmed_true": confirmed_true,
                "template_items": len(template_items),
                "template_manual_confirmed_true": template_confirmed_true,
                "public_action_queue_exists": bool(action_queue_path and action_queue_path.exists()),
                "public_action_queue_report": _display_path(action_queue_path),
                "public_action_rows": public_action_rows,
                "public_action_batches": public_action_batches,
                "public_action_next_step": config.get("public_action_next_step"),
                "updated_rows": updated_rows,
                "skipped_rows": skipped_rows,
                "duplicates": duplicates,
                "skip_reason_counts": _skip_reason_counts(report),
                "next_action": _next_action(status),
                "auto_apply_enabled": False,
            }
        )

    by_status = Counter(row["status"] for row in rows)
    return {
        "schema_version": 1,
        "generated_at": _now_utc(),
        "scope": "public_confirmed_import_readiness",
        "summary": {
            "workflow_count": len(rows),
            "confirmed_files": sum(1 for row in rows if row["confirmed_file_exists"]),
            "template_items": sum(int(row["template_items"]) for row in rows),
            "public_action_queue_rows": sum(int(row["public_action_rows"]) for row in rows),
            "public_action_queue_batches": sum(int(row["public_action_batches"]) for row in rows),
            "manual_confirmed_true": sum(int(row["manual_confirmed_true"]) for row in rows),
            "updated_rows": sum(int(row["updated_rows"]) for row in rows),
            "skipped_rows": sum(int(row["skipped_rows"]) for row in rows),
            "duplicates": sum(int(row["duplicates"]) for row in rows),
            "ready_or_pending_import_rows": sum(
                int(row["manual_confirmed_true"])
                for row in rows
                if row["status"] == "confirmed_rows_pending_import"
            ),
            "blocked_confirmed_rows": sum(
                int(row["manual_confirmed_true"])
                for row in rows
                if row["status"] == "confirmed_rows_blocked"
            ),
            "by_status": by_status.most_common(),
            "auto_apply_enabled": False,
        },
        "workflows": rows,
        "instructions": [
            "This public report exposes counts and workflow readiness only; it omits private row-level candidate details.",
            "Rows become importable only after manual_confirmed=true and a dry-run import report passes safety checks.",
            "Public action queue rows identify manually confirmable source/image/metadata templates; row-level details stay in the source queue report.",
            "Use this to decide whether image/source/metadata import queues are blocked, pending, or already imported.",
        ],
        "automation_policy": {
            "public_only": True,
            "auto_apply_catalog_changes": False,
            "requires_manual_review": True,
            "row_level_candidate_details": "omitted_from_public_report",
        },
    }


def _next_action(status: str) -> str:
    return {
        "imported": "Regenerate public catalog reports and verify coverage deltas.",
        "confirmed_rows_blocked": "Review skipped rows and fix candidate identity, duplicate, or safety reasons.",
        "confirmed_rows_pending_import": "Run the guarded import dry-run, then write only if safety checks pass.",
        "confirmed_file_empty": "Mark exact reviewed rows manual_confirmed=true or regenerate from the latest template.",
        "template_ready_for_manual_confirmation": "Review template candidates and copy exact matches into the confirmed file.",
        "public_action_queue_ready_for_confirmation": "Use the linked public action queue to prepare exact confirmed rows.",
        "no_current_candidates": "Generate or refresh the matching candidate/template queue.",
    }.get(status, "Review workflow state manually.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = build_report()
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
