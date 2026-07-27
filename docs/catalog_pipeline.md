# Deokive Catalog Pipeline

This project treats `data/catalog_public.json` as the only public catalog DB.
Flutter static catalog files are generated from that JSON so GitHub Pages can
search the catalog without a backend.

Runtime SQLite files and agent work products are local/admin artifacts. They
must not become additional public DB sources.

## Agent Intake

Agents must save newly collected goods data under `data/intake/incoming/` using
the shared schema in `data/intake/agent_goods_intake.schema.json`.

Validate intake files before import:

```powershell
python -X utf8 tools/validate_agent_goods_intake.py data/intake/incoming
```

After a reviewed intake file is merged into `data/catalog_public.json`, move it
to `data/intake/processed/`. Unsafe or mismatched submissions belong in
`data/intake/rejected/`.

Do not add new ad-hoc DB-like JSON files to the `data/` root. Root-level reports
and queues are temporary/generated work products, not app databases.

## Normal Update

GitHub Actions runs the public catalog update on schedule and can also be run
manually from the repository Actions tab. It validates agent intake, imports safe
incoming goods into `data/catalog_public.json`, regenerates local/admin quality
queues, regenerates the Flutter static seed, and audits the public data layout.

For the same local preflight, run:

```powershell
python tools/validate_agent_goods_intake.py data/intake/incoming
python tools/import_agent_goods_intake.py data/intake/incoming
python tools/catalog_quality_report.py
python tools/build_catalog_naming_quality_queue.py
python tools/build_ichiban_public_quality_queue.py
python tools/build_image_enrichment_queue.py
python tools/audit_public_catalog_image_assets.py --write
python tools/sync_missing_image_work_queue_public.py
python tools/build_catalog_update_backlog.py
python tools/generate_seed_catalog_dart.py --input data/catalog_public.json --output lib/data/catalog/seed_catalog.dart
python tools/audit_flutter_seed_matches_public.py
python tools/audit_public_data_layout.py
```

Use `--write` only on the intake importer after reviewing its dry-run report:

```powershell
python tools/import_agent_goods_intake.py data/intake/incoming --write
```

## Individual Tools

