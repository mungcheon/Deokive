import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../data/board_posts.dart';
import '../state/app_state.dart';

class BoardPostEditorScreen extends StatefulWidget {
  final BoardPost? existing;

  const BoardPostEditorScreen({super.key, this.existing});

  @override
  State<BoardPostEditorScreen> createState() => _BoardPostEditorScreenState();
}

class _BoardPostEditorScreenState extends State<BoardPostEditorScreen> {
  late final TextEditingController titleController;
  late final TextEditingController summaryController;
  late final TextEditingController contentController;
  late final TextEditingController sourceUrlController;
  late BoardPostTag tag;
  /// Bot id (matching `kInfoBots[].id`) for info tag. Null = 관리자 byline
  /// (notice posts only).
  String? selectedBotId;
  Uint8List? selectedImage;

  bool get isEditing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    final ex = widget.existing;
    titleController = TextEditingController(text: ex?.title ?? '');
    summaryController = TextEditingController(text: ex?.summary ?? '');
    contentController = TextEditingController(text: ex?.content ?? '');
    sourceUrlController = TextEditingController(text: ex?.sourceUrl ?? '');
    tag = ex?.tag ?? BoardPostTag.info;
    // Try to recover the source bot from the existing author byline.
    if (ex != null) {
      for (final b in kInfoBots) {
        if (b.label == ex.author) {
          selectedBotId = b.id;
          break;
        }
      }
      selectedBotId ??= kInfoBots.first.id;
      selectedImage = ex.imageBytes;
    } else {
      selectedBotId = kInfoBots.first.id;
    }
  }

  @override
  void dispose() {
    titleController.dispose();
    summaryController.dispose();
    contentController.dispose();
    sourceUrlController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final pickedFile = await picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 1600,
      imageQuality: 85,
    );
    if (pickedFile == null) return;
    final bytes = await pickedFile.readAsBytes();
    setState(() => selectedImage = bytes);
  }

  void _removeImage() {
    setState(() => selectedImage = null);
  }

  Future<void> _pasteFromClipboard() async {
    final data = await Clipboard.getData('text/plain');
    final text = data?.text?.trim();
    if (text == null || text.isEmpty) return;
    setState(() {
      sourceUrlController.text = text;
      // Heuristic auto-fill: if URL looks like a tweet, prefill an X-source
      // title; the human still edits before saving.
      if (text.contains('x.com') || text.contains('twitter.com')) {
        if (titleController.text.isEmpty) {
          titleController.text = '공식 X 소식';
        }
        if (summaryController.text.isEmpty) {
          summaryController.text = '$text 에서 옮긴 글입니다.';
        }
      }
    });
  }

  String _authorForTag(BoardPostTag t, AppState appState) {
    if (t == BoardPostTag.general) {
      final nick = appState.currentDisplayName.trim();
      return nick.isEmpty ? '익명' : nick;
    }
    if (t == BoardPostTag.notice) return '관리자';
    final bot = infoBotById(selectedBotId ?? kInfoBots.first.id);
    return bot?.label ?? kInfoBots.first.label;
  }

  void _save() {
    final title = titleController.text.trim();
    final content = contentController.text.trim();
    if (title.isEmpty || content.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('제목과 본문을 입력해 주세요.')),
      );
      return;
    }
    final appState = context.read<AppState>();
    final isAdmin = appState.adminMode;

    // General-tag posts: derive summary from the first ~80 chars of the
    // body; source URL is admin-only.
    final summary = isAdmin
        ? (summaryController.text.trim().isEmpty
            ? title
            : summaryController.text.trim())
        : _summaryFromContent(content);
    final source = isAdmin ? sourceUrlController.text.trim() : '';
    final author = _authorForTag(tag, appState);

    if (isEditing) {
      final updated = widget.existing!.copyWith(
        title: title,
        summary: summary,
        content: content,
        tag: tag,
        author: author,
        sourceUrl: source.isEmpty ? null : source,
        imageBytes: selectedImage,
        clearImage: selectedImage == null,
      );
      appState.updateBoardPost(updated);
    } else {
      final post = BoardPost(
        id: 'p_${DateTime.now().microsecondsSinceEpoch}',
        tag: tag,
        title: title,
        summary: summary,
        content: content,
        date: DateTime.now(),
        author: author,
        authorId: appState.stableAuthorId,
        sourceUrl: source.isEmpty ? null : source,
        imageBytes: selectedImage,
      );
      appState.addBoardPost(post);
    }
    Navigator.pop(context, true);
  }

  String _summaryFromContent(String content) {
    final flat = content.replaceAll('\n', ' ').trim();
    if (flat.length <= 80) return flat;
    return '${flat.substring(0, 80)}…';
  }

  void _delete() {
    final ex = widget.existing;
    if (ex == null) return;
    showDialog<void>(
      context: context,
      builder: (dctx) => AlertDialog(
        title: const Text('게시글 삭제'),
        content: const Text('이 게시글을 삭제할까요?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dctx),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () {
              context.read<AppState>().deleteBoardPost(ex.id);
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
    final appState = context.watch<AppState>();
    final isAdmin = appState.adminMode;
    // Non-admin members can only post under the 자유 (general) tag.
    if (!isAdmin && tag != BoardPostTag.general) {
      tag = BoardPostTag.general;
    }
    final visibleTags = isAdmin
        ? BoardPostTag.values
        : const [BoardPostTag.general];
    return Scaffold(
      appBar: AppBar(
        title: Text(isEditing ? '게시글 수정' : '새 게시글'),
        actions: [
          if (isEditing)
            IconButton(
              icon: const Icon(Icons.delete_outline),
              onPressed: _delete,
            ),
          TextButton(
            onPressed: _save,
            child: Text(isEditing ? '저장' : '발행'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('태그', style: theme.textTheme.labelLarge),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            children: visibleTags.map((t) {
              final selected = tag == t;
              return ChoiceChip(
                label: Text(t.label),
                selected: selected,
                selectedColor: t.color.withValues(alpha: 0.22),
                labelStyle: TextStyle(
                  color: selected ? t.color : null,
                  fontWeight: FontWeight.w700,
                ),
                onSelected: isAdmin
                    ? (_) => setState(() => tag = t)
                    : null,
              );
            }).toList(),
          ),
          if (isAdmin && tag == BoardPostTag.info) ...[
            const SizedBox(height: 14),
            Text('정보봇 선택', style: theme.textTheme.labelLarge),
            const SizedBox(height: 6),
            DropdownButtonFormField<String>(
              initialValue: selectedBotId,
              isExpanded: true,
              decoration: const InputDecoration(
                isDense: true,
                border: OutlineInputBorder(),
              ),
              items: [
                for (final b in kInfoBots)
                  DropdownMenuItem(
                    value: b.id,
                    child: Text('${b.label}  (${b.sourceHandle})',
                        overflow: TextOverflow.ellipsis),
                  ),
              ],
              onChanged: (v) => setState(() => selectedBotId = v),
            ),
          ],
          const SizedBox(height: 16),
          Row(
            children: [
              Text('첨부 이미지', style: theme.textTheme.labelLarge),
              const Spacer(),
              if (selectedImage != null)
                TextButton.icon(
                  onPressed: _removeImage,
                  icon: const Icon(Icons.close, size: 16),
                  label: const Text('제거'),
                ),
              TextButton.icon(
                onPressed: _pickImage,
                icon: const Icon(Icons.image_outlined, size: 16),
                label: Text(selectedImage == null ? '추가' : '변경'),
              ),
            ],
          ),
          if (selectedImage != null) ...[
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.memory(
                selectedImage!,
                width: double.infinity,
                height: 180,
                fit: BoxFit.cover,
              ),
            ),
          ],
          const SizedBox(height: 16),
          TextField(
            controller: titleController,
            maxLength: 60,
            decoration: const InputDecoration(
              labelText: '제목',
              counterText: '',
            ),
          ),
          if (isAdmin) ...[
            const SizedBox(height: 12),
            TextField(
              controller: summaryController,
              maxLength: 100,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: '요약 (목록 카드에 노출)',
                counterText: '',
              ),
            ),
          ],
          const SizedBox(height: 12),
          TextField(
            controller: contentController,
            maxLines: 10,
            minLines: 5,
            decoration: const InputDecoration(
              labelText: '본문',
              alignLabelWithHint: true,
            ),
          ),
          if (isAdmin) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.link_rounded, size: 18),
                    const SizedBox(width: 6),
                    const Text('X 출처 URL (선택)',
                        style: TextStyle(fontWeight: FontWeight.w800)),
                    const Spacer(),
                    TextButton.icon(
                      onPressed: _pasteFromClipboard,
                      icon: const Icon(Icons.content_paste_rounded, size: 16),
                      label: const Text('붙여넣기'),
                    ),
                  ],
                ),
                TextField(
                  controller: sourceUrlController,
                  decoration: const InputDecoration(
                    hintText: 'https://x.com/...',
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '공식 X 게시물을 옮길 때 URL을 붙여넣으면 제목/요약이 자동 채워져요. 발행 전 직접 수정 가능.',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color:
                        theme.colorScheme.onSurface.withValues(alpha: 0.65),
                  ),
                ),
              ],
            ),
          ),
          ],
        ],
      ),
    );
  }
}
