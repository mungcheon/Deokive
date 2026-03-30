import 'package:flutter/foundation.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart' hide AppState;

import '../config/admob_catalog.dart';
import '../config/monetization_catalog.dart';
import '../state/app_state.dart';

class AdService {
  AdService._();

  static final AdService instance = AdService._();

  bool _initialized = false;
  final Map<AdPlacement, InterstitialAd?> _interstitialCache = {};

  Future<void> initialize() async {
    if (_initialized || !AdMobCatalog.isSupportedPlatform) return;
    await MobileAds.instance.initialize();
    _initialized = true;
  }

  bool canUseAds(AppState appState) {
    return AdMobCatalog.isSupportedPlatform &&
        !kIsWeb &&
        !appState.isFeatureUnlocked(PremiumFeature.adFree);
  }

  Future<void> preloadInterstitial(AdPlacement placement) async {
    if (!AdMobCatalog.isSupportedPlatform) return;
    if (placement != AdPlacement.folderInterstitial) return;
    final unitId = AdMobCatalog.unitId(AdUnitType.interstitial);
    if (unitId == null) return;
    if (_interstitialCache[placement] != null) return;

    await InterstitialAd.load(
      adUnitId: unitId,
      request: const AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (ad) {
          _interstitialCache[placement] = ad;
        },
        onAdFailedToLoad: (_) {},
      ),
    );
  }

  Future<void> showInterstitialIfReady(
    AdPlacement placement,
    AppState appState,
  ) async {
    if (!canUseAds(appState)) return;
    final ad = _interstitialCache.remove(placement);
    if (ad == null) {
      await preloadInterstitial(placement);
      return;
    }

    ad.fullScreenContentCallback = FullScreenContentCallback(
      onAdDismissedFullScreenContent: (ad) {
        ad.dispose();
        preloadInterstitial(placement);
      },
      onAdFailedToShowFullScreenContent: (ad, _) {
        ad.dispose();
        preloadInterstitial(placement);
      },
    );

    ad.show();
  }

  void dispose() {
    for (final ad in _interstitialCache.values) {
      ad?.dispose();
    }
    _interstitialCache.clear();
  }
}
