import 'package:deokive/models/folder_item.dart';
import 'package:deokive/models/goods_catalog_entry.dart';
import 'package:deokive/models/goods_item.dart';
import 'package:deokive/state/app_state.dart';
import 'package:deokive/utils/catalog_goods_importer.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('catalog entry import creates an owned goods item in the target folder',
      () {
    final appState = AppState();
    final folder = FolderItem(
      id: 'top-folder',
      name: '대표 굿즈',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    final entry = GoodsCatalogEntry(
      nameKo: '일번쿠지 샘플 - A상 피규어',
      nameJa: '一番くじ サンプル - A賞 フィギュア',
      category: '피규어',
      characterName: '샘플 캐릭터',
      affiliation: '샘플 작품',
      seriesName: '일번쿠지 샘플',
      subSeries: 'A상',
      officialPriceJpy: 790,
      barcode: '1234567890123',
      sourceStore: '이치방쿠지',
      sourceUrl: 'https://1kuji.com/products/sample',
      releaseDate: '2026-01-23',
    );

    final item = goodsItemFromCatalogEntry(
      appState: appState,
      entry: entry,
      folder: folder,
    );

    expect(item.folderId, folder.id);
    expect(item.name, entry.nameKo);
    expect(item.category, '피규어');
    expect(item.kind, 'A상');
    expect(item.quantity, 1);
    expect(item.officialPrice, 790);
    expect(item.officialPriceCurrencyCode, Currency.jpy.code);
    expect(item.purchaseState, PurchaseState.owned);
    expect(item.itemCondition, ItemCondition.unopened);
    expect(item.seriesName, '일번쿠지 샘플');
    expect(item.characterName, '샘플 캐릭터');
    expect(item.affiliation, '샘플 작품');
    expect(item.companyName, '이치방쿠지');
    expect(item.releaseDate, DateTime(2026, 1, 23));
    expect(item.barcode, '1234567890123');
    expect(item.memo, contains('DB에서 추가'));
    expect(item.memo, contains(entry.sourceUrl!));
  });

  test('catalog import duplicate matching also uses barcode', () {
    final appState = AppState();
    final folder = FolderItem(
      id: 'top-folder',
      name: '대표 굿즈',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    final ownedEntry = GoodsCatalogEntry(
      nameKo: '판매처 A 표기명',
      category: '인형',
      characterName: '샘플 캐릭터',
      affiliation: '샘플 작품',
      sourceStore: '공식 스토어',
      barcode: '4900000000001',
    );
    final pickedEntry = GoodsCatalogEntry(
      nameKo: '판매처 B 다른 표기명',
      category: '인형',
      characterName: '샘플 캐릭터',
      affiliation: '샘플 작품',
      sourceStore: '다른 스토어',
      barcode: '4900000000001',
    );
    appState.goodsItems.add(
      goodsItemFromCatalogEntry(
        appState: appState,
        entry: ownedEntry,
        folder: folder,
      ),
    );

    final matches = matchingCatalogGoodsItems(
      goodsItems: appState.goodsItems,
      entry: pickedEntry,
    );

    expect(matches, hasLength(1));
    expect(matches.single.name, '판매처 A 표기명');
  });

  test('catalog import target folders prefer the active folder or top folder',
      () {
    const wishlist = FolderItem(
      id: kSystemWishlistFolderId,
      name: '위시리스트',
      icon: Icons.shopping_bag_rounded,
      color: Colors.amber,
      isSystemWishlist: true,
    );
    const topFolder = FolderItem(
      id: 'top-folder',
      name: '대표 굿즈',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    const childFolder = FolderItem(
      id: 'child-folder',
      name: '하위 굿즈',
      icon: Icons.inventory_2_rounded,
      color: Colors.green,
      parentId: 'group-folder',
    );
    const groupFolder = FolderItem(
      id: 'group-folder',
      name: '그룹',
      icon: Icons.folder_copy_rounded,
      color: Colors.purple,
      isGroup: true,
    );

    final defaultOrder = sortedCatalogImportTargetFolders(
      folders: const [wishlist, childFolder, groupFolder, topFolder],
    );
    expect(defaultOrder.map((folder) => folder.id), [
      'top-folder',
      'group-folder',
      'child-folder',
    ]);

    final activeFolderOrder = sortedCatalogImportTargetFolders(
      folders: const [wishlist, childFolder, groupFolder, topFolder],
      initialFolder: childFolder,
    );
    expect(activeFolderOrder.first.id, 'child-folder');
    expect(activeFolderOrder, isNot(contains(wishlist)));
  });
}
