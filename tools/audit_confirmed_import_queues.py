from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import import_confirmed_animation_category_rows
import import_confirmed_dedupe_decisions
import import_confirmed_ichiban_metadata_rows
import import_confirmed_image_attachment_rows
import import_confirmed_metadata_rows
import import_confirmed_requested_focus_rows
import import_confirmed_source_discovery_rows
import import_confirmed_variant_metadata_backfill_rows

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "server"
DATA = ROOT / "data"
DEFAULT_JSON = SERVER / "catalog_confirmed_import_queue_audit.json"
DEFAULT_MD = SERVER / "catalog_confirmed_import_queue_audit.md"

WORKFLOWS = {
    "official_detail": {
        "confirmed": SERVER / "official_detail_match_confirmed_rows.json",
        "template": SERVER / "official_detail_match_confirmed_rows.template.json",
        "report": SERVER / "official_detail_match_import_report.json",
        "artifact": SERVER / "official_detail_match_review.html",
        "description": "official detail source/image candidates",
        "dry_run_command": "python tools/import_confirmed_official_detail_matches.py --queue server/official_detail_match_confirmed_rows.json --report server/official_detail_match_import_report.json",
        "write_command": "python tools/import_confirmed_official_detail_matches.py --queue server/official_detail_match_confirmed_rows.json --report server/official_detail_match_import_report.json --write",
    },
    "storefront": {
        "confirmed": SERVER / "storefront_match_confirmed_rows.json",
        "template": SERVER / "storefront_match_confirmed_rows.template.json",
        "report": SERVER / "storefront_match_import_report.json",
        "artifact": SERVER / "storefront_match_review.html",
        "description": "storefront/Fanding source and image candidates",
        "dry_run_command": "python tools/import_confirmed_storefront_matches.py --queue server/storefront_match_confirmed_rows.json --report server/storefront_match_import_report.json",
        "write_command": "python tools/import_confirmed_storefront_matches.py --queue server/storefront_match_confirmed_rows.json --report server/storefront_match_import_report.json --write",
    },
    "catalog_field": {
        "confirmed": import_confirmed_metadata_rows.DEFAULT_QUEUE,
        "template": import_confirmed_metadata_rows.FALLBACK_QUEUE,
        "report": import_confirmed_metadata_rows.DEFAULT_REPORT,
        "artifact": SERVER / "catalog_field_enrichment_review.html",
        "description": "manual field values such as barcode/date/price",
        "dry_run_command": "python tools/import_confirmed_metadata_rows.py --queue server/catalog_field_confirmed_rows.json --report server/catalog_field_confirmed_import_report.json",
        "write_command": "python tools/import_confirmed_metadata_rows.py --queue server/catalog_field_confirmed_rows.json --report server/catalog_field_confirmed_import_report.json --write",
    },
    "source_discovery": {
        "confirmed": import_confirmed_source_discovery_rows.DEFAULT_QUEUE,
        "template": import_confirmed_source_discovery_rows.FALLBACK_QUEUE,
        "report": import_confirmed_source_discovery_rows.DEFAULT_REPORT,
        "artifact": SERVER / "source_discovery_review_batches_public.html",
        "description": "manual confirmed exact official/source URLs",
        "dry_run_command": "python tools/import_confirmed_source_discovery_rows.py --queue server/source_discovery_confirmed_rows.json --report server/source_discovery_confirmed_import_report.json",
        "write_command": "python tools/import_confirmed_source_discovery_rows.py --queue server/source_discovery_confirmed_rows.json --report server/source_discovery_confirmed_import_report.json --write",
    },
    "catalog_image": {
        "confirmed": import_confirmed_image_attachment_rows.DEFAULT_QUEUE,
        "template": import_confirmed_image_attachment_rows.FALLBACK_QUEUE,
        "report": import_confirmed_image_attachment_rows.DEFAULT_REPORT,
        "artifact": SERVER / "catalog_image_review_batches.html",
        "description": "manual confirmed exact image URLs from official/detail evidence",
        "dry_run_command": "python tools/import_confirmed_image_attachment_rows.py --queue server/catalog_image_attachment_confirmed_rows.json --report server/catalog_image_attachment_confirmed_import_report.json",
        "write_command": "python tools/import_confirmed_image_attachment_rows.py --queue server/catalog_image_attachment_confirmed_rows.json --report server/catalog_image_attachment_confirmed_import_report.json --write",
    },
    "focus_image": {
        "confirmed": import_confirmed_requested_focus_rows.DEFAULT_QUEUE,
        "template": import_confirmed_requested_focus_rows.FALLBACK_QUEUE,
        "report": import_confirmed_requested_focus_rows.DEFAULT_REPORT,
        "artifact": SERVER / "focus_missing_image_queue_current.html",
        "description": "manual confirmed exact image URLs for requested/focus series rows",
        "dry_run_command": "python tools/import_confirmed_requested_focus_rows.py --queue server/requested_focus_confirmed_rows.json --report server/requested_focus_confirmed_import_report.json",
        "write_command": "python tools/import_confirmed_requested_focus_rows.py --queue server/requested_focus_confirmed_rows.json --report server/requested_focus_confirmed_import_report.json --write",
    },
    "variant_metadata": {
        "confirmed": import_confirmed_variant_metadata_backfill_rows.DEFAULT_QUEUE,
        "template": import_confirmed_variant_metadata_backfill_rows.FALLBACK_QUEUE,
        "report": import_confirmed_variant_metadata_backfill_rows.DEFAULT_REPORT,
        "artifact": DATA / "source_discovery_next_focus_variant_metadata_confirmed_rows.template.json",
        "description": "manual confirmed exact variant metadata for risky source candidates",
        "dry_run_command": "python tools/import_confirmed_variant_metadata_backfill_rows.py",
        "write_command": "python tools/import_confirmed_variant_metadata_backfill_rows.py --write",
    },
    "ichiban_ocr": {
        "confirmed": SERVER / "ichiban_kuji_ocr_confirmed_rows.json",
        "template": SERVER / "ichiban_kuji_ocr_confirmed_rows.template.json",
        "report": SERVER / "ichiban_kuji_ocr_import_report.json",
        "artifact": SERVER / "ichiban_kuji_ocr_review.html",
        "description": "Ichiban Kuji OCR/manual prize rows",
        "dry_run_command": "python tools/import_confirmed_ichiban_ocr_rows.py --queue server/ichiban_kuji_ocr_confirmed_rows.json --report server/ichiban_kuji_ocr_import_report.json",
        "write_command": "python tools/import_confirmed_ichiban_ocr_rows.py --queue server/ichiban_kuji_ocr_confirmed_rows.json --report server/ichiban_kuji_ocr_import_report.json --write",
    },
    "ichiban_sub_series": {
        "confirmed": SERVER / "ichiban_kuji_sub_series_confirmed_rows.json",
        "template": SERVER / "ichiban_kuji_sub_series_confirmed_rows.template.json",
        "report": SERVER / "ichiban_kuji_sub_series_confirmed_import_report.json",
        "artifact": SERVER / "ichiban_kuji_sub_series_review_batches.html",
        "description": "manual confirmed Ichiban Kuji prize tier/sub-series values",
        "dry_run_command": "python tools/import_confirmed_catalog_field_rows.py --queue server/ichiban_kuji_sub_series_confirmed_rows.json --report server/ichiban_kuji_sub_series_confirmed_import_report.json",
        "write_command": "python tools/import_confirmed_catalog_field_rows.py --queue server/ichiban_kuji_sub_series_confirmed_rows.json --report server/ichiban_kuji_sub_series_confirmed_import_report.json --write",
    },
    "ichiban_metadata": {
        "confirmed": import_confirmed_ichiban_metadata_rows.DEFAULT_QUEUE,
        "template": import_confirmed_ichiban_metadata_rows.FALLBACK_QUEUE,
        "report": import_confirmed_ichiban_metadata_rows.DEFAULT_REPORT,
        "artifact": SERVER / "ichiban_kuji_metadata_review_batches_public.html",
        "description": "manual confirmed Ichiban Kuji campaign release/price/source metadata",
        "dry_run_command": "python tools/import_confirmed_ichiban_metadata_rows.py --queue server/ichiban_kuji_metadata_confirmed_rows.json --report server/ichiban_kuji_metadata_confirmed_import_report.json",
        "write_command": "python tools/import_confirmed_ichiban_metadata_rows.py --queue server/ichiban_kuji_metadata_confirmed_rows.json --report server/ichiban_kuji_metadata_confirmed_import_report.json --write",
    },
    "animation_category": {
        "confirmed": import_confirmed_animation_category_rows.DEFAULT_QUEUE,
        "template": import_confirmed_animation_category_rows.FALLBACK_QUEUE,
        "report": import_confirmed_animation_category_rows.DEFAULT_REPORT,
        "artifact": SERVER / "animation_category_review_batches_public.html",
        "description": "manual confirmed animation goods category/folder mappings",
        "dry_run_command": "python tools/import_confirmed_animation_category_rows.py --queue server/animation_category_confirmed_rows.json --report server/animation_category_confirmed_import_report.json",
        "write_command": "python tools/import_confirmed_animation_category_rows.py --queue server/animation_category_confirmed_rows.json --report server/animation_category_confirmed_import_report.json --write",
    },
    "deduplication": {
        "confirmed": import_confirmed_dedupe_decisions.DEFAULT_QUEUE,
        "template": import_confirmed_dedupe_decisions.FALLBACK_QUEUE,
        "report": import_confirmed_dedupe_decisions.DEFAULT_REPORT,
        "artifact": SERVER / "catalog_deduplication_review_batches_public.html",
        "description": "manual confirmed duplicate catalog merge/remove decisions",
        "dry_run_command": "python tools/import_confirmed_dedupe_decisions.py --queue server/catalog_dedupe_confirmed_decisions.json --report server/catalog_dedupe_confirmed_import_report.json",
        "write_command": "python tools/import_confirmed_dedupe_decisions.py --queue server/catalog_dedupe_confirmed_decisions.json --report server/catalog_dedupe_confirmed_import_report.json --write",
    },
}


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _items(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        raw_items = data.get("items")
        if isinstance(raw_items, list):
            return [item for item in raw_items if isinstance(item, dict)]
        if data.get("field") and data.get("row_index") is not None:
            return [data]
    return []


def _confirmed(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "confirmed", "확인", "확정"}


def _reason_counts(report: dict[str, Any]) -> list[tuple[str, int]]:
    samples: list[Any] = []
    for key in ("skipped_sample", "skipped", "duplicate_sample"):
        value = report.get(key)
        if isinstance(value, list):
            samples.extend(value)
    counter: Counter[str] = Counter()
    for item in samples:
        if not isinstance(item, dict):
            continue
        reason = item.get("reason")
        if not reason and "duplicate_sample" in report and item in report.get("duplicate_sample", []):
            reason = "duplicate_existing_seed_row"
        counter[str(reason or "unspecified")] += 1
    return counter.most_common()


def _report_metrics(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {"exists": False}
    updated_rows = report.get("updated_rows")
    if isinstance(updated_rows, list):
        updated_count = len(updated_rows)
    elif isinstance(updated_rows, int):
        updated_count = updated_rows
    else:
        updated_count = len(report.get("updated") or []) if isinstance(report.get("updated"), list) else None
    skipped_rows = report.get("skipped_rows")
    if not isinstance(skipped_rows, int):
        skipped_value = report.get("skipped")
        skipped_rows = skipped_value if isinstance(skipped_value, int) else len(report.get("skipped_sample") or [])
    duplicates = report.get("duplicates")
    if not isinstance(duplicates, int):
        duplicates = len(report.get("duplicate_sample") or [])
    return {
        "exists": True,
        "write": report.get("write"),
        "queue": _display_path(report.get("queue")),
        "updated_rows": updated_count or 0,
        "skipped_rows": skipped_rows,
        "duplicates": duplicates,
        "created_rows": len(report.get("created_rows") or []) if isinstance(report.get("created_rows"), list) else report.get("created"),
        "note": report.get("note"),
        "skip_reason_counts": _reason_counts(report),
    }


def audit_workflow(name: str, config: dict[str, Path | str]) -> dict[str, Any]:
    confirmed_path = config["confirmed"]
    template_path = config["template"]
    report_path = config["report"]
    assert isinstance(confirmed_path, Path)
    assert isinstance(template_path, Path)
    assert isinstance(report_path, Path)

    confirmed_data = _read_json(confirmed_path)
    template_data = _read_json(template_path)
    report_data = _read_json(report_path)
    confirmed_items = _items(confirmed_data)
    template_items = _items(template_data)
    confirmed_true = [item for item in confirmed_items if _confirmed(item.get("manual_confirmed"))]
    template_confirmed_true = [item for item in template_items if _confirmed(item.get("manual_confirmed"))]
    report = _report_metrics(report_data)

    status = "needs_manual_review"
    if confirmed_path.exists():
        if confirmed_true:
            if (report.get("updated_rows") or report.get("created_rows") or 0) > 0:
                status = "confirmed_rows_imported"
            elif (report.get("skipped_rows") or report.get("duplicates") or 0) > 0:
                status = "confirmed_rows_all_skipped"
            else:
                status = "confirmed_rows_pending_import"
        else:
            status = "confirmed_file_has_no_confirmed_rows"
    elif template_items:
        status = "template_ready_no_confirmed_file"

    return {
        "name": name,
        "description": config["description"],
        "confirmed_file": _display_path(confirmed_path),
        "confirmed_file_exists": confirmed_path.exists(),
        "template_file": _display_path(template_path),
        "template_file_exists": template_path.exists(),
        "review_artifact": _display_path(config["artifact"]),
        "confirmed_items": len(confirmed_items),
        "manual_confirmed_true": len(confirmed_true),
        "template_items": len(template_items),
        "template_manual_confirmed_true": len(template_confirmed_true),
        "import_report": report,
        "status": status,
        "dry_run_command": config.get("dry_run_command"),
        "write_command": config.get("write_command"),
        "next_action": _next_action(
            name,
            status,
            report,
            len(template_items),
            len(confirmed_true),
            str(config.get("dry_run_command") or ""),
            str(config.get("write_command") or ""),
        ),
    }


def _next_action(
    name: str,
    status: str,
    report: dict[str, Any],
    template_items: int,
    confirmed_true: int,
    dry_run_command: str = "",
    write_command: str = "",
) -> str:
    if status == "template_ready_no_confirmed_file":
        command = write_command or "the matching import tool with --write"
        return f"Copy the template to the confirmed_rows JSON, mark exact rows manual_confirmed=true, dry-run first, then run: {command}"
    if status == "confirmed_file_has_no_confirmed_rows":
        return "Open the confirmed file and mark only exact verified rows manual_confirmed=true, or replace it from the current template."
    if status == "confirmed_rows_pending_import":
        command = write_command or "the matching import tool with --write"
        dry_run = f" Dry-run: {dry_run_command}." if dry_run_command else ""
        return f"Run import for {confirmed_true} confirmed rows.{dry_run} Write: {command}"
    if status == "confirmed_rows_all_skipped":
        reasons = ", ".join(f"{reason}: {count}" for reason, count in report.get("skip_reason_counts", [])[:3])
        if not reasons and report.get("duplicates"):
            reasons = f"duplicates: {report.get('duplicates')}"
        return f"Review skipped rows before editing the queue again. Main reasons: {reasons or 'see import report'}."
    if status == "confirmed_rows_imported":
        return "Regenerate seed Dart, sync DB if needed, then rebuild/deploy the public site."
    if template_items:
        return "Review the generated template and confirm exact rows only."
    return f"No current {name} candidates were found."


def _display_path(value: Any) -> str | None:
    if value in (None, ""):
        return None
    path = Path(str(value))
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(value).replace("\\", "/")


def build() -> dict[str, Any]:
    workflows = [audit_workflow(name, config) for name, config in WORKFLOWS.items()]
    return {
        "workflows": workflows,
        "summary": {
            "workflow_count": len(workflows),
            "confirmed_files": sum(1 for item in workflows if item["confirmed_file_exists"]),
            "manual_confirmed_true": sum(int(item["manual_confirmed_true"]) for item in workflows),
            "template_items": sum(int(item["template_items"]) for item in workflows),
            "updated_rows": sum(int((item["import_report"].get("updated_rows") or 0)) for item in workflows),
            "skipped_rows": sum(int((item["import_report"].get("skipped_rows") or 0)) for item in workflows),
            "duplicates": sum(int((item["import_report"].get("duplicates") or 0)) for item in workflows),
        },
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# Confirmed Import Queue Audit",
        "",
        f"- Workflows: `{payload['summary']['workflow_count']}`",
        f"- Confirmed files: `{payload['summary']['confirmed_files']}`",
        f"- Manual confirmed rows: `{payload['summary']['manual_confirmed_true']}`",
        f"- Template candidate rows: `{payload['summary']['template_items']}`",
        f"- Imported/updated rows: `{payload['summary']['updated_rows']}`",
        f"- Skipped rows: `{payload['summary']['skipped_rows']}`",
        f"- Duplicate rows: `{payload['summary']['duplicates']}`",
        "",
    ]
    for item in payload["workflows"]:
        report = item["import_report"]
        lines.extend(
            [
                f"## {item['name']}",
                "",
                f"- Status: `{item['status']}`",
                f"- Review artifact: `{item['review_artifact']}`",
                f"- Confirmed file exists: `{item['confirmed_file_exists']}`",
                f"- Confirmed items: `{item['confirmed_items']}`",
                f"- Manual confirmed true: `{item['manual_confirmed_true']}`",
                f"- Template items: `{item['template_items']}`",
                f"- Import updated rows: `{report.get('updated_rows')}`",
                f"- Import skipped rows: `{report.get('skipped_rows')}`",
                f"- Import duplicates: `{report.get('duplicates')}`",
                f"- Dry-run command: `{item.get('dry_run_command')}`",
                f"- Write command: `{item.get('write_command')}`",
                f"- Next action: {item['next_action']}",
            ]
        )
        for reason, count in report.get("skip_reason_counts", [])[:10]:
            lines.append(f"- Skip reason `{reason}`: `{count}`")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    payload = build()
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown_output)
    print(
        json.dumps(
            {
                **payload["summary"],
                "json": str(args.json_output),
                "markdown": str(args.markdown_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
