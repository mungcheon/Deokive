from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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
DEFAULT_SEED = ROOT / "lib" / "data" / "catalog" / "seed_catalog.dart"


def _load_public_rows(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise SystemExit(f"{path} must contain a list or an object with items")
    return [row for row in rows if isinstance(row, dict)]


def expected_seed_text(catalog_path: Path) -> str:
    rows = _load_public_rows(catalog_path)
    catalog_path = catalog_path.resolve()
    try:
        source_label = catalog_path.relative_to(ROOT).as_posix()
    except ValueError:
        source_label = catalog_path.as_posix()
    return generate(rows, source_label=source_label)


def audit(catalog_path: Path, seed_path: Path) -> dict[str, object]:
    expected = expected_seed_text(catalog_path)
    actual = seed_path.read_text(encoding="utf-8")
    expected_lines = expected.splitlines()
    actual_lines = actual.splitlines()
    first_diff_line: int | None = None
    for index, (left, right) in enumerate(zip(expected_lines, actual_lines), start=1):
        if left != right:
            first_diff_line = index
            break
    if first_diff_line is None and len(expected_lines) != len(actual_lines):
        first_diff_line = min(len(expected_lines), len(actual_lines)) + 1
    return {
        "catalog": str(catalog_path),
        "seed": str(seed_path),
        "catalog_rows": len(_load_public_rows(catalog_path)),
        "seed_entries": actual.count("GoodsCatalogEntry("),
        "matches": actual == expected,
        "first_diff_line": first_diff_line,
        "expected_line_count": len(expected_lines),
        "actual_line_count": len(actual_lines),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Flutter's bundled catalog seed matches data/catalog_public.json."
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    args = parser.parse_args()

    result = audit(args.catalog, args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["matches"]:
        raise SystemExit(
            "Flutter catalog seed is stale. Run: "
            "python -X utf8 tools/generate_seed_catalog_dart.py "
            "--input data/catalog_public.json "
            "--output lib/data/catalog/seed_catalog.dart"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