- `tools/catalog_quality_report.py`: reads `data/catalog_public.json` and writes the local/admin report `server/catalog_quality_report.json`, including duplicate checks, missing-field breakdowns, character-name review counts, and Ichiban Kuji naming/price/campaign quality queues.
- `tools/build_catalog_naming_quality_queue.py`: writes the local/admin character-name and Ichiban display-name review queue to `server/catalog_naming_quality_queue.json` and `.csv`.
- `tools/catalog_text_quality_report.py`: writes `server/catalog_text_quality_report.json` for mojibake/replacement-character checks.
- `tools/normalize_catalog_seed.py`: normalizes category/store/text fields.
- `tools/dedupe_catalog.py`: removes duplicate seed rows; use `--dart` for Dart catalog files.
- `tools/dedupe_catalog_db.py`: marks duplicate SQLite rows inactive instead of deleting them.
- `tools/sync_chiikawa_market.py`: refreshes official Chiikawa Market rows from public Shopify JSON.
- `tools/enrich_chiikawa_market_fields.py`: fills empty legacy Chiikawa Market fields from official product JSON, including exact image filename/JAN matches from official Shopify CDN URLs.
- `tools/discover_ichiban_kuji_campaigns.py`: discovers official historical 1kuji campaign detail URLs from `https://1kuji.com/products/search` plus the official `/products/more` JSON endpoint, then merges them into `data/intake/sources/ichiban_kuji_campaigns.json`.
- `tools/import_ichiban_kuji_history.py`: imports explicitly listed Ichiban Kuji campaign pages.
- `tools/enrich_ichiban_kuji_fields.py`: revisits existing official 1kuji detail URLs and fills missing campaign-level price/release date fields without re-importing every prize row.
- `tools/import_anymy_kuji_history.py`: imports explicitly listed AnyMy Kuji campaign pages.
- `tools/import_chiikawa_online_kuji_history.py`: imports Chiikawa Market official online lottery campaigns from the public JSON API.
- `tools/enrich_chiikawa_online_kuji_fields.py`: fills existing online-kuji rows with campaign release date, 1-draw price, and source store from the public JSON API.
- `tools/enrich_source_urls_from_image_paths.py`: derives official detail `source_url` and release date from already-verified official CDN image paths, currently for conservative Banpresto/FuRyu patterns.
- `tools/enrich_catalog_fields_from_providers.py`: fills non-image catalog fields from strict official provider matches; current unattended provider is FuRyu exact-title API matching.
- `tools/enrich_fanding_store_from_shop_api.py`: fills exact unique Stellive/Fanding product matches and writes review-only fuzzy candidate queues.
- `tools/enrich_images_from_source_url.py`: fills missing images from existing product page metadata.
- `tools/enrich_catalog_images.py`: runs strict official image providers for selected stores and can attach both `image_url` and `source_url`; dry-run reports include unresolved query diagnostics, candidate counts, and rejected top candidates for provider debugging.
- `tools/enrich_official_source_urls.py`: fills missing source URLs with verified official source pages for store-level sources.
- `tools/propagate_catalog_fields.py`: safely fills empty fields from exact intra-seed groups, currently using strong image/source constraints.
- `tools/prune_unverified_catalog_rows.py`: removes kuji rows without an official source URL so temporary/manual prize sketches do not enter the public seed.
- `tools/generate_seed_catalog_dart.py`: generates `lib/data/catalog/seed_catalog.dart` from `data/catalog_public.json` for static GitHub Pages search/autocomplete.
- `tools/audit_public_data_layout.py`: verifies the single public DB layout, intake source lists, site status file, and incoming agent payloads.
- `tools/audit_public_catalog_image_assets.py --write`: reads `data/catalog_public.json` and writes the local/admin image asset report `server/catalog_image_asset_audit.json`.
- `tools/build_image_enrichment_queue.py`: writes the local/admin missing-image work queue to `server/catalog_image_enrichment_queue_current.json` and `.csv`.
- `tools/sync_missing_image_work_queue_public.py --write`: refreshes the simpler local missing-image queue in `server/catalog_missing_image_work_queue_current.json` and `.csv`.
- `tools/build_ichiban_public_quality_queue.py`: writes the local/admin Ichiban Kuji campaign-gap and reissue/duplicate review queue to `server/ichiban_public_quality_queue.json` and `.csv`.
- `tools/sync_catalog_db_active.py`: deactivates DB catalog rows that are no longer present in the canonical seed, inserts missing seed rows, and updates active DB rows when canonical seed fields change.
- `tools/build_catalog_source_coverage.py`: summarizes source, affiliation, category, animation goods, and kuji coverage.
- `tools/build_image_enrichment_queue.py`: writes JSON/CSV queues for missing image follow-up.
- `tools/build_image_provider_smoke_matrix.py`: summarizes provider dry-run coverage from the latest image queue. Run it after `tools/build_image_enrichment_queue.py`; running both in parallel can make the smoke matrix read a stale queue.
- `tools/build_current_image_candidate_reconciliation.py`: rechecks older image candidate JSON files against the current seed and, with `--validate-live-title`, rejects stale candidates whose live product page title no longer identifies the current row.
- `tools/build_official_detail_match_queue.py`: builds review-only official product-detail candidates from image enrichment queue items and writes JSON/CSV/Markdown plus `server/official_detail_match_review.html`.
- `tools/build_official_detail_review_batches.py`: groups official-detail candidates by seed row, excludes rows that already have both `source_url` and `image_url`, and writes prioritized JSON/CSV/Markdown/HTML review batches.
- `tools/import_confirmed_official_detail_matches.py`: imports only manually confirmed official-detail matches from `server/official_detail_match_confirmed_rows.json` or the template fallback.
- `tools/build_storefront_match_review.py`: combines generic storefront and Fanding fuzzy queues into `server/storefront_match_review.html` plus a confirmation template.
- `tools/build_storefront_review_batches.py`: groups storefront/Fanding review candidates by seed row, hides completed rows, and writes prioritized JSON/CSV/Markdown/HTML batches.
- `tools/import_confirmed_storefront_matches.py`: imports only manually confirmed storefront product URL/image matches.
- `tools/build_ichiban_kuji_gap_work_queue.py`: writes JSON/CSV/Markdown plus `server/ichiban_kuji_gap_work_queue.html` to organize missing historical 1kuji campaigns by review workflow before import.
- `tools/build_ichiban_kuji_ocr_review_queue.py`: writes JSON/CSV/Markdown plus `server/ichiban_kuji_ocr_review.html` for image-only historical 1kuji prize lineups that need OCR/manual prize names.
- `tools/build_catalog_field_enrichment_queue.py`: writes JSON/CSV/Markdown plus `server/catalog_field_enrichment_review.html` and a confirmation template for source URL, image, release date, barcode, and price follow-up.
- `tools/import_confirmed_catalog_field_rows.py`: imports only manually confirmed field values with validation for exact evidence URLs, store/domain compatibility, URL safety, barcode/date/price format, and existing-field conflicts.
- `tools/build_catalog_update_backlog.py`: summarizes field, image, source, priority-goods, naming, and Ichiban quality queues into next update actions.
- `tools/build_requested_special_goods_queue.py`: compares `data/requested_special_goods.json` with the current seed, writes `server/requested_special_goods_review.html`, and creates a manual seed template for requested collections that are still missing.
- `tools/audit_catalog_report_consistency.py`: verifies that quality, field queue, field review batches, image queue, and image review batches all describe the same current seed counts. Run it after regenerating those reports and before dashboard decisions.
- `tools/audit_catalog_goal_status.py`: writes `server/catalog_goal_status_audit.html` and Markdown/JSON goal dashboards with review queues and prioritized next actions.
- `tools/probe_image_providers.py`: probes official image providers without changing the seed.
- `tools/cache_catalog_images.py`: dry-run image URL cache helper. Use image caching conservatively.

