from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from catalog_normalize import canonical_key, normalize_row

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_QUALITY = ROOT / "server" / "catalog_quality_report.json"
DEFAULT_QUEUE = ROOT / "server" / "catalog_field_enrichment_queue.json"
DEFAULT_QUEUE_MD = ROOT / "server" / "catalog_field_enrichment_queue.md"
DEFAULT_JSON_REPORT = ROOT / "server" / "catalog_public_safety_audit.json"
DEFAULT_MD_REPORT = ROOT / "server" / "catalog_public_safety_audit.md"
DEFAULT_DB = ROOT / "server" / "deokive_dev.db"
DEFAULT_PUBLIC_CATALOG = ROOT / "data" / "catalog_public.json"

CATALOG_FIELDS = {
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
}

PERSONAL_FIELD_HINTS = {
    "account",
    "address",
    "avatar",
    "bookmark",
    "comment",
    "device",
    "draft",
    "email",
    "folder",
    "like",
    "memo",
    "nickname",
    "owner",
    "phone",
    "profile",
    "session",
    "token",
    "user",
}

TEXT_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "windows_user_path": re.compile(r"C:\\Users\\[^\\/\s]+", re.IGNORECASE),
    "unix_home_path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+"),
    "local_ip": re.compile(
        r"\b(?:127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b"
    ),
    "localhost": re.compile(r"\blocalhost\b", re.IGNORECASE),
    "secretish_word": re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|private[_-]?key)\b"),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def summarize_seed(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing = Counter()
    field_presence = Counter()
    unexpected_fields = Counter()
    personal_field_names = Counter()
    duplicate_groups: dict[tuple[str, str], list[int]] = defaultdict(list)

    for index, row in enumerate(rows):
        normalized = normalize_row(row)
        key = canonical_key(normalized)
        if key[1]:
            duplicate_groups[key].append(index)
        for field, value in row.items():
            field_presence[field] += 1
            if field not in CATALOG_FIELDS:
                unexpected_fields[field] += 1
            lowered = field.lower()
            if any(hint in lowered for hint in PERSONAL_FIELD_HINTS):
                personal_field_names[field] += 1
        for field in CATALOG_FIELDS:
            if row.get(field) in (None, "", [], {}):
                missing[field] += 1

    duplicates = {key: indexes for key, indexes in duplicate_groups.items() if len(indexes) > 1}
    duplicate_samples = []
    for key, indexes in list(duplicates.items())[:20]:
        first = rows[indexes[0]]
        duplicate_samples.append(
            {
                "key": list(key),
                "indexes": indexes[:10],
                "name_ko": first.get("name_ko"),
                "source_store": first.get("source_store"),
                "source_url": first.get("source_url"),
            }
        )

    enrichment_fields = ["image_url", "source_url", "release_date", "barcode", "official_price_jpy"]
    core_fields = ["name_ko", "category", "character_name", "affiliation", "source_store"]
    return {
        "rows": len(rows),
        "canonical_keys": len(duplicate_groups),
        "duplicate_groups": len(duplicates),
        "duplicate_rows": sum(len(indexes) - 1 for indexes in duplicates.values()),
        "duplicate_samples": duplicate_samples,
        "field_presence": dict(sorted(field_presence.items())),
        "unexpected_fields": dict(sorted(unexpected_fields.items())),
        "personal_field_name_hits": dict(sorted(personal_field_names.items())),
        "missing_core": {field: missing[field] for field in core_fields},
        "missing_enrichment": {field: missing[field] for field in enrichment_fields},
    }


def load_public_catalog_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = load_json(path)
    if isinstance(payload, dict):
        rows = payload.get("items")
    else:
        rows = payload
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def summarize_public_catalog(path: Path) -> dict[str, Any]:
    rows = load_public_catalog_rows(path)
    if not rows:
        return {
            "path": _relative_path(path),
            "exists": path.exists(),
            "rows": 0,
            "missing_enrichment": {},
        }
    summary = summarize_seed(rows)
    return {
        "path": _relative_path(path),
        "exists": True,
        "rows": summary["rows"],
        "duplicate_groups": summary["duplicate_groups"],
        "duplicate_rows": summary["duplicate_rows"],
        "missing_enrichment": summary["missing_enrichment"],
    }


