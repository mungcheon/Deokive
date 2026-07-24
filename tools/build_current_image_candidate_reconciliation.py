from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
import urllib.request
from urllib.parse import urlsplit

from image_enrichment_safety import is_safe_source_image_pair

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEED = ROOT / "data" / "catalog_public.json"
DEFAULT_OUTPUT = ROOT / "server" / "current_image_candidate_reconciliation.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

HOST_SOURCE_STORES = {
    "www.amiami.jp": "AmiAmi",
    "www.animate-onlineshop.jp": "\uc560\ub2c8\uba54\uc774\ud2b8",
    "www.enskyshop.com": "\uc5d4\uc2a4\uce74\uc774",
    "www.goodsmile.com": "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
    "www.goodsmile.info": "\uad7f\uc2a4\ub9c8\uc77c\ucef4\ud37c\ub2c8",
    "furyuprize.com": "FuRyu",
    "www.movic.jp": "Movic",
    "shop.asobistore.jp": "ASOBI STORE",
    "bsp-prize.jp": "Banpresto",
    "www.taito.co.jp": "Taito",
    "taito.co.jp": "Taito",
    "frieren-anime.jp": "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c \uacf5\uc2dd",
}


def _read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _catalog_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    return []


def _items_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    items: list[dict[str, Any]] = []
    for key in ("items", "updates", "auto_update_candidates", "changes", "candidates"):
        value = payload.get(key)
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, dict))
    return items


