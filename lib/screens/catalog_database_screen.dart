import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/folder_item.dart';
import '../models/goods_catalog_entry.dart';
import '../state/app_state.dart';
import '../theme/deokive_palette.dart';
import '../utils/catalog_goods_importer.dart';
import '../widgets/catalog_entry_image.dart';

const _catalogAddButtonBackground = Color(0xFF252938);
const _catalogAddButtonForeground = Colors.white;
const _catalogAddButtonDisabledBackground = Color(0xFFE7E9EE);
const _catalogAddButtonDisabledForeground = Color(0xFF5D6575);

class CatalogDatabaseScreen extends StatefulWidget {
  final FolderItem? initialFolder;

  const CatalogDatabaseScreen({
    super.key,
    this.initialFolder,
  });

  @override
  State<CatalogDatabaseScreen> createState() => _CatalogDatabaseScreenState();
}

class _CatalogDatabaseScreenState extends State<CatalogDatabaseScreen> {
  final TextEditingController _searchController = TextEditingController();
  final Set<String> _importingEntryKeys = {};
  String _query = '';
  String? _category;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _addEntryFromList(
    BuildContext context,
    GoodsCatalogEntry entry,
  ) async {
    final key = _identityKey(entry);
    if (_importingEntryKeys.contains(key)) return;
    setState(() => _importingEntryKeys.add(key));
    try {
      final added = await showCatalogGoodsImportFlowForEntry(
        context,
        entry: entry,
        initialFolder: widget.initialFolder,
      );
      if (added && mounted) {
        setState(() {});
      }
    } finally {
      if (mounted) {
        setState(() => _importingEntryKeys.remove(key));
      }
    }
  }

  List<GoodsCatalogEntry> _displayEntries(AppState appState) {
    final uniqueEntries = <GoodsCatalogEntry>[];
    final seenKeys = <String>{};

    for (final entry in appState.curatedCatalogEntries) {
      if (_isExampleEntry(entry)) continue;

      final key = _identityKey(entry);
      if (seenKeys.add(key)) {
        uniqueEntries.add(entry);
      }
    }

    return uniqueEntries;
  }

  List<GoodsCatalogEntry> _filteredEntries(AppState appState) {
    final normalizedQuery = _query.trim().toLowerCase();
    final normalizedCategory = _category?.trim();
    final entries = _displayEntries(appState).where((entry) {
      if (normalizedCategory != null &&
          normalizedCategory.isNotEmpty &&
          entry.normalizedCategory != normalizedCategory) {
        return false;
      }

      if (normalizedQuery.isEmpty) return true;
      final target = [
        entry.nameKo,
        entry.nameJa ?? '',
        entry.nameEn ?? '',
        entry.normalizedCategory,
        entry.characterName,
        entry.affiliation,
        entry.seriesName ?? '',
        entry.subSeries ?? '',
        entry.sourceStore,
        entry.barcode ?? '',
      ].join(' ').toLowerCase();
      return target.contains(normalizedQuery);
    }).toList();

    entries.sort((a, b) {
      final bySeries = (a.seriesName ?? '').compareTo(b.seriesName ?? '');
      if (bySeries != 0) return bySeries;
      return a.nameKo.compareTo(b.nameKo);
    });
    return entries;
  }

  List<String> _displayCategories(AppState appState) {
    final categories = <String>{};
    for (final entry in _displayEntries(appState)) {
      final category = entry.normalizedCategory.trim();
      if (category.isNotEmpty) categories.add(category);
    }
    final sorted = categories.toList()..sort();
    return sorted;
  }

