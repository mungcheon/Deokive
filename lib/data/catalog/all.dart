import '../../models/goods_catalog_entry.dart';
import 'anime.dart';
import 'chiikawa.dart';
import 'game.dart';
import 'gashapon.dart';
import 'ichibankuji.dart';
import 'vtuber.dart';
// NOTE: kpop.dart is intentionally excluded — K-POP goods are hidden from
// the catalog/picker/search until further notice.

/// Aggregated read-only view over every per-store catalog. Screens and
/// autocomplete widgets should import from here so adding a new store is just
/// a matter of dropping a `<store>.dart` file and adding it to this list.
List<GoodsCatalogEntry> get kFullCatalog => [
      ...kChiikawaCatalog,
      ...kGashaponCatalog,
      ...kIchibanKujiCatalog,
      ...kAnimeCatalog,
      ...kVtuberCatalog,
      ...kGameCatalog,
    ];

/// Distinct catalog categories across all stores.
List<String> catalogCategories() {
  final set = <String>{};
  for (final e in kFullCatalog) {
    if (e.category.isNotEmpty) set.add(e.category);
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
    if (e.seriesName != null && e.seriesName!.isNotEmpty) {
      set.add(e.seriesName!);
    }
  }
  final out = set.toList()..sort();
  return out;
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
