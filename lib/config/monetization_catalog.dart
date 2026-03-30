enum PremiumFeature {
  unlimitedFolders,
  unlimitedGoods,
  driveBackup,
  multiDeviceSync,
  adFree,
}

enum AdPlacement {
  homeBanner,
  folderInterstitial,
  newsFeedBanner,
  calendarBanner,
}

class PremiumFeatureSpec {
  final PremiumFeature feature;
  final String label;
  final String description;

  const PremiumFeatureSpec({
    required this.feature,
    required this.label,
    required this.description,
  });
}

class AdPlacementSpec {
  final AdPlacement placement;
  final String label;
  final String unitKey;
  final String note;

  const AdPlacementSpec({
    required this.placement,
    required this.label,
    required this.unitKey,
    required this.note,
  });
}

class MonetizationCatalog {
  static const List<PremiumFeatureSpec> premiumFeatures = [
    PremiumFeatureSpec(
      feature: PremiumFeature.unlimitedFolders,
      label: '폴더 무제한',
      description: '무료 계정의 폴더 2개 제한 없이 계속 폴더를 만들 수 있습니다.',
    ),
    PremiumFeatureSpec(
      feature: PremiumFeature.unlimitedGoods,
      label: '굿즈 무제한',
      description: '무료 계정의 굿즈 50개 제한 없이 계속 등록할 수 있습니다.',
    ),
    PremiumFeatureSpec(
      feature: PremiumFeature.driveBackup,
      label: 'Drive 백업',
      description: 'Google Drive에 개인 데이터를 백업하는 기능입니다.',
    ),
    PremiumFeatureSpec(
      feature: PremiumFeature.multiDeviceSync,
      label: '멀티 디바이스 동기화',
      description: '여러 기기에서 같은 계정 데이터를 동기화합니다.',
    ),
    PremiumFeatureSpec(
      feature: PremiumFeature.adFree,
      label: '광고 제거',
      description: '배너와 팝업 광고를 보지 않을 수 있습니다.',
    ),
  ];

  static const List<AdPlacementSpec> adPlacements = [
    AdPlacementSpec(
      placement: AdPlacement.homeBanner,
      label: '홈 배너',
      unitKey: 'home_banner',
      note: '홈 화면 상단 또는 중간에 노출되는 배너 영역입니다.',
    ),
    AdPlacementSpec(
      placement: AdPlacement.folderInterstitial,
      label: '폴더 전면 광고',
      unitKey: 'folder_interstitial',
      note: '폴더 탭 진입 시 노출될 수 있는 전면 광고 영역입니다.',
    ),
    AdPlacementSpec(
      placement: AdPlacement.newsFeedBanner,
      label: '소식 배너',
      unitKey: 'news_feed_banner',
      note: '공지와 소식 목록 하단에 들어가는 배너 영역입니다.',
    ),
    AdPlacementSpec(
      placement: AdPlacement.calendarBanner,
      label: '캘린더 배너',
      unitKey: 'calendar_banner',
      note: '캘린더 화면 하단 배너 영역입니다.',
    ),
  ];

  static PremiumFeatureSpec featureOf(PremiumFeature feature) {
    return premiumFeatures.firstWhere((item) => item.feature == feature);
  }

  static AdPlacementSpec placementOf(AdPlacement placement) {
    return adPlacements.firstWhere((item) => item.placement == placement);
  }
}
