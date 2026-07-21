// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Korean (`ko`).
class AppLocalizationsKo extends AppLocalizations {
  AppLocalizationsKo([String locale = 'ko']) : super(locale);

  @override
  String get home => '홈';

  @override
  String get board => '게시판';

  @override
  String get folders => '폴더';

  @override
  String get calendar => '캘린더';

  @override
  String get settings => '설정';

  @override
  String get homeSectionNotice => '공지';

  @override
  String get homeSectionGoodsNews => '굿즈 소식';

  @override
  String get homeSectionEvent => '이벤트';

  @override
  String get boardSectionFreeTalk => '자유 게시판';

  @override
  String get boardSectionTrade => '거래 게시판';

  @override
  String get boardSectionEventSchedule => '행사 일정';

  @override
  String get boardNewPost => '새 글 쓰기';

  @override
  String get boardEmptyState => '아직 등록된 글이 없습니다.';

  @override
  String get boardComingSoon => '게시판 기능은 곧 열립니다.';

  @override
  String get languageLabel => '언어';

  @override
  String get languageHelp => '앱에 표시할 언어를 선택하세요.';

  @override
  String get korean => '한국어';

  @override
  String get english => 'English';

  @override
  String get japanese => '日本語';

  @override
  String get chineseSimplified => '简体中文';

  @override
  String get chineseTraditional => '繁體中文';

  @override
  String get guest => '게스트';

  @override
  String get loginRequiredAccountId => '로그인이 필요합니다';

  @override
  String get authGuest => '게스트';

  @override
  String get authLocal => '일반 계정';

  @override
  String get authGoogle => '구글 계정';

  @override
  String get defaultFolderName => '기본 폴더';

  @override
  String get wishlistFolderName => '위시리스트';

  @override
  String get sortByName => '이름순';

  @override
  String get sortByGoodsCount => '굿즈 많은 순';

  @override
  String get sortByPriceLow => '가격 낮은 순';

  @override
  String get sortByPriceHigh => '가격 높은 순';

  @override
  String get sortBySeries => '시리즈순';

  @override
  String get sortByCharacter => '캐릭터순';

  @override
  String get sortByCategory => '카테고리순';

  @override
  String get sortByNewestPurchase => '구매일 최신순';

  @override
  String get sortByOldestPurchase => '구매일 오래된 순';

  @override
  String get sortByNewestRelease => '발매일 최신순';

  @override
  String get sortByOldestRelease => '발매일 오래된 순';

  @override
  String get sortByQuantity => '수량 많은 순';

  @override
  String get sortByFavorites => '즐겨찾기 우선';

  @override
  String get purchaseStateWished => '위시';

  @override
  String get purchaseStateOrdered => '주문함';

  @override
  String get purchaseStateArrived => '도착';

  @override
  String get purchaseStateOwned => '보유 중';

  @override
  String get markAsPurchased => '구매 완료로 표시';

  @override
  String get moveToOwnedFolder => '보유 폴더로 이동';

  @override
  String get addToWishlist => '위시리스트에 추가';

  @override
  String get currencyKrw => '원 (KRW)';

  @override
  String get currencyUsd => '달러 (USD)';

  @override
  String get currencyJpy => '엔 (JPY)';

  @override
  String get currencyEur => '유로 (EUR)';

  @override
  String get currencyCny => '위안 (CNY)';

  @override
  String get tapToChangeCurrency => '탭하여 통화 변경';

  @override
  String get categoryFigure => '피규어';

  @override
  String get categoryPlush => '봉제 인형';

  @override
  String get categoryPoster => '포스터';

  @override
  String get categoryCard => '카드';

  @override
  String get categoryBadge => '뱃지';

  @override
  String get categoryKeyring => '키링';

  @override
  String get categorySticker => '스티커';

  @override
  String get categoryStandee => '스탠디';

  @override
  String get categoryPhotoCard => '포토카드';

  @override
  String get categoryArtBook => '아트북';

  @override
  String get categoryClothing => '의류';

