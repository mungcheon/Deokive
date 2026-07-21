import 'package:flutter/material.dart';

import '../config/app_icon_catalog.dart';
import '../config/app_palette_catalog.dart';
import '../models/folder_item.dart';

class FolderEditorScreen extends StatefulWidget {
  final FolderItem? initialFolder;
  final bool isGroup;

  const FolderEditorScreen({
    super.key,
    this.initialFolder,
    required this.isGroup,
  });

  @override
  State<FolderEditorScreen> createState() => _FolderEditorScreenState();
}

class _FolderEditorScreenState extends State<FolderEditorScreen> {
  late final TextEditingController _nameController;
  late IconData _selectedIcon;
  late Color _selectedColor;

  final List<AppIconOption> _iconOptions = AppIconCatalog.folderIcons;
  final List<Color> _colors = AppPaletteCatalog.folderColors;

  @override
  void initState() {
    super.initState();
    _nameController =
        TextEditingController(text: widget.initialFolder?.name ?? '');
    _selectedIcon = widget.initialFolder?.icon ??
        (widget.isGroup ? Icons.folder_copy_rounded : Icons.folder_rounded);
    _selectedColor = widget.initialFolder?.color ?? const Color(0xFF87CEEB);
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  static const Set<String> _reservedFolderNames = {
    '위시리스트',
    '즐겨찾기',
    'wishlist',
    'favorites',
    'お気に入り',
    'ウィッシュリスト',
    '收藏',
    '愿望清单',
  };

  bool _isReservedName(String name) {
    final lower = name.toLowerCase();
    return _reservedFolderNames.contains(name) ||
        _reservedFolderNames.contains(lower);
  }

  Map<String, List<AppIconOption>> get _groupedIcons {
    final grouped = <String, List<AppIconOption>>{};
    for (final option in _iconOptions) {
      grouped.putIfAbsent(option.group, () => []).add(option);
    }
    return grouped;
  }

  void _submit() {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('폴더 이름을 입력해 주세요.')),
      );
      return;
    }
    if (_isReservedName(name)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('위시리스트, 즐겨찾기 같은 시스템 이름은 사용할 수 없어요.')),
      );
      return;
    }

    Navigator.pop(
      context,
      FolderItem(
        id: widget.initialFolder?.id ?? '',
        name: name,
        icon: _selectedIcon,
        color: _selectedColor,
        isGroup: widget.isGroup,
        parentId: widget.initialFolder?.parentId,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isEditing = widget.initialFolder != null;
    final title = isEditing
        ? (widget.isGroup ? '굿즈 묶음 수정' : '굿즈 폴더 수정')
        : (widget.isGroup ? '굿즈 묶음 만들기' : '굿즈 폴더 만들기');

    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          _PreviewCard(
            name: _nameController.text.trim().isEmpty
                ? (widget.isGroup ? '새 굿즈 묶음' : '새 굿즈 폴더')
                : _nameController.text.trim(),
            icon: _selectedIcon,
            color: _selectedColor,
            isGroup: widget.isGroup,
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _nameController,
            textInputAction: TextInputAction.done,
            decoration: InputDecoration(
              labelText: widget.isGroup ? '묶음 이름' : '폴더 이름',
              hintText: widget.isGroup ? '예: 치이카와 존' : '예: 캔뱃지 앨범',
              prefixIcon: const Icon(Icons.edit_rounded),
            ),
            onChanged: (_) => setState(() {}),
            onSubmitted: (_) => _submit(),
          ),
          const SizedBox(height: 22),
          Text(
            '아이콘',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 10),
          ..._groupedIcons.entries.map(
            (entry) => _IconSection(
              title: entry.key,
              options: entry.value,
              selectedIcon: _selectedIcon,
              selectedColor: _selectedColor,
              onSelected: (icon) => setState(() => _selectedIcon = icon),
            ),
          ),
          const SizedBox(height: 18),
          Text(
            '색상',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 10),
          _ColorGrid(
            colors: _colors,
            selectedColor: _selectedColor,
            onSelected: (color) => setState(() => _selectedColor = color),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: SizedBox(
          height: 52,
          child: FilledButton.icon(
            onPressed: _submit,
            icon: Icon(isEditing ? Icons.check_rounded : Icons.add_rounded),
            label: Text(isEditing ? '저장' : '생성'),
          ),
        ),
      ),
    );
  }
}

class _PreviewCard extends StatelessWidget {
  final String name;
  final IconData icon;
  final Color color;
  final bool isGroup;

  const _PreviewCard({
    required this.name,
    required this.icon,
    required this.color,
    required this.isGroup,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.45)),
      ),
      child: Row(
        children: [
          Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: color.withValues(alpha: 0.24),
                  blurRadius: 18,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Icon(icon, color: Colors.white, size: 30),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isGroup ? '굿즈 묶음 미리보기' : '굿즈 폴더 미리보기',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.58),
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _IconSection extends StatelessWidget {
  final String title;
  final List<AppIconOption> options;
  final IconData selectedIcon;
  final Color selectedColor;
  final ValueChanged<IconData> onSelected;

  const _IconSection({
    required this.title,
    required this.options,
    required this.selectedIcon,
    required this.selectedColor,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: theme.textTheme.labelLarge?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.64),
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final option in options)
                _IconChoice(
                  option: option,
                  selected: selectedIcon == option.icon,
                  selectedColor: selectedColor,
                  onTap: () => onSelected(option.icon),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _IconChoice extends StatelessWidget {
  final AppIconOption option;
  final bool selected;
  final Color selectedColor;
  final VoidCallback onTap;

  const _IconChoice({
    required this.option,
    required this.selected,
    required this.selectedColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final foreground = selected
        ? selectedColor
        : theme.colorScheme.onSurface.withValues(alpha: 0.78);
    return Tooltip(
      message: option.label,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Ink(
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            color: selected
                ? selectedColor.withValues(alpha: 0.14)
                : theme.colorScheme.surface,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: selected
                  ? selectedColor
                  : theme.colorScheme.outline.withValues(alpha: 0.35),
              width: selected ? 1.8 : 1,
            ),
          ),
          child: Icon(option.icon, color: foreground, size: 25),
        ),
      ),
    );
  }
}

class _ColorGrid extends StatelessWidget {
  final List<Color> colors;
  final Color selectedColor;
  final ValueChanged<Color> onSelected;

  const _ColorGrid({
    required this.colors,
    required this.selectedColor,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final color in colors)
          GestureDetector(
            onTap: () => onSelected(color),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
                border: Border.all(
                  color: selectedColor == color
                      ? theme.colorScheme.onSurface
                      : theme.colorScheme.outline.withValues(alpha: 0.18),
                  width: selectedColor == color ? 2.6 : 1,
                ),
                boxShadow: [
                  if (selectedColor == color)
                    BoxShadow(
                      color: color.withValues(alpha: 0.35),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                ],
              ),
              child: selectedColor == color
                  ? Icon(
                      Icons.check_rounded,
                      color: _readableCheckColor(color),
                      size: 18,
                    )
                  : null,
            ),
          ),
      ],
    );
  }

  Color _readableCheckColor(Color color) {
    return color.computeLuminance() > 0.68 ? Colors.black87 : Colors.white;
  }
}
