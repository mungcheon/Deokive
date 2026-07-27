from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTAKE = ROOT / "data" / "intake" / "incoming"

CONFIDENCE_VALUES = {"confirmed", "candidate", "needs_review"}
EVIDENCE_TYPES = {"official", "trusted", "manual"}
DATE_RE = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require_string(
    errors: list[str],
    item_path: str,
    payload: dict[str, object],
    key: str,
    *,
    allow_empty: bool = False,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        errors.append(f"{item_path}.{key}: expected string")
        return ""
    if not allow_empty and not value.strip():
        errors.append(f"{item_path}.{key}: must not be empty")
    return value


def validate_item(
    errors: list[str],
    item: object,
    item_path: str,
    seen_keys: set[tuple[str, str]],
) -> None:
    if not isinstance(item, dict):
        errors.append(f"{item_path}: expected object")
        return

    required = [
        "external_id",
        "display_name",
        "category",
        "series_name",
        "source_store",
        "source_url",
        "confidence",
    ]
    for key in required:
        require_string(errors, item_path, item, key)

    source_url = item.get("source_url")
    if isinstance(source_url, str) and source_url.strip() and not is_url(source_url):
        errors.append(f"{item_path}.source_url: expected http(s) product/detail URL")

    image_url = item.get("image_url")
    if image_url is not None:
        if not isinstance(image_url, str):
            errors.append(f"{item_path}.image_url: expected string when present")
        elif image_url.strip() and not is_url(image_url):
            errors.append(f"{item_path}.image_url: expected http(s) URL")

    release_date = item.get("release_date")
    if release_date is not None:
        if not isinstance(release_date, str):
            errors.append(f"{item_path}.release_date: expected string when present")
        elif release_date.strip() and not DATE_RE.match(release_date.strip()):
            errors.append(f"{item_path}.release_date: expected YYYY, YYYY-MM, or YYYY-MM-DD")

    price = item.get("official_price_jpy")
    if price is not None:
        if not isinstance(price, int) or isinstance(price, bool):
            errors.append(f"{item_path}.official_price_jpy: expected integer yen or null")
        elif price < 0:
            errors.append(f"{item_path}.official_price_jpy: must be >= 0")

    barcode = item.get("barcode")
    if barcode is not None and not isinstance(barcode, str):
        errors.append(f"{item_path}.barcode: expected string or null")

    confidence = item.get("confidence")
    if isinstance(confidence, str) and confidence not in CONFIDENCE_VALUES:
        errors.append(
            f"{item_path}.confidence: expected one of {', '.join(sorted(CONFIDENCE_VALUES))}"
        )

    evidence = item.get("evidence", [])
    if evidence is not None:
        if not isinstance(evidence, list):
            errors.append(f"{item_path}.evidence: expected array")
        else:
            for evidence_index, evidence_row in enumerate(evidence):
                evidence_path = f"{item_path}.evidence[{evidence_index}]"
                if not isinstance(evidence_row, dict):
                    errors.append(f"{evidence_path}: expected object")
                    continue
                url = require_string(errors, evidence_path, evidence_row, "url")
                if url and not is_url(url):
                    errors.append(f"{evidence_path}.url: expected http(s) URL")
                evidence_type = require_string(errors, evidence_path, evidence_row, "type")
                if evidence_type and evidence_type not in EVIDENCE_TYPES:
                    errors.append(
                        f"{evidence_path}.type: expected one of {', '.join(sorted(EVIDENCE_TYPES))}"
                    )

    duplicate_key = (
        str(item.get("source_store", "")).strip().casefold(),
        str(item.get("external_id", "")).strip().casefold(),
    )
    if duplicate_key in seen_keys:
        errors.append(f"{item_path}: duplicate source_store/external_id in this intake file")
    seen_keys.add(duplicate_key)


def validate_payload(path: Path, payload: object) -> tuple[list[str], dict[str, int | str]]:
    errors: list[str] = []
    summary: dict[str, int | str] = {"path": str(path), "items": 0}

    if not isinstance(payload, dict):
        return [f"{path}: expected top-level object"], summary

    if payload.get("schema_version") != 1:
        errors.append("schema_version: expected 1")

    agent = payload.get("agent")
    if not isinstance(agent, dict):
        errors.append("agent: expected object")
    else:
        require_string(errors, "agent", agent, "name")
        require_string(errors, "agent", agent, "run_id")
        require_string(errors, "agent", agent, "collected_at")

    items = payload.get("items")
    if not isinstance(items, list):
        errors.append("items: expected array")
        return errors, summary
    if not items:
        errors.append("items: must contain at least one item")
    summary["items"] = len(items)

    seen_keys: set[tuple[str, str]] = set()
    for index, item in enumerate(items):
        validate_item(errors, item, f"items[{index}]", seen_keys)

    return errors, summary


def iter_input_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        else:
            files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Deokive agent goods intake JSON files."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_INTAKE],
        help="Intake JSON file(s) or directories. Defaults to data/intake/incoming.",
    )
    args = parser.parse_args()

    files = iter_input_files(args.paths)
    if not files:
        print("No intake JSON files found.")
        return 0

    total_items = 0
    failed = False
    for path in files:
        try:
            payload = load_json(path)
        except json.JSONDecodeError as exc:
            print(f"{path}: invalid JSON: {exc}", file=sys.stderr)
            failed = True
            continue
        errors, summary = validate_payload(path, payload)
        total_items += int(summary["items"])
        if errors:
            failed = True
            print(f"{path}: FAILED ({len(errors)} issue(s))", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
        else:
            print(f"{path}: OK ({summary['items']} item(s))")

    print(f"Validated {len(files)} file(s), {total_items} item(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
