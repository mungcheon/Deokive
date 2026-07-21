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

  String get normalizedCategory {
    final compact = category.replaceAll(RegExp(r'\s+'), '');
    return _categoryAliases[compact] ?? category;
  }
}

const Map<String, String> _categoryAliases = {
  '봉제인형': '인형',
  '러버마스코트': '마스코트',
  '미니피규어': '피규어',
  '넨도로이드': '피규어',
  '아크릴스탠드': '아크릴 스탠드',
  '러버스트랩': '키링',
  '일러스트카드': '카드',
  '토트백': '가방',
  '백팩': '가방',
  '숄더백': '가방',
  '머그': '머그컵',
  '필기구': '문구',
  '筆記具': '문구',
  '文具': '문구',
  '靴下': '의류',
  '帽子': '의류',
  '양말': '의류',
  '모자': '의류',
  '아파렐': '의류',
  'アパレル': '의류',
  '머리띠': '액세서리',
  '포셰트': '가방',
  '쿠션': '생활잡화',
  '生活雑貨': '생활잡화',
  '雑貨': '생활잡화',
  '食器': '식기',
  '펜라이트': '응원봉',
  '우치와': '응원용품',
};
