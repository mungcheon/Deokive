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
