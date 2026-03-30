import 'package:flutter/material.dart';

class FolderItem {
  final String id;
  final String name;
  final IconData icon;
  final Color color;
  final bool isGroup;
  final String? parentId;

  const FolderItem({
    required this.id,
    required this.name,
    required this.icon,
    required this.color,
    this.isGroup = false,
    this.parentId,
  });

  FolderItem copyWith({
    String? id,
    String? name,
    IconData? icon,
    Color? color,
    bool? isGroup,
    Object? parentId = _copyWithSentinel,
  }) {
    return FolderItem(
      id: id ?? this.id,
      name: name ?? this.name,
      icon: icon ?? this.icon,
      color: color ?? this.color,
      isGroup: isGroup ?? this.isGroup,
      parentId: identical(parentId, _copyWithSentinel)
          ? this.parentId
          : parentId as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'iconCodePoint': icon.codePoint,
      'iconFontFamily': icon.fontFamily,
      'iconFontPackage': icon.fontPackage,
      'color': color.toARGB32(),
      'isGroup': isGroup,
      'parentId': parentId,
    };
  }

  factory FolderItem.fromJson(Map<String, dynamic> json) {
    final iconCodePoint =
        json['iconCodePoint'] as int? ?? Icons.folder_rounded.codePoint;
    return FolderItem(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      icon: _iconFromCodePoint(iconCodePoint),
      color: Color(json['color'] as int? ?? const Color(0xFF87CEEB).toARGB32()),
      isGroup: json['isGroup'] as bool? ?? false,
      parentId: json['parentId'] as String?,
    );
  }
}

IconData _iconFromCodePoint(int codePoint) {
  if (codePoint == Icons.folder_copy_rounded.codePoint) {
    return Icons.folder_copy_rounded;
  }
  if (codePoint == Icons.favorite_rounded.codePoint) {
    return Icons.favorite_rounded;
  }
  if (codePoint == Icons.star_rounded.codePoint) {
    return Icons.star_rounded;
  }
  if (codePoint == Icons.music_note_rounded.codePoint) {
    return Icons.music_note_rounded;
  }
  if (codePoint == Icons.auto_awesome_rounded.codePoint) {
    return Icons.auto_awesome_rounded;
  }
  if (codePoint == Icons.face_rounded.codePoint) {
    return Icons.face_rounded;
  }
  if (codePoint == Icons.redeem_rounded.codePoint) {
    return Icons.redeem_rounded;
  }
  if (codePoint == Icons.photo_library_rounded.codePoint) {
    return Icons.photo_library_rounded;
  }
  if (codePoint == Icons.palette_rounded.codePoint) {
    return Icons.palette_rounded;
  }
  if (codePoint == Icons.workspace_premium_rounded.codePoint) {
    return Icons.workspace_premium_rounded;
  }
  if (codePoint == Icons.cloud_rounded.codePoint) {
    return Icons.cloud_rounded;
  }
  return Icons.folder_rounded;
}

const Object _copyWithSentinel = Object();
