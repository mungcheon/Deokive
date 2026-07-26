from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEFAULT_PROBE = DATA / "ichiban_variant_lineup_official_probe_public.json"
DEFAULT_OUTPUT = DATA / "ichiban_variant_lineup_split_confirmed_template_public.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _prefill_variant_images(row: dict[str, Any], expected_count: int) -> list[str]:
    images = [str(value).strip() for value in row.get("official_images") or [] if str(value or "").strip()]
    if len(images) != expected_count:
        return []
    return images


def build_template(probe_report: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    image_prefilled_rows = 0
    for row in probe_report.get("candidates") or []:
        if not isinstance(row, dict) or row.get("status") != "matched":
            continue
        expected_count = row.get("expected_variant_count")
        if not isinstance(expected_count, int) or expected_count <= 1:
            continue
        prefilled_images = _prefill_variant_images(row, expected_count)
        if prefilled_images:
            image_prefilled_rows += 1
        items.append(
            {
                "manual_confirmed": False,
                "source_catalog_index": row.get("catalog_index"),
                "source_url": row.get("source_url"),
                "evidence_url": row.get("source_url"),
                "official_name": row.get("official_name"),
                "official_detail": row.get("official_detail"),
                "expected_variant_count": expected_count,
                "choice_policy": row.get("choice_policy"),
                "representative_image_ok": False,
                "image_prefill_source": "official_images_exact_count" if prefilled_images else "",
                "notes": "Fill variants from official visual/source evidence. Set representative_image_ok true only when reusing the lineup image for all variants is intentional.",
                "variants": [
                    {
                        "variant_name": "",
                        "character_name": "\uae30\ud0c0",
                        "image_url": prefilled_images[index] if prefilled_images else "",
                        "local_image_path": "",
                    }
                    for index in range(expected_count)
                ],
            }
        )

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "ichiban_variant_lineup_split_confirmed_template",
        "source_probe": str(DEFAULT_PROBE),
        "summary": {
            "template_rows": len(items),
            "image_prefilled_rows": image_prefilled_rows,
            "manual_confirmed_rows": 0,
            "auto_apply_enabled": False,
        },
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    probe = load_json(args.probe)
    if not isinstance(probe, dict):
        raise SystemExit(f"{args.probe} must contain a JSON object")
    template = build_template(probe)
    args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(template["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
