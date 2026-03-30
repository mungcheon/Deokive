import 'package:flutter/material.dart';

enum AppPalette {
  skyBlue,
  cherryBlossom,
  lavender,
  apricot,
  mintChoco,
  oatmeal,
  peachCoral,
  aquaPurple,
  melon,
  berry,
}

class AppPaletteSpec {
  final AppPalette palette;
  final String label;
  final Color primary;
  final Color accent;
  final Color background;
  final Color text;

  const AppPaletteSpec({
    required this.palette,
    required this.label,
    required this.primary,
    required this.accent,
    required this.background,
    this.text = const Color(0xFF4A4A4A),
  });
}

class AppPaletteCatalog {
  static const List<AppPaletteSpec> all = [
    AppPaletteSpec(
      palette: AppPalette.skyBlue,
      label: '스카이 블루',
      primary: Color(0xFF87CEEB),
      accent: Color(0xFFFFF491),
      background: Color(0xFFF8F9FA),
    ),
    AppPaletteSpec(
      palette: AppPalette.cherryBlossom,
      label: '벚꽃 핑크',
      primary: Color(0xFFFFC1CC),
      accent: Color(0xFFB2EBF2),
      background: Color(0xFFFFF9FB),
    ),
    AppPaletteSpec(
      palette: AppPalette.lavender,
      label: '라벤더 퍼플',
      primary: Color(0xFFDCD6F7),
      accent: Color(0xFFF4EEFF),
      background: Color(0xFFFAF9FF),
    ),
    AppPaletteSpec(
      palette: AppPalette.apricot,
      label: '살구 오렌지',
      primary: Color(0xFFFFF59D),
      accent: Color(0xFFFFAB91),
      background: Color(0xFFFFFDE7),
    ),
    AppPaletteSpec(
      palette: AppPalette.mintChoco,
      label: '민트 초코',
      primary: Color(0xFFB2DFDB),
      accent: Color(0xFF8D6E63),
      background: Color(0xFFF1F8F7),
    ),
    AppPaletteSpec(
      palette: AppPalette.oatmeal,
      label: '오트밀 베이지',
      primary: Color(0xFFD7CCC8),
      accent: Color(0xFFA1887F),
      background: Color(0xFFEFEBE9),
    ),
    AppPaletteSpec(
      palette: AppPalette.peachCoral,
      label: '피치 코랄',
      primary: Color(0xFFFFCCBC),
      accent: Color(0xFFCFD8DC),
      background: Color(0xFFFFF3E0),
    ),
    AppPaletteSpec(
      palette: AppPalette.aquaPurple,
      label: '아쿠아 퍼플',
      primary: Color(0xFFB39DDB),
      accent: Color(0xFF80DEEA),
      background: Color(0xFFF3E5F5),
    ),
    AppPaletteSpec(
      palette: AppPalette.melon,
      label: '멜론 그린',
      primary: Color(0xFFC8E6C9),
      accent: Color(0xFFFFF176),
      background: Color(0xFFF1F8E9),
    ),
    AppPaletteSpec(
      palette: AppPalette.berry,
      label: '베리 핑크',
      primary: Color(0xFFF48FB1),
      accent: Color(0xFFCE93D8),
      background: Color(0xFFFCE4EC),
    ),
  ];

  static AppPaletteSpec byPalette(AppPalette palette) {
    return all.firstWhere((item) => item.palette == palette);
  }
}
