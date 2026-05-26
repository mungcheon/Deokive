import 'app_language.dart';
import 'generated/app_localizations.dart';

/// Compat wrapper over the gen_l10n [AppLocalizations] class.
///
/// Existing call sites use `AppStrings.of(language).keyName` without a
/// BuildContext. We preserve that surface here and forward each getter to the
/// generated localization for the matching locale, so all new strings should
/// be added to `app_ko.arb` / `app_en.arb` and a one-line forward added below.
class AppStrings {
  final AppLanguage language;

  AppStrings(this.language);

  static AppStrings of(AppLanguage language) => AppStrings(language);

  AppLocalizations get _l => lookupAppLocalizations(language.locale);

  String get home => _l.home;
  String get board => _l.board;
  String get folders => _l.folders;
  String get calendar => _l.calendar;
  String get settings => _l.settings;

  String get homeSectionNotice => _l.homeSectionNotice;
  String get homeSectionGoodsNews => _l.homeSectionGoodsNews;
  String get homeSectionEvent => _l.homeSectionEvent;
  String get boardSectionFreeTalk => _l.boardSectionFreeTalk;
  String get boardSectionTrade => _l.boardSectionTrade;
  String get boardSectionEventSchedule => _l.boardSectionEventSchedule;
  String get boardNewPost => _l.boardNewPost;
  String get boardEmptyState => _l.boardEmptyState;
  String get boardComingSoon => _l.boardComingSoon;

  String get languageLabel => _l.languageLabel;
  String get languageHelp => _l.languageHelp;
  String get korean => _l.korean;
  String get english => _l.english;

  String get guest => _l.guest;
  String get loginRequiredAccountId => _l.loginRequiredAccountId;
  String get authGuest => _l.authGuest;
  String get authLocal => _l.authLocal;
  String get authGoogle => _l.authGoogle;

  String get defaultFolderName => _l.defaultFolderName;
  String get sortByName => _l.sortByName;
  String get sortByGoodsCount => _l.sortByGoodsCount;
  String get sortByPriceLow => _l.sortByPriceLow;
  String get sortByPriceHigh => _l.sortByPriceHigh;
  String get sortBySeries => _l.sortBySeries;
  String get sortByNewestPurchase => _l.sortByNewestPurchase;
  String get sortByOldestPurchase => _l.sortByOldestPurchase;

  String get backupStatusLoggedOut => _l.backupStatusLoggedOut;
  String get backupStatusGoogle => _l.backupStatusGoogle;
  String get backupStatusLocal => _l.backupStatusLocal;

  String get googleUnsupported => _l.googleUnsupported;
  String get googleNotConfigured => _l.googleNotConfigured;
  String get googleConfigError => _l.googleConfigError;
  String get googleInitializing => _l.googleInitializing;
  String get googleBackupEnabled => _l.googleBackupEnabled;
  String get googleAccountIdLocked => _l.googleAccountIdLocked;
  String get accountIdHelp => _l.accountIdHelp;
  String get tagHelp => _l.tagHelp;
  String get profileSaveError => _l.profileSaveError;

  String get todayRecommendation => _l.todayRecommendation;
  String get close => _l.close;

  String get cameraCapture => _l.cameraCapture;
  String get chooseFromLibrary => _l.chooseFromLibrary;
  String get editProfile => _l.editProfile;
  String get displayName => _l.displayName;
  String get accountId => _l.accountId;
  String get tag => _l.tag;
  String get cancel => _l.cancel;
  String get save => _l.save;
  String get login => _l.login;
  String get loginWithGoogle => _l.loginWithGoogle;
  String get signOut => _l.signOut;
  String get theme => _l.theme;
  String get darkMode => _l.darkMode;
  String get pushEnabled => _l.pushEnabled;
  String get support => _l.support;

  String get homeSectionBanner => _l.homeSectionBanner;
  String get homeSectionNews => _l.homeSectionNews;
  String get homeBadgeShowcase => _l.homeBadgeShowcase;
  String get noEquippedBadges => _l.noEquippedBadges;
  String get folderCountLabel => _l.folderCountLabel;
  String get goodsCountLabel => _l.goodsCountLabel;
  String get badgeCountLabel => _l.badgeCountLabel;
}
