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
  // Grouped roughly: 기본 → 감정/장식 → 캐릭터·인형 → 취미 → 자연/시간
  static const List<AppIconOption> folderIcons = [
    // 기본
    AppIconOption(key: 'folder', icon: Icons.folder_rounded, label: '기본'),
    AppIconOption(key: 'folder_copy', icon: Icons.folder_copy_rounded, label: '그룹'),
    AppIconOption(key: 'cloud', icon: Icons.cloud_rounded, label: '클라우드'),

    // 감정 / 장식
    AppIconOption(key: 'favorite', icon: Icons.favorite_rounded, label: '하트'),
    AppIconOption(key: 'star', icon: Icons.star_rounded, label: '스타'),
    AppIconOption(key: 'sparkle', icon: Icons.auto_awesome_rounded, label: '반짝'),
    AppIconOption(key: 'diamond', icon: Icons.diamond_rounded, label: '보석'),

    // 캐릭터 / 인형
    AppIconOption(key: 'face', icon: Icons.face_rounded, label: '캐릭터'),
    AppIconOption(key: 'pets', icon: Icons.pets_rounded, label: '애완'),
    AppIconOption(key: 'toys', icon: Icons.toys_rounded, label: '인형'),

    // 취미
    AppIconOption(key: 'music', icon: Icons.music_note_rounded, label: '음악'),
    AppIconOption(key: 'headphones', icon: Icons.headphones_rounded, label: '헤드폰'),
    AppIconOption(key: 'game', icon: Icons.sports_esports_rounded, label: '게임'),
    AppIconOption(key: 'book', icon: Icons.book_rounded, label: '책'),

    // 자연 / 시간
    AppIconOption(key: 'sun', icon: Icons.wb_sunny_rounded, label: '햇살'),
    AppIconOption(key: 'moon', icon: Icons.nightlight_rounded, label: '달밤'),
  ];
}
