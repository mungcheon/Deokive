import 'package:flutter/material.dart';

enum AppLanguage {
  korean,
  english,
  japanese,
  chineseSimplified,
  chineseTraditional,
}

extension AppLanguageX on AppLanguage {
  Locale get locale {
    switch (this) {
      case AppLanguage.korean:
        return const Locale('ko');
      case AppLanguage.english:
        return const Locale('en');
      case AppLanguage.japanese:
        return const Locale('ja');
      case AppLanguage.chineseSimplified:
        return const Locale.fromSubtags(languageCode: 'zh', scriptCode: 'Hans');
      case AppLanguage.chineseTraditional:
        return const Locale.fromSubtags(languageCode: 'zh', scriptCode: 'Hant');
    }
  }

  /// Compact code used as the translation cache key (ko / en / ja /
  /// zh_Hans / zh_Hant). Matches what `ClaudeTranslationService` expects.
  String get translationCode {
    switch (this) {
      case AppLanguage.korean:
        return 'ko';
      case AppLanguage.english:
        return 'en';
      case AppLanguage.japanese:
        return 'ja';
      case AppLanguage.chineseSimplified:
        return 'zh_Hans';
      case AppLanguage.chineseTraditional:
        return 'zh_Hant';
    }
  }

  String get label {
    switch (this) {
      case AppLanguage.korean:
        return '한국어';
      case AppLanguage.english:
        return 'English';
      case AppLanguage.japanese:
        return '日本語';
      case AppLanguage.chineseSimplified:
        return '简体中文';
      case AppLanguage.chineseTraditional:
        return '繁體中文';
    }
  }
}
