import 'dart:convert';
import 'dart:typed_data';

import 'package:share_plus/share_plus.dart';

import '../models/goods_item.dart';

class CsvExporter {
  const CsvExporter._();

  /// Build a UTF-8 BOM-prefixed CSV string (so Excel opens Korean cleanly).
  static String buildGoodsCsv(List<GoodsItem> items) {
    const headers = [
      'id',
      'folderId',
      'name',
      'category',
      'kind',
      'characterName',
      'affiliation',
      'seriesName',
      'quantity',
      'officialPrice',
      'paidPrice',
      'purchaseDate',
      'releaseDate',
      'isPreorder',
      'itemCondition',
      'purchaseState',
      'plannedShippingDate',
      'companyName',
      'purchasePlace',
      'storageLocation',
      'barcode',
      'memo',
      'isFavorite',
    ];

    final buffer = StringBuffer();
    buffer.writeln(headers.map(_escapeField).join(','));

    for (final item in items) {
      final row = [
        item.id,
        item.folderId,
        item.name,
        item.category,
        item.kind ?? '',
        item.characterName,
        item.affiliation ?? '',
        item.seriesName,
        item.quantity.toString(),
        item.officialPrice?.toString() ?? '',
        item.paidPrice?.toString() ?? '',
        item.purchaseDate?.toIso8601String() ?? '',
        item.releaseDate?.toIso8601String() ?? '',
        item.isPreorder ? 'true' : 'false',
        item.itemCondition.name,
        item.purchaseState.name,
        item.plannedShippingDate?.toIso8601String() ?? '',
        item.companyName ?? '',
        item.purchasePlace ?? '',
        item.storageLocation ?? '',
        item.barcode ?? '',
        item.memo ?? '',
        item.isFavorite ? 'true' : 'false',
      ];
      buffer.writeln(row.map(_escapeField).join(','));
    }

    return buffer.toString();
  }

  /// Share the CSV as an in-memory file so mobile, desktop, and web can all
  /// use the same export flow.
  static Future<String> exportGoodsToShare(
    List<GoodsItem> items, {
    String? fileNameHint,
  }) async {
    final csv = buildGoodsCsv(items);
    final stamp = DateTime.now().toIso8601String().replaceAll(':', '-');
    final fileName = '${fileNameHint ?? 'deokive_goods'}_$stamp.csv';
    final bytes = <int>[0xEF, 0xBB, 0xBF, ...utf8.encode(csv)];
    final xfile = XFile.fromData(
      Uint8List.fromList(bytes),
      mimeType: 'text/csv',
      name: fileName,
    );
    await Share.shareXFiles([xfile], subject: fileName);
    return fileName;
  }

  static String _escapeField(String value) {
    if (value.contains(',') || value.contains('"') || value.contains('\n')) {
      final escaped = value.replaceAll('"', '""');
      return '"$escaped"';
    }
    return value;
  }
}
