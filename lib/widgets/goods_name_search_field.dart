import 'package:flutter/material.dart';

import '../models/goods_catalog_entry.dart';
import 'catalog_entry_image.dart';

const _catalogPickerActionBackground = Color(0xFF252938);
const _catalogPickerActionForeground = Color(0xFFFFFFFF);

/// Goods-name input that opens a catalog picker dialog when tapped.
/// Selecting a row fills the form from the read-only public DB.
class GoodsNameSearchField extends StatefulWidget {
  final TextEditingController controller;
  final List<GoodsCatalogEntry> catalog;
  final ValueChanged<GoodsCatalogEntry>? onCatalogSelected;
  final ValueChanged<String>? onChanged;

  const GoodsNameSearchField({
    super.key,
    required this.controller,
    required this.catalog,
    this.onCatalogSelected,
    this.onChanged,
  });

  @override
  State<GoodsNameSearchField> createState() => _GoodsNameSearchFieldState();
}

class _GoodsNameSearchFieldState extends State<GoodsNameSearchField> {
  Future<void> _openPicker() async {
    final picked = await showDialog<GoodsCatalogEntry>(
      context: context,
      builder: (_) => _GoodsCatalogPickerDialog(
        catalog: widget.catalog,
        initialQuery: widget.controller.text.trim(),
        actionLabel: '선택',
      ),
    );
    if (picked == null) return;
    widget.controller.text = picked.nameKo;
    widget.onCatalogSelected?.call(picked);
    widget.onChanged?.call(picked.nameKo);
  }

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: widget.controller,
      onChanged: widget.onChanged,
      decoration: InputDecoration(
        labelText: '굿즈 이름 *',
        helperText: '직접 입력하거나 돋보기를 눌러 공개 DB에서 찾아보세요',
        prefixIcon: const Icon(Icons.inventory_2_outlined),
        suffixIcon: IconButton(
          tooltip: '굿즈 DB 검색',
          icon: const Icon(Icons.search_rounded),
          onPressed: _openPicker,
        ),
      ),
      validator: (value) {
        if (value == null || value.trim().isEmpty) {
          return '굿즈 이름은 필수입니다.';
        }
        return null;
      },
    );
  }
}

/// Open the catalog picker dialog standalone.
/// Returns the picked entry, or null on cancel.
Future<GoodsCatalogEntry?> showGoodsCatalogPicker(
  BuildContext context, {
  required List<GoodsCatalogEntry> catalog,
  String initialQuery = '',
  int Function(GoodsCatalogEntry entry)? ownedCountBuilder,
  String actionLabel = '선택',
}) {
  return showDialog<GoodsCatalogEntry>(
    context: context,
    builder: (_) => _GoodsCatalogPickerDialog(
      catalog: catalog,
      initialQuery: initialQuery,
      actionLabel: actionLabel,
      ownedCountBuilder: ownedCountBuilder,
    ),
  );
}

class _GoodsCatalogPickerDialog extends StatefulWidget {
  final List<GoodsCatalogEntry> catalog;
  final String initialQuery;
  final String actionLabel;
  final int Function(GoodsCatalogEntry entry)? ownedCountBuilder;

  const _GoodsCatalogPickerDialog({
    required this.catalog,
    required this.initialQuery,
    required this.actionLabel,
    this.ownedCountBuilder,
  });

  @override
  State<_GoodsCatalogPickerDialog> createState() =>
      _GoodsCatalogPickerDialogState();
}

