import 'package:flutter/material.dart';

enum AppLanguage {
  korean,
  english,
}

extension AppLanguageX on AppLanguage {
  Locale get locale {
    switch (this) {
      case AppLanguage.korean:
        return const Locale('ko');
      case AppLanguage.english:
        return const Locale('en');
    }
  }

  String get label {
    switch (this) {
      case AppLanguage.korean:
        return '한국어';
      case AppLanguage.english:
        return 'English';
    }
  }
}
