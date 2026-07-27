import '../../models/goods_catalog_entry.dart';
import 'seed_catalog.dart';

/// Aggregated read-only view generated from the canonical public seed.
List<GoodsCatalogEntry> get kFullCatalog => kSeedCatalog;

/// Distinct catalog categories across all stores.
List<String> catalogCategories() {
  final set = <String>{};
  for (final e in kFullCatalog) {
    final category = e.normalizedCategory.trim();
    if (category.isNotEmpty) set.add(category);
  }
  final out = set.toList()..sort();
  return out;
}

/// Distinct catalog characters across all stores.
List<String> catalogCharacterNames() {
  final set = <String>{};
  for (final e in kFullCatalog) {
    if (e.characterName.isNotEmpty) set.add(e.characterName);
  }
  final out = set.toList()..sort();
  return out;
}

/// Distinct catalog series names across all stores. Currently NOT used by
/// the goods input auto-fill because series labels are user-edited.
List<String> catalogSeriesNames() {
  final set = <String>{};
  for (final e in kFullCatalog) {
    final value = e.seriesName?.trim() ?? '';
    if (value.isNotEmpty && !_isOfficialMarketSeriesLabel(e, value)) {
      set.add(value);
    }
  }
  final out = set.toList()..sort();
  return out;
}

bool _isOfficialMarketSeriesLabel(GoodsCatalogEntry entry, String value) {
  final normalized = value.toLowerCase().replaceAll(RegExp(r'\s+'), '');
  final store = entry.sourceStore.toLowerCase().replaceAll(RegExp(r'\s+'), '');
  final subSeries =
      (entry.subSeries ?? '').toLowerCase().replaceAll(RegExp(r'\s+'), '');
  if (store.isNotEmpty && normalized == store) return true;
  if (subSeries == '공식마켓' || subSeries == 'officialmarket') return true;
  return normalized == '공식마켓' ||
      normalized == 'officialmarket' ||
      normalized == 'officialstore' ||
      normalized == 'officialshop';
}

/// Distinct catalog affiliations across all stores.
List<String> catalogAffiliations() {
  final set = <String>{};
  for (final e in kFullCatalog) {
    if (e.affiliation.isNotEmpty) set.add(e.affiliation);
  }
  final out = set.toList()..sort();
  return out;
}
