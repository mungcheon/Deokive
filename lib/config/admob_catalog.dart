import 'dart:io';

import 'package:flutter/foundation.dart';

enum AdUnitType {
  banner,
  interstitial,
}

class AdMobCatalog {
  static const String androidTestAppId =
      'ca-app-pub-3940256099942544~3347511713';
  static const String iosTestAppId =
      'ca-app-pub-3940256099942544~1458002511';

  static const String androidBannerTestId =
      'ca-app-pub-3940256099942544/6300978111';
  static const String iosBannerTestId =
      'ca-app-pub-3940256099942544/2934735716';

  static const String androidInterstitialTestId =
      'ca-app-pub-3940256099942544/1033173712';
  static const String iosInterstitialTestId =
      'ca-app-pub-3940256099942544/4411468910';

  static bool get isSupportedPlatform {
    if (kIsWeb) return false;
    return Platform.isAndroid || Platform.isIOS;
  }

  static String? currentAppId() {
    if (!isSupportedPlatform) return null;
    if (Platform.isAndroid) return androidTestAppId;
    if (Platform.isIOS) return iosTestAppId;
    return null;
  }

  static String? unitId(AdUnitType type) {
    if (!isSupportedPlatform) return null;
    if (Platform.isAndroid) {
      switch (type) {
        case AdUnitType.banner:
          return androidBannerTestId;
        case AdUnitType.interstitial:
          return androidInterstitialTestId;
      }
    }
    if (Platform.isIOS) {
      switch (type) {
        case AdUnitType.banner:
          return iosBannerTestId;
        case AdUnitType.interstitial:
          return iosInterstitialTestId;
      }
    }
    return null;
  }
}
