plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    id("com.google.gms.google-services")
}

android {
    namespace = "com.example.deokive"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.example.deokive"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    // The `onnxruntime` Flutter plugin only ships arm64-v8a / armeabi-v7a
    // .so files, so x86_64 emulators get dlopen("libonnxruntime.so") =
    // "not found". Microsoft's official AAR on Maven Central bundles every
    // ABI; pickFirst tells Gradle "if both AARs provide the same .so,
    // grab whichever comes first" so there's no duplicate-resource error.
    packaging {
        jniLibs {
            pickFirsts += "**/libonnxruntime.so"
        }
    }
}

dependencies {
    // Provides libonnxruntime.so for x86 / x86_64 (Android emulator) on top
    // of what the Flutter `onnxruntime` plugin ships for arm devices.
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.16.3")
}

flutter {
    source = "../.."
}
