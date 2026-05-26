/// Backend server connection config.
///
/// The board (게시판) is served from the FastAPI backend in `server/`. Until
/// that backend is deployed, [baseUrl] is empty and the app falls back to the
/// local Hive board — so the app keeps working offline / pre-deployment with
/// zero behavior change.
///
/// Point the app at a deployed server at build time:
///   flutter run --dart-define=DEOKIVE_SERVER_URL=https://your-host.example.com
class ServerConfig {
  ServerConfig._();

  static const String baseUrl =
      String.fromEnvironment('DEOKIVE_SERVER_URL', defaultValue: '');

  /// True once a server URL is configured. When false the app uses the local
  /// board only and never makes board network calls.
  static bool get enabled => baseUrl.trim().isNotEmpty;

  static Uri boardUri(String path, [Map<String, dynamic>? query]) {
    final base = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    return Uri.parse('$base$path').replace(
      queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
    );
  }
}
