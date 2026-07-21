import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/server_config.dart';
import '../models/goods_catalog_entry.dart';

class CatalogApiUnavailable implements Exception {
  final String message;
  const CatalogApiUnavailable([this.message = 'server not configured']);

  @override
  String toString() => 'CatalogApiUnavailable: $message';
}

class CatalogApiService {
  final http.Client _http;
  ({int totalCount, String? latestUpdatedAt})? _lastMeta;

  CatalogApiService({http.Client? client}) : _http = client ?? http.Client();

  void dispose() => _http.close();

  bool get enabled => ServerConfig.enabled;

  Future<({int totalCount, String? latestUpdatedAt})> fetchMeta() async {
    if (!enabled) throw const CatalogApiUnavailable();
    final uri = ServerConfig.boardUri('/catalog/meta');
    final resp = await _http.get(uri).timeout(const Duration(seconds: 15));
    if (resp.statusCode != 200) {
      throw CatalogApiUnavailable('catalog meta failed ${resp.statusCode}');
    }
    final data = jsonDecode(utf8.decode(resp.bodyBytes));
    if (data is! Map<String, dynamic>) {
      return (totalCount: 0, latestUpdatedAt: null);
    }
    final meta = (
      totalCount: (data['total_count'] as num?)?.toInt() ?? 0,
      latestUpdatedAt: data['latest_updated_at'] as String?,
    );
    _lastMeta = meta;
    return meta;
  }

  Future<int> fetchTotalCount() async {
    final meta = _lastMeta ?? await fetchMeta();
    return meta.totalCount;
  }

  Future<List<GoodsCatalogEntry>> fetchPage({
    int limit = 1000,
    int offset = 0,
  }) async {
    if (!enabled) throw const CatalogApiUnavailable();
    final uri = ServerConfig.boardUri('/catalog/items', {
      'limit': limit,
      'offset': offset,
    });
    final resp = await _http.get(uri).timeout(const Duration(seconds: 15));
    if (resp.statusCode != 200) {
      throw CatalogApiUnavailable('catalog list failed ${resp.statusCode}');
    }
    final data = jsonDecode(utf8.decode(resp.bodyBytes));
    if (data is! List) return const [];
    return data
        .whereType<Map<String, dynamic>>()
        .map(GoodsCatalogEntry.fromJson)
        .toList();
  }

  Future<List<GoodsCatalogEntry>> fetchAll({
    int pageSize = 1000,
    int? knownTotalCount,
  }) async {
    if (!enabled) throw const CatalogApiUnavailable();
    final totalCount =
        knownTotalCount ?? _lastMeta?.totalCount ?? await fetchTotalCount();
    if (totalCount <= 0) return const [];
    final offsets = <int>[];
    for (var offset = 0; offset < totalCount; offset += pageSize) {
      offsets.add(offset);
    }
    final pages = await Future.wait(
      offsets.map((offset) => fetchPage(limit: pageSize, offset: offset)),
    );
    final merged = <GoodsCatalogEntry>[];
    for (final page in pages) {
      merged.addAll(page);
    }
    if (merged.length <= 1) return merged;
    merged.sort((a, b) => (a.id ?? 0).compareTo(b.id ?? 0));
    return merged;
  }
}
