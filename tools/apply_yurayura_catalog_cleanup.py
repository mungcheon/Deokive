from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from generate_seed_catalog_dart import generate
except ModuleNotFoundError:
    from tools.generate_seed_catalog_dart import generate

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "data" / "catalog_public.json"
DEFAULT_SEED_OUTPUT = ROOT / "lib" / "data" / "catalog" / "seed_catalog.dart"
DEFAULT_LOG = ROOT / "data" / "catalog_row_removal_log_public.json"

MIXED_DUPLICATE_INDEX = 17827
MY_HERO_INDEX = 17931


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_catalog(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise SystemExit(f"{path} must contain a public catalog object with items")
    return payload


def _sync_flutter_seed(catalog: Path, output: Path) -> None:
    payload = _load_catalog(catalog)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        generate([row for row in payload["items"] if isinstance(row, dict)], source_label="data/catalog_public.json"),
        encoding="utf-8",
    )


def _load_log(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": 1,
            "scope": "catalog_row_removal_log",
            "items": [],
        }
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise SystemExit(f"{path} must contain an object with items")
    return payload


def apply_cleanup(payload: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    rows = [row for row in payload["items"] if isinstance(row, dict)]
    mixed_rows = [row for row in rows if row.get("catalog_index") == MIXED_DUPLICATE_INDEX]
    if len(mixed_rows) != 1:
        raise SystemExit(f"Expected one row for catalog_index {MIXED_DUPLICATE_INDEX}, found {len(mixed_rows)}")
    my_hero_rows = [row for row in rows if row.get("catalog_index") == MY_HERO_INDEX]
    if len(my_hero_rows) != 1:
        raise SystemExit(f"Expected one row for catalog_index {MY_HERO_INDEX}, found {len(my_hero_rows)}")

    removed = mixed_rows[0]
    before_my_hero = dict(my_hero_rows[0])
    my_hero_rows[0].update(
        {
            "name_ko": "유라유라 헤드 바쿠고 카츠키 피규어",
            "name_ja": "ゆらゆらヘッド 爆豪勝己",
            "character_name": "바쿠고 카츠키",
            "affiliation": "나의 히어로 아카데미아",
            "series_name": "유라유라 피규어 나히아",
            "sub_series": "유라유라 헤드",
            "official_price_jpy": 2000,
            "release_date": "2022-06",
            "source_store": "Max Limited",
            "source_url": "https://max-jpn.com/series1/yurayura/item_detail11.html",
            "image_url": "https://max-jpn.com/imgs/character1/myhero/30/01.jpg",
        }
    )

    payload["items"] = [row for row in rows if row.get("catalog_index") != MIXED_DUPLICATE_INDEX]
    payload["total_items"] = len(payload["items"])
    meta = payload.get("meta")
    if isinstance(meta, dict):
        fields = meta.get("fields") or []
        meta["row_count"] = len(payload["items"])
        meta["total_items"] = len(payload["items"])
        meta["missing"] = {field: sum(1 for row in payload["items"] if row.get(field) in (None, "")) for field in fields}

    return {
        "removed": removed,
        "updated": {
            "catalog_index": MY_HERO_INDEX,
            "before": before_my_hero,
            "after": my_hero_rows[0],
        },
        "generated_at": generated_at or _now_utc(),
        "reason": "mixed_requested_yurayura_summary_replaced_by_specific_existing_rows",
        "specific_existing_catalog_indexes": [17930, 17931, 17932],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up duplicate yurayura requested summary rows.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--seed-output", type=Path, default=DEFAULT_SEED_OUTPUT)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    payload = _load_catalog(args.catalog)
    result = apply_cleanup(payload)
    if args.write:
        args.catalog.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        _sync_flutter_seed(args.catalog, args.seed_output)
        log = _load_log(args.log)
        log["updated_at"] = result["generated_at"]
        log["items"].append(result)
        args.log.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "removed_catalog_index": result["removed"].get("catalog_index"),
                "updated_catalog_index": result["updated"]["catalog_index"],
                "specific_existing_catalog_indexes": result["specific_existing_catalog_indexes"],
                "write": args.write,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.write:
        print("Dry run only. Re-run with --write to update files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