def compare_public_catalog(public_summary: dict[str, Any], seed_summary: dict[str, Any]) -> dict[str, Any]:
    public_missing = public_summary.get("missing_enrichment") or {}
    seed_missing = seed_summary.get("missing_enrichment") or {}
    missing_deltas = {
        field: int(public_missing.get(field, 0)) - int(seed_missing.get(field, 0))
        for field in sorted(set(public_missing) | set(seed_missing))
    }
    return {
        "same_row_count": public_summary.get("rows") == seed_summary.get("rows"),
        "row_delta": int(public_summary.get("rows") or 0) - int(seed_summary.get("rows") or 0),
        "missing_enrichment_delta": missing_deltas,
        "public_image_missing_rows": int(public_missing.get("image_url") or 0),
        "seed_image_missing_rows": int(seed_missing.get("image_url") or 0),
        "image_missing_delta": int(public_missing.get("image_url") or 0) - int(seed_missing.get("image_url") or 0),
        "note": "data/catalog_public.json is the GitHub Pages source of truth; server/catalog_seed_from_local.json is the local DB export safety source.",
    }


def summarize_queue(queue_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "rows": queue_report.get("rows"),
        "missing_total": queue_report.get("missing_total"),
        "actionable_missing_total": queue_report.get("actionable_missing_total"),
        "non_actionable_missing_total": queue_report.get("non_actionable_missing_total"),
        "by_field": _counterish_list_to_dict(queue_report.get("by_field")),
        "by_strategy": _counterish_list_to_dict(queue_report.get("by_strategy")),
        "queue_items": len(queue_report.get("queue", [])) if isinstance(queue_report.get("queue"), list) else None,
    }


def compare_quality_report(quality_report: dict[str, Any], seed_summary: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "rows": seed_summary["rows"],
        "duplicate_groups": seed_summary["duplicate_groups"],
        "duplicate_rows": seed_summary["duplicate_rows"],
        "missing_core": seed_summary["missing_core"],
        "missing_enrichment": seed_summary["missing_enrichment"],
    }
    actual = {
        "rows": quality_report.get("rows"),
        "duplicate_groups": quality_report.get("duplicate_groups"),
        "duplicate_rows": quality_report.get("duplicate_rows"),
        "missing_core": quality_report.get("missing_core"),
        "missing_enrichment": quality_report.get("missing_enrichment"),
    }
    mismatches = {
        key: {"expected": value, "actual": actual.get(key)}
        for key, value in expected.items()
        if actual.get(key) != value
    }
    return {"matches_seed_recount": not mismatches, "mismatches": mismatches, "actual": actual}


