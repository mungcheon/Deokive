import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// User-selectable text scale presets.
enum AppFontSize { small, medium, large }

extension AppFontSizeX on AppFontSize {
  String get label {
    switch (this) {
      case AppFontSize.small:
        return '작게';
      case AppFontSize.medium:
        return '중간';
      case AppFontSize.large:
        return '크게';
    }
  }

  double get scale {
    switch (this) {
      case AppFontSize.small:
        return 0.9;
      case AppFontSize.medium:
        return 1.0;
      case AppFontSize.large:
        return 1.15;
    }
  }

  static AppFontSize fromScale(double scale) {
    if (scale <= 0.95) return AppFontSize.small;
    if (scale >= 1.10) return AppFontSize.large;
    return AppFontSize.medium;
  }
}

/// Free / OFL-licensed font choices that are actually applied via
/// [google_fonts]. The `id` is what we persist in storage; `null`/empty
/// means the bundled Pretendard default.
class AppFont {
  final String id;
  final String label;

  const AppFont({required this.id, required this.label});
}

const List<AppFont> kAppFonts = [
  AppFont(id: 'pretendard', label: 'Pretendard (기본)'),
  AppFont(id: 'NotoSansKR', label: 'Noto Sans KR'),
  AppFont(id: 'NanumGothic', label: '나눔 고딕'),
  AppFont(id: 'GowunDodum', label: '고운 도담'),
  AppFont(id: 'NanumPenScript', label: '나눔 손글씨'),
  AppFont(id: 'JuaText', label: '주아체'),
];

/// Apply the chosen [fontId] to a base [TextTheme]. For 'pretendard' (default),
/// returns the textTheme unchanged (relies on `ThemeData.fontFamily`).
TextTheme applyAppFont(TextTheme base, String? fontId) {
  switch (fontId) {
    case null:
    case '':
    case 'pretendard':
      return base;
    case 'NotoSansKR':
      return GoogleFonts.notoSansKrTextTheme(base);
    case 'NanumGothic':
      return GoogleFonts.nanumGothicTextTheme(base);
    case 'GowunDodum':
      return GoogleFonts.gowunDodumTextTheme(base);
    case 'NanumPenScript':
      return GoogleFonts.nanumPenScriptTextTheme(base);
    case 'JuaText':
      return GoogleFonts.juaTextTheme(base);
    default:
      return base;
  }
}

/// Family string for `ThemeData.fontFamily` so non-text widgets that read
/// the family directly also pick up the choice. Returns null for Pretendard
/// (uses the bundled `fontFamily: 'Pretendard'` from main.dart).
String? fontFamilyFor(String? fontId) {
  switch (fontId) {
    case 'NotoSansKR':
      return GoogleFonts.notoSansKr().fontFamily;
    case 'NanumGothic':
      return GoogleFonts.nanumGothic().fontFamily;
    case 'GowunDodum':
      return GoogleFonts.gowunDodum().fontFamily;
    case 'NanumPenScript':
      return GoogleFonts.nanumPenScript().fontFamily;
    case 'JuaText':
      return GoogleFonts.jua().fontFamily;
    default:
      return null;
  }
}
