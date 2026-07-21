import 'package:flutter/material.dart';

import '../config/app_palette_catalog.dart';

export '../config/app_palette_catalog.dart';

class DeokivePaletteSpec {
  final AppPalette palette;
  final String label;
  final Color primary;
  final Color accent;
  final Color background;
  final Color text;

  const DeokivePaletteSpec({
    required this.palette,
    required this.label,
    required this.primary,
    required this.accent,
    required this.background,
    this.text = const Color(0xFF4A4A4A),
  });

  factory DeokivePaletteSpec.fromCatalog(AppPaletteSpec spec) {
    return DeokivePaletteSpec(
      palette: spec.palette,
      label: spec.label,
      primary: spec.primary,
      accent: spec.accent,
      background: spec.background,
      text: spec.text,
    );
  }
}

class DeokivePalette extends ThemeExtension<DeokivePalette> {
  final Color primary;
  final Color accent;
  final Color background;
  final Color text;
  final Color softSurface;

  const DeokivePalette({
    required this.primary,
    required this.accent,
    required this.background,
    required this.text,
    required this.softSurface,
  });

  @override
  DeokivePalette copyWith({
    Color? primary,
    Color? accent,
    Color? background,
    Color? text,
    Color? softSurface,
  }) {
    return DeokivePalette(
      primary: primary ?? this.primary,
      accent: accent ?? this.accent,
      background: background ?? this.background,
      text: text ?? this.text,
      softSurface: softSurface ?? this.softSurface,
    );
  }

  @override
  ThemeExtension<DeokivePalette> lerp(
    covariant ThemeExtension<DeokivePalette>? other,
    double t,
  ) {
    if (other is! DeokivePalette) {
      return this;
    }

    return DeokivePalette(
      primary: Color.lerp(primary, other.primary, t) ?? primary,
      accent: Color.lerp(accent, other.accent, t) ?? accent,
      background: Color.lerp(background, other.background, t) ?? background,
      text: Color.lerp(text, other.text, t) ?? text,
      softSurface: Color.lerp(softSurface, other.softSurface, t) ?? softSurface,
    );
  }
}

final List<DeokivePaletteSpec> deokivePalettes = AppPaletteCatalog.all
    .map(DeokivePaletteSpec.fromCatalog)
    .toList(growable: false);

DeokivePaletteSpec paletteSpecFor(AppPalette palette) {
  return deokivePalettes.firstWhere((spec) => spec.palette == palette);
}

Color mixColors(Color a, Color b, double t) {
  return Color.lerp(a, b, t) ?? a;
}
