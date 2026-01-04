@echo off
chcp 65001 >nul
title Restart Bot

echo ===============================================================
echo                      RESTARTING BOT
echo ===============================================================
echo.

cd /d "%~dp0"

:: Stop bot
echo [*] Stopping current process...
call stop_bot.bat

:: Wait
echo [*] Waiting 3 seconds...
timeout /t 3 /nobreak >nul

:: Start bot
echo [*] Starting bot...
start "" /min "%~dp0start_bot.bat"

echo.
echo ===============================================================
echo                     BOT RESTARTED
echo ===============================================================
echo.
timeout /t 3
