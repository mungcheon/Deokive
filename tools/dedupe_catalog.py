"""
Remove duplicate GoodsCatalogEntry rows from each lib/data/catalog/*.dart
file. A duplicate = same (nameKo, characterName, affiliation, category).
When two entries share the dedupe key, the one with MORE fields (richer
metadata — nameJa, imageUrl, releaseDate etc.) wins. Ties: first occurrence
wins.

Usage:
    python tools/dedupe_catalog.py            # dry-run report
    python tools/dedupe_catalog.py --write    # actually rewrite files
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "lib" / "data" / "catalog"

# Capture each `GoodsCatalogEntry(...)` block (balanced parens are too
# expensive to parse with regex; we rely on the fact that no entry contains
# a literal `),\n  GoodsCatalogEntry(` substring inside it).
ENTRY_START = "GoodsCatalogEntry("
ENTRY_END_LOOKAHEAD = re.compile(r"\),\s*(?=GoodsCatalogEntry\(|\];)")

FIELD_RE = re.compile(r"(\w+)\s*:\s*('(?:[^'\\]|\\.)*'|[^,()]+)")


def parse_entries(text: str) -> list[tuple[int, int, dict[str, str]]]:
    """Return (start, end, fields) for every entry block in `text`.
    `start` and `end` are character offsets; `end` is the position AFTER
    the closing `),` (so text[start:end] is one full block including the
    trailing comma)."""
    out: list[tuple[int, int, dict[str, str]]] = []
    pos = 0
    while True:
        s = text.find(ENTRY_START, pos)
        if s < 0:
            break
        # Find the matching close — first `),` followed by another entry or `];`.
        m = ENTRY_END_LOOKAHEAD.search(text, s)
        if not m:
            break
        e = m.end()  # right after the `),` (and whitespace consumed by the regex? no)
        # The regex matches `),` plus optional whitespace via lookahead, but
        # the consumed match is just `),`. We want to swallow trailing newline
        # too so dedupe removal doesn't leave blank lines.
        while e < len(text) and text[e] in " \t":
            e += 1
        if e < len(text) and text[e] == "\n":
            e += 1
        block = text[s:e]
        fields: dict[str, str] = {}
        for fm in FIELD_RE.finditer(block):
            name = fm.group(1)
            val = fm.group(2).strip()
            if name not in fields:
                fields[name] = val
        out.append((s, e, fields))
        pos = e
    return out


def dedupe_key(fields: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        fields.get("nameKo", ""),
        fields.get("characterName", ""),
        fields.get("affiliation", ""),
        fields.get("category", ""),
    )


def richness(fields: dict[str, str]) -> int:
    return len(fields)


def process_file(path: Path, write: bool) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    entries = parse_entries(text)
    if not entries:
        return (0, 0)

    # Group by dedupe key; pick the richest (then first) as keeper.
    by_key: dict[tuple, list[int]] = {}
    for i, (_, _, f) in enumerate(entries):
        by_key.setdefault(dedupe_key(f), []).append(i)

    drop_indices: set[int] = set()
    for key, idxs in by_key.items():
        if len(idxs) < 2:
            continue
        if not any(key):
            continue  # skip entries with no identifying fields
        # Pick the richest. Ties: keep earliest.
        best = idxs[0]
        for j in idxs[1:]:
            if richness(entries[j][2]) > richness(entries[best][2]):
                best = j
        for j in idxs:
            if j != best:
                drop_indices.add(j)

    if not drop_indices:
        return (len(entries), 0)

    if write:
        # Rebuild text by skipping dropped blocks.
        parts: list[str] = []
        cursor = 0
        for i, (s, e, _) in enumerate(entries):
            parts.append(text[cursor:s])
            if i not in drop_indices:
                parts.append(text[s:e])
            cursor = e
        parts.append(text[cursor:])
        new_text = "".join(parts)
        path.write_text(new_text, encoding="utf-8")
    return (len(entries), len(drop_indices))


def main() -> int:
    write = "--write" in sys.argv
    total_entries = 0
    total_dropped = 0
    for path in sorted(CATALOG_DIR.glob("*.dart")):
        if path.name == "all.dart":
            continue
        entries, dropped = process_file(path, write=write)
        total_entries += entries
        total_dropped += dropped
        flag = "✏️ " if (write and dropped) else "  "
        print(f"{flag}{path.name:25s}  {entries:5d} entries  -{dropped}")
    label = "removed" if write else "would remove"
    print()
    print(f"Total: {total_entries} entries, {label} {total_dropped} duplicates")
    if not write:
        print("(dry run — re-run with --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