def scan_text_files(paths: list[Path]) -> dict[str, Any]:
    findings = []
    counts = Counter()
    for path in paths:
        display_path = _relative_path(path)
        if not path.exists():
            findings.append({"path": display_path, "kind": "missing_file", "severity": "info"})
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for kind, pattern in TEXT_PATTERNS.items():
            for match in pattern.finditer(text):
                severity, reason = classify_text_match(path, kind, match.group(0), text, match.start(), match.end())
                counts[(kind, severity)] += 1
                if severity in {"medium", "high"}:
                    findings.append(
                        {
                            "path": display_path,
                            "kind": kind,
                            "severity": severity,
                            "reason": reason,
                            "match": match.group(0),
                            "context": context_for(text, match.start(), match.end()),
                        }
                    )
    return {
        "counts": [{"kind": kind, "severity": severity, "count": count} for (kind, severity), count in sorted(counts.items())],
        "risk_findings": findings[:100],
        "risk_finding_count": len(findings),
    }


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def classify_text_match(path: Path, kind: str, match: str, text: str, start: int, end: int) -> tuple[str, str]:
    relative = _relative_path(path)
    context = text[max(0, start - 80) : min(len(text), end + 80)].lower()
    is_catalog_public_data = relative in {
        "server/catalog_seed_from_local.json",
        "server/catalog_quality_report.json",
        "server/catalog_field_enrichment_queue.json",
        "server/catalog_field_enrichment_queue.md",
    }
    if kind == "secretish_word":
        if "secret island" in context:
            return "low", "catalog/product title text, not a credential"
        if "do not commit" in context or "github secrets" in context or "env vars" in context or "password`" in context:
            return "low", "documentation warning or environment variable name"
    if kind == "email" and match.endswith("@users.noreply.github.com"):
        return "low", "github actions bot noreply identity"
    if kind in {"localhost", "local_ip"} and not is_catalog_public_data:
        return "low", "local development/runtime guard outside public catalog data"
    if kind in {"email", "windows_user_path", "unix_home_path", "local_ip", "localhost"} and is_catalog_public_data:
        return "high", "local or personal identifier appears inside generated public catalog data"
    if kind in {"windows_user_path", "unix_home_path"}:
        return "medium", "machine-local path appears in public-facing file"
    if kind == "secretish_word":
        return "medium", "credential-related word outside known safe documentation context"
    return "low", "allowed or informational match"


def context_for(text: str, start: int, end: int) -> str:
    snippet = text[max(0, start - 60) : min(len(text), end + 60)]
    return " ".join(snippet.split())


def inspect_db(db_path: Path, seed_summary: dict[str, Any]) -> dict[str, Any]:
    if not db_path.exists():
        return {"path": _relative_path(db_path), "exists": False}
    conn = sqlite3.connect(db_path)
    try:
        active_rows = conn.execute("select count(*) from goods_catalog where is_active = 1").fetchone()[0]
        return {
            "path": _relative_path(db_path),
            "exists": True,
            "active_catalog_rows": active_rows,
            "matches_seed_row_count": active_rows == seed_summary["rows"],
        }
    finally:
        conn.close()


