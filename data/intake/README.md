# Agent Goods Intake

This folder is the staging area for goods data collected by agents.

Agents must save new collection results with the same JSON shape:

- New raw submissions: `data/intake/incoming/<agent>-<run-id>.json`
- Official source/campaign lists: `data/intake/sources/`
- Accepted and already merged submissions: `data/intake/processed/`
- Rejected or unsafe submissions: `data/intake/rejected/`

Before any submission can update the public DB, validate it:

```powershell
python -X utf8 tools/validate_agent_goods_intake.py data/intake/incoming/example-agent-run.json
```

Only `data/catalog_public.json` is the public DB. Intake files are evidence and
review material; they are not used directly by the app.

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
- Attach both `source_url` and `image_url` when possible. Use product/detail
  pages, not generic search pages, for `source_url`.
- Set `confidence` to `confirmed`, `candidate`, or `needs_review`.
