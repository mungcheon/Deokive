class GoogleAuthConfig {
  const GoogleAuthConfig._();

  // Hardcoded fallbacks from google-services.json (Firebase project: deokive-f8f27).
  // Override via --dart-define at build time if you rotate keys.
  static const String _defaultWebServerClientId =
      '863280180794-err62ag5qdt6p5m08n8a3j7ucfvra3n4.apps.googleusercontent.com';
  static const String _defaultIosClientId =
      '863280180794-5tavqegdji5hlhg265dfrhij0vr4aqeg.apps.googleusercontent.com';

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

  // Android uses the web/server client ID for serverClientId. The native
  // Android OAuth client is matched via google-services.json + SHA-1.
  static String? get androidServerClientId =>
      _androidServerClientId.trim().isNotEmpty
          ? _androidServerClientId
          : _defaultWebServerClientId;

  static String? get iosClientId =>
      _iosClientId.trim().isNotEmpty ? _iosClientId : _defaultIosClientId;

  static String? get webClientId =>
      _webClientId.trim().isEmpty ? null : _webClientId;

  static String? get webServerClientId =>
      _webServerClientId.trim().isNotEmpty
          ? _webServerClientId
          : _defaultWebServerClientId;
}
