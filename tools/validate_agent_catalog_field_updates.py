from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTAKE = ROOT / "data" / "intake" / "field_updates" / "incoming"
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"

CONFIDENCE_VALUES = {"confirmed", "candidate", "needs_review"}
EVIDENCE_TYPES = {"official", "trusted", "manual"}
FIELD_NAMES = {
    "source_url",
    "release_date",
    "barcode",
    "official_price",
    "official_price_currency",
    "official_price_jpy",
    "name_ja",
    "name_en",
    "name_ko",
    "character_name",
    "sub_series",
}
PRICE_CURRENCIES = {"JPY", "KRW", "USD", "CNY", "TWD"}
DATE_RE = re.compile(r"^\d{4}(?:-\d{2}(?:-\d{2})?)?$")
BARCODE_RE = re.compile(r"^\d{8,14}$")
FRIEREN_KO = "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c"
FERN_JA = "\u30d5\u30a7\u30eb\u30f3"
FERN_CANONICAL_KO = "\ud398\ub978"
FERN_BAD_KO_ALIASES = ("\ud380", "\ud38c", "\ud504\ub80c", "Fern", "Pern")
TOP_LEVEL_FIELDS = {"schema_version", "agent", "updates"}
AGENT_FIELDS = {"name", "run_id", "collected_at", "notes"}
UPDATE_FIELDS = {"catalog_index", "field", "value", "evidence", "confidence", "notes"}
EVIDENCE_FIELDS = {"url", "type", "note"}


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def present(value: object) -> bool:
    return value is not None and str(value).strip() != ""