  static String _identityKey(GoodsCatalogEntry entry) {
    final barcode = entry.barcode?.trim() ?? '';
    if (barcode.isNotEmpty) return 'barcode:$barcode';

    final identityParts = [
      entry.affiliation,
      entry.seriesName ?? '',
      entry.nameKo,
      entry.nameJa ?? '',
      entry.category,
      entry.characterName,
      entry.subSeries ?? '',
    ].map((value) => value.trim().toLowerCase()).join('|');
    if (identityParts.replaceAll('|', '').isNotEmpty) {
      return 'identity:$identityParts';
    }

    final sourceUrl = entry.sourceUrl?.trim().toLowerCase() ?? '';
    if (sourceUrl.isNotEmpty) return 'source:$sourceUrl';

    return 'entry:${entry.id ?? entry.hashCode}';
  }

  static bool _isExampleEntry(GoodsCatalogEntry entry) {
    final values = [
      entry.nameKo,
      entry.nameJa ?? '',
      entry.nameEn ?? '',
      entry.category,
      entry.characterName,
      entry.affiliation,
      entry.seriesName ?? '',
      entry.subSeries ?? '',
      entry.sourceStore,
      entry.sourceUrl ?? '',
      entry.displayImagePath ?? '',
    ].map((value) => value.trim().toLowerCase());

    return values.any(_looksLikeExampleText);
  }

  static bool _looksLikeExampleText(String value) {
    if (value.isEmpty) return false;

    return [
      'sample',
      'example',
      'placeholder',
      'image_placeholder',
      'no_image',
      'no-image',
      'noimage',
      'dummy',
      'test-image',
      'fixture',
      'blank',
      'default-image',
      'default_image',
      'coming-soon',
      'coming_soon',
      '예시',
      '샘플',
      '테스트',
      '더미',
    ].any(value.contains);
  }

