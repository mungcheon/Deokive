import 'package:flutter/material.dart';

/// Palette enum values are persisted (`_paletteKey` in Hive) — never rename
/// or remove existing values. New themes get appended; the catalog list is
/// re-ordered by hue for display.
enum AppPalette {
  // Existing — preserved for backward-compat with saved user choices.
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
  // New — anime character hair colors & IP-flavored themes.
  asukaRed,
  zeroPink,
  marioRed,
  sunsetOrange,
  pikachuYellow,
  midoriyaGreen,
  mikuTeal,
  oshinoPurple,
  chiikawaBeige,
  charcoalGray,
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
  // Ordered by hue, warm → cool → neutral. Labels lean into anime character
  // hair colors and well-known IP palettes so picking feels themed rather
  // than abstract.
  static const List<AppPaletteSpec> all = [
    // ── 핑크 계열 ─────────────────────────────────────────────────────
    AppPaletteSpec(
      palette: AppPalette.cherryBlossom,
      label: '사쿠라 핑크',
      primary: Color(0xFFFFC1CC),
      accent: Color(0xFFB2EBF2),
      background: Color(0xFFFFF9FB),
    ),
    AppPaletteSpec(
      palette: AppPalette.zeroPink,
      label: '제로투 핑크',
      primary: Color(0xFFFF6B9D),
      accent: Color(0xFFFFD7E2),
      background: Color(0xFFFFF1F5),
    ),
    AppPaletteSpec(
      palette: AppPalette.berry,
      label: '베리 핑크',
      primary: Color(0xFFF48FB1),
      accent: Color(0xFFCE93D8),
      background: Color(0xFFFCE4EC),
    ),
    // ── 레드 / 오렌지 계열 ─────────────────────────────────────────────
    AppPaletteSpec(
      palette: AppPalette.asukaRed,
      label: '아스카 레드',
      primary: Color(0xFFE45A5A),
      accent: Color(0xFFFFD1A4),
      background: Color(0xFFFFF3F2),
    ),
    AppPaletteSpec(
      palette: AppPalette.marioRed,
      label: '마리오 레드',
      primary: Color(0xFFE52521),
      accent: Color(0xFFFFD93D),
      background: Color(0xFFFFF4F2),
    ),
    AppPaletteSpec(
      palette: AppPalette.peachCoral,
      label: '피치 코랄',
      primary: Color(0xFFFFCCBC),
      accent: Color(0xFFCFD8DC),
      background: Color(0xFFFFF3E0),
    ),
    AppPaletteSpec(
      palette: AppPalette.sunsetOrange,
      label: '선셋 오렌지',
      primary: Color(0xFFFFAB91),
      accent: Color(0xFFFFD180),
      background: Color(0xFFFFF3E6),
    ),
    // ── 옐로 계열 ────────────────────────────────────────────────────
    AppPaletteSpec(
      palette: AppPalette.pikachuYellow,
      label: '피카츄 옐로',
      primary: Color(0xFFFFD93D),
      accent: Color(0xFFFFA000),
      background: Color(0xFFFFFDE7),
    ),
    AppPaletteSpec(
      palette: AppPalette.apricot,
      label: '선플라워 옐로',
      primary: Color(0xFFFFF59D),
      accent: Color(0xFFFFAB91),
      background: Color(0xFFFFFDE7),
    ),
    // ── 그린 계열 ────────────────────────────────────────────────────
    AppPaletteSpec(
      palette: AppPalette.midoriyaGreen,
      label: '미도리야 그린',
      primary: Color(0xFF4CAF50),
      accent: Color(0xFFC8E6C9),
      background: Color(0xFFF1F8E9),
    ),
    AppPaletteSpec(
      palette: AppPalette.melon,
      label: '멜론 그린',
      primary: Color(0xFFC8E6C9),
      accent: Color(0xFFFFF176),
      background: Color(0xFFF1F8E9),
    ),
    AppPaletteSpec(
      palette: AppPalette.mintChoco,
      label: '민트 초코',
      primary: Color(0xFFB2DFDB),
      accent: Color(0xFF8D6E63),
      background: Color(0xFFF1F8F7),
    ),
    // ── 시안 / 블루 계열 ──────────────────────────────────────────────
    AppPaletteSpec(
      palette: AppPalette.mikuTeal,
      label: '미쿠 시안',
      primary: Color(0xFF39C5BB),
      accent: Color(0xFFB2EBF2),
      background: Color(0xFFE0F7F5),
    ),
    AppPaletteSpec(
      palette: AppPalette.skyBlue,
      label: '스카이 블루',
      primary: Color(0xFF87CEEB),
      accent: Color(0xFFFFF491),
      background: Color(0xFFF8F9FA),
    ),
    // ── 퍼플 계열 ────────────────────────────────────────────────────
    AppPaletteSpec(
      palette: AppPalette.aquaPurple,
      label: '아쿠아 퍼플',
      primary: Color(0xFFB39DDB),
      accent: Color(0xFF80DEEA),
      background: Color(0xFFF3E5F5),
    ),
    AppPaletteSpec(
      palette: AppPalette.lavender,
      label: '라벤더 퍼플',
      primary: Color(0xFFDCD6F7),
      accent: Color(0xFFF4EEFF),
      background: Color(0xFFFAF9FF),
    ),
    AppPaletteSpec(
      palette: AppPalette.oshinoPurple,
      label: '호시노 퍼플',
      primary: Color(0xFF8E5BC7),
      accent: Color(0xFFFFD93D),
      background: Color(0xFFF5EFFA),
    ),
    // ── 베이지 / 중성 ────────────────────────────────────────────────
    AppPaletteSpec(
      palette: AppPalette.chiikawaBeige,
      label: '치이카와 베이지',
      primary: Color(0xFFF4E1C7),
      accent: Color(0xFFFFC1CC),
      background: Color(0xFFFFFAF2),
    ),
    AppPaletteSpec(
      palette: AppPalette.oatmeal,
      label: '오트밀 베이지',
      primary: Color(0xFFD7CCC8),
      accent: Color(0xFFA1887F),
      background: Color(0xFFEFEBE9),
    ),
    AppPaletteSpec(
      palette: AppPalette.charcoalGray,
      label: '차콜 그레이',
      primary: Color(0xFF757575),
      accent: Color(0xFFBDBDBD),
      background: Color(0xFFF5F5F5),
    ),
  ];

