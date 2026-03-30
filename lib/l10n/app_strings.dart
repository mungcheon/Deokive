import 'app_language.dart';

class AppStrings {
  final AppLanguage language;

  const AppStrings(this.language);

  static AppStrings of(AppLanguage language) => AppStrings(language);

  String get home => language == AppLanguage.korean ? '홈' : 'Home';
  String get folders => language == AppLanguage.korean ? '폴더' : 'Folders';
  String get calendar => language == AppLanguage.korean ? '캘린더' : 'Calendar';
  String get settings => language == AppLanguage.korean ? '설정' : 'Settings';
  String get languageLabel => language == AppLanguage.korean ? '언어' : 'Language';
  String get languageHelp =>
      language == AppLanguage.korean ? '앱 표시 언어를 선택하세요' : 'Choose the app display language';
}
