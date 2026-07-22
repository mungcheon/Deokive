from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NEXT_PACK = DATA / "source_discovery_next_focus_pack_public.json"
REPORT = DATA / "source_discovery_next_focus_pack_fetch_audit_public.json"

FetchResult = dict[str, Any]
Fetcher = Callable[[str], FetchResult]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path = NEXT_PACK) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError(f"{path} must be a source discovery next focus pack object")
    return payload


def fetch_url(url: str, *, timeout: int = 20) -> FetchResult:
    if not url:
        return {"fetch_status": "missing_url", "http_status": None, "final_url": ""}
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "fetch_status": "ok",
                "http_status": int(response.status),
                "final_url": response.geturl(),
            }
    except urllib.error.HTTPError as exc:
        return {
            "fetch_status": "http_error",
            "http_status": int(exc.code),
            "final_url": exc.geturl(),
        }
    except urllib.error.URLError as exc:
        return {
            "fetch_status": "network_error",
            "http_status": None,
            "final_url": "",
            "error": str(exc.reason),
        }


def build_report(
    pack: dict[str, Any],
    *,
    fetcher: Fetcher = fetch_url,
    generated_at: str | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = pack.get("items") or []
    audited_items: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    http_status_counts: Counter[str] = Counter()

    for item in items:
        official_search_url = str(item.get("official_search_url") or "")
        result = fetcher(official_search_url)
        fetch_status = str(result.get("fetch_status") or "unknown")
        http_status = result.get("http_status")
        status_key = fetch_status if http_status is None else f"{fetch_status}_{http_status}"
        status_counts[status_key] += 1
        http_status_counts[str(http_status) if http_status is not None else "none"] += 1
        is_ok = fetch_status == "ok" and 200 <= int(http_status or 0) < 400
        audited_items.append(
            {
                "catalog_index": item.get("catalog_index"),
                "focus_pack_id": item.get("focus_pack_id"),
                "source_store": item.get("source_store"),
                "category": item.get("category"),
                "name_ko": item.get("name_ko"),
                "name_ja": item.get("name_ja"),
                "official_search_url": official_search_url,
                "web_search_url": item.get("web_search_url"),
                "fetch_status": fetch_status,
                "http_status": http_status,
                "final_url": result.get("final_url") or "",
                "error": result.get("error") or "",
                "needs_fallback_web_search": not is_ok,
                "recommended_next_action": (
                    "review_official_search_results_for_exact_detail_url"
                    if is_ok
                    else "use_web_search_or_store_archive_for_exact_detail_url"
                ),
            }
        )

    unavailable_rows = [item for item in audited_items if item["needs_fallback_web_search"]]
    return {
        "schema_version": 1,
        "generated_at": generated_at or now_utc(),
        "scope": "source_discovery_next_focus_pack_fetch_audit",
        "source_report": str(NEXT_PACK.relative_to(ROOT)).replace("\\", "/"),
        "summary": {
            "focus_pack_id": (pack.get("summary") or {}).get("focus_pack_id"),
            "pack_items": len(items),
            "official_search_ok_rows": len(items) - len(unavailable_rows),
            "official_search_unavailable_rows": len(unavailable_rows),
            "status_counts": status_counts.most_common(),
            "http_status_counts": http_status_counts.most_common(),
            "fallback_web_search_required": bool(unavailable_rows),
            "auto_apply_enabled": False,
            "recommended_next_action": (
                "resolve_unavailable_official_search_urls_before_source_import"
                if unavailable_rows
                else "review_official_search_results_for_exact_detail_urls"
            ),
        },
        "items": audited_items,
    }


def write_report(report: dict[str, Any], path: Path = REPORT) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    report = build_report(load_json())
    if args.write:
        write_report(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
