import 'package:deokive/data/catalog/all.dart';
import 'package:deokive/models/folder_item.dart';
import 'package:deokive/screens/catalog_database_screen.dart';
import 'package:deokive/state/app_state.dart';
import 'package:deokive/theme/deokive_palette.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

void main() {
  testWidgets(
      'catalog database add flow keeps a live context after sheet close',
      (tester) async {
    final appState = AppState()
      ..isLoggedIn = true
      ..folders.add(
        const FolderItem(
          id: 'default-folder',
          name: 'Default',
          icon: Icons.folder_rounded,
          color: Colors.blue,
        ),
      );
    final entry = kFullCatalog.firstWhere(
      (item) =>
          (item.imageUrl ?? '').isEmpty && (item.localImagePath ?? '').isEmpty,
    );
    final palette = paletteSpecFor(AppPalette.zeroTwoPink);

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
          home: const CatalogDatabaseScreen(),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), entry.nameKo);
    await tester.pumpAndSettle();
    await tester.tap(find.text(entry.nameKo).first);
    await tester.pumpAndSettle();

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();
    expect(find.text('Default'), findsOneWidget);

    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(appState.goodsItems, hasLength(1));
    expect(appState.goodsItems.single.name, entry.nameKo);
    expect(appState.goodsItems.single.folderId, 'default-folder');
  });

  testWidgets('catalog database can add to local guest storage',
      (tester) async {
    final appState = AppState()
      ..isLoggedIn = false
      ..folders.add(
        const FolderItem(
          id: 'default-folder',
          name: 'Default',
          icon: Icons.folder_rounded,
          color: Colors.blue,
        ),
      );
    final entry = kFullCatalog.firstWhere(
      (item) =>
          (item.imageUrl ?? '').isEmpty && (item.localImagePath ?? '').isEmpty,
    );
    final palette = paletteSpecFor(AppPalette.zeroTwoPink);

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
          home: const CatalogDatabaseScreen(),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), entry.nameKo);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '추가').first);
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(appState.goodsItems, hasLength(1));
    expect(appState.goodsItems.single.name, entry.nameKo);
    expect(appState.goodsItems.single.folderId, 'default-folder');
  });

  testWidgets('catalog database preserves image reference when adding an item',
      (tester) async {
    final appState = AppState()
      ..isLoggedIn = false
      ..folders.add(
        const FolderItem(
          id: 'default-folder',
          name: 'Default',
          icon: Icons.folder_rounded,
          color: Colors.blue,
        ),
      );
    final entry = kFullCatalog.firstWhere(
      (item) =>
          (item.localImagePath ?? '').isNotEmpty &&
          item.nameKo.trim().isNotEmpty,
    );
    final palette = paletteSpecFor(AppPalette.zeroTwoPink);

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
          home: const CatalogDatabaseScreen(),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), entry.nameKo);
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).first);
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    final savedItem = appState.goodsItems.single;
    expect(savedItem.name, entry.nameKo);
    expect(savedItem.folderId, 'default-folder');
    expect(savedItem.imageUrl, isNotNull);
    expect(savedItem.imageUrl, isNotEmpty);
    expect(savedItem.imageBytesList, isNotEmpty);
  });

  testWidgets('catalog database can add even when saved folders are empty',
      (tester) async {
    final appState = AppState()..isLoggedIn = false;
    final entry = kFullCatalog.firstWhere(
      (item) =>
          (item.imageUrl ?? '').isEmpty && (item.localImagePath ?? '').isEmpty,
    );
    final palette = paletteSpecFor(AppPalette.zeroTwoPink);

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
          home: const CatalogDatabaseScreen(),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), entry.nameKo);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '추가').first);
    await tester.pumpAndSettle();
    await tester.tap(find.byType(FilledButton).last);
    await tester.pumpAndSettle();

    expect(appState.folders.map((folder) => folder.name), contains('기본 폴더'));
    expect(appState.goodsItems, hasLength(1));
    expect(appState.goodsItems.single.folderId, 'default-folder');
  });
}
