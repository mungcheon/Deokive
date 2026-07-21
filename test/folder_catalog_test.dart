import 'package:deokive/config/app_icon_catalog.dart';
import 'package:deokive/config/app_palette_catalog.dart';
import 'package:deokive/models/folder_item.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('folder icon catalog has stable unique keys', () {
    final keys = AppIconCatalog.folderIcons.map((item) => item.key).toList();

    expect(keys.toSet().length, keys.length);
    expect(AppIconCatalog.folderIcons.length, greaterThanOrEqualTo(210));
  });

  test('folder icon catalog entries can be restored from saved folders', () {
    for (final option in AppIconCatalog.folderIcons) {
      final folder = FolderItem(
        id: option.key,
        name: option.label,
        icon: option.icon,
        color: Colors.blue,
      );

      final restored = FolderItem.fromJson(folder.toJson());

      expect(
        restored.icon.codePoint,
        option.icon.codePoint,
        reason: '${option.key} should restore ${option.icon.codePoint}',
      );
    }
  });

  test('folder colors are unique and grouped as a long picker palette', () {
    final values = AppPaletteCatalog.folderColors
        .map((color) => color.toARGB32())
        .toList();

    expect(values.toSet().length, values.length);
    expect(AppPaletteCatalog.folderColors.length, greaterThanOrEqualTo(188));
  });
}
