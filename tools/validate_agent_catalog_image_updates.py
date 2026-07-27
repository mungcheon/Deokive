from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTAKE = ROOT / "data" / "intake" / "image_updates" / "incoming"

CONFIDENCE_VALUES = {"confirmed", "candidate", "needs_review"}
EVIDENCE_TYPES = {"official", "trusted", "manual"}
TOP_LEVEL_FIELDS = {"schema_version", "agent", "updates"}
AGENT_FIELDS = {"name", "run_id", "collected_at", "notes"}
UPDATE_FIELDS = {"catalog_index", "image_url", "source_url", "evidence", "confidence", "notes"}
EVIDENCE_FIELDS = {"url", "type", "note"}


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def validate_update(
    errors: list[str],
    update: object,
    item_path: str,
    seen_indexes: set[int],
) -> None:
    if not isinstance(update, dict):
        errors.append(f"{item_path}: expected object")
        return
    reject_unknown_fields(errors, item_path, update, UPDATE_FIELDS)

    catalog_index = update.get("catalog_index")
    if not isinstance(catalog_index, int) or isinstance(catalog_index, bool):
        errors.append(f"{item_path}.catalog_index: expected integer")
    elif catalog_index in seen_indexes:
        errors.append(f"{item_path}.catalog_index: duplicate catalog_index in this update file")
    else:
        seen_indexes.add(catalog_index)

    image_url = require_string(errors, item_path, update, "image_url")
    if image_url and not is_url(image_url):
        errors.append(f"{item_path}.image_url: expected http(s) image URL")

    source_url = update.get("source_url")
    if source_url is not None:
        if not isinstance(source_url, str):
            errors.append(f"{item_path}.source_url: expected string when present")
        elif source_url.strip() and not is_url(source_url):
            errors.append(f"{item_path}.source_url: expected http(s) product/detail URL")

    confidence = update.get("confidence")
    if not isinstance(confidence, str):
        errors.append(f"{item_path}.confidence: expected string")
    elif confidence not in CONFIDENCE_VALUES:
        errors.append(
            f"{item_path}.confidence: expected one of {', '.join(sorted(CONFIDENCE_VALUES))}"
        )

    evidence = update.get("evidence")
    if not isinstance(evidence, list):
        errors.append(f"{item_path}.evidence: expected non-empty array")
        return
    if not evidence:
        errors.append(f"{item_path}.evidence: must contain at least one source row")
        return

    evidence_urls: set[str] = set()
    for evidence_index, evidence_row in enumerate(evidence):
        evidence_path = f"{item_path}.evidence[{evidence_index}]"
        if not isinstance(evidence_row, dict):
            errors.append(f"{evidence_path}: expected object")
            continue
        reject_unknown_fields(errors, evidence_path, evidence_row, EVIDENCE_FIELDS)
        url = require_string(errors, evidence_path, evidence_row, "url")
        if url:
            evidence_urls.add(url.rstrip("/"))
            if not is_url(url):
                errors.append(f"{evidence_path}.url: expected http(s) URL")
        evidence_type = require_string(errors, evidence_path, evidence_row, "type")
        if evidence_type and evidence_type not in EVIDENCE_TYPES:
            errors.append(
                f"{evidence_path}.type: expected one of {', '.join(sorted(EVIDENCE_TYPES))}"
            )

    source_in_evidence = bool(source_url and isinstance(source_url, str) and source_url.rstrip("/") in evidence_urls)
    image_in_evidence = bool(image_url and image_url.rstrip("/") in evidence_urls)
    if source_url and isinstance(source_url, str) and not source_in_evidence:
        errors.append(f"{item_path}.evidence: must include source_url")
    if image_url and not (image_in_evidence or source_in_evidence):
        errors.append(f"{item_path}.evidence: must include image_url or source_url")


def validate_payload(path: Path, payload: object) -> tuple[list[str], dict[str, int | str]]:
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

    seen_indexes: set[int] = set()
    for index, update in enumerate(updates):
        validate_update(errors, update, f"updates[{index}]", seen_indexes)
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
    parser = argparse.ArgumentParser(description="Validate Deokive catalog image update JSON files.")
    parser.add_argument("paths", nargs="*", type=Path, default=[DEFAULT_INTAKE])
    args = parser.parse_args()

    files = iter_input_files(args.paths)
    if not files:
        print("No image update JSON files found.")
        return 0

    total_updates = 0
    failed = False
    for path in files:
        try:
            payload = load_json(path)
        except json.JSONDecodeError as exc:
            print(f"{path}: invalid JSON: {exc}", file=sys.stderr)
            failed = True
            continue
        errors, summary = validate_payload(path, payload)
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
