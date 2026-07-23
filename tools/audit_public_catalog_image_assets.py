from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog_public.json"
REPORT = DATA / "catalog_image_asset_audit_public.json"


def present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_catalog(path: Path = CATALOG) -> dict[str, Any]:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or not isinstance(catalog.get("items"), list):
        raise ValueError(f"{path} must be a public catalog object with an items list")
    return catalog


def build_report(catalog: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = catalog["items"]
    rows = len(items)
    image_url_rows = [item for item in items if present(item.get("image_url"))]
    local_path_rows = [item for item in items if present(item.get("local_image_path"))]
    both_rows = [item for item in items if present(item.get("image_url")) and present(item.get("local_image_path"))]
    image_without_local = [item for item in items if present(item.get("image_url")) and not present(item.get("local_image_path"))]
    local_without_image = [item for item in items if present(item.get("local_image_path")) and not present(item.get("image_url"))]

    local_paths = [str(item.get("local_image_path")) for item in local_path_rows]
    missing_files = []
    missing_web_public_files = []
    invalid_paths = []
    for item in local_path_rows:
        local_path = str(item.get("local_image_path") or "")
        if local_path.startswith("/") or ".." in Path(local_path).parts:
            invalid_paths.append(item)
            continue
        if not (ROOT / local_path).is_file():
            missing_files.append(item)
        if not (ROOT / "assets" / local_path).is_file():
            missing_web_public_files.append(item)

    path_counts = Counter(local_paths)
    reused_paths = [path for path, count in path_counts.items() if count > 1]
    extension_counts = Counter(Path(path).suffix.lower() or "(none)" for path in local_paths)
    directory_counts = Counter(str(Path(path).parent).replace("\\", "/") for path in local_paths)

    findings: list[str] = []
    if image_without_local:
        findings.append("some rows have image_url but no local_image_path")
    if local_without_image:
        findings.append("some rows have local_image_path but no image_url")
    if missing_files:
        findings.append("some local_image_path files are missing from the repository")
    if missing_web_public_files:
        findings.append("some local_image_path files are missing from the Flutter web public asset path")
    if invalid_paths:
        findings.append("some local_image_path values are absolute or escape the repository")

    known_image_download_blockers = (
        len(image_without_local)
        + len(missing_files)
        + len(missing_web_public_files)
        + len(invalid_paths)
    )
    missing_image_url_rows = rows - len(image_url_rows)
    download_readiness = {
        "status": (
            "known_image_assets_complete"
            if known_image_download_blockers == 0
            else "known_image_asset_download_required"
        ),
        "known_image_url_rows": len(image_url_rows),
        "known_image_download_blocker_rows": known_image_download_blockers,
        "image_url_without_local_path_rows": len(image_without_local),
        "missing_local_image_files": len(missing_files),
        "missing_web_public_asset_files": len(missing_web_public_files),
        "invalid_local_image_paths": len(invalid_paths),
        "missing_image_url_rows": missing_image_url_rows,
        "rows_still_requiring_image_url_evidence": missing_image_url_rows,
        "download_complete_for_known_image_urls": known_image_download_blockers == 0,
        "next_safe_phase": (
            "find_exact_image_urls_for_missing_rows"
            if known_image_download_blockers == 0 and missing_image_url_rows
            else "download_or_repair_known_image_assets"
            if known_image_download_blockers
            else "archive_image_asset_completion"
        ),
        "auto_download_ready_rows": 0,
        "auto_apply_enabled": False,
        "operator_message": (
            "All catalog rows that already have image_url also have local and web-public image assets; "
            "remaining rows first need exact image_url/source evidence before a download can be attempted."
        )
        if known_image_download_blockers == 0
        else (
            "Some rows with known image_url are missing local or web-public assets; repair those files before "
            "moving on to image URL discovery."
        ),
    }

    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "public_catalog_image_asset_audit",
        "summary": {
            "rows": rows,
            "image_url_rows": len(image_url_rows),
            "missing_image_url_rows": missing_image_url_rows,
            "local_image_path_rows": len(local_path_rows),
            "image_url_with_local_path_rows": len(both_rows),
            "image_url_without_local_path_rows": len(image_without_local),
            "local_path_without_image_url_rows": len(local_without_image),
            "unique_local_image_paths": len(path_counts),
            "reused_local_image_paths": len(reused_paths),
            "missing_local_image_files": len(missing_files),
            "missing_web_public_asset_files": len(missing_web_public_files),
            "invalid_local_image_paths": len(invalid_paths),
            "local_asset_coverage": round(len(both_rows) / len(image_url_rows), 4) if image_url_rows else 1.0,
            "web_public_asset_coverage": round(
                (len(local_path_rows) - len(missing_web_public_files)) / len(local_path_rows), 4
            )
            if local_path_rows
            else 1.0,
            "status": "pass" if not findings else "review_required",
            "download_readiness_status": download_readiness["status"],
            "known_image_download_blocker_rows": known_image_download_blockers,
            "rows_still_requiring_image_url_evidence": missing_image_url_rows,
            "auto_download_ready_rows": 0,
        },
        "download_readiness": download_readiness,
        "breakdowns": {
            "by_extension": extension_counts.most_common(),
            "by_directory": directory_counts.most_common(20),
        },
        "findings": findings,
        "samples": {
            "image_url_without_local_path": sample_rows(image_without_local),
            "local_path_without_image_url": sample_rows(local_without_image),
            "missing_local_image_files": sample_rows(missing_files),
            "missing_web_public_asset_files": sample_rows(missing_web_public_files),
            "invalid_local_image_paths": sample_rows(invalid_paths),
            "reused_local_image_paths": [
                {"local_image_path": path, "rows": count}
                for path, count in path_counts.most_common()
                if count > 1
            ][:40],
        },
    }


def sample_rows(rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    return [
        {
            "catalog_index": item.get("catalog_index"),
            "name_ko": item.get("name_ko"),
            "name_ja": item.get("name_ja"),
            "image_url": item.get("image_url"),
            "local_image_path": item.get("local_image_path"),
            "source_store": item.get("source_store"),
        }
        for item in rows[:limit]
    ]


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_catalog())
    if args.write:
        write_report(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
