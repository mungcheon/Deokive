from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from catalog_normalize import is_generic_source_url
from image_enrichment_safety import is_product_specific_source_url

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "catalog_public.json"
DEFAULT_QUEUE = ROOT / "server" / "catalog_image_enrichment_queue.json"
DEFAULT_REPORT = ROOT / "server" / "catalog_image_safety_audit.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _catalog_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return [row for row in payload["items"] if isinstance(row, dict)]
    return []


def _source_state(row: dict[str, Any]) -> str:
    source_url = row.get("source_url")
    if not source_url:
        return "missing_source_url"
    if is_product_specific_source_url(source_url):
        return "product_specific_source_url"
    if is_generic_source_url(source_url):
        return "generic_source_url"
    return "ambiguous_source_url"


def _sample(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name_ko": row.get("name_ko"),
        "name_ja": row.get("name_ja"),
        "affiliation": row.get("affiliation"),
        "category": row.get("category"),
        "source_store": row.get("source_store"),
        "source_url": row.get("source_url"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--sample-limit", type=int, default=30)
    args = parser.parse_args()

    rows = _catalog_rows(_load_json(args.input))
    if not rows:
        raise SystemExit(f"{args.input} must contain a JSON list or an object with items")

    missing_rows = [row for row in rows if not row.get("image_url")]
    by_source_state = Counter(_source_state(row) for row in missing_rows)
    samples: dict[str, list[dict[str, Any]]] = {}
    for state in by_source_state:
        samples[state] = [_sample(row) for row in missing_rows if _source_state(row) == state][: args.sample_limit]

    queue_summary: dict[str, Any] = {}
    if args.queue.exists():
        queue_payload = _load_json(args.queue)
        queue_items = queue_payload.get("items") or queue_payload.get("queue") or []
        if isinstance(queue_items, list):
            queue_summary = {
                "items": len(queue_items),
                "by_strategy": Counter(
                    str(item.get("strategy") or "") for item in queue_items if isinstance(item, dict)
                ).most_common(),
            }

    report = {
        "missing_images": len(missing_rows),
        "by_source_state": by_source_state.most_common(),
        "queue_summary": queue_summary,
        "samples": samples,
        "policy": [
            "Automatic source_url image extraction is allowed only for product-specific official detail URLs.",
            "Generic shop, homepage, campaign, collection, and social OG images remain manual review only.",
            "Provider search matches still require exact or high-confidence title matching before attaching images.",
        ],
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "missing_images": len(missing_rows),
                "by_source_state": by_source_state.most_common(),
                "report": str(args.report),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
