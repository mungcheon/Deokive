from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ICON_SOURCE = ROOT / "lib" / "config" / "app_icon_catalog.dart"
DEFAULT_PALETTE_SOURCE = ROOT / "lib" / "config" / "app_palette_catalog.dart"
DEFAULT_ANIMATION_AUDIT = ROOT / "server" / "animation_goods_category_audit.json"
DEFAULT_JSON = ROOT / "server" / "app_folder_visual_catalog_audit.json"
DEFAULT_MD = ROOT / "server" / "app_folder_visual_catalog_audit.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _icon_options(source: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r"AppIconOption\(\s*key:\s*'([^']+)'\s*,\s*icon:\s*Icons\.([A-Za-z0-9_]+)\s*,\s*label:\s*'([^']*)'\s*,\s*group:\s*'([^']*)'",
        re.S,
    )
    return [
        {"key": key, "material_icon": icon, "label": label, "group": group}
        for key, icon, label, group in pattern.findall(source)
    ]


def _folder_colors(source: str) -> list[str]:
    match = re.search(r"folderColors\s*=\s*\[(.*?)\n\s*\];", source, re.S)
    color_source = match.group(1) if match else source
    return [_normalize_color(value) for value in re.findall(r"Color\(0x([0-9A-Fa-f]{8})\)", color_source)]


def _sectioned_folder_colors(source: str) -> list[dict[str, Any]]:
    match = re.search(r"folderColors\s*=\s*\[(.*?)\n\s*\];", source, re.S)
    color_source = match.group(1) if match else source
    current_section = "Unsectioned"
    rows: list[dict[str, Any]] = []
    for line in color_source.splitlines():
        comment = re.search(r"//\s*(.+)", line)
        if comment:
            current_section = comment.group(1).strip()
        for value in re.findall(r"Color\(0x([0-9A-Fa-f]{8})\)", line):
            color = _normalize_color(value)
            rows.append(
                {
                    "section": current_section,
                    "color": color,
                    "hue": _hue_degrees(color),
                    "lightness": _lightness(color),
                }
            )
    return rows


