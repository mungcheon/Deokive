// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Japanese (`ja`).
class AppLocalizationsJa extends AppLocalizations {
  AppLocalizationsJa([String locale = 'ja']) : super(locale);

  @override
  String get home => 'ホーム';

  @override
  String get board => '掲示板';

  @override
  String get folders => 'フォルダ';

  @override
  String get calendar => 'カレンダー';

  @override
  String get settings => '設定';

  @override
  String get homeSectionNotice => 'お知らせ';

  @override
  String get homeSectionGoodsNews => 'グッズニュース';

  @override
  String get homeSectionEvent => 'イベント';

  @override
  String get boardSectionFreeTalk => '雑談';

  @override
  String get boardSectionTrade => '取引';

  @override
  String get boardSectionEventSchedule => 'イベント日程';

  @override
  String get boardNewPost => '新規投稿';

  @override
  String get boardEmptyState => 'まだ投稿がありません。';

  @override
  String get boardComingSoon => '掲示板機能は近日公開予定です。';

  @override
  String get languageLabel => '言語';

  @override
  String get languageHelp => 'アプリの表示言語を選択してください。';

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
  String get guest => 'ゲスト';

  @override
  String get loginRequiredAccountId => 'ログインが必要です';

  @override
  String get authGuest => 'ゲスト';

  @override
  String get authLocal => '一般アカウント';

  @override
  String get authGoogle => 'Googleアカウント';

  @override
  String get defaultFolderName => 'デフォルトフォルダ';

  @override
  String get wishlistFolderName => 'ウィッシュリスト';

  @override
  String get sortByName => '名前順';

  @override
  String get sortByGoodsCount => 'グッズが多い順';

  @override
  String get sortByPriceLow => '価格が安い順';

  @override
  String get sortByPriceHigh => '価格が高い順';

  @override
  String get sortBySeries => 'シリーズ順';

  @override
  String get sortByCharacter => 'キャラクター順';

  @override
  String get sortByCategory => 'カテゴリ順';

  @override
  String get sortByNewestPurchase => '購入日が新しい順';

  @override
  String get sortByOldestPurchase => '購入日が古い順';

  @override
  String get sortByNewestRelease => '発売日が新しい順';

  @override
  String get sortByOldestRelease => '発売日が古い順';

  @override
  String get sortByQuantity => '数量が多い順';

  @override
  String get sortByFavorites => 'お気に入り優先';

  @override
  String get purchaseStateWished => 'ウィッシュ';

  @override
  String get purchaseStateOrdered => '注文済';

  @override
  String get purchaseStateArrived => '到着';

  @override
  String get purchaseStateOwned => '所持中';

  @override
  String get markAsPurchased => '購入済みにする';

  @override
  String get moveToOwnedFolder => '所持フォルダへ移動';

  @override
  String get addToWishlist => 'ウィッシュリストへ追加';

  @override
  String get currencyKrw => 'ウォン (KRW)';

  @override
  String get currencyUsd => 'ドル (USD)';

  @override
  String get currencyJpy => '円 (JPY)';

  @override
  String get currencyEur => 'ユーロ (EUR)';

  @override
  String get currencyCny => '元 (CNY)';

  @override
  String get tapToChangeCurrency => 'タップして通貨を変更';

  @override
  String get categoryFigure => 'フィギュア';

  @override
  String get categoryPlush => 'ぬいぐるみ';

  @override
  String get categoryPoster => 'ポスター';

  @override
  String get categoryCard => 'カード';

  @override
  String get categoryBadge => 'バッジ';

  @override
  String get categoryKeyring => 'キーホルダー';

  @override
  String get categorySticker => 'ステッカー';

  @override
  String get categoryStandee => 'アクスタ';

  @override
  String get categoryPhotoCard => 'フォトカード';

  @override
  String get categoryArtBook => 'アートブック';

  @override
  String get categoryClothing => '衣類';

  @override
  String get categoryAccessory => 'アクセサリー';

  @override
  String get categoryOther => 'その他';

  @override
  String get totalGoodsCount => 'グッズ総数';

  @override
  String get totalSpending => '購入費用';

  @override
  String get exportCsv => 'CSVエクスポート';

  @override
  String get csvExportedMessage => 'グッズ一覧をCSVに保存しました。';

  @override
  String get csvExportFailed => 'CSVの書き出しに失敗しました。';

  @override
  String get characterChartTitle => 'キャラクター別グッズ数';

  @override
  String get categoryChartTitle => 'カテゴリ別グッズ数';

  @override
  String get noChartData => '表示するデータがまだありません。';

  @override
  String get autocompleteHint => '既存の値を検索または新規入力';

  @override
  String get addNewValue => '新規追加';

  @override
  String get releaseDateLabel => '発売日';

  @override
  String get characterNameLabel => 'キャラクター';

  @override
  String get selectDate => '日付を選択';

  @override
  String get backupStatusLoggedOut => 'ログイン後にバックアップ状態を確認できます。';

  @override
  String get backupStatusGoogle => '個人のGoogle Driveバックアップが利用できます。';

  @override
  String get backupStatusLocal => '一般アカウントのクラウドバックアップは今後対応予定です。';

  @override
  String get googleUnsupported => '現在のプラットフォームではGoogleログインに対応していません。';

  @override
  String get googleNotConfigured => 'Googleログインの設定がまだ完了していません。';

  @override
  String get googleConfigError =>
      'Googleログインの設定が未完了か認証に失敗しました。Androidのパッケージ名とSHA-1、iOSのClient IDとURLスキームを確認してください。';

  @override
  String get googleInitializing => 'Googleログインを初期化中です。';

