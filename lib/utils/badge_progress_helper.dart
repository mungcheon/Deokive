import '../models/badge_item.dart';
import '../models/folder_item.dart';
import '../models/goods_item.dart';

class BadgeProgress {
  final Set<String> unlockedBadgeIds;

  const BadgeProgress({
    required this.unlockedBadgeIds,
  });

  bool isUnlocked(String badgeId) {
    return unlockedBadgeIds.contains(badgeId);
  }

  int unlockedCountFor(List<BadgeItem> badges) {
    return badges.where((badge) => unlockedBadgeIds.contains(badge.id)).length;
  }
}

bool hasAnyDetailInput(GoodsItem item) {
  return (item.companyName?.trim().isNotEmpty ?? false) ||
      (item.purchasePlace?.trim().isNotEmpty ?? false) ||
      (item.storageLocation?.trim().isNotEmpty ?? false) ||
      (item.memo?.trim().isNotEmpty ?? false) ||
      item.purchaseDate != null;
}

bool hasCompleteBasicInput(GoodsItem item) {
  return item.name.trim().isNotEmpty &&
      item.category.trim().isNotEmpty &&
      item.quantity > 0 &&
      item.seriesName.trim().isNotEmpty &&
      item.officialPrice != null &&
      item.paidPrice != null &&
      item.purchaseDate != null;
}

BadgeProgress evaluateBadges({
  required List<GoodsItem> goodsItems,
  required List<FolderItem> folders,
}) {
  final unlocked = <String>{};

  final goodsCount = goodsItems.fold<int>(0, (sum, item) => sum + item.quantity);
  final totalSpent = goodsItems.fold<int>(
    0,
    (sum, item) => sum + ((item.paidPrice ?? 0) * item.quantity),
  );

  if (goodsCount >= 1) unlocked.add('count_01');
  if (goodsCount >= 5) unlocked.add('count_02');
  if (goodsCount >= 10) unlocked.add('count_03');
  if (goodsCount >= 30) unlocked.add('count_04');
  if (goodsCount >= 50) unlocked.add('count_05');
  if (goodsCount >= 100) unlocked.add('count_06');
  if (goodsCount >= 200) unlocked.add('count_07');
  if (goodsCount >= 500) unlocked.add('count_08');
  if (goodsCount >= 1000) unlocked.add('count_09');

  if (totalSpent >= 10000) unlocked.add('spend_01');
  if (totalSpent >= 50000) unlocked.add('spend_02');
  if (totalSpent >= 100000) unlocked.add('spend_03');
  if (totalSpent >= 300000) unlocked.add('spend_04');
  if (totalSpent >= 500000) unlocked.add('spend_05');
  if (totalSpent >= 1000000) unlocked.add('spend_06');
  if (totalSpent >= 3000000) unlocked.add('spend_07');
  if (totalSpent >= 5000000) unlocked.add('spend_08');
  if (totalSpent >= 10000000) unlocked.add('spend_09');

  final detailRecordedCount =
      goodsItems.where((item) => hasAnyDetailInput(item)).length;
  final customFolderCount =
      folders.where((folder) => folder.id != 'default-folder').length;
  final categoryAssignedCount =
      goodsItems.where((item) => item.category.trim().isNotEmpty).length;
  final officialPriceCount =
      goodsItems.where((item) => item.officialPrice != null).length;
  final completeBasicCount =
      goodsItems.where((item) => hasCompleteBasicInput(item)).length;
  final quantity3Exists = goodsItems.any((item) => item.quantity >= 3);
  final unopenedCount =
      goodsItems.where((item) => item.status == '미개봉').length;

  if (detailRecordedCount >= 1) unlocked.add('org_01');
  if (customFolderCount >= 1) unlocked.add('org_02');
  if (categoryAssignedCount >= 10) unlocked.add('org_03');
  if (officialPriceCount >= 10) unlocked.add('org_04');
  if (completeBasicCount >= 20) unlocked.add('org_05');
  if (quantity3Exists) unlocked.add('org_06');
  if (folders.length >= 5) unlocked.add('org_07');
  if (unopenedCount >= 10) unlocked.add('org_08');

  final organizingBaseCount = [
    'org_01',
    'org_02',
    'org_03',
    'org_04',
    'org_05',
    'org_06',
    'org_07',
    'org_08',
  ].where(unlocked.contains).length;

  if (organizingBaseCount >= 5) {
    unlocked.add('org_09');
  }

  return BadgeProgress(unlockedBadgeIds: unlocked);
}
