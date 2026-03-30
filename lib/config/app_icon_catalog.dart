import 'package:flutter/material.dart';

class AppIconOption {
  final String key;
  final IconData icon;
  final String label;

  const AppIconOption({
    required this.key,
    required this.icon,
    required this.label,
  });
}

class AppIconCatalog {
  static const List<AppIconOption> folderIcons = [
    AppIconOption(key: 'folder', icon: Icons.folder_rounded, label: '기본 폴더'),
    AppIconOption(key: 'folder_copy', icon: Icons.folder_copy_rounded, label: '그룹 폴더'),
    AppIconOption(key: 'favorite', icon: Icons.favorite_rounded, label: '좋아요'),
    AppIconOption(key: 'star', icon: Icons.star_rounded, label: '스타'),
    AppIconOption(key: 'music', icon: Icons.music_note_rounded, label: '음악'),
    AppIconOption(key: 'sparkle', icon: Icons.auto_awesome_rounded, label: '반짝'),
    AppIconOption(key: 'face', icon: Icons.face_rounded, label: '캐릭터'),
    AppIconOption(key: 'redeem', icon: Icons.redeem_rounded, label: '굿즈'),
    AppIconOption(key: 'gallery', icon: Icons.photo_library_rounded, label: '포토'),
    AppIconOption(key: 'palette', icon: Icons.palette_rounded, label: '컬러'),
    AppIconOption(key: 'premium', icon: Icons.workspace_premium_rounded, label: '프리미엄'),
    AppIconOption(key: 'cloud', icon: Icons.cloud_rounded, label: '클라우드'),
  ];
}
