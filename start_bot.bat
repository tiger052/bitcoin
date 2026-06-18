@echo off
title J1 Auto Bitcoin Trading Bot
echo ===================================================
echo   J1 Auto Bitcoin Trading Bot and Web Dashboard
echo ===================================================
echo.
echo * Dashboard URL: http://127.0.0.1:5000
echo * Secrets File: b_dev/bitcoin_server/secrets.json
echo.
echo Starting the program...
echo.

cd /d "%~dp0b_dev\bitcoin_server"
python main.py

pause
