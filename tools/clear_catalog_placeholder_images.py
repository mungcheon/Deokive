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
DEFAULT_PLACEHOLDER_URLS = {
    "https://online-kuji.chiikawamarket.jp/assets/images/ogp.png",
}


def _one_line_objects(text: str) -> list[tuple[int, int, dict[str, Any]]]:
    rows: list[tuple[int, int, dict[str, Any]]] = []
    for match in re.finditer(r'\{"catalog_index":\d+,[^\{\}]*\}', text):
        rows.append((match.start(), match.end(), json.loads(match.group(0))))
    return rows


def clear_placeholder_images(
    text: str,
    placeholder_urls: set[str],
    *,
    clear_source_url: bool = False,
) -> tuple[str, list[dict[str, Any]]]:
    replacements: list[tuple[int, int, str]] = []
    cleared: list[dict[str, Any]] = []
    for start, end, row in _one_line_objects(text):
        image_url = str(row.get("image_url") or "")
        if image_url not in placeholder_urls:
            continue
        before = {
            "catalog_index": row.get("catalog_index"),
            "name_ko": row.get("name_ko"),
            "image_url": row.get("image_url"),
            "local_image_path": row.get("local_image_path"),
            "source_url": row.get("source_url"),
        }
        row["image_url"] = None
        row["local_image_path"] = None
        if clear_source_url:
            row["source_url"] = None
        cleared.append(before)
        replacements.append((start, end, json.dumps(row, ensure_ascii=False, separators=(",", ":"))))

    if not replacements:
        return text, []

    parts: list[str] = []
    cursor = 0
    for start, end, replacement in replacements:
        parts.append(text[cursor:start])
        parts.append(replacement)
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), cleared


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
    parser = argparse.ArgumentParser(description="Clear known non-product placeholder images from catalog rows.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--seed-output", type=Path, default=DEFAULT_SEED_OUTPUT)
    parser.add_argument("--placeholder-url", action="append", default=[])
    parser.add_argument(
        "--clear-source-url",
        action="store_true",
        help="Also clear source_url for rows whose image URL is known to belong to the wrong product.",
    )
    parser.add_argument("--skip-seed-sync", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    placeholder_urls = set(DEFAULT_PLACEHOLDER_URLS)
    placeholder_urls.update(url.strip() for url in args.placeholder_url if url.strip())
    text = args.catalog.read_text(encoding="utf-8")
    updated_text, cleared = clear_placeholder_images(
        text,
        placeholder_urls,
        clear_source_url=args.clear_source_url,
    )

    if args.write and cleared:
        args.catalog.write_text(updated_text, encoding="utf-8")
        if not args.skip_seed_sync:
            _sync_flutter_seed(args.catalog, args.seed_output)

    print(
        json.dumps(
            {
                "catalog": str(args.catalog.relative_to(ROOT)) if args.catalog.is_relative_to(ROOT) else str(args.catalog),
                "placeholder_urls": sorted(placeholder_urls),
                "clear_source_url": args.clear_source_url,
                "cleared_rows": len(cleared),
                "sample": cleared[:20],
                "flutter_seed_synced": bool(args.write and cleared and not args.skip_seed_sync),
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