def build_markdown(report: dict[str, Any]) -> str:
    seed = report["seed"]
    queue = report["field_enrichment_queue"]
    privacy = report["privacy_scan"]
    quality = report["quality_report_crosscheck"]
    privacy_risk_count = sum(
        1
        for item in privacy.get("risk_findings", [])
        if item.get("severity") in {"medium", "high"}
    )
    status = "PASS" if report["public_data_privacy_status"] == "pass" else "REVIEW"
    lines = [
        "# Public Catalog Safety Audit",
        "",
        f"- Status: `{status}`",
        f"- Seed rows: `{seed['rows']}`",
        f"- Canonical duplicate groups: `{seed['duplicate_groups']}`",
        f"- Quality report matches recount: `{quality['matches_seed_recount']}`",
        f"- Public catalog rows: `{report['public_catalog'].get('rows')}`",
        f"- Public image missing rows: `{report['public_catalog_comparison'].get('public_image_missing_rows')}`",
        f"- Seed image missing rows: `{report['public_catalog_comparison'].get('seed_image_missing_rows')}`",
        f"- Privacy risk findings: `{privacy_risk_count}`",
        f"- DB active rows match seed: `{report['db'].get('matches_seed_row_count')}`",
        "",
        "## Missing Enrichment Backlog",
        "",
    ]
    for field, count in queue.get("by_field", {}).items():
        lines.append(f"- `{field}`: `{count}`")
    lines.extend(
        [
            "",
            f"- Missing field cells: `{queue.get('missing_total')}`",
            f"- Actionable missing field cells: `{queue.get('actionable_missing_total')}`",
            f"- Non-actionable/manual-only field cells: `{queue.get('non_actionable_missing_total')}`",
            "",
            "## Public Data Privacy Findings",
            "",
        ]
    )
    risk_findings = [
        item
        for item in privacy.get("risk_findings", [])
        if item.get("severity") in {"medium", "high"}
    ]
    if risk_findings:
        for item in risk_findings[:20]:
            reason = item.get("reason") or "File was not present during the scan."
            lines.append(f"- `{item['severity']}` `{item['kind']}` in `{item['path']}`: {reason}")
    else:
        lines.append("- No high/medium personal, local path, local network, email, or credential-like findings in scanned public catalog/report files.")
    lines.extend(
        [
            "",
            "## Public Catalog Crosscheck",
            "",
            f"- Public catalog path: `{report['public_catalog'].get('path')}`",
            f"- Public vs seed row delta: `{report['public_catalog_comparison'].get('row_delta')}`",
            f"- Public vs seed image-missing delta: `{report['public_catalog_comparison'].get('image_missing_delta')}`",
            f"- Source of truth for GitHub Pages image backlog: `data/catalog_public.json`",
            "",
            "## Field Shape",
            "",
            f"- Unexpected catalog fields: `{len(seed['unexpected_fields'])}`",
            f"- Personal-field-name hits in catalog rows: `{len(seed['personal_field_name_hits'])}`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _counterish_list_to_dict(value: Any) -> dict[str, int]:
    if isinstance(value, dict):
        return {str(k): int(v) for k, v in value.items()}
    if isinstance(value, list):
        result: dict[str, int] = {}
        for item in value:
            if isinstance(item, list) and len(item) == 2:
                result[str(item[0])] = int(item[1])
        return result
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--quality-report", type=Path, default=DEFAULT_QUALITY)
    parser.add_argument("--field-queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--field-queue-md", type=Path, default=DEFAULT_QUEUE_MD)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--public-catalog", type=Path, default=DEFAULT_PUBLIC_CATALOG)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--md-report", type=Path, default=DEFAULT_MD_REPORT)
    args = parser.parse_args()

    seed_rows = load_json(args.seed)
    if not isinstance(seed_rows, list):
        raise SystemExit(f"{args.seed} must contain a JSON list")
    seed_summary = summarize_seed([row for row in seed_rows if isinstance(row, dict)])
    public_catalog_summary = summarize_public_catalog(args.public_catalog)
    quality_report = load_json(args.quality_report)
    field_queue_report = load_json(args.field_queue)
    scan_paths = [
        args.seed,
        args.quality_report,
        args.field_queue,
        args.field_queue_md,
        ROOT / "README.md",
        ROOT / "server" / "README.md",
        ROOT / ".github" / "workflows" / "update-catalog.yml",
        ROOT / "web" / "CNAME",
        ROOT / "web" / "index.html",
    ]

    privacy_scan = scan_text_files(scan_paths)
    privacy_risk_count = sum(
        1
        for item in privacy_scan.get("risk_findings", [])
        if item.get("severity") in {"medium", "high"}
    )
    report = {
        "seed_path": _relative_path(args.seed),
        "seed": seed_summary,
        "public_catalog": public_catalog_summary,
        "public_catalog_comparison": compare_public_catalog(public_catalog_summary, seed_summary),
        "quality_report_crosscheck": compare_quality_report(quality_report, seed_summary),
        "field_enrichment_queue": summarize_queue(field_queue_report),
        "db": inspect_db(args.db, seed_summary),
        "privacy_scan": privacy_scan,
        "public_data_privacy_status": "pass" if privacy_risk_count == 0 else "review",
    }
    args.json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.md_report.write_text(build_markdown(report), encoding="utf-8")

    print(json.dumps(
        {
            "rows": seed_summary["rows"],
            "duplicate_groups": seed_summary["duplicate_groups"],
            "missing_enrichment": seed_summary["missing_enrichment"],
            "public_catalog_rows": public_catalog_summary.get("rows"),
            "public_missing_enrichment": public_catalog_summary.get("missing_enrichment"),
            "public_vs_seed_image_missing_delta": report["public_catalog_comparison"].get("image_missing_delta"),
            "privacy_status": report["public_data_privacy_status"],
            "privacy_risk_findings": privacy_risk_count,
            "json_report": str(args.json_report),
            "md_report": str(args.md_report),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
