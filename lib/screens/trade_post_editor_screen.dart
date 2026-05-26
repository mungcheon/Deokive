import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../models/trade_post.dart';
import '../state/app_state.dart';

class TradePostEditorScreen extends StatefulWidget {
  final TradePost? existing;

  const TradePostEditorScreen({super.key, this.existing});

  @override
  State<TradePostEditorScreen> createState() => _TradePostEditorScreenState();
}

class _TradePostEditorScreenState extends State<TradePostEditorScreen> {
  late final TextEditingController titleController;
  late final TextEditingController descController;
  late final TextEditingController priceController;
  late final TextEditingController regionController;
  late final TextEditingController contactController;
  late TradeKind kind;
  late TradeStatus status;
  late List<Uint8List> images;

  bool get isEditing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    final ex = widget.existing;
    titleController = TextEditingController(text: ex?.title ?? '');
    descController = TextEditingController(text: ex?.description ?? '');
    priceController = TextEditingController(text: ex?.price?.toString() ?? '');
    regionController = TextEditingController(text: ex?.region ?? '');
    contactController = TextEditingController(text: ex?.contactInfo ?? '');
    kind = ex?.kind ?? TradeKind.sell;
    status = ex?.status ?? TradeStatus.active;
    images = List<Uint8List>.from(ex?.imageBytesList ?? const []);
  }

  @override
  void dispose() {
    titleController.dispose();
    descController.dispose();
    priceController.dispose();
    regionController.dispose();
    contactController.dispose();
    super.dispose();
  }

  Future<void> _addImage() async {
    if (images.length >= 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('사진은 최대 4장까지 추가할 수 있어요.')),
      );
      return;
    }
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 1600,
      imageQuality: 85,
    );
    if (pickedFile == null) return;
    final bytes = await pickedFile.readAsBytes();
    setState(() => images.add(bytes));
  }

  void _removeImage(int index) {
    setState(() => images.removeAt(index));
  }

  void _save() {
    final title = titleController.text.trim();
    final contact = contactController.text.trim();
    if (title.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('제목을 입력해 주세요.')),
      );
      return;
    }
    if (contact.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('연락 방법을 입력해 주세요 (오픈채팅 / SNS / 덕카이브 태그 등).')),
      );
      return;
    }
    final appState = context.read<AppState>();
    final price = int.tryParse(priceController.text.replaceAll(',', ''));
    final region = regionController.text.trim();

    if (isEditing) {
      final updated = widget.existing!.copyWith(
        kind: kind,
        status: status,
        title: title,
        description: descController.text.trim(),
        price: kind == TradeKind.free ? 0 : price,
        region: region.isEmpty ? null : region,
        contactInfo: contact,
        imageBytesList: images,
      );
      appState.updateTradePost(updated);
    } else {
      final post = TradePost(
        id: 't_${DateTime.now().microsecondsSinceEpoch}',
        authorId: appState.accountId,
        authorName: appState.displayName,
        kind: kind,
        status: TradeStatus.active,
        title: title,
        description: descController.text.trim(),
        price: kind == TradeKind.free ? 0 : price,
        priceCurrencyCode: appState.displayCurrency.code,
        region: region.isEmpty ? null : region,
        contactInfo: contact,
        imageBytesList: images,
        date: DateTime.now(),
      );
      appState.addTradePost(post);
    }
    Navigator.pop(context, true);
  }

  void _delete() {
    final ex = widget.existing;
    if (ex == null) return;
    showDialog<void>(
      context: context,
      builder: (dctx) => AlertDialog(
        title: const Text('거래 글 삭제'),
        content: const Text('이 거래 글을 삭제할까요?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dctx),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () {
              context.read<AppState>().deleteTradePost(ex.id);
              Navigator.pop(dctx);
              Navigator.pop(context, true);
            },
            child: const Text('삭제'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(isEditing ? '거래 글 수정' : '거래 글 작성'),
        actions: [
          if (isEditing)
            IconButton(
              icon: const Icon(Icons.delete_outline),
              onPressed: _delete,
            ),
          TextButton(onPressed: _save, child: const Text('저장')),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('유형', style: theme.textTheme.labelLarge),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            children: TradeKind.values.map((k) {
              final selected = kind == k;
              return ChoiceChip(
                label: Text(k.label),
                selected: selected,
                selectedColor: k.color.withValues(alpha: 0.22),
                labelStyle: TextStyle(
                  color: selected ? k.color : null,
                  fontWeight: FontWeight.w700,
                ),
                onSelected: (_) => setState(() => kind = k),
              );
            }).toList(),
          ),
          if (isEditing) ...[
            const SizedBox(height: 14),
            Text('진행 상태', style: theme.textTheme.labelLarge),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              children: TradeStatus.values.map((s) {
                final selected = status == s;
                return ChoiceChip(
                  label: Text(s.label),
                  selected: selected,
                  onSelected: (_) => setState(() => status = s),
                );
              }).toList(),
            ),
          ],
          const SizedBox(height: 16),
          TextField(
            controller: titleController,
            maxLength: 60,
            decoration: const InputDecoration(
              labelText: '제목',
              counterText: '',
              hintText: '예: 치이카와 마루푸와 인형 (시사) 미개봉',
            ),
          ),
          const SizedBox(height: 12),
          if (kind != TradeKind.free)
            TextField(
              controller: priceController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: '가격',
                prefixText: '₩ ',
              ),
            ),
          if (kind != TradeKind.free) const SizedBox(height: 12),
          TextField(
            controller: regionController,
            decoration: const InputDecoration(
              labelText: '거래 지역 (선택)',
              hintText: '예: 서울 강남 / 전국 택배',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: contactController,
            decoration: const InputDecoration(
              labelText: '연락 방법',
              hintText: '오픈채팅 URL / 인스타 ID / 덕카이브 태그',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: descController,
            minLines: 4,
            maxLines: 10,
            decoration: const InputDecoration(
              labelText: '상세 설명',
              alignLabelWithHint: true,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            '사진 (최대 4장)',
            style: theme.textTheme.labelLarge,
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (var i = 0; i < images.length; i++)
                Stack(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: Image.memory(
                        images[i],
                        width: 84,
                        height: 84,
                        fit: BoxFit.cover,
                      ),
                    ),
                    Positioned(
                      right: 0,
                      top: 0,
                      child: InkWell(
                        onTap: () => _removeImage(i),
                        child: Container(
                          padding: const EdgeInsets.all(2),
                          decoration: const BoxDecoration(
                            color: Colors.black54,
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(Icons.close,
                              color: Colors.white, size: 14),
                        ),
                      ),
                    ),
                  ],
                ),
              if (images.length < 4)
                InkWell(
                  borderRadius: BorderRadius.circular(10),
                  onTap: _addImage,
                  child: Container(
                    width: 84,
                    height: 84,
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: theme.colorScheme.outlineVariant),
                    ),
                    child: const Icon(Icons.add_a_photo_outlined),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF6E5),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Text(
              '⚠ 덕카이브는 직거래 게시판만 제공해요. 결제·배송 중개를 하지 않으며, 거래 관련 책임은 당사자 본인에게 있어요. 사기 의심 글은 신고해 주세요.',
              style: TextStyle(fontSize: 12.5, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}
