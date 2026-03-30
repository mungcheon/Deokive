# Deokive Refactor Starter

This starter refactors the single-file prototype into a multi-file Flutter app with:

- Home / Folders / Calendar / Settings tabs
- default folder creation
- editable folders with item counts
- folder detail grid with multi-select move/delete
- add goods screen with image picking
- local-first persistence using Hive CE
- local profile login state using flutter_secure_storage
- cleaner theme and reusable widgets

## Setup

1. Replace your `lib/` folder with the provided `lib/` files.
2. Merge the provided `pubspec.yaml` dependencies.
3. Run:
   - `flutter pub get`
   - `flutter run -d windows`

## Notes

- Login in this starter is **local profile login**, not remote OAuth.
- Images are copied into the app documents directory.
- Data persists locally between launches.
