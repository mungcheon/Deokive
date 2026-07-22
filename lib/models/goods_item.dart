import 'dart:typed_data';
import 'dart:convert';

enum PurchaseState {
  wished,
  ordered,
  arrived,
  owned,
}

enum ItemCondition {
  unopened,
  opened,
  used,
  preorder,
  wish,
}

PurchaseState purchaseStateFromName(String? name) {
  return PurchaseState.values.firstWhere(
    (state) => state.name == name,
    orElse: () => PurchaseState.owned,
  );
}

ItemCondition itemConditionFromName(String? name) {
  return ItemCondition.values.firstWhere(
    (state) => state.name == name,
    orElse: () => ItemCondition.unopened,
  );
}

class GoodsItem {
  // Identity
  final String id;
  final String folderId;

  // Basic (required)
  final String name;
  final String category;
  final String? kind;
  final int quantity;
  final int? officialPrice;
  final int? paidPrice;

  /// ISO-ish 3-letter code of the currency for [paidPrice]
  /// (e.g. 'KRW', 'JPY'). Stored as a string so this model has no dependency
  /// on the `Currency` enum that lives next to AppState.
  final String priceCurrencyCode;

  /// Currency for [officialPrice]. May differ from [priceCurrencyCode] —
  /// e.g. official price in JPY but the user paid in KRW. Defaults to the
  /// paid currency when omitted (legacy data).
  final String? officialPriceCurrencyCode;
  final DateTime? purchaseDate;
  final bool isPreorder;
  final ItemCondition itemCondition;

  // Catalog metadata
  final String seriesName;
  final String characterName;
  final String? affiliation;

  // Detailed (optional)
  final String? companyName;
  final String? purchasePlace;
  final DateTime? releaseDate;
  final String? memo;

  // Shipping / status / wishlist
  final DateTime? plannedShippingDate;
  final String status;
  final PurchaseState purchaseState;
  final String? wishlistTargetFolderId;

  // Misc
  final String? barcode;
  final String? storageLocation;
  final List<Uint8List> imageBytesList;
  final String? imageUrl;
  final bool isFavorite;

  const GoodsItem({
    required this.id,
    required this.folderId,
    required this.name,
    required this.category,
    required this.kind,
    required this.quantity,
    required this.officialPrice,
    required this.paidPrice,
    this.priceCurrencyCode = 'KRW',
    this.officialPriceCurrencyCode,
    required this.purchaseDate,
    required this.isPreorder,
    required this.itemCondition,
    required this.seriesName,
    required this.characterName,
    required this.affiliation,
    required this.companyName,
    required this.purchasePlace,
    required this.releaseDate,
    required this.memo,
    required this.plannedShippingDate,
    required this.status,
    required this.purchaseState,
    required this.wishlistTargetFolderId,
    required this.barcode,
    required this.storageLocation,
    required this.imageBytesList,
    this.imageUrl,
    required this.isFavorite,
  });

  /// Backward-compat: first image as the primary thumbnail.
  Uint8List? get imageBytes =>
      imageBytesList.isEmpty ? null : imageBytesList.first;

  /// Effective official-price currency, falling back to the paid currency
  /// for legacy entries that didn't store one.
  String get effectiveOfficialPriceCurrencyCode =>
      officialPriceCurrencyCode ?? priceCurrencyCode;

  int? get priceDifference {
    if (officialPrice == null || paidPrice == null) return null;
    // Only meaningful when both prices are in the same currency.
    if (effectiveOfficialPriceCurrencyCode != priceCurrencyCode) return null;
    return officialPrice! - paidPrice!;
  }

  double? get priceRate {
    if (officialPrice == null || paidPrice == null || officialPrice == 0) {
      return null;
    }
    if (effectiveOfficialPriceCurrencyCode != priceCurrencyCode) return null;
    return ((officialPrice! - paidPrice!) / officialPrice!) * 100;
  }

  bool get isWishlistItem => purchaseState == PurchaseState.wished;

