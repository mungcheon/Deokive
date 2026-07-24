# Confirmed Import Queue Audit

- Workflows: `12`
- Confirmed files: `3`
- Manual confirmed rows: `0`
- Template candidate rows: `1143`
- Imported/updated rows: `0`
- Skipped rows: `14`
- Duplicate rows: `0`

## official_detail

- Status: `confirmed_file_has_no_confirmed_rows`
- Review artifact: `server/official_detail_match_review.html`
- Confirmed file exists: `True`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `0`
- Import updated rows: `0`
- Import skipped rows: `0`
- Import duplicates: `0`
- Dry-run command: `python tools/import_confirmed_official_detail_matches.py --queue server/official_detail_match_confirmed_rows.json --report server/official_detail_match_import_report.json`
- Write command: `python tools/import_confirmed_official_detail_matches.py --queue server/official_detail_match_confirmed_rows.json --report server/official_detail_match_import_report.json --write`
- Next action: Open the confirmed file and mark only exact verified rows manual_confirmed=true, or replace it from the current template.

## storefront

- Status: `needs_manual_review`
- Review artifact: `server/storefront_match_review.html`
- Confirmed file exists: `False`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `0`
- Import updated rows: `0`
- Import skipped rows: `0`
- Import duplicates: `0`
- Dry-run command: `python tools/import_confirmed_storefront_matches.py --queue server/storefront_match_confirmed_rows.json --report server/storefront_match_import_report.json`
- Write command: `python tools/import_confirmed_storefront_matches.py --queue server/storefront_match_confirmed_rows.json --report server/storefront_match_import_report.json --write`
- Next action: No current storefront candidates were found.

## catalog_field

- Status: `template_ready_no_confirmed_file`
- Review artifact: `server/catalog_field_enrichment_review.html`
- Confirmed file exists: `False`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `500`
- Import updated rows: `0`
- Import skipped rows: `12`
- Import duplicates: `0`
- Dry-run command: `python tools/import_confirmed_metadata_rows.py --queue server/catalog_field_confirmed_rows.json --report server/catalog_field_confirmed_import_report.json`
- Write command: `python tools/import_confirmed_metadata_rows.py --queue server/catalog_field_confirmed_rows.json --report server/catalog_field_confirmed_import_report.json --write`
- Next action: Copy the template to the confirmed_rows JSON, mark exact rows manual_confirmed=true, dry-run first, then run: python tools/import_confirmed_metadata_rows.py --queue server/catalog_field_confirmed_rows.json --report server/catalog_field_confirmed_import_report.json --write
- Skip reason `manual_confirmed_false`: `12`

## source_discovery

- Status: `template_ready_no_confirmed_file`
- Review artifact: `server/source_discovery_review_batches_public.html`
- Confirmed file exists: `False`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `641`
- Import updated rows: `None`
- Import skipped rows: `None`
- Import duplicates: `None`
- Dry-run command: `python tools/import_confirmed_source_discovery_rows.py --queue server/source_discovery_confirmed_rows.json --report server/source_discovery_confirmed_import_report.json`
- Write command: `python tools/import_confirmed_source_discovery_rows.py --queue server/source_discovery_confirmed_rows.json --report server/source_discovery_confirmed_import_report.json --write`
- Next action: Copy the template to the confirmed_rows JSON, mark exact rows manual_confirmed=true, dry-run first, then run: python tools/import_confirmed_source_discovery_rows.py --queue server/source_discovery_confirmed_rows.json --report server/source_discovery_confirmed_import_report.json --write

## catalog_image

- Status: `needs_manual_review`
- Review artifact: `server/catalog_image_review_batches.html`
- Confirmed file exists: `False`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `0`
- Import updated rows: `None`
- Import skipped rows: `None`
- Import duplicates: `None`
- Dry-run command: `python tools/import_confirmed_image_attachment_rows.py --queue server/catalog_image_attachment_confirmed_rows.json --report server/catalog_image_attachment_confirmed_import_report.json`
- Write command: `python tools/import_confirmed_image_attachment_rows.py --queue server/catalog_image_attachment_confirmed_rows.json --report server/catalog_image_attachment_confirmed_import_report.json --write`
- Next action: No current catalog_image candidates were found.

## focus_image

- Status: `needs_manual_review`
- Review artifact: `server/focus_missing_image_queue_current.html`
- Confirmed file exists: `False`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `0`
- Import updated rows: `None`
- Import skipped rows: `None`
- Import duplicates: `None`
- Dry-run command: `python tools/import_confirmed_requested_focus_rows.py --queue server/requested_focus_confirmed_rows.json --report server/requested_focus_confirmed_import_report.json`
- Write command: `python tools/import_confirmed_requested_focus_rows.py --queue server/requested_focus_confirmed_rows.json --report server/requested_focus_confirmed_import_report.json --write`
- Next action: No current focus_image candidates were found.

