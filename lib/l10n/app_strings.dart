import 'app_language.dart';

class AppStrings {
  final AppLanguage language;

  const AppStrings(this.language);

  static AppStrings of(AppLanguage language) => AppStrings(language);

  bool get _isKo => language == AppLanguage.korean;

  String get home => _isKo ? '홈' : 'Home';
  String get folders => _isKo ? '폴더' : 'Folders';
  String get calendar => _isKo ? '캘린더' : 'Calendar';
  String get settings => _isKo ? '설정' : 'Settings';

  String get languageLabel => _isKo ? '언어' : 'Language';
  String get languageHelp =>
      _isKo ? '앱에 표시할 언어를 선택하세요.' : 'Choose the app display language.';
  String get korean => '한국어';
  String get english => 'English';

  String get guest => _isKo ? '게스트' : 'Guest';
  String get loginRequiredAccountId =>
      _isKo ? '로그인이 필요합니다' : 'Login required';
  String get authGuest => _isKo ? '게스트' : 'Guest';
  String get authLocal => _isKo ? '일반 계정' : 'Local account';
  String get authGoogle => _isKo ? '구글 계정' : 'Google account';

  String get defaultFolderName => _isKo ? '기본 폴더' : 'Default Folder';
  String get sortByName => _isKo ? '이름순' : 'Name';
  String get sortByGoodsCount => _isKo ? '굿즈 많은 순' : 'Most goods';
  String get sortByPriceLow => _isKo ? '가격 낮은 순' : 'Lowest price';
  String get sortByPriceHigh => _isKo ? '가격 높은 순' : 'Highest price';
  String get sortBySeries => _isKo ? '시리즈순' : 'Series';
  String get sortByNewestPurchase =>
      _isKo ? '구매일 최신순' : 'Newest purchase';
  String get sortByOldestPurchase =>
      _isKo ? '구매일 오래된 순' : 'Oldest purchase';

  String get backupStatusLoggedOut => _isKo
      ? '로그인 후 백업 상태를 확인할 수 있습니다.'
      : 'Sign in to check your backup status.';
  String get backupStatusGoogle => _isKo
      ? '개인 Google Drive 백업을 사용할 수 있습니다.'
      : 'Personal Google Drive backup is available.';
  String get backupStatusLocal => _isKo
      ? '일반 계정은 추후 클라우드 백업을 지원할 예정입니다.'
      : 'Cloud backup for local accounts will be added later.';

  String get googleUnsupported => _isKo
      ? '현재 플랫폼에서는 구글 로그인을 지원하지 않습니다.'
      : 'Google Sign-In is not supported on this platform.';
  String get googleNotConfigured => _isKo
      ? '구글 로그인 설정이 아직 완료되지 않았습니다.'
      : 'Google Sign-In is not configured yet.';
  String get googleConfigError => _isKo
      ? '구글 로그인 설정이 완료되지 않았거나 인증에 실패했습니다. Android 패키지명과 SHA-1, iOS Client ID와 URL Scheme 설정을 확인하세요.'
      : 'Google Sign-In is incomplete or authentication failed. Check the Android package name and SHA-1, and the iOS Client ID and URL scheme.';
  String get googleInitializing =>
      _isKo ? '구글 로그인을 초기화하는 중입니다.' : 'Initializing Google Sign-In.';
  String get googleBackupEnabled => _isKo
      ? '구글 계정으로 로그인하면 계정 정보와 프로필 사진을 가져오고 Google Drive 백업을 준비할 수 있습니다.'
      : 'When you sign in with Google, the app can load your account profile and prepare Google Drive backup.';
  String get googleAccountIdLocked => _isKo
      ? '구글 로그인 계정은 아이디를 변경할 수 없습니다.'
      : 'You cannot change the ID of a Google sign-in account.';
  String get accountIdHelp => _isKo
      ? '영문과 숫자만 사용할 수 있습니다.'
      : 'Use letters and numbers only.';
  String get tagHelp => _isKo
      ? '영문과 숫자만 사용할 수 있고 띄어쓰기는 지원하지 않습니다.'
      : 'Use letters and numbers only, without spaces.';
  String get profileSaveError => _isKo
      ? '프로필 정보를 저장할 수 없습니다. 태그와 아이디 형식을 확인해주세요.'
      : 'Could not save the profile. Check the tag and account ID format.';

  String get todayRecommendation =>
      _isKo ? '오늘의 추천' : 'Today\'s pick';
  String get homePromoBody => _isKo
      ? '배지 컬렉션과 홈 기능을 더 넓게 쓰고 싶다면 프리미엄 기능을 확인해보세요.'
      : 'Check out the premium features if you want to use the badge collection and home features more fully.';
  String get homePromoFootnote => _isKo
      ? '이 팝업은 홈 진입 시 노출되며, 하루 동안 보지 않기를 선택할 수 있습니다.'
      : 'This popup appears when you enter Home, and you can hide it for the rest of the day.';
  String get dismissForToday =>
      _isKo ? '하루 동안 보지 않기' : 'Hide for today';
  String get close => _isKo ? '닫기' : 'Close';

  String get cameraCapture => _isKo ? '카메라로 촬영' : 'Take photo';
  String get chooseFromLibrary =>
      _isKo ? '앨범에서 선택' : 'Choose from library';
  String get editProfile => _isKo ? '프로필 수정' : 'Edit profile';
  String get displayName => _isKo ? '닉네임' : 'Display name';
  String get accountId => _isKo ? '아이디' : 'Account ID';
  String get tag => _isKo ? '태그' : 'Tag';
  String get cancel => _isKo ? '취소' : 'Cancel';
  String get save => _isKo ? '저장' : 'Save';
  String get login => _isKo ? '로그인' : 'Log in';
  String get loginWithGoogle =>
      _isKo ? '구글로 로그인' : 'Continue with Google';
  String get signOut => _isKo ? '로그아웃' : 'Sign out';
  String get theme => _isKo ? '테마' : 'Theme';
  String get darkMode => _isKo ? '다크 모드' : 'Dark mode';
  String get pushEnabled => _isKo ? '알림 받기' : 'Push notifications';
  String get unlimited => _isKo ? '무제한' : 'Unlimited';
  String remainingCount(int count) => _isKo ? '$count개 남음' : '$count left';
  String get adShowing => _isKo ? '광고 표시 중' : 'Ads enabled';
  String get adRemoved => _isKo ? '광고 제거' : 'Ads removed';
  String get premiumPreview =>
      _isKo ? '프리미엄 미리보기' : 'Premium preview';
  String get adFreePreview =>
      _isKo ? '광고 제거 미리보기' : 'Ad-free preview';
  String get testAds => _isKo ? '테스트 광고 표시' : 'Show test ads';
  String get support => _isKo ? '문의하기' : 'Contact support';

  String get homeSectionBanner => _isKo ? '추천 배너' : 'Highlights';
  String get homeSectionNews => _isKo ? '소식' : 'News';
  String get homeBadgeShowcase => _isKo ? '배지 전시대' : 'Badge showcase';
  String get noEquippedBadges => _isKo
      ? '아직 장착한 배지가 없습니다.'
      : 'No badges are equipped yet.';
  String get folderCountLabel => _isKo ? '폴더' : 'Folders';
  String get goodsCountLabel => _isKo ? '굿즈' : 'Goods';
  String get badgeCountLabel => _isKo ? '배지' : 'Badges';
}
