# Deokive

Deokive is a Flutter Web app for organizing character goods, browsing a curated goods catalog, and checking goods-related news in a mobile-first interface.

The public GitHub Pages deployment is designed as a static, read-only site. It can run without a live backend by using catalog and news data bundled into the web build.

## Features

- Mobile-first goods archive UI
- Folder-style goods organization
- Curated goods catalog search
- Goods statistics and collection views
- Calendar and board-style news views
- Static GitHub Pages deployment
- Scheduled catalog data refresh through GitHub Actions

## Public Site Mode

The GitHub Pages build uses:

```bash
--dart-define=DEOKIVE_STATIC_SITE=true
```

In this mode, community write actions such as posting, comments, likes, and edits are disabled. The site reads bundled catalog/news data only, which keeps the public deployment simple and safe.

## Local-Only Personal Data

Personal data is local-only by default:

- Profile nickname and avatar
- Owned goods and folders
- Local account information
- Local board drafts, comments, likes, and bookmarks

The app uses:

```bash
--dart-define=DEOKIVE_PERSONAL_DATA_LOCAL_ONLY=true
```

This is also the default when no value is provided. Personal API calls for auth, device profiles, profile sync, board posting, comments, views, and likes are disabled unless a private build explicitly sets this value to `false`.

## GitHub Pages

The repository includes:

- `.github/workflows/deploy-pages.yml`
- `web/CNAME`

The custom domain is:

```txt
deokive.kro.kr
```

To use GitHub Pages for free, the repository must be public. In GitHub:

1. Open `Settings`
2. Go to `Pages`
3. Set `Source` to `GitHub Actions`
4. Make sure the domain points to GitHub Pages with a DNS CNAME:

```txt
deokive -> mungcheon.github.io
```

## Catalog DB

The public catalog has one source of truth:

```txt
data/catalog_public.json
```

`lib/data/catalog/seed_catalog.dart` is generated from that JSON for Flutter
Web. Do not edit the Dart seed by hand.

Agent-collected goods data must be saved under `data/intake/` and validated
before it is merged into the public DB:

```bash
python -X utf8 tools/validate_agent_goods_intake.py data/intake/incoming
```

Files such as reports, queues, dry-run outputs, and source-discovery notes are
work products only. They are not app databases.

## Catalog Updates

Catalog data is updated by:

- `.github/workflows/update-catalog.yml`
- `tools/sync_catalog_pipeline.py`

The workflow updates generated catalog files and the public DB JSON. Runtime SQLite databases are intentionally not committed.

For cautious image enrichment, run the workflow manually and provide an optional `image_provider_store` such as `FuRyu`, `goodsmile`, `Taito`, or `Banpresto`. Scheduled runs leave this blank.

The static app catalog is generated from `data/catalog_public.json` into `lib/data/catalog/seed_catalog.dart`, so GitHub Pages can search the public catalog without a backend.

Local SQLite databases can still be checked against the same public seed with `tools/audit_catalog_db_sync.py`. That audit is part of the catalog reports, but the public GitHub Pages deployment only needs the generated JSON and Dart catalog files.

## Local Development

```bash
flutter pub get
flutter run -d chrome
```

Build the same static site that GitHub Pages publishes:

```bash
flutter build web --release --base-href "/" --dart-define=DEOKIVE_STATIC_SITE=true
```

## Backend Note

The public site does not require a running backend. The `server/` folder is kept only for private/local experiments and future admin tooling. Do not commit `.env`, live SQLite databases, Firebase config files, tokens, or private keys.

## Privacy And Public Repository Notes

This repository is intended to be safe for public hosting:

- Live user data and local SQLite databases are ignored.
- Firebase config files are not committed.
- Secrets should be provided through environment variables or GitHub Secrets.
- Generated public catalog data may be committed because it does not contain user data.
