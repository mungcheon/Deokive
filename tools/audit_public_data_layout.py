from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from validate_agent_goods_intake import iter_input_files, load_json, validate_payload
except ImportError:
    from tools.validate_agent_goods_intake import iter_input_files, load_json, validate_payload
try:
    from validate_agent_catalog_image_updates import (
        iter_input_files as iter_image_update_files,
        load_json as load_image_update_json,
        validate_payload as validate_image_update_payload,
    )
except ImportError:
    from tools.validate_agent_catalog_image_updates import (
        iter_input_files as iter_image_update_files,
        load_json as load_image_update_json,
        validate_payload as validate_image_update_payload,
    )
try:
    from validate_agent_catalog_field_updates import (
        iter_input_files as iter_field_update_files,
        load_json as load_field_update_json,
        validate_payload as validate_field_update_payload,
    )
except ImportError:
    from tools.validate_agent_catalog_field_updates import (
        iter_input_files as iter_field_update_files,
        load_json as load_field_update_json,
        validate_payload as validate_field_update_payload,
    )


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog_public.json"
CATALOG_META = DATA / "catalog_public_meta.json"
SITE_STATUS = DATA / "site_status_public.json"
INTAKE = DATA / "intake"
INCOMING = INTAKE / "incoming"
IMAGE_UPDATES_INCOMING = INTAKE / "image_updates" / "incoming"
FIELD_UPDATES_INCOMING = INTAKE / "field_updates" / "incoming"
SOURCES = INTAKE / "sources"
SERVER_ARTIFACT_SUFFIXES = {".csv", ".html", ".json", ".md", ".jpg", ".jpeg", ".png", ".txt"}
INTAKE_FILENAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*-\d{8}-[a-z0-9][a-z0-9_-]*\.json$")
PUBLIC_DATABASE_FILES = {"data/catalog_public.json"}

ALLOWED_DATA_FILES = {
    "data/README.md",
    "data/catalog_public.json",
    "data/catalog_public_meta.json",
    "data/site_status_public.json",
    "data/intake/README.md",
    "data/intake/agent_goods_intake.schema.json",
    "data/intake/image_updates/agent_catalog_image_update.schema.json",
    "data/intake/field_updates/agent_catalog_field_update.schema.json",
    "data/intake/field_updates/incoming/.gitkeep",
    "data/intake/field_updates/processed/.gitkeep",
    "data/intake/field_updates/rejected/.gitkeep",
    "data/intake/field_updates/templates/agent_catalog_field_update.template.json",
    "data/intake/image_updates/incoming/.gitkeep",
    "data/intake/image_updates/processed/.gitkeep",
    "data/intake/image_updates/rejected/.gitkeep",
    "data/intake/image_updates/templates/agent_catalog_image_update.template.json",
    "data/intake/incoming/.gitkeep",
    "data/intake/processed/.gitkeep",
    "data/intake/rejected/.gitkeep",
    "data/intake/sources/anymy_kuji_campaigns.json",
    "data/intake/sources/chiikawa_online_kuji_campaigns.json",
    "data/intake/sources/ichiban_kuji_campaigns.json",
    "data/intake/templates/agent_goods_intake.template.json",
}
ALLOWED_INTAKE_RECORD_DIRS = {
    "data/intake/incoming",
    "data/intake/processed",
    "data/intake/rejected",
    "data/intake/image_updates/incoming",
    "data/intake/image_updates/processed",
    "data/intake/image_updates/rejected",
    "data/intake/field_updates/incoming",
    "data/intake/field_updates/processed",
    "data/intake/field_updates/rejected",
}

REQUIRED_ITEM_FIELDS = {
    "catalog_index",
    "name_ko",
    "category",
    "character_name",
    "affiliation",
    "source_store",
}


def git_ls_files_data() -> list[str]:
    return git_ls_files("data")


def git_ls_files(pathspec: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", pathspec],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def iter_data_filesystem_files() -> list[str]:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in DATA.rglob("*")
        if path.is_file()
    )


def is_allowed_data_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized in ALLOWED_DATA_FILES:
        return True
    candidate = Path(normalized)
    parent = candidate.parent.as_posix()
    return (
        parent in ALLOWED_INTAKE_RECORD_DIRS
        and candidate.suffix.lower() == ".json"
        and candidate.name != ".gitkeep"
    )