def catalog_index(items: object) -> dict[int, dict[str, object]]:
    if not isinstance(items, list):
        return {}
    rows: dict[int, dict[str, object]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        index = item.get("catalog_index")
        if isinstance(index, int) and not isinstance(index, bool):
            rows[index] = item
    return rows


def load_catalog_index(path: Path) -> dict[int, dict[str, object]]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected catalog object")
    return catalog_index(payload.get("items"))


def reject_unknown_fields(
    errors: list[str],
    item_path: str,
    payload: dict[str, object],
    allowed_fields: set[str],
) -> None:
    unknown = sorted(str(key) for key in payload if key not in allowed_fields)
    if unknown:
        errors.append(f"{item_path}: unknown field(s): {', '.join(unknown)}")


def require_string(errors: list[str], item_path: str, payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        errors.append(f"{item_path}.{key}: expected string")
        return ""
    if not value.strip():
        errors.append(f"{item_path}.{key}: must not be empty")
    return value


def is_iso_timestamp(value: str) -> bool:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt.datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def clean_text(value: object) -> str:
    return str(value or "").strip()


def validate_value(errors: list[str], item_path: str, field: str, value: object) -> None:
    if field in {"official_price", "official_price_jpy"}:
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{item_path}.value: expected integer for {field}")
        elif value < 0:
            errors.append(f"{item_path}.value: must be >= 0")
        return
    if field == "official_price_currency":
        if value not in PRICE_CURRENCIES:
            errors.append(
                f"{item_path}.value: expected one of {', '.join(sorted(PRICE_CURRENCIES))}"
            )
        return
    if field == "barcode":
        text = clean_text(value)
        if not BARCODE_RE.match(text):
            errors.append(f"{item_path}.value: expected 8-14 digit barcode")
        return
    if field == "release_date":
        text = clean_text(value)
        if not DATE_RE.match(text):
            errors.append(f"{item_path}.value: expected YYYY, YYYY-MM, or YYYY-MM-DD")
        return
    text = clean_text(value)
    if not text:
        errors.append(f"{item_path}.value: must not be empty")
        return
    if field == "source_url" and not is_url(text):
        errors.append(f"{item_path}.value: expected http(s) product/detail URL")


def validate_character_alias_value(
    errors: list[str],
    item_path: str,
    update: dict[str, object],
    catalog_row: dict[str, object] | None,
) -> None:
    field = update.get("field")
    if field not in {"name_ko", "character_name", "sub_series"}:
        return
    value = clean_text(update.get("value"))
    row_context = json.dumps(catalog_row or {}, ensure_ascii=False)
    update_context = " ".join(
        [
            value,
            clean_text((catalog_row or {}).get("name_ja")),
            clean_text((catalog_row or {}).get("affiliation")),
            clean_text((catalog_row or {}).get("series_name")),
            clean_text((catalog_row or {}).get("sub_series")),
            clean_text((catalog_row or {}).get("character_name")),
        ]
    )
    is_frieren_context = FRIEREN_KO in update_context or FERN_JA in row_context
    if not is_frieren_context:
        return
    for alias in FERN_BAD_KO_ALIASES:
        if alias in value:
            errors.append(
                f"{item_path}.value: Fern/Frieren Korean aliases must use {FERN_CANONICAL_KO}, not {alias}"
            )
            return


def validate_evidence(
    errors: list[str],
    item_path: str,
    update: dict[str, object],
) -> None:
    evidence = update.get("evidence")
    if not isinstance(evidence, list):
        errors.append(f"{item_path}.evidence: expected non-empty array")
        return
    if not evidence:
        errors.append(f"{item_path}.evidence: must contain at least one source row")
        return

    urls: set[str] = set()
    for evidence_index, evidence_row in enumerate(evidence):
        evidence_path = f"{item_path}.evidence[{evidence_index}]"
        if not isinstance(evidence_row, dict):
            errors.append(f"{evidence_path}: expected object")
            continue
        reject_unknown_fields(errors, evidence_path, evidence_row, EVIDENCE_FIELDS)
        url = require_string(errors, evidence_path, evidence_row, "url")
        if url:
            urls.add(url.rstrip("/"))
            if not is_url(url):
                errors.append(f"{evidence_path}.url: expected http(s) URL")
        evidence_type = require_string(errors, evidence_path, evidence_row, "type")
        if evidence_type and evidence_type not in EVIDENCE_TYPES:
            errors.append(
                f"{evidence_path}.type: expected one of {', '.join(sorted(EVIDENCE_TYPES))}"
            )
    if update.get("field") == "source_url":
        value = clean_text(update.get("value")).rstrip("/")
        if value and value not in urls:
            errors.append(f"{item_path}.evidence: must include the source_url value")


def validate_update(
    errors: list[str],
    update: object,
    item_path: str,
    seen_targets: set[tuple[int, str]],
    catalog_rows: dict[int, dict[str, object]] | None = None,
) -> None:
    if not isinstance(update, dict):
        errors.append(f"{item_path}: expected object")
        return
    reject_unknown_fields(errors, item_path, update, UPDATE_FIELDS)

    catalog_idx = update.get("catalog_index")
    field = update.get("field")
    if not isinstance(catalog_idx, int) or isinstance(catalog_idx, bool):
        errors.append(f"{item_path}.catalog_index: expected integer")
    if not isinstance(field, str):
        errors.append(f"{item_path}.field: expected string")
    elif field not in FIELD_NAMES:
        errors.append(f"{item_path}.field: unsupported field")

    if isinstance(catalog_idx, int) and not isinstance(catalog_idx, bool) and isinstance(field, str):
        target = (catalog_idx, field)
        if target in seen_targets:
            errors.append(f"{item_path}: duplicate catalog_index/field in this update file")
        seen_targets.add(target)
        if catalog_rows is not None:
            catalog_row = catalog_rows.get(catalog_idx)
            if catalog_row is None:
                errors.append(f"{item_path}.catalog_index: not found in catalog_public.json")
            elif field in FIELD_NAMES and present(catalog_row.get(field)):
                errors.append(f"{item_path}.{field}: target catalog field already has a value")
        else:
            catalog_row = None
    else:
        catalog_row = None

    if isinstance(field, str) and field in FIELD_NAMES:
        validate_value(errors, item_path, field, update.get("value"))
        validate_character_alias_value(errors, item_path, update, catalog_row)

    confidence = update.get("confidence")
    if not isinstance(confidence, str):
        errors.append(f"{item_path}.confidence: expected string")
    elif confidence not in CONFIDENCE_VALUES:
        errors.append(
            f"{item_path}.confidence: expected one of {', '.join(sorted(CONFIDENCE_VALUES))}"
        )

    validate_evidence(errors, item_path, update)


def validate_payload(
    path: Path,
    payload: object,
    *,
    catalog_rows: dict[int, dict[str, object]] | None = None,
) -> tuple[list[str], dict[str, int | str]]:
    errors: list[str] = []
    summary: dict[str, int | str] = {"path": str(path), "updates": 0}
    if not isinstance(payload, dict):
        return [f"{path}: expected top-level object"], summary
    reject_unknown_fields(errors, str(path), payload, TOP_LEVEL_FIELDS)

    if payload.get("schema_version") != 1:
        errors.append("schema_version: expected 1")

    agent = payload.get("agent")
    if not isinstance(agent, dict):
        errors.append("agent: expected object")
    else:
        reject_unknown_fields(errors, "agent", agent, AGENT_FIELDS)
        require_string(errors, "agent", agent, "name")
        require_string(errors, "agent", agent, "run_id")
        collected_at = require_string(errors, "agent", agent, "collected_at")
        if collected_at and not is_iso_timestamp(collected_at):
            errors.append("agent.collected_at: expected ISO-8601 timestamp")

    updates = payload.get("updates")
    if not isinstance(updates, list):
        errors.append("updates: expected array")
        return errors, summary
    if not updates:
        errors.append("updates: must contain at least one update")
    summary["updates"] = len(updates)

    seen_targets: set[tuple[int, str]] = set()
    for index, update in enumerate(updates):
        validate_update(errors, update, f"updates[{index}]", seen_targets, catalog_rows)
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
    parser = argparse.ArgumentParser(description="Validate Deokive catalog field update JSON files.")
    parser.add_argument("paths", nargs="*", type=Path, default=[DEFAULT_INTAKE])
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--skip-catalog-context", action="store_true")
    args = parser.parse_args()

    files = iter_input_files(args.paths)
    if not files:
        print("No field update JSON files found.")
        return 0

    catalog_rows = None
    if not args.skip_catalog_context:
        try:
            catalog_rows = load_catalog_index(args.catalog)
        except Exception as exc:
            print(f"{args.catalog}: failed to load catalog context: {exc}", file=sys.stderr)
            return 1

    failed = False
    total_updates = 0
    for path in files:
        try:
            payload = load_json(path)
        except json.JSONDecodeError as exc:
            print(f"{path}: invalid JSON: {exc}", file=sys.stderr)
            failed = True
            continue
        errors, summary = validate_payload(path, payload, catalog_rows=catalog_rows)
        total_updates += int(summary["updates"])
        if errors:
            failed = True
            print(f"{path}: FAILED ({len(errors)} issue(s))", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
        else:
            print(f"{path}: OK ({summary['updates']} update(s))")

    print(f"Validated {len(files)} file(s), {total_updates} update(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
