import 'package:flutter/material.dart';

import '../config/app_icon_catalog.dart';
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

  final List<IconData> _icons = AppIconCatalog.folderIcons
      .map((item) => item.icon)
      .toList(growable: false);

  final List<Color> _colors = const [
    Color(0xFF87CEEB),
    Color(0xFFFFF491),
    Color(0xFF6DD3A0),
    Color(0xFFFFC857),
    Color(0xFFF28482),
    Color(0xFF84A59D),
    Color(0xFF90CAF9),
    Color(0xFFFFA7C4),
    Color(0xFF5CC8FF),
    Color(0xFFFF8A5B),
    Color(0xFFEF5DA8),
    Color(0xFFAED9E0),
  ];

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.initialFolder?.name ?? '');
    _selectedIcon = widget.initialFolder?.icon ??
        (widget.isGroup ? Icons.folder_copy_rounded : Icons.folder_rounded);
    _selectedColor = widget.initialFolder?.color ?? const Color(0xFF87CEEB);
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  void _submit() {
    final name = _nameController.text.trim();
    if (name.isEmpty) return;

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

    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.initialFolder == null
              ? (widget.isGroup ? '그룹 폴더 생성' : '폴더 생성')
              : (widget.isGroup ? '그룹 폴더 수정' : '폴더 수정'),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: _nameController,
                    decoration: InputDecoration(
                      labelText: widget.isGroup ? '그룹 폴더 이름' : '폴더 이름',
                    ),
                  ),
                  const SizedBox(height: 20),
                  const Text(
                    '아이콘',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _icons.map((icon) {
                      final selected = _selectedIcon == icon;
                      return InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: () {
                          setState(() {
                            _selectedIcon = icon;
                          });
                        },
                        child: Ink(
                          width: 44,
                          height: 44,
                          decoration: BoxDecoration(
                            color: selected
                                ? _selectedColor.withValues(alpha: 0.16)
                                : theme.colorScheme.surface,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: selected
                                  ? _selectedColor
                                  : theme.colorScheme.outline,
                              width: selected ? 1.6 : 1,
                            ),
                          ),
                          child: Icon(
                            icon,
                            color: selected
                                ? _selectedColor
                                : theme.colorScheme.onSurface,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 20),
                  const Text(
                    '색상',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: _colors.map((color) {
                      final selected = _selectedColor == color;
                      return GestureDetector(
                        onTap: () {
                          setState(() {
                            _selectedColor = color;
                          });
                        },
                        child: Container(
                          width: 34,
                          height: 34,
                          decoration: BoxDecoration(
                            color: color,
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: selected ? Colors.black : Colors.transparent,
                              width: 2,
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: SizedBox(
          height: 52,
          child: FilledButton(
            onPressed: _submit,
            child: Text(widget.initialFolder == null ? '생성' : '저장'),
          ),
        ),
      ),
    );
  }
}
