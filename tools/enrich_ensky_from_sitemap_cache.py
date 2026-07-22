from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from enrich_catalog_images import _distinctive_query_tokens, _squash

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "server" / "catalog_seed_from_local.json"
DEFAULT_CACHE = ROOT / "server" / ".catalog_image_cache" / "ensky_sitemap_index.json"
DEFAULT_REPORT = ROOT / "server" / "ensky_sitemap_cache_enrichment_report.json"
ENSKY_STORE = "엔스카이"
COMMON_TOKENS = {
    "アクリル",
    "アクリルスタンド",
    "スタンド",
    "キーホルダー",
    "ラバーストラップ",
    "マスコット",
    "フィギュア",
    "コレクション",
    "トレーディング",
    "シリーズ",
    "vol",
}
PRODUCT_PHRASES = {
    "ラバーストラップ",
    "カラビナ付きラバーストラップ",
    "アクリルスタンド",
    "ビッグアクリルスタンド",
    "アクリルキーホルダー",
    "アクリルフィギュア",
    "キーホルダー",
    "おまんじゅうにぎにぎマスコット",
    "ちみけもますこっと",
    "ちびぬい",
    "ちびぬいマスコット",
    "ぬいぷぺ",
    "ぬいぺぺ",
    "たぴぬい",
    "スタンドミニ",
    "マスコット",
}


def row_identifier(row: dict[str, Any], fallback_index: int) -> int:
    value = row.get("catalog_index")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return fallback_index


def _last_parenthetical_variant(value: str) -> str | None:
    matches = re.findall(r"[\(\uff08]([^\(\)\uff08\uff09]+)[\)\uff09]", value)
    if not matches:
        return None
    variant = _squash(matches[-1])
    return variant or None


def _title_slash_variant(value: str) -> str | None:
    if "/" not in value:
        return None
    segment = value.rsplit("/", 1)[-1].strip()
    segment = re.sub(r"^[\(\uff08]?\d+[\)\uff09]?", "", segment).strip()
    variant = _squash(segment)
    return variant or None


def _safe_match(query: str, title: str) -> bool:
    query_key = _squash(query)
    title_key = _squash(title)
    query_variant = _last_parenthetical_variant(query)
    title_variant = _title_slash_variant(title)
    if query_variant and title_variant and query_variant != title_variant:
        return False
    required_phrases = [_squash(phrase) for phrase in PRODUCT_PHRASES if _squash(phrase) in query_key]
    if required_phrases and not any(phrase in title_key for phrase in required_phrases):
        return False
    if query_key and title_key and (query_key == title_key or query_key in title_key):
        return True

    common = {_squash(token) for token in COMMON_TOKENS}
    distinctive = [
        _squash(token)
        for token in _distinctive_query_tokens(query)
        if _squash(token) and _squash(token) not in common
    ]
    return bool(distinctive) and all(token in title_key for token in distinctive)


def enrich(rows: list[dict[str, Any]], products: list[dict[str, Any]]) -> dict[str, Any]:
    usable_products = [
        product
        for product in products
        if product.get("title") and product.get("image_url") and product.get("source_url")
    ]
    updated = 0
    scanned = 0
    changes: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    no_matches: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("source_store") != ENSKY_STORE:
            continue
        if row.get("source_url") and row.get("image_url"):
            continue
        query = str(row.get("name_ja") or row.get("name_ko") or "").strip()
        if not query:
            continue
        row_index = row_identifier(row, index)
        scanned += 1

        matches = [product for product in usable_products if _safe_match(query, str(product.get("title") or ""))]
        if not matches:
            if len(no_matches) < 100:
                no_matches.append(
                    {
                        "row_index": row_index,
                        "name_ko": row.get("name_ko"),
                        "name_ja": row.get("name_ja"),
                    }
                )
            continue
        if len(matches) > 1:
            ambiguous.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "match_titles": [product.get("title") for product in matches[:10]],
                }
            )
            continue

        product = matches[0]
        changed_fields: list[str] = []
        if not row.get("source_url"):
            row["source_url"] = product["source_url"]
            changed_fields.append("source_url")
        if not row.get("image_url"):
            row["image_url"] = product["image_url"]
            changed_fields.append("image_url")
        if changed_fields:
            updated += 1
            changes.append(
                {
                    "row_index": row_index,
                    "name_ko": row.get("name_ko"),
                    "name_ja": row.get("name_ja"),
                    "fields": changed_fields,
                    "source_url": row.get("source_url"),
                    "image_url": row.get("image_url"),
                    "match_title": product.get("title"),
                }
            )
    return {
        "scanned_rows": scanned,
        "updated_rows": updated,
        "changes": changes,
        "ambiguous": ambiguous,
        "no_matches": no_matches,
    }


def _load_rows(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)], payload
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)], None
    raise SystemExit(f"{path} must contain a JSON list or a catalog object with items")


def _write_rows(path: Path, rows: list[dict[str, Any]], wrapper: dict[str, Any] | None) -> None:
    if wrapper is not None:
        wrapper["items"] = rows
        path.write_text(json.dumps(wrapper, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        return
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    rows, wrapper = _load_rows(args.input)
    products = json.loads(args.cache.read_text(encoding="utf-8-sig"))
    if not isinstance(products, list):
        raise SystemExit("Cache must be a JSON list")

    result = enrich(rows, products)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(
            {
                "updated_rows": result["updated_rows"],
                "scanned_rows": result["scanned_rows"],
                "write": args.write,
                "changes": result["changes"],
                "ambiguous_rows": len(result["ambiguous"]),
                "ambiguous_sample": result["ambiguous"][:100],
                "no_match_rows_sampled": len(result["no_matches"]),
                "no_match_sample": result["no_matches"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if args.write and result["changes"]:
        _write_rows(args.input, rows, wrapper)
    print(
        json.dumps(
            {
                "scanned_rows": result["scanned_rows"],
                "updated_rows": result["updated_rows"],
                "ambiguous_rows": len(result["ambiguous"]),
                "no_match_rows_sampled": len(result["no_matches"]),
                "report": str(args.report),
                "write": args.write,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.write:
        print("Dry run only. Re-run with --write to update the seed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
