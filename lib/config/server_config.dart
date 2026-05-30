import 'dart:async';
import 'dart:io';

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

  static String _runtimeBaseUrl = '';
  static Future<String?>? _discoveryFuture;

  static String get baseUrl {
    final configured = configuredBaseUrl.trim();
    if (configured.isNotEmpty) return configured;
    return _runtimeBaseUrl.trim();
  }

  /// True once a configured or discovered server URL is available.
  static bool get enabled => baseUrl.isNotEmpty;

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

    try {
      final interfaces = await NetworkInterface.list(
        includeLoopback: false,
        type: InternetAddressType.IPv4,
      );

      for (final interface in interfaces) {
        for (final addr in interface.addresses) {
          final ip = addr.address;
          final octets = ip.split('.');
          if (octets.length != 4 || !_isPrivateIpv4(octets)) continue;

          final prefix = '${octets[0]}.${octets[1]}.${octets[2]}';
          final selfHost = int.tryParse(octets[3]) ?? 0;

          for (final host in const [1, 2, 10, 20, 30, 50, 100, 101, 200, 254]) {
            if (host != selfHost) addHost('$prefix.$host');
          }

          for (var host = 1; host <= 254; host++) {
            if (host == selfHost) continue;
            addHost('$prefix.$host');
          }

          addHost(ip);
        }
      }
    } catch (_) {
      // Keep the static localhost/emulator candidates only.
    }

    return out.toList(growable: false);
  }

  static bool _isPrivateIpv4(List<String> octets) {
    final a = int.tryParse(octets[0]) ?? -1;
    final b = int.tryParse(octets[1]) ?? -1;
    return a == 10 ||
        (a == 172 && b >= 16 && b <= 31) ||
        (a == 192 && b == 168);
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
