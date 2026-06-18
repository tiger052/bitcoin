@echo off
title J1 Auto Bitcoin Trading Bot
echo ===================================================
echo   J1 Auto Bitcoin Trading Bot & Web Dashboard
echo ===================================================
echo.
echo * 대시보드 주소: http://127.0.0.1:5000
echo * 기밀 설정 파일: b_dev/bitcoin_server/secrets.json
echo.
echo 프로그램을 시작합니다...
echo.

cd /d "%~dp0b_dev\bitcoin_server"
python main.py

pause
