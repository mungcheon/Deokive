@echo off
cd /d "%~dp0"
title Deokive Server

echo ====================================================
echo  Starting Deokive server
echo ====================================================
echo.
echo [1/2] Installing dependencies...
python -m pip install -q -r requirements.txt

echo [2/2] Initializing DB (kept if it already exists)...
python init_sqlite_db.py

echo.
echo  Configure the sole admin account in .env before first launch:
echo    SOLE_ADMIN_LOGIN_ID=myid
echo    SOLE_ADMIN_PASSWORD=mypassword
echo    SOLE_ADMIN_NICKNAME=MyNickname
echo  Then run:
echo    python make_admin.py
echo.
echo ====================================================
echo  Server: http://0.0.0.0:8000
echo   - health : http://localhost:8000/health
echo   - admin  : http://localhost:8000/admin
echo   - board  : http://localhost:8000/board/posts
echo  External/app uses PUBLIC_IP:8000 (needs port forward)
echo  Stop: press Ctrl+C in this window
echo ====================================================
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo Server stopped.
pause
