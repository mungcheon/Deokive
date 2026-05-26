import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/goods_item.dart';
import '../state/app_state.dart';
import 'edit_goods_screen.dart';

class GoodsDetailScreen extends StatelessWidget {
  final GoodsItem item;

  const GoodsDetailScreen({
    super.key,
    required this.item,
  });

  String formatDate(DateTime? date) {
    if (date == null) return '-';
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
  }

  String _formatPrice(int? amount, String currencyCode, AppState appState) {
    if (amount == null) return '-';
    final c = appState.currencyByCode(currencyCode);
    return '${c.symbol}$amount';
  }

  String priceCompareText(GoodsItem item, AppState appState) {
    final official = item.officialPrice;
    final paid = item.paidPrice;
    if (official == null || paid == null) return '-';
    final paidCur = appState.currencyByCode(item.priceCurrencyCode);
    final officialCur =
        appState.currencyByCode(item.effectiveOfficialPriceCurrencyCode);

    // Convert official to paid currency for an apples-to-apples diff.
    final officialInPaid =
        appState.convertCurrency(official, officialCur, paidCur);
    final diff = officialInPaid - paid;
    if (officialInPaid == 0) return '-';
    final ratePct = (diff / officialInPaid) * 100;
    final symbol = paidCur.symbol;

    if (diff == 0) return '정가 구매';
    final crossCurrency = officialCur != paidCur;
    final convertedNote = crossCurrency
        ? ' (정가 환산 $symbol$officialInPaid)'
        : '';
    if (diff > 0) {
      return '$symbol${diff.abs()} 이득 (${ratePct.abs().toStringAsFixed(1)}%)$convertedNote';
    }
    return '$symbol${diff.abs()} 손해 (${ratePct.abs().toStringAsFixed(1)}%)$convertedNote';
  }

  Future<void> _showPurchaseDialog(
    BuildContext context,
    AppState appState,
    GoodsItem currentItem,
  ) async {
    final targets = appState.owningFolders;
    if (targets.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('이동할 폴더가 없습니다. 먼저 폴더를 만들어주세요.')),
      );
      return;
    }
    String? selectedFolderId = currentItem.wishlistTargetFolderId ??
        (targets.isNotEmpty ? targets.first.id : null);
    final chosen = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setLocalState) {
            return AlertDialog(
              title: const Text('구매 완료로 표시'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('어느 폴더로 옮길까요?'),
                  const SizedBox(height: 12),
                  DropdownButton<String>(
                    value: selectedFolderId,
                    isExpanded: true,
                    items: targets
                        .map((folder) => DropdownMenuItem(
                              value: folder.id,
                              child: Text(folder.name),
                            ))
                        .toList(),
                    onChanged: (value) =>
                        setLocalState(() => selectedFolderId = value),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogContext),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: selectedFolderId == null
                      ? null
                      : () => Navigator.pop(dialogContext, selectedFolderId),
                  child: const Text('이동'),
                ),
              ],
            );
          },
        );
      },
    );
    if (chosen != null) {
      appState.markGoodsAsPurchased(currentItem.id, chosen);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('보유 폴더로 이동했습니다.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<AppState>(
      builder: (context, appState, _) {
        final currentItem = appState.goodsItems.firstWhere(
          (goods) => goods.id == item.id,
          orElse: () => item,
        );

        String folderName = '-';
        for (final folder in appState.folders) {
          if (folder.id == currentItem.folderId) {
            folderName = folder.name;
            break;
          }
        }

        return Scaffold(
          appBar: AppBar(
            title: const Text('굿즈 상세'),
            actions: [
              if (currentItem.isWishlistItem)
                IconButton(
                  tooltip: '구매 완료로 표시',
                  onPressed: () => _showPurchaseDialog(context, appState, currentItem),
                  icon: const Icon(Icons.shopping_bag_outlined),
                ),
              IconButton(
                onPressed: () => appState.toggleFavorite(currentItem.id),
                icon: Icon(
                  currentItem.isFavorite
                      ? Icons.favorite
                      : Icons.favorite_border,
                  color: currentItem.isFavorite ? Colors.pink : null,
                ),
              ),
              IconButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => EditGoodsScreen(item: currentItem),
                    ),
                  );
                },
                icon: const Icon(Icons.edit_outlined),
              ),
            ],
          ),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 900),
                  child: Column(
                    children: [
                      Container(
                        height: 280,
                        decoration: BoxDecoration(
                          color: Colors.grey.shade100,
                          borderRadius: BorderRadius.circular(22),
                        ),
                        clipBehavior: Clip.antiAlias,
                        child: currentItem.imageBytes != null
                            ? Image.memory(currentItem.imageBytes!, fit: BoxFit.cover)
                            : const Center(
                                child: Icon(Icons.image_outlined, size: 56),
                              ),
                      ),
                      const SizedBox(height: 20),
                      _SectionCard(
                        children: [
                          _InfoRow(label: '이름', value: currentItem.name),
                          _InfoRow(
                            label: '시리즈',
                            value: currentItem.seriesName.isEmpty
                                ? '-'
                                : currentItem.seriesName,
                          ),
                          _InfoRow(label: '카테고리', value: currentItem.category),
                          _InfoRow(label: '폴더', value: folderName),
                          _InfoRow(label: '상태', value: currentItem.status),
                          _InfoRow(label: '개수', value: '${currentItem.quantity}'),
                        ],
                      ),
                      const SizedBox(height: 14),
                      _SectionCard(
                        children: [
                          _InfoRow(
                            label: '정발가',
                            value: _formatPrice(
                              currentItem.officialPrice,
                              currentItem.effectiveOfficialPriceCurrencyCode,
                              appState,
                            ),
                          ),
                          _InfoRow(
                            label: '실구매가',
                            value: _formatPrice(
                              currentItem.paidPrice,
                              currentItem.priceCurrencyCode,
                              appState,
                            ),
                          ),
                          _InfoRow(
                            label: '가격 비교',
                            value: priceCompareText(currentItem, appState),
                          ),
                          _InfoRow(
                            label: '구매 날짜',
                            value: formatDate(currentItem.purchaseDate),
                          ),
                          _InfoRow(
                            label: '정발 회사명',
                            value: currentItem.companyName ?? '-',
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      _SectionCard(
                        children: [
                          _InfoRow(label: '메모', value: currentItem.memo ?? '-'),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _SectionCard extends StatelessWidget {
  final List<Widget> children;

  const _SectionCard({required this.children});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: BorderSide(color: Colors.grey.shade300),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(children: children),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 96,
            child: Text(
              label,
              style: TextStyle(
                color: Colors.grey.shade700,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}