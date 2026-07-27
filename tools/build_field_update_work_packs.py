from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "server" / "catalog_field_enrichment_queue_current.json"
DEFAULT_OUTPUT_DIR = ROOT / "server" / "field_update_work_packs"
FIELD_UPDATE_INTAKE_DIR = "data/intake/field_updates/incoming"
FIELD_UPDATE_SCHEMA = "data/intake/field_updates/agent_catalog_field_update.schema.json"
FIELD_UPDATE_TEMPLATE = "data/intake/field_updates/templates/agent_catalog_field_update.template.json"
FIELD_UPDATE_IMPORTER = "tools/import_agent_catalog_field_updates.py"
SUPPORTED_FIELDS = {"source_url", "release_date", "barcode", "official_price_jpy"}


def load_queue(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    items = payload.get("queue") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain a queue array")
    return [item for item in items if isinstance(item, dict)]


def slugify(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣ぁ-んァ-ン一-龥]+", "-", value.strip())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized[:90] or "pack"


def pack_key(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(item.get("workstream") or "unknown_workstream"),
        str(item.get("source_store") or "unknown_store"),
        str(item.get("category") or "unknown_category"),
        str(item.get("field") or "unknown_field"),
        str(item.get("applicability") or "unknown_applicability"),
    )


def field_rank(field: str) -> int:
    return {
        "source_url": 0,
        "release_date": 1,
        "official_price_jpy": 2,
        "barcode": 3,
    }.get(field, 99)


def risk_rank(risk: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(risk, 9)


def include_item(item: dict[str, Any], *, include_non_actionable: bool) -> bool:
    field = str(item.get("field") or "")
    if field not in SUPPORTED_FIELDS:
        return False
    if include_non_actionable:
        return True
    return bool(item.get("actionable_now"))


def value_placeholder(field: str) -> Any:
    if field == "official_price_jpy":
        return 0
    if field == "release_date":
        return "YYYY-MM-DD"
    if field == "barcode":
        return "0000000000000"
    return "https://..."


def target_row(item: dict[str, Any]) -> dict[str, Any]:
    field = str(item.get("field") or "")
    evidence_url = item.get("source_url") or item.get("search_url") or "https://..."
    return {
        "catalog_index": item.get("row_index"),
        "field": field,
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "category": item.get("category"),
        "affiliation": item.get("affiliation"),
        "source_store": item.get("source_store"),
        "current_source_url": item.get("source_url"),
        "search_url": item.get("search_url"),
        "field_action": item.get("field_action"),
        "risk": item.get("risk"),
        "applicability": item.get("applicability"),
        "acceptance_criteria": [
            item.get("acceptance_criteria") or "Use exact official or trusted evidence.",
            "catalog_index must exist in data/catalog_public.json and the target field must still be empty.",
            "Set confidence=confirmed only after product, character, variant, and field value are verified.",
            "Do not submit image_url here; use data/intake/image_updates/incoming for images.",
        ],
        "required_update_shape": {
            "catalog_index": item.get("row_index"),
            "field": field,
            "value": value_placeholder(field),
            "evidence": [
                {
                    "url": evidence_url,
                    "type": "official",
                    "note": "Exact product/detail/campaign page used to verify this field.",
                }
            ],
            "confidence": "confirmed",
            "notes": "",
        },
        "validator_enforced": [
            "unknown fields rejected",
            "duplicate catalog_index/field rejected within one intake file",
            "catalog_index_not_found rejected",
            "already_filled_target_fields rejected",
            "source_url value must appear in evidence when field=source_url",
            "field-specific value shape checked for date, barcode, JPY price, and URL",
        ],
    }


def next_action(first: dict[str, Any]) -> str:
    field = str(first.get("field") or "")
    applicability = str(first.get("applicability") or "")
    if applicability != "actionable":
        return "Do not import yet; resolve applicability or stronger exact evidence first."
    if field == "source_url":
        return "Find exact product/detail/campaign URLs first; later image and metadata work depends on them."
    if field == "release_date":
        return "Copy the official release, sale, shipping, or campaign start date from exact source pages."
    if field == "official_price_jpy":
        return "Copy only the official JPY price; do not convert currencies or use resale listings."
    if field == "barcode":
        return "Copy only official JAN/barcode values; leave blank when not publicly published."
    return "Verify exact evidence and create confirmed field update intake rows."


def output_contract(source_store: str, category: str, field: str) -> dict[str, Any]:
    topic = slugify(f"{source_store}-{category}-{field}").lower()
    return {
        "intake_dir": FIELD_UPDATE_INTAKE_DIR,
        "filename_pattern": "<agent>-<YYYYMMDD>-<topic>.json",
        "example_filename": f"agent-20260727-{topic}.json",
        "schema": FIELD_UPDATE_SCHEMA,
        "template": FIELD_UPDATE_TEMPLATE,
        "allowed_confidence_for_import": "confirmed",
        "candidate_or_needs_review_policy": "Keep candidates in server review notes; do not submit them to incoming.",
    }


def verification_commands() -> list[str]:
    return [
        f"python -X utf8 tools/validate_agent_catalog_field_updates.py {FIELD_UPDATE_INTAKE_DIR}",
        f"python -X utf8 {FIELD_UPDATE_IMPORTER} {FIELD_UPDATE_INTAKE_DIR}",
        f"python -X utf8 {FIELD_UPDATE_IMPORTER} {FIELD_UPDATE_INTAKE_DIR} --write",
    ]


def build_work_packs(
    items: list[dict[str, Any]],
    *,
    pack_size: int = 25,
    limit: int = 80,
    include_non_actionable: bool = False,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        if include_item(item, include_non_actionable=include_non_actionable):
            grouped[pack_key(item)].append(item)

    packs: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        workstream, source_store, category, field, applicability = key
        rows.sort(key=lambda item: (int(item.get("priority") or 999), int(item.get("row_index") or 10**9)))
        chunk_count = (len(rows) + pack_size - 1) // pack_size
        for chunk_index in range(chunk_count):
            chunk = rows[chunk_index * pack_size : (chunk_index + 1) * pack_size]
            first = chunk[0]
            pack_id = slugify(
                f"{workstream}-{source_store}-{category}-{field}-{applicability}-{chunk_index + 1:02d}"
            )
            packs.append(
                {
                    "pack_id": pack_id,
                    "workstream": workstream,
                    "source_store": source_store,
                    "category": category,
                    "field": field,
                    "applicability": applicability,
                    "risk": first.get("risk"),
                    "strategy": first.get("strategy"),
                    "field_action": first.get("field_action"),
                    "automation_candidate": bool(first.get("automation_candidate")),
                    "rows": len(chunk),
                    "total_group_rows": len(rows),
                    "chunk_index": chunk_index + 1,
                    "chunk_count": chunk_count,
                    "next_action": next_action(first),
                    "output_contract": output_contract(source_store, category, field),
                    "verification_commands": verification_commands(),
                    "blocked_until": "confirmed_exact_field_update_intake_created",
                    "auto_apply_enabled": False,
                    "target_rows": [target_row(item) for item in chunk],
                }
            )

    packs.sort(
        key=lambda item: (
            field_rank(str(item.get("field") or "")),
            risk_rank(str(item.get("risk") or "")),
            0 if item.get("automation_candidate") else 1,
            -int(item.get("total_group_rows") or 0),
            str(item.get("source_store") or ""),
            str(item.get("category") or ""),
            int(item.get("chunk_index") or 0),
        )
    )
    return balanced_limit(packs, limit)


def balanced_limit(packs: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or len(packs) <= limit:
        return packs[:limit]

    by_field: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pack in packs:
        by_field[str(pack.get("field") or "")].append(pack)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    fields = [field for field in ("source_url", "release_date", "official_price_jpy", "barcode") if by_field.get(field)]

    cursor = 0
    while len(selected) < limit and any(by_field.get(field) for field in fields):
        field = fields[cursor % len(fields)]
        cursor += 1
        bucket = by_field.get(field) or []
        if not bucket:
            continue
        pack = bucket.pop(0)
        selected.append(pack)
        selected_ids.add(str(pack.get("pack_id") or ""))

    for pack in packs:
        if len(selected) >= limit:
            break
        pack_id = str(pack.get("pack_id") or "")
        if pack_id in selected_ids:
            continue
        selected.append(pack)
        selected_ids.add(pack_id)

    return selected


def write_packs(packs: list[dict[str, Any]], output_dir: Path, *, clean: bool = True) -> dict[str, Any]:
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pack_files: list[dict[str, Any]] = []
    for pack in packs:
        filename = f"{pack['pack_id']}.json"
        path = output_dir / filename
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        pack_files.append(
            {
                "pack_id": pack["pack_id"],
                "path": display_path(path),
                "rows": pack["rows"],
                "field": pack["field"],
                "risk": pack["risk"],
                "source_store": pack["source_store"],
                "category": pack["category"],
                "applicability": pack["applicability"],
            }
        )
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_queue": "server/catalog_field_enrichment_queue_current.json",
        "pack_count": len(packs),
        "target_rows": sum(int(pack.get("rows") or 0) for pack in packs),
        "output_contract": f"Use {FIELD_UPDATE_INTAKE_DIR} for confirmed field updates only.",
        "field_update_schema": FIELD_UPDATE_SCHEMA,
        "field_update_template": FIELD_UPDATE_TEMPLATE,
        "field_update_importer": FIELD_UPDATE_IMPORTER,
        "supported_fields": sorted(SUPPORTED_FIELDS),
        "verification_commands": verification_commands(),
        "automation_policy": {
            "auto_apply_catalog_changes": False,
            "candidate_or_needs_review_updates_are_not_imported": True,
            "requires_exact_product_identity": True,
            "requires_confirmed_intake_file": True,
            "image_url_updates_use_separate_image_intake": True,
        },
        "packs": pack_files,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build agent work packs for missing catalog fields.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pack-size", type=int, default=25)
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--include-non-actionable", action="store_true")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()

    packs = build_work_packs(
        load_queue(args.queue),
        pack_size=args.pack_size,
        limit=args.limit,
        include_non_actionable=args.include_non_actionable,
    )
    manifest = write_packs(packs, args.output_dir, clean=not args.no_clean)
    print(
        json.dumps(
            {
                "pack_count": manifest["pack_count"],
                "target_rows": manifest["target_rows"],
                "output_dir": str(args.output_dir),
                "manifest": str(args.output_dir / "manifest.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
