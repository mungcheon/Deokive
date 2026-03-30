import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';
import 'package:provider/provider.dart';
import 'dart:async';

import 'l10n/app_language.dart';
import 'services/ad_service.dart';
import 'screens/root_screen.dart';
import 'state/app_state.dart';
import 'theme/deokive_palette.dart';
import 'widgets/mobile_ratio_frame.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter();
  unawaited(AdService.instance.initialize());
  runApp(const DeokiveApp());
}

class DeokiveApp extends StatelessWidget {
  const DeokiveApp({super.key});

  double _clamp(double value, double min, double max) {
    if (value < min) return min;
    if (value > max) return max;
    return value;
  }

  double _textScaleForWidth(double width) {
    if (width <= 320) return 0.84;
    if (width <= 360) return 0.9;
    if (width <= 392) return 0.95;
    if (width <= 430) return 0.98;
    return 1;
  }

  Color _contrastText(Color background, {Color? light, Color? dark}) {
    final lightColor = light ?? const Color(0xFFF8F9FA);
    final darkColor = dark ?? const Color(0xFF2F343A);
    return background.computeLuminance() > 0.62 ? darkColor : lightColor;
  }

  ThemeData _buildTheme({
    required Brightness brightness,
    required DeokivePaletteSpec spec,
    required double appBarHeight,
    required double appBarTitleSize,
    required double navBarHeight,
    required double navIconSize,
    required double navLabelSize,
  }) {
    final isDark = brightness == Brightness.dark;
    final background = isDark
        ? mixColors(spec.background, const Color(0xFF0F1115), 0.88)
        : spec.background;
    final surface = isDark
        ? mixColors(spec.primary, const Color(0xFF1A1F27), 0.82)
        : Colors.white;
    final softSurface = isDark
        ? mixColors(spec.primary, const Color(0xFF262C37), 0.74)
        : mixColors(spec.primary, Colors.white, 0.72);
    final text = _contrastText(
      background,
      dark: spec.text,
    );
    final surfaceText = _contrastText(
      surface,
      dark: spec.text,
    );
    final outline = isDark
        ? mixColors(spec.primary, Colors.white, 0.28)
        : mixColors(spec.primary, spec.accent, 0.45);
    final cardTint = isDark
        ? mixColors(spec.accent, const Color(0xFF1D212A), 0.72)
        : mixColors(spec.accent, Colors.white, 0.55);

    final colorScheme = ColorScheme.fromSeed(
      seedColor: spec.primary,
      brightness: brightness,
    ).copyWith(
      primary: spec.primary,
      secondary: spec.accent,
      surface: surface,
      outline: outline,
      onPrimary: _contrastText(spec.primary, dark: spec.text),
      onSecondary: _contrastText(spec.accent, dark: spec.text),
      onSurface: surfaceText,
    );

    return ThemeData(
      useMaterial3: true,
      fontFamily: 'Pretendard',
      colorScheme: colorScheme,
      scaffoldBackgroundColor: background,
      dividerColor: outline,
      extensions: [
        DeokivePalette(
          primary: spec.primary,
          accent: spec.accent,
          background: background,
          text: text,
          softSurface: softSurface,
        ),
      ],
      textTheme:
          (isDark ? ThemeData.dark() : ThemeData.light()).textTheme.apply(
                bodyColor: surfaceText,
                displayColor: text,
              ),
      appBarTheme: AppBarTheme(
        centerTitle: false,
        toolbarHeight: appBarHeight,
        backgroundColor: background,
        foregroundColor: text,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        titleTextStyle: TextStyle(
          color: text,
          fontSize: appBarTitleSize,
          fontWeight: FontWeight.w800,
        ),
        iconTheme: IconThemeData(color: text),
        shape: Border(
          bottom: BorderSide(
            color: outline.withValues(alpha: 0.85),
            width: 1,
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: navBarHeight,
        backgroundColor: surface,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        indicatorColor:
            mixColors(spec.primary, Colors.white, isDark ? 0.18 : 0.55),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final isSelected = states.contains(WidgetState.selected);
          return TextStyle(
            color:
                isSelected ? spec.primary : surfaceText.withValues(alpha: 0.78),
            fontSize: navLabelSize,
            fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final isSelected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: isSelected ? spec.primary : surfaceText,
            size: navIconSize,
          );
        }),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: outline),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: spec.primary,
          foregroundColor: spec.text,
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: text,
          side: BorderSide(color: outline),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: softSurface,
        selectedColor:
            mixColors(spec.primary, Colors.white, isDark ? 0.22 : 0.45),
        secondarySelectedColor:
            mixColors(spec.accent, Colors.white, isDark ? 0.2 : 0.35),
        side: BorderSide(color: outline),
        labelStyle: TextStyle(color: text, fontWeight: FontWeight.w600),
        secondaryLabelStyle:
            TextStyle(color: text, fontWeight: FontWeight.w700),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: spec.primary,
        foregroundColor: spec.text,
        shape: const CircleBorder(),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        labelStyle: TextStyle(color: surfaceText),
        helperStyle: TextStyle(color: surfaceText.withValues(alpha: 0.75)),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: outline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: spec.primary, width: 1.6),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: cardTint,
        contentTextStyle:
            TextStyle(color: _contrastText(cardTint, dark: spec.text)),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
      ),
      listTileTheme: ListTileThemeData(
        iconColor: surfaceText,
        textColor: surfaceText,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider<AppState>(
      create: (_) => AppState()..init(),
      child: Consumer<AppState>(
        builder: (context, appState, _) {
          return LayoutBuilder(
            builder: (context, constraints) {
              final screenWidth = constraints.maxWidth;
              final screenHeight = constraints.maxHeight;
              final shortestSide =
                  screenWidth < screenHeight ? screenWidth : screenHeight;

              final appBarHeight = _clamp(screenHeight * 0.075, 56, 76);
              final appBarTitleSize = _clamp(shortestSide * 0.032, 18, 24);
              final navBarHeight = _clamp(screenHeight * 0.09, 64, 84);
              final navIconSize = _clamp(shortestSide * 0.034, 22, 30);
              final navLabelSize = _clamp(shortestSide * 0.018, 11.5, 14);
              final spec = paletteSpecFor(appState.appPalette);

              return MaterialApp(
                debugShowCheckedModeBanner: false,
                title: 'Deokive',
                locale: appState.appLanguage.locale,
                supportedLocales: const [
                  Locale('ko'),
                  Locale('en'),
                ],
                localizationsDelegates: const [
                  GlobalMaterialLocalizations.delegate,
                  GlobalWidgetsLocalizations.delegate,
                  GlobalCupertinoLocalizations.delegate,
                ],
                themeMode:
                    appState.darkModeEnabled ? ThemeMode.dark : ThemeMode.light,
                theme: _buildTheme(
                  brightness: Brightness.light,
                  spec: spec,
                  appBarHeight: appBarHeight,
                  appBarTitleSize: appBarTitleSize,
                  navBarHeight: navBarHeight,
                  navIconSize: navIconSize,
                  navLabelSize: navLabelSize,
                ),
                darkTheme: _buildTheme(
                  brightness: Brightness.dark,
                  spec: spec,
                  appBarHeight: appBarHeight,
                  appBarTitleSize: appBarTitleSize,
                  navBarHeight: navBarHeight,
                  navIconSize: navIconSize,
                  navLabelSize: navLabelSize,
                ),
                builder: (context, child) {
                  final mediaQuery = MediaQuery.of(context);
                  final width = mediaQuery.size.width;
                  final textScale = _textScaleForWidth(width);

                  return MediaQuery(
                    data: mediaQuery.copyWith(
                      textScaler: TextScaler.linear(textScale),
                    ),
                    child: child ?? const SizedBox.shrink(),
                  );
                },
                home: const MobileRatioFrame(
                  child: RootScreen(),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
