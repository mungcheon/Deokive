import 'dart:typed_data';

import 'package:deokive/models/folder_item.dart';
import 'package:deokive/models/goods_catalog_entry.dart';
import 'package:deokive/models/goods_item.dart';
import 'package:deokive/state/app_state.dart';
import 'package:deokive/utils/catalog_goods_importer.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
      'catalog entry import creates an unopened owned item in the target folder',
      () {
    final appState = AppState();
    final folder = FolderItem(
      id: 'top-folder',
      name: '대표 굿즈함',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    final entry = GoodsCatalogEntry(
      nameKo: '이치방쿠지 샘플 - A상 인형',
      nameJa: '一番くじ サンプル - A賞 ぬいぐるみ',
      category: '인형',
      characterName: '샘플 캐릭터',
      affiliation: '샘플 작품',
      seriesName: '이치방쿠지 샘플',
      subSeries: 'A상',
      officialPriceJpy: 790,
      barcode: '1234567890123',
      sourceStore: '이치방쿠지',
      sourceUrl: 'https://1kuji.com/products/sample',
      imageUrl: 'https://example.com/catalog/sample.jpg',
      releaseDate: '2026-01-23',
    );

    final item = goodsItemFromCatalogEntry(
      appState: appState,
      entry: entry,
      folder: folder,
    );

    expect(item.folderId, folder.id);
    expect(item.name, entry.nameKo);
    expect(item.category, '인형');
    expect(item.kind, 'A상');
    expect(item.quantity, 1);
    expect(item.officialPrice, 790);
    expect(item.paidPrice, 790);
    expect(item.priceCurrencyCode, Currency.jpy.code);
    expect(item.officialPriceCurrencyCode, Currency.jpy.code);
    expect(item.purchaseState, PurchaseState.owned);
    expect(item.itemCondition, ItemCondition.unopened);
    expect(item.seriesName, '이치방쿠지 샘플');
    expect(item.characterName, '샘플 캐릭터');
    expect(item.affiliation, '샘플 작품');
    expect(item.companyName, '이치방쿠지');
    expect(item.releaseDate, DateTime(2026, 1, 23));
    expect(item.barcode, '1234567890123');
    expect(item.imageUrl, 'https://example.com/catalog/sample.jpg');
    expect(item.status, '미개봉');
    expect(item.memo, contains('DB에서 추가'));
    expect(item.memo, contains(entry.sourceUrl!));
  });

  test(
      'catalog import keeps an image reference when image bytes are unavailable',
      () {
    final appState = AppState();
    final folder = FolderItem(
      id: 'top-folder',
      name: 'Top goods',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    const entry = GoodsCatalogEntry(
      nameKo: 'Remote image catalog item',
      category: 'figure',
      characterName: 'sample',
      sourceStore: 'official store',
      imageUrl: '//example.com/catalog/remote.jpg',
    );

    final item = goodsItemFromCatalogEntry(
      appState: appState,
      entry: entry,
      folder: folder,
    );
    final restored = GoodsItem.fromJson(item.toJson());

    expect(item.imageBytesList, isEmpty);
    expect(item.imageUrl, 'https://example.com/catalog/remote.jpg');
    expect(restored.imageUrl, item.imageUrl);
  });

  test('catalog import keeps remote image reference when bytes are unavailable',
      () {
    final appState = AppState();
    final folder = FolderItem(
      id: 'top-folder',
      name: 'Top goods',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    const entry = GoodsCatalogEntry(
      nameKo: 'Remote preferred catalog item',
      category: 'figure',
      characterName: 'sample',
      sourceStore: 'official store',
      localImagePath: 'assets/catalog/cache/sample.jpg',
      imageUrl: 'https://example.com/catalog/source.jpg',
    );

    final item = goodsItemFromCatalogEntry(
      appState: appState,
      entry: entry,
      folder: folder,
    );

    expect(item.imageUrl, 'https://example.com/catalog/source.jpg');
  });

  test('catalog import keeps remote image reference after loading bytes', () {
    final appState = AppState();
    final folder = FolderItem(
      id: 'top-folder',
      name: 'Top goods',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    const entry = GoodsCatalogEntry(
      nameKo: 'Bundled saved catalog item',
      category: 'figure',
      characterName: 'sample',
      sourceStore: 'official store',
      localImagePath: 'assets/catalog/cache/sample.jpg',
      imageUrl: 'https://example.com/catalog/source.jpg',
    );

    final item = goodsItemFromCatalogEntry(
      appState: appState,
      entry: entry,
      folder: folder,
      imageBytes: Uint8List.fromList([1, 2, 3]),
    );

    expect(item.imageBytesList.single, [1, 2, 3]);
    expect(item.imageUrl, 'https://example.com/catalog/source.jpg');
  });

  test('catalog DB import does not persist remote image bytes', () async {
    const entry = GoodsCatalogEntry(
      nameKo: 'Remote-only catalog item',
      category: 'figure',
      characterName: 'sample',
      sourceStore: 'official store',
      imageUrl: 'https://example.com/catalog/source.jpg',
    );

    final imageBytes = await loadCatalogEntryBundledImageBytes(entry);

    expect(imageBytes, isNull);
    expect(
      catalogEntryImageReference(entry, preferLocalAsset: false),
      'https://example.com/catalog/source.jpg',
    );
  });

  test('catalog import can load a bundled catalog image for saving', () async {
    const entry = GoodsCatalogEntry(
      nameKo: 'Image catalog item',
      category: 'figure',
      characterName: 'sample',
      sourceStore: 'official store',
      localImagePath: 'lib/logo.png',
    );

    final imageBytes = await loadCatalogEntryImageBytes(entry);

    expect(imageBytes, isNotNull);
    expect(imageBytes!.length, greaterThan(0));
  });

  test('catalog import keeps paid currency in JPY even when display is KRW',
      () {
    final appState = AppState();
    appState.setDisplayCurrency(Currency.krw);
    final folder = FolderItem(
      id: 'top-folder',
      name: '대표 굿즈함',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    const entry = GoodsCatalogEntry(
      nameKo: 'JPY catalog item',
      category: 'figure',
      characterName: 'sample',
      officialPriceJpy: 1980,
      sourceStore: 'official store',
    );

    final item = goodsItemFromCatalogEntry(
      appState: appState,
      entry: entry,
      folder: folder,
    );

    expect(item.officialPrice, 1980);
    expect(item.paidPrice, 1980);
    expect(item.priceCurrencyCode, Currency.jpy.code);
    expect(item.officialPriceCurrencyCode, Currency.jpy.code);
  });

  test(
      'catalog import can create a wishlist item with zero catalog-currency paid price',
      () {
    final appState = AppState();
    const wishlist = FolderItem(
      id: kSystemWishlistFolderId,
      name: '위시리스트',
      icon: Icons.favorite_rounded,
      color: Colors.amber,
      isSystemWishlist: true,
    );
    const targetFolder = FolderItem(
      id: 'future-folder',
      name: '나중에 넣을 폴더',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    const entry = GoodsCatalogEntry(
      nameKo: 'Wishlist catalog item',
      category: 'figure',
      characterName: 'sample',
      officialPriceJpy: 1980,
      sourceStore: 'official store',
    );

    final item = goodsItemFromCatalogEntry(
      appState: appState,
      entry: entry,
      folder: wishlist,
      addToWishlist: true,
      wishlistTargetFolder: targetFolder,
    );

    expect(item.folderId, wishlist.id);
    expect(item.officialPrice, 1980);
    expect(item.officialPriceCurrencyCode, Currency.jpy.code);
    expect(item.paidPrice, 0);
    expect(item.priceCurrencyCode, Currency.jpy.code);
    expect(item.purchaseState, PurchaseState.wished);
    expect(item.itemCondition, ItemCondition.wish);
    expect(item.status, '위시');
    expect(item.wishlistTargetFolderId, targetFolder.id);
  });

  test('catalog import duplicate matching also uses barcode', () {
    final appState = AppState();
    final folder = FolderItem(
      id: 'top-folder',
      name: '대표 굿즈함',
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
      name: '대표 굿즈함',
      icon: Icons.folder_rounded,
      color: Colors.blue,
    );
    const childFolder = FolderItem(
      id: 'child-folder',
      name: '하위 굿즈함',
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
