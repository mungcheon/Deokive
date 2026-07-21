class GoogleAuthConfig {
  const GoogleAuthConfig._();

  // Public builds do not carry project-specific OAuth client IDs.
  // Provide them at build time with --dart-define when Google login is needed.
  static const String _webClientId = String.fromEnvironment(
    'GOOGLE_WEB_CLIENT_ID',
    defaultValue: '',
  );
  static const String _webServerClientId = String.fromEnvironment(
    'GOOGLE_WEB_SERVER_CLIENT_ID',
    defaultValue: '',
  );

  static String? get webClientId =>
      _webClientId.trim().isEmpty ? null : _webClientId;

  static String? get webServerClientId =>
      _webServerClientId.trim().isEmpty ? null : _webServerClientId;
}
