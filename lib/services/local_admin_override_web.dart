import 'dart:html' as html;

bool get localAdminOverrideEnabled {
  final ua = html.window.navigator.userAgent.toLowerCase();
  final isMobile = ua.contains('android') ||
      ua.contains('iphone') ||
      ua.contains('ipad') ||
      ua.contains('mobile');
  if (isMobile) return false;
  return ua.contains('windows') || ua.contains('macintosh') || ua.contains('x11');
}

bool get localAdminForceSessionEnabled {
  return false;
}