## Source Lists

- `data/intake/sources/ichiban_kuji_campaigns.json`: official 1kuji campaign pages that can be merged by `tools/import_ichiban_kuji_history.py`.
- `data/intake/sources/anymy_kuji_campaigns.json`: official AnyMy campaign pages that can be merged by `tools/import_anymy_kuji_history.py`.
- `data/intake/sources/chiikawa_online_kuji_campaigns.json`: Chiikawa Market official online lottery pages imported by `tools/import_chiikawa_online_kuji_history.py`.

Ichiban Kuji coverage notes:

- `data/intake/sources/ichiban_kuji_campaigns.json` is kept to official `https://1kuji.com/products/...` campaign detail pages.
- Use `tools/discover_ichiban_kuji_campaigns.py --category kimetsu --write` to add a verified official history slice. Supported category aliases include `one_piece`, `dragon_ball`, `my_hero_academia`, `gundam`, `kimetsu`, `jojo`, `haikyu`, `kirby`, `naruto`, `jujutsu`, `spy_family`, and `hololive`.
- The current 2026 coverage was checked against the official monthly lineup pages using `sale_year` and `sale_month` query parameters, for example `https://1kuji.com/products?sale_month=7&sale_year=2026`.
- Before adding a campaign URL, verify that the detail page title contains the monthly lineup title and that the page exposes prize blocks (`itemColList`) for `tools/import_ichiban_kuji_history.py`.
- The importer records unreachable detail pages in `server/ichiban_kuji_history_import_report.json` and continues, because official search can retain stale campaign links that now return 404.
- Chiikawa 1kuji coverage currently has the four verified official detail pages: `chiikawa`, `chiikawa2`, `chiikawa3`, and `chiikawa4`. Direct checks for likely later slugs such as `chiikawa5`, `chiikawa_5`, `chiikawa2026`, and `chiikawa2024` returned 404 as of 2026-07-18.

## Image Queue Notes

`server/catalog_image_enrichment_queue_current.csv` is sorted by `priority`:

- `10 official_search`: official store search pages with a stable search URL.
- `20 manual_official_search_review`: official search pages that are useful for review but do not yet have safe unattended detail matching.
- `20 prize_maker_search`: prize maker search pages. Review before writing because broad search result pages can return unrelated current products.
- `30 manual_review`: rows that need a new official source or manual verification.

Current conservative automation:

- `FuRyu`: `tools/enrich_catalog_images.py --store FuRyu` uses the official search API and currently only writes strict matches; many older seed rows are no longer returned by the public API.
- `FuRyu` field enrichment: `tools/enrich_catalog_fields_from_providers.py --store furyu` can attach exact-match official detail URLs and `YYYY-MM` release months from the public API.
- `Goodsmile`: `goodsmile.info` search is supported in the image tool, but only exact title matches are accepted because fuzzy results can point to different variants.
- `Animate`: official search parsing supports current result markup and can attach product `source_url` with strict matches.
- `Ensky`: sitemap cache is supported but slow and should be run in small batches.
- `Taito`: official API matching is supported for current-catalog strict matches.
- `Banpresto`: search results are followed to detail pages and accepted only after strong title validation.
- `Banpresto` image-path enrichment: if an existing trusted `bsp-prize.jp` image URL exposes an item code, `tools/enrich_source_urls_from_image_paths.py` verifies the derived detail page title before writing source/date fields.
- `Kotobukiya`, `Movic`: search candidates are followed to detail pages and accepted only for exact or near-contained title matches.
- `Chiikawa Market` `ご当地` rows are not covered by the public Shopify JSON and need a separate official regional-goods source.
- Reused manual image candidates must be rechecked with `tools/build_current_image_candidate_reconciliation.py --validate-live-title` before import. If importing a reconciliation output, dry-run `tools/import_manual_image_candidates.py` with `--require-live-title-exact`; this prevents stale row indexes or visually similar product pages from being written.

