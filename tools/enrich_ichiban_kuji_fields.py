from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from import_ichiban_kuji_history import _extract_date, _extract_price, _plain_text

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_REPORT = ROOT / "server" / "ichiban_kuji_field_enrichment_report.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.25)
    args = parser.parse_args()

    rows = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list):
        raise SystemExit(f"{args.input} must contain a JSON list")

    urls = sorted(
        {
            str(row.get("source_url") or "")
            for row in rows
            if isinstance(row, dict)
            and row.get("source_store") == "이치방쿠지"
            and row.get("source_url")
            and (
                not _present(row.get("official_price_jpy"))
                or not _present(row.get("release_date"))
            )
        }
    )
    metadata_by_url: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []
    for index, url in enumerate(urls):
        if index:
            time.sleep(args.sleep)
        try:
            plain = _plain_text(_fetch_text(url))
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            failures.append({"url": url, "error": f"{type(error).__name__}: {error}"})
            continue
        metadata_by_url[url] = {
            "official_price_jpy": _extract_price(plain),
            "release_date": _extract_date(plain),
        }

    changes: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("source_store") != "이치방쿠지":
            continue
        metadata = metadata_by_url.get(str(row.get("source_url") or ""))
        if not metadata:
            continue
        row_changes: dict[str, Any] = {}
        for field in ("official_price_jpy", "release_date"):
            if _present(row.get(field)) or not _present(metadata.get(field)):
                continue
            row[field] = metadata[field]
            row_changes[field] = metadata[field]
        if row_changes:
            changes.append(
                {
                    "name_ko": row.get("name_ko"),
                    "source_url": row.get("source_url"),
                    "changes": row_changes,
                }
            )

    report = {
        "candidate_urls": len(urls),
        "metadata_found": sum(1 for item in metadata_by_url.values() if item.get("official_price_jpy") or item.get("release_date")),
        "changed_rows": len(changes),
        "failures": failures,
        "changes": changes,
        "write": args.write,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write and changes:
        args.input.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "changes"}, ensure_ascii=False, indent=2))
    if not args.write:
        print("Dry run only. Re-run with --write to update the seed.")
    return 0


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _present(value: Any) -> bool:
    return value is not None and value != ""


if __name__ == "__main__":
    raise SystemExit(main())
