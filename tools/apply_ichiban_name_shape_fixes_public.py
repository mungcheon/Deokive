from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import audit_catalog_naming_public as naming_audit


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_CATALOG = DATA / "catalog_public.json"
DEFAULT_REPORT = DATA / "ichiban_name_shape_fixes_public.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"{path} must contain a JSON object with items")
    return payload


def build_fixed_name(row: dict[str, Any]) -> str | None:
    name = str(row.get("name_ko") or "").strip()
    parts = [part.strip() for part in name.split("/") if part.strip()]
    if len(parts) != 3:
        return None
    release_name, prize_rank, character_name = parts
    if character_name != str(row.get("character_name") or "").strip():
        return None
    product_name = str(row.get("name_ja") or row.get("sub_series") or prize_rank).strip()
    if not release_name or not prize_rank or not product_name or not character_name:
        return None
    return f"{release_name} / {prize_rank} / {product_name} / {character_name}"


def apply_fixes(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload["items"]
    changes: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        issues = naming_audit.audit_ichiban_names([row])
        reasons = {issue["reason"] for issue in issues}
        if "ichiban_name_missing_release_prize_item_character_parts" not in reasons:
            continue
        fixed_name = build_fixed_name(row)
        if not fixed_name or fixed_name == row.get("name_ko"):
            continue
        changes.append(
            {
                "catalog_index": row.get("catalog_index"),
                "name_ko": {"from": row.get("name_ko"), "to": fixed_name},
                "source_url": row.get("source_url"),
            }
        )
        row["name_ko"] = fixed_name
    return {
        "generated_at": now_utc(),
        "summary": {
            "updated_rows": len(changes),
            "auto_apply_enabled": True,
            "fix_scope": "ichiban_name_missing_item_part_only",
        },
        "changes": changes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    payload = load_payload(args.catalog)
    report = apply_fixes(payload)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if args.write:
        args.catalog.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
