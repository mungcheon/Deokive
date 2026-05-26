import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';
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

  /// Write the CSV to a temp file and trigger a system share sheet.
  /// Returns the resulting file path on success.
  static Future<String> exportGoodsToShare(List<GoodsItem> items,
      {String? fileNameHint}) async {
    final csv = buildGoodsCsv(items);
    final dir = await getTemporaryDirectory();
    final stamp = DateTime.now().toIso8601String().replaceAll(':', '-');
    final fileName = '${fileNameHint ?? 'deokive_goods'}_$stamp.csv';
    final file = File('${dir.path}${Platform.pathSeparator}$fileName');
    // Prepend UTF-8 BOM so Excel detects the encoding correctly.
    final bytes = <int>[0xEF, 0xBB, 0xBF, ...utf8.encode(csv)];
    await file.writeAsBytes(bytes);
    await Share.shareXFiles(
      [XFile(file.path, mimeType: 'text/csv', name: fileName)],
      subject: fileName,
    );
    return file.path;
  }

  static String _escapeField(String value) {
    if (value.contains(',') || value.contains('"') || value.contains('\n')) {
      final escaped = value.replaceAll('"', '""');
      return '"$escaped"';
    }
    return value;
  }
}
