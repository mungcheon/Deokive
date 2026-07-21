import 'package:flutter/material.dart';

enum BadgeCategory {
  collectionCount,
  spending,
  organizing,
}

class BadgeItem {
  final String id;
  final BadgeCategory category;
  final int level;
  final String title;
  final String description;
  final IconData icon;
  final Color color;

  const BadgeItem({
    required this.id,
    required this.category,
    required this.level,
    required this.title,
    required this.description,
    required this.icon,
    required this.color,
  });
}