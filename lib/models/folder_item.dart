import 'package:flutter/material.dart';

/// Reserved id for the auto-created system wishlist folder.
const String kSystemWishlistFolderId = '__system_wishlist__';

class FolderItem {
  final String id;
  final String name;
  final IconData icon;
  final Color color;
  final bool isGroup;
  final String? parentId;
  final bool isSystemWishlist;

  const FolderItem({
    required this.id,
    required this.name,
    required this.icon,
    required this.color,
    this.isGroup = false,
    this.parentId,
    this.isSystemWishlist = false,
  });

  FolderItem copyWith({
    String? id,
    String? name,
    IconData? icon,
    Color? color,
    bool? isGroup,
    Object? parentId = _copyWithSentinel,
    bool? isSystemWishlist,
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
      isSystemWishlist: isSystemWishlist ?? this.isSystemWishlist,
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
      'isSystemWishlist': isSystemWishlist,
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
      isSystemWishlist: json['isSystemWishlist'] as bool? ?? false,
    );
  }
}

IconData _iconFromCodePoint(int codePoint) {
  // The deprecated icons (redeem / photo_library / palette / workspace_premium)
  // are kept here so folders saved before the catalog refresh still render
  // correctly — they just can't be picked from the editor anymore.
  for (final icon in _knownIcons) {
    if (codePoint == icon.codePoint) return icon;
  }
  return Icons.folder_rounded;
}

const List<IconData> _knownIcons = [
  // Current catalog
  Icons.folder_rounded,
  Icons.folder_copy_rounded,
  Icons.cloud_rounded,
  Icons.favorite_rounded,
  Icons.star_rounded,
  Icons.auto_awesome_rounded,
  Icons.diamond_rounded,
  Icons.celebration_rounded,
  Icons.emoji_events_rounded,
  Icons.face_rounded,
  Icons.pets_rounded,
  Icons.toys_rounded,
  Icons.music_note_rounded,
  Icons.headphones_rounded,
  Icons.sports_esports_rounded,
  Icons.book_rounded,
  Icons.school_rounded,
  Icons.shopping_bag_rounded,
  Icons.cake_rounded,
  Icons.icecream_rounded,
  Icons.coffee_rounded,
  Icons.local_florist_rounded,
  Icons.spa_rounded,
  Icons.wb_sunny_rounded,
  Icons.nightlight_rounded,
  Icons.rocket_launch_rounded,
  // Deprecated but still loadable for legacy folders
  Icons.redeem_rounded,
  Icons.photo_library_rounded,
  Icons.palette_rounded,
  Icons.workspace_premium_rounded,
];

const Object _copyWithSentinel = Object();
