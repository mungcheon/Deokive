# Google 로그인 Android 설정

`google_sign_in`은 코드만 추가해서 끝나지 않습니다. 아래 4가지를 같이 맞춰야 실제 로그인됩니다.

## 1. 패키지명 확인

현재 Android `applicationId`:

`com.example.deokive`

이 값과 Google Cloud/Firebase에 등록한 Android 앱 패키지명이 반드시 같아야 합니다.

파일:

`android/app/build.gradle.kts`

## 2. SHA-1 등록

디버그 또는 릴리즈 키의 SHA-1 값을 Google Cloud Console 또는 Firebase 프로젝트에 등록해야 합니다.

예시:

```powershell
cd android
.\gradlew signingReport
```

여기서 나온 `SHA1` 값을 Android 앱 설정에 등록합니다.

## 3. Web / Server Client ID 준비

필요하면 `dart-define`으로 Client ID를 넣을 수 있게 코드가 준비되어 있습니다.

예시:

```powershell
flutter run `
  --dart-define=GOOGLE_ANDROID_SERVER_CLIENT_ID=YOUR_SERVER_CLIENT_ID
```

사용 가능한 키:

- `GOOGLE_ANDROID_SERVER_CLIENT_ID`
- `GOOGLE_IOS_CLIENT_ID`
- `GOOGLE_WEB_CLIENT_ID`
- `GOOGLE_WEB_SERVER_CLIENT_ID`

## 4. 테스트

Android에서 실행 후 설정 탭의 `구글로 로그인`을 누릅니다.

실패하면 앱 안에 다음 의미의 안내가 표시됩니다.

- 플랫폼 미지원
- 구글 로그인 초기화 중
- 패키지명 / SHA-1 / Client ID 설정 누락

## 참고

`google-services.json`은 Firebase 기능을 함께 쓸 때 보통 같이 넣지만, 현재 프로젝트의 기본 Google 로그인 자체는 패키지명 / SHA-1 / OAuth 클라이언트 설정이 더 핵심입니다.
