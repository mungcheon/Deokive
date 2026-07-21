import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';
import 'package:http/http.dart' as http;

import '../data/badge_definitions.dart';
import '../data/board_posts.dart';
import '../data/catalog/all.dart';
import '../config/google_auth_config.dart';
import '../models/badge_item.dart';
import '../models/calendar_event_item.dart';
import '../models/folder_item.dart';
import '../models/goods_catalog_entry.dart';
import '../models/goods_item.dart';
import '../models/support_inquiry_item.dart';
import '../models/trade_post.dart';
import '../config/server_config.dart';
import '../services/board_api_service.dart';
import '../services/catalog_api_service.dart';
import '../services/auth_api_service.dart';
import '../services/device_profile_api_service.dart';
import '../services/free_translation_service.dart';
import '../services/info_bot_service.dart';
import '../services/local_admin_override.dart';
import '../l10n/app_language.dart';
import '../services/exchange_rate_service.dart';
import '../theme/deokive_palette.dart';
import '../utils/badge_progress_helper.dart';

enum GoodsSortType {
  nameAsc,
  priceAsc,
  priceDesc,
  seriesAsc,
  purchaseDateNewest,
  purchaseDateOldest,
  releaseDateNewest,
  releaseDateOldest,
  quantityDesc,
  favoritesFirst,
  characterAsc,
  categoryAsc,
}

enum Currency {
  krw,
  usd,
  jpy,
  eur,
  cny,
}

extension CurrencyX on Currency {
  String get code {
    switch (this) {
      case Currency.krw:
        return 'KRW';
      case Currency.usd:
        return 'USD';
      case Currency.jpy:
        return 'JPY';
      case Currency.eur:
        return 'EUR';
      case Currency.cny:
        return 'CNY';
    }
  }

  String get symbol {
    switch (this) {
      case Currency.krw:
        return '₩';
      case Currency.usd:
        return '\$';
      case Currency.jpy:
        return '¥';
      case Currency.eur:
        return '€';
      case Currency.cny:
        return '¥';
    }
  }

  /// Static rate table relative to KRW (1 KRW = rate * targetCurrency).
  /// Manual values for now; replace with FX API in Phase 1.
  double get rateFromKrw {
    switch (this) {
      case Currency.krw:
        return 1.0;
      case Currency.usd:
        return 1 / 1380.0;
      case Currency.jpy:
        return 1 / 9.0;
      case Currency.eur:
        return 1 / 1490.0;
      case Currency.cny:
        return 1 / 190.0;
    }
  }
}

enum FolderSortType {
  nameAsc,
  goodsCountDesc,
}

enum AuthProviderType {
  guest,
  local,
  google,
}

/// Cached translation/processing result for a board post in one target
/// language. Stored under `appState.postTranslations[postId][langCode]`.
class ProcessedTranslation {
  final String title;
  final String summary;
  final String content;
  final DateTime translatedAt;

  const ProcessedTranslation({
    required this.title,
    required this.summary,
    required this.content,
    required this.translatedAt,
  });

  Map<String, dynamic> toJson() => {
        'title': title,
        'summary': summary,
        'content': content,
        'translatedAt': translatedAt.toIso8601String(),
      };

  factory ProcessedTranslation.fromJson(Map<String, dynamic> json) {
    return ProcessedTranslation(
      title: json['title'] as String? ?? '',
      summary: json['summary'] as String? ?? '',
      content: json['content'] as String? ?? '',
      translatedAt: DateTime.tryParse(json['translatedAt'] as String? ?? '') ??
          DateTime.now(),
    );
  }
}

class AppState extends ChangeNotifier {
  static const _reservedAdminNickname = '관리자';
  static const Set<String> _reservedNicknameTerms = {
    '관리자',
    '공지봇',
    '정보봇',
  };
  static const _storageBoxName = 'deokive_storage';
  static const _localAccountsKey = 'local_accounts';
  static const _nextSignupSequenceKey = 'next_signup_sequence';
  static const _pushEnabledKey = 'push_enabled';
  static const _darkModeKey = 'dark_mode_enabled';
  static const _paletteKey = 'app_palette';
  static const _fontScaleKey = 'font_scale';
  static const _fontFamilyKey = 'font_family';
  static const _showcaseBgTierKey = 'showcase_bg_tier';
  static const _boardPostsKey = 'board_posts';
  static const _tradePostsKey = 'trade_posts';
  static const _infoBotFeedsKey = 'info_bot_feeds';
  static const _claudeApiKeyKey = 'claude_api_key';
  static const _postTranslationsKey = 'post_translations';

  /// Bumped when we need a one-time data migration. Bump the version when
  /// changing migration logic.
  static const _viewCountResetVersionKey = 'view_count_reset_v1';
  static const _purchaseRecordsKey = 'purchase_records';
  static const _permissionFlagsKey = 'permission_flags';
  static const _lastAuthProviderKey = 'last_auth_provider';
  static const _lastAccountIdKey = 'last_account_id';
  static const _serverAccessTokenKey = 'server_access_token';
  static const _deviceIdKey = 'device_id';
  static const _deviceNicknameKey = 'device_nickname';
  static const _lastDeviceNicknameKey = 'last_device_nickname';
  static const _boardCommentSeenKey = 'board_comment_seen_map';
  static const _keepSignedInKey = 'keep_signed_in';
  static const _languageKey = 'app_language';
  static const _currencyKey = 'display_currency';

