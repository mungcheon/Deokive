# Deokive Public Data

`data/catalog_public.json` is the only public catalog database for the GitHub
Pages site.

Other generated files in this repository are reports, review queues, import
dry-runs, or source-discovery work products. They are not database sources of
truth and should not be treated as app data.

Agent-collected raw goods data must go through `data/intake/` first. Do not add
new ad-hoc JSON files to this folder root.
The layout audit checks both tracked files and local files, so stray DB-like
JSON files under `data/` should be moved into the proper intake folder or
removed before publishing.

## Allowed Root Files

- `catalog_public.json`: canonical public goods catalog.
- `catalog_public_meta.json`: small publication metadata for the catalog.
- `site_status_public.json`: small static status flag for maintenance notices.

Everything else should be generated from tools or stored under `data/intake/`
until it is validated and merged into `catalog_public.json`.

## Boss Review Gate

The public catalog should not absorb bulk agent work directly. Generate local
10-item boss review batches under ignored `server/boss_review/` instead:

```powershell
python -X utf8 tools/build_catalog_boss_review_batch.py --batch-size 10
```

Open `server/boss_review/catalog_boss_review.html` locally, review each item,
and export the decision JSON. Only `pass` and `fixed_pass` decisions are treated
as approved; `image_error` and `content_error` stay blocked. Import decisions
locally with:

```powershell
python -X utf8 tools/import_catalog_boss_review_decisions.py path\to\boss_review_0_9.json
```

This creates an approved-only local candidate at
`server/boss_review/catalog_public_approved.json`. It is a review artifact, not
a second public DB. Blocked rows are written to
`server/boss_review/boss_review_rework_queue.json` so `image_error` rows can go
back through `data/intake/image_updates/` and `content_error` rows can go back
through `data/intake/field_updates/`. After approval, a separate merge step may
update `data/catalog_public.json`.
