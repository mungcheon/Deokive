from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUALITY = ROOT / "server" / "catalog_quality_report.json"
DEFAULT_BACKLOG = ROOT / "server" / "catalog_update_backlog.json"
DEFAULT_IMAGE_MANIFEST = ROOT / "server" / "image_update_work_packs" / "manifest.json"
DEFAULT_FIELD_MANIFEST = ROOT / "server" / "field_update_work_packs" / "manifest.json"
DEFAULT_ICHIBAN_QUEUE = ROOT / "server" / "ichiban_public_quality_queue.json"
DEFAULT_REPORT = ROOT / "server" / "catalog_work_pack_coverage_audit.json"

FIELD_NAMES = ("source_url", "release_date", "barcode", "official_price_jpy")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_optional(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing required report: {display_path(path)}")
        return {}
    payload = read_json(path)
    if not isinstance(payload, dict):
        errors.append(f"{display_path(path)} must be a JSON object")
        return {}
    return payload


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def missing_enrichment(quality: dict[str, Any]) -> dict[str, int]:
    raw = quality.get("missing_enrichment")
    if not isinstance(raw, dict):
        return {}
    return {str(key): int(value) for key, value in raw.items() if isinstance(value, int)}


def image_pack_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    packs = [pack for pack in manifest.get("packs", []) if isinstance(pack, dict)]
    by_store: Counter[str] = Counter()
    by_strategy: Counter[str] = Counter()
    for pack in packs:
        rows = int(pack.get("rows") or 0)
        by_store[str(pack.get("source_store") or "")] += rows
        by_strategy[str(pack.get("strategy") or "")] += rows
    return {
        "pack_count": int(manifest.get("pack_count") or len(packs)),
        "target_rows": int(manifest.get("target_rows") or sum(int(pack.get("rows") or 0) for pack in packs)),
        "by_source_store": [{"source_store": key, "rows": value} for key, value in by_store.most_common(20)],
        "by_strategy": [{"strategy": key, "rows": value} for key, value in by_strategy.most_common(20)],
    }


def field_pack_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    packs = [pack for pack in manifest.get("packs", []) if isinstance(pack, dict)]
    by_field: Counter[str] = Counter()
    by_store: Counter[str] = Counter()
    by_risk: Counter[str] = Counter()
    for pack in packs:
        rows = int(pack.get("rows") or 0)
        by_field[str(pack.get("field") or "")] += rows
        by_store[str(pack.get("source_store") or "")] += rows
        by_risk[str(pack.get("risk") or "")] += rows
    return {
        "pack_count": int(manifest.get("pack_count") or len(packs)),
        "target_rows": int(manifest.get("target_rows") or sum(int(pack.get("rows") or 0) for pack in packs)),
        "by_field": {field: by_field.get(field, 0) for field in FIELD_NAMES},
        "by_source_store": [{"source_store": key, "rows": value} for key, value in by_store.most_common(20)],
        "by_risk": [{"risk": key, "rows": value} for key, value in by_risk.most_common(20)],
    }


def ichiban_summary(queue: dict[str, Any]) -> dict[str, Any]:
    summary = queue.get("summary") if isinstance(queue.get("summary"), dict) else {}
    return {
        "queue_rows": int(summary.get("queue_rows") or 0),
        "campaign_gap_queue_rows": int(summary.get("campaign_gap_queue_rows") or 0),
        "exact_display_duplicate_queue_rows": int(summary.get("exact_display_duplicate_queue_rows") or 0),
        "naming_convention_queue_rows": int(summary.get("naming_convention_queue_rows") or 0),
        "work_pack_rows": int(summary.get("work_pack_rows") or 0),
    }


def coverage_rows(missing: int, covered: int) -> dict[str, Any]:
    uncovered = max(missing - covered, 0)
    return {
        "missing": missing,
        "work_pack_target_rows": covered,
        "uncovered_or_deferred_rows": uncovered,
        "coverage_ratio": round(covered / missing, 4) if missing else 1.0,
    }


def audit(
    quality: dict[str, Any],
    backlog: dict[str, Any],
    image_manifest: dict[str, Any],
    field_manifest: dict[str, Any],
    ichiban_queue: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    missing = missing_enrichment(quality)
    image = image_pack_summary(image_manifest)
    field = field_pack_summary(field_manifest)
    ichiban = ichiban_summary(ichiban_queue)

    if image["target_rows"] > missing.get("image_url", 0):
        errors.append("image work-pack target rows exceed missing image_url count")
    for field_name, covered in field["by_field"].items():
        if covered > missing.get(field_name, 0):
            errors.append(f"{field_name} work-pack target rows exceed missing count")

    backlog_field_packs = backlog.get("field_update_work_packs")
    backlog_image_packs = backlog.get("image_work_packs")
    if isinstance(backlog_field_packs, list) and len(backlog_field_packs) > field["pack_count"]:
        errors.append("backlog field_update_work_packs count exceeds field manifest pack_count")
    if isinstance(backlog_image_packs, list) and len(backlog_image_packs) > image["pack_count"]:
        errors.append("backlog image_work_packs count exceeds image manifest pack_count")

    field_coverage = {
        field_name: coverage_rows(missing.get(field_name, 0), field["by_field"].get(field_name, 0))
        for field_name in FIELD_NAMES
    }
    report = {
        "rows": quality.get("rows"),
        "missing_enrichment": missing,
        "image_coverage": coverage_rows(missing.get("image_url", 0), image["target_rows"]),
        "field_coverage": field_coverage,
        "image_work_packs": image,
        "field_update_work_packs": field,
        "ichiban_quality": ichiban,
        "backlog_summary": {
            "field_update_work_pack_rows": len(backlog_field_packs) if isinstance(backlog_field_packs, list) else 0,
            "image_work_pack_rows": len(backlog_image_packs) if isinstance(backlog_image_packs, list) else 0,
            "ichiban_work_pack_rows": (backlog.get("ichiban_quality") or {}).get("work_pack_rows")
            if isinstance(backlog.get("ichiban_quality"), dict)
            else None,
        },
        "next_focus": next_focus(missing, image, field, ichiban),
        "status": "fail" if errors else "pass",
        "errors": errors,
    }
    return report, errors


def next_focus(
    missing: dict[str, int],
    image: dict[str, Any],
    field: dict[str, Any],
    ichiban: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    image_missing = missing.get("image_url", 0)
    image_uncovered = max(image_missing - int(image.get("target_rows") or 0), 0)
    candidates.append(
        {
            "workstream": "image_url",
            "uncovered_or_deferred_rows": image_uncovered,
            "next_action": "Expand image work packs after current confirmed-image handoff batches are reviewed.",
        }
    )
    for field_name in FIELD_NAMES:
        missing_count = missing.get(field_name, 0)
        covered = int((field.get("by_field") or {}).get(field_name, 0))
        candidates.append(
            {
                "workstream": field_name,
                "uncovered_or_deferred_rows": max(missing_count - covered, 0),
                "next_action": field_next_action(field_name),
            }
        )
    candidates.append(
        {
            "workstream": "ichiban_quality",
            "uncovered_or_deferred_rows": int(ichiban.get("queue_rows") or 0),
            "next_action": "Resolve campaign gaps, duplicate/reissue decisions, and naming policy queues before bulk historical imports.",
        }
    )
    candidates.sort(key=lambda item: (-int(item["uncovered_or_deferred_rows"]), str(item["workstream"])))
    return candidates


def field_next_action(field_name: str) -> str:
    if field_name == "source_url":
        return "Prioritize exact source URLs because they unlock later image and metadata imports."
    if field_name == "release_date":
        return "Backfill from exact product or campaign pages after source URLs are confirmed."
    if field_name == "official_price_jpy":
        return "Backfill only official Japanese prices; keep KRW or resale prices out."
    if field_name == "barcode":
        return "Treat as manual/high-risk and fill only where official JAN/barcode values are published."
    return "Review exact evidence before creating confirmed field update intake."


def run_audit(
    quality_path: Path = DEFAULT_QUALITY,
    backlog_path: Path = DEFAULT_BACKLOG,
    image_manifest_path: Path = DEFAULT_IMAGE_MANIFEST,
    field_manifest_path: Path = DEFAULT_FIELD_MANIFEST,
    ichiban_queue_path: Path = DEFAULT_ICHIBAN_QUEUE,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    quality = load_optional(quality_path, errors)
    backlog = load_optional(backlog_path, errors)
    image_manifest = load_optional(image_manifest_path, errors)
    field_manifest = load_optional(field_manifest_path, errors)
    ichiban_queue = load_optional(ichiban_queue_path, errors)
    if errors:
        return {"status": "fail", "errors": errors}, errors
    return audit(quality, backlog, image_manifest, field_manifest, ichiban_queue)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Deokive catalog work-pack coverage.")
    parser.add_argument("--quality", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--backlog", type=Path, default=DEFAULT_BACKLOG)
    parser.add_argument("--image-manifest", type=Path, default=DEFAULT_IMAGE_MANIFEST)
    parser.add_argument("--field-manifest", type=Path, default=DEFAULT_FIELD_MANIFEST)
    parser.add_argument("--ichiban-queue", type=Path, default=DEFAULT_ICHIBAN_QUEUE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    report, errors = run_audit(
        args.quality,
        args.backlog,
        args.image_manifest,
        args.field_manifest,
        args.ichiban_queue,
    )
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