def _normalize_color(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower().startswith("0x"):
        text = text[2:]
    return "0x" + text.upper()


def _rgb_tuple(color: str) -> tuple[int, int, int]:
    value = int(_normalize_color(color)[4:], 16)
    return (value >> 16) & 255, (value >> 8) & 255, value & 255


def _hue_degrees(color: str) -> float:
    red, green, blue = _rgb_tuple(color)
    hue, _lightness, _saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
    return round(hue * 360, 2)


def _lightness(color: str) -> float:
    red, green, blue = _rgb_tuple(color)
    _hue, lightness, _saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
    return round(lightness, 4)


def _animation_visuals(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    visuals = payload.get("category_visuals") if isinstance(payload, dict) else []
    return [item for item in visuals or [] if isinstance(item, dict)]


def _comment_sections(source: str) -> list[dict[str, Any]]:
    lines = source.splitlines()
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in lines:
        comment = re.search(r"//\s*(.+)", line)
        if comment:
            text = comment.group(1).strip()
            if text and not text.startswith(("ignore", "TODO")):
                current = {"section": text, "color_count": 0}
                sections.append(current)
        if "Color(0x" in line and current is not None:
            current["color_count"] += len(re.findall(r"Color\(0x[0-9A-Fa-f]{8}\)", line))
    return [item for item in sections if item["color_count"]]


EXPECTED_PALETTE_SECTION_ORDER = [
    "Rose, red, pink",
    "Peach, orange, amber, yellow",
    "Sand and warm neutrals",
    "Olive and green",
    "Mint, teal, cyan",
    "Sky and blue",
    "Indigo, violet, purple",
    "Neutrals",
]


def _palette_sort_audit(sectioned_colors: list[dict[str, Any]]) -> dict[str, Any]:
    seen_sections: list[str] = []
    section_ranges: list[dict[str, Any]] = []
    for item in sectioned_colors:
        section = str(item["section"])
        if section not in seen_sections:
            seen_sections.append(section)

    for section in seen_sections:
        rows = [item for item in sectioned_colors if item["section"] == section]
        if section == "Neutrals":
            ordered = all(rows[index]["lightness"] >= rows[index + 1]["lightness"] for index in range(len(rows) - 1))
            order_key = "lightness_desc"
            hue_span = None
        else:
            hue_span = _circular_hue_span([float(row["hue"]) for row in rows])
            ordered = hue_span <= 95
            order_key = "bounded_hue_family"
        section_ranges.append(
            {
                "section": section,
                "colors": len(rows),
                "first_color": rows[0]["color"] if rows else None,
                "last_color": rows[-1]["color"] if rows else None,
                "min_hue": min((row["hue"] for row in rows), default=None),
                "max_hue": max((row["hue"] for row in rows), default=None),
                "circular_hue_span": hue_span,
                "order_key": order_key,
                "locally_sorted": ordered,
            }
        )

    expected_positions = {section: index for index, section in enumerate(EXPECTED_PALETTE_SECTION_ORDER)}
    actual_positions = [expected_positions.get(section, 10_000) for section in seen_sections]
    return {
        "expected_section_order": EXPECTED_PALETTE_SECTION_ORDER,
        "actual_section_order": seen_sections,
        "section_order_matches_expected": seen_sections == EXPECTED_PALETTE_SECTION_ORDER,
        "section_order_monotonic": actual_positions == sorted(actual_positions),
        "section_ranges": section_ranges,
        "sections_locally_sorted": all(item["locally_sorted"] for item in section_ranges),
        "notes": [
            "Colored sections should move around the color wheel from warm hues to cool hues.",
            "Neutrals are checked by lightness from white to dark.",
        ],
    }


def _palette_color_families(sectioned_colors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    families: list[dict[str, Any]] = []
    seen_sections: list[str] = []
    for item in sectioned_colors:
        section = str(item["section"])
        if section not in seen_sections:
            seen_sections.append(section)

    expected_positions = {section: index for index, section in enumerate(EXPECTED_PALETTE_SECTION_ORDER)}
    for section_index, section in enumerate(seen_sections):
        rows = [item for item in sectioned_colors if item["section"] == section]
        family_order = expected_positions.get(section, 99 + section_index)
        colors = [
            {
                "color": row["color"],
                "hue": row["hue"],
                "lightness": row["lightness"],
                "picker_sort_key": f"{family_order:02d}-{index:03d}",
            }
            for index, row in enumerate(rows)
        ]
        families.append(
            {
                "section": section,
                "sort_order": family_order,
                "color_count": len(colors),
                "colors": colors,
            }
        )
    return families


def _palette_picker_order(sectioned_colors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in _palette_color_families(sectioned_colors):
        for color in family["colors"]:
            rows.append(
                {
                    "section": family["section"],
                    "section_sort_order": family["sort_order"],
                    "color": color["color"],
                    "hue": color["hue"],
                    "lightness": color["lightness"],
                    "picker_sort_key": color["picker_sort_key"],
                }
            )
    return rows


def _circular_hue_span(hues: list[float]) -> float:
    if not hues:
        return 0.0
    values = sorted(hue % 360 for hue in hues)
    if len(values) == 1:
        return 0.0
    gaps = [
        values[index + 1] - values[index]
        for index in range(len(values) - 1)
    ]
    gaps.append(values[0] + 360 - values[-1])
    return round(360 - max(gaps), 2)


def build(icon_source: Path, palette_source: Path, animation_audit: Path) -> dict[str, Any]:
    icon_text = _read(icon_source)
    palette_text = _read(palette_source)
    icons = _icon_options(icon_text)
    colors = _folder_colors(palette_text)
    sectioned_colors = _sectioned_folder_colors(palette_text)
    icon_keys = {item["key"] for item in icons}
    color_values = set(colors)
    animation_visuals = _animation_visuals(animation_audit)
    missing_animation_icons = sorted(
        {
            str(item.get("recommended_icon_key") or "")
            for item in animation_visuals
            if item.get("recommended_icon_key") and item.get("recommended_icon_key") not in icon_keys
        }
    )
    missing_animation_colors = sorted(
        {
            _normalize_color(item.get("recommended_color_hex"))
            for item in animation_visuals
            if item.get("recommended_color_hex")
            and _normalize_color(item.get("recommended_color_hex")) not in color_values
        }
    )

    duplicate_icon_keys = [
        key for key, count in Counter(item["key"] for item in icons).items() if count > 1
    ]
    duplicate_colors = [color for color, count in Counter(colors).items() if count > 1]
    sections = _comment_sections(palette_text)
    palette_sort = _palette_sort_audit(sectioned_colors)
    palette_color_families = _palette_color_families(sectioned_colors)
    palette_picker_order = _palette_picker_order(sectioned_colors)

    return {
        "icon_count": len(icons),
        "icon_group_count": len(set(item["group"] for item in icons)),
        "icon_groups": Counter(item["group"] for item in icons).most_common(),
        "duplicate_icon_keys": duplicate_icon_keys,
        "color_count": len(colors),
        "unique_color_count": len(color_values),
        "duplicate_colors": duplicate_colors,
        "palette_sections": sections,
        "palette_section_count": len(sections),
        "palette_color_families": palette_color_families,
        "palette_picker_order": palette_picker_order,
        "palette_sort": palette_sort,
        "palette_sorted_by_family": palette_sort["section_order_matches_expected"]
        and palette_sort["sections_locally_sorted"],
        "animation_visual_count": len(animation_visuals),
        "missing_animation_icons": missing_animation_icons,
        "missing_animation_colors": missing_animation_colors,
        "animation_visuals_covered": not missing_animation_icons and not missing_animation_colors,
        "notes": [
            "Folder colors are grouped by adjacent color-family comment sections in app_palette_catalog.dart.",
            "Palette sorting is checked by color-family section order and local hue/lightness order.",
            "Use palette_picker_order for folder color pickers so visually similar colors stay adjacent.",
            "Animation category visual hints are considered covered only when every recommended icon key and color hex exists in the app catalogs.",
        ],
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# App Folder Visual Catalog Audit",
        "",
        f"- Icon count: `{payload['icon_count']}`",
        f"- Icon group count: `{payload['icon_group_count']}`",
        f"- Folder color count: `{payload['color_count']}`",
        f"- Unique folder color count: `{payload['unique_color_count']}`",
        f"- Palette section count: `{payload['palette_section_count']}`",
        f"- Palette sorted by family: `{payload['palette_sorted_by_family']}`",
        f"- Animation visuals covered: `{payload['animation_visuals_covered']}`",
        "",
        "## Palette Sections",
        "",
    ]
    for item in payload["palette_sections"]:
        lines.append(f"- `{item['section']}`: `{item['color_count']}` colors")
    lines.extend(["", "## Picker Order", ""])
    for family in payload["palette_color_families"]:
        preview = ", ".join(item["color"] for item in family["colors"][:5])
        suffix = "..." if len(family["colors"]) > 5 else ""
        lines.append(
            f"- `{family['sort_order']:02d}` `{family['section']}`: "
            f"`{family['color_count']}` colors ({preview}{suffix})"
        )
    lines.extend(["", "## Palette Sort", ""])
    lines.append(f"- Section order matches expected: `{payload['palette_sort']['section_order_matches_expected']}`")
    lines.append(f"- Sections locally sorted: `{payload['palette_sort']['sections_locally_sorted']}`")
    for item in payload["palette_sort"]["section_ranges"]:
        lines.append(
            f"- `{item['section']}`: `{item['colors']}` colors, "
            f"`{item['order_key']}`, sorted `{item['locally_sorted']}`"
        )
    lines.extend(["", "## Icon Groups", ""])
    for group, count in payload["icon_groups"]:
        lines.append(f"- `{group}`: `{count}` icons")
    lines.extend(["", "## Gaps", ""])
    lines.append(f"- Duplicate icon keys: `{payload['duplicate_icon_keys']}`")
    lines.append(f"- Duplicate colors: `{payload['duplicate_colors']}`")
    lines.append(f"- Missing animation icons: `{payload['missing_animation_icons']}`")
    lines.append(f"- Missing animation colors: `{payload['missing_animation_colors']}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--icon-source", type=Path, default=DEFAULT_ICON_SOURCE)
    parser.add_argument("--palette-source", type=Path, default=DEFAULT_PALETTE_SOURCE)
    parser.add_argument("--animation-audit", type=Path, default=DEFAULT_ANIMATION_AUDIT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build(args.icon_source, args.palette_source, args.animation_audit)
    args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown_output)
    print(
        json.dumps(
            {
                "icon_count": payload["icon_count"],
                "color_count": payload["color_count"],
                "palette_section_count": payload["palette_section_count"],
                "palette_sorted_by_family": payload["palette_sorted_by_family"],
                "animation_visuals_covered": payload["animation_visuals_covered"],
                "json": str(args.json_output),
                "markdown": str(args.markdown_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
