import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';

import '../models/folder_item.dart';
import '../models/goods_catalog_entry.dart';
import '../models/goods_item.dart';
import '../state/app_state.dart';
import '../widgets/goods_name_search_field.dart';

Future<bool> showCatalogGoodsImportFlow(
  BuildContext context, {
  FolderItem? initialFolder,
}) async {
  final appState = context.read<AppState>();
  if (!appState.isLoggedIn) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('로그인이 필요합니다. 내 굿즈 정보는 이 기기에만 저장돼요.'),
      ),
    );
    return false;
  }

  final entry = await showGoodsCatalogPicker(
    context,
    catalog: appState.curatedCatalogEntries,
    ownedCountBuilder: (entry) => _ownedCountForCatalogEntry(appState, entry),
    actionLabel: '추가',
  );
  if (entry == null || !context.mounted) return false;

  return showCatalogGoodsImportFlowForEntry(
    context,
    entry: entry,
    initialFolder: initialFolder,
  );
}

Future<bool> showCatalogGoodsImportFlowForEntry(
  BuildContext context, {
  required GoodsCatalogEntry entry,
  FolderItem? initialFolder,
}) async {
  final appState = context.read<AppState>();
  if (!appState.isLoggedIn) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('로그인이 필요합니다. 내 굿즈 정보는 이 기기에만 저장돼요.'),
      ),
    );
    return false;
  }

  final shouldContinue =
      await _confirmDuplicateImport(context, appState, entry);
  if (!shouldContinue || !context.mounted) return false;

  final destination = await _pickDestinationForCatalogImport(
    context,
    appState,
    initialFolder: initialFolder,
  );
  if (destination == null || !context.mounted) return false;

  final imageBytes = await _downloadCatalogImage(entry);
  if (!context.mounted) return false;

  final item = goodsItemFromCatalogEntry(
    appState: appState,
    entry: entry,
    folder: destination.folder,
    addToWishlist: destination.addToWishlist,
    wishlistTargetFolder: destination.wishlistTargetFolder,
    imageBytes: imageBytes,
  );
  appState.addGoods(item);

  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text("'${entry.nameKo}'을(를) ${destination.folder.name}에 추가했어요."),
      action: SnackBarAction(
        label: '폴더 보기',
        onPressed: () => appState.setTab(2),
      ),
    ),
  );
  return true;
}

Future<bool> _confirmDuplicateImport(
  BuildContext context,
  AppState appState,
  GoodsCatalogEntry entry,
) async {
  final pickedName = entry.nameKo.trim();
  if (pickedName.isEmpty) return true;
  final matches = matchingCatalogGoodsItems(
    goodsItems: appState.goodsItems,
    entry: entry,
  );
  if (matches.isEmpty) return true;

  final folderNameById = {
    for (final folder in appState.folders) folder.id: folder.name,
  };
  final folderLines = matches
      .map((item) => folderNameById[item.folderId] ?? '알 수 없는 폴더')
      .toSet()
      .join(', ');

  final confirmed = await showDialog<bool>(
    context: context,
    builder: (dialogContext) {
      return AlertDialog(
        title: const Text('이미 보유 중인 굿즈예요'),
        content: Text(
          '"$pickedName"이(가) 이미 $folderLines에 있어요.\n그래도 하나 더 추가할까요?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('추가'),
          ),
        ],
      );
    },
  );
  return confirmed ?? false;
}

