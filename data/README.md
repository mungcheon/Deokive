# Deokive Public Data

`data/catalog_public.json` is the only public catalog database for the GitHub
Pages site.

Other generated files in this repository are reports, review queues, import
dry-runs, or source-discovery work products. They are not database sources of
truth and should not be treated as app data.

Agent-collected raw goods data must go through `data/intake/` first. Do not add
new ad-hoc JSON files to this folder root. The layout audit checks both tracked
files and local files, so stray DB-like JSON files under `data/` should be moved
into the proper intake folder or removed before publishing.

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

Check total progress at any time with:

```powershell
python -X utf8 tools/catalog_boss_review_status.py
```

Open `server/boss_review/catalog_boss_review.html` locally, review each item,
and use `다음 배치 검토하기` to continue through the catalog in 10-row batches.
The browser stores review decisions locally. Only `pass` and `fixed_pass`
decisions are treated as approved; `image_error` and `content_error` stay
blocked. If you need a backup or want to build local approved/rework artifacts,
save the backup JSON and import it with:

```powershell
python -X utf8 tools/import_catalog_boss_review_decisions.py path\to\boss_review_0_9.json
```

To continue review immediately after finishing a batch, use the advance helper:

```powershell
python -X utf8 tools/advance_catalog_boss_review.py path\to\boss_review_0_9.json
```

It imports the decisions, updates the approved/rework local artifacts, and
regenerates `server/boss_review/catalog_boss_review.html` for the next
unreviewed 10 rows.

This creates an approved-only local candidate at
`server/boss_review/catalog_public_approved.json`. It is a review artifact, not
a second public DB. Blocked rows are written to
`server/boss_review/boss_review_rework_queue.json` so `image_error` rows can go
back through `data/intake/image_updates/` and `content_error` rows can go back
through `data/intake/field_updates/`. After approval, a separate merge step may
update `data/catalog_public.json`.

## Missing Image Source Discovery

Missing-image work starts from the current generated image queue, not from a
second data file. Build the local source-discovery starter report with:

```powershell
python -X utf8 tools/build_image_enrichment_queue.py
python -X utf8 tools/build_missing_image_priority_public.py --write
```

This reads `server/catalog_image_enrichment_queue_current.json` and writes local
reports under `server/`:

- `server/catalog_missing_image_priority_public.json`
- `server/source_discovery_starter_queue_public.json`
- `server/source_discovery_starter_queue_public.html`
- `server/source_discovery_next_batch_image_update.template.json`

Rows without an exact `source_url` must get a confirmed official or licensed
product/detail page before any image is attached. The starter queue is review
only; it does not auto-apply catalog changes. The generated template starts with
`confidence: needs_review`; copy confirmed rows into
`data/intake/image_updates/incoming/`, replace the TODO URLs, and set only
verified rows to `confidence: confirmed` before importing.

## Ichiban Kuji Quality Review

Historical Ichiban Kuji rows use a local review queue for campaign gaps,
reissue/duplicate decisions, zero-price policy checks, and display-name
convention fixes:

```powershell
python -X utf8 tools/build_ichiban_public_quality_queue.py
```

This writes local review artifacts under `server/`:

- `server/ichiban_public_quality_queue.html`
- `server/ichiban_public_quality_queue.json`
- `server/ichiban_public_quality_queue.csv`

The HTML board is review-only. Do not merge or delete suspected duplicate rows
unless the evidence proves the campaign, prize rank, prize name, character, and
source identity are the same. Keep separate rows when source URLs prove a
reissue or separate campaign.

## Animation Goods Enrichment

Animation goods source/image work uses the public catalog as its default input
so generated intake templates use real `catalog_index` values:

```powershell
python -X utf8 tools/build_animation_enrichment_priority_queue.py
```

This writes local review artifacts under `server/`:

- `server/animation_enrichment_priority_queue.html`
- `server/animation_enrichment_priority_queue.json`
- `server/animation_enrichment_priority_queue.csv`
- `server/animation_next_batch_image_update.template.json`

The generated image update template is review-only and starts with
`confidence: needs_review`. Replace the TODO URLs and set only verified exact
product/detail matches to `confidence: confirmed` before importing through the
image update intake flow.
