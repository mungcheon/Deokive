import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/server_config.dart';
import 'local_admin_override.dart';

class DeviceProfileApiUnavailable implements Exception {
  final String message;
  const DeviceProfileApiUnavailable([this.message = 'server not configured']);

  @override
  String toString() => 'DeviceProfileApiUnavailable: $message';
}

class DeviceProfileApiService {
  final http.Client _http;

  DeviceProfileApiService({http.Client? client})
      : _http = client ?? http.Client();

  void dispose() => _http.close();

  bool get enabled => ServerConfig.personalApiEnabled;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (localAdminOverrideEnabled) 'X-Deokive-App-Admin': '1',
      };

  Future<bool> isNicknameAvailable(
    String nickname, {
    required String deviceId,
  }) async {
    if (!enabled) throw const DeviceProfileApiUnavailable();
    final uri = ServerConfig.boardUri(
      '/device-profile/availability/$nickname',
      {'device_id': deviceId},
    );
    final resp = await _http
        .get(uri, headers: _headers)
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw DeviceProfileApiUnavailable(
        'availability failed ${resp.statusCode}',
      );
    }
    final data =
        jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return data['available'] == true;
  }

  Future<String> claimNickname({
    required String deviceId,
    required String nickname,
  }) async {
    if (!enabled) throw const DeviceProfileApiUnavailable();
    final uri = ServerConfig.boardUri('/device-profile/claim');
    final resp = await _http
        .post(
          uri,
          headers: _headers,
          body: jsonEncode({
            'device_id': deviceId,
            'nickname': nickname,
          }),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw DeviceProfileApiUnavailable('claim failed ${resp.statusCode}');
    }
    final data =
        jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return data['nickname'] as String? ?? nickname;
  }

  Future<String> claimAutoNickname({
    required String deviceId,
  }) async {
    if (!enabled) throw const DeviceProfileApiUnavailable();
    final uri = ServerConfig.boardUri('/device-profile/claim-auto');
    final resp = await _http
        .post(
          uri,
          headers: _headers,
          body: jsonEncode({
            'device_id': deviceId,
          }),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw DeviceProfileApiUnavailable('auto claim failed ${resp.statusCode}');
    }
    final data =
        jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
    return data['nickname'] as String? ?? 'deokive';
  }
}