  Future<void> _showAddSheet(
    BuildContext context,
    AppState appState,
    GoodsCatalogEntry entry,
  ) async {
    final parentContext = context;
    final ownedCount = matchingCatalogGoodsItems(
      goodsItems: appState.goodsItems,
      entry: entry,
    ).fold<int>(0, (sum, item) => sum + item.quantity);

    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheetContext) {
        final theme = Theme.of(sheetContext);
        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.80,
          minChildSize: 0.50,
          maxChildSize: 0.96,
          builder: (context, scrollController) {
            return SafeArea(
              child: ListView(
                controller: scrollController,
                padding: EdgeInsets.fromLTRB(
                  18,
                  4,
                  18,
                  18 + MediaQuery.of(sheetContext).viewInsets.bottom,
                ),
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _CatalogImage(entry: entry, size: 72),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              entry.nameKo,
                              maxLines: 3,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              _entrySubtitle(entry),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.62),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  Text(
                    '이 굿즈를 내 굿즈함에 추가하겠습니까?',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    widget.initialFolder == null
                        ? '다음 단계에서 저장할 폴더를 고를 수 있어요. 가장 위 폴더가 기본값이에요.'
                        : "'${widget.initialFolder!.name}' 폴더가 기본 저장 위치로 먼저 선택돼요.",
                    style: theme.textTheme.bodySmall?.copyWith(
                      color:
                          theme.colorScheme.onSurface.withValues(alpha: 0.62),
                    ),
                  ),
                  if (ownedCount > 0) ...[
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 9,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFF4D8),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.info_outline_rounded,
                            size: 18,
                            color: Color(0xFF9A6A12),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              '이미 내 굿즈함에 $ownedCount개 있어요. 그래도 추가할 수 있어요.',
                              style: const TextStyle(
                                color: Color(0xFF6E4A08),
                                fontSize: 12.5,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.pop(sheetContext),
                          child: const Text('취소'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        flex: 2,
                        child: _CatalogAddButton(
                          key: const Key('catalog-add-sheet-button'),
                          label: '내 굿즈에 추가하기',
                          icon: Icons.add_rounded,
                          expanded: true,
                          onPressed: () async {
                            Navigator.pop(sheetContext);
                            if (!parentContext.mounted) return;
                            final added =
                                await showCatalogGoodsImportFlowForEntry(
                              parentContext,
                              entry: entry,
                              initialFolder: widget.initialFolder,
                            );
                            if (added && mounted) {
                              setState(() {});
                            }
                          },
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final theme = Theme.of(context);
        final palette = theme.extension<DeokivePalette>()!;
        final entries = _filteredEntries(appState);
        final totalDisplayCount = _displayEntries(appState).length;
        final categories = _displayCategories(appState).take(18).toList();

        return Scaffold(
          appBar: AppBar(
            title: const Text('DB 보기'),
            actions: [
              Padding(
                padding: const EdgeInsets.only(right: 14),
                child: Center(
                  child: Text(
                    '${entries.length}/$totalDisplayCount',
                    style: theme.textTheme.labelLarge?.copyWith(
                      color:
                          theme.colorScheme.onSurface.withValues(alpha: 0.62),
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
            ],
          ),
          body: SafeArea(
            top: false,
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 10),
                  child: TextField(
                    controller: _searchController,
                    onChanged: (value) => setState(() => _query = value),
                    textInputAction: TextInputAction.search,
                    decoration: InputDecoration(
                      hintText: '굿즈명, 작품, 캐릭터, 바코드 검색',
                      prefixIcon: const Icon(Icons.search_rounded),
                      suffixIcon: _query.isEmpty
                          ? null
                          : IconButton(
                              tooltip: '검색어 지우기',
                              onPressed: () {
                                _searchController.clear();
                                setState(() => _query = '');
                              },
                              icon: const Icon(Icons.close_rounded),
                            ),
                    ),
                  ),
                ),
                SizedBox(
                  height: 42,
                  child: ListView(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    scrollDirection: Axis.horizontal,
                    children: [
                      _FilterChip(
                        label: '전체',
                        selected: _category == null,
                        color: palette.primary,
                        onTap: () => setState(() => _category = null),
                      ),
                      for (final category in categories) ...[
                        const SizedBox(width: 8),
                        _FilterChip(
                          label: category,
                          selected: _category == category,
                          color: palette.primary,
                          onTap: () => setState(() => _category = category),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: entries.isEmpty
                      ? const _EmptyCatalogResult()
                      : ListView.separated(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
                          itemCount: entries.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 10),
                          itemBuilder: (context, index) {
                            final entry = entries[index];
                            final ownedCount = matchingCatalogGoodsItems(
                              goodsItems: appState.goodsItems,
                              entry: entry,
                            ).fold<int>(0, (sum, item) => sum + item.quantity);
                            return _CatalogListTile(
                              entry: entry,
                              ownedCount: ownedCount,
                              isAdding: _importingEntryKeys
                                  .contains(_identityKey(entry)),
                              onPreview: () =>
                                  _showAddSheet(context, appState, entry),
                              onAdd: () => _addEntryFromList(context, entry),
                            );
                          },
                        ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _CatalogListTile extends StatelessWidget {
  final GoodsCatalogEntry entry;
  final int ownedCount;
  final bool isAdding;
  final VoidCallback onPreview;
  final Future<void> Function() onAdd;

  const _CatalogListTile({
    required this.entry,
    required this.ownedCount,
    required this.isAdding,
    required this.onPreview,
    required this.onAdd,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final palette = theme.extension<DeokivePalette>()!;
    return Material(
      color: theme.colorScheme.surface,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: ownedCount > 0
                ? palette.primary.withValues(alpha: 0.32)
                : theme.colorScheme.outline.withValues(alpha: 0.5),
          ),
        ),
        child: Row(
          children: [
            InkWell(
              borderRadius: BorderRadius.circular(16),
              onTap: onPreview,
              child: _CatalogImage(entry: entry, size: 58),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: onPreview,
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        entry.nameKo,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontWeight: FontWeight.w900,
                          fontSize: 14.5,
                        ),
                      ),
                      const SizedBox(height: 5),
                      Text(
                        _entrySubtitle(entry),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.58),
                        ),
                      ),
                      if (ownedCount > 0) ...[
                        const SizedBox(height: 7),
                        Text(
                          '내 굿즈함 $ownedCount개',
                          style: TextStyle(
                            color: palette.primary,
                            fontSize: 12,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            _CatalogAddButton(
              key: const Key('catalog-add-list-button'),
              label: isAdding ? '추가 중' : '추가하기',
              icon: isAdding ? Icons.more_horiz_rounded : Icons.add_rounded,
              disabled: isAdding,
              onPressed: () async => onAdd(),
            ),
          ],
        ),
      ),
    );
  }
}

class _CatalogAddButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool disabled;
  final bool expanded;
  final Future<void> Function()? onPressed;

  const _CatalogAddButton({
    super.key,
    required this.label,
    required this.icon,
    this.disabled = false,
    this.expanded = false,
    this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    final background = disabled
        ? _catalogAddButtonDisabledBackground
        : _catalogAddButtonBackground;
    final foreground = disabled
        ? _catalogAddButtonDisabledForeground
        : _catalogAddButtonForeground;

    final content = AnimatedContainer(
      duration: const Duration(milliseconds: 140),
      height: 40,
      constraints: BoxConstraints(
        minWidth: expanded ? 0 : 112,
        maxWidth: expanded ? double.infinity : 124,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 13),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
        boxShadow: disabled
            ? null
            : [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.12),
                  blurRadius: 12,
                  offset: const Offset(0, 5),
                ),
              ],
      ),
      child: Center(
        child: FittedBox(
          fit: BoxFit.scaleDown,
          child: DefaultTextStyle.merge(
            style: TextStyle(
              color: foreground,
              fontSize: 13,
              fontWeight: FontWeight.w900,
              height: 1,
            ),
            child: IconTheme.merge(
              data: IconThemeData(color: foreground, size: 17),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(icon, color: foreground),
                  const SizedBox(width: 5),
                  Text(
                    label,
                    maxLines: 1,
                    softWrap: false,
                    overflow: TextOverflow.visible,
                    style: TextStyle(color: foreground),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );

    if (disabled || onPressed == null) {
      return content;
    }

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(999),
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onPressed,
        child: content,
      ),
    );
  }
}

class _CatalogImage extends StatelessWidget {
  final GoodsCatalogEntry entry;
  final double size;

  const _CatalogImage({
    required this.entry,
    required this.size,
  });

  @override
  Widget build(BuildContext context) {
    return CatalogEntryImage(
      entry: entry,
      width: size,
      height: size,
      borderRadius: 16,
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final Color color;
  final VoidCallback onTap;

  const _FilterChip({
    required this.label,
    required this.selected,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ActionChip(
      onPressed: onTap,
      label: Text(label),
      avatar: selected ? const Icon(Icons.check_rounded, size: 16) : null,
      backgroundColor:
          selected ? color.withValues(alpha: 0.13) : Colors.transparent,
      side: BorderSide(
        color: selected
            ? color.withValues(alpha: 0.45)
            : Theme.of(context).colorScheme.outline.withValues(alpha: 0.55),
      ),
      labelStyle: TextStyle(
        color: selected ? color : Theme.of(context).colorScheme.onSurface,
        fontWeight: FontWeight.w800,
      ),
    );
  }
}

class _EmptyCatalogResult extends StatelessWidget {
  const _EmptyCatalogResult();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.search_off_rounded,
              size: 42,
              color: Theme.of(context)
                  .colorScheme
                  .onSurface
                  .withValues(alpha: 0.34),
            ),
            const SizedBox(height: 12),
            const Text(
              '검색 결과가 없어요',
              style: TextStyle(fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 4),
            Text(
              '검색어를 줄이거나 다른 분류를 선택해 보세요.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

String _entrySubtitle(GoodsCatalogEntry entry) {
  final parts = [
    entry.seriesName,
    entry.characterName,
    entry.normalizedCategory,
    entry.sourceStore,
  ]
      .whereType<String>()
      .map((value) => value.trim())
      .where((value) => value.isNotEmpty)
      .toList();
  if (parts.isEmpty) return '상세 정보 없음';
  return parts.join(' · ');
}
