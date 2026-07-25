import 'package:deokive/models/goods_catalog_entry.dart';
import 'package:deokive/widgets/goods_name_search_field.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('catalog picker add action label stays visible', (tester) async {
    final entry = GoodsCatalogEntry(
      nameKo: '테스트 굿즈',
      seriesName: '테스트',
      category: '피규어',
      characterName: '캐릭터',
      officialPriceJpy: 1200,
      sourceStore: 'test',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) {
            return Scaffold(
              body: Center(
                child: ElevatedButton(
                  onPressed: () {
                    showGoodsCatalogPicker(
                      context,
                      catalog: [entry],
                      initialQuery: '테스트',
                      actionLabel: '추가하기',
                    );
                  },
                  child: const Text('열기'),
                ),
              ),
            );
          },
        ),
      ),
    );

    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();

    final addTextFinder = find.text('추가하기');
    final addTextStyle = tester.widget<Text>(addTextFinder).style!;

    expect(addTextStyle.color, const Color(0xFFFFFFFF));
    expect(addTextStyle.shadows, isEmpty);
    expect(tester.getSize(addTextFinder).width, greaterThanOrEqualTo(46));
  });
}