GitHub Actions can run the normal public catalog update on schedule. The
workflow uses only tracked public-data tools and commits `data/catalog_public.json`,
`data/catalog_public_meta.json`, `data/site_status_public.json`,
`data/intake`, generated Flutter seed data, and catalog image assets when they
change. Runtime SQLite files and broad local scraping pipelines stay out of the
GitHub Pages path.

Agent-reviewed image and goods candidates should now be dropped into
`data/intake/incoming/` using the shared intake schema. The pipeline imports only
preflight-safe candidate/source pairs after validation. Unsafe or already-filled
candidates stay documented in review output instead of being written blindly.

The pipeline also refreshes `server/agent_image_candidates_import_queue_broad.*`
from older image candidate files. This broad queue rechecks historical candidates
against the current seed so safe leftovers can be found without trusting stale row
indexes, while mismatches remain documented as rejected review evidence.

The image queue JSON also includes grouped backlog views for planning:

- `by_strategy`, `by_store`, and `by_category` show broad missing-image volume.
- `top_strategy_stores` groups work by automation strategy and store.
- `top_store_categories` and `top_strategy_store_categories` show practical manual batches, such as one store/category pair to review at a time.
- `samples_by_store` gives small examples for each store without opening the full CSV.

## Official Detail Review

Use this flow for candidates that are promising but still need human product
identity review:

1. Run `python tools/build_official_detail_match_queue.py`.
2. Run `python tools/build_official_detail_review_batches.py` to collapse repeated candidates into seed-row review batches and hide already completed seed rows.
3. Open `server/official_detail_review_batches.html` first for prioritized review. Use `quick_disambiguation_two_candidates` and `quick_disambiguation_small_set` before broad manual batches.
4. Open `server/official_detail_match_review.html` when you need the full raw candidate list and status filters.
5. Copy confirmed JSON items into `server/official_detail_match_confirmed_rows.json`.
6. Set `manual_confirmed` to `true` only after the official detail page, image, and seed row are the exact same product.
7. Optionally fill `manual_barcode`, `manual_release_date`, or `manual_official_price_jpy` from the same official page.
8. Run `python tools/import_confirmed_official_detail_matches.py` as a dry-run, review `server/official_detail_match_import_report.json`, then rerun with `--write`.

The importer refuses unconfirmed rows, generic source URLs, unsafe source/image
pairs, non-unique seed matches, and existing-field conflicts. Broad official
search results should stay in review until a detail URL and product image are
verified together.

## Storefront Review

Use this flow for rows whose `source_url` still points to a shop home, search
page, or other generic storefront:

1. Run `python tools/enrich_fanding_store_from_shop_api.py` to refresh exact Fanding matches and fuzzy review candidates.
2. Run `python tools/build_generic_storefront_match_queue.py`.
3. Run `python tools/build_storefront_match_review.py`.
4. Run `python tools/build_storefront_review_batches.py` to collapse repeated candidates into seed-row review batches and hide already completed seed rows.
5. Open `server/storefront_review_batches.html` first and handle smaller candidate groups before broad manual batches.
6. Open `server/storefront_match_review.html` when you need the full raw candidate list and status filters.
7. Copy verified JSON items into `server/storefront_match_confirmed_rows.json`.
8. Set `manual_confirmed` to `true` only after the detail page and image identify the exact same seed row.
9. Run `python tools/import_confirmed_storefront_matches.py` as a dry-run, review `server/storefront_match_import_report.json`, then rerun with `--write`.

The storefront importer accepts product-specific URL/image pairs only. For
stores whose product URL pattern is not yet in `tools/image_enrichment_safety.py`,
leave the row in manual review instead of weakening the safety check.

## Ichiban Kuji OCR Review

Use this flow for historical official campaigns whose prize lineup exists only
as images:

