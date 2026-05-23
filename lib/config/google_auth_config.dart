class GoogleAuthConfig {
  const GoogleAuthConfig._();

  static const String _androidServerClientId = String.fromEnvironment(
    'GOOGLE_ANDROID_SERVER_CLIENT_ID',
    defaultValue: '',
  );
  static const String _iosClientId = String.fromEnvironment(
    'GOOGLE_IOS_CLIENT_ID',
    defaultValue: '',
  );
  static const String _webClientId = String.fromEnvironment(
    'GOOGLE_WEB_CLIENT_ID',
    defaultValue: '',
  );
  static const String _webServerClientId = String.fromEnvironment(
    'GOOGLE_WEB_SERVER_CLIENT_ID',
    defaultValue: '',
  );

  static String? get androidServerClientId =>
      _androidServerClientId.trim().isEmpty ? null : _androidServerClientId;

  static String? get iosClientId =>
      _iosClientId.trim().isEmpty ? null : _iosClientId;

  static String? get webClientId =>
      _webClientId.trim().isEmpty ? null : _webClientId;

  static String? get webServerClientId =>
      _webServerClientId.trim().isEmpty ? null : _webServerClientId;
}
