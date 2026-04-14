@echo off
setlocal

set "ROOT=%~dp0"
set "API_URL=http://127.0.0.1:8000"
set "ADMIN_WEB_URL=http://127.0.0.1:4174"

start "Deokive API" cmd /k "cd /d "%ROOT%server" && uvicorn app.main:app --reload"
timeout /t 2 /nobreak >nul
start "Deokive Admin Web" cmd /k "cd /d "%ROOT%admin-web" && set VITE_DEOKIVE_ADMIN_API_BASE_URL=%API_URL% && npm run dev"

echo Deokive admin web stack is starting.
echo API: %API_URL%
echo Admin Web: %ADMIN_WEB_URL%
echo Admin Login ID: admin
echo Admin Login PW: admin

endlocal