def _first_string(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _candidate_names(item: dict[str, Any]) -> list[tuple[str, str]]:
    names: list[tuple[str, str]] = []
    for key in ("name_ko", "candidate_name_ko"):
        value = _first_string(item, key)
        if value:
            names.append(("name_ko", value))
    for key in ("name_ja", "candidate_name_ja"):
        value = _first_string(item, key)
        if value:
            names.append(("name_ja", value))
    return names


def _source_store_for_url(source_url: str, fallback: str | None) -> str | None:
    return HOST_SOURCE_STORES.get(urlsplit(source_url).netloc.lower()) or fallback


def _source_kind_for_store(source_store: str | None) -> str:
    if source_store in {"AmiAmi", "\uc560\ub2c8\uba54\uc774\ud2b8", "ASOBI STORE"}:
        return "licensed_retailer_exact"
    if source_store == "\uc7a5\uc1a1\uc758 \ud504\ub9ac\ub80c \uacf5\uc2dd":
        return "official_anime"
    return "official_manufacturer_page"


def _live_title(source_url: str) -> str:
    request = urllib.request.Request(
        source_url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ja-JP,ja;q=0.9"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        text = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)', text, re.I)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    if match:
        title = re.sub(r"<[^>]+>", " ", match.group(1))
        return re.sub(r"\s+", " ", title).strip()
    return ""


def build_reconciliation(
    seed_rows: list[dict[str, Any]],
    candidate_paths: list[Path],
    *,
    validate_live_title: bool = False,
) -> dict[str, Any]:
    missing_by_name: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for index, row in enumerate(seed_rows):
        if row.get("image_url"):
            continue
        for key in ("name_ko", "name_ja"):
            value = str(row.get(key) or "").strip()
            if value:
                missing_by_name[(key, value)].append((index, row))

    exact_by_row: dict[int, dict[tuple[str, str, str | None], dict[str, Any]]] = defaultdict(dict)
    risky: list[dict[str, Any]] = []
    scanned_items = 0
    scanned_files = 0

    for path in candidate_paths:
        payload = _read_json(path)
        if payload is None:
            continue
        file_items = _items_from_payload(payload)
        if not file_items:
            continue
        scanned_files += 1
        for item in file_items:
            scanned_items += 1
            image_url = _first_string(item, "image_url", "candidate_image_url", "new_image_url")
            source_url = _first_string(item, "source_url", "candidate_source_url", "new_source_url", "evidence_url")
            if not image_url or not source_url:
                continue
            if not is_safe_source_image_pair(source_url, image_url):
                risky.append(
                    {
                        "reason": "unsafe_source_image_pair",
                        "source_url": source_url,
                        "image_url": image_url,
                        "from_file": str(path),
                    }
                )
                continue
            candidate_title = _first_string(item, "candidate_title", "title")
            for name_key, name_value in _candidate_names(item):
                for row_index, row in missing_by_name.get((name_key, name_value), []):
                    current_ja = str(row.get("name_ja") or "").strip()
                    current_ko = str(row.get("name_ko") or "").strip()
                    if current_ja:
                        if candidate_title != current_ja:
                            risky.append(
                                {
                                    "reason": "candidate_title_not_exact_current_name_ja",
                                    "row_index": row_index,
                                    "current_name_ko": current_ko,
                                    "current_name_ja": current_ja,
                                    "candidate_title": candidate_title,
                                    "from_file": str(path),
                                }
                            )
                            continue
                    else:
                        risky.append(
                            {
                                "reason": "current_row_missing_name_ja",
                                "row_index": row_index,
                                "current_name_ko": current_ko,
                                "current_name_ja": current_ja,
                                "candidate_title": candidate_title,
                                "from_file": str(path),
                            }
                        )
                        continue
                    source_store = _source_store_for_url(source_url, _first_string(item, "source_store") or row.get("source_store"))
                    live_title = ""
                    if validate_live_title:
                        try:
                            live_title = _live_title(source_url)
                        except Exception as exc:
                            risky.append(
                                {
                                    "reason": "live_title_fetch_failed",
                                    "row_index": row_index,
                                    "source_url": source_url,
                                    "error": str(exc),
                                    "from_file": str(path),
                                }
                            )
                            continue
                        if current_ja not in live_title:
                            risky.append(
                                {
                                    "reason": "live_title_does_not_contain_current_name_ja",
                                    "row_index": row_index,
                                    "current_name_ko": current_ko,
                                    "current_name_ja": current_ja,
                                    "candidate_title": candidate_title,
                                    "live_title": live_title,
                                    "source_url": source_url,
                                    "from_file": str(path),
                                }
                            )
                            continue
                    candidate = {
                        "row_index": row_index,
                        "name_ko": row.get("name_ko"),
                        "name_ja": row.get("name_ja"),
                        "source_store": source_store,
                        "source_kind": _source_kind_for_store(source_store),
                        "confidence": "high",
                        "source_url": source_url,
                        "image_url": image_url,
                        "candidate_title": candidate_title or name_value,
                        "live_title": live_title or None,
                        "manual_confirmed": True,
                        "from_file": str(path),
                    }
                    exact_by_row[row_index][(source_url, image_url, source_store)] = candidate

    importable: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    for row_index, options in sorted(exact_by_row.items()):
        values = list(options.values())
        if len(values) == 1:
            importable.append(values[0])
        else:
            row = seed_rows[row_index]
            ambiguous.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "option_count": len(values),
                    "options": values[:10],
                }
            )

    return {
        "summary": {
            "scanned_files": scanned_files,
            "scanned_items": scanned_items,
            "importable_rows": len(importable),
            "ambiguous_rows": len(ambiguous),
            "risky_items": len(risky),
        },
        "items": importable,
        "ambiguous": ambiguous,
        "risky_sample": risky[:200],
    }


def _default_candidate_paths(root: Path) -> list[Path]:
    server = root / "server"
    paths = []
    for path in server.rglob("*.json"):
        name = path.name.lower()
        if any(token in name for token in ("candidate", "dryrun", "image", "write")):
            paths.append(path)
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--candidate", type=Path, action="append", default=[])
    parser.add_argument("--validate-live-title", action="store_true")
    args = parser.parse_args()

    rows = _read_json(args.seed)
    seed_rows = _catalog_rows(rows)
    if not seed_rows:
        raise SystemExit(f"{args.seed} must contain a JSON list or an object with items")
    candidate_paths = args.candidate or _default_candidate_paths(ROOT)
    report = build_reconciliation(
        seed_rows,
        candidate_paths,
        validate_live_title=args.validate_live_title,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**report["summary"], "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
