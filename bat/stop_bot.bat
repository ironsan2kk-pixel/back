@echo off
chcp 65001 >nul
title Stop Bot

echo ===============================================================
echo                       STOPPING BOT
echo ===============================================================
echo.

:: Find and kill Python process with bot.py
echo [*] Looking for bot process...

:: Method 1: Via tasklist and findstr
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo list ^| findstr "PID:"') do (
    wmic process where "processid=%%a" get commandline 2>nul | findstr "bot.py" >nul
    if not errorlevel 1 (
        echo [*] Stopping process PID: %%a
        taskkill /pid %%a /f >nul 2>&1
    )
)

:: Method 2: Via wmic directly
wmic process where "name='python.exe' and commandline like '%%bot.py%%'" call terminate >nul 2>&1

:: Remove PID file
cd /d "%~dp0"
cd ..
if exist "data\bot.pid" (
    del "data\bot.pid"
    echo [OK] PID file removed
)

echo.
echo ===============================================================
echo                      BOT STOPPED
echo ===============================================================
echo.
timeout /t 3
