@echo off
cd /d "%~dp0"
title Deokive Server EXE Build

echo ====================================================
echo  Building Deokive standalone server (.exe)
echo ====================================================
echo.
echo [1/2] Installing build tools...
python -m pip install -q -r requirements.txt
python -m pip install -q pyinstaller

echo [2/2] Building exe (takes 1-2 minutes)...
python -m PyInstaller --onefile --name deokive_server --noconfirm --add-data "app/static;static" --collect-submodules uvicorn --collect-submodules app --hidden-import bcrypt server_exe.py

echo.
echo ====================================================
echo  Done -^> dist\deokive_server.exe
echo  Double-click that exe to run the server.
echo  First run auto-creates an admin (id/pw shown in console).
echo ====================================================
pause
