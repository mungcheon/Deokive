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
echo  First time only - create an admin in ANOTHER window:
echo    python make_admin.py --create myid mypassword nickname
echo.
echo ====================================================
echo  Server: http://0.0.0.0:8000
echo   - health : http://localhost:8000/health
echo   - admin  : http://localhost:8000/admin
echo   - board  : http://localhost:8000/board/posts
echo  External/app uses  PUBLIC_IP:8000  (needs port forward)
echo  Stop: press Ctrl+C in this window
echo ====================================================
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo Server stopped.
pause
