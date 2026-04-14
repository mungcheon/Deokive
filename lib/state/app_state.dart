import 'dart:convert';
import 'dart:io';
import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:path_provider/path_provider.dart';

import '../config/app_server_config.dart';
import '../data/badge_definitions.dart';
import '../config/google_auth_config.dart';
import '../config/monetization_catalog.dart';
import '../models/badge_item.dart';
import '../models/calendar_event_item.dart';
import '../models/folder_item.dart';
import '../models/goods_item.dart';
import '../models/support_inquiry_item.dart';
import '../l10n/app_language.dart';
import '../theme/deokive_palette.dart';
import '../utils/badge_progress_helper.dart';

enum GoodsSortType {
  nameAsc,
  priceAsc,
  priceDesc,
  seriesAsc,
  purchaseDateNewest,
  purchaseDateOldest,
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

class BackupSnapshotInfo {
  final String source;
  final String uploadedAt;
  final int? payloadBytes;

  const BackupSnapshotInfo({
    required this.source,
    required this.uploadedAt,
    this.payloadBytes,
  });
}

class AppState extends ChangeNotifier {
  static const _driveAppDataScope =
      'https://www.googleapis.com/auth/drive.appdata';
  static const _driveBackupMimeType = 'application/json';
  static const _storageBoxName = 'deokive_storage';
  static const _localAccountsKey = 'local_accounts';
  static const _nextSignupSequenceKey = 'next_signup_sequence';
  static const _pushEnabledKey = 'push_enabled';
  static const _darkModeKey = 'dark_mode_enabled';
  static const _paletteKey = 'app_palette';
  static const _premiumEnabledKey = 'premium_enabled';
  static const _adsRemovedKey = 'ads_removed';
  static const _debugAdsEnabledKey = 'debug_ads_enabled';
  static const _homePopupDismissedDateKey = 'home_popup_dismissed_date';
  static const _lastAuthProviderKey = 'last_auth_provider';
  static const _lastAccountIdKey = 'last_account_id';
  static const _keepSignedInKey = 'keep_signed_in';
  static const _languageKey = 'app_language';
  static const _serverAccessTokenKey = 'server_access_token';
  static const _serverBackupPromptDismissedKey = 'server_backup_prompt_dismissed';

  final List<FolderItem> folders = [];
  final List<GoodsItem> goodsItems = [];
  final List<CalendarEventItem> calendarEvents = [];
  final List<SupportInquiryItem> inquiries = [];
  final List<String> equippedBadgeIds = [];

  static String? _resolveGoogleClientId() {
    if (kIsWeb) {
      return GoogleAuthConfig.webClientId;
    }
    if (Platform.isIOS || Platform.isMacOS) {
      return GoogleAuthConfig.iosClientId;
    }
    return null;
  }

  static String? _resolveGoogleServerClientId() {
    if (kIsWeb) {
      return GoogleAuthConfig.webServerClientId;
    }
    if (Platform.isAndroid) {
      return GoogleAuthConfig.androidServerClientId;
    }
    return null;
  }

  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: const ['email', _driveAppDataScope],
    clientId: _resolveGoogleClientId(),
    serverClientId: _resolveGoogleServerClientId(),
  );
  final List<Map<String, dynamic>> _localAccounts = [];

  Box<dynamic>? _storageBox;
  Future<void>? _storageInitFuture;
  bool _driveBackupQueued = false;

  int currentTabIndex = 0;
  bool isLoggedIn = false;
  bool pushEnabled = true;
  bool darkModeEnabled = false;
  bool isGoogleLinked = false;
  bool googleSignInAvailable = false;
  String? googleSignInError;
  bool driveBackupEnabled = false;
  bool premiumEnabled = false;
  bool adsRemoved = true;
  bool debugAdsEnabled = true;
  String? homePopupDismissedDate;
  bool keepSignedIn = true;
  bool driveBackupInProgress = false;
  String? driveBackupLastSyncedAt;
  String? driveBackupError;
  bool syncDialogVisible = false;
  String? syncStatusMessage;
  bool localServerBackupInProgress = false;
  String? localServerBackupLastSyncedAt;
  String? localServerBackupError;
  BackupSnapshotInfo? pendingRestoreSnapshot;
  String? serverAccessToken;

  AuthProviderType authProvider = AuthProviderType.guest;
  AppPalette appPalette = AppPalette.skyBlue;
  AppLanguage appLanguage = AppLanguage.korean;

  String displayName = 'Guest';
  String accountId = '로그인이 필요합니다';
  String tag = '@guest';
  Uint8List? profileImageBytes;
  String? profileImageUrl;
  int avatarBodyType = -1;
  int avatarBackgroundType = -1;
  int avatarFaceType = -1;
  int avatarHairStyle = -1;
  int avatarHairColorIndex = 0;
  int avatarAccentColorIndex = 0;
  int avatarOutfitColorIndex = -1;
  int avatarSkinToneIndex = -1;
  bool avatarHasHat = false;
  bool avatarHasCape = false;
  bool avatarHasHandheld = false;
  bool avatarHasBackRibbon = false;