  static AppPaletteSpec byPalette(AppPalette palette) {
    return all.firstWhere(
      (item) => item.palette == palette,
      orElse: () => all.first,
    );
  }

  /// Color swatches shown when the user picks a folder color. Ordered by
  /// hue (pink → red → orange → yellow → green → cyan → blue → purple →
  /// neutral) so similar shades sit next to each other in the picker grid.
  static const List<Color> folderColors = [
    // 핑크 / 마젠타
    Color(0xFFFF6B9D), // 핫 핑크
    Color(0xFFFFC1CC), // 사쿠라 핑크
    Color(0xFFF48FB1), // 베리 핑크
    Color(0xFFFFA7C4), // 로즈 핑크
    Color(0xFFEF5DA8), // 라즈베리
    // 레드 / 코랄
    Color(0xFFF28482), // 코랄 레드
    Color(0xFFE52521), // 마리오 레드
    Color(0xFFFFCCBC), // 살구
    // 오렌지
    Color(0xFFFF8A5B), // 오렌지
    Color(0xFFFFAB91), // 선셋 오렌지
    Color(0xFFFFC857), // 머스타드
    // 옐로 / 크림
    Color(0xFFFFD93D), // 피카츄 옐로
    Color(0xFFFFF491), // 레몬
    Color(0xFFFFF59D), // 선플라워
    // 그린
    Color(0xFFAED581), // 라임 그린
    Color(0xFF4CAF50), // 미도리야 그린
    Color(0xFFC8E6C9), // 멜론 그린
    Color(0xFF6DD3A0), // 민트 그린
    Color(0xFF84A59D), // 세이지
    // 시안 / 청록
    Color(0xFF39C5BB), // 미쿠 시안
    Color(0xFFB2DFDB), // 민트 초코
    Color(0xFFAED9E0), // 아쿠아
    // 블루
    Color(0xFF87CEEB), // 스카이 블루
    Color(0xFF5CC8FF), // 비비드 블루
    Color(0xFF90CAF9), // 라이트 블루
    // 퍼플
    Color(0xFFDCD6F7), // 라벤더
    Color(0xFFB39DDB), // 아메지스트
    Color(0xFF8E5BC7), // 그레이프
    // 베이지 / 중성
    Color(0xFFF4E1C7), // 치이카와 베이지
    Color(0xFFD7CCC8), // 오트밀
    Color(0xFFBDBDBD), // 그레이
    Color(0xFF757575), // 차콜
  ];
}
