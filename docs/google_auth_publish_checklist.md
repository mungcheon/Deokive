# Google Auth Publish Checklist

This checklist covers the remaining non-code work required to keep Deokive in production with Google sign-in and Google Drive backup.

## App Metadata

- App name: `Deokive`
- iOS bundle ID: `com.example.deokive`
- iOS OAuth client ID: `655207560279-knmgn03ve971hfmqb40e4ek7riesml9u.apps.googleusercontent.com`

## Google Auth Platform

Complete these sections in the Google Cloud project linked to Firebase:

### Branding

- Set app name
- Set support email
- Set developer contact email
- Add homepage URL
- Add privacy policy URL
- Add terms of service URL

### Audience

- User type: `External`
- Publishing status: `In production`

### Data Access

Declare the scopes actually used by the app:

- `email`
- `profile`
- `openid`
- `https://www.googleapis.com/auth/drive.appdata`

Recommended scope-use description:

- `email`, `profile`, `openid`: used to identify the signed-in user and display Google account profile information in the app
- `drive.appdata`: used only to store and update Deokive backup data inside the user's Google Drive app data folder

## Public URLs To Prepare

Before final verification, host public URLs for:

- Homepage
- Privacy Policy
- Terms of Service

This repository includes draft documents you can publish:

- `docs/privacy_policy.md`
- `docs/terms_of_service.md`

## Domain Verification

If Google requires domain ownership verification:

- verify the domain in Google Search Console
- use the same verified domain for homepage, privacy policy, and terms URLs

## Verification Submission

If Google requests verification, prepare:

- app description
- scope usage explanation
- support email
- privacy policy URL
- terms URL
- homepage URL
- video or screenshots showing the Google sign-in and Drive backup flow

## Local Project Status

Already wired in this codebase:

- iOS `GIDClientID`
- iOS URL scheme
- Flutter-side iOS client ID default
- Google Drive app data backup integration

Remaining work is mainly console configuration and public document hosting.