  int _signupSequence = 1;
  bool _serverBackupPromptDismissed = false;

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
  }

  Future<void> _ensureStorageReady() async {
    _storageInitFuture ??= _initStorage();
    await _storageInitFuture;
  }

  Future<void> _initStorage() async {
    _storageBox ??= await Hive.openBox(_storageBoxName);
    _restoreStorageValues();
    await _restoreSavedSession();
    await _loadAccountData();
    notifyListeners();
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
    premiumEnabled =
        _storageBox?.get(_premiumEnabledKey, defaultValue: false) as bool? ??
            false;
    adsRemoved =
        _storageBox?.get(_adsRemovedKey, defaultValue: true) as bool? ?? true;
    debugAdsEnabled =
        _storageBox?.get(_debugAdsEnabledKey, defaultValue: true) as bool? ??
            true;
    homePopupDismissedDate =
        _storageBox?.get(_homePopupDismissedDateKey) as String?;
    keepSignedIn =
        _storageBox?.get(_keepSignedInKey, defaultValue: true) as bool? ?? true;
    serverAccessToken = _storageBox?.get(_serverAccessTokenKey) as String?;
    _serverBackupPromptDismissed =
        _storageBox?.get(
              _serverBackupPromptDismissedKey,
              defaultValue: false,
            ) as bool? ??
            false;
    driveBackupInProgress = false;
    driveBackupLastSyncedAt = null;
    driveBackupError = null;
    syncDialogVisible = false;
    syncStatusMessage = null;
    localServerBackupInProgress = false;
    localServerBackupLastSyncedAt = null;
    localServerBackupError = null;
    pendingRestoreSnapshot = null;

    final savedPaletteName = _storageBox?.get(_paletteKey,
            defaultValue: AppPalette.skyBlue.name) as String? ??
        AppPalette.skyBlue.name;
    appPalette = AppPalette.values.firstWhere(
      (item) => item.name == savedPaletteName,
      orElse: () => AppPalette.skyBlue,
    );
    final savedLanguageName = _storageBox?.get(_languageKey,
            defaultValue: AppLanguage.korean.name) as String? ??
        AppLanguage.korean.name;
    appLanguage = AppLanguage.values.firstWhere(
      (item) => item.name == savedLanguageName,
      orElse: () => AppLanguage.korean,
    );
  }

  Future<void> _persistStorageValues() async {
    if (_storageBox == null) return;
    await _storageBox!.put(_localAccountsKey, _localAccounts);
    await _storageBox!.put(_nextSignupSequenceKey, _signupSequence);
    await _storageBox!.put(_pushEnabledKey, pushEnabled);
    await _storageBox!.put(_darkModeKey, darkModeEnabled);
    await _storageBox!.put(_paletteKey, appPalette.name);
    await _storageBox!.put(_premiumEnabledKey, premiumEnabled);
    await _storageBox!.put(_adsRemovedKey, adsRemoved);
    await _storageBox!.put(_debugAdsEnabledKey, debugAdsEnabled);
    await _storageBox!.put(_homePopupDismissedDateKey, homePopupDismissedDate);
    await _storageBox!.put(_keepSignedInKey, keepSignedIn);
    await _storageBox!.put(_languageKey, appLanguage.name);
    await _storageBox!.put(
      _serverBackupPromptDismissedKey,
      _serverBackupPromptDismissed,
    );
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
    if ((serverAccessToken ?? '').isNotEmpty) {
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

    final providerName = _storageBox!.get(_lastAuthProviderKey) as String?;
    final savedAccountId = _storageBox!.get(_lastAccountIdKey) as String?;
    if (providerName == null ||
        savedAccountId == null ||
        savedAccountId.isEmpty) {
      return;
    }

    final provider = AuthProviderType.values.firstWhere(
      (item) => item.name == providerName,
      orElse: () => AuthProviderType.guest,
    );

    switch (provider) {
      case AuthProviderType.local:
        await _restoreSavedLocalSession(savedAccountId);
        return;
      case AuthProviderType.google:
        await _restoreSavedGoogleSession(savedAccountId);
        return;
      case AuthProviderType.guest:
        return;
    }
  }

  Future<void> _restoreSavedLocalSession(String savedAccountId) async {
    if (AppServerConfig.isConfigured && (serverAccessToken ?? '').isNotEmpty) {
      try {
        final profile = await _fetchRemoteProfile();
        isLoggedIn = true;
        isGoogleLinked = false;
        authProvider = AuthProviderType.local;
        driveBackupEnabled = false;
        displayName = profile['nickname']?.toString() ?? 'Deokive User';
        accountId = profile['login_id']?.toString() ?? savedAccountId;
        tag = profile['tag']?.toString() ?? _allocateTag();
        profileImageUrl = profile['profile_image_url'] as String?;
        profileImageBytes = null;
        await _loadServerBackupSnapshotIfNeeded();
        return;
      } catch (_) {}
    }

    final account = _findLocalAccount(savedAccountId);
    if (account == null) {
      await _clearPersistedAuthSession();
      return;
    }

    isLoggedIn = true;
    isGoogleLinked = false;
    authProvider = AuthProviderType.local;
    driveBackupEnabled = false;
    displayName = (account['nickname'] as String?) ?? 'Deokive User';
    accountId = (account['id'] as String?) ?? savedAccountId;
    tag = (account['tag'] as String?) ?? _allocateTag();
    profileImageUrl = null;
    final savedImage = account['profileImageBytes'];
    profileImageBytes = savedImage is Uint8List ? savedImage : null;
    serverAccessToken = null;
  }

  Future<void> _restoreSavedGoogleSession(String savedAccountId) async {
    if (!supportsGoogleSignIn || !hasRequiredGoogleSignInConfig) {
      await _clearPersistedAuthSession();
      return;
    }

    try {
      final account =
          _googleSignIn.currentUser ?? await _googleSignIn.signInSilently();
      if (account == null || account.email != savedAccountId) {
        await _clearPersistedAuthSession();
        return;
      }

      isLoggedIn = true;
      isGoogleLinked = true;
      authProvider = AuthProviderType.google;
      driveBackupEnabled = true;
      displayName = account.displayName?.trim().isNotEmpty == true
          ? account.displayName!.trim()
          : 'Google User';
      accountId = account.email;
      tag = '@guest';
      profileImageBytes = null;
      profileImageUrl = account.photoUrl;
      googleSignInAvailable = true;
      googleSignInError = null;
      driveBackupError = null;
      driveBackupLastSyncedAt = null;
      await _restoreDriveBackupIfAvailable(account);
    } catch (_) {
      await _clearPersistedAuthSession();
    }
  }

  String get _currentStorageAccountKey {
    switch (authProvider) {
      case AuthProviderType.google:
        return 'google_${_sanitizeStorageKey(accountId)}';
      case AuthProviderType.local:
        return 'local_${_sanitizeStorageKey(accountId)}';
      case AuthProviderType.guest:
        return 'guest';
    }
  }

  String _sanitizeStorageKey(String value) {
    return value.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
  }

  Future<File> _accountStorageFile([String? accountKey]) async {
    final documentsDir = await getApplicationDocumentsDirectory();
    final baseDir = Directory(
        '${documentsDir.path}${Platform.pathSeparator}deokive_accounts');
    if (!await baseDir.exists()) {
      await baseDir.create(recursive: true);
    }

    final targetDir = Directory(
      '${baseDir.path}${Platform.pathSeparator}${accountKey ?? _currentStorageAccountKey}',
    );
    if (!await targetDir.exists()) {
      await targetDir.create(recursive: true);
    }

    return File('${targetDir.path}${Platform.pathSeparator}data.json');
  }

  void _ensureDefaultFolder() {
    if (folders.isNotEmpty) return;
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

  Map<String, dynamic> _buildAccountPayload() {
    return <String, dynamic>{
      'savedAt': DateTime.now().toIso8601String(),
      'accountKey': _currentStorageAccountKey,
      'accountId': accountId,
      'authProvider': authProvider.name,
      'driveBackupEnabled': driveBackupEnabled,
      'profile': <String, dynamic>{
        'displayName': displayName,
        'tag': tag,
        'profileImageBytes': profileImageBytes,
        'profileImageUrl': profileImageUrl,
        'avatar': <String, dynamic>{
          'bodyType': avatarBodyType,
          'backgroundType': avatarBackgroundType,
          'faceType': avatarFaceType,
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
      'monetization': <String, dynamic>{
        'premiumEnabled': premiumEnabled,
        'adsRemoved': adsRemoved,
        'debugAdsEnabled': debugAdsEnabled,
      },
      'permissionFlags': <String, dynamic>{
        'canEditProfile': canEditProfile,
        'pushEnabled': pushEnabled,
        'darkModeEnabled': darkModeEnabled,
      },
    };
  }

  Future<void> _writeAccountPayloadToFile(
    File file,
    Map<String, dynamic> payload,
  ) async {
    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(payload),
      flush: true,
    );
  }

  void _resetAccountCollections() {
    folders.clear();
    goodsItems.clear();
    calendarEvents.clear();
    inquiries.clear();
    equippedBadgeIds.clear();
    premiumEnabled = false;
    adsRemoved = false;
    debugAdsEnabled = true;
    _resetAvatarSelection();
    _ensureDefaultFolder();
  }

  void _applyAccountPayload(Map<String, dynamic> json) {
    final loadedFolders = ((json['folders'] as List<dynamic>?) ?? const [])
        .map((item) => FolderItem.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
    final loadedGoods = ((json['goodsItems'] as List<dynamic>?) ?? const [])
        .map((item) => GoodsItem.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
    final loadedEvents = ((json['calendarEvents'] as List<dynamic>?) ?? const [])
        .map((item) => CalendarEventItem.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
    final loadedInquiries = ((json['inquiries'] as List<dynamic>?) ?? const [])
        .map((item) => SupportInquiryItem.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
    final loadedBadges = ((json['equippedBadgeIds'] as List<dynamic>?) ?? const [])
        .map((item) => item.toString())
        .toList();
    final monetization =
        Map<String, dynamic>.from(json['monetization'] as Map? ?? const {});
    final profile = Map<String, dynamic>.from(json['profile'] as Map? ?? const {});
    final avatar = Map<String, dynamic>.from(profile['avatar'] as Map? ?? const {});

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
    displayName = (profile['displayName'] as String?)?.trim().isNotEmpty == true
        ? (profile['displayName'] as String).trim()
        : displayName;
    tag = (profile['tag'] as String?)?.trim().isNotEmpty == true
        ? (profile['tag'] as String).trim()
        : tag;
    final savedProfileImageBytes = _decodeImageBytes(profile['profileImageBytes']);
    if (savedProfileImageBytes != null) {
      profileImageBytes = savedProfileImageBytes;
      profileImageUrl = null;
    } else {
      final savedProfileImageUrl = profile['profileImageUrl'] as String?;
      if ((savedProfileImageUrl ?? '').isNotEmpty) {
        profileImageUrl = savedProfileImageUrl;
      }
    }
    avatarBodyType = avatar['bodyType'] as int? ?? avatarBodyType;
    avatarBackgroundType = avatar['backgroundType'] as int? ?? avatarBackgroundType;
    avatarFaceType = avatar['faceType'] as int? ?? avatarFaceType;
    avatarHairStyle = avatar['hairStyle'] as int? ?? avatarHairStyle;
    avatarHairColorIndex = avatar['hairColorIndex'] as int? ?? avatarHairColorIndex;
    avatarAccentColorIndex =
        avatar['accentColorIndex'] as int? ?? avatarAccentColorIndex;
    avatarOutfitColorIndex =
        avatar['outfitColorIndex'] as int? ?? avatarOutfitColorIndex;
    avatarSkinToneIndex = avatar['skinToneIndex'] as int? ?? avatarSkinToneIndex;
    avatarHasHat = avatar['hasHat'] as bool? ?? avatarHasHat;
    avatarHasCape = avatar['hasCape'] as bool? ?? avatarHasCape;
    avatarHasHandheld = avatar['hasHandheld'] as bool? ?? avatarHasHandheld;
    avatarHasBackRibbon =
        avatar['hasBackRibbon'] as bool? ?? avatarHasBackRibbon;
    premiumEnabled = monetization['premiumEnabled'] as bool? ?? premiumEnabled;
    adsRemoved = monetization['adsRemoved'] as bool? ?? adsRemoved;
    debugAdsEnabled = monetization['debugAdsEnabled'] as bool? ?? debugAdsEnabled;

    _ensureDefaultFolder();
  }

  Future<void> _saveAccountData() async {
    try {
      final file = await _accountStorageFile();
      final payload = _buildAccountPayload();
      await _writeAccountPayloadToFile(file, payload);
      _enqueueDriveBackup();
    } catch (_) {}
  }

  Future<void> _loadAccountData() async {
    try {
      if (authProvider == AuthProviderType.guest) {
        _resetAccountCollections();
        return;
      }

      final file = await _accountStorageFile();
      if (!await file.exists()) {
        _resetAccountCollections();
        return;
      }

      final raw = await file.readAsString();
      final json = jsonDecode(raw) as Map<String, dynamic>;
      _applyAccountPayload(json);
    } catch (_) {
      _resetAccountCollections();
    }
  }

  Future<void> _initGoogleSignIn() async {
    if (!hasRequiredGoogleSignInConfig) {
      googleSignInAvailable = false;
      googleSignInError = 'missing_platform_config';
      notifyListeners();
      return;
    }
    googleSignInAvailable = true;
    googleSignInError = null;
    notifyListeners();
  }

  bool get canEditProfile => isLoggedIn;

  int get totalGoodsCount =>
      goodsItems.fold(0, (sum, item) => sum + item.quantity);

  int get totalPaidAmount => goodsItems.fold(
        0,
        (sum, item) => sum + ((item.paidPrice ?? 0) * item.quantity),
      );

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
      return '로그인 후 백업 상태를 확인할 수 있습니다.';
    }
    if (authProvider == AuthProviderType.google) {
      if (driveBackupInProgress) {
        return 'Google Drive에 백업하는 중입니다.';
      }
      if ((driveBackupLastSyncedAt ?? '').isNotEmpty) {
        return 'Google Drive 자동 백업이 연결되어 있습니다.';
      }
      if (driveBackupError == 'drive_scope_missing') {
        return '현재 데이터는 기기에 로컬 저장 중이며, Google Drive 권한을 허용하면 기존 로컬 데이터를 바로 백업합니다.';
      }
      if ((driveBackupError ?? '').isNotEmpty) {
        return '현재 데이터는 기기에 로컬 저장 중입니다. Google Drive 재연결 후 기존 로컬 데이터를 백업할 수 있습니다.';
      }
      return 'Google Drive 자동 백업이 연결됩니다.';
    }
    return '일반 계정은 주기적인 클라우드 백업이 제한될 수 있습니다.';
  }

  bool get isBusy =>
      syncDialogVisible || driveBackupInProgress || localServerBackupInProgress;

  bool get hasPendingRestorePrompt =>
      pendingRestoreSnapshot != null && !_serverBackupPromptDismissed;

  bool get canUseServerBackups =>
      AppServerConfig.isConfigured && authProvider == AuthProviderType.local;

  String get nextDefaultTag => '@deokive$_signupSequence';

  bool get supportsGoogleSignIn {
    if (kIsWeb) return true;
    return Platform.isAndroid || Platform.isIOS || Platform.isMacOS;
  }

  bool get hasRequiredGoogleSignInConfig {
    if (kIsWeb) {
      return GoogleAuthConfig.webClientId != null;
    }
    if (Platform.isIOS || Platform.isMacOS) {
      return GoogleAuthConfig.iosClientId != null;
    }
    return true;
  }

  String get googleSignInStatusText {
    if (!supportsGoogleSignIn) {
      return '현재 플랫폼에서는 구글 로그인을 지원하지 않습니다.';
    }
    if (!hasRequiredGoogleSignInConfig) {
      return '현재 플랫폼의 구글 로그인 설정이 누락되었습니다.';
    }
    if (!googleSignInAvailable) {
      return '구글 로그인 설정이 아직 완료되지 않았습니다.';
    }
    return '구글 계정으로 로그인하고 개인 Google Drive 백업을 사용할 수 있습니다.';
  }

  String get googleSignInMessage {
    if (!supportsGoogleSignIn) {
      return '현재 플랫폼에서는 구글 로그인을 지원하지 않습니다.';
    }
    if (!hasRequiredGoogleSignInConfig) {
      if (!kIsWeb && (Platform.isIOS || Platform.isMacOS)) {
        return 'iOS/macOS 구글 로그인 설정이 없습니다. GOOGLE_IOS_CLIENT_ID와 Info.plist의 GIDClientID, URL Scheme 설정이 필요합니다.';
      }
      if (kIsWeb) {
        return '웹 구글 로그인 설정이 없습니다. GOOGLE_WEB_CLIENT_ID 설정이 필요합니다.';
      }
      return '구글 로그인 설정이 누락되었습니다.';
    }
    if (googleSignInError == 'drive_scope_denied') {
      return '구글 로그인은 완료되었지만 Google Drive 자동 백업 권한이 거부되었습니다.';
    }
    if (googleSignInError != null && googleSignInError!.isNotEmpty) {
      return '구글 로그인 설정이 완료되지 않았거나 인증에 실패했습니다. '
          'Android는 패키지명과 SHA-1, iOS는 Client ID와 URL Scheme 설정이 필요합니다.';
    }
    if (!googleSignInAvailable) {
      return '구글 로그인 초기화 중입니다.';
    }
    return '구글 계정으로 로그인하면 프로필 정보를 가져오고 Google Drive 자동 백업을 연결합니다.';
  }

  String get todayStamp {
    final now = DateTime.now();
    final month = now.month.toString().padLeft(2, '0');
    final day = now.day.toString().padLeft(2, '0');
    return '${now.year}-$month-$day';
  }

  bool get shouldShowHomePromoPopup {
    if (!debugAdsEnabled) return false;
    if (isFeatureUnlocked(PremiumFeature.adFree)) return false;
    return homePopupDismissedDate != todayStamp;
  }

  Future<void> dismissHomePromoPopupForToday() async {
    homePopupDismissedDate = todayStamp;
    await _persistStorageValues();
    notifyListeners();
  }

  Future<void> clearHomePromoPopupDismissedDate() async {
    homePopupDismissedDate = null;
    await _persistStorageValues();
    notifyListeners();
  }

  bool isValidTagText(String value) {
    return RegExp(r'^[A-Za-z0-9]+$').hasMatch(value);
  }

  String _allocateTag() {
    final value = '@deokive$_signupSequence';
    _signupSequence += 1;
    return value;
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

  Future<void> _applyGoogleAccount(GoogleSignInAccount account) async {
    final shouldAssignFreshTag = authProvider != AuthProviderType.google ||
        tag == '@guest' ||
        tag.isEmpty;

    isLoggedIn = true;
    isGoogleLinked = true;
    authProvider = AuthProviderType.google;
    driveBackupEnabled = true;
    displayName = account.displayName?.trim().isNotEmpty == true
        ? account.displayName!.trim()
        : 'Google User';
    accountId = account.email;
    if (shouldAssignFreshTag) {
      tag = _allocateTag();
    }
    profileImageBytes = null;
    profileImageUrl = account.photoUrl;
    driveBackupError = null;
    driveBackupLastSyncedAt = null;
    await _persistAuthSession();
    await _restoreDriveBackupIfAvailable(account);
    await _loadAccountData();
    unawaited(_prepareDriveBackup(account));
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
      googleSignInError = 'missing_platform_config';
      notifyListeners();
      return false;
    }
    try {
      googleSignInAvailable = true;
      googleSignInError = null;
      final account = await _googleSignIn.signIn();
      if (account == null) {
        googleSignInError = 'cancelled';
        notifyListeners();
        return false;
      }
      await _applyGoogleAccount(account);
      return true;
    } catch (error) {
      googleSignInError = error.toString();
      notifyListeners();
      return false;
    }
  }

  void _enqueueDriveBackup() {
    if (!driveBackupEnabled || authProvider != AuthProviderType.google) return;
    if (driveBackupError == 'drive_scope_missing') return;
    _driveBackupQueued = true;
    unawaited(_flushDriveBackupQueue());
  }

  Future<void> _prepareDriveBackup(GoogleSignInAccount account) async {
    final hasDriveAccess = await _ensureDriveBackupAccess(account);
    if (hasDriveAccess) {
      googleSignInError = null;
      driveBackupError = null;
      await _restoreDriveBackupIfAvailable(account);
      _enqueueDriveBackup();
    } else {
      driveBackupError = 'drive_scope_missing';
    }
    notifyListeners();
  }

  Future<void> _restoreDriveBackupIfAvailable(GoogleSignInAccount account) async {
    try {
      if (!await _hasDriveBackupAccess(account)) {
        return;
      }

      final localFile = await _accountStorageFile();
      if (await localFile.exists()) {
        return;
      }

      var authHeaders = await account.authHeaders;
      if (!authHeaders.containsKey('Authorization')) {
        return;
      }

      final backupFileName =
          'deokive_backup_${_sanitizeStorageKey(accountId)}.json';
      final existingFileId = await _findDriveBackupFileId(
        authHeaders: authHeaders,
        fileName: backupFileName,
      );
      if (existingFileId == null) {
        return;
      }

      try {
        final mediaBytes = await _downloadDriveBackup(
          authHeaders: authHeaders,
          fileId: existingFileId,
        );
        await _writeDriveBackupToLocalFile(
          localFile: localFile,
          mediaBytes: mediaBytes,
        );
        driveBackupLastSyncedAt = DateTime.now().toIso8601String();
      } on HttpException catch (error) {
        final message = error.message.toLowerCase();
        if (!message.contains('401')) {
          rethrow;
        }
        await account.clearAuthCache();
        authHeaders = await account.authHeaders;
        final mediaBytes = await _downloadDriveBackup(
          authHeaders: authHeaders,
          fileId: existingFileId,
        );
        await _writeDriveBackupToLocalFile(
          localFile: localFile,
          mediaBytes: mediaBytes,
        );
        driveBackupLastSyncedAt = DateTime.now().toIso8601String();
      }
    } catch (error) {
      driveBackupError = error.toString();
    }
  }

  Future<bool> _ensureDriveBackupAccess(GoogleSignInAccount account) async {
    if (await _hasDriveBackupAccess(account)) {
      return true;
    }
    try {
      final granted =
          await _googleSignIn.requestScopes(const [_driveAppDataScope]);
      if (!granted) {
        googleSignInError = 'drive_scope_denied';
        return false;
      }
      if (await _hasDriveBackupAccess(account)) {
        return true;
      }
    } catch (_) {
      googleSignInError = 'drive_scope_denied';
      return false;
    }
    googleSignInError = 'drive_scope_denied';
    return false;
  }

  Future<bool> retryDriveBackupAuthorizationAndSync() async {
    if (authProvider != AuthProviderType.google) return false;

    final account =
        _googleSignIn.currentUser ?? await _googleSignIn.signInSilently();
    if (account == null) {
      driveBackupError = 'drive_scope_missing';
      notifyListeners();
      return false;
    }

    driveBackupInProgress = true;
    notifyListeners();
    try {
      final granted = await _ensureDriveBackupAccess(account);
      if (!granted) {
        driveBackupError = 'drive_scope_missing';
        return false;
      }

      driveBackupError = null;
      googleSignInError = null;
      _driveBackupQueued = true;
      await _flushDriveBackupQueue();
      return driveBackupError == null;
    } finally {
      driveBackupInProgress = false;
      notifyListeners();
    }
  }

  Future<void> _flushDriveBackupQueue() async {
    if (driveBackupInProgress) return;

    while (_driveBackupQueued &&
        driveBackupEnabled &&
        authProvider == AuthProviderType.google) {
      _driveBackupQueued = false;
      driveBackupInProgress = true;
      notifyListeners();
      try {
        await _syncDriveBackup();
        driveBackupError = null;
        driveBackupLastSyncedAt = DateTime.now().toIso8601String();
      } catch (error) {
        driveBackupError = error.toString();
      } finally {
        driveBackupInProgress = false;
        notifyListeners();
      }
    }
  }

  Future<void> _syncDriveBackup() async {
    final account =
        _googleSignIn.currentUser ?? await _googleSignIn.signInSilently();
    if (account == null) {
      throw StateError('Google account is not available.');
    }
    if (!await _hasDriveBackupAccess(account)) {
      throw StateError('Google Drive backup permission has not been granted.');
    }

    var authHeaders = await account.authHeaders;
    if (!authHeaders.containsKey('Authorization')) {
      throw StateError('Google Drive authorization is missing.');
    }

    final backupFileName =
        'deokive_backup_${_sanitizeStorageKey(accountId)}.json';
    final existingFileId = await _findDriveBackupFileId(
      authHeaders: authHeaders,
      fileName: backupFileName,
    );
    final file = await _accountStorageFile();
    if (!await file.exists()) {
      if (existingFileId != null) {
        final mediaBytes = await _downloadDriveBackup(
          authHeaders: authHeaders,
          fileId: existingFileId,
        );
        await _writeDriveBackupToLocalFile(
          localFile: file,
          mediaBytes: mediaBytes,
        );
        return;
      }
      await _saveAccountData();
    }
    final mediaBytes = await file.readAsBytes();
    try {
      await _uploadDriveBackup(
        authHeaders: authHeaders,
        fileName: backupFileName,
        mediaBytes: mediaBytes,
        existingFileId: existingFileId,
      );
    } on HttpException catch (error) {
      final message = error.message.toLowerCase();
      if (message.contains('401')) {
        await account.clearAuthCache();
        authHeaders = await account.authHeaders;
        await _uploadDriveBackup(
          authHeaders: authHeaders,
          fileName: backupFileName,
          mediaBytes: mediaBytes,
          existingFileId: existingFileId,
        );
        return;
      }
      rethrow;
    }
  }

  Future<bool> _hasDriveBackupAccess(GoogleSignInAccount account) async {
    try {
      return await _googleSignIn.canAccessScopes(
        const [_driveAppDataScope],
        accessToken: (await account.authentication).accessToken,
      );
    } catch (_) {
      return false;
    }
  }

  Future<String?> _findDriveBackupFileId({
    required Map<String, String> authHeaders,
    required String fileName,
  }) async {
    final uri = Uri.https(
      'www.googleapis.com',
      '/drive/v3/files',
      <String, String>{
        'spaces': 'appDataFolder',
        'fields': 'files(id,name)',
        'q':
            "name = '$fileName' and 'appDataFolder' in parents and trashed = false",
      },
    );
    final response = await http.get(uri, headers: authHeaders);
    if (response.statusCode != 200) {
      throw HttpException(
        'Drive file lookup failed with ${response.statusCode}: ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body) as Map<String, dynamic>;
    final files = (decoded['files'] as List<dynamic>? ?? const []);
    if (files.isEmpty) return null;
    return (files.first as Map<String, dynamic>)['id'] as String?;
  }

  Future<void> _uploadDriveBackup({
    required Map<String, String> authHeaders,
    required String fileName,
    required List<int> mediaBytes,
    String? existingFileId,
  }) async {
    final uploadUri = existingFileId == null
        ? Uri.https(
            'www.googleapis.com',
            '/upload/drive/v3/files',
            const {'uploadType': 'multipart'},
          )
        : Uri.https(
            'www.googleapis.com',
            '/upload/drive/v3/files/$existingFileId',
            const {'uploadType': 'multipart'},
          );

    final request = http.MultipartRequest(
      existingFileId == null ? 'POST' : 'PATCH',
      uploadUri,
    )..headers.addAll(authHeaders);

    final metadata = <String, dynamic>{
      'name': fileName,
      'mimeType': _driveBackupMimeType,
      if (existingFileId == null) 'parents': ['appDataFolder'],
    };

    request.files.add(
      http.MultipartFile.fromString(
        'metadata',
        jsonEncode(metadata),
        contentType: MediaType('application', 'json', {'charset': 'utf-8'}),
      ),
    );
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        mediaBytes,
        filename: fileName,
        contentType: MediaType('application', 'json'),
      ),
    );

    final response = await request.send();
    final body = await response.stream.bytesToString();
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw HttpException(
        'Drive upload failed with ${response.statusCode}: $body',
      );
    }
  }

  Future<List<int>> _downloadDriveBackup({
    required Map<String, String> authHeaders,
    required String fileId,
  }) async {
    final uri = Uri.https(
      'www.googleapis.com',
      '/drive/v3/files/$fileId',
      const {'alt': 'media'},
    );
    final response = await http.get(uri, headers: authHeaders);
    if (response.statusCode != 200) {
      throw HttpException(
        'Drive download failed with ${response.statusCode}: ${response.body}',
      );
    }
    return response.bodyBytes;
  }

  Future<void> _writeDriveBackupToLocalFile({
    required File localFile,
    required List<int> mediaBytes,
  }) async {
    final decoded = utf8.decode(mediaBytes);
    jsonDecode(decoded) as Map<String, dynamic>;
    await localFile.writeAsBytes(mediaBytes, flush: true);
  }

  Uri? _serverUri(String path) {
    final baseUrl = AppServerConfig.serverBaseUrl;
    if (baseUrl == null) return null;
    return Uri.parse('$baseUrl$path');
  }

  Map<String, String> _jsonHeaders({bool includeAuth = false}) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (includeAuth && (serverAccessToken ?? '').isNotEmpty) {
      headers['Authorization'] = 'Bearer $serverAccessToken';
    }
    return headers;
  }

  void _showSyncDialog(String message) {
    syncDialogVisible = true;
    syncStatusMessage = message;
    notifyListeners();
  }

  void _hideSyncDialog() {
    syncDialogVisible = false;
    syncStatusMessage = null;
    notifyListeners();
  }

  Future<Map<String, dynamic>> _readServerJson(http.Response response) async {
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    return Map<String, dynamic>.from(decoded as Map);
  }

  Future<Map<String, dynamic>> _fetchRemoteProfile() async {
    final uri = _serverUri('/me');
    if (uri == null) {
      throw StateError('Server base URL is not configured.');
    }
    final response = await http.get(uri, headers: _jsonHeaders(includeAuth: true));
    if (response.statusCode != 200) {
      throw HttpException('Profile fetch failed with ${response.statusCode}.');
    }
    return _readServerJson(response);
  }

  Future<void> _loadServerBackupSnapshotIfNeeded() async {
    pendingRestoreSnapshot = null;
    localServerBackupError = null;
    _serverBackupPromptDismissed = false;

    if (!canUseServerBackups || (serverAccessToken ?? '').isEmpty) {
      return;
    }

    final localFile = await _accountStorageFile();
    if (await localFile.exists()) {
      return;
    }

    final uri = _serverUri('/backup/snapshot');
    if (uri == null) return;

    final response = await http.get(uri, headers: _jsonHeaders(includeAuth: true));
    if (response.statusCode == 404) {
      return;
    }
    if (response.statusCode != 200) {
      localServerBackupError =
          'server_backup_lookup_${response.statusCode.toString()}';
      return;
    }

    final json = await _readServerJson(response);
    final uploadedAt = json['uploaded_at']?.toString() ?? '';
    pendingRestoreSnapshot = BackupSnapshotInfo(
      source: 'server',
      uploadedAt: uploadedAt,
      payloadBytes: json['payload_bytes'] as int?,
    );
  }

  Future<bool> restorePendingServerBackup() async {
    if (!canUseServerBackups || pendingRestoreSnapshot == null) return false;

    final uri = _serverUri('/backup/snapshot');
    if (uri == null) return false;

    _showSyncDialog('서버 백업에서 데이터를 불러오는 중입니다.');
    try {
      localServerBackupInProgress = true;
      notifyListeners();
      final response =
          await http.get(uri, headers: _jsonHeaders(includeAuth: true));
      if (response.statusCode != 200) {
        localServerBackupError =
            'server_backup_restore_${response.statusCode.toString()}';
        return false;
      }
      final json = await _readServerJson(response);
      final payload = Map<String, dynamic>.from(json['payload'] as Map);
      final file = await _accountStorageFile();
      await _writeAccountPayloadToFile(file, payload);
      await _loadAccountData();
      localServerBackupLastSyncedAt =
          json['uploaded_at']?.toString() ?? DateTime.now().toIso8601String();
      pendingRestoreSnapshot = null;
      _serverBackupPromptDismissed = false;
      await _persistStorageValues();
      return true;
    } catch (_) {
      localServerBackupError = 'server_backup_restore_failed';
      return false;
    } finally {
      localServerBackupInProgress = false;
      _hideSyncDialog();
    }
  }

  Future<void> dismissPendingServerBackup() async {
    pendingRestoreSnapshot = null;
    _serverBackupPromptDismissed = true;
    await _persistStorageValues();
    notifyListeners();
  }

  Future<bool> uploadLocalBackupToServer() async {
    if (!canUseServerBackups || (serverAccessToken ?? '').isEmpty) {
      return false;
    }

    final uri = _serverUri('/backup/snapshot');
    if (uri == null) return false;

    _showSyncDialog('임시 서버 백업을 업로드하는 중입니다.');
    try {
      localServerBackupInProgress = true;
      localServerBackupError = null;
      notifyListeners();

      final payload = _buildAccountPayload();
      final response = await http.put(
        uri,
        headers: _jsonHeaders(includeAuth: true),
        body: jsonEncode(<String, dynamic>{
          'payload': payload,
          'source': 'manual_local_backup',
        }),
      );
      if (response.statusCode != 200) {
        localServerBackupError =
            'server_backup_upload_${response.statusCode.toString()}';
        return false;
      }
      final json = await _readServerJson(response);
      localServerBackupLastSyncedAt =
          json['uploaded_at']?.toString() ?? DateTime.now().toIso8601String();
      return true;
    } catch (_) {
      localServerBackupError = 'server_backup_upload_failed';
      return false;
    } finally {
      localServerBackupInProgress = false;
      _hideSyncDialog();
      notifyListeners();
    }
  }

  Map<String, dynamic>? _findLocalAccount(String id) {
    for (final account in _localAccounts) {
      if (account['id'] == id) {
        return account;
      }
    }
    return null;
  }

  Future<bool> signInLocal({
    required String id,
    required String password,
  }) async {
    await _ensureStorageReady();
    final normalizedId = id.trim();

    if (AppServerConfig.isConfigured) {
      final uri = _serverUri('/auth/login');
      if (uri != null) {
        _showSyncDialog('계정 정보를 확인하는 중입니다.');
        try {
          final response = await http.post(
            uri,
            headers: _jsonHeaders(),
            body: jsonEncode(<String, dynamic>{
              'login_id': normalizedId,
              'password': password,
            }),
          );
          if (response.statusCode == 200) {
            final tokenJson = await _readServerJson(response);
            serverAccessToken = tokenJson['access_token']?.toString();
            final profile = await _fetchRemoteProfile();

            isLoggedIn = true;
            isGoogleLinked = false;
            authProvider = AuthProviderType.local;
            driveBackupEnabled = false;
            displayName = profile['nickname']?.toString() ?? 'Deokive User';
            accountId = profile['login_id']?.toString() ?? normalizedId;
            tag = profile['tag']?.toString() ?? _allocateTag();
            profileImageUrl = profile['profile_image_url'] as String?;
            profileImageBytes = null;

            await _persistAuthSession();
            await _loadAccountData();
            await _loadServerBackupSnapshotIfNeeded();
            notifyListeners();
            return true;
          }
        } catch (_) {
          localServerBackupError = 'server_login_failed';
        } finally {
          _hideSyncDialog();
        }
      }
    }

    final account = _findLocalAccount(normalizedId);
    if (account == null) return false;
    if (account['password'] != password) return false;

    isLoggedIn = true;
    isGoogleLinked = false;
    authProvider = AuthProviderType.local;
    driveBackupEnabled = false;
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
    final normalizedId = id.trim();

    if (AppServerConfig.isConfigured) {
      final uri = _serverUri('/auth/signup');
      if (uri != null) {
        _showSyncDialog('계정을 생성하는 중입니다.');
        try {
          final response = await http.post(
            uri,
            headers: _jsonHeaders(),
            body: jsonEncode(<String, dynamic>{
              'login_id': normalizedId,
              'password': password,
              'nickname': nickname.trim(),
            }),
          );
          if (response.statusCode == 201) {
            final tokenJson = await _readServerJson(response);
            serverAccessToken = tokenJson['access_token']?.toString();
            final profile = await _fetchRemoteProfile();

            isLoggedIn = true;
            isGoogleLinked = false;
            authProvider = AuthProviderType.local;
            driveBackupEnabled = false;
            displayName = profile['nickname']?.toString() ?? nickname.trim();
            accountId = profile['login_id']?.toString() ?? normalizedId;
            tag = profile['tag']?.toString() ?? _allocateTag();
            profileImageBytes = null;
            profileImageUrl = profile['profile_image_url'] as String?;
            await _persistAuthSession();
            await _saveAccountData();
            notifyListeners();
            return true;
          }
          return false;
        } catch (_) {
          localServerBackupError = 'server_signup_failed';
          return false;
        } finally {
          _hideSyncDialog();
        }
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
    serverAccessToken = null;
    profileImageBytes = null;
    profileImageUrl = null;
    await _persistAuthSession();
    await _saveAccountData();
    notifyListeners();
    return true;
  }

  Future<void> signOut() async {
    try {
      if (authProvider == AuthProviderType.google) {
        await _googleSignIn.signOut();
      }
    } catch (_) {}

    isLoggedIn = false;
    isGoogleLinked = false;
    driveBackupEnabled = false;
    driveBackupInProgress = false;
    driveBackupLastSyncedAt = null;
    driveBackupError = null;
    syncDialogVisible = false;
    syncStatusMessage = null;
    localServerBackupInProgress = false;
    localServerBackupLastSyncedAt = null;
    localServerBackupError = null;
    pendingRestoreSnapshot = null;
    serverAccessToken = null;
    _serverBackupPromptDismissed = false;
    authProvider = AuthProviderType.guest;
    displayName = 'Guest';
    accountId = '로그인이 필요합니다';
    tag = '@guest';
    profileImageBytes = null;
    profileImageUrl = null;
    _resetAvatarSelection();
    await _clearPersistedAuthSession();
    await _loadAccountData();
    notifyListeners();
  }

  bool setProfile({
    required String name,
    required String handle,
    String? id,
    Uint8List? imageBytes,
  }) {
    if (!canEditProfile) return false;

    final normalizedTag = handle.startsWith('@') ? handle.substring(1) : handle;
    if (!isValidTagText(normalizedTag)) {
      return false;
    }

    displayName = name.trim().isEmpty ? displayName : name.trim();
    tag = '@$normalizedTag';

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

      if (canUseServerBackups && (serverAccessToken ?? '').isNotEmpty) {
        final uri = _serverUri('/me');
        if (uri != null) {
          http
              .patch(
                uri,
                headers: _jsonHeaders(includeAuth: true),
                body: jsonEncode(<String, dynamic>{
                  'nickname': displayName,
                  'tag': tag,
                  'profile_image_url': profileImageUrl,
                }),
              )
              .catchError((_) {});
        }
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
    int? faceType,
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
    avatarFaceType = faceType ?? avatarFaceType;
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

  void _resetAvatarSelection() {
    avatarBodyType = -1;
    avatarBackgroundType = -1;
    avatarFaceType = -1;
    avatarHairStyle = -1;
    avatarHairColorIndex = 0;
    avatarAccentColorIndex = 0;
    avatarOutfitColorIndex = -1;
    avatarSkinToneIndex = -1;
    avatarHasHat = false;
    avatarHasCape = false;
    avatarHasHandheld = false;
    avatarHasBackRibbon = false;
  }

  Uint8List? _decodeImageBytes(Object? raw) {
    if (raw is Uint8List) return raw;
    if (raw is List<int>) return Uint8List.fromList(raw);
    if (raw is List<dynamic>) {
      final numbers = raw.whereType<num>().map((item) => item.toInt()).toList();
      return Uint8List.fromList(numbers);
    }
    if (raw is String && raw.isNotEmpty) {
      try {
        return base64Decode(raw);
      } catch (_) {
        return null;
      }
    }
    return null;
  }

  void addFolder(FolderItem folder) {
    if (folder.parentId == null && !canCreateMoreFolders) return;
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
    if (!canCreateMoreGoods) return;
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
    }

    return copied;
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

  int get maxFreeFolderCount => 2;

  int get maxFreeGoodsCount => 50;

  int get maxBadgeSlots => 3;

  int get topLevelFolderCount =>
      folders.where((folder) => folder.parentId == null).length;

  int get remainingFolderSlots =>
      isFeatureUnlocked(PremiumFeature.unlimitedFolders)
          ? -1
          : maxFreeFolderCount - topLevelFolderCount;

  int get remainingGoodsSlots =>
      isFeatureUnlocked(PremiumFeature.unlimitedGoods)
          ? -1
          : maxFreeGoodsCount - goodsItems.length;

  bool get canCreateMoreFolders =>
      isFeatureUnlocked(PremiumFeature.unlimitedFolders) ||
      topLevelFolderCount < maxFreeFolderCount;

  bool get canCreateMoreGoods =>
      isFeatureUnlocked(PremiumFeature.unlimitedGoods) ||
      goodsItems.length < maxFreeGoodsCount;

  bool isFeatureUnlocked(PremiumFeature feature) {
    switch (feature) {
      case PremiumFeature.unlimitedFolders:
      case PremiumFeature.unlimitedGoods:
      case PremiumFeature.multiDeviceSync:
        return premiumEnabled;
      case PremiumFeature.driveBackup:
        return driveBackupEnabled || premiumEnabled;
      case PremiumFeature.adFree:
        return adsRemoved || premiumEnabled;
    }
  }

  bool shouldShowAd(AdPlacement placement) {
    if (!debugAdsEnabled) {
      return false;
    }
    if (isFeatureUnlocked(PremiumFeature.adFree)) {
      return false;
    }
    switch (placement) {
      case AdPlacement.homeBanner:
      case AdPlacement.folderInterstitial:
      case AdPlacement.newsFeedBanner:
      case AdPlacement.calendarBanner:
        return true;
    }
  }

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

  void setPremiumEnabled(bool value) {
    premiumEnabled = value;
    if (!premiumEnabled &&
        !adsRemoved &&
        equippedBadgeIds.length > maxBadgeSlots) {
      equippedBadgeIds.removeRange(maxBadgeSlots, equippedBadgeIds.length);
    }
    _persistStorageValues();
    _saveAccountData();
    notifyListeners();
  }

  void setAdsRemoved(bool value) {
    adsRemoved = value;
    _persistStorageValues();
    _saveAccountData();
    notifyListeners();
  }

  void setDebugAdsEnabled(bool value) {
    debugAdsEnabled = value;
    _persistStorageValues();
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
    }
  }
}