  @override
  String get categoryAccessory => '액세서리';

  @override
  String get categoryOther => '기타';

  @override
  String get totalGoodsCount => '전체 굿즈';

  @override
  String get totalSpending => '구매 비용';

  @override
  String get exportCsv => 'CSV 내보내기';

  @override
  String get csvExportedMessage => '굿즈 목록을 CSV로 저장했습니다.';

  @override
  String get csvExportFailed => 'CSV 내보내기에 실패했습니다.';

  @override
  String get characterChartTitle => '캐릭터별 굿즈 수';

  @override
  String get categoryChartTitle => '카테고리별 굿즈 수';

  @override
  String get noChartData => '아직 표시할 데이터가 없습니다.';

  @override
  String get autocompleteHint => '기존 입력값 검색 또는 새로 입력';

  @override
  String get addNewValue => '새로 추가';

  @override
  String get releaseDateLabel => '발매일';

  @override
  String get characterNameLabel => '캐릭터';

  @override
  String get selectDate => '날짜 선택';

  @override
  String get backupStatusLoggedOut => '로그인 후 백업 상태를 확인할 수 있습니다.';

  @override
  String get backupStatusGoogle => '개인 Google Drive 백업을 사용할 수 있습니다.';

  @override
  String get backupStatusLocal => '일반 계정은 추후 클라우드 백업을 지원할 예정입니다.';

  @override
  String get googleUnsupported => '현재 플랫폼에서는 구글 로그인을 지원하지 않습니다.';

  @override
  String get googleNotConfigured => '구글 로그인 설정이 아직 완료되지 않았습니다.';

  @override
  String get googleConfigError =>
      '구글 로그인 설정이 완료되지 않았거나 인증에 실패했습니다. Android 패키지명과 SHA-1, iOS Client ID와 URL Scheme 설정을 확인하세요.';

  @override
  String get googleInitializing => '구글 로그인을 초기화하는 중입니다.';

  @override
  String get googleBackupEnabled =>
      '구글 계정으로 로그인하면 계정 정보와 프로필 사진을 가져오고 Google Drive 백업을 준비할 수 있습니다.';

  @override
  String get googleAccountIdLocked => '구글 로그인 계정은 아이디를 변경할 수 없습니다.';

  @override
  String get accountIdHelp => '영문과 숫자만 사용할 수 있습니다.';

  @override
  String get tagHelp => '영문과 숫자만 사용할 수 있고 띄어쓰기는 지원하지 않습니다.';

  @override
  String get profileSaveError => '프로필 정보를 저장할 수 없습니다. 태그와 아이디 형식을 확인해주세요.';

  @override
  String get todayRecommendation => '오늘의 추천';

  @override
  String get close => '닫기';

  @override
  String get cameraCapture => '카메라로 촬영';

  @override
  String get chooseFromLibrary => '앨범에서 선택';

  @override
  String get editProfile => '프로필 수정';

  @override
  String get displayName => '닉네임';

  @override
  String get accountId => '아이디';

  @override
  String get tag => '태그';

  @override
  String get cancel => '취소';

  @override
  String get save => '저장';

  @override
  String get login => '로그인';

  @override
  String get loginWithGoogle => '구글로 로그인';

  @override
  String get signOut => '로그아웃';

  @override
  String get theme => '테마';

  @override
  String get darkMode => '다크 모드';

  @override
  String get pushEnabled => '알림 받기';

  @override
  String get support => '문의하기';

  @override
  String get homeSectionBanner => '추천 배너';

  @override
  String get homeSectionNews => '소식';

  @override
  String get homeBadgeShowcase => '배지 전시대';

  @override
  String get noEquippedBadges => '아직 장착한 배지가 없습니다.';

  @override
  String get folderCountLabel => '폴더';

  @override
  String get goodsCountLabel => '굿즈';

  @override
  String get badgeCountLabel => '배지';

  @override
  String get inquiryCategoryGeneral => '일반 문의';

  @override
  String get inquiryCategoryBug => '버그 제보';

