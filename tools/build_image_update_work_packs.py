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
DEFAULT_QUEUE = ROOT / "server" / "catalog_image_enrichment_queue_current.json"
DEFAULT_OUTPUT_DIR = ROOT / "server" / "image_update_work_packs"
DEFAULT_MANIFEST = DEFAULT_OUTPUT_DIR / "manifest.json"


def load_queue(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    items = payload.get("items") or payload.get("queue") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        raise ValueError(f"{path} must contain an items or queue array")
    return [item for item in items if isinstance(item, dict)]


def slugify(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣ぁ-んァ-ン一-龯_-]+", "-", value.strip())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized[:80] or "pack"


def pack_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(item.get("automation_safety") or "manual_research_required"),
        str(item.get("strategy") or "manual_review"),
        str(item.get("source_store") or "unknown_store"),
        str(item.get("category") or "unknown_category"),
    )


def safety_rank(value: str) -> int:
    ranks = {
        "candidate_provider_script_required": 0,
        "manual_confirmation_required": 1,
        "detail_page_validation_required": 2,
        "safe_if_exact_image_or_jsonld": 3,
        "manual_research_required": 4,
        "blocked_until_exact_product_url": 5,
    }
    return ranks.get(value, 99)


def next_action(item: dict[str, Any]) -> str:
    safety = str(item.get("automation_safety") or "")
    strategy = str(item.get("strategy") or "")
    if safety == "candidate_provider_script_required":
        return "Find exact official detail pages, then create image update intake rows from confirmed image URLs."
    if safety == "manual_confirmation_required":
        return "Open each search URL manually and confirm the exact product before writing image_url."
    if safety == "detail_page_validation_required":
        return "Resolve the search result to a precise prize/detail page before attaching any image."
    if safety == "safe_if_exact_image_or_jsonld":
        return "Extract image_url from the existing exact source_url page metadata or product media."
    if strategy.startswith("source_url_"):
        return "Replace generic or ambiguous source_url with an exact product page before image attachment."
    return "Research official or trusted source evidence manually before creating image updates."


def target_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "catalog_index": item.get("row_index"),
        "name_ko": item.get("name_ko"),
        "name_ja": item.get("name_ja"),
        "name_en": item.get("name_en"),
        "category": item.get("category"),
        "affiliation": item.get("affiliation"),
        "source_store": item.get("source_store"),
        "source_url": item.get("source_url"),
        "query": item.get("query"),
        "search_url": item.get("search_url"),
        "required_update_shape": {
            "catalog_index": item.get("row_index"),
            "image_url": "https://...",
            "source_url": item.get("source_url") or "https://...",
            "evidence": [
                {
                    "url": item.get("source_url") or "https://...",
                    "type": "official",
                    "note": "Exact product/detail page or image media URL.",
                }
            ],
            "confidence": "confirmed",
            "notes": "",
        },
    }


def build_work_packs(items: list[dict[str, Any]], *, pack_size: int = 20, limit: int = 60) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[pack_key(item)].append(item)

    packs: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        automation_safety, strategy, source_store, category = key
        rows.sort(key=lambda item: (int(item.get("row_index") or 10**9), str(item.get("name_ja") or "")))
        chunk_count = (len(rows) + pack_size - 1) // pack_size
        for chunk_index in range(chunk_count):
            chunk = rows[chunk_index * pack_size : (chunk_index + 1) * pack_size]
            first = chunk[0]
            pack_id = slugify(
                f"{automation_safety}-{strategy}-{source_store}-{category}-{chunk_index + 1:02d}"
            )
            packs.append(
                {
                    "pack_id": pack_id,
                    "automation_safety": automation_safety,
                    "provider_status": first.get("provider_status"),
                    "strategy": strategy,
                    "source_store": source_store,
                    "category": category,
                    "priority": first.get("priority"),
                    "rows": len(chunk),
                    "total_group_rows": len(rows),
                    "chunk_index": chunk_index + 1,
                    "chunk_count": chunk_count,
                    "next_action": next_action(first),
                    "output_contract": (
                        "Save confirmed results as "
                        "data/intake/image_updates/incoming/<agent>-<YYYYMMDD>-<topic>.json "
                        "using agent_catalog_image_update.schema.json."
                    ),
                    "target_rows": [target_row(item) for item in chunk],
                }
            )

    packs.sort(
        key=lambda item: (
            safety_rank(str(item.get("automation_safety") or "")),
            int(item.get("priority") or 999),
            -int(item.get("total_group_rows") or 0),
            str(item.get("source_store") or ""),
            str(item.get("category") or ""),
            int(item.get("chunk_index") or 0),
        )
    )
    return packs[:limit]


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
                "automation_safety": pack["automation_safety"],
                "strategy": pack["strategy"],
                "source_store": pack["source_store"],
                "category": pack["category"],
            }
        )
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_queue": "server/catalog_image_enrichment_queue_current.json",
        "pack_count": len(packs),
        "target_rows": sum(int(pack.get("rows") or 0) for pack in packs),
        "output_contract": "Use data/intake/image_updates/incoming for confirmed image updates.",
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
    parser = argparse.ArgumentParser(description="Build agent work packs for missing catalog images.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--pack-size", type=int, default=20)
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()

    packs = build_work_packs(load_queue(args.queue), pack_size=args.pack_size, limit=args.limit)
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
