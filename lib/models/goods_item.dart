import 'dart:typed_data';
import 'dart:convert';

class GoodsItem {
  final String id;
  final String folderId;
  final String name;
  final String category;
  final int quantity;
  final int? officialPrice;
  final int? paidPrice;
  final String seriesName;
  final String? companyName;
  final String? purchasePlace;
  final DateTime? purchaseDate;
  final DateTime? plannedShippingDate;
  final String status;
  final String? barcode;
  final String? storageLocation;
  final String? memo;
  final Uint8List? imageBytes;
  final bool isFavorite;

  const GoodsItem({
    required this.id,
    required this.folderId,
    required this.name,
    required this.category,
    required this.quantity,
    required this.officialPrice,
    required this.paidPrice,
    required this.seriesName,
    required this.companyName,
    required this.purchasePlace,
    required this.purchaseDate,
    required this.plannedShippingDate,
    required this.status,
    required this.barcode,
    required this.storageLocation,
    required this.memo,
    required this.imageBytes,
    required this.isFavorite,
  });

  int? get priceDifference {
    if (officialPrice == null || paidPrice == null) return null;
    return officialPrice! - paidPrice!;
  }

  double? get priceRate {
    if (officialPrice == null || paidPrice == null || officialPrice == 0) {
      return null;
    }
    return ((officialPrice! - paidPrice!) / officialPrice!) * 100;
  }

  GoodsItem copyWith({
    String? id,
    String? folderId,
    String? name,
    String? category,
    int? quantity,
    int? officialPrice,
    int? paidPrice,
    String? seriesName,
    String? companyName,
    String? purchasePlace,
    DateTime? purchaseDate,
    DateTime? plannedShippingDate,
    String? status,
    String? barcode,
    String? storageLocation,
    String? memo,
    Uint8List? imageBytes,
    bool? isFavorite,
  }) {
    return GoodsItem(
      id: id ?? this.id,
      folderId: folderId ?? this.folderId,
      name: name ?? this.name,
      category: category ?? this.category,
      quantity: quantity ?? this.quantity,
      officialPrice: officialPrice ?? this.officialPrice,
      paidPrice: paidPrice ?? this.paidPrice,
      seriesName: seriesName ?? this.seriesName,
      companyName: companyName ?? this.companyName,
      purchasePlace: purchasePlace ?? this.purchasePlace,
      purchaseDate: purchaseDate ?? this.purchaseDate,
      plannedShippingDate: plannedShippingDate ?? this.plannedShippingDate,
      status: status ?? this.status,
      barcode: barcode ?? this.barcode,
      storageLocation: storageLocation ?? this.storageLocation,
      memo: memo ?? this.memo,
      imageBytes: imageBytes ?? this.imageBytes,
      isFavorite: isFavorite ?? this.isFavorite,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'folderId': folderId,
      'name': name,
      'category': category,
      'quantity': quantity,
      'officialPrice': officialPrice,
      'paidPrice': paidPrice,
      'seriesName': seriesName,
      'companyName': companyName,
      'purchasePlace': purchasePlace,
      'purchaseDate': purchaseDate?.toIso8601String(),
      'plannedShippingDate': plannedShippingDate?.toIso8601String(),
      'status': status,
      'barcode': barcode,
      'storageLocation': storageLocation,
      'memo': memo,
      'imageBytes': imageBytes == null ? null : base64Encode(imageBytes!),
      'isFavorite': isFavorite,
    };
  }

  factory GoodsItem.fromJson(Map<String, dynamic> json) {
    final imageText = json['imageBytes'] as String?;
    return GoodsItem(
      id: json['id'] as String? ?? '',
      folderId: json['folderId'] as String? ?? '',
      name: json['name'] as String? ?? '',
      category: json['category'] as String? ?? '',
      quantity: json['quantity'] as int? ?? 1,
      officialPrice: json['officialPrice'] as int?,
      paidPrice: json['paidPrice'] as int?,
      seriesName: json['seriesName'] as String? ?? '',
      companyName: json['companyName'] as String?,
      purchasePlace: json['purchasePlace'] as String?,
      purchaseDate: json['purchaseDate'] == null
          ? null
          : DateTime.tryParse(json['purchaseDate'] as String),
      plannedShippingDate: json['plannedShippingDate'] == null
          ? null
          : DateTime.tryParse(json['plannedShippingDate'] as String),
      status: json['status'] as String? ?? '',
      barcode: json['barcode'] as String?,
      storageLocation: json['storageLocation'] as String?,
      memo: json['memo'] as String?,
      imageBytes: imageText == null ? null : base64Decode(imageText),
      isFavorite: json['isFavorite'] as bool? ?? false,
    );
  }
}
