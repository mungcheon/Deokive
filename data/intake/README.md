# Agent Goods Intake

This folder is the staging area for goods data collected by agents.

Agents must save new collection results with the same JSON shape:

- New raw submissions: `data/intake/incoming/<agent>-<YYYYMMDD>-<topic>.json`
- Existing catalog image updates:
  `data/intake/image_updates/incoming/<agent>-<YYYYMMDD>-<topic>.json`
- Existing catalog field updates:
  `data/intake/field_updates/incoming/<agent>-<YYYYMMDD>-<topic>.json`
- Official source/campaign lists: `data/intake/sources/`
- Accepted and already merged new-goods submissions: `data/intake/processed/`
- Rejected or unsafe new-goods submissions: `data/intake/rejected/`
- Accepted/rejected image and field update files stay under their matching
  `image_updates/processed`, `image_updates/rejected`,
  `field_updates/processed`, or `field_updates/rejected` folders.

Before any submission can update the public DB, validate it:

```powershell
python -X utf8 tools/validate_agent_goods_intake.py data/intake/incoming/example-agent-run.json
```

Then review the dry-run import report:

```powershell
python -X utf8 tools/import_agent_goods_intake.py data/intake/incoming/example-agent-run.json
```

After the dry run looks correct, write the changes:

```powershell
python -X utf8 tools/import_agent_goods_intake.py data/intake/incoming/example-agent-run.json --write
```

For existing catalog field fixes, validate and dry-run with:

```powershell
python -X utf8 tools/validate_agent_catalog_field_updates.py data/intake/field_updates/incoming/example-agent-run.json
python -X utf8 tools/import_agent_catalog_field_updates.py data/intake/field_updates/incoming/example-agent-run.json
```

After the report looks correct, merge into the single public DB:

```powershell
python -X utf8 tools/import_agent_catalog_field_updates.py data/intake/field_updates/incoming/example-agent-run.json --write
```

Only `data/catalog_public.json` is the public DB. Intake files are evidence and
review material; they are not used directly by the app.
Do not create another DB JSON, SQLite file, or app-facing catalog under
`data/`, `server/`, or `lib/data/catalog/` for agent work. Agents submit
standard intake JSON here, then the importer merges accepted rows into the
single public DB.

Boss review is the final local approval gate before public DB changes are
considered publishable. Generate 10-item review batches with
`tools/build_catalog_boss_review_batch.py`, then import exported decisions with
`tools/import_catalog_boss_review_decisions.py`. Only `pass` and `fixed_pass`
decisions may proceed; `image_error` and `content_error` require another intake
or correction pass.

Use `data/intake/image_updates/` when an agent found images for existing catalog
rows. Those files update only `image_url` and, when supplied, `source_url`; they
do not create new goods rows.
Image work-pack drafts are generated under `server/image_update_work_packs/`;
copy only confirmed results into `data/intake/image_updates/incoming/`.
Image update validation checks `catalog_index` against `data/catalog_public.json`
and rejects rows that already have an image, so agents should submit only exact,
new, confirmed image fixes for currently missing-image rows.

Do not add custom fields. The validator rejects unknown top-level, agent, item,
and evidence keys so every agent run can be imported by the same pipeline.
Use `notes` for short human context that does not belong in a structured field.
Incoming filenames must stay traceable, for example
`hooke-20260727-ichiban-kuji.json`.

## Agent Output Contract

Every agent run should produce exactly one of these three payloads:

- New goods rows: use `templates/agent_goods_intake.template.json`.
- Image fixes for existing rows: use
  `image_updates/templates/agent_catalog_image_update.template.json`.
- Missing field fixes for existing rows: use
  `field_updates/templates/agent_catalog_field_update.template.json`.

Keep scratch searches, dry runs, screenshots, and generated review queues out of
`data/`. They can live locally under ignored `server/` work folders while being
reviewed, but only validated intake JSON should be committed.
Incoming, processed, and rejected intake files are all audited against the same
JSON contract, so archive files must remain machine-readable and cannot become
free-form notes or a second database.

Field updates are for missing public catalog values such as `source_url`,
`release_date`, `barcode`, official price, official-language names,
`character_name`, and `sub_series`. They are not a second DB and should not be
read by the app. The validator rejects unknown fields, missing catalog rows, and
attempts to fill a field that already has a value; use a dedicated manual
correction queue for replacements.

## Item Rules

- Use official language fields when available: `name_ja` for Japanese official
  names, `name_en` for English official names, and `name_ko` for Korean display
  text when already verified.
- For Ichiban Kuji items, `display_name` should follow:
  `Ichiban Kuji release name / prize rank / prize name / character name`.
- If a prize has several character variants in the same rank, create one item
  per character variant.
- `last_one` and `double_chance` prizes may use `official_price: 0` and
  `official_price_currency: "JPY"` when there is no normal retail price.
- Preserve currency explicitly. If the official price is yen, set
  `official_price_currency` to `JPY`; do not copy only the number into a KRW
  price field.
- `agent.collected_at` must be an ISO-8601 timestamp, for example
  `2026-07-27T00:00:00+09:00`.
- `evidence` is required and must include the same URL as `source_url`.
- Attach `image_url` when possible. Use product/detail pages, not generic search
  pages, for `source_url`.
- Set `confidence` to `confirmed`, `candidate`, or `needs_review`.
