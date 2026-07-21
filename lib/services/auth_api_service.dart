import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/server_config.dart';

class AuthApiUnavailable implements Exception {
  final String message;
  const AuthApiUnavailable([this.message = 'server not configured']);

  @override
  String toString() => 'AuthApiUnavailable: $message';
}

class ServerProfile {
  final int userId;
  final String loginId;
  final String nickname;
  final String tag;
  final String provider;
  final String? profileImageUrl;
  final bool isPremium;

  const ServerProfile({
    required this.userId,
    required this.loginId,
    required this.nickname,
    required this.tag,
    required this.provider,
    required this.profileImageUrl,
    required this.isPremium,
  });

  factory ServerProfile.fromJson(Map<String, dynamic> json) {
    return ServerProfile(
      userId: (json['user_id'] as num?)?.toInt() ?? 0,
      loginId: json['login_id'] as String? ?? '',
      nickname: json['nickname'] as String? ?? '',
      tag: json['tag'] as String? ?? '',
      provider: json['provider'] as String? ?? 'local',
      profileImageUrl: json['profile_image_url'] as String?,
      isPremium: json['is_premium'] == true,
    );
  }
}

class ServerAuthSession {
  final String accessToken;
  final String tokenType;

  const ServerAuthSession({
    required this.accessToken,
    required this.tokenType,
  });

  factory ServerAuthSession.fromJson(Map<String, dynamic> json) {
    return ServerAuthSession(
      accessToken: json['access_token'] as String? ?? '',
      tokenType: json['token_type'] as String? ?? 'bearer',
    );
  }
}

class AuthApiService {
  final http.Client _http;

  AuthApiService({http.Client? client}) : _http = client ?? http.Client();

  void dispose() => _http.close();

  bool get enabled => ServerConfig.personalApiEnabled;

  Map<String, String> _headers([String? token]) => {
        'Content-Type': 'application/json',
        if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      };

  Future<ServerAuthSession> signUp({
    required String loginId,
    required String password,
    required String nickname,
  }) async {
    if (!enabled) throw const AuthApiUnavailable();
    final uri = ServerConfig.boardUri('/auth/signup');
    final resp = await _http
        .post(
          uri,
          headers: _headers(),
          body: jsonEncode({
            'login_id': loginId,
            'password': password,
            'nickname': nickname,
          }),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 201) {
      throw AuthApiUnavailable('signup failed ${resp.statusCode}');
    }
    return ServerAuthSession.fromJson(
      jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>,
    );
  }

  Future<ServerAuthSession> login({
    required String loginId,
    required String password,
  }) async {
    if (!enabled) throw const AuthApiUnavailable();
    final uri = ServerConfig.boardUri('/auth/login');
    final resp = await _http
        .post(
          uri,
          headers: _headers(),
          body: jsonEncode({
            'login_id': loginId,
            'password': password,
          }),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw AuthApiUnavailable('login failed ${resp.statusCode}');
    }
    return ServerAuthSession.fromJson(
      jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>,
    );
  }

  Future<ServerProfile> getMe(String token) async {
    if (!enabled) throw const AuthApiUnavailable();
    final uri = ServerConfig.boardUri('/profile/me');
    final resp = await _http
        .get(uri, headers: _headers(token))
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw AuthApiUnavailable('profile failed ${resp.statusCode}');
    }
    return ServerProfile.fromJson(
      jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>,
    );
  }

  Future<ServerProfile> updateMe(
    String token, {
    String? nickname,
    String? tag,
    String? profileImageUrl,
  }) async {
    if (!enabled) throw const AuthApiUnavailable();
    final uri = ServerConfig.boardUri('/profile/me');
    final payload = <String, dynamic>{};
    if (nickname != null) payload['nickname'] = nickname;
    if (tag != null) payload['tag'] = tag;
    if (profileImageUrl != null) payload['profile_image_url'] = profileImageUrl;
    final resp = await _http
        .patch(
          uri,
          headers: _headers(token),
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 12));
    if (resp.statusCode != 200) {
      throw AuthApiUnavailable('profile update failed ${resp.statusCode}');
    }
    return ServerProfile.fromJson(
      jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>,
    );
  }
}