def is_valid_intake_record_name(path: Path) -> bool:
    return bool(INTAKE_FILENAME_RE.match(path.name))


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def audit_tracked_data_files(errors: list[str]) -> list[str]:
    tracked = git_ls_files_data()
    unexpected = [path for path in tracked if not is_allowed_data_path(path)]
    database_files = [path for path in tracked if path in PUBLIC_DATABASE_FILES]
    missing = sorted(path for path in ALLOWED_DATA_FILES if path not in set(tracked))
    if unexpected:
        errors.append(
            "Unexpected tracked data files outside the single-DB/intake layout: "
            + ", ".join(unexpected[:20])
        )
    if database_files != sorted(PUBLIC_DATABASE_FILES):
        errors.append(
            "Public DB layout must expose exactly one database file: "
            + ", ".join(sorted(PUBLIC_DATABASE_FILES))
        )
    if missing:
        errors.append("Missing required tracked data files: " + ", ".join(missing))
    return tracked


def audit_tracked_server_artifacts(errors: list[str]) -> list[str]:
    tracked = git_ls_files("server")
    unexpected = [
        path
        for path in tracked
        if Path(path).suffix.lower() in SERVER_ARTIFACT_SUFFIXES
    ]
    if unexpected:
        errors.append(
            "Unexpected tracked server/local artifacts; keep public DB data under data/ only: "
            + ", ".join(unexpected[:20])
        )
    return tracked


def audit_data_filesystem_layout(errors: list[str]) -> dict[str, int]:
    files = iter_data_filesystem_files()
    unexpected = [path for path in files if not is_allowed_data_path(path)]
    if unexpected:
        errors.append(
            "Unexpected local data files outside the single-DB/intake layout: "
            + ", ".join(unexpected[:20])
        )
    return {"data_filesystem_files": len(files)}


def audit_catalog(errors: list[str]) -> dict[str, int]:
    payload = read_json(CATALOG)
    if not isinstance(payload, dict):
        errors.append("data/catalog_public.json must be a JSON object")
        return {"catalog_rows": 0}
    items = payload.get("items")
    if not isinstance(items, list):
        errors.append("data/catalog_public.json must contain an items list")
        return {"catalog_rows": 0}
    if not items:
        errors.append("data/catalog_public.json items must not be empty")
        return {"catalog_rows": 0}

    catalog_indexes: set[int] = set()
    duplicate_indexes: list[int] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"catalog item {index} must be an object")
            continue
        missing_fields = sorted(field for field in REQUIRED_ITEM_FIELDS if field not in item)
        if missing_fields:
            errors.append(f"catalog item {index} missing required fields: {', '.join(missing_fields)}")
        catalog_index = item.get("catalog_index")
        if not isinstance(catalog_index, int) or isinstance(catalog_index, bool):
            errors.append(f"catalog item {index} has non-integer catalog_index")
        elif catalog_index in catalog_indexes:
            duplicate_indexes.append(catalog_index)
        else:
            catalog_indexes.add(catalog_index)

    if duplicate_indexes:
        errors.append(
            "Duplicate catalog_index values: "
            + ", ".join(str(value) for value in duplicate_indexes[:20])
        )

    return {"catalog_rows": len(items)}


def audit_catalog_meta(errors: list[str], catalog_rows: int) -> None:
    meta = read_json(CATALOG_META)
    if not isinstance(meta, dict):
        errors.append("data/catalog_public_meta.json must be a JSON object")
        return
    if meta.get("source") != "data/catalog_public.json":
        errors.append("catalog_public_meta.source must be data/catalog_public.json")
    row_count = meta.get("row_count", meta.get("total_items"))
    if row_count != catalog_rows:
        errors.append(
            f"catalog_public_meta row count mismatch: expected {catalog_rows}, got {row_count}"
        )


def audit_site_status(errors: list[str]) -> None:
    status = read_json(SITE_STATUS)
    if not isinstance(status, dict):
        errors.append("data/site_status_public.json must be a JSON object")
        return
    mode = status.get("mode")
    if mode not in {"normal", "notice", "updating"}:
        errors.append("site_status_public.mode must be normal, notice, or updating")


