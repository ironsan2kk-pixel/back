@echo off
chcp 65001 >nul

:: Start bot in minimized window (background mode)
:: Use this file to run bot without visible window

cd /d "%~dp0"

echo [*] Starting bot in background mode...

:: Method 1: Start in minimized window
start "" /min cmd /c "%~dp0start_bot.bat"

echo [OK] Bot started in background mode
echo     To stop use stop_bot.bat
timeout /t 3
