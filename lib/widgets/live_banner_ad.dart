import 'package:flutter/material.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart' hide AppState;
import 'package:provider/provider.dart';

import '../config/admob_catalog.dart';
import '../config/monetization_catalog.dart';
import '../services/ad_service.dart';
import '../state/app_state.dart';
import 'ad_placeholder_card.dart';

class LiveBannerAd extends StatefulWidget {
  final AdPlacement placement;

  const LiveBannerAd({
    super.key,
    required this.placement,
  });

  @override
  State<LiveBannerAd> createState() => _LiveBannerAdState();
}

class _LiveBannerAdState extends State<LiveBannerAd> {
  BannerAd? _bannerAd;
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _loadBanner();
  }

  Future<void> _loadBanner() async {
    if (!AdMobCatalog.isSupportedPlatform) return;
    final unitId = AdMobCatalog.unitId(AdUnitType.banner);
    if (unitId == null) return;

    await AdService.instance.initialize();

    final banner = BannerAd(
      adUnitId: unitId,
      request: const AdRequest(),
      size: AdSize.banner,
      listener: BannerAdListener(
        onAdLoaded: (ad) {
          if (!mounted) return;
          setState(() {
            _bannerAd = ad as BannerAd;
            _loaded = true;
          });
        },
        onAdFailedToLoad: (ad, _) {
          ad.dispose();
          if (!mounted) return;
          setState(() {
            _bannerAd = null;
            _loaded = false;
          });
        },
      ),
    );

    banner.load();
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final appState = context.watch<AppState>();
    if (!AdService.instance.canUseAds(appState)) {
      return const SizedBox.shrink();
    }

    if (!AdMobCatalog.isSupportedPlatform || !_loaded || _bannerAd == null) {
      return AdPlaceholderCard(placement: widget.placement);
    }

    return SizedBox(
      width: _bannerAd!.size.width.toDouble(),
      height: _bannerAd!.size.height.toDouble(),
      child: AdWidget(ad: _bannerAd!),
    );
  }
}
