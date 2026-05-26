import 'dart:async';
import 'dart:convert';

import 'package:hive_ce_flutter/hive_flutter.dart';
import 'package:http/http.dart' as http;

/// Daily-refreshed FX rates pulled from the free Frankfurter API
/// (https://api.frankfurter.app). Rates are stored relative to KRW: each
/// value is "1 KRW = rate * target". A negative or missing value falls back
/// to the static table in `Currency.rateFromKrw`.
///
/// Refresh policy: cache stamp is checked against "today 12:00 in the user's
/// timezone". If the last refresh was before today's noon and now is past
/// today's noon, a refresh is attempted. Failed fetches keep the previous
/// cached values (or fall back to static rates).
class ExchangeRateService {
  ExchangeRateService._();
  static final ExchangeRateService instance = ExchangeRateService._();

  static const _boxName = 'deokive_fx_rates';
  static const _ratesKey = 'rates_from_krw';
  static const _stampKey = 'last_refresh_iso';
  static const _supportedTargets = ['USD', 'JPY', 'EUR', 'CNY'];

  Box<dynamic>? _box;
  Map<String, double> _rates = {};
  Future<void>? _refreshFuture;

  Future<void> init() async {
    _box = await Hive.openBox(_boxName);
    final stored = _box?.get(_ratesKey) as Map?;
    if (stored != null) {
      _rates = {
        for (final entry in stored.entries)
          entry.key.toString(): (entry.value as num).toDouble(),
      };
    }
    // Trigger a non-blocking refresh; caller doesn't have to await.
    unawaited(refreshIfStale());
  }

  /// Rate to multiply a KRW amount by to get `targetCode`.
  /// Returns null if not loaded — caller falls back to static rate.
  double? rateFromKrw(String targetCode) {
    if (targetCode == 'KRW') return 1.0;
    return _rates[targetCode];
  }

  /// Convert amount from `fromCode` to `toCode` using KRW as the pivot.
  /// Falls back to the static rate map (passed in by the caller) when fresh
  /// rates aren't available yet.
  double convert({
    required num amount,
    required String fromCode,
    required String toCode,
    required double Function(String code) staticRateFromKrw,
  }) {
    if (fromCode == toCode) return amount.toDouble();
    final fromRate = rateFromKrw(fromCode) ?? staticRateFromKrw(fromCode);
    final toRate = rateFromKrw(toCode) ?? staticRateFromKrw(toCode);
    if (fromRate == 0) return 0;
    // amount in fromCode → KRW → toCode
    final krw = amount / fromRate;
    return krw * toRate;
  }

  /// Refreshes the cache if today's noon has passed since the last refresh.
  Future<void> refreshIfStale() {
    return _refreshFuture ??= _refreshIfStaleInternal()
      ..whenComplete(() => _refreshFuture = null);
  }

  Future<void> _refreshIfStaleInternal() async {
    final box = _box;
    if (box == null) return;
    final lastIso = box.get(_stampKey) as String?;
    final now = DateTime.now();
    final todayNoon = DateTime(now.year, now.month, now.day, 12);
    if (lastIso != null) {
      final last = DateTime.tryParse(lastIso);
      if (last != null) {
        // Refresh only if we are past today's noon AND last refresh was
        // strictly before today's noon.
        if (now.isBefore(todayNoon) || !last.isBefore(todayNoon)) return;
      }
    }
    await forceRefresh();
  }

  Future<void> forceRefresh() async {
    try {
      final uri = Uri.parse(
        'https://api.frankfurter.app/latest?from=KRW&to=${_supportedTargets.join(",")}',
      );
      final response = await http.get(uri).timeout(const Duration(seconds: 8));
      if (response.statusCode != 200) return;
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      final ratesJson = body['rates'] as Map<String, dynamic>?;
      if (ratesJson == null) return;
      _rates = {
        'KRW': 1.0,
        for (final entry in ratesJson.entries)
          entry.key: (entry.value as num).toDouble(),
      };
      await _box?.put(_ratesKey, Map<String, dynamic>.from(_rates));
      await _box?.put(_stampKey, DateTime.now().toIso8601String());
    } catch (_) {
      // Network/JSON failures keep the previous cache; static rates remain
      // as the ultimate fallback.
    }
  }

  DateTime? get lastRefreshedAt {
    final iso = _box?.get(_stampKey) as String?;
    return iso == null ? null : DateTime.tryParse(iso);
  }
}