## variant_metadata

- Status: `confirmed_file_has_no_confirmed_rows`
- Review artifact: `data/source_discovery_next_focus_variant_metadata_confirmed_rows.template.json`
- Confirmed file exists: `True`
- Confirmed items: `2`
- Manual confirmed true: `0`
- Template items: `2`
- Import updated rows: `0`
- Import skipped rows: `2`
- Import duplicates: `0`
- Dry-run command: `python tools/import_confirmed_variant_metadata_backfill_rows.py`
- Write command: `python tools/import_confirmed_variant_metadata_backfill_rows.py --write`
- Next action: Open the confirmed file and mark only exact verified rows manual_confirmed=true, or replace it from the current template.
- Skip reason `manual_confirmed_false`: `2`

## ichiban_ocr

- Status: `confirmed_file_has_no_confirmed_rows`
- Review artifact: `server/ichiban_kuji_ocr_review.html`
- Confirmed file exists: `True`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `0`
- Import updated rows: `0`
- Import skipped rows: `0`
- Import duplicates: `0`
- Dry-run command: `python tools/import_confirmed_ichiban_ocr_rows.py --queue server/ichiban_kuji_ocr_confirmed_rows.json --report server/ichiban_kuji_ocr_import_report.json`
- Write command: `python tools/import_confirmed_ichiban_ocr_rows.py --queue server/ichiban_kuji_ocr_confirmed_rows.json --report server/ichiban_kuji_ocr_import_report.json --write`
- Next action: Open the confirmed file and mark only exact verified rows manual_confirmed=true, or replace it from the current template.

## ichiban_sub_series

- Status: `needs_manual_review`
- Review artifact: `server/ichiban_kuji_sub_series_review_batches.html`
- Confirmed file exists: `False`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `0`
- Import updated rows: `0`
- Import skipped rows: `0`
- Import duplicates: `0`
- Dry-run command: `python tools/import_confirmed_catalog_field_rows.py --queue server/ichiban_kuji_sub_series_confirmed_rows.json --report server/ichiban_kuji_sub_series_confirmed_import_report.json`
- Write command: `python tools/import_confirmed_catalog_field_rows.py --queue server/ichiban_kuji_sub_series_confirmed_rows.json --report server/ichiban_kuji_sub_series_confirmed_import_report.json --write`
- Next action: No current ichiban_sub_series candidates were found.

## ichiban_metadata

- Status: `needs_manual_review`
- Review artifact: `server/ichiban_kuji_metadata_review_batches_public.html`
- Confirmed file exists: `False`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `0`
- Import updated rows: `None`
- Import skipped rows: `None`
- Import duplicates: `None`
- Dry-run command: `python tools/import_confirmed_ichiban_metadata_rows.py --queue server/ichiban_kuji_metadata_confirmed_rows.json --report server/ichiban_kuji_metadata_confirmed_import_report.json`
- Write command: `python tools/import_confirmed_ichiban_metadata_rows.py --queue server/ichiban_kuji_metadata_confirmed_rows.json --report server/ichiban_kuji_metadata_confirmed_import_report.json --write`
- Next action: No current ichiban_metadata candidates were found.

## animation_category

- Status: `needs_manual_review`
- Review artifact: `server/animation_category_review_batches_public.html`
- Confirmed file exists: `False`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `0`
- Import updated rows: `None`
- Import skipped rows: `None`
- Import duplicates: `None`
- Dry-run command: `python tools/import_confirmed_animation_category_rows.py --queue server/animation_category_confirmed_rows.json --report server/animation_category_confirmed_import_report.json`
- Write command: `python tools/import_confirmed_animation_category_rows.py --queue server/animation_category_confirmed_rows.json --report server/animation_category_confirmed_import_report.json --write`
- Next action: No current animation_category candidates were found.

## deduplication

- Status: `needs_manual_review`
- Review artifact: `server/catalog_deduplication_review_batches_public.html`
- Confirmed file exists: `False`
- Confirmed items: `0`
- Manual confirmed true: `0`
- Template items: `0`
- Import updated rows: `None`
- Import skipped rows: `None`
- Import duplicates: `None`
- Dry-run command: `python tools/import_confirmed_dedupe_decisions.py --queue server/catalog_dedupe_confirmed_decisions.json --report server/catalog_dedupe_confirmed_import_report.json`
- Write command: `python tools/import_confirmed_dedupe_decisions.py --queue server/catalog_dedupe_confirmed_decisions.json --report server/catalog_dedupe_confirmed_import_report.json --write`
- Next action: No current deduplication candidates were found.

