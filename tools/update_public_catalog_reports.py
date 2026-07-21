from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

PUBLIC_CATALOG = DATA / "catalog_public.json"
PUBLIC_META = DATA / "catalog_public_meta.json"
QUALITY = DATA / "catalog_quality_public.json"
IMAGE_BACKLOG = DATA / "catalog_image_backlog_public.json"
IMAGE_CANDIDATES = DATA / "catalog_image_candidate_review_public.json"
GOTOUCHI = DATA / "gotouchi_chiikawa_image_candidates_public.json"
REQUESTED = DATA / "requested_special_goods_public.json"
GENERIC_SOURCE = DATA / "generic_source_cleanup_public.json"
SOURCE_DETAIL = DATA / "source_detail_probe_public.json"
SOURCE_DISCOVERY = DATA / "source_discovery_queue_public.json"

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
    "source_url",
    "source_store",
    "release_date",
]

PRIVACY_NEEDLES = [
    "C:\\Users",
    "/Users/",
    "localhost",
    "127.0.0.1",
    "deokive_dev.db",
    "password=",
    "secret=",
    "api_key=",
    "ghp_",
    "github_pat_",
    "sk-",
]


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def present(value: Any) -> bool:
    return value not in (None, "", [], {})


def missing_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return {field: sum(1 for item in items if not present(item.get(field))) for field in PUBLIC_FIELDS}


def coverage(missing: dict[str, int], rows: int, fields: list[str]) -> dict[str, float]:
    if rows <= 0:
        return {field: 0.0 for field in fields}
    return {field: round((rows - missing.get(field, 0)) / rows, 4) for field in fields}


def copy_report_summary(path: Path, key: str) -> dict[str, Any]:
    data = load_json(path, {})
    summary = data.get("summary") if isinstance(data, dict) else None
    if not isinstance(summary, dict):
        summary = {}
    return {"public_report": f"data/{path.name}", **summary}


def validate_public_files(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.exists():
            findings.append(f"missing:{path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            json.loads(text)
        for needle in PRIVACY_NEEDLES:
            if needle.lower() in text.lower():
                findings.append(f"{path.as_posix()} contains {needle}")
        if "???" in text:
            findings.append(f"{path.as_posix()} contains replacement placeholder ???")
    return findings


def update_reports(write: bool) -> dict[str, Any]:
    catalog = load_json(PUBLIC_CATALOG)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("items"), list):
        raise ValueError("data/catalog_public.json must have an items list")

    items: list[dict[str, Any]] = catalog["items"]
    rows = len(items)
    missing = missing_counts(items)
    cov = coverage(missing, rows, ["source_url", "image_url", "release_date"])
    generated_at = now_utc()

    public_meta = load_json(PUBLIC_META, {})
    public_meta.update(
        {
            "schema_version": public_meta.get("schema_version", 1),
            "generated_at": public_meta.get("generated_at") or catalog.get("meta", {}).get("generated_at"),
            "row_count": rows,
            "fields": PUBLIC_FIELDS,
            "missing": missing,
            "privacy": {
                "contains_user_accounts": False,
                "contains_local_folders": False,
                "contains_private_memos": False,
                "contains_device_profiles": False,
                "contains_server_tokens": False,
            },
        }
    )

    quality = load_json(QUALITY, {})
    quality_missing = {
        "source_url": missing["source_url"],
        "image_url": missing["image_url"],
        "release_date": missing["release_date"],
        "barcode": missing["barcode"],
        "series_name": missing["series_name"],
        "sub_series": missing["sub_series"],
        "official_price_jpy": missing["official_price_jpy"],
    }
    quality_changed = (
        quality.get("row_count") != rows
        or quality.get("missing") != quality_missing
        or quality.get("coverage") != cov
    )
    quality.update(
        {
            "schema_version": quality.get("schema_version", 1),
            "row_count": rows,
            "missing": quality_missing,
            "coverage": cov,
        }
    )
    if quality_changed:
        quality["generated_at"] = generated_at

    image_backlog = load_json(IMAGE_BACKLOG, {})
    summary = image_backlog.setdefault("summary", {})
    summary.update(
        {
            "rows": rows,
            "missing_images": missing["image_url"],
            "missing_with_source_url": sum(
                1 for item in items if present(item.get("source_url")) and not present(item.get("image_url"))
            ),
            "missing_with_exact_source_url": 0,
            "missing_with_generic_source_url": sum(
                1 for item in items if present(item.get("source_url")) and not present(item.get("image_url"))
            ),
        }
    )

    image_candidates = load_json(IMAGE_CANDIDATES, {})
    image_candidates.setdefault("summary", {})

    for target in (quality, image_backlog, image_candidates):
        if GOTOUCHI.exists():
            target["gotouchi_chiikawa_image_candidates"] = copy_report_summary(GOTOUCHI, "gotouchi")
        if REQUESTED.exists():
            target["requested_special_goods_review"] = copy_report_summary(REQUESTED, "requested")
        if GENERIC_SOURCE.exists():
            target["generic_source_cleanup_queue"] = copy_report_summary(GENERIC_SOURCE, "generic_source")
        if SOURCE_DETAIL.exists():
            target["source_detail_candidate_probe"] = copy_report_summary(SOURCE_DETAIL, "source_detail")
        if SOURCE_DISCOVERY.exists():
            target["source_discovery_queue"] = copy_report_summary(SOURCE_DISCOVERY, "source_discovery")

    public_files = [
        PUBLIC_CATALOG,
        PUBLIC_META,
        QUALITY,
        IMAGE_BACKLOG,
        IMAGE_CANDIDATES,
        GOTOUCHI,
        REQUESTED,
        GENERIC_SOURCE,
        SOURCE_DETAIL,
        SOURCE_DISCOVERY,
    ]
    findings = validate_public_files([path for path in public_files if path.exists()])
    if findings:
        raise ValueError("public safety validation failed: " + "; ".join(findings))

    if write:
        write_json(PUBLIC_META, public_meta)
        write_json(QUALITY, quality)
        write_json(IMAGE_BACKLOG, image_backlog)
        write_json(IMAGE_CANDIDATES, image_candidates)

    return {
        "write": write,
        "rows": rows,
        "missing": missing,
        "coverage": cov,
        "updated_files": [
            str(PUBLIC_META.relative_to(ROOT)),
            str(QUALITY.relative_to(ROOT)),
            str(IMAGE_BACKLOG.relative_to(ROOT)),
            str(IMAGE_CANDIDATES.relative_to(ROOT)),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(json.dumps(update_reports(write=args.write), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
