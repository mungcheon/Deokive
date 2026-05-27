@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deokive 서버 exe 빌드

echo ====================================================
echo  Deokive 서버 독립 실행파일(.exe) 빌드
echo ====================================================
echo.
echo [1/2] 빌드 도구 설치...
python -m pip install -q -r requirements.txt
python -m pip install -q pyinstaller

echo [2/2] exe 빌드 중... (1~2분)
python -m PyInstaller --onefile --name deokive_server --noconfirm ^
  --add-data "app/static;static" ^
  --collect-submodules uvicorn ^
  --collect-submodules app ^
  --hidden-import bcrypt ^
  server_exe.py

echo.
echo ====================================================
echo  완료!  dist\deokive_server.exe
echo  더블클릭하면 서버가 켜지고, 첫 실행 시 관리자 계정이
echo  자동 생성됩니다 (콘솔에 아이디/비번 출력).
echo ====================================================
pause