1. Run `python tools/build_ichiban_kuji_gap_work_queue.py`.
2. Open `server/ichiban_kuji_gap_work_queue.html` and filter missing campaigns by workflow, such as `ocr_review`, `replacement_source_search`, or `online_archive_url_research`. For image-only campaigns, use the primary OCR candidate count and inferred tier codes to estimate the manual review workload before creating rows.
   The queue includes the campaign slug, source category, and an official search link for each gap so replacement URL research can start from the exact archived title.
3. Run `python tools/build_ichiban_kuji_ocr_review_queue.py` for campaigns classified as image-only prize lineups.
4. Open `server/ichiban_kuji_ocr_review.html` and inspect each primary image.
5. Copy verified JSON items into `server/ichiban_kuji_ocr_confirmed_rows.json`.
6. Fill `manual_prize_name_ja`; optionally fill `manual_prize_name_ko`.
7. Set `manual_confirmed` to `true` only after the tier, prize name, campaign, and image are verified.
8. Run `python tools/import_confirmed_ichiban_ocr_rows.py` as a dry-run, review `server/ichiban_kuji_ocr_import_report.json`, then rerun with `--write`.

The importer skips mobile/duplicate image variants and refuses rows without a
confirmed Japanese prize name.

## Field Queue Notes

`server/catalog_field_enrichment_queue.csv` is sorted by `priority` and covers
`source_url`, `image_url`, `release_date`, `barcode`, and
`official_price_jpy`.

The field queue JSON and Markdown include several grouped views:

- `by_source_group_field` shows which source group is missing each field.
- `top_store_fields` shows the largest store/field gaps.
- `top_strategy_store_fields` turns those gaps into actionable work buckets.
- `top_store_category_fields` is useful for manual passes where one category can be checked against the same source pattern.

`server/catalog_update_backlog.md` is the quickest human-facing summary. It
combines the field, image, source, priority-goods, naming, and Ichiban quality
queues, keeping separate sections for field strategies, store/category batches,
image strategies, image work packs, character/name cleanup, Ichiban
campaign/duplicate review packs, and recommended safe update order.

- For manual field backfill, open `server/catalog_field_enrichment_review.html`, copy JSON rows into `server/catalog_field_confirmed_rows.json`, fill `manual_value`, set `manual_confirmed=true`, then dry-run `python tools/import_confirmed_catalog_field_rows.py` before using `--write`.
- Confirmation templates are review aids only. Importers read `*_confirmed_rows.json` by default and return zero updates when that confirmed file does not exist.
- Fill barcodes only from official JAN/barcode fields or exact product detail pages.
- Fill release dates only from exact product or campaign pages.
- Treat generic official shop URLs as source pointers, not product identity keys.
- Keep broad search result rows in manual review until a strict detail matcher is verified.
- Use `image_work_packs` to assign image work by provider/status/store/category;
  each pack includes the safety level, next action, and sample rows.
- Use Ichiban `work_packs` to assign campaign gaps, reissue/duplicate decisions,
  and non-prize classification by workflow and campaign family.
- When a provider dry-run fills `0` rows, inspect the `unresolved[].reason`, `query`, `candidate_count`, and `top_candidates` fields before changing matcher thresholds.

## Safety Rules

- Run dry-run before `--write`.
- Keep product image URLs as source metadata unless reuse rights are clear.
- Do not scrape private/cart/account pages.
- Prefer official sources: Chiikawa Market JSON, official campaign pages, and official store pages.
- For Chiikawa Market legacy rows, Shopify product image filenames and JAN-like handles are valid identity evidence when they match the official `products.json` image or SKU.
- For SQLite cleanup, prefer `is_active = 0` over hard deletion.

## Verification

```powershell
python tools/catalog_quality_report.py
python tools/catalog_text_quality_report.py
python tools/build_catalog_source_coverage.py
python tools/build_image_enrichment_queue.py
python tools/build_catalog_field_enrichment_queue.py
python tools/audit_catalog_db_sync.py --fail-on-mismatch
python tools/audit_catalog_report_consistency.py --fail-on-mismatch
python tools/dedupe_catalog.py
python tools/dedupe_catalog.py --dart
python tools/dedupe_catalog_db.py
dart analyze lib\data\catalog\all.dart lib\data\catalog\anime.dart lib\data\catalog\chiikawa.dart lib\data\catalog\chiikawa_market_live.dart lib\models\goods_catalog_entry.dart
```
