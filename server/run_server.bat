@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Deokive Server

echo ====================================================
echo  Deokive 서버 시작 준비
echo ====================================================
echo.
echo [1/3] 의존성 설치 중...
python -m pip install -q -r requirements.txt

echo [2/3] DB 초기화 (이미 있으면 그대로 사용)...
python init_sqlite_db.py

echo [3/3] 관리자 계정 확인...
echo     처음이면 아래 명령을 한 번 실행하세요(다른 창에서):
echo     python make_admin.py --create 아이디 비밀번호 닉네임
echo.
echo ====================================================
echo  서버 실행: http://0.0.0.0:8000
echo  - 상태    : http://localhost:8000/health
echo  - 관리자  : http://localhost:8000/admin
echo  - 게시판  : http://localhost:8000/board/posts
echo.
echo  외부(앱/포트포워드)에서는 공인IP:8000 으로 접속
echo  멈추려면 이 창에서 Ctrl+C
echo ====================================================
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo 서버가 종료되었습니다.
pause