Future<_CatalogImportDestination?> _pickDestinationForCatalogImport(
  BuildContext context,
  AppState appState, {
  FolderItem? initialFolder,
}) async {
  final folders = _sortedImportTargetFolders(appState, initialFolder);
  final wishlistFolder = _wishlistFolder(appState);
  if (folders.isEmpty && wishlistFolder == null) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('먼저 굿즈를 넣을 폴더를 만들어 주세요.')),
    );
    return null;
  }

  var selectedKind = folders.isNotEmpty
      ? _CatalogImportKind.owned
      : _CatalogImportKind.wishlist;
  String? selectedId = initialFolder != null &&
          folders.any((folder) => folder.id == initialFolder.id)
      ? initialFolder.id
      : folders.isNotEmpty
          ? folders.first.id
          : null;

  return showModalBottomSheet<_CatalogImportDestination>(
    context: context,
    showDragHandle: true,
    builder: (sheetContext) {
      return StatefulBuilder(
        builder: (context, setSheetState) {
          final selectedFolder = selectedId == null
              ? null
              : folders.firstWhere(
                  (folder) => folder.id == selectedId,
                  orElse: () => folders.first,
                );
          final destinationFolder = selectedKind == _CatalogImportKind.wishlist
              ? wishlistFolder
              : selectedFolder;
          return SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'DB 굿즈 추가 위치',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '가지고 있는 굿즈는 폴더에, 사고 싶은 굿즈는 위시리스트에 담을 수 있어요.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context)
                              .colorScheme
                              .onSurface
                              .withValues(alpha: 0.58),
                        ),
                  ),
                  const SizedBox(height: 12),
                  if (wishlistFolder != null)
                    _CatalogImportDestinationTile(
                      icon: Icons.favorite_border_rounded,
                      iconColor: wishlistFolder.color,
                      title: '위시리스트에 추가',
                      subtitle: '구매가 0원, 상태 위시로 저장',
                      selected: selectedKind == _CatalogImportKind.wishlist,
                      onTap: () {
                        setSheetState(() {
                          selectedKind = _CatalogImportKind.wishlist;
                        });
                      },
                    ),
                  if (folders.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    _CatalogImportDestinationTile(
                      icon: Icons.inventory_2_rounded,
                      iconColor: Theme.of(context).colorScheme.primary,
                      title: '내 굿즈함에 추가',
                      subtitle: selectedFolder == null
                          ? '저장할 폴더를 선택해 주세요'
                          : '${selectedFolder.name}에 정가 구매, 미개봉으로 저장',
                      selected: selectedKind == _CatalogImportKind.owned,
                      onTap: () {
                        setSheetState(() {
                          selectedKind = _CatalogImportKind.owned;
                        });
                      },
                    ),
                  ],
                  const SizedBox(height: 8),
                  Flexible(
                    child: ListView.builder(
                      shrinkWrap: true,
                      itemCount: folders.length,
                      itemBuilder: (context, index) {
                        final folder = folders[index];
                        final folderType = folder.isGroup ? '그룹' : '폴더';
                        final selected =
                            selectedKind == _CatalogImportKind.owned &&
                                folder.id == selectedId;
                        final defaultLabel =
                            index == 0 ? '기본 저장 위치' : folderType;
                        return ListTile(
                          onTap: () {
                            setSheetState(() {
                              selectedKind = _CatalogImportKind.owned;
                              selectedId = folder.id;
                            });
                          },
                          leading: Icon(folder.icon, color: folder.color),
                          title: Text(folder.name),
                          subtitle: Text(
                            '$defaultLabel · 보유 ${appState.goodsCountForFolder(folder.id)}개',
                          ),
                          trailing: Icon(
                            selected
                                ? Icons.check_circle_rounded
                                : Icons.circle_outlined,
                            color: selected
                                ? Theme.of(context).colorScheme.primary
                                : Theme.of(context)
                                    .colorScheme
                                    .onSurface
                                    .withValues(alpha: 0.32),
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: FilledButton.icon(
                      onPressed: destinationFolder == null
                          ? null
                          : () => Navigator.pop(
                                sheetContext,
                                _CatalogImportDestination(
                                  folder: destinationFolder,
                                  addToWishlist: selectedKind ==
                                      _CatalogImportKind.wishlist,
                                  wishlistTargetFolder: selectedFolder,
                                ),
                              ),
                      icon: const Icon(Icons.add_rounded),
                      label: Text(
                        selectedKind == _CatalogImportKind.wishlist
                            ? '위시리스트에 추가'
                            : '선택한 폴더에 추가',
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      );
    },
  );
}

enum _CatalogImportKind {
  wishlist,
  owned,
}

class _CatalogImportDestination {
  final FolderItem folder;
  final bool addToWishlist;
  final FolderItem? wishlistTargetFolder;

  const _CatalogImportDestination({
    required this.folder,
    required this.addToWishlist,
    this.wishlistTargetFolder,
  });
}

FolderItem? _wishlistFolder(AppState appState) {
  for (final folder in appState.folders) {
    if (folder.isSystemWishlist || folder.id == kSystemWishlistFolderId) {
      return folder;
    }
  }
  return null;
}

class _CatalogImportDestinationTile extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  const _CatalogImportDestinationTile({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = selected ? theme.colorScheme.primary : iconColor;
    return Material(
      color: selected
          ? theme.colorScheme.primary.withValues(alpha: 0.08)
          : theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.44),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: selected
                  ? theme.colorScheme.primary.withValues(alpha: 0.45)
                  : theme.colorScheme.outline.withValues(alpha: 0.22),
            ),
          ),
          child: Row(
            children: [
              CircleAvatar(
                radius: 20,
                backgroundColor: color.withValues(alpha: 0.14),
                child: Icon(icon, color: color, size: 21),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color:
                            theme.colorScheme.onSurface.withValues(alpha: 0.62),
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                selected ? Icons.check_circle_rounded : Icons.circle_outlined,
                color: selected
                    ? theme.colorScheme.primary
                    : theme.colorScheme.onSurface.withValues(alpha: 0.28),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

GoodsItem goodsItemFromCatalogEntry({
  required AppState appState,
  required GoodsCatalogEntry entry,
  required FolderItem folder,
  bool addToWishlist = false,
  FolderItem? wishlistTargetFolder,
  Uint8List? imageBytes,
}) {
  final officialPrice = entry.officialPriceJpy ?? entry.officialPriceKrw;
  final officialCurrency =
      entry.officialPriceJpy != null ? Currency.jpy : Currency.krw;
  final paidCurrency =
      officialPrice == null ? appState.displayCurrency : officialCurrency;
  final category = entry.normalizedCategory.trim().isEmpty
      ? '기타'
      : entry.normalizedCategory.trim();

  return GoodsItem(
    id: appState.makeId(),
    folderId: folder.id,
    name: entry.nameKo.trim(),
    category: category,
    kind: entry.subSeries?.trim().isEmpty ?? true
        ? null
        : entry.subSeries!.trim(),
    quantity: 1,
    officialPrice: officialPrice,
    paidPrice: addToWishlist ? 0 : officialPrice,
    priceCurrencyCode: addToWishlist ? Currency.krw.code : paidCurrency.code,
    officialPriceCurrencyCode: officialCurrency.code,
    purchaseDate: null,
    isPreorder: false,
    itemCondition: addToWishlist ? ItemCondition.wish : ItemCondition.unopened,
    seriesName: entry.seriesName?.trim() ?? '',
    characterName: entry.characterName.trim(),
    affiliation:
        entry.affiliation.trim().isEmpty ? null : entry.affiliation.trim(),
    companyName:
        entry.sourceStore.trim().isEmpty ? null : entry.sourceStore.trim(),
    purchasePlace: null,
    releaseDate: _parseCatalogReleaseDate(entry.releaseDate),
    memo: entry.sourceUrl?.trim().isEmpty ?? true
        ? 'DB에서 추가'
        : 'DB에서 추가\n출처: ${entry.sourceUrl!.trim()}',
    plannedShippingDate: null,
    status: addToWishlist ? '위시' : '미개봉',
    purchaseState: addToWishlist ? PurchaseState.wished : PurchaseState.owned,
    wishlistTargetFolderId: addToWishlist ? wishlistTargetFolder?.id : null,
    barcode:
        entry.barcode?.trim().isEmpty ?? true ? null : entry.barcode!.trim(),
    storageLocation: null,
    imageBytesList: imageBytes == null ? const [] : [imageBytes],
    isFavorite: false,
  );
}

List<FolderItem> _sortedImportTargetFolders(
  AppState appState,
  FolderItem? initialFolder,
) {
  return sortedCatalogImportTargetFolders(
    folders: appState.owningFolders,
    initialFolder: initialFolder,
  );
}

List<FolderItem> sortedCatalogImportTargetFolders({
  required Iterable<FolderItem> folders,
  FolderItem? initialFolder,
}) {
  final source = folders.where((folder) => !folder.isSystemWishlist).toList();
  if (source.isEmpty) return const [];

  final originalIndexById = <String, int>{};
  for (var index = 0; index < source.length; index++) {
    originalIndexById[source[index].id] = index;
  }

  return [...source]..sort((a, b) {
      if (initialFolder != null) {
        if (a.id == initialFolder.id && b.id != initialFolder.id) return -1;
        if (b.id == initialFolder.id && a.id != initialFolder.id) return 1;
      }

      final aTopLevel = a.parentId == null ? 0 : 1;
      final bTopLevel = b.parentId == null ? 0 : 1;
      if (aTopLevel != bTopLevel) {
        return aTopLevel.compareTo(bTopLevel);
      }

      final aGroup = a.isGroup ? 1 : 0;
      final bGroup = b.isGroup ? 1 : 0;
      if (aGroup != bGroup) return aGroup.compareTo(bGroup);

      return (originalIndexById[a.id] ?? 0)
          .compareTo(originalIndexById[b.id] ?? 0);
    });
}

List<GoodsItem> matchingCatalogGoodsItems({
  required Iterable<GoodsItem> goodsItems,
  required GoodsCatalogEntry entry,
}) {
  final catalogName = entry.nameKo.trim();
  final catalogBarcode = entry.barcode?.trim() ?? '';
  return goodsItems.where((item) {
    final sameName = catalogName.isNotEmpty && item.name.trim() == catalogName;
    final sameBarcode = catalogBarcode.isNotEmpty &&
        (item.barcode?.trim() ?? '') == catalogBarcode;
    return sameName || sameBarcode;
  }).toList(growable: false);
}

int _ownedCountForCatalogEntry(AppState appState, GoodsCatalogEntry entry) {
  return matchingCatalogGoodsItems(
    goodsItems: appState.goodsItems,
    entry: entry,
  ).fold(0, (sum, item) => sum + item.quantity);
}

DateTime? _parseCatalogReleaseDate(String? raw) {
  final value = raw?.trim();
  if (value == null || value.isEmpty) return null;
  return DateTime.tryParse(value) ??
      DateTime.tryParse('$value-01') ??
      DateTime.tryParse('$value-01-01');
}

Future<Uint8List?> _downloadCatalogImage(GoodsCatalogEntry entry) async {
  final localPath = entry.localImagePath?.trim() ?? '';
  if (localPath.isNotEmpty && !kIsWeb) {
    try {
      final data = await rootBundle.load(localPath);
      return data.buffer.asUint8List();
    } catch (_) {
      // Fall back to the remote URL when a bundled cache file is unavailable.
    }
  }

  var url = entry.imageUrl?.trim() ?? '';
  if (url.isEmpty && kIsWeb) url = localPath;
  if (url.isEmpty) return null;
  url = url.replaceAll('&amp;', '&');
  if (url.startsWith('//')) url = 'https:$url';
  if (!url.startsWith('http')) return null;

  try {
    final response = await http.get(
      Uri.parse(url),
      headers: const {
        'User-Agent': 'Mozilla/5.0 Deokive/1.0',
        'Accept': 'image/*,*/*',
      },
    ).timeout(const Duration(seconds: 8));
    if (response.statusCode != 200 || response.bodyBytes.isEmpty) {
      return null;
    }
    return response.bodyBytes;
  } catch (_) {
    return null;
  }
}