def audit_intake_sources(errors: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(SOURCES.glob("*.json")):
        payload = read_json(path)
        if not isinstance(payload, list):
            errors.append(f"{path.relative_to(ROOT)} must be a JSON array")
            continue
        counts[path.name] = len(payload)
        for index, row in enumerate(payload):
            if not isinstance(row, dict):
                errors.append(f"{path.relative_to(ROOT)}[{index}] must be an object")
                continue
            url = row.get("url")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                errors.append(f"{path.relative_to(ROOT)}[{index}].url must be an http(s) URL")
    return counts


def audit_incoming_intake(errors: list[str]) -> dict[str, int]:
    files = iter_input_files([INCOMING])
    item_count = 0
    for path in files:
        if not is_valid_intake_record_name(path):
            errors.append(
                f"{display_path(path)}: intake filename must be "
                "<agent>-<YYYYMMDD>-<topic>.json"
            )
        payload = load_json(path)
        payload_errors, summary = validate_payload(path, payload)
        item_count += int(summary["items"])
        errors.extend(payload_errors)
    return {"incoming_files": len(files), "incoming_items": item_count}


def audit_incoming_image_updates(errors: list[str]) -> dict[str, int]:
    files = iter_image_update_files([IMAGE_UPDATES_INCOMING])
    update_count = 0
    catalog_rows: dict[int, dict[str, Any]] = {}
    catalog_payload = read_json(CATALOG)
    if isinstance(catalog_payload, dict) and isinstance(catalog_payload.get("items"), list):
        for item in catalog_payload["items"]:
            if not isinstance(item, dict):
                continue
            catalog_index = item.get("catalog_index")
            if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
                catalog_rows[catalog_index] = item
    for path in files:
        if not is_valid_intake_record_name(path):
            errors.append(
                f"{display_path(path)}: image update filename must be "
                "<agent>-<YYYYMMDD>-<topic>.json"
            )
        payload = load_image_update_json(path)
        payload_errors, summary = validate_image_update_payload(path, payload, catalog_rows=catalog_rows)
        update_count += int(summary["updates"])
        errors.extend(payload_errors)
    return {"image_update_files": len(files), "image_update_items": update_count}


def load_catalog_rows_by_index() -> dict[int, dict[str, Any]]:
    catalog_rows: dict[int, dict[str, Any]] = {}
    catalog_payload = read_json(CATALOG)
    if isinstance(catalog_payload, dict) and isinstance(catalog_payload.get("items"), list):
        for item in catalog_payload["items"]:
            if not isinstance(item, dict):
                continue
            catalog_index = item.get("catalog_index")
            if isinstance(catalog_index, int) and not isinstance(catalog_index, bool):
                catalog_rows[catalog_index] = item
    return catalog_rows


def audit_incoming_field_updates(errors: list[str]) -> dict[str, int]:
    files = iter_field_update_files([FIELD_UPDATES_INCOMING])
    update_count = 0
    catalog_rows = load_catalog_rows_by_index()
    for path in files:
        if not is_valid_intake_record_name(path):
            errors.append(
                f"{display_path(path)}: field update filename must be "
                "<agent>-<YYYYMMDD>-<topic>.json"
            )
        payload = load_field_update_json(path)
        payload_errors, summary = validate_field_update_payload(path, payload, catalog_rows=catalog_rows)
        update_count += int(summary["updates"])
        errors.extend(payload_errors)
    return {"field_update_files": len(files), "field_update_items": update_count}


def run_audit() -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    tracked = audit_tracked_data_files(errors)
    tracked_server = audit_tracked_server_artifacts(errors)
    filesystem_summary = audit_data_filesystem_layout(errors)
    catalog_summary = audit_catalog(errors)
    audit_catalog_meta(errors, catalog_summary["catalog_rows"])
    audit_site_status(errors)
    source_counts = audit_intake_sources(errors)
    intake_summary = audit_incoming_intake(errors)
    image_update_summary = audit_incoming_image_updates(errors)
    field_update_summary = audit_incoming_field_updates(errors)

    summary: dict[str, Any] = {
        "tracked_data_files": len(tracked),
        "public_database_files": len([path for path in tracked if path in PUBLIC_DATABASE_FILES]),
        "tracked_server_files": len(tracked_server),
        **filesystem_summary,
        **catalog_summary,
        "source_lists": source_counts,
        **intake_summary,
        **image_update_summary,
        **field_update_summary,
        "status": "fail" if errors else "pass",
        "errors": errors,
    }
    return summary, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Deokive public data layout.")
    parser.add_argument("--json", type=Path, help="Optional path to write the audit summary.")
    args = parser.parse_args()

    summary, errors = run_audit()
    output = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    print(output, end="")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(output, encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
