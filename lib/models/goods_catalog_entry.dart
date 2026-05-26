/// Read-only editor-curated catalog entry. Mirrors the server `goods_catalog`
/// table fields but is also bundled statically in
/// `lib/data/chiikawa_seed_catalog.dart` so autocomplete works before the
/// app talks to the server.
class GoodsCatalogEntry {
  final int? id;
  final String nameKo;
  final String? nameJa;
  final String? nameEn;
  final String category;
  final String characterName;
  final String affiliation;
  final String? seriesName;
  final String? subSeries;
  final int? officialPriceJpy;
  final int? officialPriceKrw;
  final String? barcode;
  final String? imageUrl;
  final String? sourceUrl;
  final String sourceStore;
  final String? releaseDate;

  const GoodsCatalogEntry({
    this.id,
    required this.nameKo,
    this.nameJa,
    this.nameEn,
    required this.category,
    required this.characterName,
    this.affiliation = '',
    this.seriesName,
    this.subSeries,
    this.officialPriceJpy,
    this.officialPriceKrw,
    this.barcode,
    this.imageUrl,
    this.sourceUrl,
    this.sourceStore = '',
    this.releaseDate,
  });

  factory GoodsCatalogEntry.fromJson(Map<String, dynamic> json) {
    return GoodsCatalogEntry(
      id: json['id'] as int?,
      nameKo: json['name_ko'] as String? ?? '',
      nameJa: json['name_ja'] as String?,
      nameEn: json['name_en'] as String?,
      category: json['category'] as String? ?? '',
      characterName: json['character_name'] as String? ?? '',
      affiliation: json['affiliation'] as String? ?? '',
      seriesName: json['series_name'] as String?,
      subSeries: json['sub_series'] as String?,
      officialPriceJpy: json['official_price_jpy'] as int?,
      officialPriceKrw: json['official_price_krw'] as int?,
      barcode: json['barcode'] as String?,
      imageUrl: json['image_url'] as String?,
      sourceUrl: json['source_url'] as String?,
      sourceStore: json['source_store'] as String? ?? '',
      releaseDate: json['release_date'] as String?,
    );
  }

  /// Best display name, preferring Korean.
  String displayName({String locale = 'ko'}) {
    switch (locale) {
      case 'ja':
        return nameJa ?? nameKo;
      case 'en':
        return nameEn ?? nameKo;
      case 'ko':
      default:
        return nameKo;
    }
  }
}
