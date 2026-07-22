from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_OUTPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_META_OUTPUT = ROOT / "data" / "catalog_public_meta.json"
DEFAULT_REFERENCE_META = ROOT / "data" / "catalog_public_meta.json"

PUBLIC_FIELDS = [
    "catalog_index",
    "name_ko",
    "name_ja",
    "name_en",
    "category",
    "character_name",
    "affiliation",
    "series_name",
    "sub_series",
    "official_price_jpy",
    "official_price_krw",
    "barcode",
    "image_url",
    "local_image_path",
    "source_url",
    "source_store",
    "release_date",
]

INT_FIELDS = {"catalog_index", "official_price_jpy", "official_price_krw"}

PRIVACY_FLAGS = {
    "contains_user_accounts": False,
    "contains_local_folders": False,
    "contains_private_memos": False,
    "contains_device_profiles": False,
    "contains_server_tokens": False,
}


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    try:
        number = int(value)
    except (TypeError, ValueError):
        return value
    return number


def _clean_field_value(field: str, value: Any) -> Any:
    if field in INT_FIELDS:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return _clean_value(value)


def export_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        public_row: dict[str, Any] = {}
        for field in PUBLIC_FIELDS:
            if field == "catalog_index":
                public_row[field] = row.get(field, index)
                continue
            value = _clean_field_value(field, row.get(field))
            if value is not None:
                public_row[field] = value
        public_rows.append(public_row)
    return public_rows


def build_meta(rows: list[dict[str, Any]], *, source: Path, generated_at: str | None = None) -> dict[str, Any]:
    generated = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    source_path = source.relative_to(ROOT) if source.is_relative_to(ROOT) else source
    missing = {
        field: sum(1 for row in rows if row.get(field) in (None, ""))
        for field in PUBLIC_FIELDS
        if field != "catalog_index"
    }
    return {
        "schema_version": 1,
        "generated_at": generated,
        "source": source_path.as_posix(),
        "row_count": len(rows),
        "fields": PUBLIC_FIELDS,
        "missing": missing,
        "privacy": dict(PRIVACY_FLAGS),
    }


def read_seed(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list):
        raise SystemExit(f"{path} must contain a JSON list")
    return [row for row in data if isinstance(row, dict)]


def reference_row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        for key in ("row_count", "total_items"):
            value = data.get(key)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def validate_row_count(
    rows: list[dict[str, Any]],
    *,
    reference_meta: Path,
    allow_row_count_drop: bool = False,
) -> None:
    if allow_row_count_drop:
        return
    expected = reference_row_count(reference_meta)
    if expected is None:
        return
    actual = len(rows)
    if actual < expected:
        raise SystemExit(
            "refusing to export a smaller public catalog: "
            f"input rows={actual}, reference rows={expected}, "
            f"reference={reference_meta}. "
            "Pass --allow-row-count-drop only for an intentional dedupe/prune."
        )


def write_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--meta-output", type=Path, default=DEFAULT_META_OUTPUT)
    parser.add_argument("--reference-meta", type=Path, default=DEFAULT_REFERENCE_META)
    parser.add_argument("--allow-row-count-drop", action="store_true")
    parser.add_argument("--generated-at", default=None)
    args = parser.parse_args()

    rows = read_seed(args.input)
    validate_row_count(
        rows,
        reference_meta=args.reference_meta,
        allow_row_count_drop=args.allow_row_count_drop,
    )
    public_rows = export_rows(rows)
    meta = build_meta(public_rows, source=args.input, generated_at=args.generated_at)
    write_json(args.output, {"meta": meta, "items": public_rows}, compact=True)
    write_json(args.meta_output, meta)
    print(
        json.dumps(
            {
                "rows": len(public_rows),
                "output": str(args.output),
                "meta_output": str(args.meta_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
