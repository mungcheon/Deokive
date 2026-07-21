import 'package:deokive/screens/folder_editor_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('folder editor renders grouped icon choices and returns a folder',
      (tester) async {
    String? poppedName;
    bool? poppedIsGroup;

    await tester.pumpWidget(
      MaterialApp(
        home: Navigator(
          onGenerateRoute: (_) => MaterialPageRoute<void>(
            builder: (context) => Builder(
              builder: (context) => FilledButton(
                onPressed: () async {
                  final result = await Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => const FolderEditorScreen(isGroup: false),
                    ),
                  );
                  poppedName = result.name as String;
                  poppedIsGroup = result.isGroup as bool;
                },
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(find.text('굿즈 폴더 만들기'), findsOneWidget);
    expect(find.text('보관'), findsOneWidget);
    expect(find.text('굿즈'), findsOneWidget);
    expect(find.byTooltip('기본 폴더'), findsOneWidget);

    await tester.enterText(find.byType(TextField), '캔뱃지 앨범');
    await tester.tap(find.text('생성'));
    await tester.pumpAndSettle();

    expect(poppedName, '캔뱃지 앨범');
    expect(poppedIsGroup, isFalse);
  });
}
