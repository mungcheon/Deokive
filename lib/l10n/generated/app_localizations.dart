import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ja.dart';
import 'app_localizations_ko.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'generated/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ja'),
    Locale('ko'),
    Locale('zh'),
    Locale.fromSubtags(languageCode: 'zh', scriptCode: 'Hans'),
    Locale.fromSubtags(languageCode: 'zh', scriptCode: 'Hant')
  ];

  /// No description provided for @home.
  ///
  /// In ko, this message translates to:
  /// **'홈'**
  String get home;

  /// No description provided for @board.
  ///
  /// In ko, this message translates to:
  /// **'게시판'**
  String get board;

  /// No description provided for @folders.
  ///
  /// In ko, this message translates to:
  /// **'폴더'**
  String get folders;

  /// No description provided for @calendar.
  ///
  /// In ko, this message translates to:
  /// **'캘린더'**
  String get calendar;

  /// No description provided for @settings.
  ///
  /// In ko, this message translates to:
  /// **'설정'**
  String get settings;

  /// No description provided for @homeSectionNotice.
  ///
  /// In ko, this message translates to:
  /// **'공지'**
  String get homeSectionNotice;

  /// No description provided for @homeSectionGoodsNews.
  ///
  /// In ko, this message translates to:
  /// **'굿즈 소식'**
  String get homeSectionGoodsNews;

  /// No description provided for @homeSectionEvent.
  ///
  /// In ko, this message translates to:
  /// **'이벤트'**
  String get homeSectionEvent;

  /// No description provided for @boardSectionFreeTalk.
  ///
  /// In ko, this message translates to:
  /// **'자유 게시판'**
  String get boardSectionFreeTalk;

  /// No description provided for @boardSectionTrade.
  ///
  /// In ko, this message translates to:
  /// **'거래 게시판'**
  String get boardSectionTrade;

  /// No description provided for @boardSectionEventSchedule.
  ///
  /// In ko, this message translates to:
  /// **'행사 일정'**
  String get boardSectionEventSchedule;

  /// No description provided for @boardNewPost.
  ///
  /// In ko, this message translates to:
  /// **'새 글 쓰기'**
  String get boardNewPost;

  /// No description provided for @boardEmptyState.
  ///
  /// In ko, this message translates to:
  /// **'아직 등록된 글이 없습니다.'**
  String get boardEmptyState;

  /// No description provided for @boardComingSoon.
  ///
  /// In ko, this message translates to:
  /// **'게시판 기능은 곧 열립니다.'**
  String get boardComingSoon;

  /// No description provided for @languageLabel.
  ///
  /// In ko, this message translates to:
  /// **'언어'**
  String get languageLabel;

  /// No description provided for @languageHelp.
  ///
  /// In ko, this message translates to:
  /// **'앱에 표시할 언어를 선택하세요.'**
  String get languageHelp;

  /// No description provided for @korean.
  ///
  /// In ko, this message translates to:
  /// **'한국어'**
  String get korean;

  /// No description provided for @english.
  ///
  /// In ko, this message translates to:
  /// **'English'**
  String get english;

  /// No description provided for @japanese.
  ///
  /// In ko, this message translates to:
  /// **'日本語'**
  String get japanese;

  /// No description provided for @chineseSimplified.
  ///
  /// In ko, this message translates to:
  /// **'简体中文'**
  String get chineseSimplified;

  /// No description provided for @chineseTraditional.
  ///
  /// In ko, this message translates to:
  /// **'繁體中文'**
  String get chineseTraditional;

  /// No description provided for @guest.
  ///
  /// In ko, this message translates to:
  /// **'게스트'**
  String get guest;

  /// No description provided for @loginRequiredAccountId.
  ///
  /// In ko, this message translates to:
  /// **'로그인이 필요합니다'**
  String get loginRequiredAccountId;

  /// No description provided for @authGuest.
  ///
  /// In ko, this message translates to:
  /// **'게스트'**
  String get authGuest;

  /// No description provided for @authLocal.
  ///
  /// In ko, this message translates to:
  /// **'일반 계정'**
  String get authLocal;

  /// No description provided for @authGoogle.
  ///
  /// In ko, this message translates to:
  /// **'구글 계정'**
  String get authGoogle;

  /// No description provided for @defaultFolderName.
  ///
  /// In ko, this message translates to:
  /// **'기본 폴더'**
  String get defaultFolderName;

  /// No description provided for @wishlistFolderName.
  ///
  /// In ko, this message translates to:
  /// **'위시리스트'**
  String get wishlistFolderName;

  /// No description provided for @sortByName.
  ///
  /// In ko, this message translates to:
  /// **'이름순'**
  String get sortByName;

  /// No description provided for @sortByGoodsCount.
  ///
  /// In ko, this message translates to:
  /// **'굿즈 많은 순'**
  String get sortByGoodsCount;

  /// No description provided for @sortByPriceLow.
  ///
  /// In ko, this message translates to:
  /// **'가격 낮은 순'**
  String get sortByPriceLow;

  /// No description provided for @sortByPriceHigh.
  ///
  /// In ko, this message translates to:
  /// **'가격 높은 순'**
  String get sortByPriceHigh;

  /// No description provided for @sortBySeries.
  ///
  /// In ko, this message translates to:
  /// **'시리즈순'**
  String get sortBySeries;

  /// No description provided for @sortByCharacter.
  ///
  /// In ko, this message translates to:
  /// **'캐릭터순'**
  String get sortByCharacter;

  /// No description provided for @sortByCategory.
  ///
  /// In ko, this message translates to:
  /// **'카테고리순'**
  String get sortByCategory;

  /// No description provided for @sortByNewestPurchase.
  ///
  /// In ko, this message translates to:
  /// **'구매일 최신순'**
  String get sortByNewestPurchase;

  /// No description provided for @sortByOldestPurchase.
  ///
  /// In ko, this message translates to:
  /// **'구매일 오래된 순'**
  String get sortByOldestPurchase;

  /// No description provided for @sortByNewestRelease.
  ///
  /// In ko, this message translates to:
  /// **'발매일 최신순'**
  String get sortByNewestRelease;

  /// No description provided for @sortByOldestRelease.
  ///
  /// In ko, this message translates to:
  /// **'발매일 오래된 순'**
  String get sortByOldestRelease;

  /// No description provided for @sortByQuantity.
  ///
  /// In ko, this message translates to:
  /// **'수량 많은 순'**
  String get sortByQuantity;

  /// No description provided for @sortByFavorites.
  ///
  /// In ko, this message translates to:
  /// **'즐겨찾기 우선'**
  String get sortByFavorites;

  /// No description provided for @purchaseStateWished.
  ///
  /// In ko, this message translates to:
  /// **'위시'**
  String get purchaseStateWished;

  /// No description provided for @purchaseStateOrdered.
  ///
  /// In ko, this message translates to:
  /// **'주문함'**
  String get purchaseStateOrdered;

  /// No description provided for @purchaseStateArrived.
  ///
  /// In ko, this message translates to:
  /// **'도착'**
  String get purchaseStateArrived;

  /// No description provided for @purchaseStateOwned.
  ///
  /// In ko, this message translates to:
  /// **'보유 중'**
  String get purchaseStateOwned;

  /// No description provided for @markAsPurchased.
  ///
  /// In ko, this message translates to:
  /// **'구매 완료로 표시'**
  String get markAsPurchased;

  /// No description provided for @moveToOwnedFolder.
  ///
  /// In ko, this message translates to:
  /// **'보유 폴더로 이동'**
  String get moveToOwnedFolder;

  /// No description provided for @addToWishlist.
  ///
  /// In ko, this message translates to:
  /// **'위시리스트에 추가'**
  String get addToWishlist;

  /// No description provided for @currencyKrw.
  ///
  /// In ko, this message translates to:
  /// **'원 (KRW)'**
  String get currencyKrw;

  /// No description provided for @currencyUsd.
  ///
  /// In ko, this message translates to:
  /// **'달러 (USD)'**
  String get currencyUsd;

  /// No description provided for @currencyJpy.
  ///
  /// In ko, this message translates to:
  /// **'엔 (JPY)'**
  String get currencyJpy;

  /// No description provided for @currencyEur.
  ///
  /// In ko, this message translates to:
  /// **'유로 (EUR)'**
  String get currencyEur;

  /// No description provided for @currencyCny.
  ///
  /// In ko, this message translates to:
  /// **'위안 (CNY)'**
  String get currencyCny;

  /// No description provided for @tapToChangeCurrency.
  ///
  /// In ko, this message translates to:
  /// **'탭하여 통화 변경'**
  String get tapToChangeCurrency;

  /// No description provided for @categoryFigure.
  ///
  /// In ko, this message translates to:
  /// **'피규어'**
  String get categoryFigure;

  /// No description provided for @categoryPlush.
  ///
  /// In ko, this message translates to:
  /// **'봉제 인형'**
  String get categoryPlush;

  /// No description provided for @categoryPoster.
  ///
  /// In ko, this message translates to:
  /// **'포스터'**
  String get categoryPoster;

  /// No description provided for @categoryCard.
  ///
  /// In ko, this message translates to:
  /// **'카드'**
  String get categoryCard;

  /// No description provided for @categoryBadge.
  ///
  /// In ko, this message translates to:
  /// **'뱃지'**
  String get categoryBadge;

  /// No description provided for @categoryKeyring.
  ///
  /// In ko, this message translates to:
  /// **'키링'**
  String get categoryKeyring;

  /// No description provided for @categorySticker.
  ///
  /// In ko, this message translates to:
  /// **'스티커'**
  String get categorySticker;

  /// No description provided for @categoryStandee.
  ///
  /// In ko, this message translates to:
  /// **'스탠디'**
  String get categoryStandee;

  /// No description provided for @categoryPhotoCard.
  ///
  /// In ko, this message translates to:
  /// **'포토카드'**
  String get categoryPhotoCard;

  /// No description provided for @categoryArtBook.
  ///
  /// In ko, this message translates to:
  /// **'아트북'**
  String get categoryArtBook;

  /// No description provided for @categoryClothing.
  ///
  /// In ko, this message translates to:
  /// **'의류'**
  String get categoryClothing;

  /// No description provided for @categoryAccessory.
  ///
  /// In ko, this message translates to:
  /// **'액세서리'**
  String get categoryAccessory;

  /// No description provided for @categoryOther.
  ///
  /// In ko, this message translates to:
  /// **'기타'**
  String get categoryOther;

  /// No description provided for @totalGoodsCount.
  ///
  /// In ko, this message translates to:
  /// **'전체 굿즈'**
  String get totalGoodsCount;

  /// No description provided for @totalSpending.
  ///
  /// In ko, this message translates to:
  /// **'구매 비용'**
  String get totalSpending;

  /// No description provided for @exportCsv.
  ///
  /// In ko, this message translates to:
  /// **'CSV 내보내기'**
  String get exportCsv;

  /// No description provided for @csvExportedMessage.
  ///
  /// In ko, this message translates to:
  /// **'굿즈 목록을 CSV로 저장했습니다.'**
  String get csvExportedMessage;

  /// No description provided for @csvExportFailed.
  ///
  /// In ko, this message translates to:
  /// **'CSV 내보내기에 실패했습니다.'**
  String get csvExportFailed;

  /// No description provided for @characterChartTitle.
  ///
  /// In ko, this message translates to:
  /// **'캐릭터별 굿즈 수'**
  String get characterChartTitle;

  /// No description provided for @categoryChartTitle.
  ///
  /// In ko, this message translates to:
  /// **'카테고리별 굿즈 수'**
  String get categoryChartTitle;

  /// No description provided for @noChartData.
  ///
  /// In ko, this message translates to:
  /// **'아직 표시할 데이터가 없습니다.'**
  String get noChartData;

  /// No description provided for @autocompleteHint.
  ///
  /// In ko, this message translates to:
  /// **'기존 입력값 검색 또는 새로 입력'**
  String get autocompleteHint;

  /// No description provided for @addNewValue.
  ///
  /// In ko, this message translates to:
  /// **'새로 추가'**
  String get addNewValue;

  /// No description provided for @releaseDateLabel.
  ///
  /// In ko, this message translates to:
  /// **'발매일'**
  String get releaseDateLabel;

  /// No description provided for @characterNameLabel.
  ///
  /// In ko, this message translates to:
  /// **'캐릭터'**
  String get characterNameLabel;

  /// No description provided for @selectDate.
  ///
  /// In ko, this message translates to:
  /// **'날짜 선택'**
  String get selectDate;

  /// No description provided for @backupStatusLoggedOut.
  ///
  /// In ko, this message translates to:
  /// **'로그인 후 백업 상태를 확인할 수 있습니다.'**
  String get backupStatusLoggedOut;

  /// No description provided for @backupStatusGoogle.
  ///
  /// In ko, this message translates to:
  /// **'개인 Google Drive 백업을 사용할 수 있습니다.'**
  String get backupStatusGoogle;

  /// No description provided for @backupStatusLocal.
  ///
  /// In ko, this message translates to:
  /// **'일반 계정은 추후 클라우드 백업을 지원할 예정입니다.'**
  String get backupStatusLocal;

  /// No description provided for @googleUnsupported.
  ///
  /// In ko, this message translates to:
  /// **'현재 플랫폼에서는 구글 로그인을 지원하지 않습니다.'**
  String get googleUnsupported;

  /// No description provided for @googleNotConfigured.
  ///
  /// In ko, this message translates to:
  /// **'구글 로그인 설정이 아직 완료되지 않았습니다.'**
  String get googleNotConfigured;

  /// No description provided for @googleConfigError.
  ///
  /// In ko, this message translates to:
  /// **'구글 로그인 설정이 완료되지 않았거나 인증에 실패했습니다. Android 패키지명과 SHA-1, iOS Client ID와 URL Scheme 설정을 확인하세요.'**
  String get googleConfigError;

  /// No description provided for @googleInitializing.
  ///
  /// In ko, this message translates to:
  /// **'구글 로그인을 초기화하는 중입니다.'**
  String get googleInitializing;

  /// No description provided for @googleBackupEnabled.
  ///
  /// In ko, this message translates to:
  /// **'구글 계정으로 로그인하면 계정 정보와 프로필 사진을 가져오고 Google Drive 백업을 준비할 수 있습니다.'**
  String get googleBackupEnabled;

  /// No description provided for @googleAccountIdLocked.
  ///
  /// In ko, this message translates to:
  /// **'구글 로그인 계정은 아이디를 변경할 수 없습니다.'**
  String get googleAccountIdLocked;

  /// No description provided for @accountIdHelp.
  ///
  /// In ko, this message translates to:
  /// **'영문과 숫자만 사용할 수 있습니다.'**
  String get accountIdHelp;

  /// No description provided for @tagHelp.
  ///
  /// In ko, this message translates to:
  /// **'영문과 숫자만 사용할 수 있고 띄어쓰기는 지원하지 않습니다.'**
  String get tagHelp;

  /// No description provided for @profileSaveError.
  ///
  /// In ko, this message translates to:
  /// **'프로필 정보를 저장할 수 없습니다. 태그와 아이디 형식을 확인해주세요.'**
  String get profileSaveError;

  /// No description provided for @todayRecommendation.
  ///
  /// In ko, this message translates to:
  /// **'오늘의 추천'**
  String get todayRecommendation;

  /// No description provided for @close.
  ///
  /// In ko, this message translates to:
  /// **'닫기'**
  String get close;

  /// No description provided for @cameraCapture.
  ///
  /// In ko, this message translates to:
  /// **'카메라로 촬영'**
  String get cameraCapture;

  /// No description provided for @chooseFromLibrary.
  ///
  /// In ko, this message translates to:
  /// **'앨범에서 선택'**
  String get chooseFromLibrary;

  /// No description provided for @editProfile.
  ///
  /// In ko, this message translates to:
  /// **'프로필 수정'**
  String get editProfile;

  /// No description provided for @displayName.
  ///
  /// In ko, this message translates to:
  /// **'닉네임'**
  String get displayName;

  /// No description provided for @accountId.
  ///
  /// In ko, this message translates to:
  /// **'아이디'**
  String get accountId;

  /// No description provided for @tag.
  ///
  /// In ko, this message translates to:
  /// **'태그'**
  String get tag;

  /// No description provided for @cancel.
  ///
  /// In ko, this message translates to:
  /// **'취소'**
  String get cancel;

  /// No description provided for @save.
  ///
  /// In ko, this message translates to:
  /// **'저장'**
  String get save;

  /// No description provided for @login.
  ///
  /// In ko, this message translates to:
  /// **'로그인'**
  String get login;

  /// No description provided for @loginWithGoogle.
  ///
  /// In ko, this message translates to:
  /// **'구글로 로그인'**
  String get loginWithGoogle;

  /// No description provided for @signOut.
  ///
  /// In ko, this message translates to:
  /// **'로그아웃'**
  String get signOut;

  /// No description provided for @theme.
  ///
  /// In ko, this message translates to:
  /// **'테마'**
  String get theme;

  /// No description provided for @darkMode.
  ///
  /// In ko, this message translates to:
  /// **'다크 모드'**
  String get darkMode;

  /// No description provided for @pushEnabled.
  ///
  /// In ko, this message translates to:
  /// **'알림 받기'**
  String get pushEnabled;

  /// No description provided for @support.
  ///
  /// In ko, this message translates to:
  /// **'문의하기'**
  String get support;

  /// No description provided for @homeSectionBanner.
  ///
  /// In ko, this message translates to:
  /// **'추천 배너'**
  String get homeSectionBanner;

  /// No description provided for @homeSectionNews.
  ///
  /// In ko, this message translates to:
  /// **'소식'**
  String get homeSectionNews;

  /// No description provided for @homeBadgeShowcase.
  ///
  /// In ko, this message translates to:
  /// **'배지 전시대'**
  String get homeBadgeShowcase;

  /// No description provided for @noEquippedBadges.
  ///
  /// In ko, this message translates to:
  /// **'아직 장착한 배지가 없습니다.'**
  String get noEquippedBadges;

  /// No description provided for @folderCountLabel.
  ///
  /// In ko, this message translates to:
  /// **'폴더'**
  String get folderCountLabel;

  /// No description provided for @goodsCountLabel.
  ///
  /// In ko, this message translates to:
  /// **'굿즈'**
  String get goodsCountLabel;

  /// No description provided for @badgeCountLabel.
  ///
  /// In ko, this message translates to:
  /// **'배지'**
  String get badgeCountLabel;

  /// No description provided for @inquiryCategoryGeneral.
  ///
  /// In ko, this message translates to:
  /// **'일반 문의'**
  String get inquiryCategoryGeneral;

  /// No description provided for @inquiryCategoryBug.
  ///
  /// In ko, this message translates to:
  /// **'버그 제보'**
  String get inquiryCategoryBug;

  /// No description provided for @inquiryCategoryAccount.
  ///
  /// In ko, this message translates to:
  /// **'계정 문의'**
  String get inquiryCategoryAccount;

  /// No description provided for @inquiryCategoryPayment.
  ///
  /// In ko, this message translates to:
  /// **'결제 문의'**
  String get inquiryCategoryPayment;

  /// No description provided for @inquiryCategoryFeature.
  ///
  /// In ko, this message translates to:
  /// **'기능 제안'**
  String get inquiryCategoryFeature;

  /// No description provided for @inquiryCategoryLabel.
  ///
  /// In ko, this message translates to:
  /// **'문의 카테고리'**
  String get inquiryCategoryLabel;

  /// No description provided for @inquiryTitleLabel.
  ///
  /// In ko, this message translates to:
  /// **'제목'**
  String get inquiryTitleLabel;

  /// No description provided for @inquiryTitleRequired.
  ///
  /// In ko, this message translates to:
  /// **'제목을 입력해 주세요.'**
  String get inquiryTitleRequired;

  /// No description provided for @inquiryContentLabel.
  ///
  /// In ko, this message translates to:
  /// **'문의 내용'**
  String get inquiryContentLabel;

  /// No description provided for @inquiryContentRequired.
  ///
  /// In ko, this message translates to:
  /// **'문의 내용을 입력해 주세요.'**
  String get inquiryContentRequired;

  /// No description provided for @supportFormHeader.
  ///
  /// In ko, this message translates to:
  /// **'문의 메일 작성'**
  String get supportFormHeader;

  /// No description provided for @supportFormDescription.
  ///
  /// In ko, this message translates to:
  /// **'문의 내용을 작성하면 deokivecs@gmail.com으로 메일 작성 화면이 열립니다.'**
  String get supportFormDescription;

  /// No description provided for @openMailComposer.
  ///
  /// In ko, this message translates to:
  /// **'메일 작성 열기'**
  String get openMailComposer;

  /// No description provided for @mailLaunchFailed.
  ///
  /// In ko, this message translates to:
  /// **'메일 앱을 열 수 없습니다. 메일 앱 설정을 확인해 주세요.'**
  String get mailLaunchFailed;

  /// No description provided for @mailComposeOpened.
  ///
  /// In ko, this message translates to:
  /// **'메일 작성 화면을 열었습니다. 보내기를 누르면 문의가 접수됩니다.'**
  String get mailComposeOpened;

  /// No description provided for @myInquiries.
  ///
  /// In ko, this message translates to:
  /// **'내 문의'**
  String get myInquiries;

  /// No description provided for @noInquiries.
  ///
  /// In ko, this message translates to:
  /// **'아직 등록한 문의가 없어요.'**
  String get noInquiries;

  /// No description provided for @inquiryAnswered.
  ///
  /// In ko, this message translates to:
  /// **'답변 완료'**
  String get inquiryAnswered;

  /// No description provided for @inquiryPending.
  ///
  /// In ko, this message translates to:
  /// **'답변 대기'**
  String get inquiryPending;

  /// No description provided for @inquiryDetailTitle.
  ///
  /// In ko, this message translates to:
  /// **'문의 상세'**
  String get inquiryDetailTitle;

  /// No description provided for @adminAnswer.
  ///
  /// In ko, this message translates to:
  /// **'관리자 답변'**
  String get adminAnswer;

  /// No description provided for @noAnswerYet.
  ///
  /// In ko, this message translates to:
  /// **'아직 답변이 등록되지 않았어요.'**
  String get noAnswerYet;

  /// No description provided for @newsDetailTitle.
  ///
  /// In ko, this message translates to:
  /// **'소식 상세'**
  String get newsDetailTitle;

  /// No description provided for @noNewsPosts.
  ///
  /// In ko, this message translates to:
  /// **'아직 등록된 글이 없습니다.'**
  String get noNewsPosts;

  /// No description provided for @authLoginTab.
  ///
  /// In ko, this message translates to:
  /// **'로그인'**
  String get authLoginTab;

  /// No description provided for @authSignupTab.
  ///
  /// In ko, this message translates to:
  /// **'회원가입'**
  String get authSignupTab;

  /// No description provided for @authNicknameLabel.
  ///
  /// In ko, this message translates to:
  /// **'닉네임'**
  String get authNicknameLabel;

  /// No description provided for @authPasswordLabel.
  ///
  /// In ko, this message translates to:
  /// **'비밀번호'**
  String get authPasswordLabel;

  /// No description provided for @authPasswordConfirmLabel.
  ///
  /// In ko, this message translates to:
  /// **'비밀번호 확인'**
  String get authPasswordConfirmLabel;

  /// No description provided for @authKeepSignedIn.
  ///
  /// In ko, this message translates to:
  /// **'로그인 유지'**
  String get authKeepSignedIn;

  /// No description provided for @authForgotPassword.
  ///
  /// In ko, this message translates to:
  /// **'비밀번호 찾기'**
  String get authForgotPassword;

  /// No description provided for @authForgotPasswordEnterId.
  ///
  /// In ko, this message translates to:
  /// **'가입한 아이디'**
  String get authForgotPasswordEnterId;

  /// No description provided for @authCompleteSignup.
  ///
  /// In ko, this message translates to:
  /// **'회원가입 완료'**
  String get authCompleteSignup;

  /// No description provided for @authMsgIdPasswordRequired.
  ///
  /// In ko, this message translates to:
  /// **'아이디와 비밀번호를 입력해주세요.'**
  String get authMsgIdPasswordRequired;

  /// No description provided for @authMsgIdInvalidChars.
  ///
  /// In ko, this message translates to:
  /// **'아이디는 영문과 숫자만 사용할 수 있습니다.'**
  String get authMsgIdInvalidChars;

  /// No description provided for @authMsgNicknameRequired.
  ///
  /// In ko, this message translates to:
  /// **'닉네임을 입력해주세요.'**
  String get authMsgNicknameRequired;

  /// No description provided for @authMsgPasswordMismatch.
  ///
  /// In ko, this message translates to:
  /// **'비밀번호 확인이 일치하지 않습니다.'**
  String get authMsgPasswordMismatch;

  /// No description provided for @authMsgPasswordTooShort.
  ///
  /// In ko, this message translates to:
  /// **'비밀번호는 6자 이상이어야 합니다.'**
  String get authMsgPasswordTooShort;

  /// No description provided for @authMsgIdTaken.
  ///
  /// In ko, this message translates to:
  /// **'이미 사용 중인 아이디입니다.'**
  String get authMsgIdTaken;

  /// No description provided for @authMsgLoginFailed.
  ///
  /// In ko, this message translates to:
  /// **'등록된 계정 정보와 일치하지 않습니다.'**
  String get authMsgLoginFailed;

  /// No description provided for @authMsgIdEmptyOnReset.
  ///
  /// In ko, this message translates to:
  /// **'아이디를 입력해주세요.'**
  String get authMsgIdEmptyOnReset;

  /// No description provided for @authMsgResetSent.
  ///
  /// In ko, this message translates to:
  /// **'{id} 계정의 비밀번호 찾기 기능은 추후 연결됩니다.'**
  String authMsgResetSent(String id);

  /// No description provided for @authSignupNoticeTagPrefix.
  ///
  /// In ko, this message translates to:
  /// **'첫 태그는 {tag} 로 생성됩니다.'**
  String authSignupNoticeTagPrefix(String tag);

  /// No description provided for @authSignupNoticeTagBody.
  ///
  /// In ko, this message translates to:
  /// **'회원가입 순서대로 @deokive 뒤에 번호가 붙고, 이후 설정에서 원하는 태그로 바꿀 수 있습니다. 태그는 영문과 숫자만 사용할 수 있습니다.'**
  String get authSignupNoticeTagBody;

  /// No description provided for @authSignupNoticeBackup.
  ///
  /// In ko, this message translates to:
  /// **'일반 회원가입 정보는 로컬 DB에 저장됩니다. 일반 계정은 주기적인 클라우드 백업이 제한될 수 있으며 Google Drive 백업은 구글 로그인 계정에서 사용될 예정입니다.'**
  String get authSignupNoticeBackup;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ja', 'ko', 'zh'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when language+script codes are specified.
  switch (locale.languageCode) {
    case 'zh':
      {
        switch (locale.scriptCode) {
          case 'Hans':
            return AppLocalizationsZhHans();
          case 'Hant':
            return AppLocalizationsZhHant();
        }
        break;
      }
  }

  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ja':
      return AppLocalizationsJa();
    case 'ko':
      return AppLocalizationsKo();
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