  @override
  String get inquiryCategoryAccount => '계정 문의';

  @override
  String get inquiryCategoryPayment => '결제 문의';

  @override
  String get inquiryCategoryFeature => '기능 제안';

  @override
  String get inquiryCategoryLabel => '문의 카테고리';

  @override
  String get inquiryTitleLabel => '제목';

  @override
  String get inquiryTitleRequired => '제목을 입력해 주세요.';

  @override
  String get inquiryContentLabel => '문의 내용';

  @override
  String get inquiryContentRequired => '문의 내용을 입력해 주세요.';

  @override
  String get supportFormHeader => '문의 메일 작성';

  @override
  String get supportFormDescription =>
      '문의 내용을 작성하면 deokivecs@gmail.com으로 메일 작성 화면이 열립니다.';

  @override
  String get openMailComposer => '메일 작성 열기';

  @override
  String get mailLaunchFailed => '메일 앱을 열 수 없습니다. 메일 앱 설정을 확인해 주세요.';

  @override
  String get mailComposeOpened => '메일 작성 화면을 열었습니다. 보내기를 누르면 문의가 접수됩니다.';

  @override
  String get myInquiries => '내 문의';

  @override
  String get noInquiries => '아직 등록한 문의가 없어요.';

  @override
  String get inquiryAnswered => '답변 완료';

  @override
  String get inquiryPending => '답변 대기';

  @override
  String get inquiryDetailTitle => '문의 상세';

  @override
  String get adminAnswer => '관리자 답변';

  @override
  String get noAnswerYet => '아직 답변이 등록되지 않았어요.';

  @override
  String get newsDetailTitle => '소식 상세';

  @override
  String get noNewsPosts => '아직 등록된 글이 없습니다.';

  @override
  String get authLoginTab => '로그인';

  @override
  String get authSignupTab => '회원가입';

  @override
  String get authNicknameLabel => '닉네임';

  @override
  String get authPasswordLabel => '비밀번호';

  @override
  String get authPasswordConfirmLabel => '비밀번호 확인';

  @override
  String get authKeepSignedIn => '로그인 유지';

  @override
  String get authForgotPassword => '비밀번호 찾기';

  @override
  String get authForgotPasswordEnterId => '가입한 아이디';

  @override
  String get authCompleteSignup => '회원가입 완료';

  @override
  String get authMsgIdPasswordRequired => '아이디와 비밀번호를 입력해주세요.';

  @override
  String get authMsgIdInvalidChars => '아이디는 영문과 숫자만 사용할 수 있습니다.';

  @override
  String get authMsgNicknameRequired => '닉네임을 입력해주세요.';

  @override
  String get authMsgPasswordMismatch => '비밀번호 확인이 일치하지 않습니다.';

  @override
  String get authMsgPasswordTooShort => '비밀번호는 6자 이상이어야 합니다.';

  @override
  String get authMsgIdTaken => '이미 사용 중인 아이디입니다.';

  @override
  String get authMsgLoginFailed => '등록된 계정 정보와 일치하지 않습니다.';

  @override
  String get authMsgIdEmptyOnReset => '아이디를 입력해주세요.';

  @override
  String authMsgResetSent(String id) {
    return '$id 계정의 비밀번호 찾기 기능은 추후 연결됩니다.';
  }

  @override
  String authSignupNoticeTagPrefix(String tag) {
    return '첫 태그는 $tag 로 생성됩니다.';
  }

  @override
  String get authSignupNoticeTagBody =>
      '회원가입 순서대로 @deokive 뒤에 번호가 붙고, 이후 설정에서 원하는 태그로 바꿀 수 있습니다. 태그는 영문과 숫자만 사용할 수 있습니다.';

  @override
  String get authSignupNoticeBackup =>
      '일반 회원가입 정보는 로컬 DB에 저장됩니다. 일반 계정은 주기적인 클라우드 백업이 제한될 수 있으며 Google Drive 백업은 구글 로그인 계정에서 사용될 예정입니다.';
}
