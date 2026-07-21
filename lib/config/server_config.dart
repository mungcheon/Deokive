import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Backend server connection config.
///
/// Preferred flow:
/// 1. If `DEOKIVE_SERVER_URL` is provided, always use that.
/// 2. Otherwise, on mobile/desktop, try to discover a local Deokive server on
///    the current LAN by probing `http://<candidate>:8000/health`.
class ServerConfig {
  ServerConfig._();

  static const String configuredBaseUrl =
      String.fromEnvironment('DEOKIVE_SERVER_URL', defaultValue: '');
  static const bool staticSite =
      bool.fromEnvironment('DEOKIVE_STATIC_SITE', defaultValue: false);
  static const bool personalDataLocalOnly = bool.fromEnvironment(
    'DEOKIVE_PERSONAL_DATA_LOCAL_ONLY',
    defaultValue: true,
  );

  static String _runtimeBaseUrl = '';
  static Future<String?>? _discoveryFuture;

  static String get baseUrl {
    if (staticSite) return '';
    final configured = configuredBaseUrl.trim();
    if (configured.isNotEmpty) return configured;
    if (kIsWeb && (Uri.base.scheme == 'http' || Uri.base.scheme == 'https')) {
      final host = Uri.base.host.toLowerCase();
      final isLocalHost = host == 'localhost' ||
          host == '127.0.0.1' ||
          host == '0.0.0.0' ||
          host == '[::1]';
      if (!isLocalHost) return '';
      return Uri.base.origin;
    }
    return _runtimeBaseUrl.trim();
  }

  /// True once a configured or discovered server URL is available.
  static bool get enabled => baseUrl.isNotEmpty;
  static bool get personalApiEnabled => enabled && !personalDataLocalOnly;

  static Uri boardUri(String path, [Map<String, dynamic>? query]) {
    final base = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    return Uri.parse('$base$path').replace(
      queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
    );
  }

  static Future<bool> ensureResolved() async {
    if (enabled) return true;
    _discoveryFuture ??= _discoverLocalServer();
    final found = await _discoveryFuture;
    return found != null && found.isNotEmpty;
  }

  static Future<String?> _discoverLocalServer() async {
    if (kIsWeb) return null;

    final candidates = await _candidateBaseUrls();
    const batchSize = 24;
    for (var i = 0; i < candidates.length; i += batchSize) {
      final batch = candidates.skip(i).take(batchSize);
      final results = await Future.wait(batch.map(_probeBaseUrl));
      for (final result in results) {
        if (result != null && result.isNotEmpty) {
          _runtimeBaseUrl = result;
          return result;
        }
      }
    }
    return null;
  }

  static Future<List<String>> _candidateBaseUrls() async {
    final out = <String>{};

    void addHost(String host) {
      out.add('http://$host:8000');
    }

    addHost('127.0.0.1');
    addHost('10.0.2.2');
    addHost('10.0.3.2');
    addHost('localhost');

    return out.toList(growable: false);
  }

  static Future<String?> _probeBaseUrl(String base) async {
    try {
      final resp = await http
          .get(Uri.parse('$base/health'))
          .timeout(const Duration(milliseconds: 350));
      if (resp.statusCode == 200 && resp.body.contains('ok')) {
        return base;
      }
    } catch (_) {
      // Ignore unreachable hosts during LAN scan.
    }
    return null;
  }
}