  @override
  String get googleBackupEnabled =>
      'GoogleアカウントでログインするとプロフィールとGoogle Driveバックアップを準備できます。';

  @override
  String get googleAccountIdLocked => 'GoogleログインアカウントはIDを変更できません。';

  @override
  String get accountIdHelp => '英字と数字のみ使用できます。';

  @override
  String get tagHelp => '英字と数字のみ、スペースは使えません。';

  @override
  String get profileSaveError => 'プロフィールを保存できません。タグとIDの形式を確認してください。';

  @override
  String get todayRecommendation => '今日のおすすめ';

  @override
  String get close => '閉じる';

  @override
  String get cameraCapture => 'カメラで撮影';

  @override
  String get chooseFromLibrary => 'アルバムから選択';

  @override
  String get editProfile => 'プロフィール編集';

  @override
  String get displayName => 'ニックネーム';

  @override
  String get accountId => 'ID';

  @override
  String get tag => 'タグ';

  @override
  String get cancel => 'キャンセル';

  @override
  String get save => '保存';

  @override
  String get login => 'ログイン';

  @override
  String get loginWithGoogle => 'Googleでログイン';

  @override
  String get signOut => 'ログアウト';

  @override
  String get theme => 'テーマ';

  @override
  String get darkMode => 'ダークモード';

  @override
  String get pushEnabled => '通知を受け取る';

  @override
  String get support => 'お問い合わせ';

  @override
  String get homeSectionBanner => 'おすすめ';

  @override
  String get homeSectionNews => 'お知らせ';

  @override
  String get homeBadgeShowcase => 'バッジ展示';

  @override
  String get noEquippedBadges => 'まだ装着したバッジがありません。';

  @override
  String get folderCountLabel => 'フォルダ';

  @override
  String get goodsCountLabel => 'グッズ';

  @override
  String get badgeCountLabel => 'バッジ';

  @override
  String get inquiryCategoryGeneral => '一般的なお問い合わせ';

  @override
  String get inquiryCategoryBug => 'バグ報告';

  @override
  String get inquiryCategoryAccount => 'アカウントについて';

  @override
  String get inquiryCategoryPayment => '決済について';

  @override
  String get inquiryCategoryFeature => '機能の提案';

  @override
  String get inquiryCategoryLabel => 'お問い合わせカテゴリ';

  @override
  String get inquiryTitleLabel => '件名';

  @override
  String get inquiryTitleRequired => '件名を入力してください。';

  @override
  String get inquiryContentLabel => 'お問い合わせ内容';

  @override
  String get inquiryContentRequired => 'お問い合わせ内容を入力してください。';

  @override
  String get supportFormHeader => '問い合わせメール作成';

  @override
  String get supportFormDescription =>
      '内容を作成するとdeokivecs@gmail.com宛のメール作成画面が開きます。';

  @override
  String get openMailComposer => 'メール作成を開く';

  @override
  String get mailLaunchFailed => 'メールアプリを開けませんでした。設定を確認してください。';

  @override
  String get mailComposeOpened => 'メール下書きが開きました。送信すると問い合わせが完了します。';

  @override
  String get myInquiries => 'マイ問い合わせ';

  @override
  String get noInquiries => 'まだお問い合わせはありません。';

  @override
  String get inquiryAnswered => '回答済';

  @override
  String get inquiryPending => '回答待ち';

  @override
  String get inquiryDetailTitle => '問い合わせ詳細';

  @override
  String get adminAnswer => '管理者からの回答';

  @override
  String get noAnswerYet => 'まだ回答が登録されていません。';

  @override
  String get newsDetailTitle => 'お知らせ詳細';

  @override
  String get noNewsPosts => 'まだ投稿がありません。';

  @override
  String get authLoginTab => 'ログイン';

  @override
  String get authSignupTab => '会員登録';

  @override
  String get authNicknameLabel => 'ニックネーム';

  @override
  String get authPasswordLabel => 'パスワード';

  @override
  String get authPasswordConfirmLabel => 'パスワード確認';

  @override
  String get authKeepSignedIn => 'ログイン状態を保持';

  @override
  String get authForgotPassword => 'パスワードを忘れた場合';

  @override
  String get authForgotPasswordEnterId => '登録したID';

  @override
  String get authCompleteSignup => '会員登録を完了';

  @override
  String get authMsgIdPasswordRequired => 'IDとパスワードを入力してください。';

  @override
  String get authMsgIdInvalidChars => 'IDは英字と数字のみ使用できます。';

  @override
  String get authMsgNicknameRequired => 'ニックネームを入力してください。';

  @override
  String get authMsgPasswordMismatch => 'パスワード確認が一致しません。';

  @override
  String get authMsgPasswordTooShort => 'パスワードは6文字以上である必要があります。';

  @override
  String get authMsgIdTaken => 'このIDはすでに使用されています。';

  @override
  String get authMsgLoginFailed => '登録された情報と一致しません。';

  @override
  String get authMsgIdEmptyOnReset => 'IDを入力してください。';

  @override
  String authMsgResetSent(String id) {
    return '$id アカウントのパスワード復元は後ほど対応します。';
  }

  @override
  String authSignupNoticeTagPrefix(String tag) {
    return '最初のタグは $tag で発行されます。';
  }

  @override
  String get authSignupNoticeTagBody =>
      '新規アカウントには @deokive と連番が付与され、設定から変更できます。タグは英字と数字のみ使用できます。';

  @override
  String get authSignupNoticeBackup =>
      '一般登録の情報は端末ローカルに保存されます。一般アカウントのクラウドバックアップには制限があり、Google DriveバックアップはGoogleログインアカウントで利用予定です。';
}
