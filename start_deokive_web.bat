@echo off
setlocal

set "ROOT=%~dp0"
set "API_URL=http://127.0.0.1:8000"
set "WEB_HOST=127.0.0.1"
set "WEB_PORT=7357"

rem Optional: fill these in if you want Google web login enabled.
set "GOOGLE_WEB_CLIENT_ID="
set "GOOGLE_WEB_SERVER_CLIENT_ID="

set "FLUTTER_ARGS=--web-hostname %WEB_HOST% --web-port %WEB_PORT% --dart-define=DEOKIVE_SERVER_BASE_URL=%API_URL%"

if not "%GOOGLE_WEB_CLIENT_ID%"=="" (
  set "FLUTTER_ARGS=%FLUTTER_ARGS% --dart-define=GOOGLE_WEB_CLIENT_ID=%GOOGLE_WEB_CLIENT_ID%"
)

if not "%GOOGLE_WEB_SERVER_CLIENT_ID%"=="" (
  set "FLUTTER_ARGS=%FLUTTER_ARGS% --dart-define=GOOGLE_WEB_SERVER_CLIENT_ID=%GOOGLE_WEB_SERVER_CLIENT_ID%"
)

start "Deokive API" cmd /k "cd /d "%ROOT%server" && uvicorn app.main:app --reload"
timeout /t 2 /nobreak >nul
start "Deokive Web" cmd /k "cd /d "%ROOT%" && flutter run -d chrome %FLUTTER_ARGS%"

echo Deokive app web stack is starting.
echo API: %API_URL%
echo Web: http://%WEB_HOST%:%WEB_PORT%

endlocal