class _GoodsCatalogPickerDialogState extends State<_GoodsCatalogPickerDialog> {
  late final TextEditingController _searchController;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController(text: widget.initialQuery);
    _query = widget.initialQuery;
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  bool _matches(GoodsCatalogEntry entry, String q) {
    final lower = q.toLowerCase();
    if (entry.nameKo.toLowerCase().contains(lower)) return true;
    if (entry.nameJa != null && entry.nameJa!.toLowerCase().contains(lower)) {
      return true;
    }
    if (entry.nameEn != null && entry.nameEn!.toLowerCase().contains(lower)) {
      return true;
    }
    if (entry.characterName.toLowerCase().contains(lower)) return true;
    if (entry.affiliation.toLowerCase().contains(lower)) return true;
    if (entry.sourceStore.toLowerCase().contains(lower)) return true;
    if ((entry.seriesName ?? '').toLowerCase().contains(lower)) return true;
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final q = _query.trim();
    final results = q.isEmpty
        ? const <GoodsCatalogEntry>[]
        : widget.catalog.where((e) => _matches(e, q)).toList();

    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520, maxHeight: 640),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 8, 8),
              child: Row(
                children: [
                  const Icon(Icons.search_rounded),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      '굿즈 DB 검색',
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                    ),
                  ),
                  IconButton(
                    tooltip: '닫기',
                    icon: const Icon(Icons.close_rounded),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: TextField(
                controller: _searchController,
                autofocus: true,
                onChanged: (v) => setState(() => _query = v),
                decoration: InputDecoration(
                  hintText: '이름, 캐릭터, 작품, 판매처로 검색',
                  isDense: true,
                  prefixIcon: const Icon(Icons.search_rounded, size: 18),
                  suffixIcon: _query.isEmpty
                      ? null
                      : IconButton(
                          tooltip: '검색어 지우기',
                          icon: const Icon(Icons.close_rounded, size: 16),
                          onPressed: () {
                            _searchController.clear();
                            setState(() => _query = '');
                          },
                        ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: q.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(
                          '갖고 있는 굿즈 이름이나 캐릭터를 검색해 보세요.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: theme.colorScheme.onSurface
                                .withValues(alpha: 0.55),
                            fontSize: 13,
                          ),
                        ),
                      ),
                    )
                  : results.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24),
                            child: Text(
                              '검색 결과가 없어요. 직접 입력으로 추가할 수 있어요.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: 0.55),
                                fontSize: 13,
                              ),
                            ),
                          ),
                        )
                      : ListView.separated(
                          itemCount: results.length,
                          separatorBuilder: (_, __) =>
                              Divider(height: 1, color: theme.dividerColor),
                          itemBuilder: (context, i) => _CatalogRow(
                            entry: results[i],
                            actionLabel: widget.actionLabel,
                            ownedCount:
                                widget.ownedCountBuilder?.call(results[i]) ?? 0,
                          ),
                        ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(
                children: [
                  if (q.isNotEmpty)
                    Expanded(
                      child: Text(
                        '검색 결과 ${results.length}개',
                        style: TextStyle(
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.6),
                          fontSize: 12,
                        ),
                      ),
                    )
                  else
                    const Spacer(),
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('취소'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CatalogRow extends StatelessWidget {
  final GoodsCatalogEntry entry;
  final String actionLabel;
  final int ownedCount;

  const _CatalogRow({
    required this.entry,
    required this.actionLabel,
    required this.ownedCount,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final subtitle = [
      if (entry.characterName.isNotEmpty) entry.characterName,
      if (entry.affiliation.isNotEmpty) entry.affiliation,
      if (entry.sourceStore.isNotEmpty) entry.sourceStore,
    ].join(' · ');
    final priceText =
        entry.officialPriceJpy == null ? null : '¥${entry.officialPriceJpy}';
    return InkWell(
      onTap: () => Navigator.pop(context, entry),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Thumbnail(entry: entry),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entry.nameKo,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      height: 1.3,
                    ),
                  ),
                  if (subtitle.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 11.5,
                        color:
                            theme.colorScheme.onSurface.withValues(alpha: 0.65),
                      ),
                    ),
                  ],
                  if (entry.normalizedCategory.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      entry.normalizedCategory,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 11,
                        color:
                            theme.colorScheme.onSurface.withValues(alpha: 0.45),
                      ),
                    ),
                  ],
                  if (ownedCount > 0) ...[
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color:
                            theme.colorScheme.primary.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        '이미 $ownedCount개 보유 중',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w800,
                          color: theme.colorScheme.primary,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (priceText != null)
                  Text(
                    priceText,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                const SizedBox(height: 8),
                _CatalogPickerActionButton(
                  onPressed: () => Navigator.pop(context, entry),
                  label: actionLabel,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _CatalogPickerActionButton extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;

  const _CatalogPickerActionButton({
    required this.label,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: _catalogPickerActionBackground,
      borderRadius: BorderRadius.circular(999),
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onPressed,
        child: Container(
          constraints: const BoxConstraints(minWidth: 104, minHeight: 34),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: IconTheme(
            data: const IconThemeData(
              color: _catalogPickerActionForeground,
              size: 16,
            ),
            child: DefaultTextStyle.merge(
              style: const TextStyle(
                color: _catalogPickerActionForeground,
                fontSize: 12,
                fontWeight: FontWeight.w900,
                height: 1,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    Icons.add_rounded,
                    color: _catalogPickerActionForeground,
                  ),
                  const SizedBox(width: 4),
                  Flexible(
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text(
                        label,
                        style: const TextStyle(
                          inherit: false,
                          color: _catalogPickerActionForeground,
                          fontSize: 12,
                          fontWeight: FontWeight.w900,
                          height: 1,
                        ),
                        maxLines: 1,
                        softWrap: false,
                        overflow: TextOverflow.visible,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Thumbnail extends StatelessWidget {
  final GoodsCatalogEntry entry;

  const _Thumbnail({required this.entry});

  @override
  Widget build(BuildContext context) {
    return CatalogEntryImage(
      entry: entry,
      width: 56,
      height: 56,
      borderRadius: 8,
    );
  }
}