  final List<FolderItem> folders = [];
  final List<GoodsItem> goodsItems = [];
  final List<CalendarEventItem> calendarEvents = [];
  final List<SupportInquiryItem> inquiries = [];
  final List<String> equippedBadgeIds = [];

  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: const ['email'],
    clientId: GoogleAuthConfig.webClientId,
    serverClientId: GoogleAuthConfig.webServerClientId,
  );
  final List<Map<String, dynamic>> _localAccounts = [];

  Box<dynamic>? _storageBox;
  Future<void>? _storageInitFuture;
  Timer? _infoBotRefreshAnchorTimer;
  Timer? _infoBotRefreshTimer;
  Timer? _boardSyncTimer;
  bool _isNavigationReloading = false;
  bool _isSyncingBoard = false;
  bool _localAdminSessionInjected = false;
  final CatalogApiService _catalogApi = CatalogApiService();
  List<GoodsCatalogEntry> _remoteCatalogEntries = const [];
  bool isSyncingCatalog = false;
  DateTime? catalogSyncedAt;
  String? catalogSyncError;
  String? _lastCatalogUpdatedAt;
  String? _lastBoardUpdatedAt;

  int currentTabIndex = 0;
  bool isLoggedIn = false;
  bool startupResolved = false;

  /// True when the user chose "browse as guest" from the welcome screen.
  /// Transient — not persisted across launches.
  bool inGuestSession = false;
  bool pushEnabled = true;
  bool darkModeEnabled = false;
  double fontScale = 1.0;
  String? fontFamily;

  /// Selected showcase background tier. `-1` = background off.
  int selectedShowcaseBgTier = -1;

  /// Legacy client-only admin toggle removed. Keep the field for compatibility
  /// with older UI code paths, but the app no longer enables admin mode.
  bool adminMode = false;
  final List<BoardPost> boardPosts = [];
  final List<TradePost> tradePosts = [];

  /// Post IDs the current user has liked (heart).
  final Set<String> likedPostIds = {};

  /// Post IDs the current user has bookmarked (save).
  final Set<String> bookmarkedPostIds = {};

  /// Comments per post: postId → list of BoardComment.
  final Map<String, List<BoardComment>> postComments = {};
  final List<String> _pendingBoardCommentAlerts = [];
  final Map<String, int> _seenBoardCommentIdsByPost = {};

  /// Aggregated like counts per post (so multi-user backends can later sync
  /// real counts; for now this mirrors likedPostIds locally).
  final Map<String, int> postLikeCounts = {};

  /// Per-bot RSS URL override. Empty string = use the bot's default.
  final Map<String, String> infoBotFeedOverrides = {};
  bool isRefreshingInfoBots = false;

  /// Claude API key (Anthropic). Empty = not configured; translation features
  /// disabled. Stored in Hive for v1 — move to FlutterSecureStorage if this
  /// app ever ships to multiple users.
  String claudeApiKey = '';

  /// translated post fields keyed by `postId → langCode → fields`.
  final Map<String, Map<String, ProcessedTranslation>> postTranslations = {};
  final Set<String> _inFlightTranslations = {};
  bool isGoogleLinked = false;
  bool googleSignInAvailable = false;
  String? googleSignInError;
  bool driveBackupEnabled = false;
  bool keepSignedIn = true;
  String? serverAccessToken;

  AuthProviderType authProvider = AuthProviderType.guest;
  AppPalette appPalette = AppPalette.zeroTwoPink;
  AppLanguage appLanguage = AppLanguage.korean;
  Currency displayCurrency = Currency.krw;

  String displayName = 'Guest';
  String accountId = '로그인이 필요합니다';
  String tag = '@guest';
  String deviceId = '';
  Uint8List? profileImageBytes;
  String? profileImageUrl;
  int avatarBodyType = -1;
  int avatarBackgroundType = -1;
  int avatarHairStyle = -1;
  int avatarHairColorIndex = -1;
  int avatarAccentColorIndex = -1;
  int avatarOutfitColorIndex = -1;
  int avatarSkinToneIndex = -1;
  bool avatarHasHat = false;
  bool avatarHasCape = false;
  bool avatarHasHandheld = false;
  bool avatarHasBackRibbon = false;

  int _signupSequence = 1;

  FolderSortType folderSortType = FolderSortType.nameAsc;
  GoodsSortType defaultGoodsSortType = GoodsSortType.nameAsc;

  void init() {
    _ensureDefaultFolder();
    if (folders.isEmpty) {
      folders.add(
        const FolderItem(
          id: 'default-folder',
          name: '기본 폴더',
          icon: Icons.folder_rounded,
          color: Color(0xFF87CEEB),
          isGroup: false,
          parentId: null,
        ),
      );
    }

    _storageInitFuture ??= _initStorage();
    _initGoogleSignIn();
    _startInfoBotAutoRefreshScheduler();
    _startBoardAutoSyncScheduler();
    notifyListeners();
  }

  void _startInfoBotAutoRefreshScheduler() {
    _infoBotRefreshAnchorTimer?.cancel();
    _infoBotRefreshTimer?.cancel();

    final now = DateTime.now();
    final nextHour = DateTime(
      now.year,
      now.month,
      now.day,
      now.hour + 1,
    );
    final initialDelay = nextHour.difference(now);

    _infoBotRefreshAnchorTimer = Timer(initialDelay, () {
      unawaited(refreshInfoBots());
      _infoBotRefreshTimer = Timer.periodic(const Duration(hours: 1), (_) {
        unawaited(refreshInfoBots());
      });
    });
  }

  void _startBoardAutoSyncScheduler() {
    _boardSyncTimer?.cancel();
    _boardSyncTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      unawaited(syncBoardFromServer());
    });
  }

  Future<void> _ensureStorageReady() async {
    _storageInitFuture ??= _initStorage();
    await _storageInitFuture;
  }

  Future<void> _initStorage() async {
    try {
      final openBox = Hive.openBox(_storageBoxName);
      _storageBox ??= ServerConfig.staticSite && kIsWeb
          ? await openBox.timeout(const Duration(seconds: 4))
          : await openBox;
      _restoreStorageValues();
      _restoreDeviceIdentity();
      if (ServerConfig.personalDataLocalOnly) {
        serverAccessToken = null;
        driveBackupEnabled = false;
        await _storageBox?.delete(_serverAccessTokenKey);
      }
      await _restoreSavedSession();
      await _loadAccountData();
      notifyListeners();
      final hasServer = !ServerConfig.personalDataLocalOnly &&
          await ServerConfig.ensureResolved();
      if (hasServer) {
        notifyListeners();
        await _refreshAdminModeFromServer();
        unawaited(syncBoardFromServer());
        unawaited(syncCatalogFromServer());
      } else {
        // Background-fill cached translations for any pre-existing posts that
        // don't have one yet (seed notices, posts added before this version).
        unawaited(_backfillBoardTranslations());
      }
    } catch (error, stackTrace) {
      if (kDebugMode) {
        debugPrint('storage init failed: $error');
        debugPrint('$stackTrace');
      }
      _storageBox = null;
      _ensureDefaultFolder();
    } finally {
      startupResolved = true;
      notifyListeners();
    }
  }

  /// Walk every post in [boardPosts] and translate the ones that don't yet
  /// have a cached translation in the current app language. Runs
  /// sequentially with a small inter-call delay so we don't hammer the
  /// free Google Translate endpoint.
  Future<void> _backfillBoardTranslations() async {
    final code = appLanguage.translationCode;
    // Snapshot so concurrent edits don't break the iteration.
    final snapshot = List<BoardPost>.from(boardPosts);
    for (final post in snapshot) {
      if (cachedTranslationFor(post.id, code) != null) continue;
      if (post.title.trim().isEmpty && post.content.trim().isEmpty) continue;
      try {
        await translateBoardPost(post, code);
        // Light throttle — keeps the unofficial endpoint from rate-limiting.
        await Future<void>.delayed(const Duration(milliseconds: 250));
      } catch (e) {
        if (kDebugMode) debugPrint('backfill failed ${post.id}: $e');
      }
    }
  }

  void _restoreStorageValues() {
    final savedAccounts =
        _storageBox?.get(_localAccountsKey, defaultValue: <dynamic>[])
                as List<dynamic>? ??
            <dynamic>[];
    _localAccounts
      ..clear()
      ..addAll(
        savedAccounts
            .map((item) => Map<String, dynamic>.from(item as Map))
            .toList(),
      );

    _signupSequence =
        _storageBox?.get(_nextSignupSequenceKey, defaultValue: 1) as int? ?? 1;
    pushEnabled =
        _storageBox?.get(_pushEnabledKey, defaultValue: true) as bool? ?? true;
    darkModeEnabled =
        _storageBox?.get(_darkModeKey, defaultValue: false) as bool? ?? false;
    fontScale = (_storageBox?.get(_fontScaleKey, defaultValue: 1.0) as num?)
            ?.toDouble() ??
        1.0;
    fontFamily = _storageBox?.get(_fontFamilyKey) as String?;
    selectedShowcaseBgTier =
        (_storageBox?.get(_showcaseBgTierKey, defaultValue: -1) as int?) ?? -1;
    adminMode = false;
    _loadBoardPosts();
    _loadBoardSocial();
    _loadTradePosts();
    _loadInfoBotFeeds();
    _loadClaudeApiKey();
    _loadPostTranslations();
    keepSignedIn =
        _storageBox?.get(_keepSignedInKey, defaultValue: true) as bool? ?? true;

    final savedPaletteName = _storageBox?.get(_paletteKey,
            defaultValue: AppPalette.zeroTwoPink.name) as String? ??
        AppPalette.zeroTwoPink.name;
    if (savedPaletteName.toLowerCase().contains('highcontrast')) {
      _storageBox?.put(_paletteKey, AppPalette.zeroTwoPink.name);
    }
    appPalette = AppPalette.values.firstWhere(
      (item) => item.name == savedPaletteName,
      orElse: () => AppPalette.zeroTwoPink,
    );
    final savedLanguageName = _storageBox?.get(_languageKey,
            defaultValue: AppLanguage.korean.name) as String? ??
        AppLanguage.korean.name;
    appLanguage = AppLanguage.values.firstWhere(
      (item) => item.name == savedLanguageName,
      orElse: () => AppLanguage.korean,
    );
    final savedCurrencyName = _storageBox?.get(_currencyKey,
            defaultValue: Currency.krw.name) as String? ??
        Currency.krw.name;
    displayCurrency = Currency.values.firstWhere(
      (item) => item.name == savedCurrencyName,
      orElse: () => Currency.krw,
    );
  }

  void _restoreDeviceIdentity() {
    final savedDeviceId = (_storageBox?.get(_deviceIdKey) as String?)?.trim();
    if (savedDeviceId == null || savedDeviceId.isEmpty) {
      deviceId = 'dev_${DateTime.now().microsecondsSinceEpoch}';
      _storageBox?.put(_deviceIdKey, deviceId);
    } else {
      deviceId = savedDeviceId;
    }

    final savedNickname =
        (_storageBox?.get(_deviceNicknameKey) as String?)?.trim();
    if (savedNickname != null && savedNickname.isNotEmpty) {
      isLoggedIn = true;
      authProvider = AuthProviderType.local;
      displayName = savedNickname;
      accountId = deviceId;
      tag = '@$savedNickname';
    }
  }

  Future<void> _persistStorageValues() async {
    if (_storageBox == null) return;
    await _storageBox!.put(_localAccountsKey, _localAccounts);
    await _storageBox!.put(_nextSignupSequenceKey, _signupSequence);
    await _storageBox!.put(_pushEnabledKey, pushEnabled);
    await _storageBox!.put(_darkModeKey, darkModeEnabled);
    await _storageBox!.put(_paletteKey, appPalette.name);
    await _storageBox!.put(_fontScaleKey, fontScale);
    if (fontFamily == null) {
      await _storageBox!.delete(_fontFamilyKey);
    } else {
      await _storageBox!.put(_fontFamilyKey, fontFamily);
    }
    await _storageBox!.put(_showcaseBgTierKey, selectedShowcaseBgTier);
    await _storageBox!.delete('admin_mode');
    await _storageBox!.put(_keepSignedInKey, keepSignedIn);
    await _storageBox!.put(_languageKey, appLanguage.name);
    await _storageBox!.put(_currencyKey, displayCurrency.name);
  }

  void setDisplayCurrency(Currency currency) {
    if (displayCurrency == currency) return;
    displayCurrency = currency;
    _persistStorageValues();
    notifyListeners();
  }

  void cycleDisplayCurrency() {
    final next =
        Currency.values[(displayCurrency.index + 1) % Currency.values.length];
    setDisplayCurrency(next);
  }

  int convertKrwTo(int amountKrw, Currency target) {
    return (amountKrw * target.rateFromKrw).round();
  }

  /// Convert between arbitrary currencies via KRW pivot.
  int convertCurrency(int amount, Currency from, Currency to) {
    if (from == to) return amount;
    if (amount == 0) return 0;
    final asKrw = amount / from.rateFromKrw;
    return (asKrw * to.rateFromKrw).round();
  }

  Currency currencyByCode(String code, {Currency fallback = Currency.krw}) {
    return Currency.values.firstWhere(
      (c) => c.code == code,
      orElse: () => fallback,
    );
  }

  String formatPriceInDisplayCurrency(int amountKrw) {
    final converted = convertKrwTo(amountKrw, displayCurrency);
    return '${displayCurrency.symbol}${converted.toString()}';
  }

  /// Format an amount already expressed in `displayCurrency` (e.g. the value
  /// returned by `totalPaidAmount`) with the currency symbol.
  String formatInDisplayCurrency(num amount) {
    return '${displayCurrency.symbol}${amount.round()}';
  }

  Future<void> _persistAuthSession() async {
    if (_storageBox == null) return;
    if (!keepSignedIn ||
        !isLoggedIn ||
        authProvider == AuthProviderType.guest) {
      await _storageBox!.delete(_lastAuthProviderKey);
      await _storageBox!.delete(_lastAccountIdKey);
      await _storageBox!.delete(_serverAccessTokenKey);
      return;
    }
    await _storageBox!.put(_lastAuthProviderKey, authProvider.name);
    await _storageBox!.put(_lastAccountIdKey, accountId);
    if (!ServerConfig.personalDataLocalOnly &&
        (serverAccessToken ?? '').isNotEmpty) {
      await _storageBox!.put(_serverAccessTokenKey, serverAccessToken);
    } else {
      await _storageBox!.delete(_serverAccessTokenKey);
    }
  }

  Future<void> _clearPersistedAuthSession() async {
    if (_storageBox == null) return;
    await _storageBox!.delete(_lastAuthProviderKey);
    await _storageBox!.delete(_lastAccountIdKey);
    await _storageBox!.delete(_serverAccessTokenKey);
  }

  Future<void> _restoreSavedSession() async {
    if (!keepSignedIn || _storageBox == null) return;

    final savedNickname =
        (_storageBox!.get(_deviceNicknameKey) as String?)?.trim() ?? '';
    if (savedNickname.isEmpty) {
      await _clearPersistedAuthSession();
      isLoggedIn = false;
      isGoogleLinked = false;
      driveBackupEnabled = false;
      authProvider = AuthProviderType.guest;
      serverAccessToken = null;
      displayName = 'Guest';
      accountId = 'nickname_required';
      tag = '@guest';
      return;
    }

    await _clearPersistedAuthSession();
  }

  void _applyServerLocalSession(
    ServerProfile profile,
    String token,
  ) {
    final linked = _findLocalAccount(profile.loginId);
    final linkedEmail = (linked?['linkedGoogleEmail'] as String?)?.trim();
    final hasGoogleLink = linkedEmail != null && linkedEmail.isNotEmpty;

    isLoggedIn = true;
    isGoogleLinked = hasGoogleLink;
    authProvider = AuthProviderType.local;
    driveBackupEnabled = false;
    displayName = profile.nickname.trim().isEmpty
        ? 'Deokive User'
        : profile.nickname.trim();
    accountId = profile.loginId;
    tag = profile.tag.trim().isEmpty ? _allocateTag() : profile.tag.trim();
    profileImageUrl = (profile.profileImageUrl ?? '').trim().isEmpty
        ? null
        : profile.profileImageUrl!.trim();
    serverAccessToken = token;
  }

  String get _currentStorageAccountKey {
    switch (authProvider) {
      case AuthProviderType.google:
        return 'google_${_sanitizeStorageKey(accountId)}';
      case AuthProviderType.local:
        return 'local_${_sanitizeStorageKey(accountId)}';
      case AuthProviderType.guest:
        if (accountId == 'nickname_required') {
          return _deviceScopedStorageAccountKey;
        }
        return 'guest';
    }
  }

  String _sanitizeStorageKey(String value) {
    return value.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
  }

  String _normalizeAccountId(String value) => value.trim().toLowerCase();

  String get _deviceScopedStorageAccountKey =>
      'local_${_sanitizeStorageKey(deviceId)}';

  String _accountDataBoxKey([String? accountKey]) {
    return 'account_data_${accountKey ?? _currentStorageAccountKey}';
  }

  Future<void> _writeStoredAccountPayload(
    Map<String, dynamic> payload, {
    String? accountKey,
  }) async {
    if (_storageBox == null) return;
    await _storageBox!.put(
      _accountDataBoxKey(accountKey),
      const JsonEncoder.withIndent('  ').convert(payload),
    );
  }

  Future<Map<String, dynamic>?> _readStoredAccountPayload([
    String? accountKey,
  ]) async {
    final raw = _storageBox?.get(_accountDataBoxKey(accountKey));
    if (raw == null) return null;
    if (raw is String && raw.trim().isNotEmpty) {
      return Map<String, dynamic>.from(jsonDecode(raw) as Map);
    }
    if (raw is Map) {
      return Map<String, dynamic>.from(raw);
    }
    return null;
  }

  void _ensureDefaultFolder() {
    const wishlistColor = Color(0xFFFFC44D);
    const wishlistIcon = Icons.shopping_bag_rounded;
    final wishlistIndex =
        folders.indexWhere((folder) => folder.isSystemWishlist);
    if (wishlistIndex == -1) {
      folders.add(
        const FolderItem(
          id: kSystemWishlistFolderId,
          name: '위시리스트',
          icon: wishlistIcon,
          color: wishlistColor,
          isGroup: false,
          parentId: null,
          isSystemWishlist: true,
        ),
      );
    } else {
      // Force the system wishlist appearance on every load (migrate existing
      // accounts that had the old pink/heart visual).
      final existing = folders[wishlistIndex];
      if (existing.color != wishlistColor ||
          existing.icon.codePoint != wishlistIcon.codePoint ||
          existing.name != '위시리스트') {
        folders[wishlistIndex] = existing.copyWith(
          name: '위시리스트',
          icon: wishlistIcon,
          color: wishlistColor,
        );
      }
    }
    if (folders.where((folder) => !folder.isSystemWishlist).isEmpty) {
      folders.add(
        const FolderItem(
          id: 'default-folder',
          name: '기본 폴더',
          icon: Icons.folder_rounded,
          color: Color(0xFF87CEEB),
          isGroup: false,
          parentId: null,
        ),
      );
    }
  }

  Future<void> _saveAccountData() async {
    try {
      final lastNickname = _bestKnownDeviceNickname;
      final persistedDisplayName =
          adminMode && localAdminOverrideEnabled && lastNickname != null
              ? lastNickname
              : displayName;
      final persistedTag =
          adminMode && localAdminOverrideEnabled && lastNickname != null
              ? '@$lastNickname'
              : tag;
      if (lastNickname != null) {
        await _storageBox?.put(_lastDeviceNicknameKey, lastNickname);
      }
      final payload = <String, dynamic>{
        'savedAt': DateTime.now().toIso8601String(),
        'accountKey': _currentStorageAccountKey,
        'accountId': accountId,
        'authProvider': authProvider.name,
        'driveBackupEnabled': driveBackupEnabled,
        'profile': <String, dynamic>{
          'displayName': persistedDisplayName,
          'lastDeviceNickname': lastNickname,
          'tag': persistedTag,
          'profileImageBytes': profileImageBytes,
          'profileImageUrl': profileImageUrl,
          'avatar': <String, dynamic>{
            'bodyType': avatarBodyType,
            'backgroundType': avatarBackgroundType,
            'hairStyle': avatarHairStyle,
            'hairColorIndex': avatarHairColorIndex,
            'accentColorIndex': avatarAccentColorIndex,
            'outfitColorIndex': avatarOutfitColorIndex,
            'skinToneIndex': avatarSkinToneIndex,
            'hasHat': avatarHasHat,
            'hasCape': avatarHasCape,
            'hasHandheld': avatarHasHandheld,
            'hasBackRibbon': avatarHasBackRibbon,
          },
        },
        'folders': folders.map((item) => item.toJson()).toList(),
        'goodsItems': goodsItems.map((item) => item.toJson()).toList(),
        'calendarEvents': calendarEvents.map((item) => item.toJson()).toList(),
        'inquiries': inquiries.map((item) => item.toJson()).toList(),
        'equippedBadgeIds': [...equippedBadgeIds],
        'purchaseRecords': <Map<String, dynamic>>[],
        'permissionFlags': <String, dynamic>{
          'canEditProfile': canEditProfile,
          'pushEnabled': pushEnabled,
          'darkModeEnabled': darkModeEnabled,
        },
      };
      await _writeStoredAccountPayload(payload);
    } catch (_) {}
  }

  Future<void> _loadAccountData() async {
    try {
      final json = await _readStoredAccountPayload();
      if (json == null) {
        folders.clear();
        goodsItems.clear();
        calendarEvents.clear();
        inquiries.clear();
        equippedBadgeIds.clear();
        _ensureDefaultFolder();
        return;
      }

      final loadedFolders = ((json['folders'] as List<dynamic>?) ?? const [])
          .map((item) =>
              FolderItem.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
      final loadedGoods = ((json['goodsItems'] as List<dynamic>?) ?? const [])
          .map((item) =>
              GoodsItem.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
      final loadedEvents =
          ((json['calendarEvents'] as List<dynamic>?) ?? const [])
              .map((item) => CalendarEventItem.fromJson(
                  Map<String, dynamic>.from(item as Map)))
              .toList();
      final loadedInquiries =
          ((json['inquiries'] as List<dynamic>?) ?? const [])
              .map((item) => SupportInquiryItem.fromJson(
                  Map<String, dynamic>.from(item as Map)))
              .toList();
      final loadedBadges =
          ((json['equippedBadgeIds'] as List<dynamic>?) ?? const [])
              .map((item) => item.toString())
              .toList();
      final profile =
          Map<String, dynamic>.from(json['profile'] as Map? ?? const {});
      final savedLastNickname =
          (profile['lastDeviceNickname'] as String?)?.trim() ?? '';
      final avatar =
          Map<String, dynamic>.from(profile['avatar'] as Map? ?? const {});
      final preferServerProfile = authProvider == AuthProviderType.local &&
          (serverAccessToken?.trim().isNotEmpty ?? false);

      folders
        ..clear()
        ..addAll(loadedFolders);
      goodsItems
        ..clear()
        ..addAll(loadedGoods);
      calendarEvents
        ..clear()
        ..addAll(loadedEvents);
      inquiries
        ..clear()
        ..addAll(loadedInquiries);
      equippedBadgeIds
        ..clear()
        ..addAll(loadedBadges);
      final savedProfileImageBytes = profile['profileImageBytes'];
      if (savedProfileImageBytes is Uint8List) {
        profileImageBytes = savedProfileImageBytes;
        profileImageUrl = null;
      } else if (!preferServerProfile) {
        final savedProfileImageUrl = profile['profileImageUrl'] as String?;
        if ((savedProfileImageUrl ?? '').isNotEmpty) {
          profileImageUrl = savedProfileImageUrl;
        }
      }

      if (!preferServerProfile) {
        displayName =
            (profile['displayName'] as String?)?.trim().isNotEmpty == true
                ? (profile['displayName'] as String).trim()
                : displayName;
        tag = (profile['tag'] as String?)?.trim().isNotEmpty == true
            ? (profile['tag'] as String).trim()
            : tag;
      }
      if (savedLastNickname.isNotEmpty) {
        await _storageBox?.put(_lastDeviceNicknameKey, savedLastNickname);
      }
      avatarBodyType = avatar['bodyType'] as int? ?? avatarBodyType;
      avatarBackgroundType =
          avatar['backgroundType'] as int? ?? avatarBackgroundType;
      avatarHairStyle = avatar['hairStyle'] as int? ?? avatarHairStyle;
      avatarHairColorIndex =
          avatar['hairColorIndex'] as int? ?? avatarHairColorIndex;
      avatarAccentColorIndex =
          avatar['accentColorIndex'] as int? ?? avatarAccentColorIndex;
      avatarOutfitColorIndex =
          avatar['outfitColorIndex'] as int? ?? avatarOutfitColorIndex;
      avatarSkinToneIndex =
          avatar['skinToneIndex'] as int? ?? avatarSkinToneIndex;
      avatarHasHat = avatar['hasHat'] as bool? ?? avatarHasHat;
      avatarHasCape = avatar['hasCape'] as bool? ?? avatarHasCape;
      avatarHasHandheld = avatar['hasHandheld'] as bool? ?? avatarHasHandheld;
      avatarHasBackRibbon =
          avatar['hasBackRibbon'] as bool? ?? avatarHasBackRibbon;

      _ensureDefaultFolder();
    } catch (_) {
      folders.clear();
      goodsItems.clear();
      calendarEvents.clear();
      inquiries.clear();
      equippedBadgeIds.clear();
      _ensureDefaultFolder();
    }
  }

  Future<void> _initGoogleSignIn() async {
    if (!hasRequiredGoogleSignInConfig) {
      googleSignInAvailable = false;
      googleSignInError = 'missing_web_client_id';
      notifyListeners();
      return;
    }
    try {
      googleSignInAvailable = true;
      googleSignInError = null;
      final account = await _googleSignIn.signInSilently();
      // Only auto-restore a Google session if that email is linked to a
      // local account. Standalone Google login is no longer allowed —
      // users sign up with an ID first, then link Google in settings.
      final linked = account == null
          ? null
          : _findLocalAccountByGoogleEmail(account.email);
      if (account != null && linked != null) {
        await _signInAsLinkedLocal(account, linked);
      } else {
        if (account != null) {
          try {
            await _googleSignIn.signOut();
          } catch (_) {}
        }
        notifyListeners();
      }
    } catch (error) {
      googleSignInAvailable = true;
      googleSignInError = error.toString();
      notifyListeners();
    }
  }

  bool get canEditProfile => isLoggedIn;

  bool get isAdminSession {
    return adminMode;
  }

  String get currentDisplayName {
    if (adminMode && localAdminOverrideEnabled) {
      return _reservedAdminNickname;
    }
    return displayName;
  }

  String get currentTag {
    if (adminMode && localAdminOverrideEnabled) {
      return '@admin';
    }
    return tag;
  }

  bool containsReservedNicknameTerm(String value) {
    final trimmed = value.trim();
    if (trimmed.isEmpty) return false;
    return _reservedNicknameTerms.any(trimmed.contains);
  }

  String? get configuredNickname {
    final value = (_storageBox?.get(_deviceNicknameKey) as String?)?.trim();
    if (value == null || value.isEmpty) return null;
    return value;
  }

  String? get lastKnownDeviceNickname {
    final current = configuredNickname;
    if (current != null && current.isNotEmpty) return current;
    final stored =
        (_storageBox?.get(_lastDeviceNicknameKey) as String?)?.trim();
    if (stored != null && stored.isNotEmpty) return stored;
    final localDisplay = displayName.trim();
    if (authProvider == AuthProviderType.local &&
        localDisplay.isNotEmpty &&
        localDisplay != 'Guest') {
      return localDisplay;
    }
    return null;
  }

  String? get _bestKnownDeviceNickname {
    final value = lastKnownDeviceNickname?.trim();
    if (value == null || value.isEmpty || value == 'Guest') return null;
    return value;
  }

  bool get hasReusableDeviceData {
    final customFolders = folders.any(
      (folder) => !folder.isSystemWishlist && folder.id != 'default-folder',
    );
    return goodsItems.isNotEmpty ||
        calendarEvents.isNotEmpty ||
        inquiries.isNotEmpty ||
        equippedBadgeIds.isNotEmpty ||
        customFolders ||
        profileImageBytes != null ||
        (profileImageUrl?.trim().isNotEmpty ?? false) ||
        avatarBodyType >= 0 ||
        avatarBackgroundType >= 0 ||
        avatarHairStyle >= 0 ||
        avatarHairColorIndex >= 0 ||
        avatarAccentColorIndex >= 0 ||
        avatarOutfitColorIndex >= 0 ||
        avatarSkinToneIndex >= 0 ||
        avatarHasHat ||
        avatarHasCape ||
        avatarHasHandheld ||
        avatarHasBackRibbon;
  }

  bool get canOpenOfflineArchive {
    return !isLoggedIn &&
        !inGuestSession &&
        !adminMode &&
        hasReusableDeviceData;
  }

  String get stableAuthorId => 'device:$deviceId';

  int get totalGoodsCount {
    final wishlistIds =
        folders.where((f) => f.isSystemWishlist).map((f) => f.id).toSet();
    return goodsItems.fold(
      0,
      (sum, item) {
        if (item.isWishlistItem) return sum;
        if (wishlistIds.contains(item.folderId)) return sum;
        return sum + item.quantity;
      },
    );
  }

  /// Total spend converted into the currently chosen `displayCurrency`,
  /// using fresh daily-refreshed FX rates when available
  /// (`ExchangeRateService`) or the static fallback table on
  /// `Currency.rateFromKrw` if the network refresh hasn't completed yet.
  /// Wishlist items are excluded.
  int get totalPaidAmount {
    final wishlistIds =
        folders.where((f) => f.isSystemWishlist).map((f) => f.id).toSet();
    double sum = 0;
    for (final item in goodsItems) {
      if (item.isWishlistItem) continue;
      if (wishlistIds.contains(item.folderId)) continue;
      final unit = item.paidPrice ?? 0;
      if (unit == 0) continue;
      final converted = ExchangeRateService.instance.convert(
        amount: unit,
        fromCode: item.priceCurrencyCode,
        toCode: displayCurrency.code,
        staticRateFromKrw: _staticRateFromKrw,
      );
      sum += converted * item.quantity;
    }
    return sum.round();
  }

  static double _staticRateFromKrw(String code) {
    final currency = Currency.values.firstWhere(
      (c) => c.code == code,
      orElse: () => Currency.krw,
    );
    return currency.rateFromKrw;
  }

  Currency currencyFromCode(String code) {
    return Currency.values.firstWhere(
      (c) => c.code == code,
      orElse: () => Currency.krw,
    );
  }

  String get authLabel {
    switch (authProvider) {
      case AuthProviderType.guest:
        return '게스트';
      case AuthProviderType.local:
        return '일반 계정';
      case AuthProviderType.google:
        return '구글 계정';
    }
  }

  String get backupStatusLabel {
    if (!isLoggedIn) {
      return '로그인 후 내 보관함 상태를 확인할 수 있습니다.';
    }
    if (authProvider == AuthProviderType.google) {
      return '구글 계정은 빠른 로그인 연결용으로만 사용됩니다.';
    }
    return '일반 계정은 아이디와 비밀번호로 내 굿즈 보관함을 불러옵니다.';
  }

  String get nextDefaultTag => '@deokive$_signupSequence';

  bool get supportsGoogleSignIn => kIsWeb;

  bool get hasRequiredGoogleSignInConfig {
    return (GoogleAuthConfig.webClientId ?? '').trim().isNotEmpty;
  }

  String get googleSignInStatusText {
    if (!supportsGoogleSignIn) {
      return '현재 플랫폼에서는 구글 로그인을 지원하지 않습니다.';
    }
    if (!googleSignInAvailable) {
      return '구글 로그인 설정이 아직 완료되지 않았습니다.';
    }
    return '구글 로그인은 같은 계정에 빠르게 다시 들어오기 위한 연결 기능입니다.';
  }

  String get googleSignInMessage {
    if (!supportsGoogleSignIn) {
      return '현재 플랫폼에서는 구글 로그인을 지원하지 않습니다.';
    }
    if (googleSignInError != null && googleSignInError!.isNotEmpty) {
      return '구글 로그인 설정이 완료되지 않았거나 인증에 실패했습니다. ';
      'Android는 패키지명과 SHA-1, iOS는 Client ID와 URL Scheme 설정이 필요합니다.';
    }
    if (!googleSignInAvailable) {
      return '구글 로그인 초기화 중입니다.';
    }
    return '구글 계정으로 로그인하면 구글 닉네임과 프로필 사진을 기본값으로 가져옵니다.';
  }

  String? get googleSignInDebugError {
    final value = googleSignInError?.trim();
    if (value == null || value.isEmpty) return null;
    return value;
  }

  String get todayStamp {
    final now = DateTime.now();
    final month = now.month.toString().padLeft(2, '0');
    final day = now.day.toString().padLeft(2, '0');
    return '${now.year}-$month-$day';
  }

  bool isValidTagText(String value) {
    return RegExp(r'^[A-Za-z0-9]+$').hasMatch(value);
  }

  bool isStrongPassword(String value) {
    if (value.length < 8) return false;
    final hasLetter = RegExp(r'[A-Za-z]').hasMatch(value);
    final hasDigit = RegExp(r'\d').hasMatch(value);
    return hasLetter && hasDigit;
  }

  String _allocateTag() {
    final value = '@deokive$_signupSequence';
    _signupSequence += 1;
    return value;
  }

  bool isValidNickname(String value, {bool allowReservedAdmin = false}) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || trimmed.length > 20) return false;
    if (!allowReservedAdmin && containsReservedNicknameTerm(trimmed)) {
      return false;
    }
    return RegExp(r'^[A-Za-z0-9가-힣_]+$').hasMatch(trimmed);
  }

  Future<bool> claimDeviceNickname(
    String nickname, {
    bool discardExistingData = false,
    bool allowReservedAdmin = false,
  }) async {
    await _ensureStorageReady();
    final trimmed = nickname.trim();
    if (!isValidNickname(trimmed, allowReservedAdmin: allowReservedAdmin)) {
      return false;
    }
    if (ServerConfig.personalDataLocalOnly) {
      await _applyLocalDeviceNickname(
        trimmed,
        discardExistingData: discardExistingData,
      );
      return true;
    }
    final hasServer = !ServerConfig.personalDataLocalOnly &&
        await ServerConfig.ensureResolved();
    if (!hasServer) return false;
    final api = DeviceProfileApiService();
    try {
      final claimed = await api.claimNickname(
        deviceId: deviceId,
        nickname: trimmed,
      );
      isLoggedIn = true;
      authProvider = AuthProviderType.local;
      displayName = claimed;
      accountId = deviceId;
      tag = '@$claimed';
      if (discardExistingData) {
        _resetDeviceScopedDataInMemory();
      }
      await _storageBox?.put(_deviceNicknameKey, claimed);
      await _storageBox?.put(_lastDeviceNicknameKey, claimed);
      await _saveAccountData();
      notifyListeners();
      return true;
    } catch (_) {
      return false;
    } finally {
      _isSyncingBoard = false;
      api.dispose();
    }
  }

  Future<void> _applyLocalDeviceNickname(
    String nickname, {
    bool discardExistingData = false,
  }) async {
    isLoggedIn = true;
    authProvider = AuthProviderType.local;
    displayName = nickname;
    accountId = deviceId;
    tag = '@$nickname';
    serverAccessToken = null;
    profileImageUrl = null;
    driveBackupEnabled = false;
    if (discardExistingData) {
      _resetDeviceScopedDataInMemory();
    }
    await _storageBox?.put(_deviceNicknameKey, nickname);
    await _storageBox?.put(_lastDeviceNicknameKey, nickname);
    await _clearPersistedAuthSession();
    await _saveAccountData();
    notifyListeners();
  }

  Future<bool> startWithAutoNickname({bool discardExistingData = false}) async {
    await _ensureStorageReady();
    if (ServerConfig.personalDataLocalOnly) {
      final reusableNickname = lastKnownDeviceNickname;
      final nickname = !discardExistingData &&
              hasReusableDeviceData &&
              reusableNickname != null &&
              reusableNickname.isNotEmpty
          ? reusableNickname
          : _allocateTag().replaceFirst('@', '');
      await _applyLocalDeviceNickname(
        nickname,
        discardExistingData: discardExistingData,
      );
      return true;
    }
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return false;
    final reusableNickname = lastKnownDeviceNickname;
    if (!discardExistingData &&
        hasReusableDeviceData &&
        reusableNickname != null &&
        reusableNickname.isNotEmpty) {
      final reclaimed = await claimDeviceNickname(reusableNickname);
      if (reclaimed) return true;
    }
    final api = DeviceProfileApiService();
    try {
      final claimed = await api.claimAutoNickname(deviceId: deviceId);
      isLoggedIn = true;
      authProvider = AuthProviderType.local;
      displayName = claimed;
      accountId = deviceId;
      tag = '@$claimed';
      if (discardExistingData) {
        _resetDeviceScopedDataInMemory();
      }
      await _storageBox?.put(_deviceNicknameKey, claimed);
      await _storageBox?.put(_lastDeviceNicknameKey, claimed);
      await _saveAccountData();
      notifyListeners();
      return true;
    } catch (_) {
      return false;
    } finally {
      _isSyncingBoard = false;
      api.dispose();
    }
  }

  void _resetDeviceScopedDataInMemory() {
    folders.clear();
    goodsItems.clear();
    calendarEvents.clear();
    inquiries.clear();
    equippedBadgeIds.clear();
    profileImageBytes = null;
    profileImageUrl = null;
    avatarBodyType = -1;
    avatarBackgroundType = -1;
    avatarHairStyle = -1;
    avatarHairColorIndex = -1;
    avatarAccentColorIndex = -1;
    avatarOutfitColorIndex = -1;
    avatarSkinToneIndex = -1;
    avatarHasHat = false;
    avatarHasCape = false;
    avatarHasHandheld = false;
    avatarHasBackRibbon = false;
    _ensureDefaultFolder();
  }

  Future<void> clearDeviceNicknamePreservingLocalData() async {
    await _ensureStorageReady();
    final nicknameToRemember = _bestKnownDeviceNickname;
    await _saveAccountData();
    await _storageBox?.delete(_deviceNicknameKey);
    if (nicknameToRemember != null) {
      await _storageBox?.put(_lastDeviceNicknameKey, nicknameToRemember);
    }
    isLoggedIn = false;
    inGuestSession = false;
    isGoogleLinked = false;
    driveBackupEnabled = false;
    authProvider = AuthProviderType.guest;
    serverAccessToken = null;
    displayName = 'Guest';
    accountId = 'nickname_required';
    tag = '@guest';
    await _clearPersistedAuthSession();
    notifyListeners();
  }

  void setAppPalette(AppPalette palette) {
    if (appPalette == palette) return;
    appPalette = palette;
    _persistStorageValues();
    notifyListeners();
  }

  void setAppLanguage(AppLanguage language) {
    if (appLanguage == language) return;
    appLanguage = language;
    _persistStorageValues();
    notifyListeners();
  }

  /// Sign in AS a local account that has [account]'s email linked. Both
  /// login methods (ID / Google) resolve to the same local account, so the
  /// canonical authProvider stays `local` (storage key uses the local id),
  /// with isGoogleLinked flagged for UI + Drive backup.
  Future<void> _signInAsLinkedLocal(
    GoogleSignInAccount account,
    Map<String, dynamic> linked,
  ) async {
    await _ensureStorageReady();
    isLoggedIn = true;
    isGoogleLinked = true;
    authProvider = AuthProviderType.local;
    driveBackupEnabled = false;
    displayName = (linked['nickname'] as String?) ?? 'Deokive User';
    accountId = (linked['id'] as String?) ?? account.email;
    tag = (linked['tag'] as String?) ?? _allocateTag();
    profileImageUrl = null;
    serverAccessToken = null;
    final savedImage = linked['profileImageBytes'];
    profileImageBytes = savedImage is Uint8List ? savedImage : null;
    await _persistAuthSession();
    await _loadAccountData();
    notifyListeners();
  }

  Future<bool> signInWithGoogle() async {
    if (!supportsGoogleSignIn) {
      googleSignInAvailable = false;
      googleSignInError = 'unsupported_platform';
      notifyListeners();
      return false;
    }
    if (!hasRequiredGoogleSignInConfig) {
      googleSignInAvailable = false;
      googleSignInError = 'missing_web_client_id';
      notifyListeners();
      return false;
    }
    try {
      googleSignInAvailable = true;
      googleSignInError = null;
      // Force the account chooser to open every time. On some devices the
      // plugin caches the previous signInSilently result and signIn() then
      // resolves instantly to that same account — which looks to the user
      // like the button does nothing.
      try {
        await _googleSignIn.signOut();
      } catch (_) {}
      final account = await _googleSignIn.signIn();
      if (account == null) {
        googleSignInError = 'cancelled';
        notifyListeners();
        return false;
      }
      // If this Google email is linked to a local account, sign in AS that
      // local account so both providers resolve to the same data set. The
      // canonical authProvider stays `local` (storage key derivation uses
      // local id), with isGoogleLinked flagged for UI.
      final linked = _findLocalAccountByGoogleEmail(account.email);
      if (linked != null) {
        await _signInAsLinkedLocal(account, linked);
        return true;
      }
      // Not linked to any local account. We DON'T create a standalone
      // Google account anymore — users must sign up with an ID first, then
      // link Google from settings. Reject with guidance.
      googleSignInError = 'no_linked_account';
      try {
        await _googleSignIn.signOut();
      } catch (_) {}
      notifyListeners();
      return false;
    } catch (error) {
      googleSignInAvailable = true;
      googleSignInError = error.toString();
      notifyListeners();
      return false;
    }
  }

  Map<String, dynamic>? _findLocalAccount(String id) {
    final normalizedId = _normalizeAccountId(id);
    for (final account in _localAccounts) {
      final savedId = (account['id'] as String?) ?? '';
      if (_normalizeAccountId(savedId) == normalizedId) {
        return account;
      }
    }
    return null;
  }

  Map<String, dynamic>? _findLocalAccountByGoogleEmail(String email) {
    final target = email.trim().toLowerCase();
    if (target.isEmpty) return null;
    for (final account in _localAccounts) {
      final linked =
          (account['linkedGoogleEmail'] as String?)?.trim().toLowerCase();
      if (linked != null && linked == target) {
        return account;
      }
    }
    return null;
  }

  /// Email of the Google account currently linked to the signed-in local
  /// account, or null. Only meaningful when [authProvider] is local.
  String? get linkedGoogleEmail {
    if (authProvider != AuthProviderType.local) return null;
    final acc = _findLocalAccount(accountId);
    final raw = acc?['linkedGoogleEmail'];
    if (raw is String && raw.trim().isNotEmpty) return raw.trim();
    return null;
  }

  String? get linkedGoogleEmailMasked {
    final raw = linkedGoogleEmail;
    if (raw == null) return null;
    final atIndex = raw.indexOf('@');
    if (atIndex <= 1) return 'Google account linked';
    final local = raw.substring(0, atIndex);
    final domain = raw.substring(atIndex + 1);
    final maskedLocal = local.length <= 2
        ? '${local[0]}*'
        : '${local[0]}${'*' * (local.length - 2)}${local[local.length - 1]}';
    return '$maskedLocal@$domain';
  }

  /// Trigger the Google sign-in flow and attach the resulting email to the
  /// currently signed-in **local** account. After linking, signing in via
  /// Google with the same email will resolve to this same local account
  /// (so data is shared).
  ///
  /// Returns true on success. Sets [googleSignInError] on failure:
  ///   - `not_local_account` — no local user signed in
  ///   - `already_linked_elsewhere` — that Google email is linked to a
  ///     different local account
  ///   - `cancelled` — user cancelled the chooser
  ///   - other strings — propagated platform errors
  Future<bool> linkGoogleToCurrentLocalAccount() async {
    if (authProvider != AuthProviderType.local) {
      googleSignInError = 'not_local_account';
      notifyListeners();
      return false;
    }
    if (!supportsGoogleSignIn) {
      googleSignInAvailable = false;
      googleSignInError = 'unsupported_platform';
      notifyListeners();
      return false;
    }
    if (!hasRequiredGoogleSignInConfig) {
      googleSignInAvailable = false;
      googleSignInError = 'missing_web_client_id';
      notifyListeners();
      return false;
    }
    try {
      googleSignInAvailable = true;
      googleSignInError = null;
      // Clear any stale Google session so the account chooser always shows.
      // Without this, on some devices `signIn()` returns the previously-
      // silently-signed-in account immediately, which looks like the dialog
      // never opened.
      try {
        await _googleSignIn.signOut();
      } catch (_) {}
      final account = await _googleSignIn.signIn();
      if (account == null) {
        googleSignInError = 'cancelled';
        notifyListeners();
        return false;
      }
      final email = account.email;
      final other = _findLocalAccountByGoogleEmail(email);
      if (other != null && other['id'] != accountId) {
        googleSignInError = 'already_linked_elsewhere';
        try {
          await _googleSignIn.signOut();
        } catch (_) {}
        notifyListeners();
        return false;
      }
      final myAccount = _findLocalAccount(accountId);
      if (myAccount == null) {
        googleSignInError = 'local_account_missing';
        notifyListeners();
        return false;
      }
      myAccount['linkedGoogleEmail'] = email;
      profileImageUrl = null;
      isGoogleLinked = true;
      driveBackupEnabled = false;
      await _persistStorageValues();
      await _persistAuthSession();
      notifyListeners();
      return true;
    } catch (error) {
      googleSignInAvailable = true;
      googleSignInError = error.toString();
      notifyListeners();
      return false;
    }
  }

  /// Detach the Google account from the currently signed-in local account.
  /// Local credentials (id/password) keep working as before.
  Future<void> unlinkGoogleFromCurrentLocalAccount() async {
    if (authProvider != AuthProviderType.local) return;
    final acc = _findLocalAccount(accountId);
    if (acc == null) return;
    acc.remove('linkedGoogleEmail');
    isGoogleLinked = false;
    driveBackupEnabled = false;
    profileImageUrl = null;
    try {
      await _googleSignIn.signOut();
    } catch (_) {}
    await _persistStorageValues();
    await _persistAuthSession();
    notifyListeners();
  }

  Future<bool> signInLocal({
    required String id,
    required String password,
  }) async {
    await _ensureStorageReady();
    final normalizedId = _normalizeAccountId(id);
    final hasServer = await ServerConfig.ensureResolved();
    if (hasServer) {
      final api = AuthApiService();
      try {
        final session = await api.login(
          loginId: normalizedId,
          password: password,
        );
        final profile = await api.getMe(session.accessToken);
        _applyServerLocalSession(profile, session.accessToken);
        profileImageBytes = null;
        await _persistAuthSession();
        await _loadAccountData();
        notifyListeners();
        return true;
      } catch (_) {
        // Fall through to the legacy local-account path so older device-only
        // accounts remain accessible during the migration to server auth.
      } finally {
        api.dispose();
      }
    }

    final account = _findLocalAccount(normalizedId);
    if (account == null) return false;
    if (account['password'] != password) return false;

    final linkedEmail = (account['linkedGoogleEmail'] as String?)?.trim();
    final hasGoogleLink = linkedEmail != null && linkedEmail.isNotEmpty;

    isLoggedIn = true;
    isGoogleLinked = hasGoogleLink;
    authProvider = AuthProviderType.local;
    driveBackupEnabled = hasGoogleLink;
    displayName = (account['nickname'] as String?) ?? 'Deokive User';
    accountId = (account['id'] as String?) ?? normalizedId;
    tag = (account['tag'] as String?) ?? _allocateTag();
    profileImageUrl = null;
    serverAccessToken = null;

    final savedImage = account['profileImageBytes'];
    profileImageBytes = savedImage is Uint8List ? savedImage : null;

    await _persistAuthSession();
    await _loadAccountData();
    notifyListeners();
    return true;
  }

  Future<bool> signUpLocal({
    required String nickname,
    required String id,
    required String password,
  }) async {
    await _ensureStorageReady();
    final normalizedId = _normalizeAccountId(id);
    final hasServer = await ServerConfig.ensureResolved();
    if (hasServer) {
      final api = AuthApiService();
      try {
        final session = await api.signUp(
          loginId: normalizedId,
          password: password,
          nickname: nickname.trim(),
        );
        final profile = await api.getMe(session.accessToken);
        _applyServerLocalSession(profile, session.accessToken);
        profileImageBytes = null;
        avatarBodyType = -1;
        avatarBackgroundType = -1;
        avatarHairStyle = -1;
        avatarHairColorIndex = -1;
        avatarAccentColorIndex = -1;
        avatarOutfitColorIndex = -1;
        avatarSkinToneIndex = -1;
        avatarHasHat = false;
        avatarHasCape = false;
        avatarHasHandheld = false;
        avatarHasBackRibbon = false;
        await _persistAuthSession();
        await _saveAccountData();
        notifyListeners();
        return true;
      } catch (_) {
        return false;
      } finally {
        api.dispose();
      }
    }

    if (_findLocalAccount(normalizedId) != null) {
      return false;
    }

    final allocatedTag = _allocateTag();
    final account = <String, dynamic>{
      'nickname': nickname.trim(),
      'id': normalizedId,
      'password': password,
      'tag': allocatedTag,
      'profileImageBytes': null,
    };

    _localAccounts.add(account);
    await _persistStorageValues();

    isLoggedIn = true;
    isGoogleLinked = false;
    authProvider = AuthProviderType.local;
    driveBackupEnabled = false;
    displayName = nickname.trim();
    accountId = normalizedId;
    tag = allocatedTag;
    profileImageBytes = null;
    profileImageUrl = null;
    serverAccessToken = null;
    avatarBodyType = -1;
    avatarBackgroundType = -1;
    avatarHairStyle = -1;
    avatarHairColorIndex = -1;
    avatarAccentColorIndex = -1;
    avatarOutfitColorIndex = -1;
    avatarSkinToneIndex = -1;
    avatarHasHat = false;
    avatarHasCape = false;
    avatarHasHandheld = false;
    avatarHasBackRibbon = false;
    await _persistAuthSession();
    await _saveAccountData();
    notifyListeners();
    return true;
  }

  /// Enter the app as a guest — can view content but cannot create.
  void enterGuestSession() {
    inGuestSession = true;
    notifyListeners();
  }

  void setAdminMode(bool value) {
    adminMode = false;
    _persistStorageValues();
    notifyListeners();
  }

  // ── Board posts ─────────────────────────────────────────────────────
  void _loadBoardPosts() {
    final raw = _storageBox?.get(_boardPostsKey) as List<dynamic>?;
    boardPosts.clear();
    if (raw == null || raw.isEmpty) {
      // First launch — seed with bundled defaults.
      boardPosts.addAll(kSeedBoardPosts);
      _persistBoardPosts();
    } else {
      for (final item in raw) {
        try {
          boardPosts
              .add(BoardPost.fromJson(Map<String, dynamic>.from(item as Map)));
        } catch (_) {}
      }
    }
    _pruneLegacySeedNotices();
    _runViewCountResetMigration();
  }

  void _pruneLegacySeedNotices() {
    const legacyIds = {'notice_001', 'notice_002', 'notice_003'};
    final before = boardPosts.length;
    boardPosts.removeWhere((post) => legacyIds.contains(post.id));
    if (before != boardPosts.length) {
      _persistBoardPosts();
    }
  }

  /// One-time migration: zero out every existing post's viewCount. New
  /// counts only grow from real taps from this point on.
  void _runViewCountResetMigration() {
    if (_storageBox == null) return;
    final done = _storageBox!
            .get(_viewCountResetVersionKey, defaultValue: false) as bool? ??
        false;
    if (done) return;
    var changed = false;
    for (var i = 0; i < boardPosts.length; i++) {
      if (boardPosts[i].viewCount != 0) {
        boardPosts[i] = boardPosts[i].copyWith(viewCount: 0);
        changed = true;
      }
    }
    if (changed) _persistBoardPosts();
    _storageBox!.put(_viewCountResetVersionKey, true);
  }

  /// True when the app is pointed at a deployed board server.
  bool get boardServerEnabled => ServerConfig.enabled;
  bool get readOnlyPublicSite => ServerConfig.staticSite;

  List<GoodsCatalogEntry> get curatedCatalogEntries {
    if (_remoteCatalogEntries.isNotEmpty) return _remoteCatalogEntries;
    return kFullCatalog;
  }

  List<String> get curatedCatalogCategories {
    final set = <String>{};
    for (final entry in curatedCatalogEntries) {
      final value = entry.normalizedCategory.trim();
      if (value.isNotEmpty) set.add(value);
    }
    final list = set.toList()..sort();
    return list;
  }

  List<String> get curatedCatalogCharacterNames {
    final set = <String>{};
    for (final entry in curatedCatalogEntries) {
      final value = entry.characterName.trim();
      if (value.isNotEmpty) set.add(value);
    }
    final list = set.toList()..sort();
    return list;
  }

  List<String> get curatedCatalogSeriesNames {
    final set = <String>{};
    for (final entry in curatedCatalogEntries) {
      final value = entry.seriesName?.trim() ?? '';
      if (value.isNotEmpty) set.add(value);
    }
    final list = set.toList()..sort();
    return list;
  }

  List<String> get curatedCatalogAffiliations {
    final set = <String>{};
    for (final entry in curatedCatalogEntries) {
      final value = entry.affiliation.trim();
      if (value.isNotEmpty) set.add(value);
    }
    final list = set.toList()..sort();
    return list;
  }

  Future<int> syncCatalogFromServer({bool force = false}) async {
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return 0;
    if (isSyncingCatalog) return _remoteCatalogEntries.length;

    isSyncingCatalog = true;
    catalogSyncError = null;
    notifyListeners();
    try {
      final meta = await _catalogApi.fetchMeta();
      if (!force &&
          _remoteCatalogEntries.isNotEmpty &&
          meta.totalCount == _remoteCatalogEntries.length &&
          meta.latestUpdatedAt != null &&
          meta.latestUpdatedAt == _lastCatalogUpdatedAt) {
        catalogSyncedAt = DateTime.now();
        return _remoteCatalogEntries.length;
      }
      final items = await _catalogApi.fetchAll();
      _remoteCatalogEntries = items;
      _lastCatalogUpdatedAt = meta.latestUpdatedAt;
      catalogSyncedAt = DateTime.now();
      catalogSyncError = null;
      return items.length;
    } catch (e) {
      catalogSyncError = '$e';
      return -1;
    } finally {
      isSyncingCatalog = false;
      notifyListeners();
    }
  }

  /// Pull the shared board from the server and replace the local list with
  /// it. When the server is unreachable the local (cached) board is kept, so
  /// the board still renders offline. Returns the fetched count, or -1 on
  /// failure (kept local).
  Future<int> syncBoardFromServer({bool force = false}) async {
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return 0;
    if (_isSyncingBoard) return boardPosts.length;
    _isSyncingBoard = true;
    final api = BoardApiService();
    try {
      final meta = await api.fetchMeta(serverAccessToken);
      if (!force &&
          meta.latestUpdatedAt != null &&
          meta.latestUpdatedAt == _lastBoardUpdatedAt) {
        return boardPosts.length;
      }
      final serverPosts = await api.fetchPosts(limit: 200);
      var mergedPosts = List<BoardPost>.from(serverPosts);
      if (adminMode) {
        try {
          final pendingPosts = await api.fetchPending(serverAccessToken);
          final byId = <String, BoardPost>{};
          for (final post in [...serverPosts, ...pendingPosts]) {
            byId[post.id] = post;
          }
          mergedPosts = byId.values.toList()
            ..sort((a, b) => b.date.compareTo(a.date));
        } catch (_) {
          // Public posts stay visible even if pending-admin fetch fails.
        }
      }
      final existingComments =
          Map<String, List<BoardComment>>.from(postComments);
      boardPosts
        ..clear()
        ..addAll(mergedPosts);
      postLikeCounts
        ..clear()
        ..addEntries(
          mergedPosts.map((post) => MapEntry(post.id, post.likeCount)),
        );
      postComments
        ..clear()
        ..addEntries(
          mergedPosts
              .where((post) => existingComments.containsKey(post.id))
              .map((post) => MapEntry(post.id, existingComments[post.id]!)),
        );
      await _refreshOwnedPostCommentsFromServer(api, mergedPosts);
      _lastBoardUpdatedAt = meta.latestUpdatedAt;
      await _persistBoardPosts();
      await _persistComments();
      notifyListeners();
      // Translate the freshly-synced posts into the current language.
      unawaited(_backfillBoardTranslations());
      if (kDebugMode) {
        debugPrint('📡 board synced from server: ${serverPosts.length} posts');
      }
      return mergedPosts.length;
    } catch (e) {
      debugPrint('📡 board server sync failed (keeping local): $e');
      return -1;
    } finally {
      api.dispose();
    }
  }

  Future<void> _persistBoardPosts() async {
    if (_storageBox == null) return;
    await _storageBox!.put(
      _boardPostsKey,
      boardPosts.map((p) => p.toJson()).toList(growable: false),
    );
  }

  void addBoardPost(BoardPost post) {
    if (readOnlyPublicSite) return;
    boardPosts.insert(0, post);
    _persistBoardPosts();
    notifyListeners();
    unawaited(_publishBoardPostToServer(post));
    // Translate every new post (admin notice / info-bot / general user
    // post) into the current app language so the board list / detail
    // screens are consistent regardless of who authored it.
    unawaited(translateBoardPost(post, appLanguage.translationCode));
  }

  void updateBoardPost(BoardPost post) {
    if (readOnlyPublicSite) return;
    final idx = boardPosts.indexWhere((p) => p.id == post.id);
    if (idx < 0) return;
    boardPosts[idx] = post;
    // Invalidate any cached translation for this post — admin edits would
    // otherwise be hidden behind the stale auto-translation produced at
    // info-bot refresh time.
    if (postTranslations.remove(post.id) != null) {
      _persistPostTranslations();
    }
    _persistBoardPosts();
    notifyListeners();
    // Re-translate against the new content. translateBoardPost handles the
    // in-flight lock and updates the cache + notifyListeners when done.
    unawaited(translateBoardPost(post, appLanguage.translationCode));
    unawaited(_updateBoardPostOnServer(post));
  }

  void deleteBoardPost(String id) {
    if (readOnlyPublicSite) return;
    boardPosts.removeWhere((p) => p.id == id);
    _persistBoardPosts();
    if (postTranslations.remove(id) != null) {
      _persistPostTranslations();
    }
    notifyListeners();
    unawaited(_deleteBoardPostFromServer(id));
  }

  void incrementBoardPostView(String id) {
    if (readOnlyPublicSite) return;
    unawaited(_syncBoardPostViewToServer(id));
  }

  /// Posts visible to everyone (approved). Info-bot posts pending admin
  /// review are excluded.
  List<BoardPost> get visibleBoardPosts =>
      boardPosts.where((p) => p.approved).toList();

  /// Posts awaiting admin approval (info-bot fetches). Newest first.
  List<BoardPost> get pendingBoardPosts {
    final out = boardPosts.where((p) => !p.approved).toList()
      ..sort((a, b) => b.date.compareTo(a.date));
    return out;
  }

  int get pendingBoardPostCount => boardPosts.where((p) => !p.approved).length;

  /// Approve a pending post so it becomes publicly visible.
  void approveBoardPost(String id) {
    if (readOnlyPublicSite) return;
    final idx = boardPosts.indexWhere((p) => p.id == id);
    if (idx < 0) return;
    boardPosts[idx] = boardPosts[idx].copyWith(approved: true);
    _persistBoardPosts();
    notifyListeners();
    unawaited(_approveBoardPostOnServer(id));
  }

  /// Approve every pending post in one shot.
  void approveAllPendingPosts() {
    if (readOnlyPublicSite) return;
    var changed = false;
    for (var i = 0; i < boardPosts.length; i++) {
      if (!boardPosts[i].approved) {
        boardPosts[i] = boardPosts[i].copyWith(approved: true);
        changed = true;
      }
    }
    if (changed) {
      _persistBoardPosts();
      notifyListeners();
      unawaited(_approveAllPendingPostsOnServer());
    }
  }

  void deleteAllBoardPosts() {
    if (readOnlyPublicSite) return;
    final ids = boardPosts.map((post) => post.id).toList(growable: false);
    boardPosts.clear();
    postComments.clear();
    _persistBoardPosts();
    _persistComments();
    notifyListeners();
    unawaited(_deleteAllBoardPostsFromServer(ids));
  }

  // ── Likes ────────────────────────────────────────────────────────────
  static const _likedPostsKey = 'board_liked_posts';
  static const _bookmarkedPostsKey = 'board_bookmarked_posts';
  static const _postLikeCountsKey = 'board_like_counts';
  static const _postCommentsKey = 'board_comments';

  bool isPostLiked(String postId) => likedPostIds.contains(postId);

  int likeCountFor(String postId) => postLikeCounts[postId] ?? 0;

  Future<void> togglePostLike(String postId) async {
    if (readOnlyPublicSite) return;
    if (ServerConfig.personalDataLocalOnly) {
      _togglePostLikeLocally(postId);
      return;
    }
    final serverId = _serverNumericId(postId);
    final hasServer = await ServerConfig.ensureResolved();
    if (serverId == null || !hasServer) {
      _togglePostLikeLocally(postId);
      return;
    }
    final api = BoardApiService();
    try {
      final result =
          await api.toggleLike(serverAccessToken, '$serverId', deviceId);
      if (result.liked) {
        likedPostIds.add(postId);
      } else {
        likedPostIds.remove(postId);
      }
      postLikeCounts[postId] = result.likeCount;
      final idx = boardPosts.indexWhere((post) => post.id == postId);
      if (idx >= 0) {
        boardPosts[idx] = boardPosts[idx].copyWith(likeCount: result.likeCount);
      }
      _storageBox?.put(_likedPostsKey, likedPostIds.toList());
      _storageBox?.put(
        _postLikeCountsKey,
        Map<String, int>.from(postLikeCounts),
      );
      await _persistBoardPosts();
      notifyListeners();
    } catch (_) {
      _togglePostLikeLocally(postId);
    } finally {
      api.dispose();
    }
  }

  void _togglePostLikeLocally(String postId) {
    if (likedPostIds.contains(postId)) {
      likedPostIds.remove(postId);
      postLikeCounts[postId] =
          ((postLikeCounts[postId] ?? 1) - 1).clamp(0, 1 << 31);
    } else {
      likedPostIds.add(postId);
      postLikeCounts[postId] = (postLikeCounts[postId] ?? 0) + 1;
    }
    _storageBox?.put(_likedPostsKey, likedPostIds.toList());
    _storageBox?.put(
      _postLikeCountsKey,
      Map<String, int>.from(postLikeCounts),
    );
    notifyListeners();
  }

  // ── Bookmarks ────────────────────────────────────────────────────────
  bool isPostBookmarked(String postId) => bookmarkedPostIds.contains(postId);

  void togglePostBookmark(String postId) {
    if (bookmarkedPostIds.contains(postId)) {
      bookmarkedPostIds.remove(postId);
    } else {
      bookmarkedPostIds.add(postId);
    }
    _storageBox?.put(_bookmarkedPostsKey, bookmarkedPostIds.toList());
    notifyListeners();
  }

  List<BoardPost> get bookmarkedPosts =>
      boardPosts.where((p) => bookmarkedPostIds.contains(p.id)).toList();

  // ── Comments ─────────────────────────────────────────────────────────
  List<BoardComment> commentsFor(String postId) =>
      List.unmodifiable(postComments[postId] ?? const []);

  int commentCountFor(String postId) {
    final localCount = postComments[postId]?.length;
    if (localCount != null) return localCount;
    final post = boardPosts.cast<BoardPost?>().firstWhere(
          (item) => item?.id == postId,
          orElse: () => null,
        );
    return post?.commentCount ?? 0;
  }

  void addComment(String postId, String content) {
    if (readOnlyPublicSite) return;
    final trimmed = content.trim();
    if (trimmed.isEmpty) return;
    final author = displayName.trim().isEmpty ? '익명' : displayName.trim();
    final c = BoardComment(
      id: 'c_${DateTime.now().microsecondsSinceEpoch}',
      postId: postId,
      author: author,
      authorId: stableAuthorId,
      content: trimmed,
      date: DateTime.now(),
    );
    postComments.putIfAbsent(postId, () => []).add(c);
    final idx = boardPosts.indexWhere((post) => post.id == postId);
    if (idx >= 0) {
      boardPosts[idx] = boardPosts[idx].copyWith(
        commentCount: (boardPosts[idx].commentCount + 1),
      );
    }
    _persistComments();
    _persistBoardPosts();
    notifyListeners();
    unawaited(_publishCommentToServer(postId, trimmed, author));
  }

  void deleteComment(String postId, String commentId) {
    if (readOnlyPublicSite) return;
    postComments[postId]?.removeWhere((c) => c.id == commentId);
    final idx = boardPosts.indexWhere((post) => post.id == postId);
    if (idx >= 0) {
      final nextCount = postComments[postId]?.length ?? 0;
      boardPosts[idx] = boardPosts[idx].copyWith(commentCount: nextCount);
    }
    _persistComments();
    _persistBoardPosts();
    notifyListeners();
    unawaited(_deleteCommentFromServer(postId, commentId));
  }

  Future<void> _persistComments() async {
    _storageInitFuture ??= _initStorage();
    await _storageInitFuture;
    final serial = <String, dynamic>{};
    postComments.forEach((postId, list) {
      serial[postId] = list.map((c) => c.toJson()).toList();
    });
    await _storageBox?.put(_postCommentsKey, serial);
  }

  int? _serverNumericId(String postId) {
    if (!postId.startsWith('srv_')) return null;
    return int.tryParse(postId.substring(4));
  }

  Future<void> _refreshOwnedPostCommentsFromServer(
    BoardApiService api,
    List<BoardPost> posts,
  ) async {
    final ownPostIds = posts
        .where((post) => post.authorId == stableAuthorId)
        .map((post) => post.id)
        .toSet();
    for (final post in posts) {
      if (!ownPostIds.contains(post.id)) continue;
      final serverId = _serverNumericId(post.id);
      if (serverId == null) continue;
      try {
        final comments = await api.fetchComments('$serverId');
        postComments[post.id] = comments;
        final idx = boardPosts.indexWhere((item) => item.id == post.id);
        if (idx >= 0) {
          boardPosts[idx] = boardPosts[idx].copyWith(
            commentCount: comments.length,
          );
        }
      } catch (_) {
        // Keep cached comments for own posts when refresh fails.
      }
    }
    _collectBoardCommentAlerts(posts);
  }

  Future<void> refreshBoardPostComments(String postId) async {
    final serverId = _serverNumericId(postId);
    if (serverId == null) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      final comments = await api.fetchComments('$serverId');
      postComments[postId] = comments;
      final idx = boardPosts.indexWhere((post) => post.id == postId);
      if (idx >= 0) {
        boardPosts[idx] = boardPosts[idx].copyWith(
          commentCount: comments.length,
        );
      }
      _collectBoardCommentAlerts(boardPosts);
      await _persistComments();
      await _persistBoardPosts();
      notifyListeners();
    } catch (_) {
      // Keep cached comments when the server cannot be reached.
    } finally {
      api.dispose();
    }
  }

  void _collectBoardCommentAlerts(List<BoardPost> posts) {
    if (_storageBox == null) return;
    final ownPostIds = posts
        .where((post) => post.authorId == stableAuthorId)
        .map((post) => post.id)
        .toSet();
    var changed = false;
    for (final post in posts) {
      if (!ownPostIds.contains(post.id)) continue;
      final comments = postComments[post.id] ?? const <BoardComment>[];
      var maxSeen = _seenBoardCommentIdsByPost[post.id];
      if (maxSeen == null) {
        final seedMax = comments
            .map((comment) => int.tryParse(comment.id) ?? 0)
            .fold<int>(0, (max, id) => id > max ? id : max);
        _seenBoardCommentIdsByPost[post.id] = seedMax;
        changed = true;
        continue;
      }
      final newComments = comments.where((comment) {
        final numericId = int.tryParse(comment.id) ?? 0;
        return numericId > maxSeen && comment.authorId != stableAuthorId;
      }).toList()
        ..sort((a, b) => a.date.compareTo(b.date));
      if (newComments.isEmpty) continue;
      for (final comment in newComments) {
        _pendingBoardCommentAlerts.add(
          '${post.title} 글에 ${comment.author}님의 댓글: ${comment.content}',
        );
      }
      final nextMax = comments
          .map((comment) => int.tryParse(comment.id) ?? 0)
          .fold<int>(maxSeen, (max, id) => id > max ? id : max);
      _seenBoardCommentIdsByPost[post.id] = nextMax;
      changed = true;
    }
    if (changed) {
      unawaited(_persistBoardCommentSeenState());
    }
  }

  List<String> takePendingBoardCommentAlerts() {
    if (_pendingBoardCommentAlerts.isEmpty) return const [];
    final out = List<String>.from(_pendingBoardCommentAlerts);
    _pendingBoardCommentAlerts.clear();
    return out;
  }

  Future<void> _publishBoardPostToServer(BoardPost post) async {
    if (ServerConfig.personalDataLocalOnly) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      await api.createPost(
        serverAccessToken,
        post,
        author: displayName.trim().isEmpty ? '익명' : displayName.trim(),
        deviceId: deviceId,
      );
      await syncBoardFromServer();
    } catch (_) {
      // Keep local fallback copy when the server is unavailable.
    } finally {
      api.dispose();
    }
  }

  Future<void> _publishCommentToServer(
    String postId,
    String content,
    String author,
  ) async {
    if (ServerConfig.personalDataLocalOnly) return;
    final serverId = _serverNumericId(postId);
    if (serverId == null) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      await api.addComment(
        serverAccessToken,
        '$serverId',
        content,
        author: author,
        deviceId: deviceId,
      );
      await refreshBoardPostComments(postId);
    } catch (_) {
      // Local comment stays visible even when server write fails.
    } finally {
      api.dispose();
    }
  }

  Future<void> _syncBoardPostViewToServer(String postId) async {
    if (ServerConfig.personalDataLocalOnly) return;
    final serverId = _serverNumericId(postId);
    if (serverId == null) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      final updated = await api.incrementView('$serverId', deviceId: deviceId);
      final idx = boardPosts.indexWhere((post) => post.id == postId);
      if (idx >= 0) {
        boardPosts[idx] = boardPosts[idx].copyWith(
          viewCount: updated.viewCount,
          likeCount: updated.likeCount,
          commentCount: updated.commentCount,
          updatedAt: updated.updatedAt,
        );
        postLikeCounts[postId] = updated.likeCount;
        await _persistBoardPosts();
        notifyListeners();
      }
    } catch (_) {
      // Keep optimistic local count if server sync fails.
    } finally {
      api.dispose();
    }
  }

  Future<void> _deleteCommentFromServer(String postId, String commentId) async {
    if (ServerConfig.personalDataLocalOnly) return;
    final numericCommentId = int.tryParse(commentId);
    if (numericCommentId == null) return;
    final serverId = _serverNumericId(postId);
    if (serverId == null) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      await api.deleteComment(
        serverAccessToken,
        '$numericCommentId',
        deviceId: deviceId,
      );
      await refreshBoardPostComments(postId);
    } catch (_) {
      // Keep local delete visible even if the server call fails.
    } finally {
      api.dispose();
    }
  }

  Future<void> _updateBoardPostOnServer(BoardPost post) async {
    if (ServerConfig.personalDataLocalOnly) return;
    final serverId = _serverNumericId(post.id);
    if (serverId == null) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      await api.updatePost(serverAccessToken, '$serverId', post);
      await syncBoardFromServer();
    } catch (_) {
      // Keep local edit visible even when the server update fails.
    } finally {
      api.dispose();
    }
  }

  Future<void> _approveBoardPostOnServer(String postId) async {
    if (ServerConfig.personalDataLocalOnly) return;
    final serverId = _serverNumericId(postId);
    if (serverId == null) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      await api.approvePost(serverAccessToken, '$serverId');
      await syncBoardFromServer();
    } catch (_) {
      // Keep local approval visible even when the server approve fails.
    } finally {
      api.dispose();
    }
  }

  Future<void> _approveAllPendingPostsOnServer() async {
    if (ServerConfig.personalDataLocalOnly) return;
    final pendingIds = boardPosts
        .where((post) => !post.approved)
        .map((post) => post.id)
        .toList(growable: false);
    if (pendingIds.isEmpty) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      for (final postId in pendingIds) {
        final serverId = _serverNumericId(postId);
        if (serverId == null) continue;
        await api.approvePost(serverAccessToken, '$serverId');
      }
      await syncBoardFromServer();
    } catch (_) {
      // Keep local approvals visible even if the server call fails.
    } finally {
      api.dispose();
    }
  }

  Future<void> _deleteBoardPostFromServer(String postId) async {
    if (ServerConfig.personalDataLocalOnly) return;
    final serverId = _serverNumericId(postId);
    if (serverId == null) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      await api.deletePost(
        serverAccessToken,
        '$serverId',
        deviceId: deviceId,
      );
      await syncBoardFromServer();
    } catch (_) {
      // Local delete remains as a temporary fallback view.
    } finally {
      api.dispose();
    }
  }

  Future<void> _deleteAllBoardPostsFromServer(List<String> postIds) async {
    if (ServerConfig.personalDataLocalOnly) return;
    if (postIds.isEmpty) return;
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;
    final api = BoardApiService();
    try {
      for (final postId in postIds) {
        final serverId = _serverNumericId(postId);
        if (serverId == null) continue;
        await api.deletePost(
          serverAccessToken,
          '$serverId',
          deviceId: deviceId,
        );
      }
      await syncBoardFromServer();
    } catch (_) {
      // Keep local deletion visible even if the server call fails.
    } finally {
      api.dispose();
    }
  }

  Future<void> _refreshAdminModeFromServer() async {
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) {
      if (adminMode) {
        adminMode = false;
        if (_localAdminSessionInjected) {
          _restorePostAdminLocalSession();
        }
        notifyListeners();
      }
      return;
    }
    try {
      final resp = await http.get(
        ServerConfig.boardUri('/health'),
        headers: {
          if (localAdminOverrideEnabled) 'X-Deokive-App-Admin': '1',
        },
      ).timeout(const Duration(seconds: 6));
      if (resp.statusCode != 200) {
        if (adminMode) {
          adminMode = false;
          notifyListeners();
        }
        return;
      }
      final data = jsonDecode(utf8.decode(resp.bodyBytes));
      final nextAdminMode =
          data is Map<String, dynamic> && data['admin'] == true;
      if (nextAdminMode) {
        final wasAdminMode = adminMode;
        adminMode = true;
        if (localAdminOverrideEnabled) {
          if (!isLoggedIn) {
            _localAdminSessionInjected = true;
            isLoggedIn = true;
            authProvider = AuthProviderType.local;
            accountId = deviceId;
          }
          displayName = _reservedAdminNickname;
          tag = '@admin';
        }
        notifyListeners();
        if (!wasAdminMode) {
          unawaited(syncBoardFromServer());
        }
        return;
      }
      if (adminMode) {
        adminMode = false;
        if (_localAdminSessionInjected) {
          _restorePostAdminLocalSession();
        } else {
          final savedNickname = configuredNickname;
          if (savedNickname != null && savedNickname.isNotEmpty) {
            displayName = savedNickname;
            tag = '@$savedNickname';
          }
        }
        notifyListeners();
      }
    } catch (_) {
      if (adminMode) {
        adminMode = false;
        if (_localAdminSessionInjected) {
          _restorePostAdminLocalSession();
        } else {
          final savedNickname = configuredNickname;
          if (savedNickname != null && savedNickname.isNotEmpty) {
            displayName = savedNickname;
            tag = '@$savedNickname';
          }
        }
        notifyListeners();
      }
    }
  }

  void _restorePostAdminLocalSession() {
    _localAdminSessionInjected = false;
    final savedNickname = configuredNickname;
    if (savedNickname != null && savedNickname.isNotEmpty) {
      isLoggedIn = true;
      authProvider = AuthProviderType.local;
      accountId = deviceId;
      displayName = savedNickname;
      tag = '@$savedNickname';
      return;
    }
    isLoggedIn = false;
    authProvider = AuthProviderType.guest;
    accountId = 'nickname_required';
    displayName = 'Guest';
    tag = '@guest';
  }

  void _loadBoardSocial() {
    final liked = _storageBox?.get(_likedPostsKey);
    if (liked is List) {
      likedPostIds
        ..clear()
        ..addAll(liked.whereType<String>());
    }
    final saved = _storageBox?.get(_bookmarkedPostsKey);
    if (saved is List) {
      bookmarkedPostIds
        ..clear()
        ..addAll(saved.whereType<String>());
    }
    final counts = _storageBox?.get(_postLikeCountsKey);
    if (counts is Map) {
      postLikeCounts.clear();
      counts.forEach((k, v) {
        if (k is String && v is int) postLikeCounts[k] = v;
      });
    }
    final cm = _storageBox?.get(_postCommentsKey);
    if (cm is Map) {
      postComments.clear();
      cm.forEach((k, v) {
        if (k is String && v is List) {
          postComments[k] = v
              .whereType<Map>()
              .map((m) => BoardComment.fromJson(Map<String, dynamic>.from(m)))
              .toList();
        }
      });
    }
    final seen = _storageBox?.get(_boardCommentSeenKey);
    if (seen is Map) {
      _seenBoardCommentIdsByPost.clear();
      seen.forEach((k, v) {
        if (k is String && v is int) {
          _seenBoardCommentIdsByPost[k] = v;
        } else if (k is String && v is num) {
          _seenBoardCommentIdsByPost[k] = v.toInt();
        }
      });
    }
  }

  Future<void> _persistBoardCommentSeenState() async {
    if (_storageBox == null) return;
    await _storageBox!.put(
      _boardCommentSeenKey,
      Map<String, int>.from(_seenBoardCommentIdsByPost),
    );
  }

  // ── Trade posts ─────────────────────────────────────────────────────
  void _loadTradePosts() {
    final raw = _storageBox?.get(_tradePostsKey) as List<dynamic>?;
    tradePosts.clear();
    if (raw == null) return;
    for (final item in raw) {
      try {
        tradePosts
            .add(TradePost.fromJson(Map<String, dynamic>.from(item as Map)));
      } catch (_) {}
    }
  }

  Future<void> _persistTradePosts() async {
    if (_storageBox == null) return;
    await _storageBox!.put(
      _tradePostsKey,
      tradePosts.map((p) => p.toJson()).toList(growable: false),
    );
  }

  void addTradePost(TradePost post) {
    tradePosts.insert(0, post);
    _persistTradePosts();
    notifyListeners();
  }

  void updateTradePost(TradePost post) {
    final idx = tradePosts.indexWhere((p) => p.id == post.id);
    if (idx < 0) return;
    tradePosts[idx] = post;
    _persistTradePosts();
    notifyListeners();
  }

  void deleteTradePost(String id) {
    tradePosts.removeWhere((p) => p.id == id);
    _persistTradePosts();
    notifyListeners();
  }

  void incrementTradePostView(String id) {
    final idx = tradePosts.indexWhere((p) => p.id == id);
    if (idx < 0) return;
    tradePosts[idx] =
        tradePosts[idx].copyWith(viewCount: tradePosts[idx].viewCount + 1);
    _persistTradePosts();
    notifyListeners();
  }

  // ── Info bot sync ───────────────────────────────────────────────────
  void _loadInfoBotFeeds() {
    final raw = _storageBox?.get(_infoBotFeedsKey) as Map<dynamic, dynamic>?;
    infoBotFeedOverrides.clear();
    if (raw == null) return;
    raw.forEach((k, v) {
      if (k is String && v is String && v.isNotEmpty) {
        infoBotFeedOverrides[k] = v;
      }
    });
  }

  Future<void> _persistInfoBotFeeds() async {
    if (_storageBox == null) return;
    await _storageBox!.put(_infoBotFeedsKey, infoBotFeedOverrides);
  }

  void setInfoBotFeedOverride(String botId, String? url) {
    if (url == null || url.trim().isEmpty) {
      infoBotFeedOverrides.remove(botId);
    } else {
      infoBotFeedOverrides[botId] = url.trim();
    }
    _persistInfoBotFeeds();
    notifyListeners();
  }

  String resolvedInfoBotFeed(InfoBot bot) =>
      infoBotFeedOverrides[bot.id] ?? bot.defaultFeedUrl;

  // ── Claude API key + translation cache ─────────────────────────────
  void _loadClaudeApiKey() {
    claudeApiKey = _storageBox?.get(_claudeApiKeyKey) as String? ?? '';
  }

  Future<void> setClaudeApiKey(String key) async {
    claudeApiKey = key.trim();
    if (_storageBox != null) {
      if (claudeApiKey.isEmpty) {
        await _storageBox!.delete(_claudeApiKeyKey);
      } else {
        await _storageBox!.put(_claudeApiKeyKey, claudeApiKey);
      }
    }
    notifyListeners();
  }

  bool get hasClaudeApiKey => claudeApiKey.isNotEmpty;

  void _loadPostTranslations() {
    final raw =
        _storageBox?.get(_postTranslationsKey) as Map<dynamic, dynamic>?;
    postTranslations.clear();
    if (raw == null) return;
    raw.forEach((postId, langMap) {
      if (postId is! String || langMap is! Map) return;
      final byLang = <String, ProcessedTranslation>{};
      langMap.forEach((lang, fields) {
        if (lang is String && fields is Map) {
          try {
            byLang[lang] = ProcessedTranslation.fromJson(
              Map<String, dynamic>.from(fields),
            );
          } catch (_) {}
        }
      });
      if (byLang.isNotEmpty) postTranslations[postId] = byLang;
    });
  }

  Future<void> _persistPostTranslations() async {
    if (_storageBox == null) return;
    final serialized = <String, Map<String, dynamic>>{};
    postTranslations.forEach((postId, langMap) {
      serialized[postId] =
          langMap.map((lang, fields) => MapEntry(lang, fields.toJson()));
    });
    await _storageBox!.put(_postTranslationsKey, serialized);
  }

  ProcessedTranslation? cachedTranslationFor(String postId, String langCode) {
    return postTranslations[postId]?[langCode];
  }

  /// Translate a board post into [langCode] using the **free** Google
  /// Translate web endpoint (no API key, no quota, no cost). Idempotent —
  /// cached results are returned instantly. Returns null if the call fails;
  /// callers fall back to the original fields.
  Future<ProcessedTranslation?> translateBoardPost(
    BoardPost post,
    String langCode,
  ) async {
    final existing = cachedTranslationFor(post.id, langCode);
    if (existing != null) {
      if (kDebugMode) debugPrint('🌐 translate[${post.id}] cache HIT');
      return existing;
    }
    final lockKey = '${post.id}::$langCode';
    if (_inFlightTranslations.contains(lockKey)) {
      if (kDebugMode) debugPrint('🌐 translate[${post.id}] already in-flight');
      return null;
    }
    _inFlightTranslations.add(lockKey);
    if (kDebugMode) {
      debugPrint(
          '🌐 translate[${post.id}] START → $langCode ("${post.title.substring(0, post.title.length > 30 ? 30 : post.title.length)}…")');
    }
    try {
      final svc = FreeTranslationService();
      try {
        final result = await svc.process(
          rawTitle: post.title,
          rawSummary: post.summary,
          rawContent: post.content,
          targetLanguageCode: langCode,
        );
        final entry = ProcessedTranslation(
          title: result.title.isEmpty ? post.title : result.title,
          summary: result.summary.isEmpty ? post.summary : result.summary,
          content: result.content.isEmpty ? post.content : result.content,
          translatedAt: DateTime.now(),
        );
        final bucket = postTranslations.putIfAbsent(post.id, () => {});
        bucket[langCode] = entry;
        await _persistPostTranslations();
        notifyListeners();
        if (kDebugMode) {
          debugPrint(
              '🌐 translate[${post.id}] OK → "${entry.title.substring(0, entry.title.length > 30 ? 30 : entry.title.length)}…"');
        }
        return entry;
      } finally {
        svc.dispose();
      }
    } catch (e) {
      debugPrint('🌐 translate[${post.id}] FAILED: $e');
      return null;
    } finally {
      _inFlightTranslations.remove(lockKey);
    }
  }

  /// Pull latest posts from every configured info bot and add the new ones
  /// to the board. Returns the count of newly-inserted posts.
  Future<int> refreshInfoBots() async {
    if (readOnlyPublicSite) return 0;
    if (isRefreshingInfoBots) return 0;
    // When the board lives on the server, refresh the shared info-bot feeds
    // on the backend first, then pull the updated shared board state.
    if (ServerConfig.enabled) {
      isRefreshingInfoBots = true;
      notifyListeners();
      final api = BoardApiService();
      try {
        final added = await api.refreshInfoBots(serverAccessToken);
        await syncBoardFromServer();
        return added;
      } finally {
        api.dispose();
        isRefreshingInfoBots = false;
        notifyListeners();
      }
    }
    isRefreshingInfoBots = true;
    notifyListeners();
    int added = 0;
    try {
      final service = InfoBotService();
      try {
        final existingIds = boardPosts.map((p) => p.id).toSet();
        final fresh = await service.refreshAll(
          existingIds: existingIds,
          feedOverrides: infoBotFeedOverrides,
        );
        if (fresh.isNotEmpty) {
          boardPosts.insertAll(0, fresh);
          await _persistBoardPosts();
          added = fresh.length;
          // Pre-translate fresh posts into the user's current language so the
          // board list shows Korean (or whatever the app is set to) right
          // after refresh — without this, posts sit in the source language
          // (Japanese in most cases) until the user opens each one.
          final langCode = appLanguage.translationCode;
          final tx = FreeTranslationService();
          try {
            for (final post in fresh) {
              if (cachedTranslationFor(post.id, langCode) != null) continue;
              try {
                final result = await tx.process(
                  rawTitle: post.title,
                  rawSummary: post.summary,
                  rawContent: post.content,
                  targetLanguageCode: langCode,
                );
                final entry = ProcessedTranslation(
                  title: result.title.isEmpty ? post.title : result.title,
                  summary:
                      result.summary.isEmpty ? post.summary : result.summary,
                  content:
                      result.content.isEmpty ? post.content : result.content,
                  translatedAt: DateTime.now(),
                );
                final bucket = postTranslations.putIfAbsent(post.id, () => {});
                bucket[langCode] = entry;
              } catch (e) {
                debugPrint('pre-translate failed for ${post.id}: $e');
              }
            }
            await _persistPostTranslations();
            notifyListeners();
          } finally {
            tx.dispose();
          }
        }
      } finally {
        service.dispose();
      }
    } finally {
      isRefreshingInfoBots = false;
      notifyListeners();
    }
    return added;
  }

  @override
  void dispose() {
    _infoBotRefreshAnchorTimer?.cancel();
    _infoBotRefreshTimer?.cancel();
    _boardSyncTimer?.cancel();
    super.dispose();
  }

  Future<void> signOut() async {
    try {
      // Sign out of Google whenever the session was Google-authenticated —
      // either a pure Google account or a local account linked to Google.
      if (authProvider == AuthProviderType.google || isGoogleLinked) {
        await _googleSignIn.signOut();
      }
    } catch (_) {}

    isLoggedIn = false;
    inGuestSession = false;
    isGoogleLinked = false;
    driveBackupEnabled = false;
    authProvider = AuthProviderType.guest;
    serverAccessToken = null;
    displayName = 'Guest';
    accountId = '로그인이 필요합니다';
    tag = '@guest';
    await _storageBox?.delete(_deviceNicknameKey);
    profileImageBytes = null;
    profileImageUrl = null;
    avatarBodyType = -1;
    avatarBackgroundType = -1;
    avatarHairStyle = -1;
    avatarHairColorIndex = -1;
    avatarAccentColorIndex = -1;
    avatarOutfitColorIndex = -1;
    avatarSkinToneIndex = -1;
    avatarHasHat = false;
    avatarHasCape = false;
    avatarHasHandheld = false;
    avatarHasBackRibbon = false;
    await _clearPersistedAuthSession();
    await _loadAccountData();
    notifyListeners();
  }

  Future<void> _syncProfileToServer() async {
    if (ServerConfig.personalDataLocalOnly) return;
    final token = serverAccessToken?.trim();
    if (authProvider != AuthProviderType.local ||
        token == null ||
        token.isEmpty) {
      return;
    }
    final hasServer = await ServerConfig.ensureResolved();
    if (!hasServer) return;

    final api = AuthApiService();
    try {
      final profile = await api.updateMe(
        token,
        nickname: displayName,
        tag: tag,
        profileImageUrl: profileImageUrl,
      );
      displayName =
          profile.nickname.trim().isEmpty ? displayName : profile.nickname;
      tag = profile.tag.trim().isEmpty ? tag : profile.tag;
      profileImageUrl = (profile.profileImageUrl ?? '').trim().isEmpty
          ? profileImageUrl
          : profile.profileImageUrl!.trim();
      await _persistAuthSession();
      await _saveAccountData();
      notifyListeners();
    } catch (_) {
      // Keep local edits even if the server is currently offline.
    } finally {
      api.dispose();
    }
  }

  Future<bool> setProfile({
    required String name,
    required String handle,
    String? id,
    Uint8List? imageBytes,
  }) async {
    if (!canEditProfile) return false;

    final nickname = name.trim();
    final nicknameChanged = nickname != displayName.trim();
    if (isAdminSession && nicknameChanged) {
      return false;
    }
    if (!isValidNickname(nickname)) {
      return false;
    }

    if (nickname != displayName) {
      final claimed = await claimDeviceNickname(nickname);
      if (!claimed) return false;
    } else {
      displayName = nickname;
      tag = '@$nickname';
      _storageBox?.put(_deviceNicknameKey, nickname);
      _storageBox?.put(_lastDeviceNicknameKey, nickname);
    }

    if (authProvider == AuthProviderType.local &&
        id != null &&
        id.trim().isNotEmpty) {
      final normalizedId = id.trim();
      final duplicated = _localAccounts.any(
        (account) =>
            account['id'] == normalizedId && account['id'] != accountId,
      );
      if (duplicated) {
        return false;
      }
      accountId = normalizedId;
    }

    if (imageBytes != null) {
      profileImageBytes = imageBytes;
      profileImageUrl = null;
    }

    if (authProvider == AuthProviderType.local) {
      final account = _findLocalAccount(accountId);
      if (account != null) {
        account['nickname'] = displayName;
        account['id'] = accountId;
        account['tag'] = tag;
        account['profileImageBytes'] = profileImageBytes;
        _persistStorageValues();
      }
    }

    _saveAccountData();
    _persistAuthSession();
    notifyListeners();
    return true;
  }

  void updateAvatar({
    int? bodyType,
    int? backgroundType,
    int? hairStyle,
    int? hairColorIndex,
    int? accentColorIndex,
    int? outfitColorIndex,
    int? skinToneIndex,
    bool? hasHat,
    bool? hasCape,
    bool? hasHandheld,
    bool? hasBackRibbon,
  }) {
    avatarBodyType = bodyType ?? avatarBodyType;
    avatarBackgroundType = backgroundType ?? avatarBackgroundType;
    avatarHairStyle = hairStyle ?? avatarHairStyle;
    avatarHairColorIndex = hairColorIndex ?? avatarHairColorIndex;
    avatarAccentColorIndex = accentColorIndex ?? avatarAccentColorIndex;
    avatarOutfitColorIndex = outfitColorIndex ?? avatarOutfitColorIndex;
    avatarSkinToneIndex = skinToneIndex ?? avatarSkinToneIndex;
    avatarHasHat = hasHat ?? avatarHasHat;
    avatarHasCape = hasCape ?? avatarHasCape;
    avatarHasHandheld = hasHandheld ?? avatarHasHandheld;
    avatarHasBackRibbon = hasBackRibbon ?? avatarHasBackRibbon;
    _saveAccountData();
    notifyListeners();
  }

  void setTab(int index) {
    currentTabIndex = index;
    notifyListeners();
  }

  Future<void> reloadForNavigation() async {
    if (_isNavigationReloading) return;
    _isNavigationReloading = true;
    try {
      await _ensureStorageReady();
      final hasServer = await ServerConfig.ensureResolved();
      if (hasServer) {
        await _refreshAdminModeFromServer();
        await Future.wait([
          syncBoardFromServer(),
          syncCatalogFromServer(),
        ]);
      } else {
        notifyListeners();
      }
    } finally {
      _isNavigationReloading = false;
    }
  }

  void setPushEnabled(bool value) {
    pushEnabled = value;
    _persistStorageValues();
    notifyListeners();
  }

  void setDarkModeEnabled(bool value) {
    darkModeEnabled = value;
    _persistStorageValues();
    notifyListeners();
  }

  void setFontScale(double value) {
    fontScale = value.clamp(0.85, 1.4);
    _persistStorageValues();
    notifyListeners();
  }

  void setFontFamily(String? value) {
    fontFamily = value;
    _persistStorageValues();
    notifyListeners();
  }

  /// Pick a showcase background tier. `-1` means background off.
  void setShowcaseBgTier(int tier) {
    selectedShowcaseBgTier = tier.clamp(-1, 7);
    _persistStorageValues();
    notifyListeners();
  }

  /// Effective tier used to render the showcase background.
  int effectiveShowcaseBgTier(int profileLevel) {
    final maxUnlocked = (profileLevel ~/ 5).clamp(0, 7);
    if (selectedShowcaseBgTier < 0) return -1;
    if (selectedShowcaseBgTier > maxUnlocked) return maxUnlocked;
    return selectedShowcaseBgTier;
  }

  void setKeepSignedIn(bool value) {
    keepSignedIn = value;
    _persistStorageValues();
    if (keepSignedIn) {
      _persistAuthSession();
    } else {
      _clearPersistedAuthSession();
    }
    notifyListeners();
  }

  void setFolderSortType(FolderSortType value) {
    folderSortType = value;
    notifyListeners();
  }

  void setDefaultGoodsSortType(GoodsSortType value) {
    defaultGoodsSortType = value;
    notifyListeners();
  }

  String makeId() => DateTime.now().microsecondsSinceEpoch.toString();

  void addFolder(FolderItem folder) {
    folders.add(folder);
    _saveAccountData();
    notifyListeners();
  }

  void updateFolder(FolderItem updatedFolder) {
    final index = folders.indexWhere((folder) => folder.id == updatedFolder.id);
    if (index != -1) {
      folders[index] = updatedFolder;
      _saveAccountData();
      notifyListeners();
    }
  }

  void addGoods(GoodsItem item) {
    goodsItems.add(item);
    _saveAccountData();
    notifyListeners();
  }

  void updateGoods(GoodsItem updatedItem) {
    final index = goodsItems.indexWhere((item) => item.id == updatedItem.id);
    if (index != -1) {
      goodsItems[index] = updatedItem;
      _saveAccountData();
      notifyListeners();
    }
  }

  /// Deletes a non-system folder if it has no goods and no children.
  /// Returns true when deletion succeeded.
  bool deleteFolderById(String folderId) {
    final folder = folders.firstWhere(
      (f) => f.id == folderId,
      orElse: () => const FolderItem(
        id: '',
        name: '',
        icon: Icons.folder,
        color: Color(0xFF000000),
      ),
    );
    if (folder.id.isEmpty || folder.isSystemWishlist) return false;
    final hasGoods = goodsItems.any((item) => item.folderId == folderId);
    final hasChildren = folders.any((f) => f.parentId == folderId);
    if (hasGoods || hasChildren) return false;
    folders.removeWhere((f) => f.id == folderId);
    _saveAccountData();
    notifyListeners();
    return true;
  }

  /// Move a wishlist item into a real owned folder.
  /// Sets purchaseState to owned and clears the wishlistTargetFolderId hint.
  void markGoodsAsPurchased(String goodsId, String targetFolderId) {
    final index = goodsItems.indexWhere((item) => item.id == goodsId);
    if (index == -1) return;
    goodsItems[index] = goodsItems[index].copyWith(
      folderId: targetFolderId,
      purchaseState: PurchaseState.owned,
      wishlistTargetFolderId: null,
      isPreorder: false,
    );
    _saveAccountData();
    notifyListeners();
  }

  /// Folders that can receive a "purchased" goods item — any folder
  /// except the wishlist holder. Group folders are allowed since they
  /// can now hold goods directly.
  List<FolderItem> get owningFolders {
    return folders.where((folder) => !folder.isSystemWishlist).toList();
  }

  void toggleFavorite(String goodsId) {
    final index = goodsItems.indexWhere((item) => item.id == goodsId);
    if (index != -1) {
      goodsItems[index] = goodsItems[index].copyWith(
        isFavorite: !goodsItems[index].isFavorite,
      );
      _saveAccountData();
      notifyListeners();
    }
  }

  void deleteGoodsByIds(Set<String> ids) {
    goodsItems.removeWhere((item) => ids.contains(item.id));
    _saveAccountData();
    notifyListeners();
  }

  void moveGoodsToFolder(Set<String> ids, String newFolderId) {
    for (var i = 0; i < goodsItems.length; i++) {
      if (ids.contains(goodsItems[i].id)) {
        goodsItems[i] = goodsItems[i].copyWith(folderId: newFolderId);
      }
    }
    _saveAccountData();
    notifyListeners();
  }

  void moveFoldersToParent(Set<String> ids, String? newParentId) {
    for (var i = 0; i < folders.length; i++) {
      if (ids.contains(folders[i].id)) {
        folders[i] = folders[i].copyWith(parentId: newParentId);
      }
    }
    _saveAccountData();
    notifyListeners();
  }

  int goodsCountForFolder(String folderId) {
    return goodsItems.where((item) => item.folderId == folderId).length;
  }

  List<FolderItem> getSortedFolders() {
    final copied = [...folders];

    switch (folderSortType) {
      case FolderSortType.nameAsc:
        copied.sort((a, b) => a.name.compareTo(b.name));
        break;
      case FolderSortType.goodsCountDesc:
        copied.sort(
          (a, b) =>
              goodsCountForFolder(b.id).compareTo(goodsCountForFolder(a.id)),
        );
        break;
    }

    return copied;
  }

  List<GoodsItem> goodsForFolder(String folderId) {
    return goodsItems.where((item) => item.folderId == folderId).toList();
  }

  List<GoodsItem> favoriteGoods() {
    return goodsItems.where((item) => item.isFavorite).toList();
  }

  Uint8List? imageBytesForBarcode(
    String barcode, {
    String? excludingGoodsId,
  }) {
    final normalized = barcode.trim();
    if (normalized.isEmpty) return null;

    for (final item in goodsItems.reversed) {
      if (excludingGoodsId != null && item.id == excludingGoodsId) {
        continue;
      }
      if (item.barcode == normalized && item.imageBytes != null) {
        return item.imageBytes;
      }
    }
    return null;
  }

  List<GoodsItem> sortGoods(List<GoodsItem> items, GoodsSortType type) {
    final copied = [...items];

    switch (type) {
      case GoodsSortType.nameAsc:
        copied.sort((a, b) => a.name.compareTo(b.name));
        break;
      case GoodsSortType.priceAsc:
        copied.sort(
          (a, b) =>
              (a.paidPrice ?? 999999999).compareTo(b.paidPrice ?? 999999999),
        );
        break;
      case GoodsSortType.priceDesc:
        copied.sort((a, b) => (b.paidPrice ?? -1).compareTo(a.paidPrice ?? -1));
        break;
      case GoodsSortType.seriesAsc:
        copied.sort((a, b) => a.seriesName.compareTo(b.seriesName));
        break;
      case GoodsSortType.purchaseDateNewest:
        copied.sort(
          (a, b) => (b.purchaseDate ?? DateTime(1900))
              .compareTo(a.purchaseDate ?? DateTime(1900)),
        );
        break;
      case GoodsSortType.purchaseDateOldest:
        copied.sort(
          (a, b) => (a.purchaseDate ?? DateTime(9999))
              .compareTo(b.purchaseDate ?? DateTime(9999)),
        );
        break;
      case GoodsSortType.releaseDateNewest:
        copied.sort(
          (a, b) => (b.releaseDate ?? DateTime(1900))
              .compareTo(a.releaseDate ?? DateTime(1900)),
        );
        break;
      case GoodsSortType.releaseDateOldest:
        copied.sort(
          (a, b) => (a.releaseDate ?? DateTime(9999))
              .compareTo(b.releaseDate ?? DateTime(9999)),
        );
        break;
      case GoodsSortType.quantityDesc:
        copied.sort((a, b) => b.quantity.compareTo(a.quantity));
        break;
      case GoodsSortType.favoritesFirst:
        copied.sort((a, b) {
          if (a.isFavorite == b.isFavorite) return a.name.compareTo(b.name);
          return a.isFavorite ? -1 : 1;
        });
        break;
      case GoodsSortType.characterAsc:
        copied.sort((a, b) => a.characterName.compareTo(b.characterName));
        break;
      case GoodsSortType.categoryAsc:
        copied.sort((a, b) => a.category.compareTo(b.category));
        break;
    }

    return copied;
  }

  List<String> get knownSeriesNames {
    final set = <String>{};
    for (final item in goodsItems) {
      final s = item.seriesName.trim();
      if (s.isNotEmpty) set.add(s);
    }
    final list = set.toList()..sort();
    return list;
  }

  List<String> get knownCharacterNames {
    final set = <String>{};
    for (final item in goodsItems) {
      final c = item.characterName.trim();
      if (c.isNotEmpty) set.add(c);
    }
    final list = set.toList()..sort();
    return list;
  }

  List<String> get knownCategories {
    final set = <String>{};
    for (final item in goodsItems) {
      final c = item.category.trim();
      if (c.isNotEmpty) set.add(c);
    }
    final list = set.toList()..sort();
    return list;
  }

  Map<String, int> get goodsCountByCharacter {
    final map = <String, int>{};
    for (final item in goodsItems) {
      final c = item.characterName.trim();
      if (c.isEmpty) continue;
      map[c] = (map[c] ?? 0) + item.quantity;
    }
    return map;
  }

  Map<String, int> get goodsCountByCategory {
    final map = <String, int>{};
    for (final item in goodsItems) {
      final c = item.category.trim();
      if (c.isEmpty) continue;
      map[c] = (map[c] ?? 0) + item.quantity;
    }
    return map;
  }

  /// Aggregated goods count grouped by affiliation. Items with an empty
  /// affiliation are bucketed under `'(미분류)'`.
  Map<String, int> get goodsCountByAffiliation {
    final map = <String, int>{};
    for (final item in goodsItems) {
      final a = (item.affiliation ?? '').trim();
      final key = a.isEmpty ? '(미분류)' : a;
      map[key] = (map[key] ?? 0) + item.quantity;
    }
    return map;
  }

  /// Character counts limited to a given affiliation — used by the stats
  /// drill-down (소속 → 캐릭터).
  Map<String, int> goodsCountByCharacterInAffiliation(String affiliation) {
    final map = <String, int>{};
    for (final item in goodsItems) {
      final a = (item.affiliation ?? '').trim();
      final norm = a.isEmpty ? '(미분류)' : a;
      if (norm != affiliation) continue;
      final c = item.characterName.trim();
      if (c.isEmpty) continue;
      map[c] = (map[c] ?? 0) + item.quantity;
    }
    return map;
  }

  void addCalendarEvent(CalendarEventItem event) {
    calendarEvents.add(event);
    _saveAccountData();
    notifyListeners();
  }

  void updateCalendarEvent(CalendarEventItem updatedEvent) {
    final index =
        calendarEvents.indexWhere((event) => event.id == updatedEvent.id);
    if (index != -1) {
      calendarEvents[index] = updatedEvent;
      _saveAccountData();
      notifyListeners();
    }
  }

  void deleteCalendarEvent(String eventId) {
    calendarEvents.removeWhere((event) => event.id == eventId);
    _saveAccountData();
    notifyListeners();
  }

  List<CalendarEventItem> eventsForDate(DateTime date) {
    return calendarEvents.where((event) {
      return event.occursOn(date);
    }).toList()
      ..sort((a, b) {
        final left = a.timeText ?? '99:99';
        final right = b.timeText ?? '99:99';
        final byTime = left.compareTo(right);
        if (byTime != 0) return byTime;
        return a.title.compareTo(b.title);
      });
  }

  void addInquiry(SupportInquiryItem inquiry) {
    inquiries.add(inquiry);
    _saveAccountData();
    notifyListeners();
  }

  void answerInquiry(String id, String answer) {
    final index = inquiries.indexWhere((i) => i.id == id);
    if (index != -1) {
      final old = inquiries[index];
      inquiries[index] = old.copyWith(
        answer: answer,
        answeredAt: DateTime.now(),
      );
      _saveAccountData();
      notifyListeners();
    }
  }

  BadgeProgress get badgeProgress =>
      evaluateBadges(goodsItems: goodsItems, folders: folders);

  int get totalUnlockedBadgeCount => badgeProgress.unlockedBadgeIds.length;

  int get totalUnlockedBadgeLevel => allBadges
      .where((badge) => badgeProgress.unlockedBadgeIds.contains(badge.id))
      .fold(0, (sum, badge) => sum + badge.level);

  int get maxBadgeSlots => 3;

  int get topLevelFolderCount =>
      folders.where((folder) => folder.parentId == null).length;

  List<BadgeItem> get equippedBadges {
    return allBadges
        .where((badge) => equippedBadgeIds.contains(badge.id))
        .toList();
  }

  bool isBadgeUnlocked(String badgeId) {
    return badgeProgress.isUnlocked(badgeId);
  }

  bool isBadgeEquipped(String badgeId) {
    return equippedBadgeIds.contains(badgeId);
  }

  bool canEquipMoreBadges() {
    return equippedBadgeIds.length < maxBadgeSlots;
  }

  void toggleEquipBadge(String badgeId) {
    if (equippedBadgeIds.contains(badgeId)) {
      equippedBadgeIds.remove(badgeId);
    } else {
      if (!isBadgeUnlocked(badgeId)) return;
      if (equippedBadgeIds.length >= maxBadgeSlots) return;
      equippedBadgeIds.add(badgeId);
    }
    _saveAccountData();
    notifyListeners();
  }

  String folderSortLabel() {
    switch (folderSortType) {
      case FolderSortType.nameAsc:
        return '가나다순';
      case FolderSortType.goodsCountDesc:
        return '굿즈 많은순';
    }
  }

  String goodsSortLabel() {
    switch (defaultGoodsSortType) {
      case GoodsSortType.nameAsc:
        return '가나다순';
      case GoodsSortType.priceAsc:
        return '가격 낮은순';
      case GoodsSortType.priceDesc:
        return '가격 높은순';
      case GoodsSortType.seriesAsc:
        return '시리즈 가나다순';
      case GoodsSortType.purchaseDateNewest:
        return '구매일 최신순';
      case GoodsSortType.purchaseDateOldest:
        return '구매일 오래된순';
      case GoodsSortType.releaseDateNewest:
        return '발매일 최신순';
      case GoodsSortType.releaseDateOldest:
        return '발매일 오래된순';
      case GoodsSortType.quantityDesc:
        return '수량 많은순';
      case GoodsSortType.favoritesFirst:
        return '즐겨찾기 우선';
      case GoodsSortType.characterAsc:
        return '캐릭터순';
      case GoodsSortType.categoryAsc:
        return '카테고리순';
    }
  }
}