  GoodsItem copyWith({
    String? id,
    String? folderId,
    String? name,
    String? category,
    String? kind,
    int? quantity,
    int? officialPrice,
    int? paidPrice,
    String? priceCurrencyCode,
    String? officialPriceCurrencyCode,
    DateTime? purchaseDate,
    bool? isPreorder,
    ItemCondition? itemCondition,
    String? seriesName,
    String? characterName,
    String? affiliation,
    String? companyName,
    String? purchasePlace,
    DateTime? releaseDate,
    String? memo,
    DateTime? plannedShippingDate,
    String? status,
    PurchaseState? purchaseState,
    String? wishlistTargetFolderId,
    String? barcode,
    String? storageLocation,
    List<Uint8List>? imageBytesList,
    String? imageUrl,
    bool? isFavorite,
  }) {
    return GoodsItem(
      id: id ?? this.id,
      folderId: folderId ?? this.folderId,
      name: name ?? this.name,
      category: category ?? this.category,
      kind: kind ?? this.kind,
      quantity: quantity ?? this.quantity,
      officialPrice: officialPrice ?? this.officialPrice,
      paidPrice: paidPrice ?? this.paidPrice,
      priceCurrencyCode: priceCurrencyCode ?? this.priceCurrencyCode,
      officialPriceCurrencyCode:
          officialPriceCurrencyCode ?? this.officialPriceCurrencyCode,
      purchaseDate: purchaseDate ?? this.purchaseDate,
      isPreorder: isPreorder ?? this.isPreorder,
      itemCondition: itemCondition ?? this.itemCondition,
      seriesName: seriesName ?? this.seriesName,
      characterName: characterName ?? this.characterName,
      affiliation: affiliation ?? this.affiliation,
      companyName: companyName ?? this.companyName,
      purchasePlace: purchasePlace ?? this.purchasePlace,
      releaseDate: releaseDate ?? this.releaseDate,
      memo: memo ?? this.memo,
      plannedShippingDate: plannedShippingDate ?? this.plannedShippingDate,
      status: status ?? this.status,
      purchaseState: purchaseState ?? this.purchaseState,
      wishlistTargetFolderId:
          wishlistTargetFolderId ?? this.wishlistTargetFolderId,
      barcode: barcode ?? this.barcode,
      storageLocation: storageLocation ?? this.storageLocation,
      imageBytesList: imageBytesList ?? this.imageBytesList,
      imageUrl: imageUrl ?? this.imageUrl,
      isFavorite: isFavorite ?? this.isFavorite,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'folderId': folderId,
      'name': name,
      'category': category,
      'kind': kind,
      'quantity': quantity,
      'officialPrice': officialPrice,
      'paidPrice': paidPrice,
      'priceCurrencyCode': priceCurrencyCode,
      'officialPriceCurrencyCode': officialPriceCurrencyCode,
      'purchaseDate': purchaseDate?.toIso8601String(),
      'isPreorder': isPreorder,
      'itemCondition': itemCondition.name,
      'seriesName': seriesName,
      'characterName': characterName,
      'affiliation': affiliation,
      'companyName': companyName,
      'purchasePlace': purchasePlace,
      'releaseDate': releaseDate?.toIso8601String(),
      'memo': memo,
      'plannedShippingDate': plannedShippingDate?.toIso8601String(),
      'status': status,
      'purchaseState': purchaseState.name,
      'wishlistTargetFolderId': wishlistTargetFolderId,
      'barcode': barcode,
      'storageLocation': storageLocation,
      'imageBytesList':
          imageBytesList.map((b) => base64Encode(b)).toList(growable: false),
      'imageUrl': imageUrl,
      'isFavorite': isFavorite,
    };
  }

  factory GoodsItem.fromJson(Map<String, dynamic> json) {
    final imagesRaw = json['imageBytesList'] as List<dynamic>?;
    List<Uint8List> images;
    if (imagesRaw != null) {
      images = imagesRaw
          .map((e) => base64Decode(e as String))
          .toList(growable: false);
    } else {
      final legacyImage = json['imageBytes'] as String?;
      images = legacyImage == null ? const [] : [base64Decode(legacyImage)];
    }
    return GoodsItem(
      id: json['id'] as String? ?? '',
      folderId: json['folderId'] as String? ?? '',
      name: json['name'] as String? ?? '',
      category: json['category'] as String? ?? '',
      kind: json['kind'] as String?,
      quantity: json['quantity'] as int? ?? 1,
      officialPrice: json['officialPrice'] as int?,
      paidPrice: json['paidPrice'] as int?,
      priceCurrencyCode: json['priceCurrencyCode'] as String? ?? 'KRW',
      officialPriceCurrencyCode: json['officialPriceCurrencyCode'] as String?,
      purchaseDate: json['purchaseDate'] == null
          ? null
          : DateTime.tryParse(json['purchaseDate'] as String),
      isPreorder: json['isPreorder'] as bool? ?? false,
      itemCondition: itemConditionFromName(json['itemCondition'] as String?),
      seriesName: json['seriesName'] as String? ?? '',
      characterName: json['characterName'] as String? ?? '',
      affiliation: json['affiliation'] as String?,
      companyName: json['companyName'] as String?,
      purchasePlace: json['purchasePlace'] as String?,
      releaseDate: json['releaseDate'] == null
          ? null
          : DateTime.tryParse(json['releaseDate'] as String),
      memo: json['memo'] as String?,
      plannedShippingDate: json['plannedShippingDate'] == null
          ? null
          : DateTime.tryParse(json['plannedShippingDate'] as String),
      status: json['status'] as String? ?? '',
      purchaseState: purchaseStateFromName(json['purchaseState'] as String?),
      wishlistTargetFolderId: json['wishlistTargetFolderId'] as String?,
      barcode: json['barcode'] as String?,
      storageLocation: json['storageLocation'] as String?,
      imageBytesList: images,
      imageUrl: json['imageUrl'] as String?,
      isFavorite: json['isFavorite'] as bool? ?? false,
    );
  }
}
