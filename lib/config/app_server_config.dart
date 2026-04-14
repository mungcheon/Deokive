class AppServerConfig {
  const AppServerConfig._();

  static const String _serverBaseUrl = String.fromEnvironment(
    'DEOKIVE_SERVER_BASE_URL',
    defaultValue: '',
  );

  static String? get serverBaseUrl {
    final normalized = _serverBaseUrl.trim();
    if (normalized.isEmpty) return null;
    return normalized.endsWith('/')
        ? normalized.substring(0, normalized.length - 1)
        : normalized;
  }

  static bool get isConfigured => serverBaseUrl != null;
}
