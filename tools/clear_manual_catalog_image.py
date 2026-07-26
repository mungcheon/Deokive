from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from generate_seed_catalog_dart import generate
except ModuleNotFoundError:
    from tools.generate_seed_catalog_dart import generate

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_SEED_OUTPUT = ROOT / "lib" / "data" / "catalog" / "seed_catalog.dart"


def _replace_one_line_json_object(text: str, catalog_index: int, updates: dict[str, Any]) -> str:
    pattern = re.compile(rf'\{{"catalog_index":{catalog_index},[^{{}}]*\}}')
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"catalog_index {catalog_index} was not found")
    row = json.loads(match.group(0))
    before = dict(row)
    for key, value in updates.items():
        if value is None:
            row.pop(key, None)
        else:
            row[key] = value
    if before == row:
        return text
    encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
    return text[: match.start()] + encoded + text[match.end() :]


def _sync_flutter_seed(catalog: Path, output: Path) -> None:
    payload = json.loads(catalog.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{catalog} must contain a JSON list or an object with items")
    try:
        source_label = catalog.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        source_label = catalog.resolve().as_posix()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        generate([row for row in rows if isinstance(row, dict)], source_label=source_label),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clear a public catalog row image_url/local_image_path after exact mismatch review."
    )
    parser.add_argument("catalog_index", type=int)
    parser.add_argument("--expect-name", default=None)
    parser.add_argument("--note", default="")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--seed-output", type=Path, default=DEFAULT_SEED_OUTPUT)
    parser.add_argument("--skip-seed-sync", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    text = args.catalog.read_text(encoding="utf-8")
    match = re.search(rf'\{{"catalog_index":{args.catalog_index},[^{{}}]*\}}', text)
    if not match:
        raise SystemExit(f"catalog_index {args.catalog_index} was not found")
    current_row = json.loads(match.group(0))
    current_name = " ".join(
        str(current_row.get(key) or "") for key in ("name_ko", "name_ja", "name_en")
    )
    if args.expect_name and args.expect_name not in current_name:
        raise SystemExit(
            f"catalog_index {args.catalog_index} name mismatch: "
            f"expected to contain {args.expect_name!r}, got {current_name!r}"
        )

    updated_text = _replace_one_line_json_object(
        text,
        args.catalog_index,
        {"image_url": None, "local_image_path": None},
    )
    if args.write:
        args.catalog.write_text(updated_text, encoding="utf-8")
        if not args.skip_seed_sync:
            _sync_flutter_seed(args.catalog, args.seed_output)

    print(
        json.dumps(
            {
                "catalog_index": args.catalog_index,
                "removed_fields": ["image_url", "local_image_path"],
                "note": args.note,
                "flutter_seed_synced": bool(args.write and not args.skip_seed_sync),
                "write": args.write,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.write:
        print("Dry run only. Re-run with --write to update files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
