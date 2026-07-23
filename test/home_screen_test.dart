import 'package:deokive/screens/home_screen.dart';
import 'package:deokive/state/app_state.dart';
import 'package:deokive/theme/deokive_palette.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

void main() {
  testWidgets('home DB panel fits on a narrow phone screen', (tester) async {
    final appState = AppState();
    final palette = paletteSpecFor(AppPalette.zeroTwoPink);

    await tester.binding.setSurfaceSize(const Size(320, 720));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      ChangeNotifierProvider.value(
        value: appState,
        child: MaterialApp(
          theme: ThemeData(
            useMaterial3: true,
            colorScheme: ColorScheme.fromSeed(seedColor: palette.primary),
            extensions: [
              DeokivePalette(
                primary: palette.primary,
                accent: palette.accent,
                background: palette.background,
                text: palette.text,
                softSurface: Colors.white,
              ),
            ],
          ),
          home: const HomeScreen(),
        ),
      ),
    );

    await tester.scrollUntilVisible(
      find.text('굿즈 DB'),
      180,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();

    expect(find.text('굿즈 DB'), findsOneWidget);
    expect(find.textContaining('정리된 공개 DB'), findsOneWidget);
    expect(find.text('검색 후 내 굿즈함 또는 위시리스트에 추가할 수 있어요.'),
        findsNothing);
    expect(find.widgetWithText(FilledButton, 'DB 보기'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
